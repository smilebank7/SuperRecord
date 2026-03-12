[English](README.md) | [한국어](README.ko.md) | [日本語](README.ja.md)

```
 ____                        ____                        _
/ ___| _   _ _ __   ___ _ __|  _ \ ___  ___ ___  _ __ __| |
\___ \| | | | '_ \ / _ \ '__| |_) / _ \/ __/ _ \| '__/ _` |
 ___) | |_| | |_) |  __/ |  |  _ <  __/ (_| (_) | | | (_| |
|____/ \__,_| .__/ \___|_|  |_| \_\___|\___\___/|_|  \__,_|
             |_|
```

**강의 녹음을 체계적인 학습 자료로 — 자동으로.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: macOS](https://img.shields.io/badge/Platform-macOS-lightgrey.svg)]()

---

SuperRecord는 강의 녹음과 참고자료(PDF, 슬라이드, 이미지)를 입력받아 전사, 번역, 구조화된 강의노트, PDF를 생성하는 AI 에이전트 워크스페이스입니다. Apple Voice Memos를 직접 스캔하고, 대화형으로 녹음을 분류한 뒤, 전체 처리 파이프라인을 실행합니다 — 모두 AI 코딩 에이전트가 오케스트레이션합니다.

> **참고**: SuperRecord는 독립 실행형 CLI 도구가 아닙니다. [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 같은 AI 코딩 에이전트와 *함께* 사용하도록 설계되었으며, 에이전트가 `AGENTS.md`를 읽고 전체 워크플로우를 대화형으로 실행합니다.

## 주요 기능

- **Voice Memos 연동** — macOS Voice Memos 데이터베이스를 직접 스캔. 수동 파일 내보내기 불필요
- **Inbox 드롭 폴더** — 에어드롭, 다운로드 등 외부 오디오 파일을 `inbox/` 디렉토리에 드롭
- **멀티 모델 ASR** — Alibaba DashScope 기반, 쿼터 소진 시 자동으로 다음 모델로 전환
- **대화형 분류** — 에이전트가 과목, 주차, 세션 번호를 확인한 후 처리
- **풀 파이프라인** — 전사 → 번역 → 강의노트 → 정제 녹취본 → PDF 생성
- **자료 연계** — 슬라이드/PDF에서 텍스트를 추출하여 노트에 상호 참조

## 아키텍처

```
┌─────────────────┐     ┌─────────────────┐
│  Voice Memos    │     │    inbox/        │
│  (macOS DB)     │     │  (드롭 폴더)     │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │  에이전트 스캔 & 분류   │
         │  (대화형 분류)         │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   Alibaba OSS 업로드   │
         └───────────┬───────────┘
                     ▼
         ┌───────────────────────┐
         │   DashScope ASR       │◄── 모델 폴백 체인
         │   (Qwen3 ASR)         │
         └───────────┬───────────┘
                     ▼
    ┌────────────────┼────────────────┐
    ▼                ▼                ▼
┌────────┐   ┌────────────┐   ┌────────────┐
│  번역   │   │  자료 추출  │   │   정리     │
│(에이전트)│   │ (Docling)  │   │  (vault/)  │
└────┬───┘   └─────┬──────┘   └────────────┘
     ▼              │
┌────────────┐      │
│  강의노트   │◄─────┘  상호 참조
│ (에이전트)  │
└────┬───────┘
     ▼
┌────────────┐
│  PDF 변환   │
│(WeasyPrint) │
└─────────────┘
```

## 작동 방식

1. **스캔** — "스캔" 또는 "체크"라고 말하면 에이전트가 Voice Memos + `inbox/`에서 미처리 녹음을 탐색
2. **분류** — 에이전트가 목적(강의/회의/개인), 과목, 주차, 세션 번호를 확인
3. **처리** — 선택한 범위에 따라 전사, 번역, 노트 생성, PDF 내보내기 실행
4. **정리** — 결과물이 `vault/`에 체계적인 디렉토리 구조로 저장

에이전트는 모든 녹음의 파이프라인 상태를 `registry.md`에 추적하므로, 중단된 작업도 정확히 이어서 재개할 수 있습니다.

## 사전 요구사항

| 요구사항 | 세부사항 |
|----------|---------|
| **macOS** | Voice Memos 연동에 macOS 필요. `inbox/` 폴더는 모든 플랫폼에서 사용 가능. |
| **Python 3.10+** | ASR 처리, 문서 추출, PDF 생성에 필요 |
| **Alibaba Cloud** | DashScope ASR 및 OSS 스토리지용 무료 계정 |
| **Claude Code** | 파이프라인을 오케스트레이션하는 AI 코딩 에이전트 ([문서](https://docs.anthropic.com/en/docs/claude-code)) |

> Windows 및 Linux 지원은 향후 릴리스에서 제공 예정입니다. 현재 `inbox/` 폴더 입력은 크로스 플랫폼으로 작동하지만, Voice Memos 스캔은 macOS 전용입니다.

## 빠른 시작

```bash
# 1. 레포지토리 클론
git clone https://github.com/your-username/SuperRecord.git
cd SuperRecord

# 2. Python 환경 설정
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. 환경 템플릿 복사
cp .env.example .env
cp config.yaml.example config.yaml

# 4. Claude Code를 시작하고 에이전트의 안내에 따라 설정
#    에이전트가 Alibaba Cloud 구성을 대화형으로 안내합니다
claude

# 5. 에이전트에게 초기화 요청
#    > "init" 또는 "초기 설정"
```

에이전트 가이드 초기화 과정:
- 번역 대상 언어 및 현재 학기 설정
- 수강 과목 등록
- Alibaba Cloud 구성 (DashScope API 키, OSS 버킷, RAM 사용자) — `aliyun` CLI 유무 모두 지원
- 연결 테스트

## 프로젝트 구조

```
SuperRecord/
├── AGENTS.md              # 에이전트 명령 세트
├── config.yaml            # 워크스페이스 설정 (gitignore; config.yaml.example 사용)
├── registry.md            # 파이프라인 상태 추적기 (gitignore)
├── processors/
│   ├── asr_processor.py   # DashScope ASR + 모델 폴백
│   ├── doc_extractor.py   # Docling 기반 PDF/PPTX 추출
│   └── md_to_pdf.py       # WeasyPrint 기반 Markdown → PDF
├── skills/                # 에이전트 스킬 정의
│   ├── transcribe/        # 오디오 → 전사
│   ├── extract-materials/  # PDF/이미지 → 구조화 텍스트
│   ├── translate/         # 전사 → 대상 언어 번역
│   ├── generate-notes/    # 전사 + 자료 → 강의노트
│   └── organize/          # 파일 분류 + vault 구조화
├── vault/                 # 정리된 결과물 (gitignore)
│   ├── lectures/          # 학기 / 과목 / 세션
│   ├── meetings/          # 날짜 기반
│   └── personal/          # 날짜 기반
├── inbox/                 # 외부 오디오 드롭 폴더 (gitignore)
├── .env.example           # 환경변수 템플릿
├── config.yaml.example    # 설정 템플릿
└── requirements.txt       # Python 의존성
```

## 파이프라인 단계

| 단계 | 이름 | 도구 | 출력 |
|------|------|------|------|
| 1 | 전사 | `asr_processor.py` + DashScope | `transcript.json`, `transcript.txt` |
| 2 | 자료 추출 | `doc_extractor.py` + Docling | `materials/*_extracted.md` |
| 3 | 번역 | 에이전트 (LLM) | `transcript_{lang}.md` |
| 4 | 강의노트 생성 | 에이전트 (LLM) | `notes.md` + PDF |
| 4.5 | 정제 녹취본 | 에이전트 (LLM) | `refined_transcript.md` + PDF |
| 5 | 정리 | 에이전트 | `metadata.yaml`, `registry.md` 업데이트 |

## 기술 스택

- **ASR**: [Alibaba DashScope](https://www.alibabacloud.com/en/product/model-studio) — Qwen3 ASR, 자동 모델 폴백
- **스토리지**: [Alibaba OSS](https://www.alibabacloud.com/en/product/object-storage-service) — ASR용 오디오 파일 스테이징
- **문서 추출**: [Docling](https://github.com/docling-project/docling) — PDF/PPTX → 구조화 Markdown
- **PDF 생성**: [WeasyPrint](https://weasyprint.org/) — CJK 지원 Markdown → PDF
- **에이전트 런타임**: [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — AGENTS.md를 읽고 파이프라인을 오케스트레이션

## 무료 사용 범위

SuperRecord는 신규 계정에 무료 쿼터를 제공하는 Alibaba Cloud 서비스를 사용합니다.

### DashScope ASR

**싱가포르(International) 엔드포인트**에서 [Model Studio](https://www.alibabacloud.com/en/product/model-studio)를 활성화하면 각 ASR 모델에 독립적인 무료 쿼터가 부여됩니다:

| 모델 | 무료 쿼터 | 유효기간 | 유료 단가 |
|------|----------|---------|----------|
| `qwen3-asr-flash-filetrans` | 36,000초 (10시간) | 90일 | $0.000035/초 |
| `fun-asr` | 36,000초 (10시간) | 90일 | $0.000035/초 |

- **입력 오디오 길이** 기준 초당 과금 — 출력 텍스트는 무료
- 각 모델이 독립 쿼터를 가지므로, SuperRecord의 폴백 체인으로 **총 ~20시간** 사용 가능
- 일반적인 90분 강의 = ~5,400초 — 모델당 **~6–7개 강의** 무료 처리
- [콘솔](https://modelstudio.console.alibabacloud.com/)에서 **무료 쿼터 전용** 모드를 활성화하면 쿼터 소진 후 과금 방지

### Alibaba Cloud OSS

OSS는 오디오 파일 임시 스테이징(업로드 → ASR → 삭제)에만 사용됩니다. 비용은 미미합니다:

- **업로드 (인바운드)**: 항상 무료
- **스토리지**: ~$0.02/GB/월 (Standard LRS, 싱가포르) — 처리 후 파일 삭제
- **내부 전송**: DashScope가 내부 엔드포인트로 OSS에 접근하면 무료

> 신규 계정은 **1개월 무료 체험** (500GB 스토리지)을 받습니다. 이후에도 일반적인 강의 녹음 처리 비용은 1원 미만 수준입니다. 자세한 내용은 [OSS 가격 정책](https://www.alibabacloud.com/help/en/oss/free-quota-for-new-users) 참조.

## 라이선스

[MIT](LICENSE)

## 로드맵

- [ ] **로컬 ASR 지원** — [whisper.cpp](https://github.com/ggerganov/whisper.cpp) 또는 [MLX Whisper](https://github.com/ml-explore/mlx-examples)를 Apple Silicon에서 실행하여 클라우드 계정 없이 오프라인 전사
- [ ] **네이티브 macOS 앱** — 녹음 관리, 파이프라인 상태, vault 브라우징을 위한 메뉴바 앱
- [ ] Windows / Linux 지원 (Voice Memos 대안)
- [ ] 추가 클라우드 ASR 제공자 (Google Speech-to-Text, Azure Speech)
- [ ] 파이프라인 상태 및 vault 브라우징 Web UI
- [ ] 일괄 처리 모드 (프롬프트 없이 미처리 녹음 전체 처리)
- [ ] 다화자 녹음 화자 분리
