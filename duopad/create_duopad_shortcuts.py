import os
import subprocess
import ctypes

base_dir = r"C:\Users\mo.mastur\OneDrive\Desktop\console\duopad"
exe_path = os.path.join(base_dir, "DuoPad.exe")
ico_path = os.path.join(base_dir, "duopad_neon.ico")
pythonw_path = r"C:\Users\mo.mastur\anaconda3\pythonw.exe"
hub_path = os.path.join(base_dir, "duopad_hub.py")

# Target can directly be the compiled DuoPad.exe
target_path = exe_path if os.path.exists(exe_path) else pythonw_path
target_args = "" if os.path.exists(exe_path) else f'"{hub_path}"'

# ONLY put on the user's active desktop to prevent duplicate icons!
dest = r"C:\Users\mo.mastur\OneDrive\Desktop"
shortcut_file = os.path.join(dest, "DuoPad.lnk")

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
res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
print(f"Created single shortcut at {shortcut_file} -> Exists: {os.path.exists(shortcut_file)}")

# Remove any lingering duplicate files in other Desktop folders
for extra in [
    r"C:\Users\Public\Desktop\DuoPad.lnk",
    r"C:\Users\mo.mastur\Desktop\DuoPad.lnk",
    r"C:\Users\mo.mastur\OneDrive\Desktop\DuoPad.exe" # User prefers the shortcut with icon over raw exe
]:
    if os.path.exists(extra):
        try:
            os.remove(extra)
            print(f"Removed redundant item: {extra}")
        except Exception:
            pass

# Force Windows Explorer to refresh icon cache immediately
try:
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    print("[+] Windows Explorer refreshed icon cache.")
except Exception as e:
    print("SHChangeNotify error:", e)
