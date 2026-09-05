#!/usr/bin/env python3
"""
DuoPad - Desktop Gamepad Hub
Native Windows GUI Application for the DuoPad Dual Phone Controller Server.
Connects up to two smartphones over local Wi-Fi/Hotspot/USB into high-performance
virtual Xbox 360 controllers on Windows via ViGEmBus and vgamepad.
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
        # 1. Force Windows Taskbar to display DuoPad's own icon instead of Anaconda/Python default icon
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('duopad.gamepad.server.v1.0')
    except Exception:
        pass

# 2. Single-Instance Guard: Port 5001 lock socket prevents duplicate servers from stealing connections
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
sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*', ping_timeout=10, ping_interval=5)
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
    return web.FileResponse(os.path.join(TEMPLATES_DIR, 'index.html'))

async def handle_status(request):
    return web.json_response({
        'player1_connected': connected_players[1] is not None,
        'player2_connected': connected_players[2] is not None,
        'active_controllers': len(controllers)
    })

app.router.add_get('/', handle_index)
app.router.add_get('/status', handle_status)
app.router.add_static('/static', STATIC_DIR, name='static')

@sio.on('connect')
async def handle_connect(sid, environ):
    assigned_player = None
    if connected_players[1] is None:
        assigned_player = 1
    elif connected_players[2] is None:
        assigned_player = 2

    if assigned_player is not None:
        connected_players[assigned_player] = sid
        sid_to_player[sid] = assigned_player
        
        # Dynamically attach virtual Xbox 360 controller on phone connection
        if assigned_player in controllers:
            old_ctrl = controllers.pop(assigned_player, None)
            if old_ctrl:
                try:
                    old_ctrl.reset()
                    old_ctrl.update()
                except Exception:
                    pass
                del old_ctrl
            await asyncio.sleep(0.05)

        try:
            ctrl = vg.VX360Gamepad()
            ctrl.reset()
            ctrl.update()
            controllers[assigned_player] = ctrl
            print(f"[DuoPad] Virtual Xbox 360 Controller #{assigned_player} plugged into Windows for Player {assigned_player}!")
        except Exception as e:
            print(f"[DuoPad] Error attaching controller #{assigned_player}: {e}")

        print(f"[DuoPad] Player {assigned_player} connected (sid={sid})")
        await sio.emit('assigned', {'player': assigned_player, 'status': 'connected'}, to=sid)
    else:
        print(f"[DuoPad] Connection rejected for {sid}: 2 players already active.")
        await sio.emit('lobby_full', {'message': 'Both player slots are full.'}, to=sid)
        await sio.disconnect(sid)

@sio.on('disconnect')
async def handle_disconnect(sid):
    if sid in sid_to_player:
        p_num = sid_to_player.pop(sid)
        connected_players[p_num] = None
        
        # Dynamically detach virtual Xbox 360 controller when phone disconnects
        ctrl = controllers.pop(p_num, None)
        if ctrl:
            try:
                ctrl.reset()
                ctrl.update()
            except Exception:
                pass
            del ctrl
            print(f"[DuoPad] Virtual Xbox 360 Controller #{p_num} unplugged from Windows (Player {p_num} disconnected).")
        print(f"[DuoPad] Player {p_num} disconnected. Slot freed.")

@sio.on('input')
async def handle_input(sid, data):
    """
    Handle real-time controller inputs from connected phones with ultra-low latency (<2ms).
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
            val = max(0.0, min(1.0, float(data.get('value', 0.0))))
            if trig_name == 'LT':
                ctrl.left_trigger_float(value_float=val)
            elif trig_name == 'RT':
                ctrl.right_trigger_float(value_float=val)
            ctrl.update()

        elif inp_type == 'left_stick':
            x = max(-1.0, min(1.0, float(data.get('x', 0.0))))
            y = max(-1.0, min(1.0, float(data.get('y', 0.0))))
            ctrl.left_joystick_float(x_value_float=x, y_value_float=y)
            ctrl.update()

        elif inp_type == 'right_stick':
            x = max(-1.0, min(1.0, float(data.get('x', 0.0))))
            y = max(-1.0, min(1.0, float(data.get('y', 0.0))))
            ctrl.right_joystick_float(x_value_float=x, y_value_float=y)
            ctrl.update()

        elif inp_type == 'reset':
            ctrl.reset()
            ctrl.update()

    except Exception:
        pass

