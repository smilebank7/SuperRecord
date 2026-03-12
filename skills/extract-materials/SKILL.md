# Skill: Extract Materials

강의 자료(PDF, PPTX, 이미지)에서 텍스트와 구조를 추출하는 skill입니다.

## 입력

- 문서 파일: `.pdf`, `.pptx`, `.docx`
- 이미지 파일: `.png`, `.jpg`, `.jpeg`, `.heic`

## 출력

- `materials/{원본파일명}` — 원본 파일 복사 (보존)
- `materials/{이름}_extracted.md` — 추출된 텍스트 + 구조

## 실행 방법

`processors/doc_extractor.py`를 실행합니다.

```bash
python processors/doc_extractor.py --input <file_path> --output <session_dir>/materials/
```

## 추출 엔진

- **PDF/PPTX/DOCX**: Docling (IBM Research) — 테이블, 레이아웃, 수식 보존
- **이미지**: VLM (granite_docling 또는 LLM vision) — 다이어그램, 수식 설명 생성

## 파이프라인 위치

Phase 2 — Phase 1(전사)과 병렬 실행 가능.

## 추출 결과 포맷 (_extracted.md)

```markdown
# Slide 1: Course Overview

Introduction to the course and syllabus.

# Slide 2: Key Concepts

[이미지: Architecture diagram]
- Input → Processing Stage A → Processing Stage B → Output

| Strategy | Characteristics | Examples |
|----------|----------------|---------|
| Approach A | Processes all at once | C, C++ |
| Approach B | Processes incrementally | Python, JS |
```

## 주의사항

- 슬라이드 번호 / 페이지 번호 매핑을 반드시 보존
- 이미지 내 수식은 LaTeX 형태로 추출 시도
- 추출 실패 시: 원본 파일은 materials/에 복사하고, 추출은 skip
- Docling 설치 필요: `pip install docling`
