# 万能视频下载网站 — 方案设计文档

> 版本：v1.0 | 更新日期：2026-06-21

## 1. 架构概览

```
┌─────────────────────────────────────────────────────┐
│                   用户浏览器 / 手机                    │
│  Vue 3 + Tailwind CSS（参考 codefather painting UI） │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP REST
┌──────────────────────▼──────────────────────────────┐
│              FastAPI 后端 (Python 3.11+)              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ API Routes  │→ │ TaskManager  │→ │ YtdlpService│ │
│  └─────────────┘  └──────────────┘  └─────┬──────┘  │
└─────────────────────────────────────────────┼────────┘
                                              │
                              ┌───────────────▼────────┐
                              │   yt-dlp Python API    │
                              │  (YoutubeDL 类调用)     │
                              └───────────────┬────────┘
                                              │
                              ┌───────────────▼────────┐
                              │  临时目录 /tmp/downloads │
                              │  (2h 自动清理)          │
                              └────────────────────────┘
```

## 2. 技术选型

| 层级 | 技术 | 选型理由 |
|------|------|---------|
| 后端框架 | FastAPI | 异步、自动 OpenAPI 文档、与 yt-dlp 同 Python 生态 |
| 下载核心 | yt-dlp (Python API) | 170k+ Stars，支持 1000+ 站点，社区活跃 |
| 前端框架 | Vue 3 + Vite | 轻量、响应式、开发体验好 |
| 样式 | Tailwind CSS | 快速实现独特 UI，移动端友好 |
| 任务存储 | 内存 dict + asyncio | 无数据库，轻量 |
| 文件存储 | 本地临时目录 | 下载完成后供浏览器拉取 |
| 部署 | Docker Compose | 一键启动前后端 |

### 为什么不直接用 MeTube？

| 对比项 | MeTube | 本项目 |
|--------|--------|--------|
| Stars | 13k+ | — |
| 前端 | Angular（改造成本高） | Vue 3 全新定制 UI |
| 模式 | 自托管 NAS，文件持久存储 | 公开网站，临时文件 + 浏览器下载 |
| 定制性 | 低（需改 Angular 组件） | 高（完全控制 UI/UX） |
| 借鉴 | yt-dlp 调用思路 | 直接使用 yt-dlp Python API |

## 3. API 设计

### 3.1 解析视频信息

```
POST /api/info
Content-Type: application/json

Request:
{ "url": "https://www.youtube.com/watch?v=..." }

Response 200:
{
  "title": "视频标题",
  "thumbnail": "https://...",
  "duration": 360,
  "uploader": "频道名",
  "formats": [
    {
      "format_id": "137",
      "quality": "1080p",
      "ext": "mp4",
      "filesize": 52428800,
      "vcodec": "avc1",
      "acodec": "none"
    }
  ]
}
```

### 3.2 创建下载任务

```
POST /api/download
Content-Type: application/json

Request:
{ "url": "https://...", "format_id": "137" }

Response 200:
{ "task_id": "abc123def456" }
```

### 3.3 查询任务进度

```
GET /api/tasks/{task_id}

Response 200:
{
  "task_id": "abc123def456",
  "status": "downloading",       // pending | downloading | completed | failed
  "progress": 45.2,              // 0-100
  "filename": "视频标题.mp4",
  "file_url": null               // completed 时有值
}

Response 404: { "detail": "Task not found" }
```

### 3.4 下载文件

```
GET /api/files/{task_id}
→ Content-Disposition: attachment; filename="视频标题.mp4"
→ 文件二进制流
```

### 3.5 健康检查

```
GET /api/health
→ { "status": "ok", "active_tasks": 1, "max_concurrent": 3 }
```

## 4. 核心模块设计

### 4.1 YtdlpService

```python
class YtdlpService:
    async def extract_info(url: str) -> VideoInfo
    async def download(url, format_id, output_dir, progress_hook) -> str
```

- 使用 `yt_dlp.YoutubeDL` 类（非 subprocess）
- `extract_info`: `skip_download=True`，返回 formats 列表
- `download`: 指定 `format_id`，注册 `progress_hooks` 回调
- formats 过滤：按分辨率生成 `bestvideo[height<=N]+bestaudio/best` 格式选择器
- **Bilibili 412 修复**（`services/bilibili_helper.py`）：curl_cffi Cookie 预热 + Edge impersonate + 读取页面内嵌 playinfo
- 视频合并需 ffmpeg（Docker 已内置；本地 `pip install imageio-ffmpeg`）