# Backward compatibility for direct button / joystick events
@sio.on('button_down')
async def handle_button_down(sid, data):
    p_num = sid_to_player.get(sid)
    if p_num and p_num in controllers:
        btn = data.get('button')
        ctrl = controllers[p_num]
        if btn == 'LT':
            ctrl.left_trigger_float(value_float=1.0)
        elif btn == 'RT':
            ctrl.right_trigger_float(value_float=1.0)
        elif btn in BUTTON_MAP:
            ctrl.press_button(button=BUTTON_MAP[btn])
        ctrl.update()

@sio.on('button_up')
async def handle_button_up(sid, data):
    p_num = sid_to_player.get(sid)
    if p_num and p_num in controllers:
        btn = data.get('button')
        ctrl = controllers[p_num]
        if btn == 'LT':
            ctrl.left_trigger_float(value_float=0.0)
        elif btn == 'RT':
            ctrl.right_trigger_float(value_float=0.0)
        elif btn in BUTTON_MAP:
            ctrl.release_button(button=BUTTON_MAP[btn])
        ctrl.update()

@sio.on('joystick_move')
async def handle_joystick_move(sid, data):
    p_num = sid_to_player.get(sid)
    if p_num and p_num in controllers:
        stick = data.get('stick')
        x = max(-1.0, min(1.0, float(data.get('x', 0.0))))
        y = max(-1.0, min(1.0, float(data.get('y', 0.0))))
        ctrl = controllers[p_num]
        if stick == 'left':
            ctrl.left_joystick_float(x_value_float=x, y_value_float=y)
        elif stick == 'right':
            ctrl.right_joystick_float(x_value_float=x, y_value_float=y)
        ctrl.update()

@sio.on('ping_check')
async def handle_ping_check(sid, data):
    """Echo back timestamp for real-time latency calculation in phone HUD."""
    await sio.emit('pong_check', data, to=sid)

def run_server_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    
    bound = False
    for attempt in range(6):
        try:
            site = web.TCPSite(runner, '0.0.0.0', 5000, reuse_address=True)
            loop.run_until_complete(site.start())
            bound = True
            break
        except Exception:
            time.sleep(0.8)

    if bound:
        loop.run_forever()

