"""
WebSocket Chat module — JARVIS 2.0 Dual-Model Architecture.

Flow:
  1. Message arrives via WebSocket.
  2. Router (OSS 20B) classifies intent in < 300ms.
  3a. If 'chat': fast model streams response sentence-by-sentence to the client.
  3b. If 'tool': sends ThinkingResponse (stalling phrase) immediately, then
      launches a background task that calls the Reasoning model (Qwen 27B),
      executes tools, and streams the final response — without blocking the WebSocket.
"""
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.models.schemas import (
    HandshakeRequest, MessageRequest, ToolResultRequest,
    ToolCallResponse, SpeakResponse, ThinkingResponse,
    TaskPlanResponse, TaskUpdateResponse
)
from app.core.config import settings
from app.services.memory_service import add_message, get_recent_history, save_memory, search_memory
from app.services.llm_service import chat_reasoning, stream_fast_response
from app.services.router_service import classify_intent
from app.services.scheduler_service import schedule_reminder
from app.services.connection_manager import manager

router = APIRouter()


# ---------------------------------------------------------------------------
# Status broadcast loop
# ---------------------------------------------------------------------------

async def broadcast_status_loop(websocket: WebSocket, session_id: str):
    try:
        while True:
            await asyncio.sleep(3)
            if session_id in manager.active_connections:
                info = manager.get_active_clients_info()
                info["type"] = "system_status"
                try:
                    await websocket.send_text(json.dumps(info))
                except Exception:
                    break
            else:
                break
    except Exception:
        pass


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@router.websocket("/ws")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()

    session_id = "default_session"
    client_os = "unknown"
    client_caps = []
    username = "Invitado"
    role = "user"

    try:
        initial_data = await websocket.receive_text()
        try:
            handshake = HandshakeRequest.model_validate_json(initial_data)
            session_id = handshake.client_id
            client_os = handshake.os
            client_caps = handshake.capabilities
            username = handshake.username
            role = handshake.role
            device_name = handshake.device_name

            meta = {
                "username": username,
                "role": role,
                "os": client_os,
                "device_name": device_name
            }
            await manager.connect(session_id, websocket, meta=meta)
            print(f" Handshake exitoso de {session_id} (Usuario: {username}, OS: {client_os})")

            asyncio.create_task(broadcast_status_loop(websocket, session_id))

        except Exception as e:
            print(f"️ Handshake inválido: {e}")
            await websocket.send_text(SpeakResponse(message="Handshake Protocol Error.").model_dump_json())
            return

        while True:
            raw_msg = await websocket.receive_text()

            try:
                data = json.loads(raw_msg)
                msg_type = data.get("type")

                if msg_type == "message":
                    msg_obj = MessageRequest(**data)
                    print(f" User: {msg_obj.content}")

                    await add_message(session_id, {"role": "user", "content": msg_obj.content})
                    try:
                        await process_message(websocket, session_id, client_os, client_caps, username, role)
                    except Exception as err:
                        print(f"[WS ERROR] Error en process_message: {err}")
                        import traceback; traceback.print_exc()
                        await _send_loop_step(websocket, "idle", "error", detail=f"Error: {str(err)[:50]}")
                        await websocket.send_text(SpeakResponse(message="Disculpe señor, ocurrió un error procesando su solicitud.").model_dump_json())

                elif msg_type == "tool_result":
                    res_obj = ToolResultRequest(**data)
                    output_text = res_obj.output if not res_obj.error else f"Error: {res_obj.error}"
                    print(f" Tool Result: {output_text[:50]}...")

                    await add_message(session_id, {
                        "role": "tool",
                        "tool_call_id": res_obj.tool_call_id,
                        "name": "execute_command",
                        "content": output_text
                    })

                    # After a tool result, we go straight to reasoning (no need to re-classify)
                    history = await get_recent_history(session_id, limit=10)
                    asyncio.create_task(
                        _run_reasoning_and_respond(websocket, session_id, history, client_os, client_caps, username, role)
                    )

            except json.JSONDecodeError:
                print(" Mensaje WS no es JSON")

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        print(f" Cliente {session_id} desconectado")
    except Exception as e:
        manager.disconnect(session_id)
        print(f" Error fatal websocket: {e}")



# ---------------------------------------------------------------------------
# Main message routing logic
# ---------------------------------------------------------------------------

async def _send_loop_step(websocket: WebSocket, step: str, status: str = "active", **kwargs):
    """Emits real-time Loop Engineering process step events to the frontend HUD."""
    try:
        payload = {
            "type": "loop_step",
            "step": step,
            "status": status,
            **kwargs
        }
        await websocket.send_text(json.dumps(payload))
    except Exception:
        pass


