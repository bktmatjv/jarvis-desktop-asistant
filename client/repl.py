"""
Terminal REPL module — JARVIS 2.5.
Manages a persistent, asynchronous shell session for executing system commands reliably with timeouts and process recovery.
"""
import asyncio
import os

class TerminalREPL:
    def __init__(self):
        self.process = None

    async def start(self):
        if os.name == 'nt':
            self.process = await asyncio.create_subprocess_exec(
                'powershell.exe',
                '-NoProfile',
                '-ExecutionPolicy', 'Bypass',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=os.path.expanduser("~")
            )
        else:
            self.process = await asyncio.create_subprocess_exec(
                '/bin/bash',
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                preexec_fn=os.setsid,
                cwd=os.path.expanduser("~")
            )
        print("Terminal REPL iniciada.")

    async def execute_command(self, cmd: str, timeout: float = 15.0) -> str:
        if not self.process or self.process.returncode is not None:
            await self.start()

        delimiter = "__JARVIS_CMD_DONE__"
        full_cmd = f"{cmd}\necho '{delimiter}'\n"

        try:
            self.process.stdin.write(full_cmd.encode('utf-8'))
            await self.process.stdin.drain()
        except Exception as e:
            # Re-spawn if pipe broken
            await self.start()
            self.process.stdin.write(full_cmd.encode('utf-8'))
            await self.process.stdin.drain()

        output = []

        async def _read_output():
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break
                decoded_line = line.decode('utf-8', errors='replace')
                if delimiter in decoded_line:
                    break
                output.append(decoded_line)

        try:
            await asyncio.wait_for(_read_output(), timeout=timeout)
        except asyncio.TimeoutError:
            output.append(f"\n[AVISO]: El comando superó el tiempo límite de espera ({timeout}s).")

        return "".join(output)

repl_instance = TerminalREPL()

