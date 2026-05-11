@echo off
setlocal EnableDelayedExpansion
REM Stops the background transcriber process started by run_transcriber.bat.

set "SCRIPT_DIR=%~dp0"
set "PID_FILE=%SCRIPT_DIR%.private\transcriber.pid"

if exist "%PID_FILE%" (
    set /p EXISTING_PID=<"%PID_FILE%"
    if defined EXISTING_PID (
        taskkill /PID !EXISTING_PID! /F >nul 2>&1
    )
    del "%PID_FILE%" >nul 2>&1
)
