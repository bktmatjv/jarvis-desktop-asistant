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

function formatMarkdown(text) {
    if (!text) return "";
    let html = text.replace(/\*\*(.*?)\*\*/g, '<b style="color: #00e5ff;">$1</b>');
    html = html.replace(/\*(.*?)\*/g, '<i>$1</i>');
    html = html.replace(/`(.*?)`/g, '<code style="background: rgba(0,229,255,0.2); padding: 2px 4px; border-radius: 3px;">$1</code>');
    return html;
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
                jarvisResponse.innerHTML = formatMarkdown(result);
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
    document.body.style.opacity = "1";
    document.body.style.filter = "none";
}

function sleepUI() {
    statusText.innerText = "[ SLEEPING_MODE ]";
    statusText.style.color = "#444";
    ring1.style.animationDuration = "30s";
    jarvisResponse.innerText = "SISTEMA EN ESPERA... DIGA 'JARVIS' PARA INVOCAR";
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
    statusText.style.color = "#ff00ff";
    ring1.style.animationDuration = "0.2s"; 
    jarvisResponse.innerText = "ESCUCHANDO...";
    jarvisResponse.classList.add("processing");
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
    
    if(message.includes("[ALERTA]") || message.includes("error") || message.includes("ERROR") || message.includes("[DENEGADA]")) {
        newLog.style.color = "#ff3333";
    } else if (message.includes("[PERMITIDA]") || message.includes("Done") || message.includes("COMPLETADA") || message.includes("SUCCESS")) {
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
    
    actionDisplay.classList.remove('active');
    actionHeader.innerText = '[ STANDBY ]';
    actionText.innerText = '>_ WAITING FOR PROCESS...';
    outputDisplay.style.opacity = '0.2';
    
    jarvisResponse.innerHTML = formatMarkdown(text);
    jarvisResponse.classList.remove("processing");
    
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
    
    actionDisplay.classList.add('active');
    actionHeader.innerText = '[ SYSTEM.OVERRIDE ]';
    outputDisplay.style.opacity = '0.2'; 
    
    statusText.innerText = `[ EXECUTING_SUBROUTINE ]`;
    statusText.style.color = "#ff003c";
    ring1.style.animationDuration = "0.2s"; 
    ring2.style.borderColor = "#ff003c";
    
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
    
    statusText.innerText = `[ COMMAND_EXECUTED ]`;
    statusText.style.color = "#00ff00";
    ring1.style.animationDuration = "5s"; 
    ring2.style.borderColor = "#00ff00";
}

// --- 7. PLANNER AI ---
let currentPlanSteps = [];

function createTaskPlan(title, steps) {
    const plannerDisplay = document.getElementById('plannerDisplay');
    const plannerTitle = document.getElementById('plannerTitle');
    const plannerSteps = document.getElementById('plannerSteps');
    
    plannerTitle.innerText = `[ PLAN ] ${title.toUpperCase()}`;
    plannerSteps.innerHTML = '';
    currentPlanSteps = steps;
    
    steps.forEach((step, index) => {
        const stepDiv = document.createElement('div');
        stepDiv.className = 'task-step';
        stepDiv.id = `task-step-${index}`;
        
        stepDiv.innerHTML = `
            <span class="task-icon" id="task-icon-${index}">[ ]</span>
            <span class="task-text">${step}</span>
        `;
        
        plannerSteps.appendChild(stepDiv);
    });
    
    plannerDisplay.style.display = 'block';
}

function updateTaskStep(index, status) {
    const stepDiv = document.getElementById(`task-step-${index}`);
    const iconSpan = document.getElementById(`task-icon-${index}`);
    
    if (stepDiv && iconSpan) {
        stepDiv.className = `task-step ${status}`;
        if (status === 'in_progress') {
            iconSpan.innerText = '[~]';
        } else if (status === 'completed') {
            iconSpan.innerText = '[X]';
        } else if (status === 'failed') {
            iconSpan.innerText = '[!]';
        }
    }
}

// --- 8. ADMIN DASHBOARD & SYSTEM STATUS ---
function toggleAdminDashboard() {
    const modal = document.getElementById('adminDashboard');
    if (modal.style.display === 'none' || modal.style.display === '') {
        modal.style.display = 'flex';
    } else {
        modal.style.display = 'none';
    }
}

function updateSystemStatus(payload) {
    const serversList = document.getElementById('dynamicServersList');
    if (serversList) {
        serversList.innerHTML = '';
        if (payload.total_clients > 0) {
            let totalDevices = 0;
            payload.users.forEach(user => {
                totalDevices += user.devices.length;
            });
            
            serversList.innerHTML += `<div class="server-status"><span class="server-icon"></span> Usuarios Activos: <span class="status-ok">${payload.users.length}</span></div>`;
            serversList.innerHTML += `<div class="server-status"><span class="server-icon">️</span> Dispositivos: <span class="status-ok">${totalDevices}</span></div>`;
            serversList.innerHTML += `<div class="server-status"><span class="server-icon">⏱️</span> Backend: <span class="status-ok">ONLINE</span></div>`;
        } else {
            serversList.innerHTML = `<div class="server-status"><span class="server-icon">️</span> Sin clientes conectados.</div>`;
        }
    }

    const adminTotal = document.getElementById('adminTotalNodes');
    const adminList = document.getElementById('adminClientsList');
    
    if (adminTotal && adminList) {
        adminTotal.innerText = payload.total_clients;
        adminList.innerHTML = '';
        
        payload.users.forEach(user => {
            let html = `<div class="admin-user-card">
                            <div class="admin-user-title">
                                <span> ${user.username}</span>
                                <span style="font-size: 10px; color: ${user.role === 'admin' ? '#ffaa00' : '#00e5ff'};">[${user.role.toUpperCase()}]</span>
                            </div>`;
            
            user.devices.forEach(dev => {
                html += `<div class="admin-device-item">
                            <span> ${dev.device_name} (${dev.os.toUpperCase()})</span>
                            <span style="color: #00ff00;">ONLINE</span>
                         </div>`;
            });
            html += `</div>`;
            adminList.innerHTML += html;
        });
    }
}