async def process_message(
    websocket: WebSocket,
    session_id: str,
    client_os: str,
    client_caps: list,
    username: str,
    role: str,
):
    """
    Loop Engineering Pipeline:
    1. Ingestion: Prompt received.
    2. Fast Router: groq/compound-mini classifies domain and stalling phrase.
    3. Context Pruner: Prunes skills to match domain (< 1200 tokens).
    4. Reasoning / Fast Stream: Routes to reasoning or fast generator.
    """
    history = await get_recent_history(session_id, limit=6)

    # 1. Ingestion
    await _send_loop_step(websocket, "ingestion", "active", detail="Prompt recibido y verificado")

    # 2. Fast Router
    await _send_loop_step(websocket, "router", "active", model=settings.ROUTER_MODEL, detail=f"Clasificando con {settings.ROUTER_MODEL}...")
    classification = await classify_intent(history)
    intent = classification.get("intent", "tool")
    domain = classification.get("domain", "system")
    stalling_phrase = classification.get("stalling_phrase", "")
    await _send_loop_step(websocket, "router", "completed", domain=domain, intent=intent, stalling=stalling_phrase, detail=f"Dominio: {domain.upper()}")

    print(f"[ROUTER] Dominio: {domain} | Intent: {intent}")

    if intent == "chat":
        # Branch Left: Nodo 2A Fast Conversational Stream
        await _send_loop_step(websocket, "fast_stream", "active", model=settings.FAST_MODEL, detail=f"Streaming respuesta rápida con {settings.FAST_MODEL}...")
        await _stream_fast_and_save(websocket, session_id, history, client_os, username)
        await _send_loop_step(websocket, "fast_stream", "completed", detail="Respuesta conversacional generada")
        await _send_loop_step(websocket, "synthesizer", "active", detail="Audio TTS y renderizado en HUD")
        await _send_loop_step(websocket, "idle", "idle", detail="Ciclo completado. JARVIS en espera.")
    else:
        # Branch Right: Nodo 2B Context & Skill Pruner
        await _send_loop_step(websocket, "pruning", "completed", domain=domain, detail=f"Inyectando SOLO skills de {domain.upper()} (< 1,200 tokens)")

        # Send stalling phrase immediately
        if stalling_phrase:
            thinking_resp = ThinkingResponse(message=stalling_phrase)
            await websocket.send_text(thinking_resp.model_dump_json())
            print(f" [STALLING] Jarvis dice: {stalling_phrase}")

        # 4. Launch reasoning in background
        asyncio.create_task(
            _run_reasoning_and_respond(websocket, session_id, history, client_os, client_caps, username, role, domain=domain)
        )


# ---------------------------------------------------------------------------
# Fast streaming path
# ---------------------------------------------------------------------------

async def _stream_fast_and_save(
    websocket: WebSocket,
    session_id: str,
    history: list,
    client_os: str,
    username: str,
):
    """Streams the fast model response sentence-by-sentence and saves the full reply."""
    full_response = []
    try:
        sentence_queue = await stream_fast_response(history, client_os, username)
        while True:
            sentence = await sentence_queue.get()
            if sentence is None:
                break
            full_response.append(sentence)
            resp = SpeakResponse(message=sentence)
            print(f" [FAST] Jarvis dice: {sentence}")
            await websocket.send_text(resp.model_dump_json())
    except Exception as e:
        print(f"️ Error en streaming rápido: {e}")
        error_msg = "Disculpe señor, ocurrió un error procesando su solicitud."
        full_response.append(error_msg)
        await websocket.send_text(SpeakResponse(message=error_msg).model_dump_json())

    # Save the complete assembled response to history
    complete = " ".join(full_response)
    if complete:
        await add_message(session_id, {"role": "assistant", "content": complete})


# ---------------------------------------------------------------------------
# Reasoning path — background task
# ---------------------------------------------------------------------------

async def _run_reasoning_and_respond(
    websocket: WebSocket,
    session_id: str,
    history: list,
    client_os: str,
    client_caps: list,
    username: str,
    role: str,
    domain: str = None,
):
    """
    Background task: calls the Reasoning model with domain-specific tools and handles tool execution.
    """
    try:
        await _send_loop_step(websocket, "reasoning", "active", model=settings.REASONING_MODEL, domain=domain, detail=f"Orquestador de razonamiento con {settings.REASONING_MODEL}...")
        action = await chat_reasoning(history, client_os, client_caps, username, role, domain=domain)
        await _send_loop_step(websocket, "reasoning", "completed", detail="Razonamiento completado")
        await _dispatch_action(websocket, session_id, action, client_os, client_caps, username, role)
    except Exception as e:
        print(f"️ Error en tarea de razonamiento: {e}")
        try:
            await websocket.send_text(
                SpeakResponse(message="Señor, ocurrió un error en el proceso de razonamiento.").model_dump_json()
            )
            await _send_loop_step(websocket, "idle", "error", detail=f"Error en razonamiento: {str(e)[:60]}")
        except Exception:
            pass




