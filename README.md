[English](README.md) | [한국어](README.ko.md) | [日本語](README.ja.md)

```
 ____                        ____                        _
/ ___| _   _ _ __   ___ _ __|  _ \ ___  ___ ___  _ __ __| |
\___ \| | | | '_ \ / _ \ '__| |_) / _ \/ __/ _ \| '__/ _` |
 ___) | |_| | |_) |  __/ |  |  _ <  __/ (_| (_) | | | (_| |
|____/ \__,_| .__/ \___|_|  |_| \_\___|\___\___/|_|  \__,_|
             |_|
```

**Turn lecture recordings into structured study materials — automatically.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: macOS](https://img.shields.io/badge/Platform-macOS-lightgrey.svg)]()

---

SuperRecord is an AI agent workspace that takes your lecture recordings and reference materials (PDFs, slides, images) and produces transcriptions, translations, structured lecture notes, and organized PDFs. It scans Apple Voice Memos directly, classifies recordings through conversation, and runs a full processing pipeline — all orchestrated by an AI coding agent.

> **Note**: SuperRecord is not a standalone CLI tool. It's designed to work *with* an AI coding agent (such as [Claude Code](https://docs.anthropic.com/en/docs/claude-code)) that reads `AGENTS.md` as its instruction set and drives the entire workflow interactively.

## Features

- **Voice Memos integration** — Scans macOS Voice Memos database directly; no manual file export needed
- **Inbox drop folder** — Supports external audio files (AirDrop, downloads) via a simple `inbox/` directory
- **Multi-model ASR** — Alibaba DashScope with automatic fallback across models on quota exhaustion
- **Interactive classification** — Agent asks you to confirm course, week, and session before processing
- **Full pipeline** — Transcription → Translation → Lecture notes → Refined transcript → PDF generation
- **Material linking** — Extracts text from slides/PDFs and cross-references them in your notes

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│  Voice Memos    │     │    inbox/        │
│  (macOS DB)     │     │  (drop folder)   │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   Agent Scan & Sort   │
         │  (interactive classify)│
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   Alibaba OSS Upload  │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   DashScope ASR       │◄── model fallback chain
         │   (Qwen3 ASR)         │
         └───────────┬───────────┘
                     ▼
    ┌────────────────┼────────────────┐
    ▼                ▼                ▼
┌────────┐   ┌────────────┐   ┌────────────┐
│Translate│   │Extract Docs│   │  Organize  │
│ (Agent) │   │ (Docling)  │   │  (vault/)  │
└────┬───┘   └─────┬──────┘   └────────────┘
     ▼              │
┌────────────┐      │
│Lecture Notes│◄─────┘  cross-reference
│  (Agent)   │
└────┬───────┘
     ▼
┌────────────┐
│  PDF Export │
│(WeasyPrint) │
└─────────────┘
```

## How It Works

1. **Scan** — Say "scan" or "check" and the agent scans Voice Memos + `inbox/` for unprocessed recordings
2. **Classify** — The agent asks you to confirm: purpose (lecture/meeting/personal), course, week, and session number
3. **Process** — Depending on your chosen scope, the agent runs transcription, translation, note generation, and PDF export
4. **Organize** — Results are saved to `vault/` in a structured directory hierarchy with full metadata

The agent tracks every recording's pipeline state in `registry.md`, so interrupted work can resume exactly where it left off.

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **macOS** | Voice Memos integration requires macOS. The `inbox/` folder works on any platform. |
| **Python 3.10+** | For ASR processing, document extraction, and PDF generation |
| **Alibaba Cloud** | Free-tier account for DashScope ASR and OSS storage |
| **Claude Code** | AI coding agent that orchestrates the pipeline ([docs](https://docs.anthropic.com/en/docs/claude-code)) |

> Windows and Linux support is planned for a future release. Currently, the `inbox/` folder input works cross-platform, but Voice Memos scanning is macOS-only.

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-username/SuperRecord.git
cd SuperRecord

# 2. Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Copy environment template
cp .env.example .env
cp config.yaml.example config.yaml

# 4. Start Claude Code and let the agent guide you through setup
#    The agent will walk you through Alibaba Cloud configuration interactively
claude

# 5. Ask the agent to initialize
#    > "init" or "초기 설정"
```

The agent-guided init will:
- Set your target language and current semester
- Register your courses
- Configure Alibaba Cloud (DashScope API key, OSS bucket, RAM user) — with or without `aliyun` CLI
- Test the connection

## Project Structure

```
SuperRecord/
├── AGENTS.md              # Agent instruction set (the brain)
├── config.yaml            # Workspace config (gitignored; use config.yaml.example)
├── registry.md            # Pipeline state tracker (gitignored)
├── processors/
│   ├── asr_processor.py   # DashScope ASR with model fallback
│   ├── doc_extractor.py   # PDF/PPTX extraction via Docling
│   └── md_to_pdf.py       # Markdown → PDF via WeasyPrint
├── skills/                # Agent skill definitions
│   ├── transcribe/        # Audio → transcript
│   ├── extract-materials/  # PDF/images → structured text
│   ├── translate/         # Transcript → target language
│   ├── generate-notes/    # Transcript + materials → lecture notes
│   └── organize/          # File classification + vault structure
├── vault/                 # Organized output (gitignored)
│   ├── lectures/          # semester / course / session
│   ├── meetings/          # date-based
│   └── personal/          # date-based
├── inbox/                 # Drop folder for external audio (gitignored)
├── .env.example           # Environment variable template
├── config.yaml.example    # Configuration template
└── requirements.txt       # Python dependencies
```

## Pipeline Phases

| Phase | Name | Tool | Output |
|-------|------|------|--------|
| 1 | Transcribe | `asr_processor.py` + DashScope | `transcript.json`, `transcript.txt` |
| 2 | Extract Materials | `doc_extractor.py` + Docling | `materials/*_extracted.md` |
| 3 | Translate | Agent (LLM) | `transcript_{lang}.md` |
| 4 | Generate Notes | Agent (LLM) | `notes.md` + PDF |
| 4.5 | Refined Transcript | Agent (LLM) | `refined_transcript.md` + PDF |
| 5 | Organize | Agent | `metadata.yaml`, `registry.md` update |

## Tech Stack

- **ASR**: [Alibaba DashScope](https://www.alibabacloud.com/en/product/model-studio) — Qwen3 ASR with automatic model fallback
- **Storage**: [Alibaba OSS](https://www.alibabacloud.com/en/product/object-storage-service) — Audio file staging for ASR
- **Document Extraction**: [Docling](https://github.com/docling-project/docling) — PDF/PPTX to structured Markdown
- **PDF Generation**: [WeasyPrint](https://weasyprint.org/) — Markdown to styled PDF with CJK support
- **Agent Runtime**: [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — AI agent that reads AGENTS.md and orchestrates the pipeline

## Free Tier

SuperRecord uses Alibaba Cloud services that offer free quotas for new accounts.

### DashScope ASR

Each ASR model receives its own independent free quota upon activating [Model Studio](https://www.alibabacloud.com/en/product/model-studio) on the **Singapore (International) endpoint**:

| Model | Free Quota | Validity | Paid Rate |
|-------|-----------|----------|-----------|
| `qwen3-asr-flash-filetrans` | 36,000 sec (10 hours) | 90 days | $0.000035/sec |
| `fun-asr` | 36,000 sec (10 hours) | 90 days | $0.000035/sec |

- Billing is per second of **input audio duration** — output text is free
- Each model has its own quota (not shared), so SuperRecord's fallback chain gives you **~20 hours total**
- A typical 90-minute lecture uses ~5,400 seconds — **~6–7 lectures per model** on the free tier
- Enable **Free Quota Only** in the [console](https://modelstudio.console.alibabacloud.com/) to prevent unexpected charges after exhaustion

### Alibaba Cloud OSS

OSS is used only for temporary audio staging (upload → ASR → delete). Costs are negligible:

- **Uploads (inbound)**: Always free
- **Storage**: ~$0.02/GB/month (Standard LRS, Singapore) — audio files are deleted after processing
- **Internal transfer**: Free if DashScope accesses OSS via the internal endpoint

> New accounts receive a **1-month free trial** (500 GB storage). After that, a typical lecture recording session costs fractions of a cent. See [OSS pricing](https://www.alibabacloud.com/help/en/oss/free-quota-for-new-users) for details.

## License

[MIT](LICENSE)

## Roadmap

- [ ] **Local ASR support** — Run transcription offline using [whisper.cpp](https://github.com/ggerganov/whisper.cpp) or [MLX Whisper](https://github.com/ml-explore/mlx-examples) on Apple Silicon, eliminating the need for a cloud account
- [ ] **Native macOS app** — Standalone menu bar app for recording management, pipeline status, and vault browsing
- [ ] Windows / Linux support (Voice Memos alternative)
- [ ] Additional cloud ASR providers (Google Speech-to-Text, Azure Speech)
- [ ] Web UI for pipeline status and vault browsing
- [ ] Batch processing mode (process all unhandled recordings without prompts)
- [ ] Speaker diarization for multi-speaker recordings
