/**
 * jarvisActivation.js — Main GSAP Timeline Orchestrator
 *
 * Runs the 6-phase cinematic boot sequence for JARVIS Panel.
 * Phases:
 *   "signal"     0.00s → Dormant point awakens
 *   "hud"        0.45s → HUD skeleton construction
 *   "core"       0.90s → Central brain assembly
 *   "activation" 1.55s → Energy pulse, nodes online
 *   "ready"      2.10s → Transition to main panel
 *
 * Usage:
 *   import { runJarvisActivation } from './animation/jarvisActivation.js';
 *   runJarvisActivation(() => console.log('JARVIS ONLINE'));
 */

import { buildHudElements } from './hudElements.js';
import { buildCentralCore  } from './centralCore.js';
import { createParticles, getParticles } from './particles.js';

/* ─── Easing aliases ─────────────────────────────────────────────────────── */
const EASE_OUT  = 'power2.out';
const EASE_IN   = 'power2.in';
const EASE_IO   = 'power2.inOut';
const EASE_EXPO = 'expo.out';
const EASE_BACK = 'back.out(1.4)';

/* ─── Build the overlay DOM ──────────────────────────────────────────────── */
function buildOverlay() {
    const overlay = document.createElement('div');
    overlay.id = 'jarvis-activation-overlay';

    // Signal point (the first thing that lights up)
    const signalPoint = document.createElement('div');
    signalPoint.id = 'act-signal-point';
    overlay.appendChild(signalPoint);

    // Particles
    createParticles(overlay);

    // HUD elements
    const hud = buildHudElements(overlay);

    // Central core container
    const coreContainer = document.createElement('div');
    coreContainer.id = 'act-central-core';
    overlay.appendChild(coreContainer);
    const core = buildCentralCore(coreContainer);

    const slideHome = document.getElementById('slide-home');
    if (slideHome) {
        slideHome.appendChild(overlay);
    } else {
        document.body.insertBefore(overlay, document.body.firstChild);
    }

    return { overlay, signalPoint, hud, core };
}

/* ─── Helper: set stroke-dashoffset on all SVG arcs ─────────────────────── */
function initArcDash(els, length = 200) {
    els.forEach(e => {
        const totalLength = e.getTotalLength ? e.getTotalLength() : length;
        e.style.strokeDasharray  = totalLength;
        e.style.strokeDashoffset = totalLength;
    });
}

/* ─── PHASE 1: SIGNAL ────────────────────────────────────────────────────── */
function phaseSignal(tl, refs) {
    const { signalPoint } = refs;
    const particles = getParticles();

    tl.add('signal', 0);

    // Central point appears with a quick scale-in
    tl.to(signalPoint, {
        opacity: 1, scale: 1,
        duration: 0.18,
        ease: EASE_EXPO,
    }, 'signal');

    // Point pulses outward twice — like a sonar ping
    tl.to(signalPoint, {
        scale: 2.5, opacity: 0.4,
        duration: 0.22,
        ease: EASE_OUT,
    }, 'signal+=0.18');
    tl.to(signalPoint, {
        scale: 1.2, opacity: 0.9,
        duration: 0.12,
        ease: EASE_IN,
    }, 'signal+=0.40');

    // Scan lines sweep through
    tl.to('#act-scanline-0, #act-scanline-1, #act-scanline-2', {
        opacity: 1,
        duration: 0.12,
        stagger: 0.06,
        ease: EASE_OUT,
    }, 'signal+=0.10');
    tl.to('#act-scanline-0, #act-scanline-1, #act-scanline-2', {
        opacity: 0,
        duration: 0.25,
        stagger: 0.04,
        ease: EASE_IN,
        delay: 0.12,
    }, 'signal+=0.22');

    // Particles appear with stagger (lightweight DOM)
    tl.to(particles, {
        opacity: () => 0.3 + Math.random() * 0.5,
        duration: 0.3,
        stagger: { each: 0.015, from: 'random' },
        ease: EASE_OUT,
    }, 'signal+=0.15');
}

