# %%
import wave
import io

from openai import OpenAI
from sounddevice import InputStream
import numpy as np
from pynput.keyboard import GlobalHotKeys
from pynput import keyboard as kb


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
        print("Press Ctrl+Alt+Shift+Q to start/stop recording.")
        with GlobalHotKeys(
            {
                "<ctrl>+<alt>+<shift>+q": self.toggle_recording,
                "<esc>": self.cancel,
            }
        ) as hk:
            hk.join()

    def start(self):
        self.controller.type("🔴")
        self.rec.start()

    def stop(self):
        self.controller.tap(kb.Key.backspace)
        self.controller.type("⌛")

        wav_bytes = self.rec.stop()

        text = self.oai.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=("audio.wav", wav_bytes),
            language="en",
            response_format="text",
            prompt="Use unicode characters where appropriate, like 'CO₂' and '45°'.",
        ).strip()

        self.controller.tap(kb.Key.backspace)
        self.controller.type(text)

    def cancel(self):
        if self.rec.recording:
            self.controller.tap(kb.Key.backspace)
            self.rec.stop()

    def toggle_recording(self):
        self.controller.release(kb.Key.ctrl)
        self.controller.release(kb.Key.alt)
        self.controller.release(kb.Key.shift)

        if not self.rec.recording:
            self.start()
        else:
            self.stop()


transcriber = Transcriber()
transcriber.run()
