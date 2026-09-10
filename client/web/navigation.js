/**
 * navigation.js — Horizontal slide navigation: Home ↔ Panel
 *
 * Two slides side by side. Drag mouse or click the edge indicators to switch.
 * Also supports keyboard arrows and touch/trackpad swipe.
 *
 * Depends on GSAP (loaded before this script in index.html).
 */
(function () {
    'use strict';

    let currentSlide = 0;
    let panelReady   = false;

    // Drag state
    let isDragging   = false;
    let dragStartX   = 0;
    let dragLiveX    = 0;
    const DRAG_THRESHOLD = 80; // px

    document.addEventListener('DOMContentLoaded', () => {
        const track    = document.getElementById('slides-track');
        const viewport = document.getElementById('jarvis-viewport');
        const navLeft  = document.getElementById('nav-left');
        const navRight = document.getElementById('nav-right');
        if (!track || !viewport) return;

        if (navLeft) navLeft.addEventListener('click', () => slideTo(0));
        if (navRight) navRight.addEventListener('click', () => slideTo(1));

        /* ── Core slide function ──────────────────────────────────────── */
        function slideTo(index) {
            if (index < 0 || index > 1) return;

            gsap.to(track, {
                x: -index * window.innerWidth,
                duration: 0.72,
                ease: 'power3.inOut',
                onComplete() {
                    if (index === 1 && !panelReady) {
                        panelReady = true;
                        initPanel();
                    }
                },
            });

            currentSlide = index;
            updateNav();
        }

        /* ── First visit to panel: fade in + cascade ─────────────────── */
        function initPanel() {
            const mainApp = document.getElementById('mainApp');
            const panels  = document.querySelectorAll('.panel');

            gsap.set(panels, { opacity: 0, y: 12 });
            gsap.to(mainApp, { opacity: 1, pointerEvents: 'auto', duration: 0.3, ease: 'power2.out' });
            gsap.to(panels, {
                opacity: 1, y: 0,
                duration: 0.38,
                stagger: 0.05,
                ease: 'power2.out',
                delay: 0.1,
            });

            if (typeof startAudioVisualizer === 'function') startAudioVisualizer();
            if (typeof loadSystemData       === 'function') loadSystemData();
        }

        /* ── Nav indicator visibility ─────────────────────────────────── */
        function updateNav() {
            const onHome = currentSlide === 0;

            // Left indicator (← HOME): only visible on panel
            gsap.to(navLeft, {
                opacity: onHome ? 0 : 1,
                x:       onHome ? -6 : 0,
                duration: 0.35,
                ease: 'power2.out',
            });
            navLeft.style.pointerEvents = onHome ? 'none' : 'auto';

            // Right indicator (PANEL →): only visible on home
            gsap.to(navRight, {
                opacity: onHome ? 1 : 0,
                x:       onHome ? 0 : 6,
                duration: 0.35,
                ease: 'power2.out',
            });
            navRight.style.pointerEvents = onHome ? 'auto' : 'none';
        }

        /* ── Mouse drag ───────────────────────────────────────────────── */
        viewport.addEventListener('mousedown', (e) => {
            if (e.target.closest('input, button, .nav-indicator, select, textarea')) return;
            isDragging = true;
            dragStartX = e.clientX;
            dragLiveX  = e.clientX;
            viewport.style.cursor = 'grabbing';
        });

        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            dragLiveX = e.clientX;
            const delta = (dragLiveX - dragStartX) * 0.65; // dampen
            gsap.set(track, { x: -currentSlide * window.innerWidth + delta });
        });

        window.addEventListener('mouseup', () => {
            if (!isDragging) return;
            isDragging = false;
            viewport.style.cursor = '';
            const delta = dragLiveX - dragStartX;
            if (Math.abs(delta) > DRAG_THRESHOLD) {
                slideTo(delta < 0 ? 1 : 0);
            } else {
                gsap.to(track, {
                    x: -currentSlide * window.innerWidth,
                    duration: 0.4,
                    ease: 'power3.out',
                });
            }
        });

        /* ── Touch / trackpad ─────────────────────────────────────────── */
        let touchStart = 0, touchLive = 0;
        viewport.addEventListener('touchstart',  (e) => { touchStart = touchLive = e.touches[0].clientX; });
        viewport.addEventListener('touchmove',   (e) => {
            touchLive = e.touches[0].clientX;
            const delta = (touchLive - touchStart) * 0.65;
            gsap.set(track, { x: -currentSlide * window.innerWidth + delta });
        });
        viewport.addEventListener('touchend', () => {
            const delta = touchLive - touchStart;
            if (Math.abs(delta) > DRAG_THRESHOLD) slideTo(delta < 0 ? 1 : 0);
            else gsap.to(track, { x: -currentSlide * window.innerWidth, duration: 0.4, ease: 'power3.out' });
        });

        /* ── Keyboard shortcuts ───────────────────────────────────────── */
        document.addEventListener('keydown', (e) => {
            if (document.activeElement?.tagName === 'INPUT') return;
            if (e.key === 'ArrowRight') slideTo(1);
            if (e.key === 'ArrowLeft')  slideTo(0);
        });

        /* ── Expose globally ──────────────────────────────────────────── */
        window.slideTo   = slideTo;
        window.jarvisNav = { slideTo, initPanel };

        /* ── Initial state ────────────────────────────────────────────── */
        // Start on home screen (index 0); right arrow visible, left hidden
        gsap.set(navLeft,  { opacity: 0, x: -6 });
        gsap.set(navRight, { opacity: 1, x:  0 });
        navLeft.style.pointerEvents  = 'none';
        navRight.style.pointerEvents = 'auto';
    });
})();
