@echo off
echo ============================================================
echo   Fixing Windows Firewall for FC 26 Phone Controller
echo ============================================================
echo.
echo 1. Removing block rules for Python...
netsh advfirewall firewall delete rule name="python.exe" dir=in action=block

echo 2. Adding Inbound Allow Rule for Port 5000...
netsh advfirewall firewall add rule name="FC26 Controller Server" dir=in action=allow protocol=TCP localport=5000 profile=any

echo 3. Switching Wi-Fi network profile to Private...
powershell -NoProfile -Command "Set-NetConnectionProfile -Name 'GM' -NetworkCategory Private"

echo.
echo ============================================================
echo   SUCCESS! Firewall has been configured.
echo   Now your phone will be able to load http://192.168.0.101:5000
echo ============================================================
pause
