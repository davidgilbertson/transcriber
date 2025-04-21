# %%
from pathlib import Path
import os
import pandas as pd
from deepgram import DeepgramClient, PrerecordedOptions
from openai import OpenAI
from pydub import AudioSegment

from utils import stopwatch

file = Path("last_recording.wav")

dg_client = DeepgramClient(api_key=os.environ["DG_API_KEY"])
oai = OpenAI()


for model in [
    "gpt-4o-transcribe",
    # "gpt-4o-mini-transcribe",
]:
    with stopwatch(model):
        oai_transcript = oai.audio.transcriptions.create(
            model=model,
            file=file,
            language="en",
            response_format="text",
        ).strip()
        print(oai_transcript)

# Send MP3 to gpt-4o-transcribe and time the transcription
with stopwatch("gpt-4o-transcribe (MP3)"):
    mp3_file = Path("last_recording.mp3")
    audio = AudioSegment.from_wav(file)
    audio.export(mp3_file, format="mp3")
    mp3_transcript = oai.audio.transcriptions.create(
        model="gpt-4o-transcribe",
        file=mp3_file,
        language="en",
        response_format="text",
    ).strip()
    print(mp3_transcript)

with stopwatch("DeepGram"):
    response_raw = dg_client.listen.rest.v("1").transcribe_file(
        source={"buffer": file.read_bytes()},
        options=PrerecordedOptions(
            model="nova-3",
            diarize=True,
            smart_format=True,
            filler_words=True,
        ),
    )
    dg_transcript = response_raw.results.channels[0].alternatives[0].transcript
    print(dg_transcript)
