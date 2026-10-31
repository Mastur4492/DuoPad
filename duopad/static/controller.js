/**
 * DuoPad - Esports Ultra-Low Latency Mobile Gamepad Engine
 * Unified Pointer & Multi-touch controller optimized for 2-Player Co-Op:
 *  - Supports both Mobile Touch & Desktop PC Mouse testing
 *  - 0ms priority dispatch for buttons & triggers (zero lag)
 *  - 120Hz smooth joystick polling with precision circular deadzone
 *  - Anti-stick auto-reclamation engine (eliminates ghost touches)
 *  - Real-time latency HUD monitor
 *  - Dynamic Player 1 (Cyan) & Player 2 (Magenta) theme switching
 * 100% Free and Open Source for Gamers.
 */

(function () {
    'use strict';

    // --------------------------------------------------------------------------
    // Socket.IO Setup (WebSocket First with Long-Polling Fallback)
    // --------------------------------------------------------------------------
    const socket = io({
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 400,
        transports: ['websocket', 'polling'],
        upgrade: true,
        timeout: 8000
    });

    let assignedPlayer = 1;
    let wakeLock = null;

    // DOM Elements
    const statusOverlay = document.getElementById('status-overlay');
    const statusSpinner = document.getElementById('status-spinner');
    const statusTitle = document.getElementById('status-title');
    const statusMessage = document.getElementById('status-message');
    const playerBanner = document.getElementById('player-banner');
    const playerBadge = document.getElementById('player-badge');
    const btnReconnect = document.getElementById('btn-reconnect');
    const hudPlayerText = document.getElementById('hud-player-text');
    const hudPing = document.getElementById('hud-ping');
    const btnFullscreen = document.getElementById('btn-fullscreen');

    // Joysticks
    let leftStick = null;
    let rightStick = null;

    // --------------------------------------------------------------------------
    // Socket Connection & Player Slot Assignment
    // --------------------------------------------------------------------------
    socket.on('connect', () => {
        console.log('[DuoPad] Connected to PC server.');
        if (statusTitle) statusTitle.textContent = 'Authenticating Slot...';
        if (statusMessage) statusMessage.textContent = 'Acquiring Player Slot from PC...';
    });

    socket.on('assigned', (data) => {
        assignedPlayer = (data && data.player) ? data.player : 1;
        console.log(`[DuoPad] Assigned as Player ${assignedPlayer}`);

        // Dynamic theme switching: Player 1 = Cyan, Player 2 = Magenta
        document.body.className = assignedPlayer === 1 ? 'theme-p1' : 'theme-p2';

        if (playerBadge) playerBadge.textContent = `PLAYER ${assignedPlayer}`;
        if (hudPlayerText) hudPlayerText.textContent = `P${assignedPlayer}`;
        if (playerBanner) playerBanner.classList.remove('hidden');
        if (statusTitle) statusTitle.textContent = `Connected as Player ${assignedPlayer}`;
        if (statusMessage) statusMessage.textContent = `Linked to Virtual Xbox 360 Controller #${assignedPlayer}`;
        if (statusSpinner) statusSpinner.classList.add('hidden');

        setTimeout(() => {
            if (statusOverlay) statusOverlay.classList.remove('active');
        }, 250);

        requestWakeLock();
    });

    function handleLobbyFull(data) {
        console.warn('[DuoPad] Both player slots are occupied.');
        if (statusOverlay) statusOverlay.classList.add('active');
        if (statusSpinner) statusSpinner.classList.add('hidden');
        if (statusTitle) statusTitle.textContent = 'Game is Full';
        if (statusMessage) statusMessage.textContent = (data && data.message) ? data.message : 'Two players are already connected.';
        if (btnReconnect) btnReconnect.classList.remove('hidden');
    }

    socket.on('game_full', handleLobbyFull);
    socket.on('lobby_full', handleLobbyFull);

    socket.on('disconnect', (reason) => {
        console.warn('[DuoPad] Disconnected:', reason);
        if (statusOverlay) statusOverlay.classList.add('active');
        if (statusSpinner) statusSpinner.classList.remove('hidden');
        if (statusTitle) statusTitle.textContent = 'Reconnecting to PC...';
        if (statusMessage) statusMessage.textContent = 'Searching for DuoPad server over local Wi-Fi...';
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
    // Real-Time Latency Ping Monitor
    // --------------------------------------------------------------------------
    let pingStartTimestamp = 0;
    setInterval(() => {
        if (socket.connected) {
            pingStartTimestamp = performance.now();
            socket.emit('ping_check', { time: pingStartTimestamp });
        }
    }, 2000);

    socket.on('pong_check', (data) => {
        const sentTime = (data && data.time) ? data.time : pingStartTimestamp;
        const rtt = Math.max(1, Math.round(performance.now() - sentTime));
        if (hudPing) {
            hudPing.textContent = `${rtt} ms`;
        }
    });

    // --------------------------------------------------------------------------
    // Instant Priority Input Emitters (Sub-millisecond Dispatch)
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

    function sendReset() {
        if (!socket.connected) return;
        socket.emit('input', { type: 'reset' });
    }

    function triggerHaptic(duration = 12) {
        if (window.Android && window.Android.vibrate) {
            try { window.Android.vibrate(duration); return; } catch (e) {}
        }
        if (navigator.vibrate) {
            try { navigator.vibrate(duration); } catch (e) {}
        }
    }

    // --------------------------------------------------------------------------
    // Unified Multi-Pointer & Touch Button Tracker (Mobile + PC Mouse)
    // --------------------------------------------------------------------------
    const activePointers = new Map(); // pointerId -> buttonElement

    function pressButtonElement(el, pointerId) {
        if (!el) return;
        activePointers.set(pointerId, el);
        el.classList.add('active');
        triggerHaptic(12);

        if (el.dataset.btn) {
            sendButton(el.dataset.btn, true);
        } else if (el.dataset.trigger) {
            sendTrigger(el.dataset.trigger, 1.0);
        }
    }

    function releaseButtonElement(el, pointerId) {
        if (!el) return;
        activePointers.delete(pointerId);
        el.classList.remove('active');

        if (el.dataset.btn) {
            sendButton(el.dataset.btn, false);
        } else if (el.dataset.trigger) {
            sendTrigger(el.dataset.trigger, 0.0);
        }
    }

    function isStickPointer(pointerId) {
        return (leftStick && leftStick.pointerId === pointerId) ||
               (rightStick && rightStick.pointerId === pointerId);
    }

    function getButtonUnderPoint(x, y) {
        const hit = document.elementFromPoint(x, y);
        if (!hit) return null;
        return hit.closest('[data-btn], [data-trigger]');
    }

    function initButtons() {
        const stage = document.querySelector('.gamepad-stage') || document.body;

        // Modern Unified Pointer Events (Mouse, Touch & Stylus)
        stage.addEventListener('pointerdown', (e) => {
            if (isStickPointer(e.pointerId)) return;
            const btn = getButtonUnderPoint(e.clientX, e.clientY);
            if (btn) {
                e.preventDefault();
                try { btn.setPointerCapture(e.pointerId); } catch (_) {}
                pressButtonElement(btn, e.pointerId);
            }
        }, { passive: false });

        stage.addEventListener('pointermove', (e) => {
            if (isStickPointer(e.pointerId)) return;
            if (!activePointers.has(e.pointerId)) return;

            const currentHeld = activePointers.get(e.pointerId);
            const btnUnder = getButtonUnderPoint(e.clientX, e.clientY);

            if (btnUnder !== currentHeld) {
                if (currentHeld) {
                    releaseButtonElement(currentHeld, e.pointerId);
                }
                if (btnUnder) {
                    e.preventDefault();
                    pressButtonElement(btnUnder, e.pointerId);
                }
            }
        }, { passive: false });

        const handlePointerEnd = (e) => {
            if (activePointers.has(e.pointerId)) {
                const el = activePointers.get(e.pointerId);
                try { el.releasePointerCapture(e.pointerId); } catch (_) {}
                releaseButtonElement(el, e.pointerId);
            }
        };

        window.addEventListener('pointerup', handlePointerEnd, { passive: false });
        window.addEventListener('pointercancel', handlePointerEnd, { passive: false });

        // Touch event fallback for older WebKit / browsers
        stage.addEventListener('touchstart', (e) => {
            for (let i = 0; i < e.changedTouches.length; i++) {
                const touch = e.changedTouches[i];
                if (isStickPointer(touch.identifier)) continue;
                const btn = getButtonUnderPoint(touch.clientX, touch.clientY);
                if (btn && !activePointers.has(touch.identifier)) {
                    e.preventDefault();
                    pressButtonElement(btn, touch.identifier);
                }
            }
        }, { passive: false });

        stage.addEventListener('touchmove', (e) => {
            for (let i = 0; i < e.changedTouches.length; i++) {
                const touch = e.changedTouches[i];
                if (isStickPointer(touch.identifier)) continue;
                const currentHeld = activePointers.get(touch.identifier);
                const btnUnder = getButtonUnderPoint(touch.clientX, touch.clientY);
                if (btnUnder !== currentHeld) {
                    if (currentHeld) releaseButtonElement(currentHeld, touch.identifier);
                    if (btnUnder) {
                        e.preventDefault();
                        pressButtonElement(btnUnder, touch.identifier);
                    }
                }
            }
        }, { passive: false });

        const handleTouchEnd = (e) => {
            for (let i = 0; i < e.changedTouches.length; i++) {
                const touch = e.changedTouches[i];
                if (activePointers.has(touch.identifier)) {
                    const el = activePointers.get(touch.identifier);
                    releaseButtonElement(el, touch.identifier);
                }
            }
        };

        window.addEventListener('touchend', handleTouchEnd, { passive: false });
        window.addEventListener('touchcancel', handleTouchEnd, { passive: false });
    }

    function releaseAllInputs() {
        activePointers.forEach((el, pId) => {
            el.classList.remove('active');
        });
        activePointers.clear();

        if (leftStick) leftStick.forceRelease();
        if (rightStick) rightStick.forceRelease();

        sendReset();
    }

    // --------------------------------------------------------------------------
    // Precision Analog Joystick Controller (Ultra-Low Latency & Anti-Stick)
    // Supports both Touch (Mobile) and Mouse/Trackpad (Desktop PC Testing)
    // --------------------------------------------------------------------------
    class VirtualJoystick {
        constructor(zoneId, knobId, stickType) {
            this.zone = document.getElementById(zoneId);
            this.knob = document.getElementById(knobId);
            this.base = this.zone ? (this.zone.querySelector('.stick-ring') || this.zone) : null;
            this.stickType = stickType; // 'left_stick' or 'right_stick'

            this.pointerId = null;
            this.centerX = 0;
            this.centerY = 0;
            this.maxRadius = 42;
            this.deadzone = 0.05;

            this.currentX = 0.0;
            this.currentY = 0.0;
            this.lastSentX = 0.0;
            this.lastSentY = 0.0;
            this.lastSendTime = 0;

            this.initEvents();
        }

        initEvents() {
            if (!this.zone) return;

            // Pointer Events (Unifies Mobile Multi-touch & Desktop Mouse Testing)
            this.zone.addEventListener('pointerdown', (e) => this.onPointerDown(e), { passive: false });
            window.addEventListener('pointermove', (e) => this.onPointerMove(e), { passive: false });
            window.addEventListener('pointerup', (e) => this.onPointerUp(e), { passive: false });
            window.addEventListener('pointercancel', (e) => this.onPointerUp(e), { passive: false });

            // Touch events fallback
            this.zone.addEventListener('touchstart', (e) => this.onTouchStart(e), { passive: false });
            window.addEventListener('touchmove', (e) => this.onTouchMove(e), { passive: false });
            window.addEventListener('touchend', (e) => this.onTouchEnd(e), { passive: false });
            window.addEventListener('touchcancel', (e) => this.onTouchEnd(e), { passive: false });
        }

        onPointerDown(e) {
            e.preventDefault();
            if (this.pointerId !== null) {
                this.forceRelease();
            }

            this.pointerId = e.pointerId;
            try { this.zone.setPointerCapture(e.pointerId); } catch (_) {}

            const rect = (this.base || this.zone).getBoundingClientRect();
            this.maxRadius = Math.max(34, (rect.width - 48) / 2 + 8);
            this.centerX = rect.left + rect.width / 2;
            this.centerY = rect.top + rect.height / 2;

            if (this.base) this.base.classList.add('active-stick');
            this.knob.style.transition = 'none';

            this.processCoords(e.clientX, e.clientY, true);
        }

        onPointerMove(e) {
            if (this.pointerId === null || e.pointerId !== this.pointerId) return;
            e.preventDefault();
            this.processCoords(e.clientX, e.clientY, false);
        }

        onPointerUp(e) {
            if (this.pointerId === null || e.pointerId !== this.pointerId) return;
            try { this.zone.releasePointerCapture(e.pointerId); } catch (_) {}
            this.forceRelease();
        }

        onTouchStart(e) {
            if (this.pointerId !== null) return;
            const rect = (this.base || this.zone).getBoundingClientRect();
            let stickTouch = null;

            for (let i = 0; i < e.changedTouches.length; i++) {
                const t = e.changedTouches[i];
                if (t.clientX >= rect.left - 24 && t.clientX <= rect.right + 24 &&
                    t.clientY >= rect.top - 24 && t.clientY <= rect.bottom + 24) {
                    stickTouch = t;
                    break;
                }
            }

            if (!stickTouch) return;
            e.preventDefault();

            this.pointerId = stickTouch.identifier;
            this.maxRadius = Math.max(34, (rect.width - 48) / 2 + 8);
            this.centerX = rect.left + rect.width / 2;
            this.centerY = rect.top + rect.height / 2;

            if (this.base) this.base.classList.add('active-stick');
            this.knob.style.transition = 'none';

            this.processCoords(stickTouch.clientX, stickTouch.clientY, true);
        }

        onTouchMove(e) {
            if (this.pointerId === null) return;
            let currentTouch = null;
            for (let i = 0; i < e.touches.length; i++) {
                if (e.touches[i].identifier === this.pointerId) {
                    currentTouch = e.touches[i];
                    break;
                }
            }
            if (!currentTouch) {
                this.forceRelease();
                return;
            }
            e.preventDefault();
            this.processCoords(currentTouch.clientX, currentTouch.clientY, false);
        }

        onTouchEnd(e) {
            if (this.pointerId === null) return;
            for (let i = 0; i < e.changedTouches.length; i++) {
                if (e.changedTouches[i].identifier === this.pointerId) {
                    this.forceRelease();
                    return;
                }
            }
        }

        forceRelease() {
            this.pointerId = null;
            if (this.base) this.base.classList.remove('active-stick');

            this.knob.style.transition = 'transform 0.08s cubic-bezier(0.25, 1, 0.5, 1)';
            this.knob.style.transform = 'translate3d(0px, 0px, 0)';

            this.currentX = 0.0;
            this.currentY = 0.0;
            this.lastSentX = 0.0;
            this.lastSentY = 0.0;
            this.lastSendTime = performance.now();

            sendStick(this.stickType, 0.0, 0.0);
        }

        processCoords(clientX, clientY, isInitial = false) {
            const dx = clientX - this.centerX;
            const dy = clientY - this.centerY;
            const dist = Math.hypot(dx, dy);

            let clampedX = dx;
            let clampedY = dy;

            if (dist > this.maxRadius) {
                clampedX = (dx / dist) * this.maxRadius;
                clampedY = (dy / dist) * this.maxRadius;
            }

            // Direct GPU layer render for silky smooth 120Hz display refresh
            this.knob.style.transform = `translate3d(${clampedX}px, ${clampedY}px, 0)`;

            // Normalized float (-1.0 to 1.0) with inverted Y for Xbox standard (UP is positive)
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

            // 120Hz matched dynamic polling (8ms throttle, 0.010 threshold)
            const now = performance.now();
            const timeSinceLastSend = now - this.lastSendTime;
            const delta = Math.hypot(this.currentX - this.lastSentX, this.currentY - this.lastSentY);

            if (isInitial || (timeSinceLastSend >= 8 && delta >= 0.010)) {
                this.lastSendTime = now;
                this.lastSentX = this.currentX;
                this.lastSentY = this.currentY;
                sendStick(this.stickType, this.currentX, this.currentY);
            }
        }
    }

    // --------------------------------------------------------------------------
    // Watchdog: Automatic Zombie Touch & Visibility Reclamation
    // --------------------------------------------------------------------------
    window.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
            releaseAllInputs();
        } else {
            requestWakeLock();
        }
    });

    window.addEventListener('blur', releaseAllInputs);

    // Prevent default touch gestures that interfere with gaming
    document.addEventListener('contextmenu', (e) => e.preventDefault(), { passive: false });
    document.addEventListener('gesturestart', (e) => e.preventDefault(), { passive: false });

    // --------------------------------------------------------------------------
    // Fullscreen & Wake-Lock APIs
    // --------------------------------------------------------------------------
    async function requestWakeLock() {
        if ('wakeLock' in navigator) {
            try {
                wakeLock = await navigator.wakeLock.request('screen');
                console.log('[DuoPad] Screen WakeLock acquired.');
            } catch (err) {
                console.warn('[DuoPad] WakeLock request:', err);
            }
        }
    }

    if (btnFullscreen) {
        btnFullscreen.addEventListener('click', (e) => {
            e.stopPropagation();
            if (!document.fullscreenElement) {
                const el = document.documentElement;
                if (el.requestFullscreen) {
                    el.requestFullscreen().catch(() => {});
                } else if (el.webkitRequestFullscreen) {
                    el.webkitRequestFullscreen();
                }
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen().catch(() => {});
                }
            }
        });
    }

    // --------------------------------------------------------------------------
    // Initialization
    // --------------------------------------------------------------------------
    window.addEventListener('DOMContentLoaded', () => {
        initButtons();
        leftStick = new VirtualJoystick('left-stick-zone', 'left-stick-knob', 'left_stick');
        rightStick = new VirtualJoystick('right-stick-zone', 'right-stick-knob', 'right_stick');
    });

})();
