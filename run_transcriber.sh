#!/bin/bash
# Equivalent of run_transcriber.bat for macOS/Linux
# Note: You may need to make this script executable with: chmod +x run_transcriber.sh

# Get the directory where the script is located
SCRIPT_DIR="$(dirname "$0")"

# Run the transcriber using the Python from the virtual environment
"$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/transcriber_macos.py"

# Alternative version without console window (commented out)
# nohup "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/transcriber_macos.py" > /dev/null 2>&1 &
