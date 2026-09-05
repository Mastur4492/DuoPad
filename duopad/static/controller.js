/**
 * DuoPad - Mobile Virtual Gamepad Client
 * High-performance touchscreen controller for PC games (FIFA/EA FC, Co-Op, Racing, Fighting).
 * Features:
 *  - Independent multi-touch tracking via Touch.identifier
 *  - Continuous 360-degree analog joysticks with inverted Y-axis for Xbox standard
 *  - Tactile button press feedback & haptic vibration
 *  - Screen Wake-Lock integration to keep display awake during matches
 *  - Anti-stuck button safety on blur/visibility change
 *  - Real-time ping/latency monitor
 */

(function () {
    'use strict';

    // --------------------------------------------------------------------------
    // State & References
    // --------------------------------------------------------------------------
    const socket = io({
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        transports: ['websocket']
    });

    let assignedPlayer = null;
    let wakeLock = null;

    // DOM Elements
    const statusOverlay = document.getElementById('status-overlay');
    const statusSpinner = document.getElementById('status-spinner');
    const statusTitle = document.getElementById('status-title');
    const statusMessage = document.getElementById('status-message');
    const playerBanner = document.getElementById('player-banner');
    const playerBadge = document.getElementById('player-badge');
    const btnReconnect = document.getElementById('btn-reconnect');
    const hudPlayerPill = document.getElementById('hud-player-pill');
    const hudPlayerText = document.getElementById('hud-player-text');
    const hudPing = document.getElementById('hud-ping');
    const btnFullscreen = document.getElementById('btn-fullscreen');

    // --------------------------------------------------------------------------
    // Socket.IO Lifecycle & Player Assignment
    // --------------------------------------------------------------------------
    socket.on('connect', () => {
        console.log('[Socket] Connected to server.');
        statusTitle.textContent = 'Authenticating Slot...';
        statusMessage.textContent = 'Requesting Player Assignment from PC...';
    });

    socket.on('assigned', (data) => {
        assignedPlayer = data.player;
        console.log(`[Socket] Assigned as Player ${assignedPlayer}`);

        // Update Theme
        document.body.className = assignedPlayer === 1 ? 'theme-p1' : 'theme-p2';
        playerBadge.textContent = `PLAYER ${assignedPlayer}`;
        hudPlayerText.textContent = `P${assignedPlayer}`;
        playerBanner.classList.remove('hidden');
        statusTitle.textContent = `Connected as Player ${assignedPlayer}`;
        statusMessage.textContent = `Linked to Virtual Xbox Controller #${assignedPlayer}`;
        statusSpinner.classList.add('hidden');

        // Hide overlay after 600ms so player sees confirmation
        setTimeout(() => {
            statusOverlay.classList.remove('active');
        }, 600);

        requestWakeLock();
    });

    socket.on('game_full', (data) => {
        console.warn('[Socket] Game is full');
        statusOverlay.classList.add('active');
        statusSpinner.classList.add('hidden');
        statusTitle.textContent = 'Game is Full';
        statusMessage.textContent = data.message || 'Two players are already connected. Please wait for an open slot.';
        btnReconnect.classList.remove('hidden');
    });

    socket.on('disconnect', (reason) => {
        console.warn('[Socket] Disconnected:', reason);
        statusOverlay.classList.add('active');
        statusSpinner.classList.remove('hidden');
        statusTitle.textContent = 'Reconnecting to Laptop...';
        statusMessage.textContent = 'Connection lost. Trying to reconnect over Wi-Fi...';
        playerBanner.classList.add('hidden');
        btnReconnect.classList.add('hidden');
        
        // Safety: release all local states
        releaseAllInputs();
    });

    btnReconnect.addEventListener('click', () => {
        window.location.reload();
    });

    // --------------------------------------------------------------------------
    // Ping / Latency Monitor
    // --------------------------------------------------------------------------
    let pingStartTime = 0;
    setInterval(() => {
        if (socket.connected) {
            pingStartTime = performance.now();
            socket.emit('ping_check', { time: pingStartTime });
        }
    }, 2000);

    socket.on('pong_check', (data) => {
        const rtt = Math.round(performance.now() - pingStartTime);
        if (hudPing) {
            hudPing.textContent = `${rtt} ms`;
        }
    });

    // --------------------------------------------------------------------------
    // Input Emitter Helpers
    // --------------------------------------------------------------------------
    function sendButton(btnName, pressed) {
        if (!socket.connected) return;
        socket.emit('input', {
            type: 'button',
            button: btnName,
            pressed: pressed
        });
    }

    function sendTrigger(trigName, value) {
        if (!socket.connected) return;
        socket.emit('input', {
            type: 'trigger',
            trigger: trigName,
            value: value
        });
    }

    function sendStick(stickType, x, y) {
        if (!socket.connected) return;
        socket.emit('input', {
            type: stickType, // 'left_stick' or 'right_stick'
            x: x,
            y: y
        });
    }

    function sendReset() {
        if (!socket.connected) return;
        socket.emit('input', { type: 'reset' });
    }

    function triggerHaptic(duration = 14) {
        if (window.Android && window.Android.vibrate) {
            try {
                window.Android.vibrate(duration);
                return;
            } catch (e) {}
        }
        if (navigator.vibrate) {
            try {
                navigator.vibrate(duration);
            } catch (e) {}
        }
    }

    // --------------------------------------------------------------------------
    // Multi-Touch Button Handler
    // Maps touch identifier -> button element for multi-touch safety
    // --------------------------------------------------------------------------
    const activeTouchButtons = new Map(); // touchId -> element

    function initButtons() {
        const interactiveButtons = document.querySelectorAll('[data-btn], [data-trigger]');

        interactiveButtons.forEach((btn) => {
            btn.addEventListener('touchstart', (e) => {
                e.preventDefault();
                for (let i = 0; i < e.changedTouches.length; i++) {
                    const touch = e.changedTouches[i];
                    pressButtonElement(btn, touch.identifier);
                }
            }, { passive: false });
        });

        // Global touch end/cancel to ensure no buttons get stuck if finger slides off
        window.addEventListener('touchend', handleGlobalTouchEnd, { passive: false });
        window.addEventListener('touchcancel', handleGlobalTouchEnd, { passive: false });
    }

    function pressButtonElement(el, touchId) {
        activeTouchButtons.set(touchId, el);
        el.classList.add('active');
        triggerHaptic(14);

        if (el.dataset.btn) {
            sendButton(el.dataset.btn, true);
        } else if (el.dataset.trigger) {
            sendTrigger(el.dataset.trigger, 1.0);
        }
    }

    function releaseButtonElement(el, touchId) {
        activeTouchButtons.delete(touchId);
        el.classList.remove('active');

        if (el.dataset.btn) {
            sendButton(el.dataset.btn, false);
        } else if (el.dataset.trigger) {
            sendTrigger(el.dataset.trigger, 0.0);
        }
    }

    function handleGlobalTouchEnd(e) {
        for (let i = 0; i < e.changedTouches.length; i++) {
            const touch = e.changedTouches[i];
            if (activeTouchButtons.has(touch.identifier)) {
                const el = activeTouchButtons.get(touch.identifier);
                releaseButtonElement(el, touch.identifier);
            }
        }
    }

    function releaseAllInputs() {
        activeTouchButtons.forEach((el, touchId) => {
            el.classList.remove('active');
        });
        activeTouchButtons.clear();
        sendReset();
    }

    // --------------------------------------------------------------------------
    // Analog Joystick Controller (Monect PC Remote Grade - Silky Smooth 60Hz)
    // --------------------------------------------------------------------------
    class VirtualJoystick {
        constructor(zoneId, knobId, stickType) {
            this.zone = document.getElementById(zoneId);
            this.knob = document.getElementById(knobId);
            this.base = this.zone ? (this.zone.querySelector('.stick-ring') || this.zone.querySelector('.stick-base')) : null;
            this.stickType = stickType; // 'left_stick' or 'right_stick'

            this.touchId = null;
            this.centerX = 0;
            this.centerY = 0;
            this.maxRadius = 55; // Monect-grade full thumb travel range
            this.deadzone = 0.03; // Ultra-precise 3% deadzone

            this.currentX = 0.0;
            this.currentY = 0.0;
            this.lastSentX = -999.0;
            this.lastSentY = -999.0;
            this.ticker = null;
            this.rafPending = false;
            this.pendingClampedX = 0;
            this.pendingClampedY = 0;

            this.initEvents();
        }

        initEvents() {
            if (!this.zone) return;
            this.zone.addEventListener('touchstart', (e) => this.onTouchStart(e), { passive: false });
            window.addEventListener('touchmove', (e) => this.onTouchMove(e), { passive: false });
            window.addEventListener('touchend', (e) => this.onTouchEnd(e), { passive: false });
            window.addEventListener('touchcancel', (e) => this.onTouchEnd(e), { passive: false });
        }

        onTouchStart(e) {
            if (this.touchId !== null) return;
            e.preventDefault();

            const touch = e.changedTouches[0];
            this.touchId = touch.identifier;

            // Anchor center precisely to the visual ring center
            const targetElement = this.base || this.zone;
            const rect = targetElement.getBoundingClientRect();
            this.centerX = rect.left + rect.width / 2;
            this.centerY = rect.top + rect.height / 2;

            if (this.base) this.base.classList.add('active-stick');
            this.processTouch(touch.clientX, touch.clientY);

            // Steady 30Hz keepalive heartbeat while holding stick (prevents Wi-Fi buffer congestion)
            if (!this.ticker) {
                this.ticker = setInterval(() => {
                    if (this.touchId !== null) {
                        sendStick(this.stickType, this.currentX, this.currentY);
                    }
                }, 33);
            }
        }

        onTouchMove(e) {
            if (this.touchId === null) return;
            for (let i = 0; i < e.changedTouches.length; i++) {
                const touch = e.changedTouches[i];
                if (touch.identifier === this.touchId) {
                    e.preventDefault();
                    this.processTouch(touch.clientX, touch.clientY);
                    break;
                }
            }
        }

        onTouchEnd(e) {
            if (this.touchId === null) return;
            for (let i = 0; i < e.changedTouches.length; i++) {
                const touch = e.changedTouches[i];
                if (touch.identifier === this.touchId) {
                    this.touchId = null;
                    if (this.ticker) {
                        clearInterval(this.ticker);
                        this.ticker = null;
                    }
                    this.resetKnob();
                    break;
                }
            }
        }

        processTouch(clientX, clientY) {
            const dx = clientX - this.centerX;
            const dy = clientY - this.centerY;
            const dist = Math.hypot(dx, dy);

            let clampedX = dx;
            let clampedY = dy;

            if (dist > this.maxRadius) {
                clampedX = (dx / dist) * this.maxRadius;
                clampedY = (dy / dist) * this.maxRadius;
            }

            // High-refresh rate 60/90/120Hz smooth GPU compositing via requestAnimationFrame
            this.pendingClampedX = clampedX;
            this.pendingClampedY = clampedY;
            if (!this.rafPending) {
                this.rafPending = true;
                requestAnimationFrame(() => {
                    this.knob.style.transform = `translate3d(${this.pendingClampedX}px, ${this.pendingClampedY}px, 0)`;
                    this.rafPending = false;
                });
            }

            // Normalized (-1.0 to 1.0) with inverted Y (Xbox 360 standard: up is positive)
            const normX = clampedX / this.maxRadius;
            const normY = -(clampedY / this.maxRadius);
            const mag = Math.hypot(normX, normY);

            if (mag > this.deadzone) {
                const scale = (mag - this.deadzone) / (1.0 - this.deadzone);
                const factor = Math.min(1.0, scale) / mag;
                this.currentX = Number((normX * factor).toFixed(4));
                this.currentY = Number((normY * factor).toFixed(4));
            } else {
                this.currentX = 0.0;
                this.currentY = 0.0;
            }

            // Zero-latency instant delta dispatch: transmits in <1ms on any thumb motion
            const delta = Math.hypot(this.currentX - this.lastSentX, this.currentY - this.lastSentY);
            if (delta >= 0.005) {
                this.lastSentX = this.currentX;
                this.lastSentY = this.currentY;
                sendStick(this.stickType, this.currentX, this.currentY);
            }
        }

        resetKnob() {
            if (this.base) this.base.classList.remove('active-stick');
            this.knob.style.transition = 'transform 0.10s cubic-bezier(0.2, 0.9, 0.3, 1)';
            this.knob.style.transform = 'translate3d(0px, 0px, 0)';
            setTimeout(() => {
                this.knob.style.transition = '';
            }, 100);

            this.currentX = 0.0;
            this.currentY = 0.0;
            this.lastSentX = 0.0;
            this.lastSentY = 0.0;
            sendStick(this.stickType, 0.0, 0.0);
        }
    }

    // --------------------------------------------------------------------------
    // Fullscreen & Wake-Lock APIs
    // --------------------------------------------------------------------------
    async function requestWakeLock() {
        if ('wakeLock' in navigator) {
            try {
                wakeLock = await navigator.wakeLock.request('screen');
                console.log('[WakeLock] Screen wake lock acquired.');
                wakeLock.addEventListener('release', () => {
                    console.log('[WakeLock] Released.');
                });
            } catch (err) {
                console.warn('[WakeLock] Failed to acquire:', err);
            }
        }
    }

    btnFullscreen.addEventListener('click', () => {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(err => {
                console.warn('Fullscreen request failed:', err);
            });
        } else {
            document.exitFullscreen().catch(err => {});
        }
    });

    // Safety: Reset on page minimize / tab change
    window.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
            releaseAllInputs();
        } else {
            requestWakeLock();
        }
    });

    window.addEventListener('blur', releaseAllInputs);

    // --------------------------------------------------------------------------
    // Bootstrap
    // --------------------------------------------------------------------------
    window.addEventListener('DOMContentLoaded', () => {
        initButtons();
        new VirtualJoystick('left-stick-zone', 'left-stick-knob', 'left_stick');
        new VirtualJoystick('right-stick-zone', 'right-stick-knob', 'right_stick');
    });

})();
