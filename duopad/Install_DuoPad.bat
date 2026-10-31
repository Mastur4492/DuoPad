@echo off
title DuoPad - Automated Setup & Installer
color 0B

echo ========================================================
echo        DUOPAD - Zero-Latency Smartphone Gamepad
echo ========================================================
echo.
echo [*] Checking Python installation...
py -3 --version >nul 2>&1
if %errorlevel% neq 0 (
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [!] Python was not found!
        echo Please install Python 3.10+ from https://www.python.org/downloads/
        echo Make sure to check "Add python.exe to PATH" during installation.
        pause
        exit /b 1
    )
    set PY_CMD=python
) else (
    set PY_CMD=py -3
)

echo [*] Installing required Python dependencies...
%PY_CMD% -m pip install --upgrade pip >nul 2>&1
%PY_CMD% -m pip install -r requirements.txt

echo.
echo [*] Generating high-resolution DuoPad brand assets & icons...
%PY_CMD% generate_duopad_logo.py >nul 2>&1

echo.
echo [*] Compiling native Windows executable (DuoPad.exe)...
if exist "duopad_neon.ico" (
    set ICON_ARG=/win32icon:duopad_neon.ico
) else (
    set ICON_ARG=/win32icon:duopad_icon.ico
)
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /target:winexe %ICON_ARG% /out:"DuoPad.exe" Launcher.cs >nul 2>&1

echo.
echo [*] Creating Desktop shortcuts...
%PY_CMD% create_duopad_shortcuts.py

echo.
echo ========================================================
echo   [+] DuoPad Setup Complete!
echo   Double-click the "DuoPad" icon on your Desktop to play!
echo ========================================================
echo.
pause
