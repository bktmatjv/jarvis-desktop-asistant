"""
Executor module.
Parses JSON commands received from the backend via WebSocket and maps them to local execution functions (UI updates, Bash execution, or local tools).
"""
import asyncio
from repl import repl_instance
from tool_registry import get_tool

DANGEROUS_WORDS = ["rm -rf", "chmod", "chown", "mkfs", "dd", "mkpasswd", "passwd"]

# Variable global para pausar la ejecución y esperar la respuesta del usuario
security_event = asyncio.Event()
security_allowed = False

# Variable global para pausar la ejecución y esperar la respuesta del usuario
async def execute_from_server(action: dict):
    """Procesa el JSON enviado por el servidor."""
    import main  # Importación local para evitar circular import
    
    msg_type = action.get("type")
    tool_name = action.get("tool")
    
    if msg_type == "speak":
        main.update_ui_response(action.get("message", ""))
        return None
        
    tool_name = action.get("tool")
    
    if tool_name == "execute_bash":
        command = action.get("command", "")
        tool_call_id = action.get("tool_call_id", "")
        import main
        main.ui_print(f"⚙️ EJECUTANDO: {command}")
        main.set_action_status(command)
        
        is_dangerous = any(word in command for word in DANGEROUS_WORDS)
        if is_dangerous:
            main.ui_print("⚠️ ALERTA DE SEGURIDAD DETECTADA")
            security_event.clear()
            global security_allowed
            security_allowed = False
            if main.window:
                safe_cmd = command.replace("'", "\\'").replace('"', '\\"')
                main.window.evaluate_js(f"showSecurityAlert('{safe_cmd}')")
            await security_event.wait()
            
            if not security_allowed:
                main.ui_print("⛔ EJECUCIÓN DENEGADA POR EL USUARIO")
                return {"type": "tool_result", "tool_call_id": tool_call_id, "output": "Execution denied by user due to security risk."}
            else:
                main.ui_print("✅ EJECUCIÓN PERMITIDA")
                
        output = await repl_instance.execute_command(command)
        main.show_action_output(output)
        return {"type": "tool_result", "tool_call_id": tool_call_id, "output": output}
        
    elif tool_name:
        tool_func = get_tool(tool_name)
        if tool_func:
            params = action.get("params", {})
            try:
                result = tool_func(**params) if isinstance(params, dict) else tool_func(params)
                return {"type": "tool_result", "tool_call_id": tool_call_id, "output": str(result) if result else "Success"}
            except Exception as e:
                return {"type": "tool_result", "tool_call_id": tool_call_id, "error": str(e)}
        else:
            return {"type": "tool_result", "tool_call_id": tool_call_id, "error": f"Tool '{tool_name}' not found locally."}
    
    return {"type": "error", "message": "Unknown action type"}

def resolve_security(allowed: bool):
    """Llamado desde pywebview cuando el usuario hace clic en el modal."""
    global security_allowed
    security_allowed = allowed
    security_event.set()