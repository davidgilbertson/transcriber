import io
from timeit import default_timer


def openai_stt(wav_bytes: io.BytesIO, model: str) -> str:
    from openai import OpenAI

    oai = OpenAI()
    text = oai.audio.transcriptions.create(
        model=model,
        file=("audio.wav", wav_bytes),
        language="en",
        response_format="text",
        prompt="Use unicode characters where appropriate, like 'CO₂' and '45°'. Use UK spelling, not US spelling.",
    )
    return text


def google_stt(wav_bytes: io.BytesIO, model: str) -> str:
    import google.auth
    from google.api_core.client_options import ClientOptions
    from google.cloud.speech_v2 import SpeechClient
    from google.cloud.speech_v2.types import cloud_speech

    # Uses ADC automatically
    creds, project_id = google.auth.default()

    client = SpeechClient(
        credentials=creds,
        client_options=ClientOptions(api_endpoint="us-speech.googleapis.com"),
    )
    resp = client.recognize(
        cloud_speech.RecognizeRequest(
            recognizer=f"projects/{project_id}/locations/us/recognizers/_",
            config=cloud_speech.RecognitionConfig(
                model=model,
                language_codes=["en-US"],
                auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
            ),
            content=wav_bytes.getvalue(),
        )
    )

    return resp.results[0].alternatives[0].transcript


def speech_to_text(
    wav_bytes: io.BytesIO,
    model="gpt-4o-mini-transcribe-2025-12-15",
) -> str:
    if model.startswith("gpt"):
        text = openai_stt(wav_bytes, model)
    else:
        text = google_stt(wav_bytes, model)

    return text.strip().replace("\n", "⏎")


if __name__ == "__main__":
    with open("last_recording.wav", "rb") as f:
        audio_data = io.BytesIO(f.read())

    models = [
        "gpt-4o-mini-transcribe-2025-12-15",
        "gpt-4o-transcribe",
        "chirp_3",
    ]

    for model in models:
        audio_data.seek(0)
        start = default_timer()
        try:
            result = speech_to_text(audio_data, model=model)
            print(f"{model} ({default_timer() - start:.2f}s):\n{result}")
        except Exception as e:
            print(f"{model} ({default_timer() - start:.2f}s): Error: {e}")
