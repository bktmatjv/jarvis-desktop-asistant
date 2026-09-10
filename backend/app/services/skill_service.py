import os
import json

def get_skills_path():
    # backend/app/services/skill_service.py -> backend/app/services -> backend/app -> backend -> root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    return os.path.join(project_root, "client", "skills")

def load_skills():
    skills = []
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    
    backend_skills_dir = os.path.join(project_root, "backend", "skills")
    client_skills_dir = os.path.join(project_root, "client", "skills")
    
    # Load backend skills
    if os.path.exists(backend_skills_dir):
        for item in os.listdir(backend_skills_dir):
            skill_path = os.path.join(backend_skills_dir, item)
            if os.path.isdir(skill_path):
                json_path = os.path.join(skill_path, "skill.json")
                if os.path.exists(json_path):
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            skill_def = json.load(f)
                            skill_def["_is_dynamic"] = True 
                            skill_def["_execution_context"] = "backend"
                            skill_def["_path"] = skill_path
                            skills.append(skill_def)
                    except Exception as e:
                        print(f"Error loading backend skill from {json_path}: {e}")
                        
    # Load client skills
    if os.path.exists(client_skills_dir):
        for item in os.listdir(client_skills_dir):
            skill_path = os.path.join(client_skills_dir, item)
            if os.path.isdir(skill_path):
                json_path = os.path.join(skill_path, "skill.json")
                if os.path.exists(json_path):
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            skill_def = json.load(f)
                            skill_def["_is_dynamic"] = True 
                            skill_def["_execution_context"] = "client"
                            skills.append(skill_def)
                    except Exception as e:
                        print(f"Error loading client skill from {json_path}: {e}")
                        
    return skills

DOMAIN_SKILL_MAP = {
    "system": ["system_control", "window_manager", "system_telemetry", "input_controller", "execute_command"],
    "research": ["web_search", "web_fetch", "search_memory", "save_memory"],
    "media": ["play_ytmusic", "media_control", "system_control"],
    "chat": []
}

def get_tools_for_domain(domain: str = None, all_core_tools: list = None):
    """
    Skill & Context Pruner: returns only the tools/skills relevant to the target domain.
    Drastically reduces token usage to avoid Groq TPM rate limits.
    """
    if all_core_tools is None:
        all_core_tools = []

    if domain == "chat":
        return []

    target_names = DOMAIN_SKILL_MAP.get(domain)
    
    # If no specific domain match, return all available tools
    all_skills = load_skills()
    dynamic_tools = []
    for skill in all_skills:
        name = skill.get("name")
        if target_names is None or name in target_names:
            dynamic_tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": skill.get("description", ""),
                    "parameters": skill.get("parameters", {"type": "object", "properties": {}})
                }
            })

    # Filter core tools (execute_command, schedule_reminder, etc.)
    filtered_core = []
    for ct in all_core_tools:
        c_name = ct.get("function", {}).get("name")
        if target_names is None or c_name in target_names:
            filtered_core.append(ct)

    # Always ensure at least the domain-specific tools or fallback to core
    combined = filtered_core + dynamic_tools
    if not combined and domain != "chat":
        # Safe fallback: at least provide execute_command
        return [ct for ct in all_core_tools if ct.get("function", {}).get("name") == "execute_command"]

    return combined

