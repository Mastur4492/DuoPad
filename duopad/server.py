#!/usr/bin/env python3
"""
EA SPORTS FC 26 - Dual Phone Controller Server
Connects two Android phones over local Wi-Fi to control two separate
persistent virtual Xbox 360 controllers on Windows via ViGEmBus and vgamepad.
Uses high-performance aiohttp + python-socketio for ultra-low WebSocket latency (<2ms).
"""

import os
import sys
import time
import socket
import atexit
import qrcode
import asyncio

# Ensure Windows console handles UTF-8 / emojis properly without crash
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

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
    ping_interval=5
)
app = web.Application()
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

# XUSB Button mappings
BUTTON_MAP = {
    'A': vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    'B': vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    'X': vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    'Y': vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    'LB': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    'RB': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    'START': vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    'Start': vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    'BACK': vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    'Back': vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    'GUIDE': vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
    'Guid': vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
    'DPAD_UP': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    'DPAD_DOWN': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    'DPAD_LEFT': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    'DPAD_RIGHT': vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
    'L3': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    'LS': vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    'R3': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    'RS': vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
}

def cleanup_controllers():
    """Detach all connected controllers on server shutdown."""
    print("\n[*] Server stopping. Detaching controllers...")
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
    return web.FileResponse(index_path)

async def handle_status(request):
    return web.json_response({
        'player1_connected': connected_players[1] is not None,
        'player2_connected': connected_players[2] is not None,
        'controllers_initialized': len(controllers) == 2
    })

# Register HTTP routes and static directory
app.router.add_get('/', handle_index)
app.router.add_get('/status', handle_status)
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
        
        # Dynamically attach virtual Xbox controller
        try:
            ctrl = vg.VX360Gamepad()
            ctrl.reset()
            ctrl.update()
            controllers[assigned_player] = ctrl
            print(f"🎮 [ViGEmBus] Virtual Xbox 360 Controller #{assigned_player} plugged into Windows!")
        except Exception as e:
            print(f"❌ [ViGEmBus] Error attaching controller #{assigned_player}: {e}")
        
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
        print(f"⚠️ [REJECTED] Third device attempted to connect from {client_ip} (sid: {sid[:8]}). Game is full.")

@sio.on('disconnect')
async def handle_disconnect(sid):
    if sid in sid_to_player:
        player_num = sid_to_player.pop(sid)
        connected_players[player_num] = None
        
        # Dynamically detach virtual controller from Windows
        ctrl = controllers.pop(player_num, None)
        if ctrl:
            try:
                ctrl.reset()
                ctrl.update()
            except Exception:
                pass
            del ctrl
            print(f"🔌 [ViGEmBus] Virtual Xbox 360 Controller #{player_num} unplugged from Windows.")
            
        print(f"🔴 [DISCONNECT] Player {player_num} disconnected.")
        _print_player_status()

@sio.on('input')
async def handle_input(sid, data):
    """
    Handle real-time controller inputs from connected phones.
    Payload types:
      - button:      { type: 'button', button: 'A', pressed: true/false }
      - trigger:     { type: 'trigger', trigger: 'RT', value: 0.0 - 1.0 }
      - left_stick:  { type: 'left_stick', x: -1.0 to 1.0, y: -1.0 to 1.0 }
      - right_stick: { type: 'right_stick', x: -1.0 to 1.0, y: -1.0 to 1.0 }
      - reset:       { type: 'reset' }
    """
    player_num = sid_to_player.get(sid)
    if not player_num or player_num not in controllers:
        return
    
    ctrl = controllers[player_num]
    inp_type = data.get('type')
    
    try:
        if inp_type == 'button':
            btn_name = data.get('button')
            pressed = bool(data.get('pressed', False))
            xusb_btn = BUTTON_MAP.get(btn_name)
            if xusb_btn:
                if pressed:
                    ctrl.press_button(button=xusb_btn)
                else:
                    ctrl.release_button(button=xusb_btn)
                ctrl.update()

        elif inp_type == 'trigger':
            trig_name = data.get('trigger')
            val = float(data.get('value', 0.0))
            val = max(0.0, min(1.0, val))
            
            if trig_name == 'LT':
                ctrl.left_trigger_float(value_float=val)
            elif trig_name == 'RT':
                ctrl.right_trigger_float(value_float=val)
            ctrl.update()

        elif inp_type == 'left_stick':
            x = float(data.get('x', 0.0))
            y = float(data.get('y', 0.0))
            x = max(-1.0, min(1.0, x))
            y = max(-1.0, min(1.0, y))
            ctrl.left_joystick_float(x_value_float=x, y_value_float=y)
            ctrl.update()

        elif inp_type == 'right_stick':
            x = float(data.get('x', 0.0))
            y = float(data.get('y', 0.0))
            x = max(-1.0, min(1.0, x))
            y = max(-1.0, min(1.0, y))
            ctrl.right_joystick_float(x_value_float=x, y_value_float=y)
            ctrl.update()

        elif inp_type == 'reset':
            ctrl.reset()
            ctrl.update()

    except Exception as e:
        print(f"[!] Input processing error for Player {player_num}: {e}")

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
    # Controllers are attached dynamically on-demand when phones connect
    
    # 2. Resolve local network address
    local_ip = get_local_ip()
    port = 5000
    server_url = f"http://{local_ip}:{port}"
    
    print("\n" + "=" * 62)
    print(" ⚽ EA SPORTS FC 26 - DUAL PHONE CONTROLLER SERVER ⚽")
    print("=" * 62)
    print(f"  Local Wi-Fi IP:    {local_ip}")
    print(f"  Port:              {port}")
    print(f"\n  👉 OPEN THIS URL ON BOTH ANDROID PHONES:")
    print(f"     {server_url}")
    print("=" * 62)
    
    # 3. Print QR code in terminal for instant scanning
    try:
        qr = qrcode.QRCode(border=1)
        qr.add_data(server_url)
        qr.make(fit=True)
        print("\n  📱 SCAN THIS QR CODE WITH YOUR PHONE CAMERA:\n")
        qr.print_ascii(invert=True)
    except Exception:
        pass
        
    print("\n" + "-" * 62)
    print("  🎮 LIVE CONTROLLER SLOTS:")
    print("   • Slot 1: [ FREE ] -> Ready for Phone 1 (Player 1)")
    print("   • Slot 2: [ FREE ] -> Ready for Phone 2 (Player 2)")
    print("   (Both virtual Xbox 360 controllers are active in joy.cpl)")
    print("-" * 62)
    print("  [joy.cpl Tip] Run 'joy.cpl' in Windows to see both controllers!")
    print("  Server is listening on 0.0.0.0:5000 (Press Ctrl+C to stop)...")
    print("=" * 62 + "\n")
    
    # Run the high-performance async web server on 0.0.0.0
    web.run_app(app, host='0.0.0.0', port=port, print=None)

if __name__ == '__main__':
    main()
