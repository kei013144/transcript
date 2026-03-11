# YouTube Raw Transcript CLI

YouTube URL 1件を入力し、LLM投入前の Raw transcript データを生成する CLI ツールです。  
要約やQAは行わず、以下3ファイルを保存します。

- `transcript.txt` (全文)
- `segments.json` (`start` / `end` / `text`)
- `metadata.json` (動画情報 + 処理情報)

## 要件

- Python 3.11+
- `ffmpeg` が実行可能であること
- ローカル実行時: `faster-whisper` を使用（APIキー不要）
- OpenAI実行時のみ: OpenAI APIキー (`OPENAI_API_KEY`)

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

OpenAIを使う場合のみ環境変数を設定:

```bash
export OPENAI_API_KEY="YOUR_KEY"  # Windows PowerShell: $env:OPENAI_API_KEY="YOUR_KEY"
```

## 使い方まとめ

1. YouTube URLを指定して実行（デフォルトはローカルWhisper / CPU / 進捗バーON）
2. 標準出力に出る `transcript_path` / `segments_path` / `metadata_path` を確認

最小実行:

```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

OpenAIで実行する場合:

```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --transcriber openai
```

初回実行:

- `audio/source.m4a` をダウンロード
- 音声を文字起こし
- `transcript.txt` / `segments.json` / `metadata.json` を保存

同じ `video_id` で再実行:

- デフォルトでは音声キャッシュは利用し、文字起こしは毎回再実行（`--force-transcribe` が既定で有効）
- 文字起こしキャッシュを利用したい場合は `--no-force-transcribe` を指定

再取得したい場合:

```bash
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --force-download
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --force-download --force-transcribe
python main.py "https://www.youtube.com/watch?v=VIDEO_ID" --no-force-transcribe
```

オプション一覧:

- `--transcriber`: 文字起こしバックエンド（`faster-whisper` / `openai`）
- `--force-download`: 音声キャッシュがあっても再ダウンロード
- `--force-transcribe` / `--no-force-transcribe`: 文字起こしキャッシュ利用の切り替え（`default: --force-transcribe`）
- `--output-root`: 出力ルート (`default: data`)
- `--prefer-captions`: 将来の字幕優先モード用フラグ（現状はSTTへフォールバック）
- `--openai-model`: OpenAIモデル (`default: whisper-1`)
- `--whisper-model`: ローカルfaster-whisperモデル (`default: small`)
- `--whisper-device`: ローカルfaster-whisperデバイス (`default: cpu`)
- `--whisper-compute-type`: ローカルfaster-whisper計算精度 (`default: int8`)
- `--progress` / `--no-progress`: ダウンロード・文字起こし時の進捗バー表示切り替え（`default: --progress`）
- `--log-level`: ログレベル (`DEBUG/INFO/WARNING/ERROR`)

出力先を変更する例:

```bash
python main.py "https://youtu.be/dQw4w9WgXcQ" --output-root ./data
```

## 出力構成

```text
data/
  youtube/
    <video_id>/
      audio/
        source.m4a
      transcript/
        transcript.txt
        segments.json
        metadata.json
```

## キャッシュ仕様

- キャッシュキーは URL ではなく `video_id`
- `audio/source.m4a` が存在する場合、再ダウンロードをスキップ
- `transcript/transcript.txt` と `segments.json` が存在しても、デフォルトでは再文字起こしを実行
- `--no-force-transcribe` 指定時のみ、文字起こしキャッシュがある場合に再文字起こしをスキップ

## クラス構成

- `YouTubeResolver`: URL解析と動画メタデータ取得
- `AudioCacheManager`: 音声キャッシュ管理とダウンロード
- `Transcriber` / `OpenAITranscriber` / `FasterWhisperTranscriber`: 文字起こしインターフェースと実装
- `TranscriptStore`: 出力保存 (`transcript.txt`, `segments.json`, `metadata.json`)

## 補足

- 文字起こし結果は後段で Claude / GPT 等にそのまま渡せる中間データを想定
- `Transcriber` インターフェースにより、将来的に Whisper ローカル実装へ差し替え可能
