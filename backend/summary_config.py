"""Configuration for AI video summary (Phase 2). Loaded independently from core config."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(_BACKEND_DIR / ".env")

# HuggingFace 镜像 + 禁用 XET（避免国内网络 401 导致 Whisper 模型下载失败）
os.environ.setdefault("HF_ENDPOINT", os.getenv("HF_ENDPOINT", "https://hf-mirror.com"))
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

SUMMARY_DIR = Path(os.getenv("SUMMARY_DIR", str(_BACKEND_DIR / "summary_temp")))
SUMMARY_MAX_CONCURRENT = int(os.getenv("SUMMARY_MAX_CONCURRENT", "2"))
SUMMARY_MAX_DURATION_SECONDS = int(os.getenv("SUMMARY_MAX_DURATION_SECONDS", "5400"))
SUMMARY_MAX_TRANSCRIPT_CHARS = int(os.getenv("SUMMARY_MAX_TRANSCRIPT_CHARS", "30000"))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# tiny 模型体积更小、下载更快，对短中视频转写足够
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "tiny")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
