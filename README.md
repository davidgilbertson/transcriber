# Transcriber

A tool to run locally that transcribes microphone input into a text box.

## Getting Started

### Prerequisites

- Git
- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. Clone the repository:
```
git clone https://github.com/davidgilbertson/transcriber.git
cd transcriber
```

2. Create a virtual environment (optional but recommended):
```
python -m venv .venv
```

3. Activate the virtual environment:
   - On Windows:
   ```
   .venv\Scripts\activate
   ```
   - On macOS/Linux:
   ```
   source .venv/bin/activate
   ```

4. Install required Python dependencies:
```
pip install -r requirements.txt
```

### Running the Application

#### On Windows
Run the batch file:
```
run_transcriber.bat
```

#### On macOS/Linux
Make the shell script executable and run it:
```
chmod +x run_transcriber.sh
./run_transcriber.sh
```

## Usage

Once running, press `Ctrl+Alt+Shift+Q` to start/stop recording. The transcribed text will be inserted at the cursor position.

## Building Executable

To build so it runs with a terminal window (showing the shortcut and feedback):
```
pyinstaller --onefile transcriber.py
```

To build so it runs in the background:
```
pyinstaller --onefile --noconsole transcriber.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. This is a permissive license that allows you to use, modify, and distribute the code freely, including for commercial purposes.
