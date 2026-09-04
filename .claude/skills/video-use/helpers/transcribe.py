"""Transcribe a video with ElevenLabs Scribe or local Whisper.

Extracts mono 16kHz audio via ffmpeg, then either uploads to Scribe
(verbatim + diarize + audio events + word-level timestamps) or runs
faster-whisper locally (see transcribe_whisper.py), and writes the
Scribe-shaped response to <edit_dir>/transcripts/<video_stem>.json.

Engine selection (--engine, or VIDEO_USE_TRANSCRIBER env var):
    auto     (default) Scribe if an ElevenLabs key is configured, else whisper
    scribe   ElevenLabs Scribe (needs ELEVENLABS_API_KEY; paid, diarization)
    whisper  faster-whisper on this machine (free, offline, no diarization)

Cached: if the output file already exists, transcription is skipped.

Usage:
    python helpers/transcribe.py <video_path>
    python helpers/transcribe.py <video_path> --engine whisper --whisper-model small
    python helpers/transcribe.py <video_path> --edit-dir /custom/edit
    python helpers/transcribe.py <video_path> --language ja
    python helpers/transcribe.py <video_path> --num-speakers 2
"""

from __future__ import annotations

import argparse
import array
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import requests


SCRIBE_URL = "https://api.elevenlabs.io/v1/speech-to-text"


ENGINES = ("auto", "scribe", "whisper")


def find_api_key() -> str:
    """ELEVENLABS_API_KEY from .env (repo root or cwd) or the environment. '' if absent."""
    for candidate in [Path(__file__).resolve().parent.parent / ".env", Path(".env")]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == "ELEVENLABS_API_KEY":
                    return v.strip().strip('"').strip("'")
    return os.environ.get("ELEVENLABS_API_KEY", "")


def load_api_key() -> str:
    v = find_api_key()
    if not v:
        sys.exit("ELEVENLABS_API_KEY not found in .env or environment "
                 "(or pass --engine whisper to transcribe locally)")
    return v


def resolve_engine(engine: str | None = None) -> tuple[str, str]:
    """Return (engine, api_key). api_key is '' for whisper."""
    engine = (engine or os.environ.get("VIDEO_USE_TRANSCRIBER") or "auto").lower()
    if engine not in ENGINES:
        sys.exit(f"unknown engine {engine!r}; choose one of {', '.join(ENGINES)}")
    if engine == "whisper":
        return "whisper", ""
    key = find_api_key()
    if engine == "scribe":
        if not key:
            load_api_key()  # exits with the standard message
        return "scribe", key
    return ("scribe", key) if key else ("whisper", "")


