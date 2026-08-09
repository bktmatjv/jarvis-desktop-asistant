from tools.window_tool import list_windows, focus_window, minimize_window, maximize_window, close_window
from tools.system_tool import open_program, shutdown_system, restart_system, sleep_system, lock_system, control_volume
from tools.system_info_tool import (
    get_system_time, 
    get_battery_info, 
    get_cpu_usage, 
    get_memory_usage, 
    list_running_programs, 
    take_screenshot
)
from tools.input_tool import keyboard_type, keyboard_shortcut, mouse_move, mouse_click, mouse_scroll

'''
    Documentación:
    - Registro centralizado de herramientas para el "Dumb Client".
'''

TOOLS = {
    # window management tools
    "window.list": list_windows,
    "window.focus": focus_window,
    "window.minimize": minimize_window,
    "window.maximize": maximize_window,
    "window.close": close_window,

    # SYSTEM CONTROL
    "system.open_program": open_program,
    "system.shutdown": shutdown_system,
    "system.restart": restart_system,
    "system.sleep": sleep_system,
    "system.lock": lock_system,
    "system.volume": control_volume,

    # SYSTEM INFORMATION
    "system.time": get_system_time,
    "system.battery": get_battery_info,
    "system.cpu_usage": get_cpu_usage,
    "system.memory_usage": get_memory_usage,
    "system.running_programs": list_running_programs,
    "system.screenshot": take_screenshot,

    # KEYBOARD & MOUSE
    "keyboard.type": keyboard_type,
    "keyboard.shortcut": keyboard_shortcut,
    "mouse.move": mouse_move,
    "mouse.click": mouse_click,
    "mouse.scroll": mouse_scroll
}

def get_tool(name):
    return TOOLS.get(name)