# %%
from openai import OpenAI
from pynput.keyboard import GlobalHotKeys
from pynput import keyboard as kb
from recorder import Recorder


# Similar logic to transcriber.py, but pynput is less buggy on macOS.
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

        self.rec.start()

    def stop(self):
        self.controller.tap(kb.Key.backspace)

        wav_bytes = self.rec.stop()
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
