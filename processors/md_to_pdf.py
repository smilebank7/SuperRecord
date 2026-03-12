#!/usr/bin/env python3
"""Markdown to PDF converter using WeasyPrint.

Usage:
  python processors/md_to_pdf.py --input notes.md --output notes.pdf [--css style.css]
"""

from __future__ import annotations

import argparse
import importlib
import re
import sys
from pathlib import Path


DEFAULT_CSS = """
@page {
  size: A4;
  margin: 25mm;
  @bottom-center {
    content: "Page " counter(page) " / " counter(pages);
    font-family: "Noto Sans CJK KR", "Apple SD Gothic Neo", sans-serif;
    font-size: 10pt;
    color: #666666;
  }
}

html, body {
  font-family: "Noto Sans CJK KR", "Apple SD Gothic Neo", sans-serif;
  font-size: 11pt;
  line-height: 1.7;
  color: #1f2937;
}

body {
  margin: 0;
  padding: 0;
}

article {
  word-break: keep-all;
  overflow-wrap: break-word;
}

h1, h2, h3 {
  line-height: 1.3;
  margin-top: 1.2em;
  margin-bottom: 0.5em;
  color: #111827;
}

h1 {
  font-size: 22pt;
  border-bottom: 2px solid #d1d5db;
  padding-bottom: 0.25em;
  margin-top: 0;
}

h2 {
  font-size: 16pt;
  border-left: 5px solid #9ca3af;
  padding-left: 0.5em;
}

h3 {
  font-size: 13pt;
}

article > blockquote:first-of-type,
.meta-block {
  border: 1px solid #cbd5e1;
  border-left: 6px solid #334155;
  border-radius: 8px;
  background: #f8fafc;
  margin: 0 0 1.2em 0;
  padding: 12px 14px;
}

blockquote {
  border-left: 4px solid #9ca3af;
  color: #374151;
  margin: 1em 0;
  padding: 0.1em 0 0.1em 1em;
}

pre {
  background: #111827;
  color: #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  overflow-x: auto;
  white-space: pre-wrap;
}

code {
  font-family: Consolas, "SF Mono", Menlo, monospace;
  font-size: 0.9em;
}

pre code {
  background: transparent;
  color: inherit;
}

:not(pre) > code {
  background: #eef2ff;
  color: #1e293b;
  border-radius: 4px;
  padding: 0.1em 0.35em;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 1em 0;
  font-size: 10.5pt;
}

th, td {
  border: 1px solid #cbd5e1;
  padding: 7px 9px;
  text-align: left;
  vertical-align: top;
}

th {
  background: #e2e8f0;
  color: #0f172a;
}

tr:nth-child(even) td {
  background: #f8fafc;
}

ul, ol {
  padding-left: 1.35em;
}

img {
  max-width: 100%;
  height: auto;
}

.toc {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #f9fafb;
  padding: 10px 14px;
}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Markdown file to PDF")
    _ = parser.add_argument("--input", required=True, help="Input markdown file path")
    _ = parser.add_argument("--output", required=True, help="Output pdf file path")
    _ = parser.add_argument("--css", help="Optional custom CSS file path")
    return parser.parse_args()


def build_html(markdown_text: str, base_dir: Path) -> str:
    markdown_module = importlib.import_module("markdown")
    body_html = markdown_module.markdown(
        markdown_text,
        extensions=["tables", "fenced_code", "toc"],
        output_format="html",
    )

    body_html = re.sub(
        r"(<article>\s*<h1[^>]*>.*?</h1>\s*)(<blockquote>)",
        r"\1<blockquote class=\"meta-block\">",
        f"<article>{body_html}</article>",
        count=1,
        flags=re.DOTALL,
    )

    return f"""<!doctype html>
<html lang=\"ko\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <base href=\"{base_dir.resolve().as_uri()}/\" />
  </head>
  <body>
    {body_html}
  </body>
</html>
"""


def convert_markdown_to_pdf(
    input_path: Path, output_path: Path, css_path: Path | None
) -> int:
    weasyprint_module = importlib.import_module("weasyprint")
    css_cls = weasyprint_module.CSS
    html_cls = weasyprint_module.HTML

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if input_path.suffix.lower() != ".md":
        raise ValueError(f"Input file must be a markdown file: {input_path}")

    markdown_text = input_path.read_text(encoding="utf-8")
    html_text = build_html(markdown_text, input_path.parent)

    stylesheets = [css_cls(string=DEFAULT_CSS)]
    if css_path is not None:
        if not css_path.exists():
            raise FileNotFoundError(f"CSS file not found: {css_path}")
        stylesheets.append(css_cls(filename=str(css_path)))

    output_path.parent.mkdir(parents=True, exist_ok=True)

    document = html_cls(string=html_text, base_url=str(input_path.parent)).render(
        stylesheets=stylesheets
    )
    page_count = len(document.pages)
    document.write_pdf(str(output_path))
    return page_count


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    css_path = Path(args.css) if args.css else None

    try:
        pages = convert_markdown_to_pdf(input_path, output_path, css_path)
        print(f"[OK] {output_path.name} ({pages} pages)")
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