# ---------------------------------------------------------------------------
# Native Desktop GUI (Tkinter)
# ---------------------------------------------------------------------------
class DuoPadHubApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DuoPad - Smartphone Gamepad Server")
        self.root.geometry("550x600")
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
        header_frame.pack(pady=(14, 4))

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
            titles_frame, text="Zero-Latency Dual Smartphone Controller for PC",
            font=("Segoe UI", 9), fg="#94a3b8", bg="#050a12", anchor="w"
        )
        lbl_sub.pack(anchor="w")

        # Status Pill
        self.lbl_server_status = tk.Label(
            self.root, text=f"● SERVER ONLINE: {self.server_url}",
            font=("Segoe UI", 10, "bold"), fg="#10b981", bg="#0b1726",
            padx=16, pady=5, relief="ridge", bd=1
        )
        self.lbl_server_status.pack(pady=(0, 10))

        # QR Code Card
        qr_card = tk.Frame(self.root, bg="#0b1726", bd=2, relief="groove", padx=14, pady=12)
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
        lbl_scan.pack(pady=(8, 0))

        # Live Player Status Boxes
        frame_players = tk.Frame(self.root, bg="#050a12")
        frame_players.pack(fill="x", padx=36, pady=10)

        # Player 1 Box (Cyan)
        self.card_p1 = tk.Frame(frame_players, bg="#081422", bd=1, relief="solid", padx=12, pady=8)
        self.card_p1.pack(side="left", expand=True, fill="both", padx=(0, 6))
        tk.Label(self.card_p1, text="PLAYER 1", font=("Segoe UI", 10, "bold"), fg="#00f0ff", bg="#081422").pack()
        self.lbl_p1_status = tk.Label(self.card_p1, text="⚪ Waiting for Phone 1...", font=("Segoe UI", 9), fg="#94a3b8", bg="#081422")
        self.lbl_p1_status.pack(pady=(3, 0))

        # Player 2 Box (Magenta)
        self.card_p2 = tk.Frame(frame_players, bg="#081422", bd=1, relief="solid", padx=12, pady=8)
        self.card_p2.pack(side="right", expand=True, fill="both", padx=(6, 0))
        tk.Label(self.card_p2, text="PLAYER 2", font=("Segoe UI", 10, "bold"), fg="#ff007f", bg="#081422").pack()
        self.lbl_p2_status = tk.Label(self.card_p2, text="⚪ Waiting for Phone 2...", font=("Segoe UI", 9), fg="#94a3b8", bg="#081422")
        self.lbl_p2_status.pack(pady=(3, 0))

        # Warning / Info Notice Box (Keep Open in Background)
        warn_box = tk.Frame(
            self.root, bg="#1a1306", bd=1, relief="solid",
            highlightbackground="#f59e0b", highlightthickness=1, padx=14, pady=8
        )
        warn_box.pack(fill="x", padx=36, pady=(4, 8))

        lbl_warn_title = tk.Label(
            warn_box,
            text="⚠️  WARNING: KEEP THIS APP OPEN IN BACKGROUND WHILE PLAYING",
            font=("Segoe UI", 9, "bold"),
            fg="#fbbf24",
            bg="#1a1306"
        )
        lbl_warn_title.pack(anchor="w")

        lbl_warn_desc = tk.Label(
            warn_box,
            text="Do NOT close this window during games (you can minimize it).\nClosing this app stops the server and disconnects your virtual gamepads.",
            font=("Segoe UI", 8),
            fg="#fef3c7",
            bg="#1a1306",
            justify="left"
        )
        lbl_warn_desc.pack(anchor="w", pady=(2, 0))

        # Action Buttons
        frame_actions = tk.Frame(self.root, bg="#050a12")
        frame_actions.pack(pady=6)

        btn_joy = tk.Button(
            frame_actions, text="🎮 Test Gamepads (joy.cpl)", font=("Segoe UI", 9, "bold"),
            bg="#0284c7", fg="#ffffff", padx=14, pady=6, bd=0, cursor="hand2",
            command=self.open_joy_cpl
        )
        btn_joy.pack(side="left", padx=6)

        btn_browser = tk.Button(
            frame_actions, text="🌐 Open Controller Link", font=("Segoe UI", 9),
            bg="#1e293b", fg="#cbd5e1", padx=12, pady=6, bd=0, cursor="hand2",
            command=self.open_in_browser
        )
        btn_browser.pack(side="left", padx=6)

        # Footer
        lbl_foot = tk.Label(
            self.root, text="DuoPad v1.0 • 100% Free & Open Source for Gamers • Leave open while playing",
            font=("Segoe UI", 8), fg="#64748b", bg="#050a12"
        )
        lbl_foot.pack(pady=(8, 12))

    def start_server_background(self):
        t = threading.Thread(target=run_server_thread, daemon=True)
        t.start()

    def poll_player_status(self):
        if connected_players[1] is not None:
            self.lbl_p1_status.config(text="🟢 CONNECTED (Active)", fg="#10b981")
            self.card_p1.config(highlightbackground="#00f0ff", highlightcolor="#00f0ff", highlightthickness=2)
        else:
            self.lbl_p1_status.config(text="⚪ Waiting for Phone 1...", fg="#94a3b8")
            self.card_p1.config(highlightthickness=0)

        if connected_players[2] is not None:
            self.lbl_p2_status.config(text="🟢 CONNECTED (Active)", fg="#10b981")
            self.card_p2.config(highlightbackground="#ff007f", highlightcolor="#ff007f", highlightthickness=2)
        else:
            self.lbl_p2_status.config(text="⚪ Waiting for Phone 2...", fg="#94a3b8")
            self.card_p2.config(highlightthickness=0)

        self.root.after(400, self.poll_player_status)

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
