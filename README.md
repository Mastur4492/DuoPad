<div align="center">

<img src="duopad-web/duopad_icon.png" alt="DuoPad Logo" width="140" />

# DuoPad

**Turn Any Smartphone into a Zero-Latency Wireless Xbox 360 Controller for PC Games**

*Play EA Sports FC 24/25/26, FIFA, GTA V, Rocket League, Forza, and 2-Player Co-Op with Friends — No Physical Controller Needed!*

[![Live Website](https://img.shields.io/badge/Website-duopad--web.vercel.app-00f0ff?style=for-the-badge&logo=vercel)](https://duopad-web.vercel.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6.svg)](https://microsoft.com/windows)
[![Latency](https://img.shields.io/badge/Latency-%3C1ms%20Local%20Wi--Fi-10b981.svg)](#)
[![Controllers](https://img.shields.io/badge/Emulation-Dual%20Xbox%20360%20(XInput)-purple.svg)](#)

</div>

---

## 🌟 Live Demo & Download
Visit the official DuoPad website to download the Windows installer:
👉 **[https://duopad-web.vercel.app](https://duopad-web.vercel.app)**

---

## 💡 Key Features
* **Zero Phone App Downloads** — No APK or Play Store download needed. Simply scan the QR code on your PC screen with your phone's camera to play instantly in Chrome or Safari.
* **Player 1 & Player 2 Dual Co-Op** — Connect two phones simultaneously (Player 1 = Cyan, Player 2 = Magenta) for 1v1 local matches or split-screen co-op.
* **Official Hardware Emulation** — Uses the industry-standard Nefarius ViGEmBus virtual bus driver. Windows natively detects two Xbox 360 controllers with zero configuration.
* **Ultra-Low Latency (<1ms)** — Direct binary WebSocket packets transmission over local Wi-Fi.
* **Works with All PC Games** — Fully compatible with EA App, Steam, Epic Games Store, and Xbox Game Pass.

---

## 📂 Project Structure
* `duopad/` — Windows Desktop Hub, Python WebSocket server, ViGEmBus driver bridge, virtual controller HTML templates.
* `duopad-web/` — Modern responsive landing page deployed on Vercel (`duopad-web.vercel.app`).

---

## 📜 License
Licensed under the [MIT License](duopad/LICENSE).
