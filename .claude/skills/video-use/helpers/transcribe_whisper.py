"""Local Whisper backend for video-use (drop-in replacement for ElevenLabs Scribe).

Runs faster-whisper on a mono 16kHz wav and emits a transcript JSON in the
same shape Scribe returns, so pack_transcripts.py, timeline_view.py and
render.py --build-subtitles work unchanged:

    {"text": "...", "language_code": "ja",
     "words": [{"text": "word", "start": 1.23, "end": 1.61, "type": "word",
                "speaker_id": "speaker_0"},
               {"text": " ", "start": 1.61, "end": 2.20, "type": "spacing"}, ...]}

Differences from Scribe you should know about:
  * No speaker diarization. Every word is tagged speaker_0. Fine for solo
    talking heads; for interviews pass --num-speakers to Scribe instead.
  * No audio events ((laughs), (applause)).
  * Whisper tends to drop fillers ("umm", "えー"). A language-specific
    initial prompt nudges it to keep them, but it is not verbatim.
  * Word timestamps are estimated by cross-attention alignment, so they can
    drift ~50-150ms. Keep cut padding at the upper end of the 30-200ms window.
  * For Japanese/Chinese the "words" are sub-word chunks (1-3 characters).
    That is still fine for choosing cut points.

Free, offline, no API key. Models are downloaded once from Hugging Face.

Usage (normally invoked through transcribe.py --engine whisper):
    python helpers/transcribe_whisper.py <audio.wav> -o out.json --model large-v3-turbo
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_MODEL = "large-v3-turbo"

# Fillers Whisper otherwise normalizes away. The editor wants them: they are
# exactly the words a cut should remove.
VERBATIM_PROMPTS = {
    "ja": "えー、あの、その、まあ、えっと、なんか、はい。",
    "en": "Umm, uh, so, like, you know, hmm, okay.",
}


_MODEL_CACHE: dict[tuple[str, str, str], object] = {}


def _load_model(model_name: str, device: str, compute_type: str):
    """Load once per process; batch mode transcribes many files with one model."""
    key = (model_name, device, compute_type)
    if key not in _MODEL_CACHE:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            sys.exit(
                "faster-whisper is not installed. Run: pip install faster-whisper "
                "(or: uv pip install faster-whisper) inside the video-use environment."
            )
        _MODEL_CACHE[key] = WhisperModel(model_name, device=device, compute_type=compute_type)
    return _MODEL_CACHE[key]


def _detect_language(model, audio_path: Path) -> str | None:
    detect = getattr(model, "detect_language", None)
    if detect is None:
        return None
    try:
        result = detect(str(audio_path))
    except Exception:
        return None
    # faster-whisper >= 1.1 returns (language, probability, all_probs)
    if isinstance(result, tuple) and result:
        return result[0]
    return None


def call_whisper(
    audio_path: Path,
    language: str | None = None,
    model_name: str = DEFAULT_MODEL,
    device: str = "auto",
    compute_type: str = "auto",
    speaker_id: str = "speaker_0",
    verbatim_prompt: bool = True,
    beam_size: int = 5,
) -> dict:
    """Transcribe one audio file and return a Scribe-shaped dict."""
    model = _load_model(model_name, device, compute_type)

    lang = language or _detect_language(model, audio_path)
    prompt = VERBATIM_PROMPTS.get(lang or "") if verbatim_prompt else None

    segments, info = model.transcribe(
        str(audio_path),
        language=lang,
        beam_size=beam_size,
        word_timestamps=True,
        vad_filter=True,
        condition_on_previous_text=False,
        initial_prompt=prompt,
    )

    words: list[dict] = []
    text_parts: list[str] = []
    prev_end: float | None = None
    for seg in segments:
        text_parts.append(seg.text.strip())
        for w in seg.words or []:
            token = w.word.strip()
            if not token:
                continue
            start = round(float(w.start), 3)
            end = round(float(w.end), 3)
            if prev_end is not None and start > prev_end:
                words.append({
                    "text": " ",
                    "start": prev_end,
                    "end": start,
                    "type": "spacing",
                })
            words.append({
                "text": token,
                "start": start,
                "end": end,
                "type": "word",
                "speaker_id": speaker_id,
                "logprob": round(float(w.probability), 4),
            })
            prev_end = max(end, start)

    return {
        "text": " ".join(p for p in text_parts if p),
        "language_code": getattr(info, "language", lang),
        "language_probability": round(float(getattr(info, "language_probability", 0.0)), 4),
        "engine": "faster-whisper",
        "model": model_name,
        "words": words,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Transcribe a wav with local faster-whisper (Scribe-shaped JSON)")
    ap.add_argument("audio", type=Path, help="Mono 16kHz wav (transcribe.py extracts this for you)")
    ap.add_argument("-o", "--output", type=Path, required=True, help="Output transcript JSON path")
    ap.add_argument("--language", default=None, help="ISO code (ja, en, ...). Omit to auto-detect.")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help=f"faster-whisper model name or CTranslate2 dir (default: {DEFAULT_MODEL}; "
                         "use 'small' or 'medium' on slow CPUs)")
    ap.add_argument("--device", default="auto", help="auto | cpu | cuda")
    ap.add_argument("--compute-type", default="auto", help="auto | int8 | float16 | float32")
    ap.add_argument("--no-verbatim-prompt", action="store_true",
                    help="Do not prime the model with fillers")
    args = ap.parse_args()

    if not args.audio.exists():
        sys.exit(f"audio not found: {args.audio}")

    payload = call_whisper(
        args.audio,
        language=args.language,
        model_name=args.model,
        device=args.device,
        compute_type=args.compute_type,
        verbatim_prompt=not args.no_verbatim_prompt,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    n = sum(1 for w in payload["words"] if w["type"] == "word")
    print(f"saved: {args.output} ({n} words, language={payload['language_code']})")


if __name__ == "__main__":
    main()
