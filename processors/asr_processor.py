#!/usr/bin/env python3
"""
Audio → Qwen3 ASR Transcription

Two modes:
  Agent mode:  python processors/asr_processor.py --input <audio> --output <dir>
  Batch mode:  python processors/asr_processor.py [--list|--all|--select 1,2]
"""

import os
import sys
import json
import time
import sqlite3
import argparse
import mimetypes
import subprocess
from pathlib import Path

# ─── Configuration ────────────────────────────────────────────────────────────

RECORDINGS_DIR = (
    Path.home()
    / "Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings"
)
DB_PATH = RECORDINGS_DIR / "CloudRecordings.db"

ASR_MODELS = [
    "qwen3-asr-flash-filetrans",
    "qwen3-asr-flash-filetrans-2025-11-17",
    "fun-asr",
]
POLL_INTERVAL = 10  # seconds
POLL_TIMEOUT = 3600  # 1 hour


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_env():
    for candidate in [PROJECT_ROOT / ".env", Path(__file__).parent / ".env"]:
        if candidate.exists():
            with open(candidate) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip("'\"")
                        if key and value and key not in os.environ:
                            os.environ[key] = value
            break


def get_config(use_china=False):
    """Validate and return configuration dict."""
    load_env()

    dashscope_url = (
        "https://dashscope.aliyuncs.com/api/v1"
        if use_china
        else "https://dashscope-intl.aliyuncs.com/api/v1"
    )

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("Error: DASHSCOPE_API_KEY 환경변수를 설정해주세요.")
        print("  .env 파일에 추가: DASHSCOPE_API_KEY=sk-...")
        sys.exit(1)

    oss_access_key_id = os.getenv("OSS_ACCESS_KEY_ID")
    oss_access_key_secret = os.getenv("OSS_ACCESS_KEY_SECRET")
    oss_bucket = os.getenv("OSS_BUCKET")
    oss_endpoint = os.getenv("OSS_ENDPOINT")
    oss_prefix = os.getenv("OSS_PREFIX", "superrecord")

    missing = []
    if not oss_access_key_id:
        missing.append("OSS_ACCESS_KEY_ID")
    if not oss_access_key_secret:
        missing.append("OSS_ACCESS_KEY_SECRET")
    if not oss_bucket:
        missing.append("OSS_BUCKET")
    if not oss_endpoint:
        missing.append("OSS_ENDPOINT")

    if missing:
        print("Error: Alibaba OSS 설정이 필요합니다.")
        print("  누락된 환경변수:", ", ".join(missing))
        print("  .env 파일에 추가:")
        print("    OSS_ACCESS_KEY_ID=...")
        print("    OSS_ACCESS_KEY_SECRET=...")
        print("    OSS_BUCKET=...")
        print("    OSS_ENDPOINT=oss-ap-southeast-1.aliyuncs.com")
        sys.exit(1)

    return {
        "DASHSCOPE_API_KEY": api_key,
        "DASHSCOPE_BASE_URL": dashscope_url,
        "OSS_ACCESS_KEY_ID": oss_access_key_id,
        "OSS_ACCESS_KEY_SECRET": oss_access_key_secret,
        "OSS_BUCKET": oss_bucket,
        "OSS_ENDPOINT": oss_endpoint,
        "OSS_PREFIX": oss_prefix.strip("/"),
    }


# ─── Voice Memos DB ───────────────────────────────────────────────────────────


