from __future__ import annotations

from pathlib import Path
from timeit import default_timer

import google.auth
from google.api_core.client_options import ClientOptions
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech


AUDIO_BYTES = Path("last_recording.wav").read_bytes()

# Uses ADC automatically (gcloud application-default login, or service account env var if you set it)
creds, project_id = google.auth.default()

start = default_timer()
client = SpeechClient(
    credentials=creds,
    client_options=ClientOptions(api_endpoint="us-speech.googleapis.com"),
)
print(f"Duration: {default_timer() - start} seconds")

start = default_timer()

resp = client.recognize(
    cloud_speech.RecognizeRequest(
        recognizer=f"projects/{project_id}/locations/us/recognizers/_",
        config=cloud_speech.RecognitionConfig(
            model="chirp_3",
            language_codes=["en-US"],
            auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
        ),
        content=AUDIO_BYTES,
    )
)

print(resp.results[0].alternatives[0].transcript)
print(f"Duration: {default_timer() - start} seconds")
