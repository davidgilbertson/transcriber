import base64
import threading
import time

from dotenv import load_dotenv
from openai import OpenAI
from sounddevice import RawInputStream

load_dotenv()

####### FINDINGS #######
# You can use `gpt-4o-transcribe` with a `client.realtime.connect()`, but it's not really realtime.
# It will transcribe only once you commit. It will then stream the response.
# You can commit once per n seconds, but each committed chunk is treated independently, resulting
#  in terrible transcriptions as words are cut off and context lost.
# This version tries server VAD with one final manual commit, to see whether `gpt-4o-transcribe`
# accepts the docs-style config.
# Note that `turn_detection` works with `gpt-4o-transcribe` but not `gpt-realtime-whisper`

model = "gpt-realtime-whisper"
# model = "gpt-4o-transcribe"
RECORD_SECONDS = 5
SAMPLE_RATE = 24_000
BLOCK_SIZE = 2_400

client = OpenAI()
recording_finished = False


def ts():
    return round(time.monotonic(), 4)


def receive_events():
    for event in connection:
        if event.type == "conversation.item.input_audio_transcription.delta":
            print(ts(), "delta", event.delta, flush=True)
        elif event.type == "conversation.item.input_audio_transcription.completed":
            print(ts(), "completed", flush=True)
            if recording_finished:
                break
        elif event.type == "error":
            raise RuntimeError(event)
        else:
            print(ts(), "Event type:", event.type, flush=True)


with client.realtime.connect(extra_query=dict(intent="transcription")) as connection:
    connection.session.update(
        session=dict(
            type="transcription",
            audio=dict(
                input=dict(
                    format=dict(type="audio/pcm", rate=SAMPLE_RATE),
                    transcription=dict(
                        model=model,
                        language="en",
                    ),
                )
            ),
        )
    )

    receiver_thread = threading.Thread(target=receive_events)
    receiver_thread.start()

    print(f"Recording {RECORD_SECONDS} seconds...")
    with RawInputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=BLOCK_SIZE,
    ) as stream:
        stop_at = time.monotonic() + RECORD_SECONDS

        while time.monotonic() < stop_at:
            audio_chunk, overflowed = stream.read(BLOCK_SIZE)
            if overflowed:
                print("Input overflowed")
            connection.input_audio_buffer.append(
                audio=base64.b64encode(bytes(audio_chunk)).decode("ascii")
            )

    print(ts(), "commit", flush=True)
    print("Waiting for transcript...")
    recording_finished = True
    connection.input_audio_buffer.commit()
    receiver_thread.join()
