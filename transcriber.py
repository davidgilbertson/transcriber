# %%
import os

import keyboard
from openai import OpenAI

import kb
from recorder import Recorder

DEBUG = os.getenv("PYCHARM_HOSTED")

if DEBUG:
    # Catch COM faults
    import faulthandler

    faulthandler.enable()


class Transcriber:
    def __init__(self, hotkey="ctrl+alt+shift+q"):
        self.rec = Recorder()
        self.oai = OpenAI()

        kb.add_hotkey(hotkey, self.toggle_recording)
        print(f"Press {hotkey} to start/stop recording.")

    def start(self):
        keyboard.write("🔴")  # or ● if using with a terminal
        kb.add_hotkey("esc", self.stop)

        self.rec.start()

    def stop(self):
        # Stop first, which entails COM operations (volume.restore()), before using keyboard
        wav_bytes = self.rec.stop()

        keyboard.send("backspace")
        kb.remove_hotkey("esc")

        return wav_bytes

    def transcribe(self, wav_bytes):
        keyboard.write("⌛")
        text = self.oai.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=("audio.wav", wav_bytes),
            language="en",
            response_format="text",
            prompt="Use unicode characters where appropriate, like 'CO₂' and '45°'.",
        ).strip()

        keyboard.send("backspace")
        keyboard.write(text)

        if DEBUG:
            with open("transcriptions.log", "a", encoding="utf-8") as f:
                f.write("-" * 80 + "\n")
                f.write(text + "\n")
            with open("last_recording.wav", "wb") as f:
                f.write(wav_bytes.getbuffer())

    def toggle_recording(self):
        if not self.rec.recording:
            self.start()
        else:
            wav_bytes = self.stop()
            self.transcribe(wav_bytes)


transcriber = Transcriber()

try:
    kb.wait()
finally:
    kb.remove_all_hotkeys()
