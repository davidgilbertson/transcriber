# %%
import os
import gc
import tkinter as tk

import keyboard
from openai import OpenAI

import kb
from recorder import Recorder
from border import Border

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
        self.oai = OpenAI()

        kb.add_hotkey(hotkey, self.toggle_recording)
        print(f"Press {hotkey} to start/stop recording.")

    def start(self):
        # keyboard.write("🔴")  # or ● for use with a terminal
        kb.add_hotkey("esc", self.stop)
        self.border.show("#F8312F")

        self.rec.start()

    def stop(self):
        wav_bytes = self.rec.stop()
        gc.collect()  # If GC happens during keyboard() methods, it errors, so we force one now (~15ms)

        # keyboard.send("backspace")
        kb.remove_hotkey("esc")

        self.border.hide()
        return wav_bytes

    def transcribe(self, wav_bytes):
        # keyboard.write("⌛")
        self.border.show("#FFB02E")
        from utils import stopwatch

        with stopwatch("Transcription", log=False) as sw:
            text = (
                self.oai.audio.transcriptions.create(
                    model="gpt-4o-transcribe",
                    file=("audio.wav", wav_bytes),
                    language="en",
                    response_format="text",
                    prompt="Use unicode characters where appropriate, like 'CO₂' and '45°'. Use UK spelling, not US spelling.",
                )
                .strip()
                .replace("\n", "⏎")
            )

        # keyboard.send("backspace")
        self.border.hide()
        keyboard.write(text)

        if DEBUG:
            import json

            n_frames = sum(len(x) for x in self.rec.frames)
            data = dict(
                audio_length_s=n_frames / self.rec.stream.samplerate,
                transcribe_time_ms=int(sw.get_time_ms()),
                text=text,
            )
            with open("log.jsonl", "a") as f:
                f.write(json.dumps(data) + "\n")
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
