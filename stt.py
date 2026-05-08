import io
import json
import os
import time
import uuid
from typing import Literal
from urllib import request

from dotenv import load_dotenv

load_dotenv()

Model = Literal[
    "gpt-4o-mini-transcribe-2025-12-15",
    "gpt-4o-transcribe",
    "mai-transcribe-1",
    "scribe_v2",
    "stt-async-v4",
    "chirp_3",
    "gemini-3-flash-preview",
]


def openai_stt(
    wav_bytes: io.BytesIO,
    model: Literal["gpt-4o-mini-transcribe-2025-12-15", "gpt-4o-transcribe"],
) -> str:
    from openai import OpenAI

    wav_bytes.seek(0)
    oai = OpenAI()
    text = oai.audio.transcriptions.create(
        model=model,
        file=("audio.wav", wav_bytes),
        language="en",
        response_format="text",
        prompt="Use unicode characters where appropriate, like 'CO₂' and '45°'. Use UK spelling, not US spelling.",
    )
    return text


def microsoft_stt(wav_bytes: io.BytesIO, model: Literal["mai-transcribe-1"]) -> str:
    api_key = os.environ["AZURE_SPEECH_API_KEY"]
    endpoint = os.environ["AZURE_SPEECH_ENDPOINT"].rstrip("/")

    boundary = f"----transcriber-{uuid.uuid4().hex}"
    definition = json.dumps(
        dict(
            enhancedMode=dict(
                enabled=True,
                task="transcribe",
                model=model,
            ),
        )
    )
    audio_bytes = wav_bytes.getvalue()
    parts = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="audio"; filename="audio.wav"\r\n',
        b"Content-Type: audio/wav\r\n\r\n",
        audio_bytes,
        b"\r\n",
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="definition"\r\n\r\n',
        definition.encode(),
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    body = b"".join(parts)

    req = request.Request(
        url=f"{endpoint}/speechtotext/transcriptions:transcribe?api-version=2025-10-15",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Ocp-Apim-Subscription-Key": api_key,
        },
        method="POST",
    )

    with request.urlopen(req) as response:
        payload = json.loads(response.read())

    return payload["combinedPhrases"][0]["text"]


def elevenlabs_stt(wav_bytes: io.BytesIO, model: Literal["scribe_v2"]) -> str:
    api_key = os.environ["ELEVENLABS_API_KEY"]

    boundary = f"----transcriber-{uuid.uuid4().hex}"
    audio_bytes = wav_bytes.getvalue()
    parts = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n',
        b"Content-Type: audio/wav\r\n\r\n",
        audio_bytes,
        b"\r\n",
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="model_id"\r\n\r\n',
        model.encode(),
        b"\r\n",
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="language_code"\r\n\r\n',
        b"en",
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    body = b"".join(parts)

    req = request.Request(
        url="https://api.elevenlabs.io/v1/speech-to-text",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "xi-api-key": api_key,
        },
        method="POST",
    )

    with request.urlopen(req) as response:
        payload = json.loads(response.read())

    return payload["text"]


def soniox_stt(wav_bytes: io.BytesIO, model: Literal["stt-async-v4"]) -> str:
    api_key = os.environ["SONIOX_API_KEY"]
    boundary = f"----transcriber-{uuid.uuid4().hex}"
    audio_bytes = wav_bytes.getvalue()
    upload_body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n',
            b"Content-Type: audio/wav\r\n\r\n",
            audio_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )

    upload_req = request.Request(
        url="https://api.soniox.com/v1/files",
        data=upload_body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with request.urlopen(upload_req) as response:
        file_id = json.loads(response.read())["id"]

    transcription_req = request.Request(
        url="https://api.soniox.com/v1/transcriptions",
        data=json.dumps(
            dict(
                model=model,
                file_id=file_id,
                language_hints=["en"],
            )
        ).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with request.urlopen(transcription_req) as response:
        transcription_id = json.loads(response.read())["id"]

    while True:
        status_req = request.Request(
            url=f"https://api.soniox.com/v1/transcriptions/{transcription_id}",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with request.urlopen(status_req) as response:
            payload = json.loads(response.read())

        if payload["status"] == "completed":
            break
        if payload["status"] == "error":
            raise RuntimeError(payload["error_message"])
        time.sleep(1)

    transcript_req = request.Request(
        url=f"https://api.soniox.com/v1/transcriptions/{transcription_id}/transcript",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    with request.urlopen(transcript_req) as response:
        return json.loads(response.read())["text"]


def google_stt(wav_bytes: io.BytesIO, model: Literal["chirp_3"]) -> str:
    from google.api_core.client_options import ClientOptions
    from google.cloud.speech_v2 import SpeechClient
    from google.cloud.speech_v2.types import cloud_speech

    client = SpeechClient(
        client_options=ClientOptions(
            api_endpoint="asia-northeast1-speech.googleapis.com"
        ),
    )
    resp = client.recognize(
        cloud_speech.RecognizeRequest(
            recognizer="projects/transcriber-707/locations/asia-northeast1/recognizers/_",
            config=cloud_speech.RecognitionConfig(
                model=model,
                language_codes=["en-US"],
                auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
            ),
            content=wav_bytes.getvalue(),
        )
    )

    return resp.results[0].alternatives[0].transcript


def gemini_stt(wav_bytes: io.BytesIO, model: Literal["gemini-3-flash-preview"]) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client()
    response = client.models.generate_content(
        model=model,
        contents=[
            "Generate a transcript of the speech. Use UK spelling, not US spelling.",
            types.Part.from_bytes(
                data=wav_bytes.getvalue(),
                mime_type="audio/wav",
            ),
        ],
    )
    return response.text


def speech_to_text(
    wav_bytes: io.BytesIO,
    model: Model = "gpt-4o-mini-transcribe-2025-12-15",
) -> str:
    if model.startswith("gpt"):
        text = openai_stt(wav_bytes, model)
    elif model.startswith("mai-"):
        text = microsoft_stt(wav_bytes, model)
    elif model.startswith("scribe"):
        text = elevenlabs_stt(wav_bytes, model)
    elif model.startswith("stt-async"):
        text = soniox_stt(wav_bytes, model)
    elif model.startswith("gemini"):
        text = gemini_stt(wav_bytes, model)
    else:
        text = google_stt(wav_bytes, model)

    return text.strip().replace("\n", "⏎")
