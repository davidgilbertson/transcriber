# %%
import wave
import io

from openai import OpenAI
from sounddevice import InputStream
import numpy as np
from pynput.keyboard import GlobalHotKeys
from pynput import keyboard as kb

import volume


# Similar logic to transcriber.py, but less buggy on macOS.
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
        self.controller = kb.Controller()

    def run(self):
        print("Press Ctrl+Shift+Q to start/stop recording.")
        with GlobalHotKeys(
            {
                "<ctrl>+<shift>+q": self.toggle_recording,
                "<esc>": self.stop,
            }
        ) as hk:
            hk.join()

    def start(self):
        self.controller.type("●")

        volume.duck()
        self.rec.start()

    def stop(self):
        self.controller.tap(kb.Key.backspace)

        wav_bytes = self.rec.stop()
        volume.restore()
        return wav_bytes

    def transcribe(self, wav_bytes):
        self.controller.type("⌛")
        text = self.oai.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=("audio.wav", wav_bytes),
            language="en",
            response_format="text",
            prompt="Use unicode characters where appropriate, like 'CO₂' and '45°'.",
        ).strip()

        self.controller.tap(kb.Key.backspace)
        self.controller.type(text)

    def toggle_recording(self):
        if not self.rec.recording:
            self.start()
        else:
            wav_bytes = self.stop()
            self.transcribe(wav_bytes)

transcriber = Transcriber()
transcriber.run()
