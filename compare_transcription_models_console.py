from datetime import datetime
import html
import io
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
import threading
from timeit import default_timer

from recorder import Recorder
from stt import Model, speech_to_text


MODELS: list[Model] = [
    "gpt-4o-mini-transcribe-2025-12-15",
    # "gpt-4o-transcribe",
    "mai-transcribe-1",
    # "scribe_v2",
    "stt-async-v4",
    "chirp_3",
    "gemini-3-flash-preview",
]

PRIVATE_DIR = Path(".private")
LAST_RECORDING_PATH = PRIVATE_DIR / "last_recording.wav"
RESULTS_PATH = PRIVATE_DIR / "transcription_model_results.json"
HTML_PATH = PRIVATE_DIR / "transcription_diff_views.html"
TOKEN_RE = re.compile(r"\w+|[^\w\s]|\s+")
MODEL_PRICING: dict[Model, dict[str, str]] = {
    "gpt-4o-mini-transcribe-2025-12-15": dict(
        price="$0.18/hr",
        note="OpenAI estimated $0.003/min",
        url="https://platform.openai.com/docs/pricing/",
    ),
    "gpt-4o-transcribe": dict(
        price="$0.36/hr",
        note="OpenAI estimated $0.006/min",
        url="https://platform.openai.com/docs/pricing/",
    ),
    "mai-transcribe-1": dict(
        price="~$0.36/hr",
        note="Azure says LLM Speech shares Fast Transcription pricing; public page hides exact figure",
        url="https://azure.microsoft.com/en-us/pricing/details/cognitive-services/speech-services/",
    ),
    "scribe_v2": dict(
        price="$0.40/hr",
        note="ElevenLabs additional-hour API rate",
        url="https://elevenlabs.io/pricing/api?price.section=speech_to_text",
    ),
    "stt-async-v4": dict(
        price="~$0.10/hr",
        note="Soniox async pricing",
        url="https://soniox.com/pricing/",
    ),
    "chirp_3": dict(
        price="$0.96/hr",
        note="Google $0.016/min for standard v2 models incl. Chirp",
        url="https://cloud.google.com/speech-to-text/pricing?hl=en",
    ),
    # "gemini-3-flash-preview": dict(
    #     price="~$0.12/hr + output",
    #     note="Gemini API audio input at $1/1M tokens; audio is 32 tokens/s",
    #     url="https://ai.google.dev/gemini-api/docs/pricing",
    # ),
}

recorder = Recorder()


def start():
    recorder.start()
    print("Recording. Press Enter to stop.")

    def wait_for_enter():
        input()
        stop()

    threading.Thread(target=wait_for_enter, daemon=True).start()


def stop():
    wav_bytes = recorder.stop()
    PRIVATE_DIR.mkdir(exist_ok=True)
    LAST_RECORDING_PATH.write_bytes(wav_bytes.getbuffer())
    return compare_wav_bytes(wav_bytes.getvalue())


def compare_last_recording():
    compare_wav_bytes(LAST_RECORDING_PATH.read_bytes())


def compare_wav_bytes(audio_bytes: bytes):
    PRIVATE_DIR.mkdir(exist_ok=True)
    result = dict(recorded_at=datetime.now().isoformat(timespec="seconds"))

    for model in MODELS:
        print(f"> Calling {model}...")
        started_at = default_timer()
        try:
            text = speech_to_text(io.BytesIO(audio_bytes), model=model)
            print(text)
            print()
            result[model] = dict(
                text=text,
                response_time_s=round(default_timer() - started_at, 2),
            )
        except Exception as exc:
            print(f"Skipping {model}. ERROR: {exc}")
            # result[model] = dict(
            #     error=str(exc),
            #     response_time_s=round(default_timer() - started_at, 2),
            # )

    if RESULTS_PATH.exists():
        results = json.loads(RESULTS_PATH.read_text())
    else:
        results = []

    results.append(result)
    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    write_diff_html(results)
    print(f"Saved to {RESULTS_PATH}")
    print(f"Updated {HTML_PATH}")
    return result


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text)


def changed_indexes(
    root_tokens: list[str], other_tokens: list[str]
) -> tuple[set[int], set[int]]:
    matcher = SequenceMatcher(a=root_tokens, b=other_tokens)
    root_changes = set()
    other_changes = set()

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        root_changes.update(range(i1, i2))
        other_changes.update(range(j1, j2))

    return root_changes, other_changes


def render_text(tokens: list[str], changed: set[int]) -> str:
    parts = []
    for i, token in enumerate(tokens):
        escaped = html.escape(token)
        if i in changed and not token.isspace():
            parts.append(f'<span class="changed">{escaped}</span>')
        else:
            parts.append(escaped)
    return "".join(parts)


def get_text(entry: dict) -> str:
    return entry.get("text") or entry.get("error") or ""


