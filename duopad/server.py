#!/usr/bin/env python3
"""
DuoPad - Ultra-Low Latency Dual Phone Gamepad Server
Connects up to two smartphones over local Wi-Fi to control two separate
persistent virtual Xbox 360 controllers on Windows via ViGEmBus and vgamepad.
Uses high-performance aiohttp + python-socketio for sub-millisecond WebSocket latency.
100% Free and Open Source for the Gaming Industry.
"""

import os
import sys
import time
import socket
import atexit
import asyncio
import ctypes

# Ensure Windows console handles UTF-8 / emojis properly without crash
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import qrcode
from aiohttp import web
import socketio
import vgamepad as vg

# ---------------------------------------------------------------------------
# High-Performance Async SocketIO & Aiohttp Setup
# ---------------------------------------------------------------------------
sio = socketio.AsyncServer(
    async_mode='aiohttp',
    cors_allowed_origins='*',
    ping_timeout=10,
    ping_interval=5,
    http_compression=False,
    async_handlers=False
)

@web.middleware
async def no_cache_middleware(request, handler):
    resp = await handler(request)
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

app = web.Application(middlewares=[no_cache_middleware])
sio.attach(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

# ---------------------------------------------------------------------------
# Global Controller & Multiplayer State
# ---------------------------------------------------------------------------
controllers = {}
connected_players = {1: None, 2: None}  # maps player_number (1, 2) -> sid
sid_to_player = {}                      # maps sid -> player_number

# Normalized XUSB Button mappings
BUTTON_MAP = {
    'A': vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    'B': vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    'X': vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    'Y': vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    'LB': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    'RB': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    'START': vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    'BACK': vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    'GUIDE': vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
    'GUID': vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
    'DPAD_UP': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    'DPAD_DOWN': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    'DPAD_LEFT': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    'DPAD_RIGHT': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
    'L3': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    'LS': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    'R3': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    'RS': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
}

# ---------------------------------------------------------------------------
# Native Windows Mouse & Keyboard Emulation (Universal PC Desktop Control)
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
    user32.mouse_event.restype = None
    user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]
    user32.keybd_event.restype = None
else:
    user32 = None

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800

VK_MAP = {
    'W': 0x57, 'A': 0x41, 'S': 0x53, 'D': 0x44,
    'UP': 0x26, 'DOWN': 0x28, 'LEFT': 0x25, 'RIGHT': 0x27,
    'SPACE': 0x20, 'ENTER': 0x0D, 'ESC': 0x1B, 'ESCAPE': 0x1B,
    'SHIFT': 0x10, 'CTRL': 0x11, 'ALT': 0x12, 'TAB': 0x09,
    'E': 0x45, 'Q': 0x51, 'R': 0x52, 'F': 0x46, 'C': 0x43,
    'Z': 0x5A, 'X': 0x58, 'V': 0x56, 'B': 0x42, 'J': 0x4A, 'K': 0x4B,
    'PAGEUP': 0x21, 'PAGEDOWN': 0x22,
    '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34
}
KEYEVENTF_KEYUP = 0x0002

def init_virtual_gamepads():
    """
    Initialize persistent virtual Xbox 360 controllers on Windows.
    Controllers remain persistently connected to Windows so games (EA Sports FC 24/25/26,
    FIFA, GTA V, Forza) never lose the controller or pause when phones reconnect.
    """
    print("[*] Initializing persistent virtual Xbox 360 controllers on Windows...")
    for p_num in (1, 2):
        if p_num in controllers:
            continue
        try:
            ctrl = vg.VX360Gamepad()
            ctrl.reset()
            ctrl.update()
            controllers[p_num] = ctrl
            print(f"🎮 [ViGEmBus] Virtual Xbox 360 Controller #{p_num} plugged into Windows (Slot {p_num})!")
            time.sleep(0.35)  # Required for Windows PnP kernel bus enumeration
        except Exception as e:
            print(f"❌ [ViGEmBus] Failed to initialize Controller #{p_num}: {e}")

