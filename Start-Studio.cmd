@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Studio.ps1" %*
if errorlevel 1 (
    echo.
    echo Studio could not start. See the error above.
    pause
)
