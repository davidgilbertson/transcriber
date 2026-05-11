# %%
import gc
import json
import tkinter as tk
import tomllib
from pathlib import Path

import kb
from recorder import Recorder
from border import Border
import keyboard
from openai import OpenAI
from utils import stopwatch

from dotenv import load_dotenv

load_dotenv()

config = tomllib.loads(Path(__file__).with_name("config.toml").read_text())
hotkey = config["hotkey"]
model = config["batch_model"]
push_to_talk = config["push_to_talk"]
TRANSCRIPTION_PROMPT = """\
Use unicode characters where appropriate, like 'CO₂' and '45°'.
User is an AI Engineer who uses Python and JavaScript, among other languages. 
Use UK spelling, not US spelling."""

PRIVATE_DIR = Path(".private")
LAST_RECORDING_PATH = PRIVATE_DIR / "last_recording.wav"
LOG_PATH = PRIVATE_DIR / "log.jsonl"


class Transcriber:
    def __init__(self, root: tk.Tk):
        self.border = Border(root)
        self.rec = Recorder()

        if push_to_talk:
            kb.add_hold_hotkey(hotkey, self.start, self.stop_and_transcribe)
        else:
            kb.add_hotkey(hotkey, self.toggle_recording)

    def start(self):
        if self.rec.recording:
            return

        self.border.show("#F8312F")

        self.rec.start()

    def stop(self):
        if not self.rec.recording:
            return None

        wav_bytes = self.rec.stop()
        gc.collect()  # If GC happens during keyboard() methods, it errors, so we force one now (~15ms)

        self.border.hide()
        return wav_bytes

    def stop_and_transcribe(self):
        wav_bytes = self.stop()
        if wav_bytes is not None:
            self.transcribe(wav_bytes)

    def transcribe(self, wav_bytes):
        PRIVATE_DIR.mkdir(exist_ok=True)
        self.border.show("#FFB02E")

        # TODO: Hide the orange border in a finally block so API/keyboard errors
        # cannot leave it stuck on screen.
        with stopwatch("Transcription", log=False) as sw:
            wav_bytes.seek(0)
            stream = OpenAI().audio.transcriptions.create(
                model=model,
                file=("audio.wav", wav_bytes),
                language="en",
                response_format="text",
                prompt=TRANSCRIPTION_PROMPT,
                stream=True,
            )

            text = ""
            for event in stream:
                if event.type == "transcript.text.delta":
                    delta = event.delta.replace("\n", "⏎")
                    keyboard.write(delta)
                    text += delta
                elif event.type == "transcript.text.done":
                    text = event.text.strip().replace("\n", "⏎")

        self.border.hide()

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
            self.stop_and_transcribe()


root = tk.Tk()
transcriber = Transcriber(root)

try:
    root.mainloop()
finally:
    kb.remove_all_hotkeys()
