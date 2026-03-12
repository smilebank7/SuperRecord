[English](README.md) | [한국어](README.ko.md) | [日本語](README.ja.md)

```
 ____                        ____                        _
/ ___| _   _ _ __   ___ _ __|  _ \ ___  ___ ___  _ __ __| |
\___ \| | | | '_ \ / _ \ '__| |_) / _ \/ __/ _ \| '__/ _` |
 ___) | |_| | |_) |  __/ |  |  _ <  __/ (_| (_) | | | (_| |
|____/ \__,_| .__/ \___|_|  |_| \_\___|\___\___/|_|  \__,_|
             |_|
```

**講義録音を体系的な学習資料に — 自動で。**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: macOS](https://img.shields.io/badge/Platform-macOS-lightgrey.svg)]()

---

SuperRecordは、講義の録音と参考資料（PDF、スライド、画像）を入力として、文字起こし、翻訳、構造化された講義ノート、PDFを生成するAIエージェントワークスペースです。Apple Voice Memosを直接スキャンし、対話形式で録音を分類した後、処理パイプライン全体を実行します — すべてAIコーディングエージェントがオーケストレーションします。

> **注意**: SuperRecordはスタンドアロンのCLIツールではありません。[Claude Code](https://docs.anthropic.com/en/docs/claude-code)などのAIコーディングエージェントと*共に*使用するよう設計されており、エージェントが`AGENTS.md`を読み取り、ワークフロー全体を対話的に実行します。

## 主な機能

- **Voice Memos連携** — macOS Voice Memosデータベースを直接スキャン。手動でのファイルエクスポート不要
- **Inboxドロップフォルダ** — AirDrop、ダウンロードなど外部オーディオファイルを`inbox/`ディレクトリにドロップ
- **マルチモデルASR** — Alibaba DashScope基盤、クォータ消費時に自動で次のモデルにフォールバック
- **対話型分類** — エージェントが科目、週、セッション番号を確認してから処理
- **フルパイプライン** — 文字起こし → 翻訳 → 講義ノート → 精製トランスクリプト → PDF生成
- **資料リンク** — スライド/PDFからテキストを抽出し、ノートに相互参照

## アーキテクチャ

```
┌─────────────────┐     ┌─────────────────┐
│  Voice Memos    │     │    inbox/        │
│  (macOS DB)     │     │ (ドロップフォルダ) │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │ エージェント スキャン&分類│
         │   (対話型分類)          │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │  Alibaba OSS アップロード│
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   DashScope ASR       │◄── モデルフォールバックチェーン
         │   (Qwen3 ASR)         │
         └───────────┬───────────┘
                     ▼
    ┌────────────────┼────────────────┐
    ▼                ▼                ▼
┌────────┐   ┌────────────┐   ┌────────────┐
│  翻訳   │   │  資料抽出   │   │   整理     │
│(エージェント)│ │ (Docling)  │   │  (vault/)  │
└────┬───┘   └─────┬──────┘   └────────────┘
     ▼              │
┌────────────┐      │
│  講義ノート  │◄─────┘  相互参照
│(エージェント) │
└────┬───────┘
     ▼
┌────────────┐
│  PDF変換    │
│(WeasyPrint) │
└─────────────┘
```

## 使い方

1. **スキャン** — 「scan」または「check」と言うと、エージェントがVoice Memos + `inbox/`から未処理の録音を探索
2. **分類** — エージェントが目的（講義/会議/個人）、科目、週、セッション番号を確認
3. **処理** — 選択した範囲に応じて、文字起こし、翻訳、ノート生成、PDFエクスポートを実行
4. **整理** — 結果が`vault/`に体系的なディレクトリ構造で保存

エージェントはすべての録音のパイプライン状態を`registry.md`で追跡するため、中断された作業も正確に再開できます。

## 前提条件

| 要件 | 詳細 |
|------|------|
| **macOS** | Voice Memos連携にはmacOSが必要。`inbox/`フォルダは全プラットフォームで使用可能。 |
| **Python 3.10+** | ASR処理、ドキュメント抽出、PDF生成に必要 |
| **Alibaba Cloud** | DashScope ASRおよびOSSストレージ用の無料アカウント |
| **Claude Code** | パイプラインをオーケストレーションするAIコーディングエージェント ([ドキュメント](https://docs.anthropic.com/en/docs/claude-code)) |

> WindowsおよびLinuxサポートは将来のリリースで提供予定です。現在、`inbox/`フォルダ入力はクロスプラットフォームで動作しますが、Voice Memosスキャンはmacos専用です。

## クイックスタート

```bash
# 1. リポジトリをクローン
git clone https://github.com/smilebank7/SuperRecord.git
cd SuperRecord

# 2. Python環境のセットアップ
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. 環境テンプレートをコピー
cp .env.example .env
cp config.yaml.example config.yaml

# 4. Claude Codeを起動し、エージェントのガイドに従ってセットアップ
#    エージェントがAlibaba Cloud設定を対話的にガイドします
claude

# 5. エージェントに初期化を依頼
#    > "init" または "初期設定"
```

エージェントガイド初期化の内容:
- 翻訳対象言語と現在の学期を設定
- 受講科目を登録
- Alibaba Cloudを設定（DashScope APIキー、OSSバケット、RAMユーザー） — `aliyun` CLIの有無に対応
- 接続テスト

## プロジェクト構造

```
SuperRecord/
├── AGENTS.md              # エージェント命令セット
├── config.yaml            # ワークスペース設定（gitignore; config.yaml.exampleを使用）
├── registry.md            # パイプライン状態トラッカー（gitignore）
├── processors/
│   ├── asr_processor.py   # DashScope ASR + モデルフォールバック
│   ├── doc_extractor.py   # Docling基盤 PDF/PPTX抽出
│   └── md_to_pdf.py       # WeasyPrint基盤 Markdown → PDF
├── skills/                # エージェントスキル定義
│   ├── transcribe/        # オーディオ → 文字起こし
│   ├── extract-materials/  # PDF/画像 → 構造化テキスト
│   ├── translate/         # 文字起こし → 対象言語翻訳
│   ├── generate-notes/    # 文字起こし + 資料 → 講義ノート
│   └── organize/          # ファイル分類 + vault構造化
├── vault/                 # 整理された成果物（gitignore）
│   ├── lectures/          # 学期 / 科目 / セッション
│   ├── meetings/          # 日付ベース
│   └── personal/          # 日付ベース
├── inbox/                 # 外部オーディオドロップフォルダ（gitignore）
├── .env.example           # 環境変数テンプレート
├── config.yaml.example    # 設定テンプレート
└── requirements.txt       # Python依存関係
```

## パイプラインフェーズ

| フェーズ | 名前 | ツール | 出力 |
|---------|------|--------|------|
| 1 | 文字起こし | `asr_processor.py` + DashScope | `transcript.json`, `transcript.txt` |
| 2 | 資料抽出 | `doc_extractor.py` + Docling | `materials/*_extracted.md` |
| 3 | 翻訳 | エージェント (LLM) | `transcript_{lang}.md` |
| 4 | 講義ノート生成 | エージェント (LLM) | `notes.md` + PDF |
| 4.5 | 精製トランスクリプト | エージェント (LLM) | `refined_transcript.md` + PDF |
| 5 | 整理 | エージェント | `metadata.yaml`, `registry.md` 更新 |

## 技術スタック

- **ASR**: [Alibaba DashScope](https://www.alibabacloud.com/en/product/model-studio) — Qwen3 ASR、自動モデルフォールバック
- **ストレージ**: [Alibaba OSS](https://www.alibabacloud.com/en/product/object-storage-service) — ASR用オーディオファイルステージング
- **ドキュメント抽出**: [Docling](https://github.com/docling-project/docling) — PDF/PPTX → 構造化Markdown
- **PDF生成**: [WeasyPrint](https://weasyprint.org/) — CJK対応 Markdown → PDF
- **エージェントランタイム**: [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — AGENTS.mdを読み取りパイプラインをオーケストレーション

## 無料利用枠

SuperRecordは、新規アカウントに無料クォータを提供するAlibaba Cloudサービスを使用しています。

### DashScope ASR

**シンガポール（International）エンドポイント**で[Model Studio](https://www.alibabacloud.com/en/product/model-studio)を有効にすると、各ASRモデルに独立した無料クォータが付与されます：

| モデル | 無料クォータ | 有効期間 | 有料単価 |
|--------|------------|---------|---------|
| `qwen3-asr-flash-filetrans` | 36,000秒（10時間） | 90日 | $0.000035/秒 |
| `fun-asr` | 36,000秒（10時間） | 90日 | $0.000035/秒 |

- **入力オーディオの長さ**に基づく秒単位課金 — 出力テキストは無料
- 各モデルが独立したクォータを持つため、SuperRecordのフォールバックチェーンで**合計約20時間**利用可能
- 一般的な90分の講義 = 約5,400秒 — モデルあたり**約6〜7講義**を無料で処理
- [コンソール](https://modelstudio.console.alibabacloud.com/)で**無料クォータ専用**モードを有効にすると、クォータ消費後の課金を防止

### Alibaba Cloud OSS

OSSはオーディオファイルの一時ステージング（アップロード → ASR → 削除）にのみ使用されます。コストはごくわずかです：

- **アップロード（インバウンド）**：常に無料
- **ストレージ**：約$0.02/GB/月（Standard LRS、シンガポール）— 処理後にファイル削除
- **内部転送**：DashScopeが内部エンドポイントでOSSにアクセスすれば無料

> 新規アカウントには**1ヶ月の無料トライアル**（500GBストレージ）が提供されます。それ以降も、一般的な講義録音処理のコストはほぼゼロです。詳細は[OSS料金](https://www.alibabacloud.com/help/en/oss/free-quota-for-new-users)を参照。

## ライセンス

[MIT](LICENSE)

## ロードマップ

- [ ] **ローカルASRサポート** — [whisper.cpp](https://github.com/ggerganov/whisper.cpp)または[MLX Whisper](https://github.com/ml-explore/mlx-examples)をApple Siliconで実行し、クラウドアカウント不要のオフライン文字起こし
- [ ] **ネイティブmacOSアプリ** — 録音管理、パイプライン状態、vaultブラウジング用のメニューバーアプリ
- [ ] Windows / Linuxサポート（Voice Memos代替）
- [ ] 追加クラウドASRプロバイダー（Google Speech-to-Text、Azure Speech）
- [ ] パイプライン状態およびvaultブラウジングWeb UI
- [ ] バッチ処理モード（プロンプトなしで未処理録音を一括処理）
- [ ] 多話者録音の話者分離
