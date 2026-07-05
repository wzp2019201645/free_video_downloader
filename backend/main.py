import urllib.parse
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from config import CORS_ORIGINS, MAX_CONCURRENT
from models.schemas import (
    DownloadRequest,
    DownloadResponse,
    HealthResponse,
    InfoRequest,
    TaskResponse,
    VideoInfoResponse,
)
from services.task_manager import TaskManager
from services.thumbnail_proxy import fetch_thumbnail
from services.youtube_helper import friendly_youtube_error
from services.douyin_helper import friendly_douyin_error
from register_summary import register_summary_routes

task_manager = TaskManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task_manager.start_cleanup_loop()
    yield


app = FastAPI(
    title="万能视频下载 API",
    description="基于 yt-dlp 的视频下载服务",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_summary_routes(app)


@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        active_tasks=task_manager.active_count,
        max_concurrent=MAX_CONCURRENT,
    )


@app.post("/api/info", response_model=VideoInfoResponse)
async def get_video_info(req: InfoRequest):
    try:
        return await task_manager.ytdlp.extract_info(req.url)
    except Exception as e:
        hint = friendly_douyin_error(e) or friendly_youtube_error(e)
        detail = hint or str(e)
        raise HTTPException(status_code=400, detail=f"解析失败: {detail}")


@app.post("/api/download", response_model=DownloadResponse)
async def start_download(req: DownloadRequest):
    try:
        task_id = await task_manager.create_task(req.url, req.format_id)
        return DownloadResponse(task_id=task_id)
    except RuntimeError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"创建任务失败: {e}")


@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task_manager.to_response(task)


@app.get("/api/thumbnail")
async def proxy_thumbnail(url: str = Query(..., min_length=10)):
    """Proxy thumbnail images to bypass hotlink / mixed-content restrictions."""
    try:
        data, content_type = await fetch_thumbnail(url)
        return Response(
            content=data,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"封面加载失败: {e}")


@app.get("/api/files/{task_id}")
async def download_file(task_id: str):
    task = task_manager.get_task(task_id)
    if not task or not task.filepath:
        raise HTTPException(status_code=404, detail="文件不存在")
    if task.status.value != "completed":
        raise HTTPException(status_code=400, detail="文件尚未下载完成")

    filepath = Path(task.filepath)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="文件已被清理")

    encoded_name = urllib.parse.quote(task.filename or filepath.name)
    return FileResponse(
        path=filepath,
        filename=task.filename or filepath.name,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"
        },
    )
