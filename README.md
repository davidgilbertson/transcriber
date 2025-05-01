# Transcriber

A push-to-talk tool that records your voice and types the transcription wherever your cursor is.

This is a personal experiment, not a polished product. Expect a few rough edges, especially if you're not on Windows.

# Getting started

## Prerequisites

- Git
- Python 3.8 or higher
- An OpenAI API key set as an environment variable, `OPENAI_API_KEY=...`

## Installation

This works well on Windows, not so much on macOS. If you're using a Mac some extra work will be required. There's an alternate `transcriber_macos.py` file that shows using a different package, which is more reliable on macOS, but still not perfect.


Clone the repository:
```
git clone https://github.com/davidgilbertson/transcriber.git
cd transcriber
```

Create a virtual environment (optional but recommended):
```
python -m venv .venv
```

Activate the virtual environment:
- On Windows:
  ```
  .venv\Scripts\activate
  ```
- On macOS/Linux:
  ```
  source .venv/bin/activate
  ```

Install required Python dependencies:
```
pip install -r requirements.txt
```

## Running the application

 - On Windows, run the batch file:
   ```
   run_transcriber.bat
   ```
 - On macOS/Linux, make the shell script executable and run it:
   ```
   chmod +x run_transcriber.sh
   ./run_transcriber.sh
   ```

Once running, press `Ctrl+Alt+Shift+Q` to start recording. Press it again to stop recording and begin transcription (takes a few seconds). The transcribed text will be inserted at the cursor position.

# Building an executable

To build so it runs with a terminal window (showing the shortcut and feedback):
```
pyinstaller --onefile transcriber.py
```

To build so it runs in the background:
```
pyinstaller --onefile --noconsole transcriber.py
```

# License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. This is a permissive license that allows you to use, modify, and distribute the code freely, including for commercial purposes.
