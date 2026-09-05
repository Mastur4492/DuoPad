@echo off
title DuoPad - Automated Setup & Installer
color 0B

echo ========================================================
echo        DUOPAD - Zero-Latency Smartphone Gamepad
echo ========================================================
echo.
echo [*] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python was not found in PATH!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

echo [*] Installing required Python dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo [*] Generating high-resolution DuoPad brand assets & icons...
python generate_duopad_logo.py

echo.
echo [*] Compiling native Windows executable (DuoPad.exe)...
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /target:winexe /win32icon:duopad_icon.ico /out:"DuoPad.exe" Launcher.cs >nul 2>&1

echo.
echo [*] Creating Desktop shortcuts...
python create_duopad_shortcuts.py

echo.
echo ========================================================
echo   [+] DuoPad Setup Complete!
echo   Double-click the "DuoPad" icon on your Desktop to play!
echo ========================================================
echo.
pause
