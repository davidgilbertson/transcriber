import io
import wave

import numpy as np
from sounddevice import InputStream

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
        volume.duck()
        self.stream.start()

    def stop(self):
        self.stream.stop()
        volume.restore()

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


if __name__ == "__main__":
    import time
    from pathlib import Path

    rec = Recorder()

    rec.start()
    print("Recording...")

    time.sleep(2)

    print("Done")
    wav_bytes = rec.stop()

    Path("last_recording.wav").write_bytes(wav_bytes.getbuffer())
