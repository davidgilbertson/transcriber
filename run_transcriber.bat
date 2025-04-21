@echo off
REM Windows batch file for running the transcriber
REM Equivalent of run_transcriber.sh for Windows systems

REM Get the directory where the script is located using %~dp0

REM Run the transcriber using the Python from the virtual environment
start "" "%~dp0.venv\Scripts\python.exe" "%~dp0transcriber.py"

REM Alternative version without console window (commented out)
REM start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0transcriber.py"
