"""
Executor module.
Parses JSON commands received from the backend via WebSocket and maps them to local execution functions (UI updates, Bash execution, or local tools).
"""
import asyncio
import json
import os
from repl import repl_instance
from tool_registry import get_tool

DANGEROUS_WORDS = ["rm -rf", "chmod", "chown", "mkfs", "dd", "mkpasswd", "passwd"]

# Variable global para pausar la ejecución y esperar la respuesta del usuario
security_event = asyncio.Event()
security_allowed = False

# Variable global para pausar la ejecución y esperar la respuesta del usuario
async def execute_from_server(action: dict):
    """Ejecuta una acción local enviada por el servidor WebSocket"""
    import main
    msg_type = action.get("type")
    main.reset_activity()
    
    tool_name = action.get("tool")
    
    if msg_type == "speak":
        mensaje = action.get("message", "")
        main.update_ui_response(mensaje)
        try:
            import voice_engine
            # Use streaming TTS: speaks sentence-by-sentence for lower perceived latency
            voice_engine.speak_streaming(mensaje)
        except Exception as e:
            print(f"Error al activar voz: {e}")
        return None

    if msg_type == "thinking":
        # Stalling phrase from the router — speak it immediately while Reasoning model works
        mensaje = action.get("message", "")
        try:
            import voice_engine
            voice_engine.speak(mensaje)  # Single short phrase, no need for streaming
        except Exception as e:
            print(f"Error al activar voz (thinking): {e}")
        # Show thinking indicator in HUD if available
        if main.window:
            try:
                safe_msg = __import__('json').dumps(str(mensaje))
                main.window.evaluate_js(f"showThinkingIndicator({safe_msg})")
            except Exception:
                pass
        return None

    if msg_type == "task_plan":
        title = action.get("title", "")
        steps = action.get("steps", [])
        if main.window:
            safe_title = title.replace("'", "\\'").replace('"', '\\"')
            steps_js = json.dumps(steps)
            main.window.evaluate_js(f"createTaskPlan('{safe_title}', {steps_js})")
        return None
        
    if msg_type == "task_update":
        step_index = action.get("step_index", 0)
        status = action.get("status", "")
        if main.window:
            safe_status = status.replace("'", "\\'").replace('"', '\\"')
            main.window.evaluate_js(f"updateTaskStep({step_index}, '{safe_status}')")
        return None

    if msg_type == "system_status":
        if main.window:
            safe_payload = json.dumps(action)
            main.window.evaluate_js(f"updateSystemStatus({safe_payload})")
        return None
        
    tool_name = action.get("tool")
    tool_call_id = action.get("tool_call_id", "")
    
    if tool_name == "execute_command":
        command = action.get("command", "")
        import main
        main.ui_print(f"[COLA DE PROCESOS] INICIANDO COMANDO: {command}")
        main.set_action_status(f"Comando: {command}")
        
        is_dangerous = any(word in command for word in DANGEROUS_WORDS)
        if is_dangerous:
            main.ui_print("[ALERTA] DE SEGURIDAD DETECTADA")
            security_event.clear()
            global security_allowed
            security_allowed = False
            if main.window:
                safe_cmd = command.replace("'", "\\'").replace('"', '\\"')
                main.window.evaluate_js(f"showSecurityAlert('{safe_cmd}')")
            await security_event.wait()
            
            if not security_allowed:
                main.ui_print("[DENEGADA] POR EL USUARIO")
                return {"type": "tool_result", "tool_call_id": tool_call_id, "output": "Execution denied by user due to security risk."}
            else:
                main.ui_print("[PERMITIDA] EJECUCIÓN")
                
        output = await repl_instance.execute_command(command)
        main.show_action_output(output)
        return {"type": "tool_result", "tool_call_id": tool_call_id, "output": output}
        
    elif tool_name == "execute_skill":
        skill_name = action.get("skill_name")
        params = action.get("params", {})
        
        import main
        main.ui_print(f"[COLA DE PROCESOS] INICIANDO SKILL: {skill_name}")
        main.set_action_status(f"Skill: {skill_name}")
        
        skills_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills")
        skill_path = os.path.join(skills_dir, skill_name)
        json_path = os.path.join(skill_path, "skill.json")
        
        if not os.path.exists(json_path):
            error_msg = f"Skill '{skill_name}' no encontrada en {json_path}"
            main.show_action_output(error_msg)
            return {"type": "tool_result", "tool_call_id": tool_call_id, "error": error_msg}
            
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                skill_def = json.load(f)
                
            executable = skill_def.get("executable")
            language = skill_def.get("language", "python").lower()
            
            if not executable:
                raise ValueError(f"La skill {skill_name} no define un 'executable' en skill.json")
                
            script_path = os.path.join(skill_path, executable)
            if not os.path.exists(script_path):
                raise ValueError(f"El script {script_path} no existe")
                
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as tmp:
                json.dump(params, tmp)
                tmp_path = tmp.name
                
            import sys
            if language == "python":
                cmd = [sys.executable, "-X", "utf8", script_path, tmp_path]
            elif language == "powershell":
                cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path, tmp_path]
            else:
                raise ValueError(f"Lenguaje {language} no soportado para skills")
                
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            try:
                os.remove(tmp_path)
            except:
                pass
                
            output = stdout.decode('utf-8', errors='replace') + stderr.decode('utf-8', errors='replace')
            if not output.strip():
                output = "Skill executed successfully (no output)."
                
            main.show_action_output(output)
            return {"type": "tool_result", "tool_call_id": tool_call_id, "output": output}
            
        except Exception as e:
            error_msg = f"Error ejecutando skill {skill_name}: {str(e)}"
            main.show_action_output(error_msg)
            return {"type": "tool_result", "tool_call_id": tool_call_id, "error": error_msg}
        
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