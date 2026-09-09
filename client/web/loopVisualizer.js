/**
 * loopVisualizer.js — JARVIS 2.5 Circular High-Tech HUD Loop Engineering Visualizer.
 * Inspired by futuristic circular arc reactor HUD dials (Image 1) and the exact
 * 8-node branched pipeline graph of Loop Engineering (Image 2):
 * 
 *   [ENTRADA] ➔ [01. FAST ROUTER]
 *                     ├──> [02A. FAST STREAM] ──────────────────────────┐
 *                     │                                                 ▼
 *                     └──> [02B. PRUNER] ➔ [03. REASONING] ➔ [04. SKILL] ➔ [05. FORMATTER] ➔ [SALIDA TTS]
 */

(function () {
    let currentStep = "idle";
    let cycleStartTime = 0;
    let cycleTimer = null;
    let isSimulationRunning = false;

    // Node definitions according to Image 2
    const NODES = {
        input: {
            id: "node_input",
            num: "ENTRADA",
            title: "VOZ O TEXTO",
            sub: "Mic STT / CLI",
            x: 60, y: 110,
            icon: `<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>`,
            accentColor: "#00e5ff"
        },
        router: {
            id: "node_router",
            num: "NODO 1",
            title: "FAST ROUTER",
            sub: "compound-mini",
            x: 185, y: 110,
            icon: `<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>`,
            accentColor: "#ffb700"
        },
        fast_stream: {
            id: "node_fast_stream",
            num: "NODO 2A",
            title: "FAST STREAM",
            sub: "Conversación",
            x: 460, y: 48,
            icon: `<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>`,
            accentColor: "#00e5ff"
        },
        pruner: {
            id: "node_pruner",
            num: "NODO 2B",
            title: "CONTEXT PRUNER",
            sub: "-84% Tokens",
            x: 310, y: 168,
            icon: `<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><line x1="20" y1="4" x2="8.12" y2="15.88"/><line x1="14.47" y1="14.48" x2="20" y2="20"/><line x1="8.12" y1="8.12" x2="12" y2="12"/>`,
            accentColor: "#ffb700"
        },
        reasoning: {
            id: "node_reasoning",
            num: "NODO 3",
            title: "REASONING",
            sub: "qwen3.6-27b",
            x: 450, y: 168,
            icon: `<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/>`,
            accentColor: "#00e5ff"
        },
        skill_runner: {
            id: "node_skill_runner",
            num: "NODO 4",
            title: "SKILL RUNNER",
            sub: "client/skills/",
            x: 590, y: 168,
            icon: `<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>`,
            accentColor: "#ffb700"
        },
        formatter: {
            id: "node_formatter",
            num: "NODO 5",
            title: "FORMATTER",
            sub: "Executive Resp",
            x: 730, y: 168,
            icon: `<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>`,
            accentColor: "#00e5ff"
        },
        output: {
            id: "node_output",
            num: "SALIDA",
            title: "TTS + HUD",
            sub: "pyttsx3 Audio",
            x: 865, y: 110,
            icon: `<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>`,
            accentColor: "#00ff66"
        }
    };

    /**
     * Builds the complete futuristic SVG graph with circular reactor nodes and circuit traces
     */
    function renderGraphSVG() {
        const container = document.getElementById("loopGraphView");
        if (!container) return;

        container.innerHTML = `
            <svg class="loop-hud-svg" id="loopSvgGraph" viewBox="0 0 940 220" preserveAspectRatio="xMidYMid meet">
                <defs>
                    <!-- Filters -->
                    <filter id="glowCyan" x="-30%" y="-30%" width="160%" height="160%">
                        <feGaussianBlur stdDeviation="3.5" result="blur"/>
                        <feMerge>
                            <feMergeNode in="blur"/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                    <filter id="glowAmber" x="-30%" y="-30%" width="160%" height="160%">
                        <feGaussianBlur stdDeviation="3.5" result="blur"/>
                        <feMerge>
                            <feMergeNode in="blur"/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                    <filter id="glowGreen" x="-30%" y="-30%" width="160%" height="160%">
                        <feGaussianBlur stdDeviation="3.5" result="blur"/>
                        <feMerge>
                            <feMergeNode in="blur"/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>

                    <!-- Gradients -->
                    <linearGradient id="wireGradCyan" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stop-color="#00e5ff" stop-opacity="0.3"/>
                        <stop offset="50%" stop-color="#00e5ff" stop-opacity="1"/>
                        <stop offset="100%" stop-color="#00e5ff" stop-opacity="0.3"/>
                    </linearGradient>
                    <linearGradient id="wireGradAmber" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stop-color="#ffb700" stop-opacity="0.3"/>
                        <stop offset="50%" stop-color="#ffb700" stop-opacity="1"/>
                        <stop offset="100%" stop-color="#ffb700" stop-opacity="0.3"/>
                    </linearGradient>
                </defs>

                <!-- 1. CIRCUIT WIRES LAYER -->
                <g id="circuitTracks" class="circuit-tracks">
                    <!-- Input -> Router -->
                    <path id="wire-input-router" class="c-wire" d="M 88 110 L 157 110" />

                    <!-- Router -> Top Branch (Fast Stream) -->
                    <path id="wire-router-faststream" class="c-wire" d="M 213 110 C 260 110, 320 48, 432 48" />
                    <!-- Fast Stream -> Output -->
                    <path id="wire-faststream-output" class="c-wire" d="M 488 48 C 620 48, 790 110, 837 110" />

                    <!-- Router -> Bottom Branch (Pruner) -->
                    <path id="wire-router-pruner" class="c-wire" d="M 213 110 C 240 110, 260 168, 282 168" />
                    <!-- Pruner -> Reasoning -->
                    <path id="wire-pruner-reasoning" class="c-wire" d="M 338 168 L 422 168" />
                    <!-- Reasoning -> Skill -->
                    <path id="wire-reasoning-skill" class="c-wire" d="M 478 168 L 562 168" />
                    <!-- Skill -> Formatter -->
                    <path id="wire-skill-formatter" class="c-wire" d="M 618 168 L 702 168" />
                    <!-- Formatter -> Output -->
                    <path id="wire-formatter-output" class="c-wire" d="M 758 168 C 795 168, 825 110, 837 110" />

                    <!-- Circuit Junction Solder Pads -->
                    <circle class="solder-pad" cx="88" cy="110" r="2.5" />
                    <circle class="solder-pad" cx="157" cy="110" r="2.5" />
                    <circle class="solder-pad" cx="213" cy="110" r="2.5" />
                    <circle class="solder-pad" cx="282" cy="168" r="2.5" />
                    <circle class="solder-pad" cx="432" cy="48" r="2.5" />
                    <circle class="solder-pad" cx="837" cy="110" r="2.5" />
                </g>

                <!-- 2. CIRCULAR HUD NODES LAYER -->
                <g id="hudNodesGroup">
                    ${Object.keys(NODES).map(key => createCircularDialNode(NODES[key])).join('')}
                </g>
            </svg>

            <!-- 3. LIVE TELEMETRY TICKER AT BOTTOM -->
            <div class="loop-telemetry-strip">
                <div class="lt-item"><span class="lt-tag">[FASE ACTIVA]</span> <span class="lt-text" id="tActivePhase">STANDBY // MONITOREANDO</span></div>
                <div class="lt-item"><span class="lt-tag">[DETALLE]</span> <span class="lt-text" id="tProcessDetail">Esperando comando de voz o teclado</span></div>
                <div class="lt-item"><span class="lt-tag">[LATENCIA]</span> <span class="lt-text" id="tCycleLatency">-- ms</span></div>
                <div class="lt-item"><span class="lt-tag">[POOL GROQ]</span> <span class="lt-text green">OPERATIVO (3 KEYS)</span></div>
            </div>
        `;
    }

    /**
     * Generates the SVG template for an intricate sci-fi circular dial reactor (Image 1 style)
     */
    function createCircularDialNode(node) {
        const { id, num, title, sub, x, y, icon, accentColor } = node;
        const R_OUTER = 26;
        const R_MID = 21;
        const R_INNER = 16;
        const R_CORE = 13;

        return `
            <g class="hud-dial state-idle" id="${id}" transform="translate(${x}, ${y})" style="--accent: ${accentColor};">
                <!-- Background Ambient Glow -->
                <circle class="dial-halo" r="${R_OUTER + 2}" />

                <!-- Sonar Pulse Ring (Active) -->
                <circle class="dial-sonar-wave" r="${R_OUTER}" />

                <!-- 1. Outer Segmented Tick Ring (Rotates CW) -->
                <circle class="dial-rot-cw dial-outer-ticks" r="${R_OUTER}" />

                <!-- 2. Dual-color Segmented Arcs (Cyan & Amber) -->
                <circle class="dial-rot-ccw dial-segmented-arc" r="${R_MID}" />

                <!-- 3. Inner Dashed Ring -->
                <circle class="dial-rot-cw dial-inner-dashed" r="${R_INNER}" />

                <!-- 4. Cardinal Crosshair Ticks (12, 3, 6, 9) -->
                <line class="dial-tick-line" x1="0" y1="-${R_OUTER}" x2="0" y2="-${R_OUTER - 4}" />
                <line class="dial-tick-line" x1="0" y1="${R_OUTER - 4}" x2="0" y2="${R_OUTER}" />
                <line class="dial-tick-line" x1="-${R_OUTER}" y1="0" x2="-${R_OUTER - 4}" y2="0" />
                <line class="dial-tick-line" x1="${R_OUTER - 4}" y1="0" x2="${R_OUTER}" y2="0" />

                <!-- 5. Center Core Hub -->
                <circle class="dial-core-circle" r="${R_CORE}" />

                <!-- 6. Center Tech Icon -->
                <g class="dial-icon-svg" transform="translate(-8, -8)">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8">
                        ${icon}
                    </svg>
                </g>

                <!-- Labels -->
                <text class="dial-label-num" y="-31" text-anchor="middle">${num}</text>
                <text class="dial-label-title" y="${R_OUTER + 12}" text-anchor="middle">${title}</text>
                <text class="dial-label-sub" y="${R_OUTER + 21}" text-anchor="middle">${sub}</text>
                
                <!-- Status Badge -->
                <g class="dial-badge-wrap" transform="translate(0, ${R_OUTER + 25})">
                    <rect class="dial-badge-rect" x="-22" y="0" width="44" height="10" rx="2" />
                    <text class="dial-badge-text" x="0" y="7.5" text-anchor="middle">STANDBY</text>
                </g>
            </g>
        `;
    }

    /**
     * Switch view between Loop Engineering Graph and Neural Core Rings
     */
    window.switchBrainView = function (view) {
        const loopView = document.getElementById("loopGraphView");
        const coreView = document.getElementById("neuralCoreView");
        const tabLoop = document.getElementById("tabBtnLoop");
        const tabCore = document.getElementById("tabBtnCore");

        if (view === "loop") {
            if (loopView) loopView.style.display = "flex";
            if (coreView) coreView.style.display = "none";
            if (tabLoop) tabLoop.classList.add("active");
            if (tabCore) tabCore.classList.remove("active");
        } else {
            if (loopView) loopView.style.display = "none";
            if (coreView) coreView.style.display = "flex";
            if (tabLoop) tabLoop.classList.remove("active");
            if (tabCore) tabCore.classList.add("active");
        }
    };

    /**
     * Sets node state: 'idle', 'active', 'completed', 'error'
     */
    function setNodeState(nodeKey, state, badgeText, detailText) {
        const nodeObj = NODES[nodeKey];
        if (!nodeObj) return;
        const nodeEl = document.getElementById(nodeObj.id);
        if (!nodeEl) return;

        nodeEl.classList.remove("state-idle", "state-active", "state-completed", "state-error");
        nodeEl.classList.add(`state-${state}`);

        const badgeTxt = nodeEl.querySelector(".dial-badge-text");
        if (badgeTxt && badgeText !== undefined) {
            badgeTxt.textContent = badgeText;
        }

        if (detailText) {
            const subTxt = nodeEl.querySelector(".dial-label-sub");
            if (subTxt) subTxt.textContent = detailText;
        }
    }

    /**
     * Activates animated energy flow along a specific wire
     */
    function activateWire(wireId) {
        const wire = document.getElementById(wireId);
        if (wire) {
            wire.classList.remove("wire-flowing", "wire-active-path");
            void wire.offsetWidth; // force reflow
            wire.classList.add("wire-flowing", "wire-active-path");
        }
    }

    /**
     * Resets all nodes and circuit tracks to standby
     */
    function resetPipeline() {
        Object.keys(NODES).forEach(k => {
            setNodeState(k, "idle", "STANDBY");
            const sub = nodeDefaultSub[k];
            if (sub) {
                const nodeEl = document.getElementById(NODES[k].id);
                if (nodeEl) {
                    const subTxt = nodeEl.querySelector(".dial-label-sub");
                    if (subTxt) subTxt.textContent = sub;
                }
            }
        });

        const wires = document.querySelectorAll(".c-wire");
        wires.forEach(w => w.classList.remove("wire-flowing", "wire-active-path", "wire-completed"));

        const tPhase = document.getElementById("tActivePhase");
        if (tPhase) tPhase.textContent = "STANDBY // MONITOREANDO";

        const tDetail = document.getElementById("tProcessDetail");
        if (tDetail) tDetail.textContent = "Esperando comando de voz o teclado";

        const headerPill = document.getElementById("loopHeaderPill");
        if (headerPill) {
            headerPill.textContent = "LOOP STANDBY";
            headerPill.className = "loop-status-pill standby";
        }
    }

    const nodeDefaultSub = {
        input: "Mic STT / CLI",
        router: "compound-mini",
        fast_stream: "Conversación",
        pruner: "-84% Tokens",
        reasoning: "qwen3.6-27b",
        skill_runner: "client/skills/",
        formatter: "Executive Resp",
        output: "pyttsx3 Audio"
    };

    /**
     * Main event receiver called by backend WebSocket or Client Python
     */
    window.updateLoopProcess = function (payload) {
        if (!payload) return;
        const step = payload.step;
        const status = payload.status || "active";
        const detail = payload.detail || "";

        if (step === "ingestion" && status === "active") {
            window.switchBrainView("loop");
            cycleStartTime = performance.now();
            resetPipeline();
        }

        const headerPill = document.getElementById("loopHeaderPill");
        const tPhase = document.getElementById("tActivePhase");
        const tDetail = document.getElementById("tProcessDetail");
        const tLatency = document.getElementById("tCycleLatency");

        if (headerPill) {
            headerPill.textContent = `PROCESANDO: ${step.toUpperCase()}`;
            headerPill.className = "loop-status-pill active";
        }
        if (tPhase) tPhase.textContent = `FASE: ${step.toUpperCase()}`;
        if (tDetail && detail) tDetail.textContent = detail;

        // --- STEP 1: INGESTION (Input Node) ---
        if (step === "ingestion") {
            setNodeState("input", "active", "RECIBIDO", detail || "Prompt verificado");
            activateWire("wire-input-router");
        }

        // --- STEP 2: FAST ROUTER (Node 1) ---
        else if (step === "router") {
            if (status === "active") {
                setNodeState("input", "completed", "OK");
                setNodeState("router", "active", "CLASIFICANDO", "compound-mini");
            } else if (status === "completed") {
                const domain = (payload.domain || "system").toUpperCase();
                const intent = payload.intent || "tool";
                setNodeState("router", "completed", domain, `Dominio: ${domain}`);

                if (intent === "chat") {
                    activateWire("wire-router-faststream");
                } else {
                    activateWire("wire-router-pruner");
                }
            }
        }

        // --- STEP 2A: FAST STREAM (Node 2A, Chat branch) ---
        else if (step === "fast_stream") {
            if (status === "active") {
                setNodeState("fast_stream", "active", "STREAMING", "compound-mini");
                activateWire("wire-faststream-output");
            } else if (status === "completed") {
                setNodeState("fast_stream", "completed", "GENERADO", "Respuesta lista");
            }
        }

        // --- STEP 2B: CONTEXT PRUNER (Node 2B, Action branch) ---
        else if (step === "pruning") {
            setNodeState("pruner", "active", "PODANDO", "Optimizando...");
            activateWire("wire-pruner-reasoning");
            setTimeout(() => {
                setNodeState("pruner", "completed", "-84% TK", "< 1,200 tokens");
            }, 300);
        }

        // --- STEP 3: REASONING (Node 3, Action branch) ---
        else if (step === "reasoning") {
            if (status === "active") {
                setNodeState("pruner", "completed", "OK");
                setNodeState("reasoning", "active", "RAZONANDO", "qwen3.6-27b");
                activateWire("wire-reasoning-skill");
            } else if (status === "completed") {
                setNodeState("reasoning", "completed", "ORQUESTADO", "Plan listo");
            }
        }

        // --- STEP 4: SKILL RUNNER (Node 4, Action branch) ---
        else if (step === "skill_runner") {
            if (status === "active") {
                const skillName = payload.skill || payload.skill_name || "skill";
                setNodeState("reasoning", "completed", "OK");
                setNodeState("skill_runner", "active", "EJECUTANDO", skillName);
                activateWire("wire-skill-formatter");
            } else if (status === "completed") {
                setNodeState("skill_runner", "completed", "EXITO [0]", "Salida OK");
            }
        }

        // --- STEP 5: FORMATTER (Node 5, Action branch) ---
        else if (step === "formatter") {
            if (status === "active") {
                setNodeState("skill_runner", "completed", "OK");
                setNodeState("formatter", "active", "FORMATEANDO", "Respuesta");
                activateWire("wire-formatter-output");
            } else if (status === "completed") {
                setNodeState("formatter", "completed", "EJECUTIVO", "Texto final");
            }
        }

        // --- STEP 6: SYNTHESIZER / TTS OUTPUT (Convergence) ---
        else if (step === "synthesizer") {
            setNodeState("output", "active", "STREAMING", "pyttsx3 Audio");
        }

        // --- IDLE / COMPLETED ---
        else if (step === "idle") {
            setNodeState("output", "completed", "FINALIZADO", "Audio OK");

            if (cycleStartTime > 0) {
                const elapsed = Math.round(performance.now() - cycleStartTime);
                if (tLatency) tLatency.textContent = `${elapsed} ms`;
            }

            if (headerPill) {
                headerPill.textContent = "LOOP COMPLETADO";
                headerPill.className = "loop-status-pill completed";
            }
            if (tPhase) tPhase.textContent = "CICLO FINALIZADO";

            if (cycleTimer) clearTimeout(cycleTimer);
            cycleTimer = setTimeout(() => {
                resetPipeline();
            }, 4000);
        }
    };

    /**
     * Interactive Simulation: runs a full animated demonstration of either flow
     * @param {string} mode - 'action' (default) or 'chat'
     */
    window.simulateLoopCycle = function (mode = "action") {
        if (isSimulationRunning) return;
        isSimulationRunning = true;
        window.switchBrainView("loop");

        const isAction = (mode !== "chat");

        // 1. Ingestion
        window.updateLoopProcess({
            step: "ingestion",
            status: "active",
            detail: isAction ? 'Input: "sube el volumen al 70%"' : 'Input: "Hola Jarvis, ¿cómo estás?"'
        });

        // 2. Router
        setTimeout(() => {
            window.updateLoopProcess({
                step: "router",
                status: "active",
                detail: "groq/compound-mini clasificando..."
            });
        }, 400);

        setTimeout(() => {
            window.updateLoopProcess({
                step: "router",
                status: "completed",
                domain: isAction ? "system" : "chat",
                intent: isAction ? "tool" : "chat",
                stalling: isAction ? "Un momento señor..." : "",
                detail: isAction ? "Dominio: SYSTEM" : "Dominio: CHAT"
            });
        }, 900);

        if (isAction) {
            // Action Branch: Pruner -> Reasoning -> Skill -> Formatter -> TTS
            setTimeout(() => {
                window.updateLoopProcess({
                    step: "pruning",
                    status: "active",
                    domain: "system",
                    detail: "Podando herramientas (8,200 -> 1,150 tokens)"
                });
            }, 1200);

            setTimeout(() => {
                window.updateLoopProcess({
                    step: "reasoning",
                    status: "active",
                    domain: "system",
                    detail: "qwen/qwen3.6-27b orquestando acción..."
                });
            }, 1700);

            setTimeout(() => {
                window.updateLoopProcess({
                    step: "reasoning",
                    status: "completed",
                    detail: "Llamada: system_control.set_volume(70)"
                });
            }, 2600);

            setTimeout(() => {
                window.updateLoopProcess({
                    step: "skill_runner",
                    status: "active",
                    skill: "system_control",
                    detail: "client/skills/system_control/main.py"
                });
            }, 2900);

            setTimeout(() => {
                window.updateLoopProcess({
                    step: "skill_runner",
                    status: "completed",
                    detail: "Volumen ajustado al 70%"
                });
            }, 3600);

            setTimeout(() => {
                window.updateLoopProcess({
                    step: "formatter",
                    status: "active",
                    detail: "Estructurando confirmación ejecutiva"
                });
            }, 3900);

            setTimeout(() => {
                window.updateLoopProcess({
                    step: "formatter",
                    status: "completed",
                    detail: "Confirmación formulada"
                });
            }, 4300);

            setTimeout(() => {
                window.updateLoopProcess({
                    step: "synthesizer",
                    status: "active",
                    detail: "pyttsx3: 'Volumen ajustado al 70%, señor.'"
                });
            }, 4600);

            setTimeout(() => {
                window.updateLoopProcess({
                    step: "idle",
                    status: "idle",
                    detail: "Acción de sistema ejecutada con éxito."
                });
                isSimulationRunning = false;
            }, 5600);

        } else {
            // Conversational Branch: Fast Stream -> TTS
            setTimeout(() => {
                window.updateLoopProcess({
                    step: "fast_stream",
                    status: "active",
                    detail: "Streaming directo desde groq/compound-mini..."
                });
            }, 1200);

            setTimeout(() => {
                window.updateLoopProcess({
                    step: "fast_stream",
                    status: "completed",
                    detail: "Respuesta conversacional lista"
                });
            }, 2200);

            setTimeout(() => {
                window.updateLoopProcess({
                    step: "synthesizer",
                    status: "active",
                    detail: "pyttsx3: 'Buenos días señor, todos los sistemas en línea.'"
                });
            }, 2500);

            setTimeout(() => {
                window.updateLoopProcess({
                    step: "idle",
                    status: "idle",
                    detail: "Conversación finalizada."
                });
                isSimulationRunning = false;
            }, 3500);
        }
    };

    // Auto-render on DOM ready
    document.addEventListener("DOMContentLoaded", () => {
        renderGraphSVG();
        resetPipeline();
    });

    if (document.readyState === "complete" || document.readyState === "interactive") {
        renderGraphSVG();
        resetPipeline();
    }
})();
