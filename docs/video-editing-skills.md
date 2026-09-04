# Claude Code の動画編集スキル 調査メモ（2026-09-04）

きっかけ: X の投稿 https://x.com/aitech_komoriya/status/2095455134579048892
（このセッションからは x.com 系が閲覧不可のため、投稿本文は未確認。
「Claude Code で動画編集ができるスキル」として日本語圏で拡散しているものを調べた。）

## 結論

- 日本語圏で「動画編集スキル」として一番バズっているのは **browser-use 製「Video Use」**。
  MIT ライセンス、100% OSS。素材フォルダを渡すだけで、無音・フィラーカット、
  カラーグレード、字幕焼き込み、アニメーション挿入、セルフレビューまでやって `edit/final.mp4` を返す。
- 「動画を作る（生成する）」方向は **Remotion 公式 Agent Skills** が本命。
  React で動画をコード生成するもので、モーショングラフィックスや説明動画向け。
- この 2 つは補完関係。**撮った素材を編集するなら Video Use、ゼロから動画を作るなら Remotion**。

## このリポジトリに取り込んだもの

`.claude/skills/video-use/` に Video Use のスナップショットを同梱した
（コミットは `VENDORED_FROM.txt` を参照。バナー画像・テスト・poster.html は除外）。
このリポジトリで `claude` を起動すると `video-use` スキルとして認識される。

ただし公式の想定インストールは「Mac に clone して `~/.claude/skills/video-use` にシンボリックリンク」。
最新版を追いたい場合は後述の手順で本体を入れ直すのがおすすめ。

## 1. Video Use（browser-use/video-use）

- リポジトリ: https://github.com/browser-use/video-use
- できること
  - フィラー（えー、あの）・言い直し・無音の自動カット
  - セグメントごとの自動カラーグレード（プリセット or 任意の ffmpeg フィルタ）
  - カット境界に 30ms のオーディオフェード（プチノイズ防止）
  - スタイル指定の字幕焼き込み（デフォルトは 2 語ずつ大文字）
  - HyperFrames / Remotion / Manim / PIL によるアニメーション挿入（サブエージェント並列）
  - レンダリング結果をカット境界ごとにセルフチェックしてから提示
  - `project.md` にセッション記憶を残す
- 仕組み: 動画を「見る」のではなく、ElevenLabs Scribe の単語レベル文字起こしを読んで
  カット位置を決める。必要な箇所だけ `timeline_view` でフィルムストリップ + 波形 PNG を確認。
- 必要なもの
  - `ffmpeg` / `ffprobe`（必須）
  - Python 3.10+ と `uv`（または pip）
  - **ElevenLabs API キー（必須・有料）** 文字起こしに使う。これがないと何も始まらない
  - `yt-dlp`（任意、URL から素材を取る場合）
  - Node.js 22+（任意、HyperFrames / Remotion のアニメーションを使う場合）
- 注意点
  - 文字起こしは ElevenLabs のクレジットを消費する。同じ素材はキャッシュされ再文字起こししない
  - 日本語素材の実績は README に明記なし。Scribe 自体は日本語対応なので動くはずだが要検証
  - 出力は素材フォルダ直下の `edit/` に出る。スキル本体のフォルダは汚さない

### インストール（Mac、公式手順）

Claude Code に以下を貼るだけで、clone・依存・ffmpeg・スキル登録・API キー設定まで代行してくれる。

```text
Set up https://github.com/browser-use/video-use for me.

Read install.md first to install this repo, wire up ffmpeg, register the skill with whichever agent you're running under, and set up the ElevenLabs API key — ask me to paste it when you need it. Then read SKILL.md for daily usage, and always read helpers/ because that's where the editing scripts live. After install, don't transcribe anything on your own — just tell me it's ready and wait for me to drop footage into a folder.
```

手動でやる場合:

```bash
git clone https://github.com/browser-use/video-use ~/Developer/video-use
ln -sfn ~/Developer/video-use ~/.claude/skills/video-use
cd ~/Developer/video-use
uv sync                 # または pip install -e .
brew install ffmpeg
brew install yt-dlp     # 任意
cp .env.example .env    # ELEVENLABS_API_KEY=... を書く
```

使い方:

```bash
cd /path/to/素材フォルダ
claude
# > edit these into a launch video
# > この素材で1分のダイジェストを作って。無音カットと字幕付きで
```

## 2. Remotion 公式 Agent Skills（remotion-dev/skills）

- リポジトリ: https://github.com/remotion-dev/skills
- ドキュメント: https://www.remotion.dev/docs/ai/skills
- インストール: `npx skills add remotion-dev/skills`
- 内容: `/remotion-create`（新規作成）、`/remotion-markup`（アニメーション記法）、
  `/remotion-captions`（字幕）、`/remotion-render`（書き出し）、`/remotion-maps`（地図アニメ）、
  `/remotion-studio`（プレビュー）など 11 スキル
- 向き: ロゴアニメ、テロップ、縦型ショート、データ可視化動画など「コードで動画を作る」用途
- 必要なもの: Node.js、`npx create-video@latest` で作る Remotion プロジェクト

## 3. その他の候補

| 名前 | 内容 | 備考 |
| --- | --- | --- |
| haidrrrry/claude-remotion-skill | Remotion でモーショングラフィックスを作る単体スキル。レンダリング → フレーム抽出 → 目視検証のループ付き | MIT。`.skill` ファイルで Claude Desktop にも入る |
| wilwaldon/Claude-Code-Video-Toolkit | Remotion / Manim / YouTube クリッパー / FFmpeg スキルの寄せ集めガイド | MIT。個別スキルへのリンク集 |
| digitalsamba/claude-code-video-toolkit | Remotion ベースの動画制作キット。共通コンポーネントとトランジション同梱 | 別プラットフォーム向け移行スクリプトもあり |
| iret の video-composer（Zenn 記事） | Remotion × Google 生成 AI で構成案 → 素材生成 → 合成 → セルフレビュー | 日本語記事。Google API キー前提 |

## 参考リンク

- Video Use を使った日本語の紹介投稿（X）: https://x.com/shota7180/status/2050771083541033126
- Claude Code だけで自動編集した例（X）: https://x.com/masahirochaen/status/2034854890338660420
- Claude Code で動画編集 入門（fyve）: https://fyve.co.jp/claude-code/articles/claude-code-video-editing-start
- 3 層スタック解説（AI 氣道）: https://ai-kidou.jp/cc-video-3-layer-stack/
- 無音カット × テロップ × B ロール自動化（Routine labo）: https://rutinelabo.com/claudecode-video-editing-automation/
- video-composer 紹介（Zenn）: https://zenn.dev/iret/articles/claude-code-video-composer
