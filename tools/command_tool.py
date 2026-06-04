import os

# en desarrollo aun, no lo estoy usando en ningún lado, pero la idea es que sea una herramienta genérica para ejecutar comandos del sistema operativo, así no tengo que crear una función específica cada vez que quiera ejecutar algo nuevo, sino que puedo simplemente enviar el comando como texto desde el cerebro y esta herramienta se encarga de ejecutarlo.

def run_command(params):
    command = params.get("command")

    if not command:
        print("No command")
        return

    print("Running:", command)

    os.system(command)