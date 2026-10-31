import os
import subprocess
import ctypes
from pathlib import Path

base_dir = os.path.dirname(os.path.abspath(__file__))
exe_path = os.path.join(base_dir, "DuoPad.exe")
ico_path = os.path.join(base_dir, "duopad_neon.ico")
if not os.path.exists(ico_path):
    ico_path = os.path.join(base_dir, "duopad_icon.ico")

hub_path = os.path.join(base_dir, "duopad_hub.py")

# Target can directly be the compiled DuoPad.exe
target_path = exe_path if os.path.exists(exe_path) else "pythonw.exe"
target_args = "" if os.path.exists(exe_path) else f'"{hub_path}"'

# Resolve Desktop folder dynamically
desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
onedrive_desktop = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
if os.path.exists(onedrive_desktop):
    desktop_dir = onedrive_desktop

shortcut_file = os.path.join(desktop_dir, "DuoPad.lnk")

if os.path.exists(shortcut_file):
    try:
        os.remove(shortcut_file)
    except Exception:
        pass

ps_cmd = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_file}')
$Shortcut.TargetPath = '{target_path}'
$Shortcut.Arguments = '{target_args}'
$Shortcut.WorkingDirectory = '{base_dir}'
$Shortcut.IconLocation = '{ico_path},0'
$Shortcut.Description = 'DuoPad - Smartphone Gamepad Server'
$Shortcut.Save()
"""
res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
print(f"Created shortcut at {shortcut_file} -> Exists: {os.path.exists(shortcut_file)}")