def ensure_controller(p_num):
    """Ensure a virtual controller exists for player p_num."""
    if p_num in controllers:
        return controllers[p_num]
    try:
        ctrl = vg.VX360Gamepad()
        ctrl.reset()
        ctrl.update()
        controllers[p_num] = ctrl
        print(f"🎮 [ViGEmBus] Virtual Xbox 360 Controller #{p_num} plugged into Windows!")
        return ctrl
    except Exception as e:
        print(f"❌ [ViGEmBus] Error ensuring Controller #{p_num}: {e}")
        return None

def cleanup_controllers():
    """Detach all connected controllers on server shutdown."""
    print("\n[*] Server stopping. Detaching controllers from Windows...")
    for pid, ctrl in list(controllers.items()):
        try:
            ctrl.reset()
            ctrl.update()
        except Exception:
            pass
        del ctrl
    controllers.clear()

atexit.register(cleanup_controllers)

def get_local_ip():
    """Detect local IPv4 address on the Wi-Fi/LAN network."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# ---------------------------------------------------------------------------
# HTTP Routes
# ---------------------------------------------------------------------------
async def handle_index(request):
    index_path = os.path.join(TEMPLATES_DIR, 'index.html')
    resp = web.FileResponse(index_path)
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

async def handle_status(request):
    return web.json_response({
        'status': 'online',
        'player1_connected': connected_players[1] is not None,
        'player2_connected': connected_players[2] is not None,
        'controllers_initialized': len(controllers),
        'active_controllers': list(controllers.keys())
    })

async def handle_health(request):
    return web.Response(text="OK", content_type="text/plain")

app.router.add_get('/', handle_index)
app.router.add_get('/status', handle_status)
app.router.add_get('/health', handle_health)
app.router.add_static('/static', STATIC_DIR, name='static')

# ---------------------------------------------------------------------------
# WebSocket Events
# ---------------------------------------------------------------------------
@sio.on('connect')
async def handle_connect(sid, environ):
    client_ip = environ.get('REMOTE_ADDR', 'Unknown')
    
    assigned_player = None
    if connected_players[1] is None:
        assigned_player = 1
    elif connected_players[2] is None:
        assigned_player = 2

    if assigned_player is not None:
        connected_players[assigned_player] = sid
        sid_to_player[sid] = assigned_player
        
        # Ensure the persistent virtual controller is active
        ctrl = ensure_controller(assigned_player)
        if ctrl:
            try:
                ctrl.reset()
                ctrl.update()
            except Exception:
                pass
        
        await sio.emit('assigned', {
            'status': 'connected',
            'player': assigned_player,
            'message': f'Connected as Player {assigned_player}'
        }, to=sid)
        
        print(f"🟢 [CONNECT] Player {assigned_player} connected from {client_ip} (sid: {sid[:8]})")
        _print_player_status()
    else:
        # 3rd+ phone trying to connect
        await sio.emit('game_full', {
            'status': 'full',
            'message': 'Game is full! Two players are already connected.'
        }, to=sid)
        print(f"⚠️ [REJECTED] Device attempted to connect from {client_ip} (sid: {sid[:8]}). Game is full.")

@sio.on('disconnect')
async def handle_disconnect(sid):
    if sid in sid_to_player:
        player_num = sid_to_player.pop(sid)
        connected_players[player_num] = None
        
        # Neutralize controller inputs so game character stops moving,
        # but keep the controller plugged into Windows for instant reconnect
        ctrl = controllers.get(player_num)
        if ctrl:
            try:
                ctrl.reset()
                ctrl.update()
            except Exception:
                pass
            
        print(f"🔴 [DISCONNECT] Player {player_num} disconnected. Slot {player_num} freed.")
        _print_player_status()

@sio.on('input')
def handle_input(sid, data):
    """
    Handle real-time controller inputs from connected phones with zero lag (<1ms).
    Fast-paths Gamepad XInput inputs directly to ViGEmBus kernel driver.
    """
    player_num = sid_to_player.get(sid)
    if player_num and player_num in controllers:
        ctrl = controllers[player_num]
        try:
            if isinstance(data, list):
                # Check if it's a compact tuple packet like ['ls', x, y] or a batch of items
                if data and isinstance(data[0], str):
                    if _apply_gamepad_item(ctrl, data):
                        ctrl.update()
                        return
                else:
                    for item in data:
                        _apply_gamepad_item(ctrl, item)
                    ctrl.update()
                    return

            if _apply_gamepad_item(ctrl, data):
                ctrl.update()
                return
        except Exception as e:
            print(f"[!] Input processing error for Player {player_num}: {e}")
        return

    # Fallback to Universal Desktop Mouse / Keyboard emulation
    inp_type = str(data.get('type') or data.get('t', '')).lower() if isinstance(data, dict) else ''
    try:
        if inp_type == 'scroll':
            delta = int(data.get('delta', 0))
            if user32 and delta != 0:
                dw_data = ctypes.c_uint32(delta & 0xFFFFFFFF).value
                user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, dw_data, 0)
            return

        elif inp_type == 'mouse_move':
            dx = int(data.get('dx', 0))
            dy = int(data.get('dy', 0))
            if user32 and (dx != 0 or dy != 0):
                user32.mouse_event(MOUSEEVENTF_MOVE, dx, dy, 0, 0)
            return

        elif inp_type == 'mouse_click':
            btn = str(data.get('button', 'left')).lower()
            pressed = bool(data.get('pressed', False))
            if user32:
                if btn == 'left':
                    flag = MOUSEEVENTF_LEFTDOWN if pressed else MOUSEEVENTF_LEFTUP
                elif btn == 'right':
                    flag = MOUSEEVENTF_RIGHTDOWN if pressed else MOUSEEVENTF_RIGHTUP
                elif btn == 'middle':
                    flag = MOUSEEVENTF_MIDDLEDOWN if pressed else MOUSEEVENTF_MIDDLEUP
                else:
                    flag = 0
                if flag:
                    user32.mouse_event(flag, 0, 0, 0, 0)
            return

        elif inp_type == 'key':
            k = str(data.get('key', '')).upper()
            pressed = bool(data.get('pressed', False))
            if user32 and k in VK_MAP:
                vk = VK_MAP[k]
                flags = 0 if pressed else KEYEVENTF_KEYUP
                user32.keybd_event(vk, 0, flags, 0)
            return
    except Exception:
        pass

def _apply_gamepad_item(ctrl, item):
    """Sub-microsecond helper to update a single virtual Xbox 360 controller control."""
    # Fast path for compact tuple/list format: ['b', 'A', 1], ['ls', x, y], ['rs', x, y], ['t', 'RT', 1.0], ['r']
    if isinstance(item, (list, tuple)):
        if not item:
            return False
        code = item[0]
        if code == 'b':  # Button
            btn_raw = str(item[1]).upper().strip()
            pressed = bool(item[2])
            if btn_raw in ('LT', 'LEFT_TRIGGER', 'L2'):
                ctrl.left_trigger_float(value_float=1.0 if pressed else 0.0)
                return True
            elif btn_raw in ('RT', 'RIGHT_TRIGGER', 'R2'):
                ctrl.right_trigger_float(value_float=1.0 if pressed else 0.0)
                return True
            xusb_btn = BUTTON_MAP.get(btn_raw)
            if xusb_btn:
                if pressed:
                    ctrl.press_button(button=xusb_btn)
                else:
                    ctrl.release_button(button=xusb_btn)
                return True
        elif code == 'ls':  # Left Stick
            x = float(item[1])
            y = float(item[2])
            ctrl.left_joystick_float(x_value_float=max(-1.0, min(1.0, x)), y_value_float=max(-1.0, min(1.0, y)))
            return True
        elif code == 'rs':  # Right Stick
            x = float(item[1])
            y = float(item[2])
            ctrl.right_joystick_float(x_value_float=max(-1.0, min(1.0, x)), y_value_float=max(-1.0, min(1.0, y)))
            return True
        elif code == 't':  # Trigger
            trig_name = str(item[1]).upper().strip()
            val = max(0.0, min(1.0, float(item[2])))
            if trig_name in ('LT', 'L2', 'LEFT'):
                ctrl.left_trigger_float(value_float=val)
            elif trig_name in ('RT', 'R2', 'RIGHT'):
                ctrl.right_trigger_float(value_float=val)
            return True
        elif code == 'r':  # Reset
            ctrl.reset()
            return True
        return False

    if not isinstance(item, dict):
        return False

    inp_type = str(item.get('type') or item.get('t', '')).lower()

    if inp_type in ('button', 'b'):
        btn_raw = str(item.get('button') or item.get('b', '')).upper().strip()
        pressed = bool(item.get('pressed', item.get('p', False)))
        
        # Handle LT / RT sent as buttons
        if btn_raw in ('LT', 'LEFT_TRIGGER', 'L2'):
            ctrl.left_trigger_float(value_float=1.0 if pressed else 0.0)
            return True
        elif btn_raw in ('RT', 'RIGHT_TRIGGER', 'R2'):
            ctrl.right_trigger_float(value_float=1.0 if pressed else 0.0)
            return True

        xusb_btn = BUTTON_MAP.get(btn_raw)
        if xusb_btn:
            if pressed:
                ctrl.press_button(button=xusb_btn)
            else:
                ctrl.release_button(button=xusb_btn)
            return True

    elif inp_type in ('left_stick', 'ls'):
        x = float(item.get('x', 0.0))
        y = float(item.get('y', 0.0))
        ctrl.left_joystick_float(x_value_float=max(-1.0, min(1.0, x)), y_value_float=max(-1.0, min(1.0, y)))
        return True

    elif inp_type in ('right_stick', 'rs'):
        x = float(item.get('x', 0.0))
        y = float(item.get('y', 0.0))
        ctrl.right_joystick_float(x_value_float=max(-1.0, min(1.0, x)), y_value_float=max(-1.0, min(1.0, y)))
        return True

    elif inp_type in ('trigger', 'trig'):
        trig_name = str(item.get('trigger') or item.get('trig', '')).upper().strip()
        val = max(0.0, min(1.0, float(item.get('value', item.get('v', 0.0)))))
        if trig_name in ('LT', 'L2', 'LEFT'):
            ctrl.left_trigger_float(value_float=val)
        elif trig_name in ('RT', 'R2', 'RIGHT'):
            ctrl.right_trigger_float(value_float=val)
        return True

    elif inp_type == 'sticks':
        lx = max(-1.0, min(1.0, float(item.get('lx', 0.0))))
        ly = max(-1.0, min(1.0, float(item.get('ly', 0.0))))
        rx = max(-1.0, min(1.0, float(item.get('rx', 0.0))))
        ry = max(-1.0, min(1.0, float(item.get('ry', 0.0))))
        ctrl.left_joystick_float(x_value_float=lx, y_value_float=ly)
        ctrl.right_joystick_float(x_value_float=rx, y_value_float=ry)
        return True

    elif inp_type in ('reset', 'r'):
        ctrl.reset()
        return True

    return False

# Backward compatibility direct listeners
@sio.on('button_down')
async def handle_button_down(sid, data):
    p_num = sid_to_player.get(sid)
    if p_num and p_num in controllers:
        btn = str(data.get('button', '')).upper().strip()
        ctrl = controllers[p_num]
        if btn in ('LT', 'LEFT_TRIGGER', 'L2'):
            ctrl.left_trigger_float(value_float=1.0)
        elif btn in ('RT', 'RIGHT_TRIGGER', 'R2'):
            ctrl.right_trigger_float(value_float=1.0)
        elif btn in BUTTON_MAP:
            ctrl.press_button(button=BUTTON_MAP[btn])
        ctrl.update()

@sio.on('button_up')
async def handle_button_up(sid, data):
    p_num = sid_to_player.get(sid)
    if p_num and p_num in controllers:
        btn = str(data.get('button', '')).upper().strip()
        ctrl = controllers[p_num]
        if btn in ('LT', 'LEFT_TRIGGER', 'L2'):
            ctrl.left_trigger_float(value_float=0.0)
        elif btn in ('RT', 'RIGHT_TRIGGER', 'R2'):
            ctrl.right_trigger_float(value_float=0.0)
        elif btn in BUTTON_MAP:
            ctrl.release_button(button=BUTTON_MAP[btn])
        ctrl.update()

@sio.on('joystick_move')
async def handle_joystick_move(sid, data):
    p_num = sid_to_player.get(sid)
    if p_num and p_num in controllers:
        stick = str(data.get('stick', '')).lower()
        x = max(-1.0, min(1.0, float(data.get('x', 0.0))))
        y = max(-1.0, min(1.0, float(data.get('y', 0.0))))
        ctrl = controllers[p_num]
        if stick in ('left', 'left_stick', 'ls'):
            ctrl.left_joystick_float(x_value_float=x, y_value_float=y)
        elif stick in ('right', 'right_stick', 'rs'):
            ctrl.right_joystick_float(x_value_float=x, y_value_float=y)
        ctrl.update()

@sio.on('ping_check')
async def handle_ping_check(sid, data):
    """Echo back timestamp for real-time latency calculation."""
    await sio.emit('pong_check', data, to=sid)

def _print_player_status():
    p1 = "🟢 Connected" if connected_players[1] else "⚪ Waiting..."
    p2 = "🟢 Connected" if connected_players[2] else "⚪ Waiting..."
    print(f"    Status: Player 1: {p1} | Player 2: {p2}\n")

# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------
def main():
    # 1. Initialize persistent virtual Xbox 360 controllers
    init_virtual_gamepads()

    # 2. Resolve local network address
    local_ip = get_local_ip()
    port = 5000
    server_url = f"http://{local_ip}:{port}"
    
    print("\n" + "=" * 64)
    print(" 🎮 DUOPAD - ZERO-LATENCY ESPORTS GAMEPAD SERVER 🎮")
    print("=" * 64)
    print(f"  Local Wi-Fi IP:    {local_ip}")
    print(f"  Port:              {port}")
    print(f"\n  👉 OPEN THIS URL ON YOUR SMARTPHONE(S):")
    print(f"     {server_url}")
    print("=" * 64)
    
    # 3. Print QR code in terminal for instant scanning
    try:
        qr = qrcode.QRCode(border=1)
        qr.add_data(server_url)
        qr.make(fit=True)
        print("\n  📱 SCAN THIS QR CODE WITH YOUR PHONE CAMERA:\n")
        qr.print_ascii(invert=True)
    except Exception:
        pass
        
    print("\n" + "-" * 64)
    print("  🎮 LIVE CONTROLLER SLOTS:")
    print("   • Slot 1: [ ACTIVE IN WINDOWS ] -> Ready for Phone 1 (Player 1)")
    print("   • Slot 2: [ ACTIVE IN WINDOWS ] -> Ready for Phone 2 (Player 2)")
    print("   (Both virtual Xbox 360 controllers are active in joy.cpl)")
    print("-" * 64)
    print("  [joy.cpl Tip] Run 'joy.cpl' in Windows to see both controllers!")
    print("  Server is listening on 0.0.0.0:5000 (Press Ctrl+C to stop)...")
    print("=" * 64 + "\n")
    
    web.run_app(app, host='0.0.0.0', port=port, print=None, access_log=None)

if __name__ == '__main__':
    main()
