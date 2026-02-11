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


# DEBUG = os.getenv("PYCHARM_HOSTED")
DEBUG = False

if DEBUG:
    # Catch COM faults
    import faulthandler

    faulthandler.enable()


class Transcriber:
    def __init__(self, root: tk.Tk, hotkey="ctrl+alt+shift+q"):
        self.border = Border(root)
        self.rec = Recorder()
        self._active_monitor_idx = None

        kb.add_hotkey(hotkey, self.toggle_recording)
        print(f"Press {hotkey} to start/stop recording.")

    def start(self):
        kb.add_hotkey("esc", self.stop)
        # Pick active monitor once; reuse for transcribing
        try:
            self._active_monitor_idx = self.border.get_active_monitor_index()
        except Exception:
            self._active_monitor_idx = None
        self.border.show("#F8312F", monitor_index=self._active_monitor_idx)

        self.rec.start()

    def stop(self):
        wav_bytes = self.rec.stop()
        gc.collect()  # If GC happens during keyboard() methods, it errors, so we force one now (~15ms)

        kb.remove_hotkey("esc")

        self.border.hide()
        return wav_bytes

    def transcribe(self, wav_bytes):
        self.border.show("#FFB02E", monitor_index=self._active_monitor_idx)
        from utils import stopwatch

        with stopwatch("Transcription", log=False) as sw:
            text = speech_to_text(wav_bytes)

        self.border.hide()
        # Without a small delay, Claude Code drops characters.
        # And with the delay it looks nicer anyway
        keyboard.write(text, delay=0.01)

        n_frames = sum(len(x) for x in self.rec.frames)
        log_line = json.dumps(
            dict(
                audio_length_s=n_frames / self.rec.stream.samplerate,
                transcribe_time_ms=int(sw.get_time_ms()),
                text=text,
            )
        )

        # Log the text
        log_path = Path("log.jsonl")
        if not log_path.exists():
            log_path.write_text(log_line)
        else:
            log_lines = log_path.read_text().splitlines()[-499:]  # Truncate
            log_lines.append(log_line)
            log_path.write_text("\n".join(log_lines))

        # Log the last recording
        with open("last_recording.wav", "wb") as f:
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