def get_recordings():
    """Voice Memos SQLite DB에서 녹음 정보와 한글 이름을 읽습니다."""
    if not DB_PATH.exists():
        print(f"Error: Voice Memos DB를 찾을 수 없습니다: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        """
        SELECT
            COALESCE(
                NULLIF(ZCUSTOMLABEL, ''),
                ZENCRYPTEDTITLE,
                ZCUSTOMLABELFORSORTING,
                'Untitled'
            ) as title,
            ZPATH,
            ZDURATION,
            datetime(ZDATE + 978307200, 'unixepoch', 'localtime') as date
        FROM ZCLOUDRECORDING
        WHERE ZPATH IS NOT NULL AND ZPATH != '' AND ZDURATION > 10
        ORDER BY ZDATE
        """
    ).fetchall()
    conn.close()

    recordings = []
    for title, path, duration, date in rows:
        filepath = RECORDINGS_DIR / path
        if filepath.exists():
            recordings.append(
                {
                    "title": title.strip(),
                    "filename": path,
                    "filepath": str(filepath),
                    "duration": duration,
                    "date": date,
                }
            )
    return recordings


# ─── Alibaba OSS Public Upload ────────────────────────────────────────────────


def upload_to_oss_public(filepath, config):
    try:
        import importlib

        oss2 = importlib.import_module("oss2")
    except ImportError as e:
        raise RuntimeError("oss2 패키지가 필요합니다: pip install oss2") from e

    filename = os.path.basename(filepath).replace(" ", "_")
    key = f"{config['OSS_PREFIX']}/{filename}" if config["OSS_PREFIX"] else filename
    content_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
    size_mb = os.path.getsize(filepath) / (1024 * 1024)

    print(f"  [OSS] Uploading {filename} ({size_mb:.1f}MB)...")

    auth = oss2.Auth(config["OSS_ACCESS_KEY_ID"], config["OSS_ACCESS_KEY_SECRET"])
    bucket = oss2.Bucket(
        auth, f"https://{config['OSS_ENDPOINT']}", config["OSS_BUCKET"]
    )
    headers = {"Content-Type": content_type}
    result = bucket.put_object_from_file(key, filepath, headers=headers)
    if result.status not in (200, 201):
        raise RuntimeError(f"OSS upload failed: status={result.status}")

    signed_url_ttl = int(os.getenv("OSS_SIGNED_URL_TTL", "86400"))
    signed_url = bucket.sign_url("GET", key, signed_url_ttl)
    print(f"  [OSS] Upload complete → signed URL (ttl={signed_url_ttl}s)")
    return signed_url


# ─── DashScope ASR API ────────────────────────────────────────────────────────


class QuotaExhaustedError(RuntimeError):
    """Raised when a model's free quota is exhausted."""

    pass


def submit_transcription(file_url, config, model):
    """비동기 ASR 작업을 제출하고 task_id를 반환합니다."""
    import requests

    url = f"{config['DASHSCOPE_BASE_URL']}/services/audio/asr/transcription"
    headers = {
        "Authorization": f"Bearer {config['DASHSCOPE_API_KEY']}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    payload = {
        "model": model,
        "input": {"file_url": file_url},
        "parameters": {"enable_words": True},
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    data = resp.json()

    # Quota exhausted → caller should try next model
    error_code = data.get("code", "")
    error_msg = data.get("message", "")
    if (
        resp.status_code == 429
        or "quota" in error_msg.lower()
        or "Throttling" in error_code
    ):
        raise QuotaExhaustedError(f"[{model}] Quota exhausted: {error_msg}")

    if resp.status_code != 200:
        raise RuntimeError(f"Submit failed ({resp.status_code}): {resp.text}")

    task_id = data.get("output", {}).get("task_id")
    if not task_id:
        raise RuntimeError(
            f"No task_id in response: {json.dumps(data, ensure_ascii=False)}"
        )
    return task_id


def submit_with_fallback(file_url, config):
    """ASR_MODELS 순서대로 시도하여 첫 성공한 모델로 task 제출."""
    last_error = None
    for model in ASR_MODELS:
        try:
            print(f"  [ASR] Trying model: {model}")
            task_id = submit_transcription(file_url, config, model)
            print(f"  [ASR] Using model: {model}")
            return task_id, model
        except QuotaExhaustedError as e:
            print(f"  [ASR] {e} — trying next model...")
            last_error = e
            continue
    raise RuntimeError(f"All ASR models exhausted. Last error: {last_error}")


def poll_task(task_id, config):
    """작업 완료까지 폴링합니다."""
    import requests

    url = f"{config['DASHSCOPE_BASE_URL']}/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {config['DASHSCOPE_API_KEY']}"}

    start = time.time()
    while time.time() - start < POLL_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Poll failed ({resp.status_code}): {resp.text}")

        data = resp.json()
        status = data.get("output", {}).get("task_status", "UNKNOWN")
        elapsed = int(time.time() - start)

        if status == "SUCCEEDED":
            print(f"\n  [ASR] Completed in {elapsed}s")
            return data
        elif status in ("FAILED", "CANCELED", "UNKNOWN"):
            msg = data.get("output", {}).get("message", "")
            raise RuntimeError(f"Task {status}: {msg}")

        print(f"  [ASR] {status} ... {elapsed}s", end="\r", flush=True)

    raise TimeoutError(f"Task {task_id} timed out after {POLL_TIMEOUT}s")


def fetch_transcription(result):
    """결과 JSON에서 문장 리스트를 추출합니다."""
    import requests

    output = result.get("output", {})
    results_list = output.get("results", [])
    if not results_list:
        single = output.get("result", {})
        if isinstance(single, dict) and single.get("transcription_url"):
            results_list = [single]

    sentences = []
    for entry in results_list:
        trans_url = entry.get("transcription_url", "")
        if not trans_url:
            continue

        resp = requests.get(trans_url, timeout=60)
        if resp.status_code != 200:
            print(f"  [WARN] Failed to fetch transcription_url: {resp.status_code}")
            continue

        data = resp.json()
        for transcript in data.get("transcripts", []):
            for s in transcript.get("sentences", []):
                begin_ms = s.get("begin_time", 0)
                end_ms = s.get("end_time", 0)
                mm = int((begin_ms / 1000) // 60)
                ss = int((begin_ms / 1000) % 60)

                sentences.append(
                    {
                        "timestamp": f"[{mm:02d}:{ss:02d}]",
                        "begin_ms": begin_ms,
                        "end_ms": end_ms,
                        "text": s.get("text", ""),
                        "emotion": s.get("emotion", ""),
                    }
                )

    return sentences


# ─── Output ───────────────────────────────────────────────────────────────────


def fmt_duration(seconds):
    h, remainder = divmod(int(seconds), 3600)
    m, s = divmod(remainder, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


def fmt_size(filepath):
    return f"{os.path.getsize(filepath) / (1024 * 1024):.1f}MB"


def save_result(
    title,
    date,
    duration,
    sentences,
    output_dir,
    *,
    fixed_names=False,
    part=None,
    model=ASR_MODELS[0],
):
    if fixed_names:
        if part is not None:
            txt_path = output_dir / f"transcript_{part:02d}.txt"
            json_path = output_dir / f"transcript_{part:02d}.json"
        else:
            txt_path = output_dir / "transcript.txt"
            json_path = output_dir / "transcript.json"
    else:
        safe_name = title.replace("/", "_").replace("\\", "_").strip()
        txt_path = output_dir / f"{safe_name}.txt"
        json_path = output_dir / f"{safe_name}.json"

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n")
        f.write(f"# 날짜: {date}\n")
        f.write(f"# 길이: {fmt_duration(duration)}\n")
        f.write(f"# 모델: {model}\n")
        f.write(f"# {'─' * 50}\n\n")
        for s in sentences:
            f.write(f"{s['timestamp']} {s['text']}\n")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "title": title,
                "date": date,
                "duration_seconds": duration,
                "model": model,
                "sentence_count": len(sentences),
                **({"part": part} if part is not None else {}),
                "sentences": sentences,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    return txt_path, json_path


# ─── Processing ───────────────────────────────────────────────────────────────


def process_single(filepath, config, output_dir, title=None, part=None):
    """Agent mode: process a single audio file → transcript.json + transcript.txt
    If part is specified, outputs transcript_0N.json instead."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Audio file not found: {filepath}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    title = title or filepath.stem
    file_url = upload_to_oss_public(str(filepath), config)

    task_id, model = submit_with_fallback(file_url, config)
    print(f"  [ASR] Task ID: {task_id}")

    print(f"  [ASR] Waiting for result (polling every {POLL_INTERVAL}s)...")
    result = poll_task(task_id, config)
    sentences = fetch_transcription(result)

    if not sentences:
        raw_path = output_dir / "transcript_raw.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  [WARN] 문장 추출 실패. Raw 결과: {raw_path}")
        return None

    import datetime

    date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    duration = sum((s["end_ms"] - s["begin_ms"]) for s in sentences) / 1000

    txt_path, json_path = save_result(
        title,
        date,
        duration,
        sentences,
        output_dir,
        fixed_names=True,
        part=part,
        model=model,
    )
    print(f"  [OK] {txt_path.name} ({len(sentences)} sentences)")
    return json_path


def process_recording(rec, config, output_dir):
    filepath = rec["filepath"]

    file_url = upload_to_oss_public(filepath, config)

    task_id, model = submit_with_fallback(file_url, config)
    print(f"  [ASR] Task ID: {task_id}")

    print(f"  [ASR] Waiting for result (polling every {POLL_INTERVAL}s)...")
    result = poll_task(task_id, config)

    sentences = fetch_transcription(result)

    if not sentences:
        raw_path = output_dir / f"{rec['title']}_raw.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  [WARN] 문장 추출 실패. Raw 결과: {raw_path}")
        return

    txt_path, json_path = save_result(
        rec["title"],
        rec["date"],
        rec["duration"],
        sentences,
        output_dir,
        model=model,
    )
    print(f"  [OK] {txt_path.name} ({len(sentences)} sentences)")


# ─── CLI ──────────────────────────────────────────────────────────────────────


def print_recordings(recordings):
    print(f"\n{'=' * 60}")
    print(f"  Voice Memos ({len(recordings)} recordings)")
    print(f"{'=' * 60}\n")

    for i, rec in enumerate(recordings, 1):
        dur = fmt_duration(rec["duration"])
        size = fmt_size(rec["filepath"])
        print(f"  [{i}] {rec['title']}")
        print(f"      {rec['date']}  |  {dur}  |  {size}")
        print(f"      {rec['filename']}")
        print()


def select_recordings(recordings, args):
    if args.all:
        return list(range(len(recordings)))

    if args.select:
        indices = [int(x.strip()) - 1 for x in args.select.split(",")]
        return [i for i in indices if 0 <= i < len(recordings)]

    sel = input("처리할 번호를 입력하세요 (예: 1,2,3 또는 all): ").strip()
    if sel.lower() == "all":
        return list(range(len(recordings)))

    indices = [int(x.strip()) - 1 for x in sel.split(",")]
    return [i for i in indices if 0 <= i < len(recordings)]


def main():
    parser = argparse.ArgumentParser(
        description="Audio → Qwen3 ASR Transcription",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--input", type=str, help="단일 오디오 파일 경로 (Agent mode)")
    parser.add_argument("--title", type=str, help="전사 제목 (--input과 함께 사용)")
    parser.add_argument(
        "--part", type=int, help="파트 번호 (다중 녹음 시, 출력: transcript_0N.json)"
    )

    parser.add_argument("--list", action="store_true", help="녹음 목록만 표시")
    parser.add_argument("--all", action="store_true", help="모든 녹음 처리")
    parser.add_argument("--select", type=str, help="처리할 번호 (예: 1,2,3)")
    parser.add_argument(
        "--output", type=str, default="./transcriptions", help="출력 디렉토리"
    )
    parser.add_argument(
        "--china", action="store_true", help="중국 본토 DashScope 엔드포인트"
    )
    args = parser.parse_args()

    config = get_config(use_china=args.china)

    if args.input:
        result = process_single(
            args.input, config, args.output, title=args.title, part=args.part
        )
        if result:
            print(f"\n  Output: {result}")
        else:
            sys.exit(1)
        return

    recordings = get_recordings()
    if not recordings:
        print("녹음 파일을 찾을 수 없습니다.")
        sys.exit(1)

    print_recordings(recordings)

    if args.list:
        return

    selected = select_recordings(recordings, args)
    if not selected:
        print("처리할 녹음이 선택되지 않았습니다.")
        return

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'─' * 60}")
    print(f"  Processing {len(selected)} recording(s)")
    print(f"  Output:   {output_dir.resolve()}")
    print(f"  Endpoint: {config['DASHSCOPE_BASE_URL']}")
    print(f"  Models:   {' → '.join(ASR_MODELS)}")
    print(f"{'─' * 60}\n")

    success = 0

    for i, idx in enumerate(selected):
        rec = recordings[idx]
        print(
            f"[{i + 1}/{len(selected)}] {rec['title']} ({fmt_duration(rec['duration'])})"
        )
        try:
            process_recording(rec, config, output_dir)
            success += 1
        except Exception as e:
            print(f"  [ERROR] {e}")
        print()

    print(f"\n{'=' * 60}")
    print(f"  Done: {success}/{len(selected)} processed")
    print(f"  Output: {output_dir.resolve()}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