/* ─── PHASE 2: HUD CONSTRUCTION ─────────────────────────────────────────── */
function phaseHud(tl, refs) {
    const { hud } = refs;

    tl.add('hud', 0.45);

    // 1. Corner brackets: reveal opacity then draw stroke
    tl.to(hud.corners, {
        opacity: 1, duration: 0.01,
        stagger: 0.06,
    }, 'hud');

    // Animate stroke-dashoffset to 0 (draw the L-shape)
    tl.to(hud.cornerPaths, {
        strokeDashoffset: 0,
        duration: 0.35,
        stagger: 0.07,
        ease: EASE_EXPO,
    }, 'hud+=0.02');

    // 2. Horizontal HUD lines extend from center outward
    hud.hlines.forEach((line, i) => {
        tl.to(line, {
            opacity: 1,
            width: line.dataset.finalW,
            duration: 0.28,
            ease: EASE_EXPO,
        }, `hud+=${0.12 + i * 0.06}`);
    });

    // 3. Grid nodes blink in with stagger
    tl.to(hud.nodes, {
        opacity: 1,
        duration: 0.15,
        stagger: { each: 0.04, from: 'random' },
        ease: EASE_OUT,
    }, 'hud+=0.18');

    // 4. Connector SVG lines fade in
    tl.to(hud.connectorsSvg, {
        opacity: 1,
        duration: 0.3,
        ease: EASE_OUT,
    }, 'hud+=0.22');

    // 5. Side panels reveal via clip-path
    tl.to([hud.panelLeft, hud.panelRight], {
        opacity: 1,
        clipPath: 'inset(0 0% 0 0)',  // From right edge → full reveal
        duration: 0.35,
        stagger: 0.08,
        ease: EASE_IO,
    }, 'hud+=0.28');

    // 6. Coordinates
    tl.to(hud.coords, {
        opacity: 1,
        duration: 0.2,
        stagger: 0.06,
        ease: EASE_OUT,
    }, 'hud+=0.38');
}

/* ─── PHASE 3: CORE ASSEMBLY ─────────────────────────────────────────────── */
function phaseCore(tl, refs) {
    const { core } = refs;

    tl.add('core', 0.90);

    // Set up dash arrays for stroke animation
    // (done here since elements exist in DOM now)
    core.outerArcs.forEach(arc => {
        try {
            const len = arc.getTotalLength();
            arc.style.strokeDasharray  = len;
            arc.style.strokeDashoffset = len;
        } catch(_) {}
    });
    core.neuralPaths.forEach(path => {
        try {
            const len = path.getTotalLength();
            path.style.strokeDasharray  = len;
            path.style.strokeDashoffset = len;
        } catch(_) {}
    });

    // 1. Outer segmented arcs draw in stagger
    tl.to(core.outerArcs, {
        strokeDashoffset: 0,
        opacity: 1,
        duration: 0.4,
        stagger: { each: 0.05, from: 'start' },
        ease: EASE_EXPO,
    }, 'core');

    // 2. Middle ring + ticks
    tl.to(core.midRing, {
        opacity: 1,
        duration: 0.3,
        ease: EASE_OUT,
    }, 'core+=0.18');
    tl.to(core.midTicks, {
        opacity: 1,
        duration: 0.1,
        stagger: 0.05,
        ease: EASE_OUT,
    }, 'core+=0.25');

    // 3. Neural web paths draw in (stroke-dashoffset → 0)
    tl.to(core.neuralPaths, {
        strokeDashoffset: 0,
        duration: 0.45,
        stagger: { each: 0.06, from: 'random' },
        ease: EASE_IO,
    }, 'core+=0.22');

    // 4. Inner ring fades in
    tl.to(core.innerRing, {
        opacity: 1,
        duration: 0.25,
        ease: EASE_OUT,
    }, 'core+=0.32');

    // 5. Accent arcs
    tl.to(core.accentArcs, {
        opacity: 1,
        duration: 0.2,
        stagger: 0.05,
        ease: EASE_OUT,
    }, 'core+=0.36');

    // 6. Hex core scales in from center
    tl.to(core.hexCore, {
        opacity: 1,
        scale: 1,
        transformOrigin: '140px 140px',
        duration: 0.3,
        ease: EASE_BACK,
    }, 'core+=0.42');

    // 7. Center pulse ring expands
    tl.fromTo(core.centerPulse,
        { opacity: 0, scale: 0.3, transformOrigin: '140px 140px' },
        { opacity: 1, scale: 1,   duration: 0.28, ease: EASE_BACK },
        'core+=0.50'
    );

    // 8. Core dot appears
    tl.to(core.centerDot, {
        opacity: 1,
        scale: 1,
        transformOrigin: '140px 140px',
        duration: 0.2,
        ease: EASE_EXPO,
    }, 'core+=0.56');

    // 9. Particles disappear as core takes over visual focus
    tl.to(getParticles(), {
        opacity: 0,
        duration: 0.3,
        stagger: { each: 0.01, from: 'random' },
        ease: EASE_IN,
    }, 'core+=0.50');
}

