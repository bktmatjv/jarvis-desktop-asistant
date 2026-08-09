import subprocess
import time
from pywinauto import Desktop

def automate_program(params):
    # Jarvis extraerá estos parámetros de tu orden
    executable = params.get("executable", "notepad.exe")
    window_title = params.get("window_title", ".*Bloc de notas|.*Notepad")
    text_to_type = params.get("text", "")

    print(f"⚙️ Jarvis intentando abrir y controlar: {executable}...")

    try:
        # Abre el programa
        subprocess.Popen(executable)
        time.sleep(2)  # Pausa para que el OS renderice la ventana

        # Busca la ventana en el escritorio
        escritorio = Desktop(backend="uia")
        ventana = escritorio.window(title_re=window_title, visible_only=True, found_index=0)
        
        # Trae la ventana al frente
        ventana.set_focus()

        # 4. Si Jarvis tiene algo que escribir, lo inyecta
        if text_to_type:
            print("✍️ Jarvis está escribiendo en el sistema...")
            
            # Reemplazamos los espacios normales por la pulsación de tecla {SPACE}
            texto_seguro = text_to_type.replace(" ", "{SPACE}")
            texto_seguro += "{ENTER}"  # Presionamos Enter al final del texto
            print(texto_seguro)

            # Enviamos el texto seguro
            ventana.type_keys(texto_seguro)
        print("✅ Acción de sistema operativo completada.")

    except Exception as e:
        print(f"ERROR:  Error al intentar controlar el sistema: {e}")