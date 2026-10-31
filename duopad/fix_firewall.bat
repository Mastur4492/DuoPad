@echo off
title DuoPad - Windows Firewall Configuration
echo ============================================================
echo   DuoPad - Windows Firewall Configuration for Phone Gamepad
echo ============================================================
echo.
echo [*] Adding Inbound Allow Rule for DuoPad on Port 5000...
netsh advfirewall firewall delete rule name="DuoPad Server" >nul 2>&1
netsh advfirewall firewall add rule name="DuoPad Server" dir=in action=allow protocol=TCP localport=5000 profile=any >nul 2>&1

echo [*] Ensuring Wi-Fi network category allows local LAN connections...
powershell -NoProfile -Command "Get-NetConnectionProfile | Where-Object { $_.NetworkCategory -eq 'Public' } | Set-NetConnectionProfile -NetworkCategory Private -ErrorAction SilentlyContinue" >nul 2>&1

echo.
echo ============================================================
echo   [+] SUCCESS! Windows Firewall is now optimized for DuoPad.
echo   Your phone will connect instantly over local Wi-Fi / Hotspot!
echo ============================================================
echo.
pause