def write_diff_html(results: list[dict]):
    max_response_time_s = max(
        entry["response_time_s"]
        for run in results
        for model, entry in run.items()
        if model != "recorded_at"
    )
    run_sections = []

    for run in reversed(results):
        model_names = [key for key in run if key != "recorded_at"]
        root_model = model_names[0]
        root_entry = run[root_model]
        root_tokens = tokenize(get_text(root_entry))
        root_highlights = set()
        model_rows = []

        for model in model_names[1:]:
            entry = run[model]
            other_tokens = tokenize(get_text(entry))
            root_changes, other_changes = changed_indexes(root_tokens, other_tokens)
            root_highlights.update(root_changes)
            width_pct = entry["response_time_s"] / max_response_time_s * 100
            model_rows.append(
                f"""
                <div class="row">
                  <div class="meta">
                    <div class="name">{html.escape(model)}</div>
                    <div class="time">{entry["response_time_s"]}s</div>
                    <div class="bar" style="width: {width_pct:.1f}%"></div>
                  </div>
                  <div class="text">{render_text(other_tokens, other_changes)}</div>
                </div>
                """
            )

        root_width_pct = root_entry["response_time_s"] / max_response_time_s * 100
        run_sections.append(
            f"""
            <section class="run">
              <div class="run_header">{html.escape(run["recorded_at"])}</div>
              <div class="row root">
                <div class="meta">
                  <div class="name">{html.escape(root_model)}</div>
                  <div class="time">{root_entry["response_time_s"]}s</div>
                  <div class="bar" style="width: {root_width_pct:.1f}%"></div>
                </div>
                <div class="text">{render_text(root_tokens, root_highlights)}</div>
              </div>
              {''.join(model_rows)}
            </section>
            """
        )

    pricing_rows = "".join(
        f"""
        <tr>
          <td>{html.escape(model)}</td>
          <td>{html.escape(info["price"])}</td>
          <td>{html.escape(info["note"])}</td>
        </tr>
        """
        for model, info in MODEL_PRICING.items()
    )

    HTML_PATH.write_text(
        f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Transcription Diffs</title>
  <style>
    :root {{
      --bg: #f8fafc;
      --panel: #ffffff;
      --border: #dbe4ee;
      --text: #0f172a;
      --muted: #64748b;
      --changed: #fde68a;
      --root: #e0f2fe;
      --bar: #f44336;
    }}

    body {{
      margin: 0;
      padding: 20px;
      background: var(--bg);
      color: var(--text);
      font: 15px/1.45 "Segoe UI", sans-serif;
    }}

    main {{
      max-width: 1400px;
      margin: 0 auto;
    }}

    .run {{
      margin-bottom: 16px;
      border: 1px solid var(--border);
      background: var(--panel);
      overflow: hidden;
    }}

    .pricing {{
      margin-bottom: 16px;
      border: 1px solid var(--border);
      background: var(--panel);
      padding: 10px 14px;
    }}

    .pricing h2 {{
      margin: 0 0 6px;
      font-size: 15px;
    }}

    .pricing p {{
      margin: 0 0 8px;
      color: var(--muted);
      font-size: 13px;
    }}

    .pricing table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}

    .pricing th,
    .pricing td {{
      padding: 4px 8px;
      border: 1px solid var(--border);
      text-align: left;
      vertical-align: top;
    }}

    .pricing th {{
      background: #eef2f7;
    }}

    .run_header {{
      padding: 10px 14px;
      background: #eef2f7;
      color: var(--muted);
      font-size: 13px;
    }}

    .row {{
      display: grid;
      grid-template-columns: 270px 1fr;
      border-top: 1px solid var(--border);
    }}

    .row.root {{
      background: var(--root);
    }}

    .meta {{
      position: relative;
      padding: 6px 7px;
      border-right: 1px solid var(--border);
    }}

    .name {{
      font-weight: 600;
    }}

    .time {{
      margin-top: 4px;
      color: var(--muted);
      font-size: 13px;
    }}

    .text {{
      padding: 6px 7px;
      white-space: pre-wrap;
      word-break: break-word;
    }}

    .changed {{
      background: var(--changed);
    }}

    .bar {{
      position: absolute;
      left: 0;
      bottom: 0;
      height: 4px;
      background: var(--bar);
    }}
  </style>
</head>
<body>
  <main>
    <section class="pricing">
      <h2>Approximate Model Pricing</h2>
      <p>All prices normalized to approximate USD per audio hour. This is intentionally rough so everything fits on one scale.</p>
      <table>
        <thead>
          <tr>
            <th>Model</th>
            <th>Approx USD / hour</th>
            <th>Basis</th>
          </tr>
        </thead>
        <tbody>
          {pricing_rows}
        </tbody>
      </table>
    </section>
    {''.join(run_sections)}
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )


print("Run start(), then press Enter.")
print("Or run compare_last_recording().")
