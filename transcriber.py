# %%
from pathlib import Path
import wave
import io

import keyboard
from openai import OpenAI
from sounddevice import InputStream
import numpy as np

import kb
import volume


class Recorder:
    def __init__(self):
        self.frames = []
        self.stream = InputStream(
            samplerate=24_000,  # Expected by OpenAI
            channels=1,  # Mono
            dtype="int16",  # 16-bit
            callback=lambda indata, *_: self.frames.append(indata.copy()),
        )

    def start(self):
        self.frames = []
        self.stream.start()

    def stop(self):
        self.stream.stop()

        wav_bytes = io.BytesIO()

        with wave.open(wav_bytes, "wb") as wave_file:
            wave_file.setframerate(self.stream.samplerate)
            wave_file.setnchannels(self.stream.channels)
            wave_file.setsampwidth(self.stream.samplesize)
            wave_file.writeframes(np.concatenate(self.frames, axis=0).tobytes())

        return wav_bytes

    @property
    def recording(self):
        return self.stream.active


class Transcriber:
    def __init__(self, hotkey="ctrl+alt+shift+q"):
        self.rec = Recorder()
        self.oai = OpenAI()

        kb.add_hotkey(hotkey, self.toggle_recording)
        print(f"Press {hotkey} to start/stop recording.")

    def start(self):
        keyboard.write("🔴")  # or ● if using with a terminal
        kb.add_hotkey("esc", self.stop)

        volume.duck()
        self.rec.start()

    def stop(self):
        keyboard.send("backspace")
        kb.remove_hotkey("esc")

        wav_bytes = self.rec.stop()
        volume.restore()
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

        # For debugging:
        # with open("transcriptions.log", "a", encoding="utf-8") as f:
        #     f.write("-" * 80 + "\n")
        #     f.write(text + "\n")
        # Path("last_recording.wav").write_bytes(wav_bytes.getbuffer())

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
