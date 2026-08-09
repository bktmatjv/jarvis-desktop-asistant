"""
LLM Service module.
Handles integration with the Groq API, tool definitions, and API key rotation for rate limits.
"""
import json
import asyncio
from groq import AsyncGroq, RateLimitError, APIStatusError
from app.core.config import settings

api_keys = [k.strip() for k in settings.GROQ_API_KEYS.split(",") if k.strip()]
if not api_keys:
    raise ValueError("Debes proveer al menos una GROQ_API_KEYS en el .env")

clients = [AsyncGroq(api_key=key) for key in api_keys]
current_client_idx = 0

tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_bash",
            "description": "Ejecuta un comando bash en la terminal del cliente. Útil para investigar, abrir archivos o explorar el sistema. Usa comandos no interactivos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "El comando bash a ejecutar. Ejemplo: ls -la, pwd, echo hello, google-chrome &"
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_reminder",
            "description": "Agenda un recordatorio o notificación proactiva para el futuro en el lado del servidor. El servidor te despertará y te pedirá que le digas esto al usuario cuando el temporizador expire.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "El mensaje o recordatorio exacto que quieres decirle al usuario cuando el temporizador expire."
                    },
                    "delay_seconds": {
                        "type": "integer",
                        "description": "La cantidad de segundos a esperar antes de notificar al usuario. (ej. 60 para 1 minuto)"
                    }
                },
                "required": ["message", "delay_seconds"],
            },
        },
    }
]

async def chat_with_jarvis(session_history: list, client_os: str, client_caps: list) -> dict:
    global current_client_idx
    
    system_prompt = f"""Eres JARVIS, el asistente de escritorio autónomo.
Estás conectado al dispositivo del usuario con sistema operativo: {client_os}.
Capacidades del cliente: {client_caps}.

Si necesitas investigar el sistema, abrir una aplicación o realizar una acción, TIENES que usar obligatoriamente la herramienta 'execute_bash'.
Responde textualmente si ya completaste una acción o si simplemente estás charlando."""

    clean_history = []
    allowed_keys = {"role", "content", "name", "tool_call_id", "tool_calls"}
    for msg in session_history:
        clean_msg = {k: v for k, v in msg.items() if k in allowed_keys}
        clean_history.append(clean_msg)

    messages = [{"role": "system", "content": system_prompt}] + clean_history
    
    for attempt in range(len(clients)):
        groq_client = clients[current_client_idx]
        try:
            response = await groq_client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=1000
            )
            
            response_message = response.choices[0].message
            
            if response_message.tool_calls:
                tool_call = response_message.tool_calls[0]
                if tool_call.function.name == "execute_bash":
                    args = json.loads(tool_call.function.arguments)
                    return {
                        "type": "tool_call",
                        "tool": "execute_bash",
                        "command": args.get("command", "echo 'Error: Comando vacío'"),
                        "tool_call_id": tool_call.id
                    }
                elif tool_call.function.name == "schedule_reminder":
                    args = json.loads(tool_call.function.arguments)
                    return {
                        "type": "server_tool",
                        "tool": "schedule_reminder",
                        "message": args.get("message", "Recordatorio vacío"),
                        "delay_seconds": args.get("delay_seconds", 60),
                        "tool_call_id": tool_call.id
                    }
                    
            return {
                "type": "speak",
                "message": response_message.content or "..."
            }
            
        except (RateLimitError, APIStatusError) as e:
            if getattr(e, 'status_code', 0) == 429 or isinstance(e, RateLimitError):
                print(f"Rate Limit reached for key index {current_client_idx}. Rotating...")
                current_client_idx = (current_client_idx + 1) % len(clients)
                await asyncio.sleep(1)
                continue
            else:
                print(f"Groq API Error: {e}")
                return {"type": "speak", "message": f"Error interno en el LLM: {str(e)}"}
        except Exception as e:
            print(f"Error en Groq API: {e}")
            return {"type": "speak", "message": f"Error interno en el LLM: {str(e)}"}
            
    return {"type": "speak", "message": "All Groq API keys exhausted due to rate limits."}
