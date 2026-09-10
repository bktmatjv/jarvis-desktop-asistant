/**
 * hudElements.js — HUD SVG & DOM element builders for JARVIS activation.
 * Generates: corner brackets, scan lines, horizontal lines, side panels,
 * grid nodes, connector SVG overlay, and coordinates display.
 * All elements are appended to the activation overlay and start invisible.
 */

/* ─── Corner Brackets ────────────────────────────────────────────────────── */

/**
 * Creates an SVG corner bracket element.
 * @param {'tl'|'tr'|'bl'|'br'} pos
 * @returns {HTMLElement}
 */
function createCorner(pos) {
    const div = document.createElement('div');
    div.className = `act-corner ${pos}`;
    div.id = `act-corner-${pos}`;

    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '0 0 60 60');
    svg.setAttribute('overflow', 'visible');

    const path = document.createElementNS(ns, 'path');

    // Each corner: L-shape with a small perpendicular tick
    // Path draws from outermost point inward
    const d = {
        tl: 'M 58 4 L 4 4 L 4 58 M 4 4 L 4 4',
        tr: 'M 2 4 L 56 4 L 56 58 M 56 4 L 56 4',
        bl: 'M 58 56 L 4 56 L 4 2 M 4 56 L 4 56',
        br: 'M 2 56 L 56 56 L 56 2 M 56 56 L 56 56',
    }[pos];

    path.setAttribute('d', d);
    path.classList.add('act-corner-path');

    svg.appendChild(path);
    div.appendChild(svg);
    return div;
}

/* ─── Scan Lines ─────────────────────────────────────────────────────────── */

function createScanLines(container) {
    const positions = [0.28, 0.5, 0.72]; // % from top
    const lines = [];
    positions.forEach((pct, i) => {
        const line = document.createElement('div');
        line.className = 'act-scanline';
        line.id = `act-scanline-${i}`;
        line.style.top = `${pct * 100}%`;
        container.appendChild(line);
        lines.push(line);
    });
    return lines;
}

/* ─── Horizontal HUD Lines ───────────────────────────────────────────────── */

function createHLines(container) {
    const config = [
        { top: '30%', finalW: '55%' },
        { top: '40%', finalW: '35%' },
        { top: '60%', finalW: '55%' },
        { top: '70%', finalW: '35%' },
    ];
    return config.map((cfg, i) => {
        const line = document.createElement('div');
        line.className = 'act-hline';
        line.id = `act-hline-${i}`;
        line.style.top = cfg.top;
        line.dataset.finalW = cfg.finalW;
        container.appendChild(line);
        return line;
    });
}

/* ─── Side Panels ────────────────────────────────────────────────────────── */

function createSidePanel(side) {
    const panel = document.createElement('div');
    panel.className = `act-side-panel ${side}`;
    panel.id = `act-panel-${side}`;

    if (side === 'left') {
        panel.innerHTML = `
          <div class="sp-header">SYS DIAGNOSTICS</div>
          <div class="sp-row"><span>CPU LOAD</span><span class="sp-val">—</span></div>
          <div class="sp-row"><span>MEM</span><span class="sp-val">—</span></div>
          <div class="sp-row"><span>NETWORK</span><span class="sp-val">INIT</span></div>
          <div class="sp-row"><span>ENCRYPT</span><span class="sp-val">AES-256</span></div>
          <div class="sp-row"><span>STATUS</span><span class="sp-val" style="color:#00ff66">ONLINE</span></div>
        `;
    } else {
        panel.innerHTML = `
          <div class="sp-header">NEURAL CORE</div>
          <div class="sp-row"><span>SYNAPSIS</span><span class="sp-val">98.7%</span></div>
          <div class="sp-row"><span>PROCESSES</span><span class="sp-val">128</span></div>
          <div class="sp-row"><span>LATENCY</span><span class="sp-val">23ms</span></div>
          <div class="sp-row"><span>MODEL</span><span class="sp-val">JARVIS-7</span></div>
          <div class="sp-row"><span>UPTIME</span><span class="sp-val" style="color:#00ff66">RUNNING</span></div>
        `;
    }
    return panel;
}

/* ─── Grid Nodes ─────────────────────────────────────────────────────────── */

function createGridNodes(container) {
    // Nodes placed at meaningful grid intersections (% positions)
    const positions = [
        { x: 20, y: 30 }, { x: 80, y: 30 },
        { x: 20, y: 70 }, { x: 80, y: 70 },
        { x: 35, y: 20 }, { x: 65, y: 20 },
        { x: 35, y: 80 }, { x: 65, y: 80 },
        { x: 15, y: 50 }, { x: 85, y: 50 },
    ];
    return positions.map((pos, i) => {
        const node = document.createElement('div');
        node.className = 'act-node';
        node.id = `act-node-${i}`;
        node.style.left = `${pos.x}%`;
        node.style.top  = `${pos.y}%`;
        container.appendChild(node);
        return node;
    });
}

