# Skill: Transcribe

오디오 파일을 텍스트로 전사하는 skill입니다.
하나의 세션이 여러 녹음 파일(파트)로 나뉘어 있을 수 있습니다.

## 입력

- 오디오 파일 경로 1개 이상 (`.m4a`, `.mp3`, `.wav`, `.webm`, `.ogg`)
- 다중 파트일 경우 파트 순서대로 전달

## 출력

### 단일 녹음

- `transcript.json` — 타임스탬프 + 문장 + 감정 메타데이터
- `transcript.txt` — 사람이 읽기 좋은 텍스트 포맷

### 다중 녹음 (같은 세션의 파트들)

- `transcript_01.json`, `transcript_02.json`, ... — 파트별 ASR 결과
- `transcript.txt` — 통합본 (파트 구분자 포함)

## 실행 방법

### 단일 녹음

```bash
python processors/asr_processor.py --input <audio_path> --output <session_dir>
```

### 다중 녹음

각 파트를 순서대로 실행하고, 통합 `transcript.txt`를 생성합니다:

```bash
# 파트별 ASR 실행
python processors/asr_processor.py --input <part1.m4a> --output <session_dir> --part 1
python processors/asr_processor.py --input <part2.m4a> --output <session_dir> --part 2

# 통합 transcript.txt는 Agent가 파트별 .json을 읽어서 직접 생성
```

`--part N` 플래그: 출력 파일명을 `transcript_0N.json`으로 저장합니다.
통합 `transcript.txt`는 Agent가 모든 파트 완료 후 직접 조합합니다.

## 통합 transcript.txt 포맷

```
=== Part 1 ===

[00:35] Okay, hello everyone.
[01:12] Today we'll be talking about...

=== Part 2 ===

[00:05] Alright, let's continue.
[00:20] So where were we...
```

- 각 파트의 타임스탬프는 파트 내 기준 (0:00부터 시작)
- 파트 구분자: `=== Part N ===`

## 파이프라인 위치

Phase 1 — 가장 먼저 실행. 이후 모든 phase의 입력 소스.

## 주의사항

- Alibaba OSS 업로드가 필요합니다 (`.env`에 OSS 설정 필수)
- DashScope API 비동기 폴링 방식 — 긴 녹음은 수 분 소요
- 10초 미만 녹음은 건너뜁니다
- 이미 `transcript.json` (또는 `transcript_0N.json`)이 존재하면 사용자에게 덮어쓸지 확인
- 다중 파트 시, 모든 파트 ASR 완료 후 통합 `transcript.txt` 생성

## 출력 포맷 (transcript.json / transcript_0N.json)

```json
{
  "title": "Linear Algebra W03-1",
  "date": "2025-03-10 11:01:01",
  "duration_seconds": 3228.37,
  "model": "qwen3-asr-flash-filetrans",
  "sentence_count": 444,
  "part": 1,
  "sentences": [
    {
      "timestamp": "[00:35]",
      "begin_ms": 35948,
      "end_ms": 37068,
      "text": "Okay, hello everyone.",
      "emotion": "neutral"
    }
  ]
}
```
