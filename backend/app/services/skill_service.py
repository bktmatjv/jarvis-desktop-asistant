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

def get_llm_tools():
    skills = load_skills()
    llm_tools = []
    for skill in skills:
        tool = {
            "type": "function",
            "function": {
                "name": skill.get("name"),
                "description": skill.get("description", ""),
                "parameters": skill.get("parameters", {"type": "object", "properties": {}})
            }
        }
        llm_tools.append(tool)
    return llm_tools
