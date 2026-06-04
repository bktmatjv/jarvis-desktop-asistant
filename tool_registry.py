from tools.system_tool import open_program
from tools.filesystem_tool import create_folder
from tools.command_tool import run_command
from tools.browser_tool import open_url
from tools.os_automation_tool import automate_program
from tools.window_tool import list_windows, focus_window, minimize_window, maximize_window, close_window
from tools.system_tool import open_program, shutdown_system, restart_system, sleep_system, lock_system, control_volume
from tools.filesystem_tool import create_folder, create_file, write_file, read_file, delete_path, list_directory
from tools.browser_tool import open_url, open_tab, search_google
from tools.system_info_tool import (
    get_system_time, 
    get_battery_info, 
    get_cpu_usage, 
    get_memory_usage, 
    list_running_programs, 
    take_screenshot
)
from tools.media_tool import play_youtube_music, global_music_play, global_music_pause, global_music_next, global_music_previous
from tools.input_tool import keyboard_type, keyboard_shortcut, mouse_move, mouse_click, mouse_scroll

'''
    Documentación:
    - Este módulo actúa como un registro centralizado de todas las herramientas disponibles para Jarvis.
    - Cada herramienta se importa desde su respectivo módulo y se asigna a una clave única en el diccionario TOOLS.
    - La función get_tool(name) permite recuperar una herramienta específica por su nombre, facilitando su uso en el cerebro de Jarvis o en cualquier otra parte del sistema.   

'''


TOOLS = {


    "browser.open_url": open_url,
    "os.automate_program": automate_program,

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

    # FILESYSTEM
    "filesystem.create_folder": create_folder,
    "filesystem.create_file": create_file,
    "filesystem.write": write_file,
    "filesystem.read": read_file,
    "filesystem.delete": delete_path,
    "filesystem.list": list_directory,

    # BROWSER
    "browser.open_url": open_url,
    "browser.open_tab": open_tab,
    "browser.search": search_google,

    # SYSTEM INFORMATION
    "system.time": get_system_time,
    "system.battery": get_battery_info,
    "system.cpu_usage": get_cpu_usage,
    "system.memory_usage": get_memory_usage,
    "system.running_programs": list_running_programs,
    "system.screenshot": take_screenshot,

    # MEDIA
    "youtube.play_song": play_youtube_music,
    "music.play": global_music_play,
    "music.pause": global_music_pause,
    "music.next": global_music_next,
    "music.previous": global_music_previous,

    # KEYBOARD & MOUSE
    "keyboard.type": keyboard_type,
    "keyboard.shortcut": keyboard_shortcut,
    "mouse.move": mouse_move,
    "mouse.click": mouse_click,
    "mouse.scroll": mouse_scroll

}


def get_tool(name):
    return TOOLS.get(name)