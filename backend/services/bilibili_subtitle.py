"""Fetch Bilibili subtitles via Player WBI API."""

from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import urljoin

import requests

from models.summary_schemas import TranscriptSegment
from services.bilibili_helper import DEFAULT_UA, warmup_bilibili_cookies
from services.bilibili_wbi import get_wbi_keys, sign_wbi_params

logger = logging.getLogger(__name__)

_PLAYER_WBI_URL = "https://api.bilibili.com/x/player/wbi/v2"
_PAGE_LIST_URL = "https://api.bilibili.com/x/player/pagelist"
_VIEW_URL = "https://api.bilibili.com/x/web-interface/view"

_BVID_RE = re.compile(r"BV[\w]+", re.I)
_AID_RE = re.compile(r"av(\d+)", re.I)


def _parse_bvid(url: str) -> Optional[str]:
    m = _BVID_RE.search(url)
    return m.group(0) if m else None


def _parse_aid(url: str) -> Optional[int]:
    m = _AID_RE.search(url)
    return int(m.group(1)) if m else None


def _session_with_cookies(url: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {"User-Agent": DEFAULT_UA, "Referer": "https://www.bilibili.com/"}
    )
    cookiefile = warmup_bilibili_cookies(url)
    if cookiefile:
        session.cookies.update(_load_netscape_cookies(cookiefile))
    return session


def _load_netscape_cookies(path: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 7:
                    cookies[parts[5].strip()] = parts[6].strip()
    except OSError:
        pass
    return cookies


def _resolve_ids(url: str, session: requests.Session) -> tuple[Optional[str], Optional[int], int]:
    bvid = _parse_bvid(url)
    aid = _parse_aid(url)

    if bvid and not aid:
        resp = session.get(_VIEW_URL, params={"bvid": bvid}, timeout=15)
        if resp.ok:
            aid = resp.json().get("data", {}).get("aid")

    params: dict = {}
    if bvid:
        params["bvid"] = bvid
    if aid:
        params["aid"] = aid

    resp = session.get(_PAGE_LIST_URL, params=params, timeout=15)
    resp.raise_for_status()
    pages = resp.json().get("data") or []
    if not pages:
        raise RuntimeError("无法获取 B 站视频分 P 信息")
    cid = int(pages[0]["cid"])
    if not bvid and pages[0].get("bvid"):
        bvid = pages[0]["bvid"]
    if not aid and pages[0].get("aid"):
        aid = int(pages[0]["aid"])
    return bvid, aid, cid


def _pick_subtitle_url(subtitles: list[dict]) -> Optional[str]:
    if not subtitles:
        return None
    preferred = ("zh-CN", "zh-Hans", "zh", "ai-zh", "ai-cn")
    for lang in preferred:
        for item in subtitles:
            if item.get("lan") == lang and item.get("subtitle_url"):
                return item["subtitle_url"]
    for item in subtitles:
        if item.get("subtitle_url"):
            return item["subtitle_url"]
    return None


def _normalize_subtitle_url(raw_url: str) -> str:
    if raw_url.startswith("//"):
        return "https:" + raw_url
    if raw_url.startswith("/"):
        return urljoin("https://www.bilibili.com", raw_url)
    return raw_url


def _parse_bilibili_subtitle_json(data: dict) -> list[TranscriptSegment]:
    body = data.get("body") or data.get("subtitles") or []
    segments: list[TranscriptSegment] = []
    for item in body:
        text = (item.get("content") or item.get("subtitle") or "").strip()
        if not text:
            continue
        start_ms = item.get("from") or item.get("start") or 0
        end_ms = item.get("to") or item.get("end") or start_ms
        if isinstance(start_ms, str):
            start_ms = float(start_ms)
        if isinstance(end_ms, str):
            end_ms = float(end_ms)
        if start_ms > 1000 or end_ms > 1000:
            start = float(start_ms) / 1000.0
            end = float(end_ms) / 1000.0
        else:
            start = float(start_ms)
            end = float(end_ms)
        segments.append(TranscriptSegment(start=start, end=end, text=text))
    return segments


def fetch_bilibili_subtitles(url: str) -> list[TranscriptSegment]:
    session = _session_with_cookies(url)
    bvid, aid, cid = _resolve_ids(url, session)

    # 优先：View API 字幕列表（部分 AI 字幕仅在此返回）
    try:
        view_params: dict = {}
        if bvid:
            view_params["bvid"] = bvid
        elif aid:
            view_params["aid"] = aid
        view_resp = session.get(_VIEW_URL, params=view_params, timeout=15)
        if view_resp.ok:
            subtitle_obj = view_resp.json().get("data", {}).get("subtitle") or {}
            view_list = subtitle_obj.get("list") or []
            subtitle_url = _pick_subtitle_url(view_list)
            if subtitle_url:
                segments = _download_subtitle_json(session, subtitle_url)
                if segments:
                    logger.info("Fetched %d segments from Bilibili View API", len(segments))
                    return segments
    except Exception as exc:
        logger.warning("Bilibili View API subtitle failed: %s", exc)

    img_key, sub_key = get_wbi_keys(session)
    params: dict = {"cid": cid}
    if bvid:
        params["bvid"] = bvid
    if aid:
        params["aid"] = aid
    signed = sign_wbi_params(params, img_key, sub_key)

    resp = session.get(_PLAYER_WBI_URL, params=signed, timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") != 0:
        raise RuntimeError(payload.get("message") or "B 站 Player API 返回错误")

    subtitles = (payload.get("data") or {}).get("subtitle", {}).get("subtitles") or []
    subtitle_url = _pick_subtitle_url(subtitles)
    if not subtitle_url:
        raise RuntimeError("该 B 站视频暂无可用字幕")

    segments = _download_subtitle_json(session, subtitle_url)
    if not segments:
        raise RuntimeError("B 站字幕内容为空")
    logger.info("Fetched %d subtitle segments from Bilibili Player API", len(segments))
    return segments


def _download_subtitle_json(session: requests.Session, raw_url: str) -> list[TranscriptSegment]:
    subtitle_url = _normalize_subtitle_url(raw_url)
    sub_resp = session.get(subtitle_url, timeout=30)
    sub_resp.raise_for_status()
    data = sub_resp.json()
    return _parse_bilibili_subtitle_json(data)