async def _dispatch_action(
    websocket: WebSocket,
    session_id: str,
    action: dict,
    client_os: str,
    client_caps: list,
    username: str,
    role: str,
):
    """
    Dispatches an action dict returned by the reasoning model.
    Mirrors the old process_llm_loop logic but is called from an async background task.
    """
    if action["type"] == "tool_call":
        if action["tool"] == "execute_command":
            await add_message(session_id, {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": action["tool_call_id"],
                    "type": "function",
                    "function": {
                        "name": "execute_command",
                        "arguments": json.dumps({"command": action["command"]})
                    }
                }]
            })

            await _send_loop_step(websocket, "skill_runner", "active", skill="terminal_cmd", detail=f"Ejecutando comando: {action['command'][:35]}...")
            resp = ToolCallResponse(
                tool_call_id=action["tool_call_id"],
                tool="execute_command",
                command=action["command"]
            )
            print(f" Jarvis ejecuta: {action['command']}")
            await websocket.send_text(resp.model_dump_json())
            # Will resume when client sends tool_result

        elif action["tool"] == "execute_skill":
            skill_name = action["skill_name"]
            params = action["params"]

            await add_message(session_id, {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": action["tool_call_id"],
                    "type": "function",
                    "function": {
                        "name": skill_name,
                        "arguments": json.dumps(params)
                    }
                }]
            })

            await _send_loop_step(websocket, "skill_runner", "active", skill=skill_name, detail=f"Invocando skill: {skill_name}...")
            resp = ToolCallResponse(
                tool_call_id=action["tool_call_id"],
                tool="execute_skill",
                skill_name=skill_name,
                params=params
            )
            print(f" Jarvis usa skill: {skill_name}")
            await websocket.send_text(resp.model_dump_json())

    elif action["type"] == "server_skill":
        await _send_loop_step(websocket, "skill_runner", "active", skill=action.get("skill_name"), detail=f"Ejecutando server skill: {action.get('skill_name')}...")
        await _handle_server_skill(websocket, session_id, action, client_os, client_caps, username, role)

    elif action["type"] == "server_tool":
        await _send_loop_step(websocket, "skill_runner", "active", skill=action.get("tool"), detail=f"Ejecutando server tool: {action.get('tool')}...")
        await _handle_server_tool(websocket, session_id, action, client_os, client_caps, username, role)

    elif action["type"] == "speak":
        await add_message(session_id, {
            "role": "assistant",
            "content": action["message"]
        })
        # Nodo 5: Executive Response Formatter
        await _send_loop_step(websocket, "formatter", "completed", detail="Respuesta ejecutiva estructurada")
        # Salida: TTS Streaming Local pyttsx3 + HUD
        await _send_loop_step(websocket, "synthesizer", "active", detail="Transmitiendo respuesta a TTS local + HUD...")
        resp = SpeakResponse(message=action["message"])
        print(f" Jarvis dice: {action['message']}")
        await websocket.send_text(resp.model_dump_json())
        await _send_loop_step(websocket, "idle", "idle", detail="Ciclo completado. JARVIS en espera.")


# ---------------------------------------------------------------------------
# Server-side tool/skill handlers
# ---------------------------------------------------------------------------

async def _handle_server_skill(
    websocket: WebSocket, session_id: str, action: dict,
    client_os: str, client_caps: list, username: str, role: str
):
    import os, tempfile, sys, subprocess

    skill_name = action["skill_name"]
    params = action["params"]
    skill_path = action["skill_path"]
    executable = action["executable"]
    language = action["language"].lower()

    await add_message(session_id, {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": action["tool_call_id"],
            "type": "function",
            "function": {
                "name": skill_name,
                "arguments": json.dumps(params)
            }
        }]
    })

    await websocket.send_text(SpeakResponse(message=f"Un momento señor, ejecuto la skill: {skill_name}...").model_dump_json())
    print(f" Jarvis usa skill de backend: {skill_name}")

    try:
        script_path = os.path.join(skill_path, executable)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
            json.dump(params, tmp)
            tmp_path = tmp.name

        if language == "python":
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
            venv_python = os.path.join(project_root, "venv", "Scripts", "python.exe")
            cmd = [venv_python if os.path.exists(venv_python) else sys.executable, script_path, tmp_path]
        elif language == "powershell":
            cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path, tmp_path]
        else:
            raise ValueError(f"Language {language} not supported.")

        process = await asyncio.to_thread(
            subprocess.run, cmd,
            capture_output=True, text=True, encoding='utf-8', errors='replace'
        )

        try:
            os.remove(tmp_path)
        except Exception:
            pass

        output = process.stdout + process.stderr
        if not output.strip():
            output = "Skill executed successfully (no output)."

    except Exception as e:
        output = f"Error ejecutando skill de backend: {e}"

    print(f"️ Tool Result (Backend): {output[:50]}...")

    await add_message(session_id, {
        "role": "tool",
        "tool_call_id": action["tool_call_id"],
        "name": skill_name,
        "content": output
    })

    # Continue the reasoning loop
    history = await get_recent_history(session_id, limit=10)
    await _run_reasoning_and_respond(websocket, session_id, history, client_os, client_caps, username, role)


