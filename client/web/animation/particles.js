/**
 * particles.js — Minimal DOM particle system for the JARVIS activation.
 * Creates ~22 small glowing points scattered around the viewport,
 * used during the Signal phase (Phase 1).
 */

const PARTICLE_COUNT = 22;
const particles = [];

/**
 * Creates and appends all particles to the overlay.
 * Called once during DOM setup — particles start invisible.
 * @param {HTMLElement} container — the activation overlay div
 */
export function createParticles(container) {
    for (let i = 0; i < PARTICLE_COUNT; i++) {
        const p = document.createElement('div');
        p.className = 'act-particle';
        p.id = `act-p-${i}`;

        // Distribute particles around the periphery (not center)
        // to avoid cluttering the core area.
        const zone = Math.random();
        let x, y;

        if (zone < 0.25) {
            // Top band
            x = 10 + Math.random() * 80;
            y = 5  + Math.random() * 20;
        } else if (zone < 0.5) {
            // Bottom band
            x = 10 + Math.random() * 80;
            y = 75 + Math.random() * 20;
        } else if (zone < 0.75) {
            // Left band
            x = 3  + Math.random() * 18;
            y = 20 + Math.random() * 60;
        } else {
            // Right band
            x = 79 + Math.random() * 18;
            y = 20 + Math.random() * 60;
        }

        p.style.left = `${x}%`;
        p.style.top  = `${y}%`;

        // Slightly randomize size for depth variation
        const size = 1.5 + Math.random() * 2.5;
        p.style.width  = `${size}px`;
        p.style.height = `${size}px`;

        container.appendChild(p);
        particles.push(p);
    }

    return particles;
}

/**
 * Returns all particle elements for GSAP to animate.
 */
export function getParticles() {
    return particles;
}
