# %%
from pathlib import Path
import wave
import io

import keyboard
from openai import OpenAI
from sounddevice import InputStream
import numpy as np


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
    def __init__(self):
        self.rec = Recorder()
        self.oai = OpenAI()

        keyboard.add_hotkey("ctrl+alt+shift+q", self.toggle_recording)
        print("Press Ctrl+Alt+Shift+Q to start/stop recording.")

    def start(self):
        keyboard.write("🔴")
        keyboard.add_hotkey("esc", self.cancel, suppress=True)
        self.rec.start()

    def stop(self):
        keyboard.send("backspace")
        keyboard.write("⌛")
        keyboard.remove_hotkey("esc")

        wav_bytes = self.rec.stop()

        text = self.oai.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=("audio.wav", wav_bytes),
            language="en",
            response_format="text",
            prompt="Use unicode characters where appropriate, like 'CO₂' and '45°'.",
        ).strip()

        keyboard.send("backspace")
        keyboard.write(text)

        Path("last_recording.wav").write_bytes(wav_bytes.getbuffer())

    def cancel(self):
        keyboard.send("backspace")
        keyboard.remove_hotkey("esc")
        self.rec.stop()

    def toggle_recording(self):
        keyboard.release("ctrl")
        keyboard.release("alt")
        keyboard.release("shift")

        if not self.rec.recording:
            self.start()
        else:
            self.stop()


transcriber = Transcriber()

try:
    keyboard.wait()
finally:
    keyboard.clear_all_hotkeys()
