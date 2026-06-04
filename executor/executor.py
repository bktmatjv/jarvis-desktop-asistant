from jarvis_scripts.script_manager import get_script
from tool_registry import get_tool

'''
    Documentacion:
    - Este módulo se encarga de ejecutar las acciones que el cerebro de Jarvis le indique, ya sea llamando a una herramienta específica del sistema o ejecutando un script personalizado creado por el usuario.
    - La función execute(action) recibe un diccionario que representa la acción a ejecutar. Si el diccionario contiene una clave "tool", se interpreta como una llamada a una herramienta específica, y se ejecuta la herramienta con los parámetros proporcionados. Si el diccionario tiene una clave "action" con el valor "run_script", se interpreta como una orden para ejecutar un script personalizado, y se carga el script por su nombre y se ejecuta paso a paso cada acción que contiene. Esta función es fundamental para que el cerebro de Jarvis pueda interactuar con el sistema operativo y realizar tareas complejas basadas en las órdenes del usuario. AUN EN DESARROLLO, NO TODAS LAS FUNCIONES ESTÁN OPTIMIZADAS O TERMINADAS, PERO LA IDEA ES QUE SEA UNA HERRAMIENTA COMPLETA PARA EJECUTAR ACCIONES Y SCRIPTS DESDE EL CEREBRO DE JARVIS.   
'''

def execute(action: dict):
    print("EXECUTOR RECEIVED:", action)

    if not action:
        print("No action received")
        return
    
    # TOOL SYSTEM

    tool_name = action.get("tool")

    if tool_name:
        params = action.get("params", {})
        tool = get_tool(tool_name)

        if not tool:
            print("Tool not found:", tool_name)
            return

        print("Running tool:", tool_name)
        tool(params)
        return


    # SCRIPTS

    if action.get("action") == "run_script":
        script_name = action.get("name")
        script = get_script(script_name)

        if not script:
            print("Script not found")
            return

        for step in script:
            execute(step)