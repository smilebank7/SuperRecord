# AGENTS.md — SuperRecord

SuperRecord는 녹음 파일과 참고자료(PDF, 이미지, 슬라이드)를 함께 처리하여
전사, 번역, 강의노트 생성, 자료 연계까지 수행하는 Agent workspace입니다.

Apple Voice Memos를 직접 스캔하여 미처리 녹음을 감지하고, 대화형으로 분류 후 자동 처리합니다.

## Quick Reference

| 경로 | 역할 |
|------|------|
| `vault/` | 정리된 결과물 (학습/회의/개인) |
| `skills/` | Agent가 로드하는 처리 능력 (SKILL.md) |
| `processors/` | 실제 실행 코드 (Python: `asr_processor.py`, `doc_extractor.py`, `md_to_pdf.py`) |
| `config.yaml` | workspace 설정 (언어, ASR, 과목 등) |
| `registry.md` | 녹음별 파이프라인 상태 추적 DB |

---

## 네이밍 규칙

### 폴더명

| 유형 | 패턴 | 예시 |
|------|------|------|
| 과목 | `kebab-case` 영문 | `compiler`, `data-science` |
| 강의 세션 | `w{주차}-{번호}_{토픽-kebab}` | `w02-1_language-processors` |
| 회의 | `{YYYY-MM-DD}_{제목-kebab}` | `2026-03-11_team-standup` |
| 개인 메모 | `{YYYY-MM-DD}_{제목-kebab}` | `2026-03-11_idea-brainstorm` |

- 토픽은 해당 세션의 핵심 내용을 영문 kebab-case로 요약 (ASR 결과에서 추론)
- 주차/번호를 모르면 question으로 사용자에게 확인

### 파일명

세션 폴더 안에서는 고정된 파일명 사용 (내용에 따라 이름이 달라지지 않음):

| 파일 | 이름 | 설명 |
|------|------|------|
| ASR 원본 (단일) | `transcript.json` | 녹음 1개일 때 |
| ASR 원본 (다중) | `transcript_01.json`, `transcript_02.json`, ... | 녹음 여러 파트일 때 |
| ASR 통합 텍스트 | `transcript.txt` | 항상 통합본 (다중일 때 파트 구분 포함) |
| 번역본 | `transcript_{lang}.md` | 통합 번역 (`transcript_ko.md`) |
| 강의노트 | `notes.md` | 구조화된 학습 노트 |
| 강의노트 PDF | `{과목} {N}주차{M}_강의노트.pdf` | notes.md의 PDF 변환본 |
| 정제 녹취본 | `refined_transcript.md` | 줄글 형태로 정제된 번역 녹취본 |
| 정제 녹취본 PDF | `{과목} {N}주차{M}_녹취본.pdf` | refined_transcript.md의 PDF 변환본 |
| 번역 노트 | `notes_{lang}.md` | 노트 번역본 (`notes_ko.md`) |
| 메타데이터 | `metadata.yaml` | 분류, 날짜, 태그 등 |
| 자료 원본 | `materials/{원본파일명}` | PDF, 이미지 등 원본 보존 |
| 추출 텍스트 | `materials/{이름}_extracted.md` | 자료에서 추출된 텍스트+구조 |

#### 다중 녹음 파트 규칙

하나의 강의/세션이 여러 녹음 파일로 나뉘어 있을 수 있습니다 (예: 중간 휴식, 녹음 앱 재시작 등).

- **단일 녹음**: `transcript.json` + `transcript.txt` (기존과 동일)
- **다중 녹음**: 파트별 `transcript_01.json`, `transcript_02.json`, ... + 통합 `transcript.txt`

통합 `transcript.txt` 포맷 (다중 파트):
```
=== Part 1 ===

[00:35] Okay, hello everyone.
[01:12] Today we'll be talking about...
...

=== Part 2 ===

[00:05] Alright, let's continue.
[00:20] So where were we...
...
```

번역과 노트 생성은 항상 통합 `transcript.txt`를 입력으로 사용합니다.

### vault/ 디렉토리 구조