async def _handle_server_tool(
    websocket: WebSocket, session_id: str, action: dict,
    client_os: str, client_caps: list, username: str, role: str
):
    tool = action["tool"]

    # --- Schedule reminder ---
    if tool == "schedule_reminder":
        msg = action["message"]
        delay = action["delay_seconds"]

        await add_message(session_id, {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": action["tool_call_id"],
                "type": "function",
                "function": {
                    "name": "schedule_reminder",
                    "arguments": json.dumps({"message": msg, "delay_seconds": delay})
                }
            }]
        })

        schedule_reminder(session_id, msg, delay)

        await add_message(session_id, {
            "role": "tool",
            "tool_call_id": action["tool_call_id"],
            "name": "schedule_reminder",
            "content": f"El recordatorio fue agendado exitosamente para dentro de {delay} segundos."
        })

        history = await get_recent_history(session_id, limit=10)
        await _run_reasoning_and_respond(websocket, session_id, history, client_os, client_caps, username, role)

    # --- Create plan ---
    elif tool == "create_plan":
        title = action["title"]
        steps = action["steps"]

        await add_message(session_id, {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": action["tool_call_id"],
                "type": "function",
                "function": {
                    "name": "create_plan",
                    "arguments": json.dumps({"title": title, "steps": steps})
                }
            }]
        })

        await websocket.send_text(TaskPlanResponse(title=title, steps=steps).model_dump_json())

        await add_message(session_id, {
            "role": "tool",
            "tool_call_id": action["tool_call_id"],
            "name": "create_plan",
            "content": "Plan creado exitosamente y mostrado al usuario."
        })

        history = await get_recent_history(session_id, limit=10)
        await _run_reasoning_and_respond(websocket, session_id, history, client_os, client_caps, username, role)

    # --- Update plan step ---
    elif tool == "update_plan_step":
        step_index = action["step_index"]
        status = action["status"]

        await add_message(session_id, {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": action["tool_call_id"],
                "type": "function",
                "function": {
                    "name": "update_plan_step",
                    "arguments": json.dumps({"step_index": step_index, "status": status})
                }
            }]
        })

        await websocket.send_text(TaskUpdateResponse(step_index=step_index, status=status).model_dump_json())

        await add_message(session_id, {
            "role": "tool",
            "tool_call_id": action["tool_call_id"],
            "name": "update_plan_step",
            "content": f"Paso {step_index} actualizado a estado {status}."
        })

        history = await get_recent_history(session_id, limit=10)
        await _run_reasoning_and_respond(websocket, session_id, history, client_os, client_caps, username, role)

    # --- Save memory ---
    elif tool == "save_memory":
        fact = action["fact"]

        await add_message(session_id, {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": action["tool_call_id"],
                "type": "function",
                "function": {
                    "name": "save_memory",
                    "arguments": json.dumps({"fact": fact})
                }
            }]
        })

        result = await save_memory(fact)

        await add_message(session_id, {
            "role": "tool",
            "tool_call_id": action["tool_call_id"],
            "name": "save_memory",
            "content": result
        })

        history = await get_recent_history(session_id, limit=10)
        await _run_reasoning_and_respond(websocket, session_id, history, client_os, client_caps, username, role)

    # --- Search memory ---
    elif tool == "search_memory":
        query = action["query"]

        await add_message(session_id, {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": action["tool_call_id"],
                "type": "function",
                "function": {
                    "name": "search_memory",
                    "arguments": json.dumps({"query": query})
                }
            }]
        })

        result = await search_memory(query)

        await add_message(session_id, {
            "role": "tool",
            "tool_call_id": action["tool_call_id"],
            "name": "search_memory",
            "content": result
        })

        history = await get_recent_history(session_id, limit=10)
        await _run_reasoning_and_respond(websocket, session_id, history, client_os, client_caps, username, role)
