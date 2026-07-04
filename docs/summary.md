# 万能视频下载 — 项目总结

> 版本：v1.0 | 完成日期：2026-07-04 | 状态：第一期 MVP 已交付

## 1. 项目概述

**free_video_downloader** 是一个基于 **yt-dlp + FastAPI + Vue 3** 的万能视频下载 Web 应用。用户粘贴视频链接，即可解析视频信息、选择清晰度/格式，并将文件保存到本地（支持桌面与手机浏览器）。

核心定位：轻量、无数据库、临时文件模式，适合个人学习研究场景。

## 2. 已完成功能

### 2.1 核心流程

| 步骤 | 功能 | 实现说明 |
|------|------|----------|
| 1 | URL 解析 | `POST /api/info`，返回标题、封面、时长、上传者、可选格式列表 |
| 2 | 格式选择 | 按分辨率生成选项（最佳质量 / 1080p / 720p … / 仅音频） |
| 3 | 创建下载 | `POST /api/download`，返回 `task_id`，后台异步下载 |
| 4 | 进度轮询 | `GET /api/tasks/{task_id}`，实时展示 0–100% 进度 |
| 5 | 文件保存 | `GET /api/files/{task_id}`，支持浏览器下载与「另存为」对话框 |

### 2.2 平台适配

| 平台 | 适配模块 | 关键技术点 |
|------|----------|------------|
| **通用** | `ytdlp_service.py` | yt-dlp Python API，非 subprocess 调用 |
| **YouTube** | `youtube_helper.py` | URL 规范化、代理自动检测、友好错误提示 |
| **Bilibili** | `bilibili_helper.py` | curl_cffi Cookie 预热、Edge impersonate、412 反爬修复 |
| **抖音** | `douyin_helper.py` + `douyin_parser.py` | 短链展开、Cookie 合并、独立解析器兜底 |
| **封面** | `thumbnail_proxy.py` | 后端代理缩略图，绕过防盗链与混合内容限制 |

### 2.3 前端体验

- **UI 风格**：参考 [codefather painting](https://ai.codefather.cn/painting)，浅灰背景 + 蓝色主色 `#1677FF`
- **响应式布局**：移动端单列堆叠，桌面端卡片式展示
- **组件化**：`HeroSection`（输入）→ `VideoResult`（结果 + 下载）→ `DownloadProgress`（进度条）
- **保存优化**：Chrome/Edge 优先使用 `showSaveFilePicker` 原生「另存为」对话框
- **平台展示**：`PlatformGrid` 静态卡片，展示支持的主流平台

### 2.4 运维与资源管理

- **并发控制**：最多 3 个同时下载（`MAX_CONCURRENT`）
- **文件清理**：下载完成后 2 小时自动删除临时文件（`FILE_TTL_SECONDS=7200`）
- **无数据库**：任务状态存于内存 `dict`，重启后任务丢失（符合临时下载场景）
- **ffmpeg 自动发现**：支持环境变量、PATH、项目 `tools/ffmpeg`、WinGet 安装路径
- **Docker 部署**：`docker compose up -d --build` 一键启动前后端

## 3. 技术架构

```
浏览器 (Vue 3 + Tailwind + Vite)
    │  /api/* (开发时代理到 :8000)
    ▼
FastAPI 后端
    ├── main.py          — 路由、CORS、生命周期
    ├── task_manager.py  — 任务队列、并发锁、定时清理
    └── ytdlp_service.py — yt-dlp 封装、格式构建
            │
            ▼
    yt-dlp (Python API) → 临时目录 ./downloads
```

### API 端点一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 + 活跃任务数 |
| POST | `/api/info` | 解析视频信息 |
| POST | `/api/download` | 创建下载任务 |
| GET | `/api/tasks/{task_id}` | 查询任务进度 |
| GET | `/api/files/{task_id}` | 下载完成文件 |
| GET | `/api/thumbnail?url=...` | 封面图代理 |

## 4. 项目结构

```
free_video_downloader/
├── docs/
│   ├── requirements.md   # 需求分析
│   ├── design.md         # 方案设计
│   └── summary.md        # 项目总结（本文档）
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── models/schemas.py
│   ├── services/
│   │   ├── ytdlp_service.py
│   │   ├── task_manager.py
│   │   ├── bilibili_helper.py
│   │   ├── youtube_helper.py
│   │   ├── douyin_helper.py
│   │   ├── douyin_parser.py
│   │   └── thumbnail_proxy.py
│   ├── test_unit.py
│   └── test_bilibili.py
├── frontend/
│   └── src/
│       ├── App.vue
│       ├── api/client.js
│       └── components/
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── README.md
```

## 5. 本地开发与运行

### 后端

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

### 环境变量（可选）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DOWNLOAD_DIR` | `./downloads` | 临时下载目录 |
| `MAX_CONCURRENT` | `3` | 最大并发下载 |
| `FILE_TTL_SECONDS` | `7200` | 文件保留时间（秒） |
| `YTDLP_PROXY` | — | 代理（YouTube 等受限网络需要） |
| `FFMPEG_PATH` | 自动发现 | ffmpeg 所在目录 |
| `CORS_ORIGINS` | `*` | 跨域来源 |

## 6. 关键经验与踩坑记录

1. **B站 412 反爬**：单纯 yt-dlp 默认请求会被拒，需 curl_cffi 预热 Cookie + Edge 浏览器指纹模拟。
2. **抖音短链**：分享链接需先展开为真实视频页，Cookie 文件合并后成功率更高。
3. **高清合并**：B站/YouTube 高清流为音视频分离，必须同时具备 `ffmpeg` 和 `ffprobe`。
4. **封面加载**：B站等站点缩略图有防盗链，前端通过后端 `/api/thumbnail` 代理解决。
5. **Windows 代理**：自动读取系统代理注册表 + 常见本地代理端口检测，减少 YouTube 访问配置成本。
6. **首次启动慢**：Python 模块（尤其 yt-dlp）加载耗时约 20–60 秒，属正常现象。

## 7. 测试覆盖

- `backend/test_unit.py`：单元测试（格式构建、任务管理等）
- `backend/test_bilibili.py`：B站解析集成测试

## 8. 后续规划（未实现）

| 功能 | 说明 |
|------|------|
| 批量下载 | 多行 URL 粘贴，队列处理 |
| 字幕 / 音频提取 | yt-dlp `--write-subs` / `-x` |
| AI 视频总结 | 预留 `/api/summary` 接口 |
| 付费会员 | Pro 入口已占位，功能 gating 待实现 |

## 9. 合规声明

本工具仅供个人学习研究使用，请尊重视频版权与平台服务条款。不支持登录态/Cookie 导入，不记录用户 URL 历史。
