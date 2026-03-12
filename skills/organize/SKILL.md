# Skill: Organize

처리된 파일들을 vault/에 네이밍 규칙에 따라 정리하는 skill입니다.

## 역할

1. AGENTS.md의 네이밍 규칙에 따라 vault/ 하위에 세션 폴더 생성
2. `metadata.yaml` 생성
3. `registry.md` 업데이트 (파이프라인 상태 추적)

## 폴더 생성 규칙

### 학습 (lectures)

```
vault/lectures/{semester}/{course}/{session}/
```

예시:
```
vault/lectures/2026-1/compiler/w02-1_language-processors/
vault/lectures/2026-1/data-science/w02-2_regression-analysis/
```

- `{semester}`: config.yaml의 `current_semester` (예: `2026-1`)
- `{course}`: config.yaml의 과목 key (예: `compiler`)
- `{session}`: `w{주차:02d}-{번호}_{토픽-kebab}`
  - 토픽은 전사 내용에서 핵심 주제를 영문 kebab-case로 추론
  - 추론 불가 시 사용자에게 question으로 확인

### 회의 (meetings)

```
vault/meetings/{YYYY-MM-DD}_{title-kebab}/
```

### 개인 (personal)

```
vault/personal/{YYYY-MM-DD}_{title-kebab}/
```

## metadata.yaml 생성

모든 세션 폴더에 `metadata.yaml`을 생성합니다. AGENTS.md의 스키마를 따릅니다.

자동으로 채워지는 필드:
- `title`: 전사 내용에서 추론 (또는 사용자 입력)
- `date`: 녹음 날짜
- `duration`: 녹음 길이
- `source_language`: 감지된 언어
- `tags`: LLM이 전사에서 추출한 키워드
- `summary`: LLM이 생성한 1-2문장 요약
- `pipeline`: 각 phase 실행 여부

## 기존 데이터 마이그레이션

`transcriptions/` 폴더의 기존 파일 처리:

1. 파일명에서 과목/세션 추론:
   - `Lin Alg W01.json` → `linear-algebra`, week=1, session=1
   - `OS Lecture 2-2.json` → `operating-systems`, session=2
   - `Physics W03.json` → `physics`, week=3, session=1

2. vault/ 경로에 배치:
   - `.json` → `transcript.json`으로 rename
   - `.txt` → `transcript.txt`로 rename

3. 사용자 확인 후 이동 실행

## registry.md 관리

모든 파이프라인 단계에서 `registry.md`를 업데이트합니다:

- **새 녹음 처리 시작**: 엔트리 추가 (모든 단계 `pending`)
- **각 단계 완료 시**: 해당 단계를 `done`으로 즉시 업데이트
- **실패 시**: 해당 단계를 `failed`로 업데이트
- **재처리 시**: `failed` → `done`으로 변경

Agent는 파이프라인 시작 전 반드시 registry.md를 읽고 이미 완료된 단계는 건너뜁니다.

## 녹음 원본 관리

### Voice Memos
- Apple Voice Memos가 관리 — Agent가 삭제하지 않음
- vault/에 오디오 파일을 복사하지 않음

### inbox/ 파일
- 파이프라인 **완전 완료**(registry의 모든 단계 `done`) 전까지 inbox/에서 삭제하지 않음
- 파이프라인 완료 후, 사용자에게 삭제 여부 확인:
  > "inbox/의 {파일명} 처리가 완료되었습니다. inbox에서 삭제할까요?"
  > - 삭제 (추천)
  > - 유지
- vault/에 오디오 파일을 복사하지 않음 (전사 결과만 저장)

## 주의사항

- 같은 세션 폴더가 이미 존재하면 덮어쓰기 전 사용자 확인
- metadata.yaml은 새로 생성되더라도 기존 값이 있으면 merge (덮어쓰지 않음)
