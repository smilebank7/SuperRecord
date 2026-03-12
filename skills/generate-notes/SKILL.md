# Skill: Generate Notes

전사 결과와 추출된 자료를 기반으로 구조화된 강의노트를 생성하는 skill입니다.

## 실행 방식

**Agent 직접 수행** — 별도 processor 없음.
Agent가 transcript + materials를 읽고 직접 구조화된 노트를 작성합니다.

## 입력

- `transcript.json` 또는 `transcript.txt` — 전사 결과 (필수)
- `materials/*_extracted.md` — 추출된 자료 (선택)
- `metadata.yaml` — 과목, 주차 등 컨텍스트 (선택)

## 출력

- `notes.md` — 구조화된 강의노트 (target_language로 작성)
- `{과목} {N}주차{M}_강의노트.pdf` — notes.md의 PDF 변환본

## PDF 변환

Agent가 notes.md 작성 완료 후, 자동으로 PDF를 생성합니다:

```bash
python processors/md_to_pdf.py --input <session_dir>/notes.md --output "<session_dir>/{과목} {N}주차{M}_강의노트.pdf"
```

## 파이프라인 위치

Phase 4 — Phase 1(전사) + Phase 2(자료추출) 이후.
번역(Phase 3)과 독립 — 노트는 처음부터 target_language로 생성.

## 노트 구조

```markdown
# {세션 제목}

> **과목**: {course_name} | **주차**: {N}주차 {M}번 | **날짜**: {YYYY-MM-DD}
> **요약**: {1~2문장 강의 요약}

## 핵심 개념

### 1. {Core Concept} ({번역})
- 정의: {concept definition}
- 핵심 포인트: {key insight}
  [슬라이드 p.3 참조]

### 2. Compilation vs Interpretation
...

## 강의 중 Q&A

- **Q** [50:39]: execution time의 의미?
- **A**: 컴파일된 target program이 특정 task를 수행하는 데 걸리는 시간

## 용어 정리

| 영문 | 한국어 | 설명 |
|------|--------|------|
| Semantically equivalent | 의미적으로 동등한 | 소스 코드와 목적 코드의 동작이 같음 |
| Lexical analyzer | 어휘 분석기 | 문자열을 토큰으로 분리 |
```

## 자료 Cross-Reference 규칙

- 슬라이드 참조: `[슬라이드 p.{번호}]` 또는 `[슬라이드 #{슬라이드번호}]`
- 교재 참조: `[교재 p.{번호}]` 또는 `[교재 그림 {번호}]`
- 전사 참조: `[전사 {타임스탬프}]` 예: `[전사 23:15]`

## 작성 가이드라인

- 전사 텍스트의 ASR 오류를 자연스럽게 교정 (원문 의미 보존)
- 강의 흐름 순서대로 정리 (시간순)
- 교수의 부연 설명과 예시를 핵심 개념에 통합
- 질문-답변은 별도 섹션으로 분리
- 전문 용어는 `영문(한국어)` 형태로 병기
