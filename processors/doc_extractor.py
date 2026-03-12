#!/usr/bin/env python3
"""PDF/PPTX/DOCX/Image → Markdown extraction via Docling."""

import sys
import argparse
from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".pptx",
    ".docx",
    ".xlsx",
    ".png",
    ".jpg",
    ".jpeg",
    ".tiff",
    ".bmp",
    ".html",
    ".md",
}


def extract_single(input_path: Path, output_dir: Path) -> Path:
    from docling.document_converter import DocumentConverter

    if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported format: {input_path.suffix}")

    output_dir.mkdir(parents=True, exist_ok=True)

    converter = DocumentConverter()
    result = converter.convert(str(input_path))
    markdown = result.document.export_to_markdown()

    out_name = f"{input_path.stem}_extracted.md"
    out_path = output_dir / out_name

    out_path.write_text(markdown, encoding="utf-8")
    print(f"  [OK] {input_path.name} → {out_name} ({len(markdown)} chars)")
    return out_path


def extract_batch(input_paths: list[Path], output_dir: Path) -> list[Path]:
    results = []
    for p in input_paths:
        try:
            results.append(extract_single(p, output_dir))
        except Exception as e:
            print(f"  [ERROR] {p.name}: {e}")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Document → Markdown extraction (Docling)",
    )
    parser.add_argument("inputs", nargs="+", help="입력 파일 경로(들)")
    parser.add_argument(
        "--output", type=str, required=True, help="출력 디렉토리 (materials/)"
    )
    args = parser.parse_args()

    input_paths = [Path(p) for p in args.inputs]
    missing = [p for p in input_paths if not p.exists()]
    if missing:
        for p in missing:
            print(f"  [ERROR] File not found: {p}")
        sys.exit(1)

    output_dir = Path(args.output)
    results = extract_batch(input_paths, output_dir)

    print(f"\n  Done: {len(results)}/{len(input_paths)} extracted")
    for r in results:
        print(f"    {r}")


if __name__ == "__main__":
    main()
