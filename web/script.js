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