/* ─── Connector SVG Lines ────────────────────────────────────────────────── */

function createConnectorsSVG(container) {
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.id = 'act-connectors-svg';
    svg.setAttribute('preserveAspectRatio', 'none');

    // Lines connect edge nodes to the center conceptually
    // Positions in % — converted at runtime by the timeline
    const lines = [
        { x1: '20%', y1: '30%', x2: '35%', y2: '38%' },
        { x1: '80%', y1: '30%', x2: '65%', y2: '38%' },
        { x1: '20%', y1: '70%', x2: '35%', y2: '62%' },
        { x1: '80%', y1: '70%', x2: '65%', y2: '62%' },
        { x1: '35%', y1: '20%', x2: '43%', y2: '33%' },
        { x1: '65%', y1: '20%', x2: '57%', y2: '33%' },
        { x1: '15%', y1: '50%', x2: '33%', y2: '50%' },
        { x1: '85%', y1: '50%', x2: '67%', y2: '50%' },
    ];

    lines.forEach((l, i) => {
        const line = document.createElementNS(ns, 'line');
        line.setAttribute('x1', l.x1); line.setAttribute('y1', l.y1);
        line.setAttribute('x2', l.x2); line.setAttribute('y2', l.y2);
        line.id = `act-conn-${i}`;
        svg.appendChild(line);
    });

    container.appendChild(svg);
    return svg;
}

/* ─── Coordinates Display ────────────────────────────────────────────────── */

function createCoords(container) {
    const data = [
        { cls: 'bottom-left',  html: 'LAT 34.052° N / LON 118.243° W<br>ALT 287.4m — ZONE UTC-5' },
        { cls: 'bottom-right', html: 'JARVIS OS v2.5.1<br>NODE: CORE-01 — SECURE' },
        { cls: 'top-center',   html: '■ INITIATING NEURAL MATRIX ■' },
    ];
    return data.map((d, i) => {
        const el = document.createElement('div');
        el.className = `act-coords ${d.cls}`;
        el.id = `act-coords-${i}`;
        el.innerHTML = d.html;
        container.appendChild(el);
        return el;
    });
}

/* ─── Pulse Rings ────────────────────────────────────────────────────────── */

function createPulseRings(container) {
    return [140, 190, 240].map((size, i) => {
        const ring = document.createElement('div');
        ring.className = 'act-pulse-ring';
        ring.id = `act-pulse-${i}`;
        ring.style.width  = `${size}px`;
        ring.style.height = `${size}px`;
        container.appendChild(ring);
        return ring;
    });
}

/* ─── JARVIS ONLINE text ─────────────────────────────────────────────────── */

function createOnlineText(container) {
    const el = document.createElement('div');
    el.id = 'act-online-text';
    el.textContent = '■ JARVIS  ONLINE ■';
    container.appendChild(el);
    return el;
}

/* ─── Main Build Function ────────────────────────────────────────────────── */

/**
 * Builds all HUD DOM elements and appends them to the overlay.
 * Returns references to all created elements for use in the GSAP timeline.
 * @param {HTMLElement} overlay
 * @returns {Object} refs — named references to all elements
 */
export function buildHudElements(overlay) {
    // Corner brackets
    const corners = ['tl', 'tr', 'bl', 'br'].map(pos => {
        const el = createCorner(pos);
        overlay.appendChild(el);
        return el;
    });

    // Scan lines
    const scanlines = createScanLines(overlay);

    // Horizontal HUD lines
    const hlines = createHLines(overlay);

    // Side panels
    const panelLeft  = createSidePanel('left');
    const panelRight = createSidePanel('right');
    overlay.appendChild(panelLeft);
    overlay.appendChild(panelRight);

    // Grid nodes
    const nodes = createGridNodes(overlay);

    // Connector SVG
    const connectorsSvg = createConnectorsSVG(overlay);

    // Coordinates
    const coords = createCoords(overlay);

    // Pulse rings
    const pulseRings = createPulseRings(overlay);

    // JARVIS ONLINE text
    const onlineText = createOnlineText(overlay);

    return {
        corners,
        scanlines,
        hlines,
        panelLeft,
        panelRight,
        nodes,
        connectorsSvg,
        coords,
        pulseRings,
        onlineText,
        // Shortcut selectors for GSAP
        cornerPaths: overlay.querySelectorAll('.act-corner-path'),
    };
}
