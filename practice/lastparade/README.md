# 練習: LastParade（SAWA）に全ひらがな歌詞を焼き込む

元動画: https://youtu.be/tfGO1T47lp8

このフォルダにあるもの

- `lyrics.txt` 歌詞（原文。☆ はセクション区切りで字幕には出ない）
- `lyrics_kana.txt` 表示用の全ひらがな版。pykakasi の誤読 4 か所（素手で・君と・渦巻く・やり甲斐）は手で修正済み

やること: Whisper で歌の「単語ごとの時刻」だけを取り、既知の歌詞をその時刻に合わせ込んで
（`lyrics_align.py`）、ひらがな字幕を焼き込む。Whisper の聞き取り結果の文字は使わないので、
歌で誤認識が多くてもタイミングは崩れない。

## 手順（Mac、Claude Code のこのリポジトリで）

Claude Code にそのまま貼れる指示:

```text
practice/lastparade/README.md の手順で、LastParade にひらがな歌詞を焼き込んで。
文字起こしは --engine whisper、歌詞は lyrics.txt、表示は lyrics_kana.txt。
終わったら timeline_view で最初の3行と最後の3行のカット位置を確認して。
```

手でやる場合:

```bash
# 0. 依存（初回だけ）
brew install ffmpeg yt-dlp
pip install faster-whisper pykakasi

# 1. 動画を取得
cd practice/lastparade
yt-dlp -f "bv*[height<=1080]+ba/b" --merge-output-format mp4 -o "lastparade.%(ext)s" "https://youtu.be/tfGO1T47lp8"

# 2. 単語時刻付きの文字起こし（ローカル Whisper、日本語固定）
python ../../.claude/skills/video-use/helpers/transcribe.py lastparade.mp4 --engine whisper --language ja
#   -> edit/transcripts/lastparade.json

# 3. 歌詞を時刻に合わせ込み、字幕を書き出す
python ../../.claude/skills/video-use/helpers/lyrics_align.py \
    edit/transcripts/lastparade.json lyrics.txt --display lyrics_kana.txt \
    -o edit/lyrics --font "Hiragino Sans" --font-size 60 --res 1920x1080
#   -> edit/lyrics.srt / edit/lyrics.ass / edit/lyrics.json
#   「lines under 50% match」と出た行は lyrics.json の start/end を目で確認

# 4. 焼き込み（映像は再エンコード、音声はそのまま）
ffmpeg -i lastparade.mp4 -vf "ass=edit/lyrics.ass" -c:v libx264 -crf 18 -preset medium -c:a copy edit/lastparade_kana.mp4

# 5. 確認（任意）: 行の切り替わり付近をフィルムストリップ + 波形で見る
python ../../.claude/skills/video-use/helpers/timeline_view.py edit/lastparade_kana.mp4 10 20
```

## 調整のコツ

- 全体が一律に早い/遅い: `lyrics_align.py --lead` を変える（既定 0.15 秒早出し）。
- 行が消えるのが早い: `--hold`（既定 2.5 秒、次の行が始まれば自動で切る）。
- 特定の行だけズレる: `edit/lyrics.json` の `start` / `end` を直して、
  `lyrics.srt` / `lyrics.ass` を作り直す（再実行せず SRT を手で直しても良い）。
- 認識が弱くて 50% 未満の行が多い: 伴奏が強い曲なので、先にボーカルを分離すると精度が上がる
  （`pip install demucs` → `demucs --two-stems=vocals lastparade.mp4` → 出来た vocals.wav を
  `transcribe_whisper.py vocals.wav -o edit/transcripts/lastparade.json --language ja` で文字起こし）。
- 縦型やサイズ違いの動画は `--res` を実際の解像度に合わせる（`ffprobe` で確認）。
- フォントは macOS なら `Hiragino Sans`、Windows なら `Yu Gothic`、Linux なら `Noto Sans CJK JP`。

## 精度の目安

疑似データ（前奏の幻聴、脱字 15%、誤認識 10%、丸ごと落ちた行 2 つ）で
行頭の平均誤差 0.13 秒、表示区間が歌唱区間を覆った行 40/46。実音声ではまだ未検証。
