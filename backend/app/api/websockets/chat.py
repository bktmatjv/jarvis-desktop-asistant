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
                    await process_message(websocket, session_id, client_os, client_caps, username, role)

                elif msg_type == "tool_result":
                    res_obj = ToolResultRequest(**data)
                    output_text = res_obj.output if not res_obj.error else f"Error: {res_obj.error}"
                    print(f"️ Tool Result: {output_text[:50]}...")

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
                print("️ Mensaje WS no es JSON")

    except WebSocketDisconnect:
        manager.disconnect(session_id)
        print(f" Cliente {session_id} desconectado")
    except Exception as e:
        manager.disconnect(session_id)
        print(f"️ Error fatal websocket: {e}")


# ---------------------------------------------------------------------------
# Main message routing logic
# ---------------------------------------------------------------------------

async def process_message(
    websocket: WebSocket,
    session_id: str,
    client_os: str,
    client_caps: list,
    username: str,
    role: str,
):
    """
    1. Classify intent with OSS 20B (fast, < 300ms).
    2a. 'chat' → Stream response from OSS 20B sentence by sentence.
    2b. 'tool' → Send ThinkingResponse immediately, then launch reasoning in background.
    """
    history = await get_recent_history(session_id, limit=10)

    # --- Step 1: Fast intent classification ---
    classification = await classify_intent(history)
    intent = classification["intent"]
    stalling_phrase = classification["stalling_phrase"]

    print(f"[ROUTER] Intent: {intent}")

    if intent == "chat":
        # --- Path A: Fast streaming response ---
        await _stream_fast_and_save(websocket, session_id, history, client_os, username)
    else:
        # --- Path B: Send stalling phrase immediately, reason in background ---
        if stalling_phrase:
            thinking_resp = ThinkingResponse(message=stalling_phrase)
            await websocket.send_text(thinking_resp.model_dump_json())
            print(f" [STALLING] Jarvis dice: {stalling_phrase}")

        # Launch reasoning as a non-blocking background task
        asyncio.create_task(
            _run_reasoning_and_respond(websocket, session_id, history, client_os, client_caps, username, role)
        )


# ---------------------------------------------------------------------------
# Fast streaming path (OSS 20B)
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
# Reasoning path (Qwen 27B) — background task
# ---------------------------------------------------------------------------

async def _run_reasoning_and_respond(
    websocket: WebSocket,
    session_id: str,
    history: list,
    client_os: str,
    client_caps: list,
    username: str,
    role: str,
):
    """
    Background task: calls the Reasoning model and handles the full tool-calling loop.
    Equivalent to the old process_llm_loop but runs without blocking the WebSocket.
    """
    try:
        action = await chat_reasoning(history, client_os, client_caps, username, role)
        await _dispatch_action(websocket, session_id, action, client_os, client_caps, username, role)
    except Exception as e:
        print(f"️ Error en tarea de razonamiento: {e}")
        try:
            await websocket.send_text(
                SpeakResponse(message="Señor, ocurrió un error en el proceso de razonamiento.").model_dump_json()
            )
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

            resp = ToolCallResponse(
                tool_call_id=action["tool_call_id"],
                tool="execute_skill",
                skill_name=skill_name,
                params=params
            )
            print(f" Jarvis usa skill: {skill_name}")
            await websocket.send_text(resp.model_dump_json())

    elif action["type"] == "server_skill":
        await _handle_server_skill(websocket, session_id, action, client_os, client_caps, username, role)

    elif action["type"] == "server_tool":
        await _handle_server_tool(websocket, session_id, action, client_os, client_caps, username, role)

    elif action["type"] == "speak":
        await add_message(session_id, {
            "role": "assistant",
            "content": action["message"]
        })
        resp = SpeakResponse(message=action["message"])
        print(f" Jarvis dice: {action['message']}")
        await websocket.send_text(resp.model_dump_json())


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
