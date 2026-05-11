# Target realtime transcriber flow:
# 1. User presses the hotkey to start recording.
# 2. Recording starts immediately. No waiting for OpenAI connection setup before capturing audio.
# 3. In the background, the realtime OpenAI connection/session is created or already available.
# 4. As microphone audio arrives, it is sent to the realtime connection continuously.
# 5. As transcription deltas come back while the user is still speaking, those words are written to the active window live, not held until the stop hotkey.
# 6. User presses the hotkey again to stop recording.
# 7. The app stops capturing microphone audio.
# 8. The app sends `commit` for the final buffered audio, keeps listening for remaining deltas / the `completed` transcript, and writes any final trailing text that was not already written.
# 9. Once `completed` arrives, the app is done with that recording turn.

import base64
import queue
import threading
import tkinter as tk
import tomllib
from pathlib import Path

import keyboard
from dotenv import load_dotenv
from openai import OpenAI
from sounddevice import RawInputStream

import kb
import volume
from border import Border


model = "gpt-realtime-whisper"
config = tomllib.loads(Path(__file__).with_name("config.toml").read_text())
hotkey = config["realtime"]["hotkey"]
push_to_talk = config["realtime"]["push_to_talk"]


class TranscriberRealtime:
    def __init__(self, root: tk.Tk):
        self.border = Border(root)
        self.client = OpenAI()
        self.audio_queue = queue.Queue()
        self.completed = threading.Event()
        self.connection = None
        self.stream = None
        self.sender_thread = None
        self.receiver_thread = None
        self.recording = False
        self.recording_lock = threading.Lock()
        self.wrote_text = False

        if push_to_talk:
            kb.add_hold_hotkey(hotkey, self.start, self.stop)
        else:
            kb.add_hotkey(hotkey, self.toggle_recording)

    def start(self):
        with self.recording_lock:
            if self.recording:
                return

            self.audio_queue = queue.Queue()
            self.completed.clear()
            self.wrote_text = False
            self.recording = True

            self.border.show("#F8312F")
            volume.duck()

            self.sender_thread = threading.Thread(target=self.send_audio)
            self.sender_thread.start()

            self.stream = RawInputStream(
                samplerate=24_000,
                channels=1,
                dtype="int16",
                callback=self.process_audio_input,
            )
            self.stream.start()

    def stop(self):
        with self.recording_lock:
            if not self.recording:
                return

            self.recording = False
            self.stream.close()
            volume.restore()
            self.border.hide()
            self.audio_queue.put(None)

    def process_audio_input(self, indata, *_):
        self.audio_queue.put(bytes(indata))

    def send_audio(self):
        with self.client.realtime.connect(
            extra_query=dict(intent="transcription")
        ) as self.connection:
            self.receiver_thread = threading.Thread(target=self.receive_events)
            self.receiver_thread.start()

            self.connection.session.update(
                session=dict(
                    type="transcription",
                    audio=dict(
                        input=dict(
                            format=dict(type="audio/pcm", rate=24_000),
                            transcription=dict(
                                model=model,
                                language="en",
                                delay="xhigh",  # "minimal", "low", "medium", "high", "xhigh"
                            ),
                            turn_detection=None,
                        )
                    ),
                )
            )

            while True:
                audio_chunk = self.audio_queue.get()
                if audio_chunk is None:
                    break
                self.connection.input_audio_buffer.append(
                    audio=base64.b64encode(audio_chunk).decode("ascii")
                )

            self.connection.input_audio_buffer.commit()
            self.completed.wait()
            self.connection.close()
            self.receiver_thread.join()

    def receive_events(self):
        for event in self.connection:
            if event.type == "conversation.item.input_audio_transcription.delta":
                text = event.delta
                if not self.wrote_text:
                    self.wrote_text = True
                    text = text.lstrip()

                keyboard.write(text)
            elif event.type == "conversation.item.input_audio_transcription.completed":
                self.completed.set()
                break

    def toggle_recording(self):
        if self.recording:
            self.stop()
        else:
            self.start()


load_dotenv()

root = tk.Tk()
transcriber = TranscriberRealtime(root)

try:
    root.mainloop()
finally:
    kb.remove_all_hotkeys()
