"""
WebSocket Chat module.
Handles incoming client connections, message routing, and delegates logic to the LLM Service.
"""
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.models.schemas import HandshakeRequest, MessageRequest, ToolResultRequest, ToolCallResponse, SpeakResponse
from app.services.memory_service import add_message, get_recent_history
from app.services.llm_service import chat_with_jarvis
from app.services.scheduler_service import schedule_reminder
from app.services.connection_manager import manager

router = APIRouter()

@router.websocket("/ws")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    session_id = "default_session"
    client_os = "unknown"
    client_caps = []
    
    try:
        initial_data = await websocket.receive_text()
        try:
            handshake = HandshakeRequest.model_validate_json(initial_data)
            session_id = handshake.client_id
            client_os = handshake.os
            client_caps = handshake.capabilities
            await manager.connect(session_id, websocket)
            print(f"✅ Handshake exitoso de {session_id} ({client_os})")
        except Exception as e:
            print(f"⚠️ Handshake inválido: {e}")
            await websocket.send_text(SpeakResponse(message="Handshake Protocol Error.").model_dump_json())
            return
            
        while True:
            raw_msg = await websocket.receive_text()
            
            try:
                data = json.loads(raw_msg)
                msg_type = data.get("type")
                
                if msg_type == "message":
                    msg_obj = MessageRequest(**data)
                    print(f"👤 User: {msg_obj.content}")
                    
                    await add_message(session_id, {"role": "user", "content": msg_obj.content})
                    await process_llm_loop(websocket, session_id, client_os, client_caps)
                    
                elif msg_type == "tool_result":
                    res_obj = ToolResultRequest(**data)
                    output_text = res_obj.output if not res_obj.error else f"Error: {res_obj.error}"
                    print(f"🖥️ Tool Result: {output_text[:50]}...")
                    
                    await add_message(session_id, {
                        "role": "tool",
                        "tool_call_id": res_obj.tool_call_id,
                        "name": "execute_bash",
                        "content": output_text
                    })
                    
                    await process_llm_loop(websocket, session_id, client_os, client_caps)
                    
            except json.JSONDecodeError:
                print("⚠️ Mensaje WS no es JSON")
                
    except WebSocketDisconnect:
        manager.disconnect(session_id)
        print(f"❌ Cliente {session_id} desconectado")
    except Exception as e:
        manager.disconnect(session_id)
        print(f"⚠️ Error fatal websocket: {e}")


async def process_llm_loop(websocket: WebSocket, session_id: str, client_os: str, client_caps: list):
    """
    Toma el historial (Sliding Window de 10) y llama a LLM. 
    Si decide usar la tool, envía ToolCall y termina (esperará a que el cliente envíe tool_result).
    Si decide hablar, envía SpeakResponse.
    """
    history = await get_recent_history(session_id, limit=10)
    
    action = await chat_with_jarvis(history, client_os, client_caps)
    
    if action["type"] == "tool_call":
        await add_message(session_id, {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": action["tool_call_id"],
                "type": "function",
                "function": {
                    "name": "execute_bash",
                    "arguments": json.dumps({"command": action["command"]})
                }
            }]
        })
        
        resp = ToolCallResponse(
            tool_call_id=action["tool_call_id"],
            command=action["command"]
        )
        print(f"🤖 Jarvis decide: {action['command']}")
        await websocket.send_text(resp.model_dump_json())
        
    elif action["type"] == "server_tool":
        if action["tool"] == "schedule_reminder":
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
            
            await process_llm_loop(websocket, session_id, client_os, client_caps)
            
    elif action["type"] == "speak":
        await add_message(session_id, {
            "role": "assistant",
            "content": action["message"]
        })
        
        resp = SpeakResponse(message=action["message"])
        print(f"🤖 Jarvis dice: {action['message']}")
        await websocket.send_text(resp.model_dump_json())
