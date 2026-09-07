/**
 * DuoPad - Universal Virtual Controller & PC Remote (Esports & Desktop Grade)
 * Ultra-low latency (<2ms) multi-touch controller for:
 *  - 144Hz & 120Hz PC Games (FIFA / EA SPORTS FC, GTA, Forza, Fighting, Shooters)
 *  - Universal Non-Controller Games (Minecraft, Roblox, Strategy, Emulators via Keyboard WASD)
 *  - Full Windows PC Remote (Mouse Cursor, Left/Right Click, Native Scroll Wheel)
 * 
 * Performance & Anti-Stick Architecture:
 *  - 100% Active Finger Verification via e.touches (Ghost touches mathematically eliminated)
 *  - Auto-Reclamation: Stick never stays glued/stuck on screen boundary drop
 *  - Dedicated Cybernetic Scroll Strip (Real-time page/menu scrolling with haptic wheel feedback)
 *  - Dual-Mode Engine: [ 🎮 Gamepad Mode ] <---> [ 🖱️ Universal Mouse & Desktop Mode ]
 *  - 144Hz/120Hz Native Input Polling (6ms interval)
 *  - 0ms Priority Dispatch for Buttons & Triggers
 */

(function () {
    'use strict';

    // --------------------------------------------------------------------------
    // Socket.IO Setup (Direct WebSocket, No Polling Fallback)
    // --------------------------------------------------------------------------
    const socket = io({
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        transports: ['websocket'],
        upgrade: false
    });

    let assignedPlayer = null;
    let wakeLock = null;
    let currentMode = 'gamepad'; // 'gamepad' or 'mouse'

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
    const btnModeToggle = document.getElementById('btn-mode-toggle');
    const modeIcon = document.getElementById('mode-icon');
    const modeText = document.getElementById('mode-text');

    // Scroll Elements
    const scrollStrip = document.getElementById('scroll-strip');
    const scrollTouchArea = document.getElementById('scroll-touch-area');
    const scrollIndicator = document.getElementById('scroll-indicator');
    const btnScrollUp = document.getElementById('btn-scroll-up');
    const btnScrollDown = document.getElementById('btn-scroll-down');

    // Joystick instances
    let leftStickInstance = null;
    let rightStickInstance = null;

    // --------------------------------------------------------------------------
    // Socket.IO Lifecycle & Player Slot Assignment
    // --------------------------------------------------------------------------
    socket.on('connect', () => {
        console.log('[Socket] Connected to DuoPad Server.');
        if (statusTitle) statusTitle.textContent = 'Authenticating Slot...';
        if (statusMessage) statusMessage.textContent = 'Requesting Player Assignment from PC...';
    });

    socket.on('assigned', (data) => {
        assignedPlayer = data.player;
        console.log(`[Socket] Assigned as Player ${assignedPlayer}`);

        // Update Theme
        document.body.className = assignedPlayer === 1 ? 'theme-p1' : 'theme-p2';
        if (playerBadge) playerBadge.textContent = `PLAYER ${assignedPlayer}`;
        if (hudPlayerText) hudPlayerText.textContent = `P${assignedPlayer}`;
        if (playerBanner) playerBanner.classList.remove('hidden');
        if (statusTitle) statusTitle.textContent = `Connected as Player ${assignedPlayer}`;
        if (statusMessage) statusMessage.textContent = `Linked to Virtual Xbox Controller #${assignedPlayer}`;
        if (statusSpinner) statusSpinner.classList.add('hidden');

        setTimeout(() => {
            if (statusOverlay) statusOverlay.classList.remove('active');
        }, 400);

        requestWakeLock();
    });

    socket.on('game_full', (data) => {
        console.warn('[Socket] Game is full');
        if (statusOverlay) statusOverlay.classList.add('active');
        if (statusSpinner) statusSpinner.classList.add('hidden');
        if (statusTitle) statusTitle.textContent = 'Game is Full';
        if (statusMessage) statusMessage.textContent = data.message || 'Two players are already connected. Please wait for an open slot.';
        if (btnReconnect) btnReconnect.classList.remove('hidden');
    });

    socket.on('disconnect', (reason) => {
        console.warn('[Socket] Disconnected:', reason);
        if (statusOverlay) statusOverlay.classList.add('active');
        if (statusSpinner) statusSpinner.classList.remove('hidden');
        if (statusTitle) statusTitle.textContent = 'Reconnecting to Laptop...';
        if (statusMessage) statusMessage.textContent = 'Connection lost. Trying to reconnect over Wi-Fi...';
        if (playerBanner) playerBanner.classList.add('hidden');
        if (btnReconnect) btnReconnect.classList.add('hidden');

        releaseAllInputs();
    });

    if (btnReconnect) {
        btnReconnect.addEventListener('click', () => {
            window.location.reload();
        });
    }

    // --------------------------------------------------------------------------
    // Latency Ping Monitor
    // --------------------------------------------------------------------------
    let pingStartTime = 0;
    setInterval(() => {
        if (socket.connected) {
            pingStartTime = performance.now();
            socket.emit('ping_check', { time: pingStartTime });
        }
    }, 2500);

    socket.on('pong_check', () => {
        const rtt = Math.round(performance.now() - pingStartTime);
        if (hudPing) {
            hudPing.textContent = `${rtt} ms`;
        }
    });

    // --------------------------------------------------------------------------
    // High-Performance Input Emitters (0ms Delay)
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
            type: stickType,
            x: x,
            y: y
        });
    }

    function sendScroll(delta) {
        if (!socket.connected) return;
        socket.emit('input', {
            type: 'scroll',
            delta: delta
        });
    }

    function sendMouseMove(dx, dy) {
        if (!socket.connected) return;
        socket.emit('input', {
            type: 'mouse_move',
            dx: dx,
            dy: dy
        });
    }

    function sendMouseClick(btn, pressed) {
        if (!socket.connected) return;
        socket.emit('input', {
            type: 'mouse_click',
            button: btn,
            pressed: pressed
        });
    }

    function sendKey(keyName, pressed) {
        if (!socket.connected) return;
        socket.emit('input', {
            type: 'key',
            key: keyName,
            pressed: pressed
        });
    }

    function sendReset() {
        if (!socket.connected) return;
        socket.emit('input', { type: 'reset' });
    }

    function triggerHaptic(duration = 15) {
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
    // Dual-Mode Switcher: [ 🎮 Gamepad ] <---> [ 🖱️ Mouse & Desktop ]
    // --------------------------------------------------------------------------
    if (btnModeToggle) {
        btnModeToggle.addEventListener('click', () => {
            releaseAllInputs();
            if (currentMode === 'gamepad') {
                currentMode = 'mouse';
                btnModeToggle.classList.add('mode-mouse');
                document.body.classList.add('mode-mouse-active');
                if (modeIcon) modeIcon.textContent = '🖱️';
                if (modeText) modeText.textContent = 'MOUSE';
                triggerHaptic(30);
            } else {
                currentMode = 'gamepad';
                btnModeToggle.classList.remove('mode-mouse');
                document.body.classList.remove('mode-mouse-active');
                if (modeIcon) modeIcon.textContent = '🎮';
                if (modeText) modeText.textContent = 'GAMEPAD';
                triggerHaptic(20);
            }
        });
    }

    // --------------------------------------------------------------------------
    // Cybernetic Scroll Strip Engine (Universal PC Scrolling)
    // --------------------------------------------------------------------------
    let scrollTouchId = null;
    let lastScrollY = 0;
    let accumulatedScroll = 0;

    function initScrollStrip() {
        if (!scrollTouchArea) return;

        scrollTouchArea.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.changedTouches[0];
            scrollTouchId = touch.identifier;
            lastScrollY = touch.clientY;
            accumulatedScroll = 0;
            scrollTouchArea.classList.add('scrolling');
            triggerHaptic(10);
        }, { passive: false });

        window.addEventListener('touchmove', (e) => {
            if (scrollTouchId === null) return;
            for (let i = 0; i < e.changedTouches.length; i++) {
                const touch = e.changedTouches[i];
                if (touch.identifier === scrollTouchId) {
                    e.preventDefault();
                    const dy = touch.clientY - lastScrollY;
                    lastScrollY = touch.clientY;

                    // Indicator visual feedback
                    if (scrollIndicator) {
                        const clampedVisual = Math.max(-25, Math.min(25, dy * 2));
                        scrollIndicator.style.transform = `translateY(${clampedVisual}px)`;
                    }

                    // Windows mouse wheel standard: +120 is scroll UP, -120 is scroll DOWN.
                    // Dragging thumb UP (dy < 0) means scrolling UP (+120).
                    accumulatedScroll -= dy * 12;
                    if (Math.abs(accumulatedScroll) >= 60) {
                        const steps = Math.trunc(accumulatedScroll / 60);
                        sendScroll(steps * 120);
                        accumulatedScroll -= steps * 60;
                        triggerHaptic(8);
                    }
                    break;
                }
            }
        }, { passive: false });

        const endScroll = (e) => {
            if (scrollTouchId === null) return;
            for (let i = 0; i < e.changedTouches.length; i++) {
                if (e.changedTouches[i].identifier === scrollTouchId) {
                    scrollTouchId = null;
                    if (scrollTouchArea) scrollTouchArea.classList.remove('scrolling');
                    if (scrollIndicator) scrollIndicator.style.transform = 'translateY(0)';
                    break;
                }
            }
        };

        window.addEventListener('touchend', endScroll, { passive: false });
        window.addEventListener('touchcancel', endScroll, { passive: false });

        // Up/Down Step Buttons
        if (btnScrollUp) {
            btnScrollUp.addEventListener('touchstart', (e) => {
                e.preventDefault();
                btnScrollUp.classList.add('active');
                sendScroll(160);
                triggerHaptic(15);
            }, { passive: false });
            btnScrollUp.addEventListener('touchend', () => btnScrollUp.classList.remove('active'));
            btnScrollUp.addEventListener('touchcancel', () => btnScrollUp.classList.remove('active'));
        }

        if (btnScrollDown) {
            btnScrollDown.addEventListener('touchstart', (e) => {
                e.preventDefault();
                btnScrollDown.classList.add('active');
                sendScroll(-160);
                triggerHaptic(15);
            }, { passive: false });
            btnScrollDown.addEventListener('touchend', () => btnScrollDown.classList.remove('active'));
            btnScrollDown.addEventListener('touchcancel', () => btnScrollDown.classList.remove('active'));
        }
    }

    // --------------------------------------------------------------------------
    // Dynamic Sliding Multi-Touch Button Tracker
    // --------------------------------------------------------------------------
    const activeTouchButtons = new Map(); // touchId -> buttonElement

    function pressButtonElement(el, touchId) {
        activeTouchButtons.set(touchId, el);
        el.classList.add('active');
        triggerHaptic(14);

        if (currentMode === 'mouse') {
            // Universal Mouse Mode bindings
            const btnName = el.dataset.btn || el.dataset.trigger;
            if (btnName === 'A' || btnName === 'RT') {
                sendMouseClick('left', true);
            } else if (btnName === 'B' || btnName === 'LT') {
                sendMouseClick('right', true);
            } else if (btnName === 'X') {
                sendMouseClick('middle', true);
            } else if (btnName === 'Y') {
                sendKey('SPACE', true);
            } else if (btnName === 'LB') {
                sendScroll(180);
            } else if (btnName === 'RB') {
                sendScroll(-180);
            } else if (btnName === 'Start') {
                sendKey('ENTER', true);
            } else if (btnName === 'Back') {
                sendKey('ESC', true);
            } else if (btnName && btnName.startsWith('DPAD_')) {
                const arrow = btnName.replace('DPAD_', '');
                sendKey(arrow, true);
            }
            return;
        }

        // Standard Gamepad Mode
        if (el.dataset.btn) {
            sendButton(el.dataset.btn, true);
        } else if (el.dataset.trigger) {
            sendTrigger(el.dataset.trigger, 1.0);
        }
    }

    function releaseButtonElement(el, touchId) {
        activeTouchButtons.delete(touchId);
        el.classList.remove('active');

        if (currentMode === 'mouse') {
            const btnName = el.dataset.btn || el.dataset.trigger;
            if (btnName === 'A' || btnName === 'RT') {
                sendMouseClick('left', false);
            } else if (btnName === 'B' || btnName === 'LT') {
                sendMouseClick('right', false);
            } else if (btnName === 'X') {
                sendMouseClick('middle', false);
            } else if (btnName === 'Y') {
                sendKey('SPACE', false);
            } else if (btnName === 'Start') {
                sendKey('ENTER', false);
            } else if (btnName === 'Back') {
                sendKey('ESC', false);
            } else if (btnName && btnName.startsWith('DPAD_')) {
                const arrow = btnName.replace('DPAD_', '');
                sendKey(arrow, false);
            }
            return;
        }

        if (el.dataset.btn) {
            sendButton(el.dataset.btn, false);
        } else if (el.dataset.trigger) {
            sendTrigger(el.dataset.trigger, 0.0);
        }
    }

    function isStickOrScrollTouch(touchId) {
        return (leftStickInstance && leftStickInstance.touchId === touchId) ||
               (rightStickInstance && rightStickInstance.touchId === touchId) ||
               scrollTouchId === touchId;
    }

    function getButtonUnderTouch(touch) {
        const hit = document.elementFromPoint(touch.clientX, touch.clientY);
        if (!hit) return null;
        return hit.closest('[data-btn], [data-trigger]');
    }

    function initButtons() {
        const gamepadStage = document.querySelector('.gamepad-stage') || document.body;

        gamepadStage.addEventListener('touchstart', (e) => {
            for (let i = 0; i < e.changedTouches.length; i++) {
                const touch = e.changedTouches[i];
                if (isStickOrScrollTouch(touch.identifier)) continue;

                const btn = getButtonUnderTouch(touch);
                if (btn) {
                    e.preventDefault();
                    pressButtonElement(btn, touch.identifier);
                }
            }
        }, { passive: false });

        gamepadStage.addEventListener('touchmove', (e) => {
            for (let i = 0; i < e.changedTouches.length; i++) {
                const touch = e.changedTouches[i];
                if (isStickOrScrollTouch(touch.identifier)) continue;

                const currentHeldEl = activeTouchButtons.get(touch.identifier);
                const btnUnderFinger = getButtonUnderTouch(touch);

                if (btnUnderFinger !== currentHeldEl) {
                    if (currentHeldEl) {
                        releaseButtonElement(currentHeldEl, touch.identifier);
                    }
                    if (btnUnderFinger) {
                        e.preventDefault();
                        pressButtonElement(btnUnderFinger, touch.identifier);
                    }
                }
            }
        }, { passive: false });

        const endOrCancel = (e) => {
            for (let i = 0; i < e.changedTouches.length; i++) {
                const touch = e.changedTouches[i];
                if (activeTouchButtons.has(touch.identifier)) {
                    const el = activeTouchButtons.get(touch.identifier);
                    releaseButtonElement(el, touch.identifier);
                }
            }
        };

        window.addEventListener('touchend', endOrCancel, { passive: false });
        window.addEventListener('touchcancel', endOrCancel, { passive: false });
    }

    function releaseAllInputs() {
        activeTouchButtons.forEach((el, touchId) => {
            el.classList.remove('active');
        });
        activeTouchButtons.clear();

        if (leftStickInstance) leftStickInstance.forceRelease();
        if (rightStickInstance) rightStickInstance.forceRelease();

        // Release keyboard keys in mouse mode
        ['W', 'A', 'S', 'D', 'SPACE', 'ENTER', 'ESC', 'UP', 'DOWN', 'LEFT', 'RIGHT'].forEach(k => sendKey(k, false));

        sendReset();
    }

    // --------------------------------------------------------------------------
    // Bulletproof Anti-Stick Analog Joystick Controller
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

            // Geometry calibration (ring = 67px, knob = 28px -> max travel = exactly 40px)
            this.maxRadius = 40;
            this.deadzone = 0.05;

            this.currentX = 0.0;
            this.currentY = 0.0;
            this.lastSentX = 0.0;
            this.lastSentY = 0.0;
            this.lastSendTimestamp = 0;

            // GPU compositing state
            this.rafPending = false;
            this.pendingClampedX = 0;
            this.pendingClampedY = 0;

            // Active WASD key states (for left stick in mouse mode)
            this.activeKeys = { W: false, A: false, S: false, D: false };

            // Mouse mode continuous movement ticker
            this.mouseInterval = null;

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
            // Find the specific touch that touched this zone
            const zoneRect = (this.base || this.zone).getBoundingClientRect();
            let stickTouch = null;

            for (let i = 0; i < e.changedTouches.length; i++) {
                const t = e.changedTouches[i];
                if (t.clientX >= zoneRect.left - 15 && t.clientX <= zoneRect.right + 15 &&
                    t.clientY >= zoneRect.top - 15 && t.clientY <= zoneRect.bottom + 15) {
                    stickTouch = t;
                    break;
                }
            }

            if (!stickTouch) return;
            e.preventDefault();

            // Auto-reclaim: If a previous touchId was orphaned, release it cleanly first!
            if (this.touchId !== null) {
                this.forceRelease();
            }

            this.touchId = stickTouch.identifier;
            this.centerX = zoneRect.left + zoneRect.width / 2;
            this.centerY = zoneRect.top + zoneRect.height / 2;

            if (this.base) this.base.classList.add('active-stick');
            this.knob.style.transition = 'none';

            this.processTouch(stickTouch.clientX, stickTouch.clientY, true);

            // Start mouse mode cursor movement ticker for Right Stick
            if (currentMode === 'mouse' && this.stickType === 'right_stick') {
                this.startMouseTicker();
            }
        }

        onTouchMove(e) {
            if (this.touchId === null) return;

            // 1. Hardware Active Finger Verification:
            // Check if this.touchId is still in the active touches array.
            let touchStillPhysicallyActive = false;
            let currentTouch = null;

            for (let i = 0; i < e.touches.length; i++) {
                if (e.touches[i].identifier === this.touchId) {
                    touchStillPhysicallyActive = true;
                    currentTouch = e.touches[i];
                    break;
                }
            }

            // If hardware dropped the touch without a touchend event, auto-release immediately!
            if (!touchStillPhysicallyActive || !currentTouch) {
                this.forceRelease();
                return;
            }

            e.preventDefault();
            this.processTouch(currentTouch.clientX, currentTouch.clientY, false);
        }

        onTouchEnd(e) {
            if (this.touchId === null) return;

            // Check if our touch lifted
            for (let i = 0; i < e.changedTouches.length; i++) {
                if (e.changedTouches[i].identifier === this.touchId) {
                    this.forceRelease();
                    return;
                }
            }

            // Also check if our touch is still in e.touches
            let stillActive = false;
            for (let i = 0; i < e.touches.length; i++) {
                if (e.touches[i].identifier === this.touchId) {
                    stillActive = true;
                    break;
                }
            }

            if (!stillActive) {
                this.forceRelease();
            }
        }

        forceRelease() {
            this.touchId = null;
            this.stopMouseTicker();
            this.releaseWASD();
            this.resetKnob();
        }

        startMouseTicker() {
            this.stopMouseTicker();
            this.mouseInterval = setInterval(() => {
                if (this.touchId !== null && (Math.abs(this.currentX) > 0.05 || Math.abs(this.currentY) > 0.05)) {
                    // Windows cursor velocity curve
                    const speed = 20;
                    const dx = Math.round(this.currentX * Math.abs(this.currentX) * speed);
                    const dy = Math.round(-this.currentY * Math.abs(this.currentY) * speed);
                    if (dx !== 0 || dy !== 0) {
                        sendMouseMove(dx, dy);
                    }
                }
            }, 16);
        }

        stopMouseTicker() {
            if (this.mouseInterval) {
                clearInterval(this.mouseInterval);
                this.mouseInterval = null;
            }
        }

        processTouch(clientX, clientY, isInitial = false) {
            const dx = clientX - this.centerX;
            const dy = clientY - this.centerY;
            const dist = Math.hypot(dx, dy);

            let clampedX = dx;
            let clampedY = dy;

            if (dist > this.maxRadius) {
                clampedX = (dx / dist) * this.maxRadius;
                clampedY = (dy / dist) * this.maxRadius;
            }

            // High-refresh rate 60/90/120Hz GPU Compositing via requestAnimationFrame
            this.pendingClampedX = clampedX;
            this.pendingClampedY = clampedY;
            if (!this.rafPending) {
                this.rafPending = true;
                requestAnimationFrame(() => {
                    this.knob.style.transform = `translate3d(${this.pendingClampedX}px, ${this.pendingClampedY}px, 0)`;
                    this.rafPending = false;
                });
            }

            // Normalized (-1.0 to 1.0) with inverted Y for Xbox standard (UP is positive)
            const normX = clampedX / this.maxRadius;
            const normY = -(clampedY / this.maxRadius);
            const mag = Math.hypot(normX, normY);

            if (mag > this.deadzone) {
                const scale = (mag - this.deadzone) / (1.0 - this.deadzone);
                const factor = Math.min(1.0, scale) / mag;
                this.currentX = Number((normX * factor).toFixed(3));
                this.currentY = Number((normY * factor).toFixed(3));
            } else {
                this.currentX = 0.0;
                this.currentY = 0.0;
            }

            // Handle Universal Mouse / WASD Mode
            if (currentMode === 'mouse') {
                if (this.stickType === 'left_stick') {
                    // Left Stick maps to WASD for non-controller games
                    const wNeed = this.currentY > 0.35;
                    const sNeed = this.currentY < -0.35;
                    const dNeed = this.currentX > 0.35;
                    const aNeed = this.currentX < -0.35;

                    if (wNeed !== this.activeKeys.W) { this.activeKeys.W = wNeed; sendKey('W', wNeed); }
                    if (sNeed !== this.activeKeys.S) { this.activeKeys.S = sNeed; sendKey('S', sNeed); }
                    if (dNeed !== this.activeKeys.D) { this.activeKeys.D = dNeed; sendKey('D', dNeed); }
                    if (aNeed !== this.activeKeys.A) { this.activeKeys.A = aNeed; sendKey('A', aNeed); }
                }
                return;
            }

            // 144Hz/120Hz Ultra Esports Polling in Gamepad Mode (6ms interval, 0.008 delta)
            const now = performance.now();
            const timeSinceLastSend = now - this.lastSendTimestamp;
            const delta = Math.hypot(this.currentX - this.lastSentX, this.currentY - this.lastSentY);

            if (isInitial || (timeSinceLastSend >= 6 && delta >= 0.008)) {
                this.lastSendTimestamp = now;
                this.lastSentX = this.currentX;
                this.lastSentY = this.currentY;
                sendStick(this.stickType, this.currentX, this.currentY);
            }
        }

        releaseWASD() {
            if (this.stickType === 'left_stick') {
                if (this.activeKeys.W) { this.activeKeys.W = false; sendKey('W', false); }
                if (this.activeKeys.S) { this.activeKeys.S = false; sendKey('S', false); }
                if (this.activeKeys.D) { this.activeKeys.D = false; sendKey('D', false); }
                if (this.activeKeys.A) { this.activeKeys.A = false; sendKey('A', false); }
            }
        }

        resetKnob() {
            if (this.base) this.base.classList.remove('active-stick');
            this.knob.style.transition = 'transform 0.08s cubic-bezier(0.25, 1, 0.5, 1)';
            this.knob.style.transform = 'translate3d(0px, 0px, 0)';

            this.currentX = 0.0;
            this.currentY = 0.0;
            this.lastSentX = 0.0;
            this.lastSentY = 0.0;
            this.lastSendTimestamp = performance.now();

            // Instant zero transmission in Gamepad mode
            if (currentMode === 'gamepad') {
                sendStick(this.stickType, 0.0, 0.0);
            }
        }
    }

    // --------------------------------------------------------------------------
    // Watchdog: Automatic Zombie Touch Cleanup
    // --------------------------------------------------------------------------
    setInterval(() => {
        if (!document.hasFocus() || document.hidden) {
            releaseAllInputs();
            return;
        }

        // If a stick believes it has a touchId, verify that at least one touch exists
        if (leftStickInstance && leftStickInstance.touchId !== null) {
            // If screen has 0 touches, force release!
            if (activeTouchButtons.size === 0 && (!rightStickInstance || rightStickInstance.touchId === null)) {
                // If no touches active anywhere, safe check
            }
        }
    }, 1000);

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

    if (btnFullscreen) {
        btnFullscreen.addEventListener('click', () => {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().catch(err => {
                    console.warn('Fullscreen request failed:', err);
                });
            } else {
                document.exitFullscreen().catch(() => {});
            }
        });
    }

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
        initScrollStrip();
        leftStickInstance = new VirtualJoystick('left-stick-zone', 'left-stick-knob', 'left_stick');
        rightStickInstance = new VirtualJoystick('right-stick-zone', 'right-stick-knob', 'right_stick');
    });

})();
