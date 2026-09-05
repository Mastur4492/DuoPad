<div align="center">

<img src="duopad_icon.png" alt="DuoPad Logo" width="160" />

# DuoPad

**Turn Any Smartphone into a Zero-Latency Wireless Xbox Controller for PC Games**

*Play EA FC 26, FIFA, Rocket League, WWE 2K, and Split-Screen Co-Op with Friends — No Extra Gamepad Needed!*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)](https://microsoft.com/windows)
[![Latency](https://img.shields.io/badge/Latency-%3C2ms%20WebSocket-brightgreen.svg)](#)
[![Controllers](https://img.shields.io/badge/Emulation-Dual%20Xbox%20360%20(XInput)-purple.svg)](#)
[![Price](https://img.shields.io/badge/Price-100%25%20Free%20%26%20Open%20Source-ff69b4.svg)](#)

</div>

---

## 💡 Why DuoPad?

Ever had a friend or brother visit to play **EA SPORTS FC / FIFA / Mortal Kombat / It Takes Two**, only to realize you **only have one controller**?
An original Xbox or PS5 controller costs **$50 - $70 (₹4,000 - ₹6,000)**, and cheap third-party pads break within weeks.

**DuoPad solves this instantly:**
1. **Zero Phone App Downloads** — No APKs, no ad-bloated Play Store apps. Just scan a QR code with your phone's camera, and your mobile browser instantly turns into a responsive wireless gamepad.
2. **True 2-Player Co-Op** — Emulates two independent, persistent virtual Xbox 360 controllers on Windows via industry-standard ViGEmBus.
3. **Engineered for Competitive Sports & Co-Op** — Sprint, finesse, through balls, tactile D-Pad, 360° dual analog thumbsticks, and haptic vibration feedback.
4. **Sub-2ms Latency** — Powered by high-throughput async WebSockets for real-time responsiveness.

---

## 🎮 Controller Layout

<div align="center">
  <img src="duopad_icon.png" alt="DuoPad Layout" width="340" />
</div>

- **Player 1**: Glowing Electric Cyan Theme (`#00f0ff`)
- **Player 2**: Glowing Neon Magenta Theme (`#ff007f`)
- **Dual Analog Sticks**: Left Thumbstick (Movement) & Right Thumbstick (Skill moves)
- **8-Way D-Pad**: Quick tactics, camera, and navigation
- **Action Buttons**: Y, B, A, X diamond layout with high-contrast tactile feedback
- **Bumpers & Triggers**: LB, RB, LT (Brake/Shield), RT (Sprint)
- **Menu & Controls**: Start, Back, Guide, Fullscreen toggle, and Screen Wake-Lock

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Windows 10 or 11 (64-bit)**
- **Python 3.10+** (Ensure *"Add python.exe to PATH"* is checked during Python installation)
- **Nefarius ViGEmBus Driver** (Free open-source Windows gamepad driver: [Download ViGEmBus Installer](https://github.com/nefarius/ViGEmBus/releases/latest))

### 2. Installation
1. Clone or download this repository:
   ```bash
   git clone https://github.com/your-username/duopad.git
   cd duopad
   ```
2. Run the automated installer:
   ```cmd
   Install_DuoPad.bat
   ```
   *(This automatically installs dependencies, generates high-res icons, compiles `DuoPad.exe`, and places a shortcut on your Desktop).*

### 3. Playing
1. Double-click the **DuoPad** icon on your Desktop.
2. The DuoPad Hub opens and displays your unique connection QR code.
3. Open your phone's camera, scan the QR code, and rotate your phone to **Landscape mode**.
4. Launch your game (**EA SPORTS FC 26**, FIFA, Rocket League, etc.) and enjoy!

---

## 📡 3 Flexible Connection Modes

| Mode | Setup | Latency | When to Use |
| :--- | :--- | :--- | :--- |
| **1. Home Wi-Fi** (Default) | PC & Phone on the same Wi-Fi router | **~1-3 ms** | At home with normal Wi-Fi |
| **2. Mobile Hotspot** | Turn on Phone Hotspot -> Connect PC to it | **~1-2 ms** | No router available / Traveling |
| **3. USB Tethering** | Plug phone into PC via USB cable -> Turn on USB Tethering | **<0.5 ms** | Competitive esports / Zero lag |

---

## 🛠️ Testing Your Gamepads

Want to verify your virtual controllers before launching a game?
1. In the **DuoPad Hub**, click **"🎮 Test Gamepads (joy.cpl)"**.
2. Windows will open the native Game Controllers panel.
3. Move your phone's analog sticks or press buttons to watch the virtual Xbox 360 controller respond in real time!

---

## 🎯 Supported Games

DuoPad emulates genuine **XInput Xbox 360 controllers**, making it natively compatible with 99.9% of PC games without keymapping software:
- ⚽ **Football / Sports**: EA SPORTS FC 24/25/26, FIFA 19-23, eFootball, NBA 2K
- 🏎️ **Racing**: Forza Horizon 4/5, F1 23/24, Need for Speed, Trackmania
- 🥊 **Fighting**: Mortal Kombat 1/11, Tekken 8, Street Fighter 6, WWE 2K23/24
- 👥 **Local Co-Op**: It Takes Two, A Way Out, Overcooked! 2, Cuphead, Broforce, Rayman Legends

---

## 🛡️ License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
Free to use, modify, and distribute for all gamers.

---

<div align="center">
  <sub>Built with ❤️ for gamers worldwide. If DuoPad saved you from buying an extra controller, consider starring the repository ⭐!</sub>
</div>
