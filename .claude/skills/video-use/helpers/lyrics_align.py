"""Align KNOWN lyrics (or any script) to a video-use transcript and emit subtitles.

Use this when the user already has the exact text — song lyrics, a read
script, a speech manuscript — and only needs timing. Whisper's own text is
thrown away; only its word timestamps are kept. Each lyric line is matched
to the recognised characters with a global sequence alignment (phonetic:
everything is compared as hiragana), so mis-heard words, missing fillers and
hallucinated fragments do not break the timing.

Inputs
    transcript JSON from transcribe.py (Scribe or --engine whisper)
    lyrics text: one subtitle line per text line; blank lines / lines that are
    only "☆" mark section breaks and are skipped

Outputs
    <out>.srt      plain subtitles
    <out>.ass      styled subtitles (Japanese-capable font, bottom centre)
    <out>.json     per-line timing + confidence, for review / hand-tweaks

Usage
    python helpers/lyrics_align.py edit/transcripts/song.json lyrics.txt -o edit/lyrics
    python helpers/lyrics_align.py ... --font "Hiragino Sans" --font-size 64
    python helpers/lyrics_align.py ... --hold 4.0 --lead 0.2
    python helpers/lyrics_align.py ... --display display.txt   # show this text, align with lyrics.txt

pykakasi (pip install pykakasi) is used to read kanji in the transcript as
hiragana. Without it only kana/latin characters take part in matching, which
is still fine when the transcript is mostly kana (songs, Whisper with
--language ja often emits kana for sung vocals).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

try:  # optional
    import pykakasi  # type: ignore

    _KKS = pykakasi.kakasi()
except Exception:  # pragma: no cover - optional dependency
    _KKS = None


# --------------------------------------------------------------------------- text

_SMALL = str.maketrans("ぁぃぅぇぉゃゅょゎ", "あいうえおやゆよわ")
_FOLD = str.maketrans({"ぢ": "じ", "づ": "ず", "を": "お", "ゐ": "い", "ゑ": "え", "ゔ": "ぶ"})
_SKIP = set(" 　、。，．,.!！?？「」『』（）()[]〈〉《》…・～〜-—ー\"'’‘“”:;")


def katakana_to_hiragana(s: str) -> str:
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)


def to_hiragana(s: str) -> str:
    """Kanji/katakana/romaji-ish text -> hiragana (best effort)."""
    s = unicodedata.normalize("NFKC", s)
    if _KKS is not None and re.search(r"[一-鿿]", s):
        s = "".join(item["hira"] for item in _KKS.convert(s))
    return katakana_to_hiragana(s).lower()


def match_key(ch: str) -> str | None:
    """Character as used for matching, or None if it should be ignored."""
    if ch in _SKIP or ch.isspace():
        return None
    ch = katakana_to_hiragana(ch).translate(_SMALL).translate(_FOLD).lower()
    if ch == "っ":  # sokuon carries no vowel; Whisper places it inconsistently
        return None
    return ch


# --------------------------------------------------------------------------- data

@dataclass
class HypChar:
    key: str
    t0: float
    t1: float


@dataclass
class LyricLine:
    index: int
    display: str
    keys: list[str]


def load_lyrics(path: Path, display_path: Path | None) -> list[LyricLine]:
    raw = [ln.rstrip("\n") for ln in path.read_text(encoding="utf-8").splitlines()]
    disp = None
    if display_path:
        disp = [ln.rstrip("\n") for ln in display_path.read_text(encoding="utf-8").splitlines()]
    lines: list[LyricLine] = []
    j = 0
    for i, ln in enumerate(raw):
        if not ln.strip() or ln.strip() in {"☆", "★", "*", "---"}:
            continue
        keys = [k for k in (match_key(c) for c in to_hiragana(ln)) if k]
        text = ln.strip()
        if disp is not None:
            # display file must have the same non-blank lines in the same order
            while j < len(disp) and (not disp[j].strip() or disp[j].strip() in {"☆", "★", "*", "---"}):
                j += 1
            if j < len(disp):
                text = disp[j].strip()
                j += 1
        lines.append(LyricLine(len(lines), text, keys))
    if not lines:
        sys.exit("no lyric lines found")
    return lines


def load_hyp(path: Path) -> list[HypChar]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[HypChar] = []
    for w in data.get("words", []):
        if w.get("type", "word") != "word":
            continue
        text = (w.get("text") or "").strip()
        if not text:
            continue
        t0, t1 = float(w["start"]), float(w.get("end", w["start"]))
        keys = [k for k in (match_key(c) for c in to_hiragana(text)) if k]
        if not keys:
            continue
        step = max(t1 - t0, 0.05) / len(keys)
        for i, k in enumerate(keys):
            out.append(HypChar(k, t0 + i * step, t0 + (i + 1) * step))
    if not out:
        sys.exit("transcript has no usable words")
    return out


# --------------------------------------------------------------------------- alignment

MATCH, MISMATCH, GAP_REF, GAP_HYP = 3, -2, -2, -1
OUTLIER_WINDOW = 4.0  # seconds; matched chars farther than this from a line's median are ignored


def align(ref: list[str], hyp: list[str]) -> list[int | None]:
    """Semi-global alignment. Returns, for every ref char, the hyp index or None.

    Leading/trailing hyp characters are free (intro chatter, hallucinated
    outro), every ref char must be placed or skipped at a cost.
    """
    n, m = len(ref), len(hyp)
    NEG = -10**9
    score = [[NEG] * (m + 1) for _ in range(n + 1)]
    back = [[0] * (m + 1) for _ in range(n + 1)]  # 0 diag, 1 up (skip ref), 2 left (skip hyp)
    for j in range(m + 1):
        score[0][j] = 0  # free leading hyp
        back[0][j] = 2
    for i in range(1, n + 1):
        score[i][0] = score[i - 1][0] + GAP_REF
        back[i][0] = 1
        ri = ref[i - 1]
        row, prow, brow = score[i], score[i - 1], back[i]
        for j in range(1, m + 1):
            d = prow[j - 1] + (MATCH if ri == hyp[j - 1] else MISMATCH)
            u = prow[j] + GAP_REF
            l = row[j - 1] + (0 if i == n else GAP_HYP)  # free trailing hyp
            if d >= u and d >= l:
                row[j], brow[j] = d, 0
            elif u >= l:
                row[j], brow[j] = u, 1
            else:
                row[j], brow[j] = l, 2
    # best end anywhere in the last row (trailing hyp free)
    j = max(range(m + 1), key=lambda jj: score[n][jj])
    i = n
    result: list[int | None] = [None] * n
    while i > 0:
        b = back[i][j]
        if b == 0:
            if ref[i - 1] == hyp[j - 1]:
                result[i - 1] = j - 1
            i, j = i - 1, j - 1
        elif b == 1:
            i -= 1
        else:
            j -= 1
    return result


# --------------------------------------------------------------------------- timing

def time_lines(lines: list[LyricLine], hyp: list[HypChar], mapping: list[int | None],
               lead: float, hold: float, min_dur: float) -> list[dict]:
    pos = 0
    rows: list[dict] = []
    for ln in lines:
        idxs = [mapping[pos + k] for k in range(len(ln.keys))]
        pos += len(ln.keys)
        hits = [h for h in idxs if h is not None]
        conf = len(hits) / max(len(ln.keys), 1)
        if hits:
            # drop stray matches far from the bulk of the line (a lone character
            # that latched onto another verse), keep the true first/last ones
            times = sorted(hyp[h].t0 for h in hits)
            median = times[len(times) // 2]
            good = [h for h in hits if abs(hyp[h].t0 - median) <= OUTLIER_WINDOW]
            start, end = hyp[min(good)].t0, hyp[max(good)].t1
        else:
            start = end = None
        rows.append({"index": ln.index, "text": ln.display, "chars": len(ln.keys),
                     "matched": len(hits), "confidence": round(conf, 2),
                     "start": start, "end": end, "interpolated": False})

    # Interpolate low-confidence lines between their anchored neighbours
    anchored = [r for r in rows if r["start"] is not None and r["confidence"] >= 0.3]
    if not anchored:
        sys.exit("alignment failed: no line reached 30% character matches")
    for k, r in enumerate(rows):
        if r["start"] is not None and r["confidence"] >= 0.3:
            continue
        prev = next((rows[p] for p in range(k - 1, -1, -1)
                     if rows[p]["start"] is not None and rows[p]["confidence"] >= 0.3), None)
        nxt = next((rows[p] for p in range(k + 1, len(rows))
                    if rows[p]["start"] is not None and rows[p]["confidence"] >= 0.3), None)
        if prev and nxt:
            span_lines = [rows[p] for p in range(rows.index(prev) + 1, rows.index(nxt))]
            total = sum(x["chars"] for x in span_lines) or 1
            t = prev["end"]
            avail = max(nxt["start"] - prev["end"], min_dur * len(span_lines))
            for x in span_lines:
                d = avail * x["chars"] / total
                x["start"], x["end"], x["interpolated"] = t, t + d, True
                t += d
        elif prev:
            r["start"], r["end"], r["interpolated"] = prev["end"], prev["end"] + min_dur, True
        else:
            r["start"], r["end"], r["interpolated"] = max(0.0, nxt["start"] - min_dur), nxt["start"], True

    # Monotonic, lead-in, hold until next line (capped)
    for k, r in enumerate(rows):
        if k and r["start"] < rows[k - 1]["end"]:
            r["start"] = rows[k - 1]["end"]
        if r["end"] < r["start"] + min_dur:
            r["end"] = r["start"] + min_dur
    for k, r in enumerate(rows):
        r["show"] = max(0.0, r["start"] - lead)
        nxt_start = rows[k + 1]["start"] - lead if k + 1 < len(rows) else r["end"] + hold
        # keep the line up while the singer is still on it, then hold it (capped by the next line)
        r["hide"] = max(min(r["end"] + hold, nxt_start - 0.05), r["start"] + min_dur)
        if r["hide"] <= r["show"]:
            r["hide"] = r["show"] + min_dur
        if k and r["show"] < rows[k - 1]["hide"]:
            rows[k - 1]["hide"] = r["show"]
    return rows


# --------------------------------------------------------------------------- output

def _srt_ts(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _ass_ts(t: float) -> str:
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360_000)
    m, cs = divmod(cs, 6_000)
    s, cs = divmod(cs, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def write_srt(rows: list[dict], path: Path) -> None:
    out = []
    for k, r in enumerate(rows, 1):
        out += [str(k), f"{_srt_ts(r['show'])} --> {_srt_ts(r['hide'])}", r["text"], ""]
    path.write_text("\n".join(out), encoding="utf-8")


def write_ass(rows: list[dict], path: Path, font: str, size: int, width: int, height: int,
              margin_v: int) -> None:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Lyrics,{font},{size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,3,1,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for r in rows:
        text = r["text"].replace("　", " ").replace("\\", "\\\\")
        events.append(f"Dialogue: 0,{_ass_ts(r['show'])},{_ass_ts(r['hide'])},Lyrics,,0,0,0,,{{\\fad(120,120)}}{text}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description="Align known lyrics/script to a transcript and write subtitles")
    ap.add_argument("transcript", type=Path, help="transcript JSON from transcribe.py")
    ap.add_argument("lyrics", type=Path, help="lyrics/script text, one subtitle line per line")
    ap.add_argument("-o", "--out", type=Path, required=True, help="output base path (writes .srt/.ass/.json)")
    ap.add_argument("--display", type=Path, default=None,
                    help="text to SHOW instead of lyrics (same lines, e.g. hiragana version)")
    ap.add_argument("--lead", type=float, default=0.15, help="show each line this early (s)")
    ap.add_argument("--hold", type=float, default=2.5, help="keep a line up to this long after it ends (s)")
    ap.add_argument("--min-dur", type=float, default=0.6, help="minimum on-screen time per line (s)")
    ap.add_argument("--font", default="Hiragino Sans", help="ASS font name (needs kana/kanji glyphs)")
    ap.add_argument("--font-size", type=int, default=60)
    ap.add_argument("--res", default="1920x1080", help="ASS PlayRes, match the video")
    ap.add_argument("--margin-v", type=int, default=70)
    args = ap.parse_args()

    lines = load_lyrics(args.lyrics, args.display)
    hyp = load_hyp(args.transcript)
    ref_keys = [k for ln in lines for k in ln.keys]
    mapping = align(ref_keys, [h.key for h in hyp])
    rows = time_lines(lines, hyp, mapping, args.lead, args.hold, args.min_dur)

    w, h = (int(x) for x in args.res.lower().split("x"))
    base = args.out
    base.parent.mkdir(parents=True, exist_ok=True)
    write_srt(rows, base.with_suffix(".srt"))
    write_ass(rows, base.with_suffix(".ass"), args.font, args.font_size, w, h, args.margin_v)
    base.with_suffix(".json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    matched = sum(1 for m in mapping if m is not None)
    weak = [r for r in rows if r["confidence"] < 0.5]
    print(f"aligned {matched}/{len(ref_keys)} characters, {len(rows)} lines "
          f"-> {base.with_suffix('.srt').name}, {base.with_suffix('.ass').name}, {base.with_suffix('.json').name}")
    if weak:
        print(f"{len(weak)} lines under 50% match (check these in the .json / preview):")
        for r in weak:
            tag = " (interpolated)" if r["interpolated"] else ""
            print(f"  [{r['start']:7.2f}-{r['end']:7.2f}] {r['confidence']:.0%} {r['text']}{tag}")


if __name__ == "__main__":
    main()
