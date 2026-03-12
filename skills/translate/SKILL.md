# Skill: Translate

전사 결과를 사용자의 모국어로 번역하는 skill입니다.

## 실행 방식

**Agent 직접 수행** — 별도 processor 없음.
Agent가 `transcript.txt`를 읽고 직접 번역하여 `transcript_{lang}.md`를 작성합니다.

## 입력

- `transcript.txt` — 타임스탬프 포함 전사 텍스트
- `config.yaml` — target_language 참조

## 출력

- `transcript_{lang}.md` — 번역된 전사 (예: `transcript_ko.md`)

## 파이프라인 위치

Phase 3 — Phase 1(전사) 이후.

## 번역 규칙

### 타임스탬프 보존

번역 후에도 원본 타임스탬프를 유지합니다:

```markdown
[00:35] 자, 안녕하세요 여러분.
[00:37] 오늘 강의를 시작하겠습니다.
[00:40] 지난 주에 recitation(보충 수업)이 있었고, 그때 이번 학기에 배울 내용을 설명했습니다.
```

### 전문 용어 처리

- 전문 용어의 첫 등장 시: `영문(한국어)` 형태로 병기
  - 예: `semantically equivalent(의미적으로 동등한)`
- 이후 등장: 한국어만 사용하되, 영문이 더 자연스러운 경우 영문 유지
  - 예: `GCC`, `Python`, `bytecode` 등 고유명사는 원문 유지

### 청크 분할

- 긴 전사 텍스트는 자연스러운 경계(주제 전환, 휴지)에서 분할
- 각 청크를 독립적으로 번역하되, 용어 일관성 유지

### 품질 기준

- ASR 오류로 인한 이상한 문장은 문맥에서 교정하여 번역
- 교수의 구어체는 자연스러운 한국어 구어체로 번역
- "like", "you know", "right?" 등 필러는 맥락상 필요한 경우만 번역
