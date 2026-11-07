#!/usr/bin/env python3
"""
DuoPad - Desktop Gamepad Hub
Native Windows GUI Application for the DuoPad Dual Phone Controller Server.
Connects up to two smartphones over local Wi-Fi/Hotspot/USB into high-performance
persistent virtual Xbox 360 controllers on Windows via ViGEmBus and vgamepad.
100% Free and Open Source for the Gaming Industry.
"""

import os
import sys
import time
import socket
import threading
import subprocess
import asyncio
import webbrowser
import traceback

def _global_exception_handler(exc_type, exc_value, exc_traceback):
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        with open(os.path.join(os.path.expanduser("~"), "duopad_crash.log"), "w", encoding="utf-8") as f:
            f.write(err_msg)
    except Exception:
        pass
    try:
        import tkinter as _tk
        from tkinter import messagebox as _mb
        _r = _tk.Tk()
        _r.withdraw()
        _mb.showerror("DuoPad Error", f"An unexpected error occurred:\n\n{err_msg}")
        _r.destroy()
    except Exception:
        pass

sys.excepthook = _global_exception_handler

import tkinter as tk
from tkinter import ttk, messagebox

# Explicitly block Pillow C-extensions from being imported by qrcode
sys.modules['PIL'] = None
sys.modules['PIL.Image'] = None
import qrcode

# Windows console encoding safeguard & Taskbar App ID
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('duopad.gamepad.server.v1.0')
    except Exception:
        pass

# Single-Instance Guard: Port 5001 lock socket prevents duplicate servers
_lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    _lock_socket.bind(('127.0.0.1', 5001))
except OSError:
    try:
        import tkinter as _tk
        from tkinter import messagebox as _mb
        _r = _tk.Tk()
        _r.withdraw()
        _mb.showwarning("DuoPad Already Running", "DuoPad Hub is already running in the background!\nPlease check your taskbar.")
        _r.destroy()
    except Exception:
        pass
    sys.exit(0)

from aiohttp import web
import socketio
import engineio
import engineio.async_drivers.aiohttp
import vgamepad as vg

# ---------------------------------------------------------------------------
# Server Logic & State
# ---------------------------------------------------------------------------
sio = socketio.AsyncServer(
    async_mode='aiohttp',
    cors_allowed_origins='*',
    ping_timeout=10,
    ping_interval=5,
    http_compression=False,
    async_handlers=False
)
app = web.Application()
sio.attach(app)

if getattr(sys, 'frozen', False):
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

