# Target realtime transcriber flow:
#
# 1. User presses the hotkey to start recording.
#
# 2. Recording starts immediately. No waiting for OpenAI connection setup before capturing audio.
#
# 3. In the background, the realtime OpenAI connection/session is created or already available.
#
# 4. As microphone audio arrives, it is sent to the realtime connection continuously.
#
# 5. As transcription deltas come back while the user is still speaking, those words are written to the active window live, not held until the stop hotkey.
#
# 6. User presses the hotkey again to stop recording.
#
# 7. The app stops capturing microphone audio.
#
# 8. The app sends `commit` for the final buffered audio, keeps listening for remaining deltas / the `completed` transcript, and writes any final trailing text that was not already written.
#
# 9. Once `completed` arrives, the app is done with that recording turn.

import base64
import queue
import threading
import time

from dotenv import load_dotenv
from openai import OpenAI
from sounddevice import RawInputStream


MODEL = "gpt-realtime-whisper"
record_seconds = 5
delay = "xhigh"


load_dotenv()
client = OpenAI()

audio_queue = queue.Queue()
completed = threading.Event()
connection = None
started_at = None
sender_thread = None
receiver_thread = None
first_append_logged = False


def print_event(event_type, text):
    print(f"{time.perf_counter() - started_at:6.2f}s {event_type}: {text}", flush=True)


def receive_events():
    for event in connection:
        if event.type == "session.updated":
            print_event("session_updated", event.session.type)
        if event.type == "conversation.item.input_audio_transcription.delta":
            print_event("delta", event.delta or "")
        elif event.type == "conversation.item.input_audio_transcription.completed":
            print_event("completed", event.transcript)
            completed.set()
            break
        elif event.type == "input_audio_buffer.committed":
            print_event("committed", event.item_id)


def send_audio():
    global connection, receiver_thread, first_append_logged

    print_event("status", "connecting")
    with client.realtime.connect(
        extra_query=dict(intent="transcription")
    ) as connection:
        receiver_thread = threading.Thread(target=receive_events)
        receiver_thread.start()

        print_event("status", "updating session")
        connection.session.update(
            session=dict(
                type="transcription",
                audio=dict(
                    input=dict(
                        format=dict(type="audio/pcm", rate=24_000),
                        transcription=dict(
                            model=MODEL,
                            language="en",
                            delay=delay,
                        ),
                        turn_detection=None,
                    )
                ),
            )
        )

        while True:
            audio_chunk = audio_queue.get()
            if audio_chunk is None:
                break
            if not first_append_logged:
                print_event("append", "first audio chunk")
                first_append_logged = True
            connection.input_audio_buffer.append(
                audio=base64.b64encode(audio_chunk).decode("ascii")
            )

        print_event("status", "committing final audio")
        connection.input_audio_buffer.commit()
        completed.wait()
        connection.close()
        receiver_thread.join()


def record_callback(indata, *_):
    audio_queue.put(bytes(indata))


def run():
    global started_at, sender_thread, audio_queue, first_append_logged

    started_at = time.perf_counter()
    audio_queue = queue.Queue()
    first_append_logged = False
    completed.clear()

    sender_thread = threading.Thread(target=send_audio)
    sender_thread.start()

    with RawInputStream(
        samplerate=24_000,
        channels=1,
        dtype="int16",
        callback=record_callback,
    ):
        print_event("status", f"recording for {record_seconds}s")
        time.sleep(record_seconds)

    print_event("status", "stopped recording")
    audio_queue.put(None)
    sender_thread.join()


if __name__ == "__main__":
    print("Starting...")
    run()
