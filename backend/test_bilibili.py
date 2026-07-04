"""End-to-end integration test for Bilibili download."""

import asyncio
import glob
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from services.ytdlp_service import YtdlpService

BILIBILI_URL = "https://www.bilibili.com/video/BV1hJjk67E33"


def _find_ffmpeg() -> bool:
    if shutil.which("ffmpeg"):
        return True
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
    ]
    for path in candidates:
        if Path(path).exists():
            os.environ["PATH"] = str(Path(path).parent) + os.pathsep + os.environ.get("PATH", "")
            return True
    return False


async def main():
    if not _find_ffmpeg():
        print("SKIP: ffmpeg not available yet")
        return 1

    svc = YtdlpService()
    print("1) extract_info...")
    info = await svc.extract_info(BILIBILI_URL)
    print(f"   title: {info.title}")
    print(f"   formats: {len(info.formats)}")
    assert info.formats, "no formats returned"

    fmt = info.formats[min(2, len(info.formats) - 1)]
    print(f"2) download format: {fmt.quality} ({fmt.format_id})...")
    outdir = Path(tempfile.mkdtemp())
    try:
        filename, filepath = await svc.download(
            BILIBILI_URL, fmt.format_id, outdir, lambda p: None
        )
        size = Path(filepath).stat().st_size
        print(f"   OK: {filename} ({size} bytes)")
        assert size > 100_000, f"file too small: {size}"
        print("\nAll integration tests passed!")
        return 0
    finally:
        shutil.rmtree(outdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
