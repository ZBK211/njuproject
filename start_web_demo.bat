@echo off
cd /d "%~dp0"
start "ForgeAgent demo server" powershell -NoExit -ExecutionPolicy Bypass -Command "Set-Location -LiteralPath '%~dp0'; python scripts\demo_server.py"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8787/"
echo ForgeAgent web demo is starting at http://127.0.0.1:8787/
echo Keep the server window open while using the demo.
pause