def count_audio_tracks(video_path: Path) -> int:
    """How many audio streams the container holds."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(video_path)],
        capture_output=True, text=True,
    )
    return len([ln for ln in out.stdout.splitlines() if ln.strip()])


def peak_dbfs(wav_path: Path) -> float:
    """Peak level of a 16-bit PCM wav, in dBFS. -inf for digital silence."""
    peak = 0
    with wave.open(str(wav_path), "rb") as w:
        # A chunk at a time: batch mode runs several of these at once, and a two-hour
        # take is 230 MB of 16 kHz mono before the array copy doubles it.
        while frames := w.readframes(1 << 16):
            samples = array.array("h", frames)
            peak = max(peak, max(samples), -min(samples))
    return 20 * math.log10(peak / 32768) if peak > 0 else float("-inf")


def extract_audio(video_path: Path, dest: Path, audio_track: int = 0) -> None:
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-map", f"0:a:{audio_track}",
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def call_scribe(
    audio_path: Path,
    api_key: str,
    language: str | None = None,
    num_speakers: int | None = None,
) -> dict:
    data: dict[str, str] = {
        "model_id": "scribe_v1",
        "diarize": "true",
        "tag_audio_events": "true",
        "timestamps_granularity": "word",
    }
    if language:
        data["language_code"] = language
    if num_speakers:
        data["num_speakers"] = str(num_speakers)

    with open(audio_path, "rb") as f:
        resp = requests.post(
            SCRIBE_URL,
            headers={"xi-api-key": api_key},
            files={"file": (audio_path.name, f, "audio/wav")},
            data=data,
            timeout=1800,
        )

    if resp.status_code != 200:
        raise RuntimeError(f"Scribe returned {resp.status_code}: {resp.text[:500]}")

    return resp.json()


def transcript_path(edit_dir: Path, video: Path, audio_track: int = 0) -> Path:
    """Where a video's transcript lands.

    The track belongs in the name, or a rerun with --audio-track hands back the transcript of
    the track it is meant to replace. Track 0 keeps the plain name, so transcripts made before
    the flag existed stay valid. Batch mode tests its cache with this too — one function, so
    the two cannot drift apart.
    """
    suffix = "" if audio_track == 0 else f".track{audio_track}"
    return edit_dir / "transcripts" / f"{video.stem}{suffix}.json"


def transcribe_one(
    video: Path,
    edit_dir: Path,
    api_key: str,
    language: str | None = None,
    num_speakers: int | None = None,
    verbose: bool = True,
    audio_track: int = 0,
    engine: str = "scribe",
    whisper_model: str | None = None,
) -> Path:
    """Transcribe a single video. Returns path to transcript JSON.

    engine is "scribe" (upload to ElevenLabs, api_key required) or "whisper"
    (local faster-whisper; api_key ignored). Use resolve_engine() to pick.

    Cached: returns existing path immediately if the transcript already exists.
    """
    transcripts_dir = edit_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcript_path(edit_dir, video, audio_track)

    if out_path.exists():
        if verbose:
            print(f"cached: {out_path.name}")
        return out_path

    if verbose:
        print(f"  extracting audio from {video.name}", flush=True)

    n_tracks = count_audio_tracks(video)
    if n_tracks > 1 and verbose:
        print(f"  note: {video.name} has {n_tracks} audio tracks, using track "
              f"{audio_track + 1} (--audio-track to change)", flush=True)

    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{video.stem}.wav"
        extract_audio(video, audio, audio_track)

        # Uploading silence costs the same as uploading speech and returns
        # nothing, so catch the wrong-track case before paying for it.
        peak = peak_dbfs(audio)
        if peak < -60.0:
            raise RuntimeError(
                f"track {audio_track + 1} of {video.name} is silent "
                f"(peak {peak:.1f} dBFS) - not uploading. "
                + (f"The file has {n_tracks} audio tracks; try --audio-track "
                   + " or ".join(str(i) for i in range(n_tracks) if i != audio_track) + "."
                   if n_tracks > 1 else "Check the source audio.")
            )

        if engine == "whisper":
            from transcribe_whisper import DEFAULT_MODEL, call_whisper

            model_name = whisper_model or os.environ.get("VIDEO_USE_WHISPER_MODEL") or DEFAULT_MODEL
            if verbose:
                print(f"  transcribing {video.stem}.wav locally (faster-whisper {model_name})", flush=True)
            payload = call_whisper(audio, language=language, model_name=model_name)
        else:
            size_mb = audio.stat().st_size / (1024 * 1024)
            if verbose:
                print(f"  uploading {video.stem}.wav ({size_mb:.1f} MB)", flush=True)
            payload = call_scribe(audio, api_key, language, num_speakers)

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    dt = time.time() - t0

    if verbose:
        kb = out_path.stat().st_size / 1024
        print(f"  saved: {out_path.name} ({kb:.1f} KB) in {dt:.1f}s")
        if isinstance(payload, dict) and "words" in payload:
            print(f"    words: {len(payload['words'])}")

    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Transcribe a video with ElevenLabs Scribe or local Whisper")
    ap.add_argument("video", type=Path, help="Path to video file")
    ap.add_argument(
        "--engine",
        choices=ENGINES,
        default=None,
        help="auto (default: Scribe if a key exists, else whisper) | scribe | whisper. "
             "Env VIDEO_USE_TRANSCRIBER overrides the default.",
    )
    ap.add_argument(
        "--whisper-model",
        default=None,
        help="faster-whisper model for --engine whisper (default large-v3-turbo; "
             "env VIDEO_USE_WHISPER_MODEL). Try 'small' on a slow CPU.",
    )
    ap.add_argument(
        "--edit-dir",
        type=Path,
        default=None,
        help="Edit output directory (default: <video_parent>/edit)",
    )
    ap.add_argument(
        "--language",
        type=str,
        default=None,
        help="Optional ISO language code (e.g., 'en'). Omit to auto-detect.",
    )
    ap.add_argument(
        "--num-speakers",
        type=int,
        default=None,
        help="Optional number of speakers when known. Improves diarization accuracy.",
    )
    ap.add_argument(
        "--audio-track",
        type=int,
        default=0,
        help="Zero-based audio track to transcribe. OBS writes the game on track 0 "
             "and the mic on track 1; without this ffmpeg applies its default audio "
             "stream selection, which picks the track with the most channels.",
    )
    args = ap.parse_args()

    video = args.video.resolve()
    if not video.exists():
        sys.exit(f"video not found: {video}")

    edit_dir = (args.edit_dir or (video.parent / "edit")).resolve()
    engine, api_key = resolve_engine(args.engine)

    transcribe_one(
        video=video,
        edit_dir=edit_dir,
        api_key=api_key,
        language=args.language,
        num_speakers=args.num_speakers,
        audio_track=args.audio_track,
        engine=engine,
        whisper_model=args.whisper_model,
    )


if __name__ == "__main__":
    main()