/* ─── PHASE 4: ACTIVATION ────────────────────────────────────────────────── */
function phaseActivation(tl, refs) {
    const { core, hud } = refs;

    tl.add('activation', 1.55);

    // 1. Orbital nodes activate in sequence (like systems coming online)
    tl.to(core.orbitalNodes, {
        opacity: 1,
        fill: 'rgba(0, 229, 255, 0.5)',
        filter: 'drop-shadow(0 0 4px rgba(0, 229, 255, 0.9))',
        duration: 0.12,
        stagger: { each: 0.08, from: 'start' },
        ease: EASE_EXPO,
    }, 'activation');

    // 2. Energy pulse rings expand outward from core center
    tl.fromTo(hud.pulseRings,
        { opacity: 0.8, scale: 0.3 },
        {
            opacity: 0,
            scale: 1,
            transformOrigin: '50% 50%',
            duration: 0.55,
            stagger: 0.12,
            ease: EASE_OUT,
        },
        'activation+=0.15'
    );

    // 3. Center dot pulses bright
    tl.to(core.centerDot, {
        scale: 1.8,
        transformOrigin: '140px 140px',
        duration: 0.15,
        ease: EASE_OUT,
        yoyo: true,
        repeat: 1,
    }, 'activation+=0.20');

    // 4. HUD elements do a synchronized micro-pulse (opacity flash)
    tl.to([hud.panelLeft, hud.panelRight, hud.connectorsSvg], {
        opacity: 0.5,
        duration: 0.08,
        ease: EASE_IN,
        yoyo: true,
        repeat: 1,
    }, 'activation+=0.30');

    // 5. Outer arcs do a brief brightness surge
    tl.to(core.outerArcs, {
        filter: 'drop-shadow(0 0 8px rgba(0, 229, 255, 1))',
        duration: 0.2,
        ease: EASE_OUT,
        yoyo: true,
        repeat: 1,
    }, 'activation+=0.35');

    // 6. JARVIS ONLINE text flashes in
    tl.to(hud.onlineText, {
        opacity: 1,
        duration: 0.15,
        ease: EASE_OUT,
    }, 'activation+=0.45');
    tl.to(hud.onlineText, {
        opacity: 0.7,
        duration: 0.3,
        ease: EASE_OUT,
    }, 'activation+=0.65');

    // 7. Signal point fades out (its job is done)
    tl.to('#act-signal-point', {
        opacity: 0,
        duration: 0.2,
        ease: EASE_IN,
    }, 'activation+=0.20');
}

/* ─── PHASE 5: READY → TRANSITION ────────────────────────────────────────── */
function phaseReady(tl, refs, mainApp, panels) {
    const { overlay, core } = refs;

    tl.add('ready', 2.10);

    // 1. Fade out the ONLINE text
    tl.to(refs.hud.onlineText, {
        opacity: 0, duration: 0.2, ease: EASE_IN,
    }, 'ready');

    // 2. Add ready CSS class for idle breathing (CSS takes over)
    tl.call(() => {
        document.getElementById('act-central-core')?.classList.add('act-core-ready');
    }, [], 'ready');

    // The overlay now stays visible in Slide 0.
    // navigation.js handles the manual slide transition to mainApp.
}

/* ─── Public API ─────────────────────────────────────────────────────────── */

/**
 * Runs the full JARVIS cinematic activation sequence.
 * @param {Function} onComplete — Called when animation finishes and panel is ready.
 */
export function runJarvisActivation(onComplete) {
    // Find main app elements
    const mainApp = document.getElementById('mainApp');
    const panels  = document.querySelectorAll('.panel');

    // Build overlay DOM
    const refs = buildOverlay();

    // Measure SVG lengths AFTER elements are in DOM
    requestAnimationFrame(() => {
        // Master timeline
        const tl = gsap.timeline({
            onComplete: () => {
                if (typeof onComplete === 'function') onComplete();
            },
            defaults: { ease: EASE_OUT },
        });

        phaseSignal(tl, refs);
        phaseHud(tl, refs);
        phaseCore(tl, refs);
        phaseActivation(tl, refs);
        phaseReady(tl, refs, mainApp, panels);

        tl.play();
    });
}

/* ─── Auto-start on DOMContentLoaded ────────────────────────────────────── */
// Called automatically when the module loads. Bridges to the window callback
// exposed by script.js (non-module) so panel logic starts after animation.
document.addEventListener('DOMContentLoaded', () => {
    runJarvisActivation(() => {
        if (typeof window.onActivationComplete === 'function') {
            window.onActivationComplete();
        }
    });
});
