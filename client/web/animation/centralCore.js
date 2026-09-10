/**
 * centralCore.js — SVG Central Brain/Core for JARVIS activation animation.
 *
 * Builds the layered technological nucleus:
 *   Outer segmented ring arcs
 *   ↓ Middle dashed ring (rotates slowly in ready state)
 *   ↓ Neural web paths (stroke-dashoffset animated)
 *   ↓ Inner solid ring
 *   ↓ Hexagonal core frame
 *   ↓ Center pulse + dot
 *   ↓ 6 Orbital activation nodes
 *   ↓ 4 Segment tick marks (12/3/6/9 o'clock)
 *
 * All drawn in a 280×280 SVG (cx=140, cy=140).
 */

const NS  = 'http://www.w3.org/2000/svg';
const CX  = 140;
const CY  = 140;
const TAU = Math.PI * 2;

/** Helper: create SVG element with attributes */
function el(tag, attrs = {}) {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    return e;
}

/** Helper: polar to cartesian */
function polar(cx, cy, r, angleDeg) {
    const rad = (angleDeg - 90) * (Math.PI / 180);
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

/** Helper: SVG arc path for a partial circle */
function arcPath(cx, cy, r, startDeg, endDeg) {
    const s = polar(cx, cy, r, startDeg);
    const e = polar(cx, cy, r, endDeg);
    const large = (endDeg - startDeg) > 180 ? 1 : 0;
    return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`;
}

/* ─── Outer Segmented Arcs ───────────────────────────────────────────────── */
function buildOuterArcs(svg) {
    const arcs = [];
    // 8 arcs with varying gaps — creates a technical segmented ring look
    const segments = [
        { start: 0,   end: 38  },
        { start: 45,  end: 83  },
        { start: 90,  end: 128 },
        { start: 135, end: 173 },
        { start: 180, end: 218 },
        { start: 225, end: 263 },
        { start: 270, end: 308 },
        { start: 315, end: 353 },
    ];
    segments.forEach((seg, i) => {
        const path = el('path', {
            d: arcPath(CX, CY, 126, seg.start, seg.end),
            class: 'act-outer-arc',
            id: `act-arc-${i}`,
        });
        svg.appendChild(path);
        arcs.push(path);
    });
    return arcs;
}

/* ─── Middle Dashed Ring ─────────────────────────────────────────────────── */
function buildMidRing(svg) {
    const g = el('g', { id: 'act-mid-ring-group' });

    // Dashed ring
    const ring = el('circle', {
        cx: CX, cy: CY, r: 104,
        class: 'act-mid-ring',
        id: 'act-mid-ring',
    });

    // Tick marks at 0°/90°/180°/270°
    const ticks = [0, 90, 180, 270].map(deg => {
        const inner = polar(CX, CY, 98,  deg);
        const outer = polar(CX, CY, 110, deg);
        return el('line', {
            x1: inner.x, y1: inner.y,
            x2: outer.x, y2: outer.y,
            class: 'act-segment-mark',
            id:    `act-tick-${deg}`,
        });
    });

    g.appendChild(ring);
    ticks.forEach(t => g.appendChild(t));
    svg.appendChild(g);

    return { group: g, ring, ticks };
}

/* ─── Neural Web Paths ───────────────────────────────────────────────────── */
function buildNeuralWeb(svg) {
    // Semi-random "neural connection" paths inside the core.
    // These create the brain-like network feel.
    const pathDefs = [
        // Horizontal / diagonal strands through the core
        `M ${CX - 60} ${CY - 20} C ${CX - 30} ${CY - 50} ${CX + 30} ${CY + 50} ${CX + 60} ${CY + 20}`,
        `M ${CX - 70} ${CY + 10} C ${CX - 20} ${CY - 30} ${CX + 20} ${CY + 30} ${CX + 70} ${CY - 10}`,
        `M ${CX}     ${CY - 75} C ${CX + 40} ${CY - 20} ${CX - 40} ${CY + 20} ${CX}     ${CY + 75}`,
        `M ${CX - 55} ${CY - 55} C ${CX}      ${CY - 10} ${CX}     ${CY + 10} ${CX + 55} ${CY + 55}`,
        `M ${CX + 55} ${CY - 55} C ${CX}      ${CY - 10} ${CX}     ${CY + 10} ${CX - 55} ${CY + 55}`,
        `M ${CX - 30} ${CY - 80} C ${CX + 10} ${CY - 30} ${CX - 10} ${CY + 30} ${CX + 30} ${CY + 80}`,
    ];

    return pathDefs.map((d, i) => {
        const path = el('path', {
            d,
            class: 'act-neural-path',
            id: `act-neural-${i}`,
        });
        svg.appendChild(path);
        return path;
    });
}

/* ─── Inner Ring ─────────────────────────────────────────────────────────── */
function buildInnerRing(svg) {
    const ring = el('circle', {
        cx: CX, cy: CY, r: 70,
        class: 'act-inner-ring',
        id: 'act-inner-ring',
        opacity: 0,
    });
    svg.appendChild(ring);
    return ring;
}

/* ─── Hexagonal Core Frame ───────────────────────────────────────────────── */
function buildHexCore(svg) {
    // Regular hexagon, pointy-top, radius 42
    const R = 42;
    const pts = Array.from({ length: 6 }, (_, i) => {
        const a = (Math.PI / 180) * (60 * i - 30);
        return `${CX + R * Math.cos(a)},${CY + R * Math.sin(a)}`;
    }).join(' ');

    const hex = el('polygon', {
        points: pts,
        class: 'act-hex-core',
        id: 'act-hex-core',
        opacity: 0,
    });
    svg.appendChild(hex);
    return hex;
}

/* ─── Center Pulse + Core Dot ────────────────────────────────────────────── */
function buildCenterCore(svg) {
    const pulse = el('circle', {
        cx: CX, cy: CY, r: 22,
        class: 'act-center-pulse',
        id: 'act-center-pulse',
        opacity: 0,
    });
    const dot = el('circle', {
        cx: CX, cy: CY, r: 5,
        class: 'act-center-core-dot',
        id: 'act-center-dot',
        opacity: 0,
    });
    svg.appendChild(pulse);
    svg.appendChild(dot);
    return { pulse, dot };
}

/* ─── Orbital Activation Nodes ───────────────────────────────────────────── */
function buildOrbitalNodes(svg) {
    return Array.from({ length: 6 }, (_, i) => {
        const deg = i * 60;
        const pos = polar(CX, CY, 86, deg);
        const node = el('circle', {
            cx: pos.x, cy: pos.y, r: 5,
            class: 'act-orbital-node',
            id: `act-orbital-${i}`,
        });
        svg.appendChild(node);
        return node;
    });
}

/* ─── Inner Accent Arcs (secondary details) ──────────────────────────────── */
function buildAccentArcs(svg) {
    const arcs = [];
    const configs = [
        { r: 55, start: 20,  end: 70,  opacity: 0.5 },
        { r: 55, start: 110, end: 160, opacity: 0.5 },
        { r: 55, start: 200, end: 250, opacity: 0.5 },
        { r: 55, start: 290, end: 340, opacity: 0.5 },
    ];
    configs.forEach((cfg, i) => {
        const path = el('path', {
            d: arcPath(CX, CY, cfg.r, cfg.start, cfg.end),
            fill: 'none',
            stroke: 'rgba(0, 229, 255, 0.45)',
            'stroke-width': '1',
            opacity: 0,
            id: `act-accent-arc-${i}`,
        });
        svg.appendChild(path);
        arcs.push(path);
    });
    return arcs;
}

/* ─── Main Build ─────────────────────────────────────────────────────────── */

/**
 * Builds the complete SVG central core and appends it to the container.
 * Returns refs to all sub-elements for GSAP animation.
 * @param {HTMLElement} container — the #act-central-core div
 */
export function buildCentralCore(container) {
    const svg = el('svg', {
        viewBox: '0 0 280 280',
        width: '280',
        height: '280',
        id: 'act-core-svg',
        overflow: 'visible',
    });

    const outerArcs   = buildOuterArcs(svg);
    const midRing     = buildMidRing(svg);
    const neuralPaths = buildNeuralWeb(svg);
    const innerRing   = buildInnerRing(svg);
    const accentArcs  = buildAccentArcs(svg);
    const hexCore     = buildHexCore(svg);
    const center      = buildCenterCore(svg);
    const orbitalNodes = buildOrbitalNodes(svg);

    container.appendChild(svg);

    return {
        svg,
        outerArcs,
        midRingGroup:  midRing.group,
        midRing:       midRing.ring,
        midTicks:      midRing.ticks,
        neuralPaths,
        innerRing,
        accentArcs,
        hexCore,
        centerPulse:   center.pulse,
        centerDot:     center.dot,
        orbitalNodes,
    };
}