### 4.2 TaskManager

```python
class TaskManager:
    tasks: dict[str, Task]           # 内存任务表
    max_concurrent: int = 3          # 并发上限
    file_ttl: int = 7200             # 文件保留 2 小时

    async def create_task(url, format_id) -> str
    async def get_task(task_id) -> Task
    async def cleanup_expired()      # 后台定时清理
```

- 任务状态机：`pending → downloading → completed | failed`
- 后台 asyncio 任务每 10 分钟清理过期文件
- 下载完成后生成 `file_url = /api/files/{task_id}`

### 4.3 前端组件结构

```
App.vue
├── AppHeader.vue          # 导航栏（Logo + Pro 预留）
├── HeroSection.vue        # 大标题 + URL 输入
├── VideoResult.vue        # 解析结果（封面 + 格式选择 + 下载）
├── PlatformGrid.vue       # 支持平台卡片网格
├── DownloadProgress.vue   # 进度条组件
├── AppFooter.vue          # 版权提示
└── api/client.js          # Axios 封装
```

## 5. UI 设计规范

参考 [ai.codefather.cn/painting](https://ai.codefather.cn/painting)：

| 元素 | 规范 |
|------|------|
| 主色 | `#1677FF` |
| 背景 | `#F5F5F5` |
| 卡片背景 | `#FFFFFF` |
| 圆角 | `12px`（卡片）、`9999px`（输入框/按钮） |
| 阴影 | `0 2px 8px rgba(0,0,0,0.08)` |
| 标题字号 | Hero `2.5rem`，卡片 `1rem` |
| 标签 | `#标签名`，灰色小字 |
| 断点 | `sm:640px`, `md:768px`, `lg:1024px` |

### Hero 文案

- 标题：`万能视频下载，` + `<span class="text-primary">一键保存</span>`
- 副标题：`支持 YouTube / B站 / TikTok 等 1000+ 平台，粘贴链接即可下载`

## 6. 目录结构

```
free_video_downloader/
├── docs/
│   ├── requirements.md      # 需求分析（本文档同级）
│   └── design.md            # 方案设计（本文档）
├── backend/
│   ├── main.py              # FastAPI 入口 + CORS + 路由
│   ├── config.py            # 环境变量配置
│   ├── models/
│   │   └── schemas.py       # Pydantic 请求/响应模型
│   ├── services/
│   │   ├── ytdlp_service.py # yt-dlp 封装
│   │   └── task_manager.py  # 任务队列 + 文件清理
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── package.json
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── api/client.js
│       ├── assets/
│       └── components/
│           ├── AppHeader.vue
│           ├── HeroSection.vue
│           ├── VideoResult.vue
│           ├── PlatformGrid.vue
│           ├── DownloadProgress.vue
│           └── AppFooter.vue
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── README.md
```

## 7. 扩展预留

### 7.1 AI 视频总结（第二期）

```
POST /api/summary
Body: { "task_id": "abc123" }  或  { "url": "..." }
Response: { "summary": "...", "chapters": [...] }
```

- 下载完成后提取音频 → Whisper 转文字 → LLM 总结
- 前端 VideoResult 组件预留「AI 总结」按钮位（disabled）

### 7.2 付费会员（第三期）

- 前端 AppHeader 已有 Pro 入口占位
- 后端 middleware 预留 `X-API-Key` 鉴权
- 功能 gating：批量下载、4K、AI 总结

## 8. 部署说明

```bash
# 开发模式
cd backend && pip install -r requirements.txt && uvicorn main:app --reload
cd frontend && npm install && npm run dev

# 生产模式
docker compose up -d
# 前端: http://localhost:3000
# 后端: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

## 9. 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DOWNLOAD_DIR` | `/tmp/downloads` | 临时下载目录 |
| `MAX_CONCURRENT` | `3` | 最大并发下载数 |
| `FILE_TTL_SECONDS` | `7200` | 文件保留时间（秒） |
| `MAX_FILE_SIZE_MB` | `2048` | 单文件大小上限 |
| `CORS_ORIGINS` | `*` | 允许的前端域名 |
