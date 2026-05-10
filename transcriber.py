# %%
import gc
import json
import tkinter as tk
from pathlib import Path
import kb
from recorder import Recorder
from border import Border
import keyboard
from stt import speech_to_text
from utils import get_foreground_window_title


# DEBUG = os.getenv("PYCHARM_HOSTED")
DEBUG = False

SLOW_TYPE_DELAY_S = 0.01
PRIVATE_DIR = Path(".private")
LAST_RECORDING_PATH = PRIVATE_DIR / "last_recording.wav"
LOG_PATH = PRIVATE_DIR / "log.jsonl"

if DEBUG:
    # Catch COM faults
    import faulthandler

    faulthandler.enable()


class Transcriber:
    def __init__(self, root: tk.Tk, hotkey="ctrl+alt+shift+q"):
        self.border = Border(root)
        self.rec = Recorder()

        kb.add_hotkey(hotkey, self.toggle_recording)
        print(f"Press {hotkey} to start/stop recording.")

    def start(self):
        kb.add_hotkey("esc", self.stop)
        self.border.show("#F8312F")

        self.rec.start()

    def stop(self):
        wav_bytes = self.rec.stop()
        gc.collect()  # If GC happens during keyboard() methods, it errors, so we force one now (~15ms)

        kb.remove_hotkey("esc")

        self.border.hide()
        return wav_bytes

    def transcribe(self, wav_bytes):
        PRIVATE_DIR.mkdir(exist_ok=True)
        self.border.show("#FFB02E")
        from utils import stopwatch

        with stopwatch("Transcription", log=False) as sw:
            text = speech_to_text(wav_bytes)

        self.border.hide()
        title = get_foreground_window_title()

        # If a window title contains one of these terms, we feed in characters slowly.
        if any(text in title for text in ["Claude", " - Notepad"]):
            # Without a small delay, Claude Code drops characters.
            keyboard.write(text, delay=0.01)
        else:
            keyboard.write(text)

        n_frames = sum(len(x) for x in self.rec.frames)
        log_line = json.dumps(
            dict(
                audio_length_s=n_frames / self.rec.stream.samplerate,
                transcribe_time_ms=int(sw.get_time_ms()),
                text=text,
            )
        )

        # Log the text
        if not LOG_PATH.exists():
            LOG_PATH.write_text(log_line)
        else:
            log_lines = LOG_PATH.read_text().splitlines()[-499:]  # Truncate
            log_lines.append(log_line)
            LOG_PATH.write_text("\n".join(log_lines))

        # Log the last recording
        with open(LAST_RECORDING_PATH, "wb") as f:
            f.write(wav_bytes.getbuffer())

    def toggle_recording(self):
        if not self.rec.recording:
            self.start()
        else:
            wav_bytes = self.stop()
            self.transcribe(wav_bytes)


root = tk.Tk()
transcriber = Transcriber(root)

try:
    root.mainloop()
finally:
    kb.remove_all_hotkeys()
