@echo off
rem Double-click to start the card tracker on Windows.
rem If a tracker server is already running, it is stopped first (restart).
setlocal
cd /d "%~dp0"
set "PORT=%CARD_TRACKER_PORT%"
if not defined PORT set "PORT=8484"

rem Stop the Python process listening on the port, if any (never another app).
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r /c:":%PORT% .*LISTENING"') do (
  tasklist /fi "PID eq %%p" /fo csv /nh | findstr /i "python py.exe" >nul && (
    echo Stopping the running server ^(PID %%p^)...
    taskkill /pid %%p /f >nul
  )
)
rem Give Windows a moment to free the port.
timeout /t 1 /nobreak >nul

where py >nul 2>nul
if %errorlevel%==0 (py server.py) else (python server.py)
pause
