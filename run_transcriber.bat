@echo off
setlocal EnableDelayedExpansion
REM Windows batch file for running the transcriber
REM Equivalent of run_transcriber.sh for Windows systems

REM Get the directory where the script is located using %~dp0
set "SCRIPT_DIR=%~dp0"
set "PRIVATE_DIR=%SCRIPT_DIR%.private"
set "PID_FILE=%PRIVATE_DIR%\transcriber.pid"

if not exist "%PRIVATE_DIR%" mkdir "%PRIVATE_DIR%"

if exist "%PID_FILE%" (
    set /p EXISTING_PID=<"%PID_FILE%"
    if defined EXISTING_PID (
        taskkill /PID !EXISTING_PID! /F >nul 2>&1
    )
    del "%PID_FILE%" >nul 2>&1
)

for /f %%i in ('powershell -NoProfile -Command "$process = Start-Process -FilePath '%SCRIPT_DIR%.venv\Scripts\pythonw.exe' -ArgumentList @('%SCRIPT_DIR%transcriber_realtime.py') -WorkingDirectory '%SCRIPT_DIR%' -PassThru; $process.Id"') do (
    >"%PID_FILE%" echo %%i
)