controllers = {}
connected_players = {1: None, 2: None}
sid_to_player = {}
player_telemetry = {1: "Neutral", 2: "Neutral"}
player_last_active = {1: 0.0, 2: 0.0}

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
# Native Windows Mouse & Keyboard Emulation
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
    Pre-initialize persistent virtual Xbox 360 controllers on Windows.
    This guarantees joy.cpl and games (FIFA, FC 24/25/26, Forza, GTA) detect them immediately.
    """
    for p_num in (1, 2):
        if p_num in controllers:
            continue
        try:
            ctrl = vg.VX360Gamepad()
            ctrl.reset()
            ctrl.update()
            controllers[p_num] = ctrl
            print(f"[DuoPad] Persistent Virtual Xbox 360 Controller #{p_num} plugged into Windows!")
            time.sleep(0.35)  # Crucial: Allow Windows PnP bus enumeration
        except Exception as e:
            print(f"[DuoPad] ViGEmBus warning for Controller #{p_num}: {e}")

def ensure_controller(p_num):
    if p_num in controllers:
        return controllers[p_num]
    try:
        ctrl = vg.VX360Gamepad()
        ctrl.reset()
        ctrl.update()
        controllers[p_num] = ctrl
        return ctrl
    except Exception as e:
        print(f"[DuoPad] Error ensuring Controller #{p_num}: {e}")
        return None

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

async def handle_index(request):
    resp = web.FileResponse(os.path.join(TEMPLATES_DIR, 'index.html'))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

async def handle_status(request):
    return web.json_response({
        'status': 'online',
        'player1_connected': connected_players[1] is not None,
        'player2_connected': connected_players[2] is not None,
        'active_controllers': len(controllers)
    })

async def handle_health(request):
    return web.Response(text="OK", content_type="text/plain")

app.router.add_get('/', handle_index)
app.router.add_get('/status', handle_status)
app.router.add_get('/health', handle_health)
app.router.add_static('/static', STATIC_DIR, name='static')

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
        
        ctrl = ensure_controller(assigned_player)
        if ctrl:
            try:
                ctrl.reset()
                ctrl.update()
            except Exception:
                pass

        print(f"[DuoPad] Player {assigned_player} connected from {client_ip} (sid={sid[:8]})")
        await sio.emit('assigned', {
            'player': assigned_player,
            'status': 'connected',
            'message': f'Connected as Player {assigned_player}'
        }, to=sid)
    else:
        print(f"[DuoPad] Connection rejected for {sid[:8]}: Both player slots occupied.")
        await sio.emit('game_full', {'status': 'full', 'message': 'Both player slots are full.'}, to=sid)
        await sio.disconnect(sid)

@sio.on('disconnect')
async def handle_disconnect(sid):
    if sid in sid_to_player:
        p_num = sid_to_player.pop(sid)
        connected_players[p_num] = None
        player_telemetry[p_num] = "Disconnected"
        
        # Neutralize inputs without detaching from Windows
        ctrl = controllers.get(p_num)
        if ctrl:
            try:
                ctrl.reset()
                ctrl.update()
            except Exception:
                pass
        print(f"[DuoPad] Player {p_num} disconnected. Slot freed.")

@sio.on('input')
def handle_input(sid, data):
    """
    Handle real-time controller inputs with zero lag (<1ms).
    Fast-paths Gamepad XInput directly to ViGEmBus kernel driver.
    """
    player_num = sid_to_player.get(sid)
    if player_num and player_num in controllers:
        ctrl = controllers[player_num]
        try:
            player_last_active[player_num] = time.time()
            if isinstance(data, list):
                # Check if it's a compact tuple packet like ['ls', x, y] or a batch of items
                if data and isinstance(data[0], str):
                    if _apply_gamepad_item(ctrl, data, player_num):
                        ctrl.update()
                        return
                else:
                    for item in data:
                        _apply_gamepad_item(ctrl, item, player_num)
                    ctrl.update()
                    return

            if _apply_gamepad_item(ctrl, data, player_num):
                ctrl.update()
                return
        except Exception as e:
            print(f"[!] Input processing error for Player {player_num}: {e}")
        return

    # Fallback to Desktop Mouse / Keyboard emulation
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

def _apply_gamepad_item(ctrl, item, p_num=None):
    """Sub-microsecond helper to update a single virtual Xbox 360 controller control."""
    # Fast path for compact tuple/list format: ['b', 'A', 1], ['ls', x, y], ['rs', x, y], ['t', 'RT', 1.0], ['r']
    if isinstance(item, (list, tuple)):
        if not item:
            return False
        code = item[0]
        if code == 'b':  # Button
            btn_raw = str(item[1]).upper().strip()
            pressed = bool(item[2])
            if p_num:
                player_telemetry[p_num] = f"Btn: {btn_raw}" if pressed else "Neutral"
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
            if p_num and (abs(x) > 0.05 or abs(y) > 0.05):
                player_telemetry[p_num] = f"LS: ({x:.2f}, {y:.2f})"
            ctrl.left_joystick_float(x_value_float=max(-1.0, min(1.0, x)), y_value_float=max(-1.0, min(1.0, y)))
            return True
        elif code == 'rs':  # Right Stick
            x = float(item[1])
            y = float(item[2])
            if p_num and (abs(x) > 0.05 or abs(y) > 0.05):
                player_telemetry[p_num] = f"RS: ({x:.2f}, {y:.2f})"
            ctrl.right_joystick_float(x_value_float=max(-1.0, min(1.0, x)), y_value_float=max(-1.0, min(1.0, y)))
            return True
        elif code == 't':  # Trigger
            trig_name = str(item[1]).upper().strip()
            val = max(0.0, min(1.0, float(item[2])))
            if p_num and val > 0.05:
                player_telemetry[p_num] = f"{trig_name}: {val:.2f}"
            if trig_name in ('LT', 'L2', 'LEFT'):
                ctrl.left_trigger_float(value_float=val)
            elif trig_name in ('RT', 'R2', 'RIGHT'):
                ctrl.right_trigger_float(value_float=val)
            return True
        elif code == 'r':  # Reset
            ctrl.reset()
            if p_num:
                player_telemetry[p_num] = "Neutral"
            return True
        return False

    if not isinstance(item, dict):
        return False

    inp_type = str(item.get('type') or item.get('t', '')).lower()

    if inp_type in ('button', 'b'):
        btn_raw = str(item.get('button') or item.get('b', '')).upper().strip()
        pressed = bool(item.get('pressed', item.get('p', False)))

        if p_num:
            player_telemetry[p_num] = f"Btn: {btn_raw}" if pressed else "Neutral"

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
        if p_num and (abs(x) > 0.05 or abs(y) > 0.05):
            player_telemetry[p_num] = f"LS: ({x:.2f}, {y:.2f})"
        ctrl.left_joystick_float(x_value_float=max(-1.0, min(1.0, x)), y_value_float=max(-1.0, min(1.0, y)))
        return True

    elif inp_type in ('right_stick', 'rs'):
        x = float(item.get('x', 0.0))
        y = float(item.get('y', 0.0))
        if p_num and (abs(x) > 0.05 or abs(y) > 0.05):
            player_telemetry[p_num] = f"RS: ({x:.2f}, {y:.2f})"
        ctrl.right_joystick_float(x_value_float=max(-1.0, min(1.0, x)), y_value_float=max(-1.0, min(1.0, y)))
        return True

    elif inp_type in ('trigger', 'trig'):
        trig_name = str(item.get('trigger') or item.get('trig', '')).upper().strip()
        val = max(0.0, min(1.0, float(item.get('value', item.get('v', 0.0)))))
        if p_num and val > 0.05:
            player_telemetry[p_num] = f"{trig_name}: {val:.2f}"
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
        if p_num:
            player_telemetry[p_num] = "Neutral"
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
    await sio.emit('pong_check', data, to=sid)

def run_server_thread():
    init_virtual_gamepads()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    runner = web.AppRunner(app, access_log=None)
    loop.run_until_complete(runner.setup())
    
    bound = False
    for attempt in range(8):
        try:
            site = web.TCPSite(runner, '0.0.0.0', 5000, reuse_address=True)
            loop.run_until_complete(site.start())
            bound = True
            break
        except Exception:
            time.sleep(0.5)

    if bound:
        loop.run_forever()

# ---------------------------------------------------------------------------
# Native Desktop GUI (Tkinter)
# ---------------------------------------------------------------------------
class DuoPadHubApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DuoPad - Smartphone Gamepad Server")
        self.root.geometry("560x620")
        self.root.resizable(False, False)
        self.root.configure(bg="#050a12")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Window Icon
        ico_file = os.path.join(BASE_DIR, 'duopad_neon.ico')
        if not os.path.exists(ico_file):
            ico_file = os.path.join(BASE_DIR, 'duopad_icon.ico')
        if os.path.exists(ico_file):
            try:
                self.root.iconbitmap(default=ico_file)
            except Exception:
                try:
                    self.root.iconbitmap(ico_file)
                except Exception:
                    pass
        png_file = os.path.join(BASE_DIR, 'duopad_icon.png')
        if os.path.exists(png_file):
            try:
                self.tk_win_icon = tk.PhotoImage(file=png_file)
                self.root.iconphoto(True, self.tk_win_icon)
            except Exception:
                pass

        self.local_ip = get_local_ip()
        self.port = 5000
        self.server_url = f"http://{self.local_ip}:{self.port}"
        
        self.setup_ui()
        self.start_server_background()
        self.poll_player_status()

    def setup_ui(self):
        # Header Banner with App Logo
        header_frame = tk.Frame(self.root, bg="#050a12")
        header_frame.pack(pady=(12, 4))

        png_file = os.path.join(BASE_DIR, 'duopad_icon.png')
        if os.path.exists(png_file):
            try:
                self.tk_logo = tk.PhotoImage(file=png_file).subsample(8, 8)
                lbl_logo = tk.Label(header_frame, image=self.tk_logo, bg="#050a12")
                lbl_logo.pack(side="left", padx=(0, 12))
            except Exception:
                pass

        titles_frame = tk.Frame(header_frame, bg="#050a12")
        titles_frame.pack(side="left")

        lbl_header = tk.Label(
            titles_frame, text="DuoPad",
            font=("Segoe UI", 22, "bold"), fg="#00f0ff", bg="#050a12", anchor="w"
        )
        lbl_header.pack(anchor="w")

        lbl_sub = tk.Label(
            titles_frame, text="Zero-Latency Dual Smartphone Controller for PC (Free)",
            font=("Segoe UI", 9), fg="#94a3b8", bg="#050a12", anchor="w"
        )
        lbl_sub.pack(anchor="w")

        # Status Pill
        self.lbl_server_status = tk.Label(
            self.root, text=f"● SERVER ONLINE: {self.server_url}",
            font=("Segoe UI", 10, "bold"), fg="#10b981", bg="#0b1726",
            padx=16, pady=5, relief="ridge", bd=1
        )
        self.lbl_server_status.pack(pady=(0, 8))

        # QR Code Card
        qr_card = tk.Frame(self.root, bg="#0b1726", bd=2, relief="groove", padx=12, pady=10)
        qr_card.pack(pady=2)

        qr = qrcode.QRCode(box_size=5, border=2)
        qr.add_data(self.server_url)
        qr.make(fit=True)
        matrix = qr.get_matrix()
        n_modules = len(matrix)
        box_size = 5
        canvas_dim = n_modules * box_size

        canvas_qr = tk.Canvas(qr_card, width=canvas_dim, height=canvas_dim, bg="#ffffff", highlightthickness=0, bd=0)
        canvas_qr.pack()

        for r in range(n_modules):
            for c in range(n_modules):
                if matrix[r][c]:
                    canvas_qr.create_rectangle(
                        c * box_size, r * box_size,
                        (c + 1) * box_size, (r + 1) * box_size,
                        fill="#000000", outline=""
                    )

        lbl_scan = tk.Label(
            qr_card, text="📱 Scan with Phone Camera to Connect Gamepad",
            font=("Segoe UI", 9, "bold"), fg="#e2e8f0", bg="#0b1726"
        )
        lbl_scan.pack(pady=(6, 0))

        # Live Player Status Boxes with Input Telemetry
        frame_players = tk.Frame(self.root, bg="#050a12")
        frame_players.pack(fill="x", padx=32, pady=8)

        # Player 1 Box (Cyan)
        self.card_p1 = tk.Frame(frame_players, bg="#081422", bd=1, relief="solid", padx=10, pady=6)
        self.card_p1.pack(side="left", expand=True, fill="both", padx=(0, 5))
        tk.Label(self.card_p1, text="PLAYER 1 (Cyan)", font=("Segoe UI", 10, "bold"), fg="#00f0ff", bg="#081422").pack()
        self.lbl_p1_status = tk.Label(self.card_p1, text="⚪ Waiting for Phone 1...", font=("Segoe UI", 9), fg="#94a3b8", bg="#081422")
        self.lbl_p1_status.pack(pady=(2, 0))
        self.lbl_p1_input = tk.Label(self.card_p1, text="Active: Xbox 360 #1", font=("Segoe UI", 8), fg="#38bdf8", bg="#081422")
        self.lbl_p1_input.pack(pady=(1, 0))

        # Player 2 Box (Magenta)
        self.card_p2 = tk.Frame(frame_players, bg="#081422", bd=1, relief="solid", padx=10, pady=6)
        self.card_p2.pack(side="right", expand=True, fill="both", padx=(5, 0))
        tk.Label(self.card_p2, text="PLAYER 2 (Magenta)", font=("Segoe UI", 10, "bold"), fg="#ff007f", bg="#081422").pack()
        self.lbl_p2_status = tk.Label(self.card_p2, text="⚪ Waiting for Phone 2...", font=("Segoe UI", 9), fg="#94a3b8", bg="#081422")
        self.lbl_p2_status.pack(pady=(2, 0))
        self.lbl_p2_input = tk.Label(self.card_p2, text="Active: Xbox 360 #2", font=("Segoe UI", 8), fg="#f43f5e", bg="#081422")
        self.lbl_p2_input.pack(pady=(1, 0))

        # Warning / Info Notice Box
        warn_box = tk.Frame(
            self.root, bg="#1a1306", bd=1, relief="solid",
            highlightbackground="#f59e0b", highlightthickness=1, padx=12, pady=6
        )
        warn_box.pack(fill="x", padx=32, pady=(2, 6))

        lbl_warn_title = tk.Label(
            warn_box,
            text="🎮 BOTH VIRTUAL XBOX 360 GAMEPADS ARE READY IN WINDOWS",
            font=("Segoe UI", 9, "bold"),
            fg="#fbbf24",
            bg="#1a1306"
        )
        lbl_warn_title.pack(anchor="w")

        lbl_warn_desc = tk.Label(
            warn_box,
            text="Launch EA Sports FC, FIFA, Forza or GTA V anytime. Keep this app open in background.\nMinimize to taskbar while playing.",
            font=("Segoe UI", 8),
            fg="#fef3c7",
            bg="#1a1306",
            justify="left"
        )
        lbl_warn_desc.pack(anchor="w", pady=(1, 0))

        # Action Buttons
        frame_actions = tk.Frame(self.root, bg="#050a12")
        frame_actions.pack(pady=4)

        btn_joy = tk.Button(
            frame_actions, text="🎮 Test Gamepads (joy.cpl)", font=("Segoe UI", 9, "bold"),
            bg="#0284c7", fg="#ffffff", padx=14, pady=5, bd=0, cursor="hand2",
            command=self.open_joy_cpl
        )
        btn_joy.pack(side="left", padx=5)

        btn_browser = tk.Button(
            frame_actions, text="🌐 Open Controller Link", font=("Segoe UI", 9),
            bg="#1e293b", fg="#cbd5e1", padx=12, pady=5, bd=0, cursor="hand2",
            command=self.open_in_browser
        )
        btn_browser.pack(side="left", padx=5)

        # Footer
        lbl_foot = tk.Label(
            self.root, text="DuoPad v1.0 • 100% Free & Open Source for Gamers • Leave open while playing",
            font=("Segoe UI", 8), fg="#64748b", bg="#050a12"
        )
        lbl_foot.pack(pady=(6, 8))

    def start_server_background(self):
        t = threading.Thread(target=run_server_thread, daemon=True)
        t.start()

    def poll_player_status(self):
        now = time.time()
        # Player 1 Status & Telemetry
        if connected_players[1] is not None:
            active_str = player_telemetry.get(1, "Neutral")
            is_recent = (now - player_last_active.get(1, 0)) < 1.0
            live_tag = " [INPUT ACTIVE]" if (is_recent and active_str != "Neutral") else ""
            self.lbl_p1_status.config(text=f"🟢 CONNECTED{live_tag}", fg="#10b981")
            self.lbl_p1_input.config(text=f"Live: {active_str}", fg="#38bdf8")
            self.card_p1.config(highlightbackground="#00f0ff", highlightcolor="#00f0ff", highlightthickness=2)
        else:
            self.lbl_p1_status.config(text="⚪ Waiting for Phone 1...", fg="#94a3b8")
            self.lbl_p1_input.config(text="Virtual Xbox 360 #1: Ready", fg="#64748b")
            self.card_p1.config(highlightthickness=0)

        # Player 2 Status & Telemetry
        if connected_players[2] is not None:
            active_str = player_telemetry.get(2, "Neutral")
            is_recent = (now - player_last_active.get(2, 0)) < 1.0
            live_tag = " [INPUT ACTIVE]" if (is_recent and active_str != "Neutral") else ""
            self.lbl_p2_status.config(text=f"🟢 CONNECTED{live_tag}", fg="#10b981")
            self.lbl_p2_input.config(text=f"Live: {active_str}", fg="#f43f5e")
            self.card_p2.config(highlightbackground="#ff007f", highlightcolor="#ff007f", highlightthickness=2)
        else:
            self.lbl_p2_status.config(text="⚪ Waiting for Phone 2...", fg="#94a3b8")
            self.lbl_p2_input.config(text="Virtual Xbox 360 #2: Ready", fg="#64748b")
            self.card_p2.config(highlightthickness=0)

        self.root.after(200, self.poll_player_status)

    def open_joy_cpl(self):
        try:
            subprocess.Popen("joy.cpl", shell=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open joy.cpl: {e}")

    def open_in_browser(self):
        webbrowser.open(self.server_url)

    def on_close(self):
        active_count = sum(1 for p in connected_players.values() if p is not None)
        if active_count > 0:
            ans = messagebox.askyesno(
                "Exit DuoPad?",
                f"⚠️ A phone is currently connected to DuoPad ({active_count} active)!\n\n"
                "Closing DuoPad will disconnect your gamepads.\n"
                "Tip: You can MINIMIZE this window while playing instead.\n\n"
                "Are you sure you want to close DuoPad?",
                icon="warning"
            )
            if not ans:
                return

        for p_num, ctrl in list(controllers.items()):
            try:
                ctrl.reset()
                ctrl.update()
            except Exception:
                pass
            del ctrl
        controllers.clear()
        self.root.destroy()
        os._exit(0)

def main():
    root = tk.Tk()
    app = DuoPadHubApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
