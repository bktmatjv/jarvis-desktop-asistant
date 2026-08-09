"""
Terminal REPL module.
Manages a continuous asynchronous bash session for executing system commands reliably.
"""
import asyncio
import os

class TerminalREPL:
    def __init__(self):
        self.process = None

    async def start(self):
        self.process = await asyncio.create_subprocess_exec(
            '/bin/bash',
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            preexec_fn=os.setsid,
            cwd=os.path.expanduser("~")
        )
        print("🖥️  Terminal REPL iniciada.")

    async def execute_command(self, cmd: str) -> str:
        if not self.process:
            await self.start()
        
        delimiter = "__JARVIS_CMD_DONE__"
        full_cmd = f"{cmd}\necho '{delimiter}'\n"
        
        self.process.stdin.write(full_cmd.encode('utf-8'))
        await self.process.stdin.drain()
        
        output = []
        while True:
            line = await self.process.stdout.readline()
            if not line:
                break
            decoded_line = line.decode('utf-8', errors='replace')
            if delimiter in decoded_line:
                break
            output.append(decoded_line)
            
        return "".join(output)

repl_instance = TerminalREPL()
