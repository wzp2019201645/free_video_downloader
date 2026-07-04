import os
import shutil
from pathlib import Path

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "./downloads"))
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "3"))
FILE_TTL_SECONDS = int(os.getenv("FILE_TTL_SECONDS", "7200"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "2048"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "")
YTDLP_PROXY = os.getenv("YTDLP_PROXY", "").strip()
YTDLP_COOKIES_BROWSER = os.getenv("YTDLP_COOKIES_BROWSER", "").strip()
YTDLP_COOKIES_FILE = os.getenv("YTDLP_COOKIES_FILE", "").strip()

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def resolve_proxy() -> str | None:
    """Return proxy URL for yt-dlp (YouTube etc. need this in restricted networks)."""
    if YTDLP_PROXY:
        return YTDLP_PROXY
    for key in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"):
        val = os.getenv(key, "").strip()
        if val:
            return val
    win_proxy = _read_windows_system_proxy()
    if win_proxy:
        return win_proxy
    from services.youtube_helper import detect_local_proxy

    return detect_local_proxy()


def _read_windows_system_proxy() -> str | None:
    if os.name != "nt":
        return None
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        )
        enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
        if not enabled:
            return None
        server, _ = winreg.QueryValueEx(key, "ProxyServer")
        if not server:
            return None
        if "=" in server:
            for part in server.split(";"):
                part = part.strip()
                if part.lower().startswith("https="):
                    host = part.split("=", 1)[1]
                    return host if "://" in host else f"http://{host}"
            for part in server.split(";"):
                part = part.strip()
                if part.lower().startswith("http="):
                    host = part.split("=", 1)[1]
                    return host if "://" in host else f"http://{host}"
        return server if "://" in server else f"http://{server}"
    except OSError:
        return None


def _dir_has_ffmpeg_tools(dir_path: Path) -> bool:
    """yt-dlp merge requires ffmpeg + ffprobe in the same directory."""
    ffmpeg_ok = (dir_path / "ffmpeg.exe").exists() or (dir_path / "ffmpeg").exists()
    ffprobe_ok = (dir_path / "ffprobe.exe").exists() or (dir_path / "ffprobe").exists()
    return ffmpeg_ok and ffprobe_ok


def resolve_ffmpeg_dir() -> str | None:
    """Return a directory containing both ffmpeg and ffprobe."""
    if FFMPEG_PATH:
        p = Path(FFMPEG_PATH)
        if p.is_file() and _dir_has_ffmpeg_tools(p.parent):
            return str(p.parent)
        if p.is_dir() and _dir_has_ffmpeg_tools(p):
            return str(p)

    found = shutil.which("ffmpeg")
    if found and _dir_has_ffmpeg_tools(Path(found).parent):
        return str(Path(found).parent)

    tools_dir = Path(__file__).resolve().parent.parent / "tools" / "ffmpeg"
    if tools_dir.exists():
        for ffmpeg_exe in tools_dir.rglob("ffmpeg.exe"):
            bin_dir = ffmpeg_exe.parent
            if _dir_has_ffmpeg_tools(bin_dir):
                return str(bin_dir)

    for path in (
        r"C:\ffmpeg\bin",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links"),
    ):
        p = Path(path)
        if _dir_has_ffmpeg_tools(p):
            return str(p)

    return None


def resolve_ffmpeg() -> str | None:
    ffmpeg_dir = resolve_ffmpeg_dir()
    if ffmpeg_dir:
        for name in ("ffmpeg.exe", "ffmpeg"):
            exe = Path(ffmpeg_dir) / name
            if exe.exists():
                return str(exe)
    return None