```
vault/
├── lectures/                     # 학습 목적
│   └── {semester}/               # 예: 2026-1
│       └── {course}/             # 예: compiler
│           └── {session}/        # 예: w02-1_language-processors
│               ├── transcript.json      # 단일 녹음 시
│               ├── transcript_01.json   # 다중 녹음 시 (파트별)
│               ├── transcript_02.json
│               ├── transcript.txt       # 항상 통합본
│               ├── transcript_ko.md
│               ├── notes.md
│               ├── metadata.yaml
│               └── materials/
│                   ├── slides.pdf
│                   └── slides_extracted.md
├── meetings/                     # 회의 목적
│   └── {YYYY-MM-DD}_{title}/
└── personal/                     # 개인 메모
    └── {YYYY-MM-DD}_{title}/
```

---

## Init 프로토콜

`config.yaml`이 없거나, 사용자가 처음 SuperRecord를 사용할 때 실행합니다.

### Init 트리거 조건

다음 중 하나라도 해당하면 Init부터 시작합니다:
- `config.yaml`이 없음
- `config.yaml`의 `courses`가 비어 있음
- 사용자가 "초기 설정", "init", "설정" 등을 요청

### Init Step 1: 언어 설정

> **질문**: "번역 대상 언어를 선택하세요"
> - 한국어 (ko) (추천)
> - 영어 (en)
> - 중국어 (zh)
> - 일본어 (ja)

### Init Step 2: 학기 설정

> **질문**: "현재 학기는?"
> - (직접 입력: 예 "2026-1")

### Init Step 3: 과목 등록

> **질문**: "수강 중인 과목을 등록하세요 (여러 개 가능)"

과목마다 다음을 수집합니다:
- 과목명: 예 "Linear Algebra"
- 과목 key (영문 kebab-case): 예 "linear-algebra"
- 강의 언어: 예 "en"
- 별칭 (자동 감지용): 예 ["linear algebra", "lin alg", "선형대수"]

수집된 과목을 `config.yaml`의 `courses`에 저장합니다.

> **질문**: "더 추가할 과목이 있나요?"
> - 네 (반복)
> - 아니요 (다음 단계)

### Init Step 4: Alibaba Cloud 셋업

ASR과 오디오 업로드에 필요한 Alibaba Cloud 인증을 설정합니다.
Agent가 대화형으로 가이드하며, `aliyun` CLI가 있으면 인프라 생성까지 직접 수행합니다.

#### Step 4-1: `.env` 파일 확인

`.env` 파일 존재 여부와 필수 키를 확인합니다:

