const input = document.getElementById('commandInput');
const statusText = document.getElementById('status');
const ring1 = document.getElementById('ring1');
const wrapper = document.getElementById('mainWrapper');
const jarvisResponse = document.getElementById('jarvisResponse');        


// --- 1. LÓGICA DEL VISUALIZADOR DE AUDIO ---
const vizContainer = document.getElementById('audioViz');
const numBars = 32;
let isProcessing = false;

for(let i=0; i<numBars; i++) {
    let bar = document.createElement('div');
    bar.className = 'viz-bar';
    bar.style.height = '4px';
    vizContainer.appendChild(bar);
}
const bars = document.querySelectorAll('.viz-bar');

function animateVisualizer() {
    bars.forEach(bar => {
        let baseHeight = isProcessing ? 10 : 3;
        let randomJump = isProcessing ? 30 : 6;
        let height = baseHeight + (Math.random() * randomJump);
        bar.style.height = `${height}px`;
    });
    setTimeout(() => requestAnimationFrame(animateVisualizer), 70);
}
animateVisualizer();

// --- 2. COMUNICACIÓN Y FUNCIONES ---
function updateStatus(text) {
    statusText.innerText = `[ ${text.toUpperCase()} ]`;
    statusText.style.color = "#00e5ff"; 
}

input.addEventListener('keydown', async function(e) {


    if (e.key === 'Enter') {
        const text = input.value.trim();
        
        if (text !== "") {
            if (window.pywebview) {
                // 1. Estado de "Pensando"
                statusText.innerText = "[ PROCESSING_COMMAND... ]";
                statusText.style.color = "#fff";
                ring1.style.animationDuration = "0.5s"; 
                isProcessing = true; 
                
                // Actualizamos la nueva pantalla
                jarvisResponse.innerText = "PROCESANDO CONSULTA...";
                jarvisResponse.classList.add("processing");
                
                input.value = ''; 
                
                // 2. Enviamos el comando a Python
                const result = await pywebview.api.send_command(text);
                
                // 3. Mostramos la respuesta del JSON/LLM en la pantalla
                jarvisResponse.innerText = result;
                jarvisResponse.classList.remove("processing");
                
                // Restauramos el estado
                statusText.innerText = `[ SYS_READY ]`;
                statusText.style.color = "#00ff00"; 
                ring1.style.animationDuration = "10s"; 
                isProcessing = false; 
            }
        }
    }
    
    if (e.key === 'Escape') {
        if (window.pywebview) {
            pywebview.api.hide_ui();
            resetHUD();
        }
    }
});

// --- 3. ANIMACIÓN DE ARRANQUE ---
window.addEventListener('focus', () => {
    input.focus();
    resetHUD();
    wrapper.classList.remove('boot-sequence');
    void wrapper.offsetWidth; 
    wrapper.classList.add('boot-sequence');
});

function resetHUD() {
    statusText.innerText = "[ AWAITING_INPUT ]";
    statusText.style.color = "#00e5ff";
    ring1.style.animationDuration = "10s";
    isProcessing = false;
}

// --- 4. RELOJ Y SENSORES ---
setInterval(() => {
    const now = new Date();
    document.getElementById('clock').innerText = now.toLocaleTimeString('es-ES', {hour: '2-digit', minute:'2-digit'});
}, 1000);

async function updateHUD() {
    if (window.pywebview) {
        try {
            const sysData = await pywebview.api.get_system_data();
            document.getElementById('greetingDisplay').innerText = sysData.greeting;
            const cpuText = document.getElementById('cpuData');
            cpuText.innerText = `CPU: ${sysData.cpu.toFixed(1)}% ${sysData.cpu > 80 ? "[CRITICAL]" : "[STABLE]"}`;
            cpuText.style.color = sysData.cpu > 80 ? "#ff3333" : "var(--jarvis-cyan)";
            document.getElementById('ramData').innerText = `RAM: ${sysData.ram_used} / ${sysData.ram_total} GB`;
            document.getElementById('ramFill').style.width = `${sysData.ram_percent}%`;
        } catch (err) {}
    }
}

window.addEventListener('pywebviewready', function() {
    updateHUD(); 
    setInterval(updateHUD, 2000); 
});

