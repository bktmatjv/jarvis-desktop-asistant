const input = document.getElementById('commandInput');
const statusText = document.getElementById('status');

// --- 0. CINEMATIC BOOT SEQUENCE ---
// The visual animation is handled by animation/jarvisActivation.js (ES Module).
// That module calls runJarvisActivation() automatically on DOMContentLoaded,
// then fires onActivationComplete() below when it's done.
//
// We expose the callback via window so the module can call it across the
// module/non-module script boundary.
window.onActivationComplete = function () {
    // Clock, audio visualizer, and other panel logic start AFTER animation
    startClock();
    startAudioVisualizer();
    loadSystemData();
};


// --- 0.1 HEADER CONTROLS ---
function toggleBtn(btn) {
    btn.classList.toggle('active');
}

function winMin() {
    if (window.pywebview) window.pywebview.api.minimize_window();
}

function winMax() {
    if (window.pywebview) window.pywebview.api.maximize_window();
}

function winClose() {
    if (window.pywebview) window.pywebview.api.close_window();
}


// --- 1. LÓGICA DEL VISUALIZADOR DE AUDIO ---
const vizContainer = document.getElementById('audioViz');
const numBars = 40;
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

// Wrapped so the animation can start it post-activation
function startAudioVisualizer() {
    animateVisualizer();
}

// --- 2. COMUNICACIÓN Y FUNCIONES (CHAT DINAMICO) ---
const chatHistory = document.getElementById('chatHistory');

function formatMarkdown(text) {
    if (!text) return "";
    let html = text.replace(/\*\*(.*?)\*\*/g, '<b style="color: var(--jarvis-cyan);">$1</b>');
    html = html.replace(/\*(.*?)\*/g, '<i>$1</i>');
    html = html.replace(/`(.*?)`/g, '<code style="background: rgba(0,229,255,0.2); padding: 2px 4px; border-radius: 3px;">$1</code>');
    // Convert newlines to br for bubbles
    html = html.replace(/\n/g, '<br>');
    return html;
}

function addChatMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}`;
    
    const timeText = new Date().toLocaleTimeString('es-ES', {hour: '2-digit', minute:'2-digit', second:'2-digit'});
    
    let innerHTML = '';
    if (sender === 'jarvis') {
        innerHTML += `<div class="sender">JARVIS</div>`;
    }
    innerHTML += `<div class="bubble">${sender === 'jarvis' ? formatMarkdown(text) : text}</div>`;
    innerHTML += `<div class="time">${timeText}</div>`;
    
    msgDiv.innerHTML = innerHTML;
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Escuchamos el Enter en el chat
input.addEventListener('keydown', async function(e) {
    if (e.key === 'Enter') {
        const text = input.value.trim();
        
        if (text !== "") {
            addChatMessage(text, 'user');
            
            if (window.pywebview) {
                // Estado Pensando
                statusText.innerText = "[ PROCESSING... ]";
                statusText.style.color = "#fff";
                const core = document.getElementById('brainCoreSVG');
                if (core) core.style.animationDuration = '0.5s';
                isProcessing = true; 
                input.value = ''; 

                // Notificar inicio de ciclo al visualizador del Loop Engineering
                if (window.updateLoopProcess) {
                    window.updateLoopProcess({
                        step: 'ingestion',
                        status: 'active',
                        detail: `Prompt: "${text.substring(0, 32)}..."`
                    });
                }
                
                // Enviamos el comando a Python (la respuesta real llega vía WebSocket a updateJarvisResponse)
                await pywebview.api.send_command(text);
            } else {
                // MOCK para navegador
                if (window.simulateLoopCycle) {
                    window.simulateLoopCycle(text);
                }
                setTimeout(() => {
                    addChatMessage("Esta es una respuesta simulada del sistema porque no estás ejecutando en Python.", 'jarvis');
                    resetHUD();
                }, 1200);
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

// --- 3. ANIMACIÓN DE ARRANQUE / WAKE ---
function resetHUD() {
    statusText.innerText = "[ JARVIS ONLINE ]";
    statusText.style.color = "var(--jarvis-green)";
    // brainCoreSVG replaces the old brainCore3D
    const core = document.getElementById('brainCoreSVG');
    if (core) core.style.animationDuration = '2s';
    isProcessing = false;
    document.body.style.opacity = "1";
    document.body.style.filter = "none";
}

function sleepUI() {
    statusText.innerText = "[ SLEEPING_MODE ]";
    statusText.style.color = "#444";
    const core = document.getElementById('brainCoreSVG');
    if (core) core.style.animationDuration = '6s';
    document.body.style.opacity = "0.7";
    document.body.style.filter = "grayscale(50%) brightness(0.6)";
}

function wakeUpUI() {
    document.body.style.opacity = "1";
    document.body.style.filter = "none";
    resetHUD();
    input.focus();
}

function listeningUI() {
    statusText.innerText = "[ LISTENING_VOICE... ]";
    statusText.style.color = "var(--jarvis-cyan)";
    const core = document.getElementById('brainCoreSVG');
    if (core) core.style.animationDuration = '0.1s'; 
}

// --- 4. RELOJ Y SENSORES ---
let clockInterval = null;

function startClock() {
    if (clockInterval) return; // Prevent double start
    clockInterval = setInterval(() => {
        const now = new Date();
        document.getElementById('clock-time').innerText = now.toLocaleTimeString('es-ES', {hour: '2-digit', minute:'2-digit', second:'2-digit'});
        const options = { day: '2-digit', month: 'short', year: 'numeric' };
        document.getElementById('clock-date').innerText = now.toLocaleDateString('en-GB', options).toUpperCase();
    }, 1000);
}

function loadSystemData() {
    // Initial data load + recurring update
    updateHUD();
    setInterval(updateHUD, 2000);
}

async function updateHUD() {
    if (window.pywebview) {
        try {
            const sysData = await pywebview.api.get_system_data();
            
            const cpuText = document.getElementById('cpuData');
            const cpuRing = document.getElementById('cpu-ring');
            cpuText.innerText = `${sysData.cpu.toFixed(0)}%`;
            cpuRing.style.strokeDasharray = `${sysData.cpu.toFixed(0)}, 100`;
            // Flash animation on value update
            cpuText.classList.remove('updated');
            void cpuText.offsetWidth; // reflow to restart animation
            cpuText.classList.add('updated');
            
            const ramPercent = sysData.ram_percent.toFixed(0);
            const ramText = document.getElementById('ramData');
            ramText.innerText = `${ramPercent}%`;
            document.getElementById('ram-ring').style.strokeDasharray = `${ramPercent}, 100`;
            ramText.classList.remove('updated');
            void ramText.offsetWidth;
            ramText.classList.add('updated');

            // Populate user identity fields dynamically (no hardcoded personal data)
            if (sysData.username) {
                const unEl = document.getElementById('user-name');
                const urEl = document.getElementById('user-role');
                const dnEl = document.getElementById('device-name');
                if (unEl) unEl.innerText = sysData.username;
                if (urEl) urEl.innerText = (sysData.role || 'USUARIO').toUpperCase();
                if (dnEl) dnEl.innerText = sysData.device_name || 'JARVIS-HOST';
            }
            
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
    newLog.className = 'log-line';
    const time = new Date().toLocaleTimeString('es-ES', {hour: '2-digit', minute:'2-digit', second:'2-digit'});
    
    let tag = '<span class="tag cyan">[INFO]</span>';
    if(message.includes("error") || message.includes("ERROR") || message.includes("[DENEGADA]")) {
        tag = '<span class="tag red">[ERROR]</span>';
    } else if (message.includes("[PERMITIDA]") || message.includes("Done") || message.includes("SUCCESS")) {
        tag = '<span class="tag green">[SUCCESS]</span>';
    } else if (message.includes("warn") || message.includes("WARN")) {
        tag = '<span class="tag orange">[WARN]</span>';
    }
    
    newLog.innerHTML = `<span class="time">${time}</span> ${tag} ${message}`;
    consoleBox.appendChild(newLog);
    consoleBox.scrollTop = consoleBox.scrollHeight;
}

// --- 6. SEGURIDAD ---
function showSecurityAlert(commandStr) {
    const modal = document.getElementById('securityModal');
    const cmdEl = document.getElementById('securityCommand');
    
    cmdEl.innerText = commandStr;
    modal.style.display = 'block'; 
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
    addChatMessage(text, 'jarvis');
    resetHUD();
    if (window.updateLoopProcess) {
        window.updateLoopProcess({
            step: 'idle',
            status: 'idle',
            detail: 'Respuesta completada y transmitida.'
        });
    }
}

let typeWriterTimeout = null;

function showSystemAction(commandText) {
    const actionDisplay = document.getElementById('actionDisplay');
    const outputDisplay = document.getElementById('outputDisplay');
    
    outputDisplay.style.opacity = '0.2'; 
    
    actionDisplay.innerText = ">_ ";
    let i = 0;
    const fullText = ">_ " + commandText;
    
    if (typeWriterTimeout) clearTimeout(typeWriterTimeout);
    
    function type() {
        if (i < fullText.length) {
            actionDisplay.innerText = fullText.substring(0, i+1);
            i++;
            typeWriterTimeout = setTimeout(type, 15);
        }
    }
    type();

    if (window.updateLoopProcess) {
        window.updateLoopProcess({
            step: 'skill_runner',
            status: 'active',
            skill: commandText,
            detail: `Ejecutando: ${commandText.substring(0, 30)}...`
        });
    }
}

function showCommandOutput(outputText) {
    const outputDisplay = document.getElementById('outputDisplay');
    outputDisplay.style.opacity = '1';
    outputDisplay.innerText = outputText;

    if (window.updateLoopProcess) {
        window.updateLoopProcess({
            step: 'skill_runner',
            status: 'completed',
            detail: 'Salida de proceso capturada con éxito.'
        });
    }
}

// --- 7. PLANNER AI ---
function createTaskPlan(title, steps) {
    const plannerTitle = document.getElementById('plannerTitle');
    const plannerSteps = document.getElementById('plannerSteps');
    
    plannerTitle.innerText = `TASK PLANNER - ${title.toUpperCase()}`;
    plannerSteps.innerHTML = '';
    
    steps.forEach((step, index) => {
        const stepDiv = document.createElement('div');
        stepDiv.className = 'task-item'; // Default color cyan
        stepDiv.id = `task-step-${index}`;
        stepDiv.innerHTML = `[-] ${step}`;
        plannerSteps.appendChild(stepDiv);
    });
}

function updateTaskStep(index, status) {
    const stepDiv = document.getElementById(`task-step-${index}`);
    
    if (stepDiv) {
        let text = stepDiv.innerText.substring(4); // Remove prefix
        if (status === 'in_progress') {
            stepDiv.className = `task-item cyan`;
            stepDiv.innerText = `[~] ${text}`;
        } else if (status === 'completed') {
            stepDiv.className = `task-item green`;
            stepDiv.innerText = `[X] ${text}`;
        } else if (status === 'failed') {
            stepDiv.className = `task-item red`;
            stepDiv.innerText = `[!] ${text}`;
        }
    }
}

// --- 8. ADMIN DASHBOARD ---
function toggleAdminDashboard() {
    const modal = document.getElementById('adminDashboard');
    if (modal.style.display === 'none' || modal.style.display === '') {
        modal.style.display = 'block';
    } else {
        modal.style.display = 'none';
    }
}

// --- 9. SYSTEM STATUS UPDATE ---
function updateSystemStatus(payload) {
    if (!payload) return;
    
    // Log interno en consola del navegador
    console.log("Estado del sistema actualizado:", payload);
    
    // Mostrar en la consola del HUD holográfico si incluye un mensaje general
    if (payload.message) {
        addLog(`[SYSTEM UPDATE] ${payload.message}`);
    }
    
    // (Opcional) Si el servidor envía métricas específicas, aquí se actualizaría el DOM
    // Ejemplo hipotético:
    // if(payload.network_status) updateNetwork(payload.network_status);
}