| 변수 | 필수 | 용도 | 발급 위치 |
|------|------|------|-----------|
| `DASHSCOPE_API_KEY` | ✅ | ASR API 호출 | [DashScope 콘솔](https://dashscope-intl.console.aliyun.com) → API Keys |
| `OSS_ACCESS_KEY_ID` | ✅ | OSS 오디오 업로드 | RAM User AccessKey (아래 Step에서 생성) |
| `OSS_ACCESS_KEY_SECRET` | ✅ | OSS 인증 | 위와 동일 |
| `OSS_BUCKET` | ✅ | OSS 버킷명 | 아래 Step에서 생성 |
| `OSS_ENDPOINT` | ✅ | OSS 리전 엔드포인트 | 기본: `oss-ap-southeast-1.aliyuncs.com` |

`.env`가 없으면 `.env.example`을 복사하여 안내합니다.

#### Step 4-2: DashScope API Key

- 이미 설정됨 → 다음 단계
- 없음 → 발급 안내:

> Alibaba Cloud International 계정이 필요합니다.
> 1. https://www.alibabacloud.com 에서 계정 생성
> 2. https://dashscope-intl.console.aliyun.com 에서 Model Studio 활성화
> 3. API Keys 메뉴에서 키 발급
> 4. `.env`에 `DASHSCOPE_API_KEY=sk-...` 입력

#### Step 4-3: OSS 버킷 + RAM User

OSS 인증은 **정적 AccessKey** 방식을 사용합니다 (만료 없음, OAuth 불필요).

Agent는 먼저 `aliyun` CLI 설치 여부를 확인합니다:

> **질문** (CLI 미설치 시): "aliyun CLI가 설치되어 있지 않습니다. 설치하시겠습니까?"
> - brew install aliyun-cli → 설치 후 진행
> - 수동으로 설정할게요 → Alibaba Cloud 콘솔에서 직접 생성하도록 안내

**CLI 사용 가능 시 — Agent가 직접 실행:**

Agent가 `aliyun` CLI로 아래를 순차 실행하고, 각 단계 결과를 보고합니다:

1. **인증 확인**: `aliyun sts GetCallerIdentity` — 실패 시 `aliyun configure --mode AK` 안내
2. **OSS 버킷 생성**: `aliyun oss mb oss://{bucket-name} --region ap-southeast-1 --acl private`
3. **RAM User 생성**: `superrecord-oss` 이름으로 전용 유저 생성
4. **권한 정책 생성**: `SuperRecordOSSPolicy` — 해당 버킷 PutObject/GetObject만 허용
5. **정책 연결**: RAM User에 정책 부착
6. **AccessKey 발급**: 정적 AK/SK 생성 → `.env`에 저장

**수동 설정 시 — Agent가 콘솔 안내:**

> 1. https://oss.console.aliyun.com 에서 버킷 생성 (리전: Singapore, ACL: private)
> 2. https://ram.console.aliyun.com 에서 사용자 생성 → AccessKey 발급
> 3. 사용자에게 `AliyunOSSFullAccess` 또는 커스텀 정책 부여
> 4. AK/SK를 `.env`에 입력

#### Step 4-4: 연결 테스트

설정 완료 후 Agent가 OSS 업로드 테스트를 실행합니다:

```python
python3 -c "
import oss2, os
auth = oss2.Auth(os.environ['OSS_ACCESS_KEY_ID'], os.environ['OSS_ACCESS_KEY_SECRET'])
bucket = oss2.Bucket(auth, 'https://' + os.environ['OSS_ENDPOINT'], os.environ['OSS_BUCKET'])
bucket.put_object('_test_connection', b'ok')
bucket.delete_object('_test_connection')
print('OSS 연결 성공')
"
```

- 성공 → 다음 단계
- 실패 → 에러 메시지 기반으로 원인 안내 (잘못된 키, 버킷 없음, 권한 부족 등)

설정 완료 후 `config.yaml`을 저장하고 요약을 보여줍니다.

### Init Step 5: 기존 데이터 감지

`transcriptions/` 폴더에 기존 파일이 있으면:

> **질문**: "기존 전사 파일이 {N}개 발견되었습니다. vault/로 마이그레이션할까요?"
> - 예, 지금 정리 (추천)
> - 나중에

---

## 녹음 스캔 및 분류 프로토콜

사용자가 "체크해줘", "스캔", "새 녹음", "확인" 등을 요청하면,
Agent는 **두 가지 소스**를 동시에 스캔하여 미처리 녹음을 찾고 분류합니다:

1. **Apple Voice Memos** — 기기에서 직접 녹음한 파일
2. **inbox/ 폴더** — 외부에서 받은 녹음 파일 (에어드롭, 다운로드 등)

> **필수 규칙**: 각 Step의 질문은 **반드시** question 도구로 사용자에게 확인합니다.
> 자동 추론이 가능하더라도 추론 결과를 선택지에 포함하여 확인을 받습니다.
> Step을 건너뛰거나 임의로 판단하지 않습니다.

### 소스 1: Voice Memos

녹음 원본은 macOS Apple Voice Memos에서 직접 읽습니다:

- **DB 경로**: `~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/CloudRecordings.db`
- **녹음 파일**: 같은 디렉토리의 `.m4a` 파일
- **스캔 쿼리**:

```sql
SELECT
    COALESCE(NULLIF(ZCUSTOMLABEL, ''), ZENCRYPTEDTITLE, 'Untitled') as title,
    ZPATH,
    ZDURATION,
    datetime(ZDATE + 978307200, 'unixepoch', 'localtime') as recorded_at
FROM ZCLOUDRECORDING
WHERE ZPATH IS NOT NULL AND ZDURATION > 10
ORDER BY ZDATE DESC;
```

> **참고**: `ZDATE`는 Core Data epoch (2001-01-01 기준). Unix epoch 변환: `ZDATE + 978307200`.
> `ZENCRYPTEDTITLE`은 이름과 달리 macOS에서는 평문 (iCloud 전송 시에만 암호화).

### 소스 2: inbox/ 폴더

외부에서 받은 녹음 파일(에어드롭, 다운로드 등)을 드롭하는 폴더입니다:

- **경로**: `config.yaml`의 `inbox_dir` (기본: `inbox/`)
- **지원 확장자**: `config.yaml`의 `inbox_extensions` (기본: `.m4a`, `.mp3`, `.wav`, `.ogg`, `.flac`, `.webm`)
- **파일 정보**: 파일명 + 수정 시간 (duration은 ASR 후 확인)

> **참고**: inbox 파일은 Voice Memos와 달리 DB가 없으므로, 파일명과 파일 시스템 메타데이터만 사용합니다.
> duration은 사전에 알 수 없어 스캔 시 "?" 로 표시하고, ASR 완료 후 registry에 기록합니다.

### Step 1: 통합 스캔 (필수)

두 소스를 **동시에** 스캔하고, `registry.md`와 대조하여 미처리 녹음만 필터링합니다.

**Voice Memos 매칭**: registry.md의 `voice_memos`에 있는 파일명(ZPATH)이 이미 등록되어 있으면 "처리됨".
**inbox 매칭**: registry.md의 `inbox`에 있는 파일명이 이미 등록되어 있으면 "처리됨".

스캔 결과를 소스별로 구분하여 보여줍니다:

```
📱 Voice Memos (미처리 2개):
    1. Calculus W03         | 2026-03-11 | 99m52s
    2. OS Lecture 2-1       | 2026-03-10 | 34m22s

📥 inbox/ (미처리 1개):
    3. lecture_recording.m4a | 2026-03-11 | ?

  이미 처리됨 (3개): Lin Alg W01, Lin Alg W01-2, Physics W02
```

**양쪽 모두 미처리 녹음이 없으면**: "새로운 녹음이 없습니다" 메시지 후 중단합니다.

### Step 2: 처리할 녹음 선택 (필수)

> **질문**: "어떤 녹음을 처리할까요?"
> - (미처리 녹음 목록에서 복수 선택 가능, `multiple: true`)
> - 전부 처리

### Step 2.5: 오디오 그룹핑 (2개 이상 선택 시 — 필수)

선택된 녹음이 2개 이상이면, 같은 세션의 파트 분할 여부를 확인합니다.

> **질문**: "선택한 녹음 중 같은 수업/세션의 파트로 나뉜 녹음이 있나요?"

제목에서 동일 과목/세션으로 추론되는 녹음이 있으면 자동 그룹 제안:
> - "Lin Alg W01" + "Lin Alg W01-2" → 같은 세션 (추천)
> - 각각 별개의 세션
> - (직접 그룹 지정)

**그룹핑 결과**: 이후 Step 3~8은 **세션 단위**로 진행합니다.
- 그룹된 녹음들 → 하나의 세션으로 처리 (다중 파트)
- 그룹되지 않은 녹음 → 각각 독립 세션

### Step 3: 목적 분류 (필수 — 건너뛸 수 없음)

각 세션에 대해:

> **질문**: "이 녹음의 목적은 무엇인가요?"
> - 학습 (강의/수업)
> - 회의 (팀미팅/스터디)
> - 개인 (메모/아이디어)
> - (직접 입력)

### Step 4: 학습인 경우 — 과목 분류 (필수 — 건너뛸 수 없음)

`config.yaml`의 등록된 과목 목록을 선택지로 제시합니다:

> **질문**: "어떤 과목인가요?"
> - (config.yaml에 등록된 과목 목록을 선택지로 제시)
> - (새 과목 추가 — 직접 입력)

녹음 제목에서 과목이 자동 감지되면 해당 선택지를 "(추천)" 표시합니다.
**자동 감지되더라도 반드시 사용자 확인을 받습니다.**

새 과목 추가 시, `config.yaml`에 자동으로 과목을 등록합니다.

### Step 5: 학습인 경우 — 주차/세션 (필수 — 건너뛸 수 없음)

녹음 제목이나 날짜에서 주차를 추론 시도합니다.

> **질문**: "몇 주차, 몇 번째 수업인가요?"
> - {추론 결과} (추천) — 추론 가능한 경우
> - (직접 입력: 예 "2주차 1번")

### Step 6: 폴더 생성 + 자료 안내 (필수 — 건너뛸 수 없음)

분류 결과에 따라 vault/ 폴더 구조를 **즉시 생성**합니다:

```bash
mkdir -p vault/lectures/{semester}/{course}/{session}/materials/
```

생성 후, 사용자에게 자료 안내:

> **질문**: "이 수업에서 사용된 자료(슬라이드, PDF, 이미지 등)가 있나요?"
> - 자료 있음 — 넣고 알려줄게
> - 자료 없음
> - 나중에 추가

**"자료 있음" 선택 시**:
```
📁 자료를 여기에 넣어주세요:
   vault/lectures/{semester}/{course}/{session}/materials/

준비되면 알려주세요!
```
→ 사용자가 "넣었어", "완료", "했어" 등 응답할 때까지 **대기**합니다.
→ 응답 후 materials/ 내 파일 존재를 확인하고, 발견된 파일 목록을 보여줍니다.

**"나중에 추가" 선택 시**: materials 단계를 `skipped`로 표시하고 나머지 파이프라인 진행.
사용자가 나중에 자료를 넣고 재요청하면, 해당 단계만 재실행할 수 있습니다.

### Step 7: 처리 범위 확인 (필수 — 건너뛸 수 없음)

> **질문**: "어떤 처리를 실행할까요?"
> - 전사 + 번역 + 강의노트 + 자료연계 (풀 파이프라인, 추천)
> - 전사 + 번역 + 강의노트
> - 전사 + 번역
> - 전사만 (ASR)

**자료가 있는 경우**: "풀 파이프라인"을 기본 추천합니다.
**자료가 없는 경우**: "전사 + 번역 + 강의노트"를 기본 추천합니다.

### Step 8: 확인 후 실행 (필수 — 건너뛸 수 없음)

분류 결과를 요약해서 보여주고, **반드시 확인 후** 처리를 시작합니다:

```
📋 분류 결과:
  목적: 학습 (강의)
  과목: linear-algebra (Linear Algebra)
  세션: w03-1
  소스: 20260310 110101.m4a (Voice Memos에서 직접 읽음)
  자료: slides.pdf (materials/에 배치됨)
  처리: 전사 + 번역 + 강의노트 + 자료연계

  저장 경로: vault/lectures/2025-1/linear-algebra/w03-1_eigenvalues/

진행할까요?
```

### 필수 확인 체크리스트

파이프라인 실행 전, Agent는 다음이 모두 결정되었는지 자체 점검합니다:

- [ ] 목적 (lectures / meetings / personal)
- [ ] 과목 + 주차/세션 (학습인 경우)
- [ ] 자료 존재 여부 (명시적으로 "없음" 확인 포함)
- [ ] 처리 범위
- [ ] 저장 경로 (vault 폴더 생성 완료)
- [ ] registry.md에 이미 처리된 단계 확인

**하나라도 미결정이면 해당 Step으로 돌아가서 질문합니다.**

---

## 처리 파이프라인

분류 완료 후, 선택된 범위에 따라 순차적으로 실행합니다.

### Phase 1: 전사 (Transcribe)

**skill**: `skills/transcribe/SKILL.md`
**processor**: `processors/asr_processor.py`

**단일 녹음**:
1. 오디오 파일을 Alibaba OSS에 업로드
2. Qwen3 ASR 비동기 전사 요청
3. 결과 폴링 → sentence 추출
4. `transcript.json` + `transcript.txt` 저장

**다중 녹음 (같은 세션의 파트들)**:
1. 각 파트별로 ASR 실행 → `transcript_01.json`, `transcript_02.json`, ...
2. 파트 순서대로 통합 `transcript.txt` 생성 (`=== Part N ===` 구분자)
3. 각 파트의 타임스탬프는 파트 내 기준 (0:00부터 시작)
4. 번역/노트 생성은 항상 통합 `transcript.txt`를 입력으로 사용

### Phase 2: 자료 추출 (Extract Materials)

**skill**: `skills/extract-materials/SKILL.md`
**processor**: `processors/doc_extractor.py`

1. PDF/PPTX → Docling으로 텍스트 + 구조 추출
2. 이미지 → VLM으로 설명 생성 (수식, 다이어그램)
3. `materials/{이름}_extracted.md` 저장
4. 슬라이드 번호 / 페이지 번호 매핑 보존

### Phase 3: 번역 (Translate)

**skill**: `skills/translate/SKILL.md`
**실행**: Agent 직접 수행 (별도 processor 없음)

1. Agent가 transcript.txt를 읽고 직접 번역
2. 타임스탬프 보존
3. 전문 용어는 `원문(번역)` 형태로 주석
4. `transcript_{lang}.md` 저장

### Phase 4: 강의노트 생성 (Generate Notes)

**skill**: `skills/generate-notes/SKILL.md`
**실행**: Agent 직접 수행 (별도 processor 없음)

1. Agent가 전사 + 추출자료를 읽고 직접 구조화된 노트 작성
2. 처음부터 target_language로 생성 (별도 번역 불필요)
3. 포함 내용:
   - 핵심 개념 정리
   - 예시 및 설명
   - 자료 cross-reference (`[슬라이드 p.3]`, `[교재 그림 2.1]`)
   - Q&A 섹션 (강의 중 질문-답변)
   - 용어 정리
4. `notes.md` 저장
5. `notes.md` 생성 후, `processors/md_to_pdf.py`로 `{과목} {N}주차{M}_강의노트.pdf` 자동 생성

### Phase 4.5: 정제 녹취본 (Refined Transcript)

**실행**: Agent 직접 수행 (별도 processor 없음)

1. Agent가 `transcript_ko.md`(번역본)를 읽고 줄글 형태로 정제
2. 타임스탬프 제거, ASR 잡음 교정, 자연스러운 문장으로 재구성
3. 주제별 단락 구분 (빈 줄로 분리)
4. 전문 용어는 첫 등장 시 `영문(한국어)` 형태 유지
5. `refined_transcript.md` 저장
6. `processors/md_to_pdf.py`로 `{과목} {N}주차{M}_녹취본.pdf` 자동 생성

### Phase 5: 정리 (Organize)

**skill**: `skills/organize/SKILL.md`

1. 네이밍 규칙에 따라 vault/ 하위에 세션 폴더 생성 (Step 6에서 이미 생성됨)
2. `metadata.yaml` 생성
3. `registry.md` 업데이트

---

## metadata.yaml 스키마

```yaml
# 필수 필드
title: string              # 세션 제목 (영문, 토픽 기반)
purpose: enum               # lectures | meetings | personal
date: date                  # YYYY-MM-DD
duration: string            # 예: 53m48s
source_language: string     # 녹음 언어 (en, ko, zh, ...)
target_language: string     # 번역 대상 언어

# 학습 전용
course: string              # config.yaml 과목 key
semester: string            # 예: 2026-1
week: integer               # 주차
session: integer             # 세션 번호

# 처리 상태
pipeline:
  transcribed: boolean
  translated: boolean
  notes_generated: boolean
  materials_extracted: boolean

# 자료
materials:
  - type: string            # slides, handout, textbook, image
    filename: string
    pages: string            # 해당 페이지 범위 (optional)

# 자동 생성
tags: list[string]          # 핵심 키워드 (LLM 추출)
summary: string             # 1-2문장 요약 (LLM 생성)
created_at: datetime
updated_at: datetime
```

---

## Processing Registry (`registry.md`)

프로젝트 루트의 `registry.md`는 모든 녹음의 파이프라인 상태를 추적하는 DB입니다.

### 포맷

```markdown
## {녹음 제목}
- voice_memos: {파일1}, {파일2}, ...
- inbox: {파일1}, {파일2}, ...
- parts: {파트 수}
- date: {YYYY-MM-DD}
- duration: {길이}
- vault: {vault/ 내 세션 경로}
- asr: {pending|done|failed|skipped}
- translate: {pending|done|failed|skipped}
- notes: {pending|done|failed|skipped}
- materials: {pending|done|failed|skipped}
```

**소스 필드 규칙**:
- Voice Memos 녹음: `voice_memos:` 필드에 ZPATH 파일명 기록
- inbox 녹음: `inbox:` 필드에 inbox/ 내 파일명 기록
- 두 소스가 혼합된 세션: 각각의 필드에 분리 기록 (둘 다 존재 가능)
- 사용하지 않는 소스 필드는 생략

예시:
- Voice Memos 1개: `voice_memos: 20260310 110101.m4a` / `parts: 1`
- Voice Memos 여러 개: `voice_memos: part1.m4a, part2.m4a` / `parts: 2`
- inbox 1개: `inbox: lecture_recording.m4a` / `parts: 1`
- 혼합: `voice_memos: part1.m4a` + `inbox: external_part2.m4a` / `parts: 2`

### Agent 사용 규칙

- **파이프라인 시작 전**: registry.md에서 해당 녹음의 상태 확인
- **이미 done인 단계**: 건너뜀 (재처리 시 사용자 확인 필요)
- **failed인 단계**: 재시도 대상으로 표시
- **단계 완료 시**: 즉시 registry.md 업데이트 (다음 단계 실패 시 복구 가능)
- **새 녹음 발견 시**: registry.md에 엔트리 추가 (모든 단계 `pending`)

---

## Agent 행동 규칙

### 자동 vs 대화형 판단

| 상황 | 행동 |
|------|------|
| 사용자가 "스캔", "체크", "새 녹음" 등 요청 | Voice Memos + inbox 통합 스캔 프로토콜 시작 |
| 녹음 제목에서 과목/주차 추론 가능 | 추론 결과 제시 + 확인 |
| 녹음 제목에서 추론 불가 | question으로 직접 물어봄 |
| 이미 처리된 세션 | 덮어쓰기 여부 확인 |
| 에러 발생 | 해당 phase에서 중단, 부분 결과 보존, 사용자에게 보고 |

### 파일명에서 과목 자동 감지

녹음 제목에 `config.yaml` 등록 과목의 `name` 또는 `aliases`가 포함되면 자동 매칭 시도:
- "Lin Alg W01" → `linear-algebra`, week=1, session=1
- "OS Lecture 2-2" → `operating-systems`, session=2 (주차 불확실 → 확인)
- "선형대수 2주차1" → `linear-algebra` (별칭 매칭), week=2, session=1

매칭 신뢰도가 낮으면 question으로 확인합니다.

### 실패 시 복구

- ASR 실패: Voice Memos 원본은 그대로 유지 (Apple이 관리), inbox 원본도 삭제하지 않음, 에러 로그 보고
- 번역/노트 생성 실패: transcript는 이미 저장되어 있으므로 해당 phase만 재시도 가능
- 자료 추출 실패: 원본 PDF는 materials/에 복사, 추출은 skip하고 계속 진행
- inbox 파일: 파이프라인 **완전 완료** 전까지 inbox/에서 삭제하지 않음. 완료 후 사용자에게 삭제 여부 확인

### 기존 데이터 마이그레이션

`transcriptions/` 폴더에 이미 처리된 파일이 있으면:
- 사용자에게 vault/로 마이그레이션할지 확인
- 파일명에서 과목/세션 추론 → 적절한 vault/ 경로에 배치
- 기존 .json + .txt 포맷은 그대로 보존 (transcript.json, transcript.txt로 rename)

---

## Skills 참조

각 skill의 상세 정의는 `skills/` 디렉토리의 SKILL.md를 참조하세요:

| Skill | 경로 | 역할 |
|-------|------|------|
| transcribe | `skills/transcribe/SKILL.md` | 오디오 → 전사 |
| extract-materials | `skills/extract-materials/SKILL.md` | PDF/이미지 → 텍스트 |
| generate-notes | `skills/generate-notes/SKILL.md` | 전사+자료 → 강의노트 |
| translate | `skills/translate/SKILL.md` | 원문 → 모국어 번역 |
| organize | `skills/organize/SKILL.md` | 파일 분류 + 정리 |

---

## 환경 설정

### 필수 환경변수 (.env)

```
DASHSCOPE_API_KEY=sk-...          # Qwen3 ASR용
OSS_BUCKET=...                     # Alibaba OSS 버킷
OSS_ENDPOINT=...                   # OSS 엔드포인트
```

### 선택 환경변수

```
ANTHROPIC_API_KEY=sk-...           # 강의노트 생성용 (Claude)
OPENAI_API_KEY=sk-...              # 대안 LLM
```

### Python 의존성

```
pip install requests oss2          # ASR 기본
pip install docling                # PDF/PPTX 추출
pip install anthropic              # LLM 강의노트 (또는 openai)
```