// --- 5. MINI CONSOLA ---
function addLog(message) {
    const consoleBox = document.getElementById('miniConsole');
    const newLog = document.createElement('div');
    const time = new Date().toLocaleTimeString('es-ES', {hour: '2-digit', minute:'2-digit', second:'2-digit'});
    
    if(message.includes("❌") || message.includes("error") || message.includes("ERROR")) {
        newLog.style.color = "#ff3333";
    } else if (message.includes("✅") || message.includes("Done") || message.includes("COMPLETADA")) {
        newLog.style.color = "#00ff00";
    }
    
    newLog.innerText = `[${time}] ${message}`;
    consoleBox.appendChild(newLog);
    consoleBox.scrollTop = consoleBox.scrollHeight;
}

// --- 6. SEGURIDAD (DUMB CLIENT) ---
function showSecurityAlert(commandStr) {
    const modal = document.getElementById('securityModal');
    const cmdEl = document.getElementById('securityCommand');
    
    cmdEl.innerText = commandStr;
    modal.style.display = 'flex';
    
    // Pause auto-hide or focus issues if any
    input.blur();
}

function confirmSecurity(isAllowed) {
    const modal = document.getElementById('securityModal');
    modal.style.display = 'none';
    
    input.focus();
    
    if (window.pywebview) {
        window.pywebview.api.security_response(isAllowed);
    }
}

function updateJarvisResponse(text) {
    const jarvisResponse = document.getElementById('jarvisResponse');
    const actionDisplay = document.getElementById('actionDisplay');
    const actionHeader = document.getElementById('actionHeader');
    const actionText = document.getElementById('actionText');
    const outputDisplay = document.getElementById('outputDisplay');
    const statusText = document.getElementById('status');
    const ring1 = document.getElementById('ring1');
    const ring2 = document.querySelector('.reactor-ring-2');
    
    // Devolvemos la caja derecha a estado inactivo (Standby)
    actionDisplay.classList.remove('active');
    actionHeader.innerText = '[ STANDBY ]';
    actionText.innerText = '>_ WAITING FOR PROCESS...';
    outputDisplay.style.opacity = '0.2';
    
    jarvisResponse.innerText = text;
    jarvisResponse.classList.remove("processing");
    
    // Restauramos el estado
    statusText.innerText = `[ SYS_READY ]`;
    statusText.style.color = "#00ff00"; 
    ring1.style.animationDuration = "10s"; 
    ring2.style.borderColor = "#fff";
    isProcessing = false; 
}

let typeWriterTimeout = null;

function showSystemAction(commandText) {
    const actionDisplay = document.getElementById('actionDisplay');
    const actionHeader = document.getElementById('actionHeader');
    const actionText = document.getElementById('actionText');
    const outputDisplay = document.getElementById('outputDisplay');
    const statusText = document.getElementById('status');
    const ring1 = document.getElementById('ring1');
    const ring2 = document.querySelector('.reactor-ring-2');
    
    // Activamos agresivamente la columna derecha
    actionDisplay.classList.add('active');
    actionHeader.innerText = '[ SYSTEM.OVERRIDE ]';
    outputDisplay.style.opacity = '0.2'; // Opacamos el output viejo si lo hubiera
    
    // UI super agresiva
    statusText.innerText = `[ EXECUTING_SUBROUTINE ]`;
    statusText.style.color = "#ff003c";
    ring1.style.animationDuration = "0.2s"; 
    ring2.style.borderColor = "#ff003c";
    
    // Efecto Typewriter
    actionText.innerText = ">_ ";
    let i = 0;
    const fullText = ">_ " + commandText;
    
    if (typeWriterTimeout) clearTimeout(typeWriterTimeout);
    
    function type() {
        if (i < fullText.length) {
            actionText.innerText = fullText.substring(0, i+1);
            i++;
            typeWriterTimeout = setTimeout(type, 15);
        }
    }
    type();
}

function showCommandOutput(outputText) {
    const outputDisplay = document.getElementById('outputDisplay');
    const outputTextEl = document.getElementById('outputText');
    const statusText = document.getElementById('status');
    const ring1 = document.getElementById('ring1');
    const ring2 = document.querySelector('.reactor-ring-2');
    
    outputDisplay.style.opacity = '1';
    outputTextEl.innerText = outputText;
    
    // Cambiar estado a verde/procesado
    statusText.innerText = `[ COMMAND_EXECUTED ]`;
    statusText.style.color = "#00ff00";
    ring1.style.animationDuration = "5s"; 
    ring2.style.borderColor = "#00ff00";
}
