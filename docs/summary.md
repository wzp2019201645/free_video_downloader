# 万能视频下载 — 项目总结

> 版本：v2.0 | 更新日期：2026-07-12 | 状态：下载 MVP + AI 总结/思维导图/问答 已交付

## 1. 项目概述

**free_video_downloader** 是一个基于 **yt-dlp + FastAPI + Vue 3 + DeepSeek** 的万能视频下载与 AI 分析 Web 应用。

用户粘贴视频链接，即可：

1. **解析并下载**视频（多平台、多清晰度）
2. **AI 视频总结**（摘要、要点、章节大纲）
3. **字幕/转录**查看与复制
4. **思维导图**自动生成
5. **AI 问答**基于视频内容多轮对话

核心定位：轻量、无数据库、临时文件模式，下载 + AI 分析同站完成，适合个人学习研究场景。

### 与竞品差异化

| 能力 | BibiGPT / NoteGPT | 本项目 |
|------|-------------------|--------|
| 视频下载 | 弱或无 | ✅ 核心能力 |
| AI 总结 | ✅ | ✅ |
| 思维导图 | ✅ | ✅ |
| AI 问答 | ✅ | ✅ |
| 同页完成下载+总结 | 通常分离 | ✅ |

---

## 2. 已完成功能

### 2.1 视频下载（第一期 MVP）

| 步骤 | 功能 | 实现说明 |
|------|------|----------|
| 1 | URL 解析 | `POST /api/info`，返回标题、封面、时长、上传者、可选格式 |
| 2 | 格式选择 | 最佳质量 / 1080p / 720p … / 仅音频 |
| 3 | 创建下载 | `POST /api/download`，返回 `task_id`，后台异步下载 |
| 4 | 进度轮询 | `GET /api/tasks/{task_id}`，实时 0–100% 进度 |
| 5 | 文件保存 | `GET /api/files/{task_id}`，支持浏览器下载与「另存为」 |

### 2.2 AI 视频总结（第二期）

| 步骤 | 功能 | 实现说明 |
|------|------|----------|
| 1 | 创建总结 | `POST /api/summary`，返回 `task_id` |
| 2 | 字幕获取 | B站 API → yt-dlp → Whisper ASR 三级兜底 |
| 3 | AI 分析 | DeepSeek 生成结构化 JSON（摘要/要点/章节/标签） |
| 4 | 进度轮询 | `GET /api/summary/tasks/{task_id}` |
| 5 | 结果展示 | 四页签：总结摘要 / 字幕文本 / 思维导图 / AI 问答 |
| 6 | 本地保存 | 复制 Markdown、另存为 `.md` 文件 |

**支持平台（总结）：** B站、抖音（含精选页 `modal_id` 链接）

**字幕来源策略：**

```
B站：官方字幕 API → yt-dlp 字幕 → Whisper 语音识别
抖音：DouyinParser 下载音频 → Whisper 语音识别
```

### 2.3 思维导图 & AI 问答（第二期扩展）

| 功能 | API | 说明 |
|------|-----|------|
| 思维导图 | `POST /api/summary/mindmap` | 基于已完成总结，DeepSeek 生成树形结构，服务端缓存 |
| AI 问答 | `POST /api/summary/chat` | 传入 `task_id` + 问题 + 历史，基于视频上下文回答 |

前端四页签组件：

- `SummaryOverviewTab` — 摘要、要点、章节、复制/保存
- `TranscriptTab` — 全文转录、复制
- `MindMapTab` — 自动生成思维导图树
- `ChatTab` — 多轮对话界面

### 2.4 平台适配

| 平台 | 下载 | AI 总结 | 关键技术 |
|------|------|---------|----------|
| **通用** | yt-dlp | yt-dlp 字幕 | Python API 直接调用 |
| **YouTube** | ✅ | — | 代理自动检测、URL 规范化 |
| **Bilibili** | ✅ | ✅ | curl_cffi Cookie 预热、Edge impersonate、WBI 字幕 |
| **抖音** | ✅ | ✅ | `douyin_parser.py` 独立解析器；精选页 `modal_id` 链接支持 |

### 2.5 前端体验

- **UI 风格**：浅灰背景 + 蓝色主色 `#1677FF`，参考 codefather painting
- **响应式**：移动端单列，桌面端卡片式
- **组件流**：`HeroSection` → `VideoResult`（下载）→ `SummaryPanelTabs`（AI 四页签）
- **保存优化**：Chrome/Edge `showSaveFilePicker` 原生对话框

---

## 3. 技术架构

```
浏览器 (Vue 3 + Tailwind + Vite)
    │  /api/* (开发时代理到 :8000)
    ▼
FastAPI 后端
    ├── main.py                    — 路由、CORS、生命周期
    ├── register_summary.py        — 注册 AI 总结路由（开闭原则）
    ├── register_summary_extended.py — 注册思维导图/问答路由
    ├── task_manager.py            — 下载任务队列、并发、清理
    ├── ytdlp_service.py           — yt-dlp 封装（下载核心，未改逻辑）
    ├── summary_manager.py         — AI 总结任务管理
    ├── summary_executor.py        — 独立线程池（避免阻塞解析）
    └── services/
        ├── subtitle_service.py    — 字幕编排（平台 API → yt-dlp → ASR）
        ├── deepseek_service.py    — DeepSeek 总结
        ├── mindmap_service.py     — DeepSeek 思维导图
        ├── summary_chat_service.py— DeepSeek 问答
        ├── douyin_parser.py       — 抖音独立解析（无 Cookie）
        └── bilibili_subtitle.py   — B站字幕 API
            │
            ▼
    yt-dlp / requests / faster-whisper / DeepSeek API
```

### 开闭原则（OCP）实践

| 层次 | 策略 |
|------|------|
| 下载核心 | `ytdlp_service.py`、`task_manager.py` 保持稳定 |
| AI 总结 | 新增 `register_summary.py` + 独立 services，main.py 一行注册 |
| 思维导图/问答 | 新增 `register_summary_extended.py`，不修改原有 summary 模块 |
| 前端 | 保留原 `SummaryPanel.vue`，新增 `SummaryPanelTabs.vue` 替换挂载 |

### API 端点一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/info` | 解析视频信息 |
| POST | `/api/download` | 创建下载任务 |
| GET | `/api/tasks/{task_id}` | 下载进度 |
| GET | `/api/files/{task_id}` | 下载完成文件 |
| GET | `/api/thumbnail?url=...` | 封面代理 |
| POST | `/api/summary` | 创建 AI 总结任务 |
| GET | `/api/summary/tasks/{task_id}` | 总结进度与结果 |
| POST | `/api/summary/mindmap` | 生成思维导图 |
| POST | `/api/summary/chat` | AI 问答 |

---

## 4. 项目结构

```
free_video_downloader/
├── docs/
│   ├── requirements.md          # 需求分析
│   ├── design.md                # 方案设计
│   └── summary.md               # 项目总结（本文档）
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── summary_config.py        # AI 总结独立配置（.env）
│   ├── register_summary.py
│   ├── register_summary_extended.py
│   ├── models/
│   │   ├── schemas.py
│   │   ├── summary_schemas.py
│   │   └── summary_extended_schemas.py
│   ├── routes/
│   │   ├── summary_router.py
│   │   └── summary_extended_router.py
│   ├── services/
│   │   ├── ytdlp_service.py         # 下载核心
│   │   ├── task_manager.py
│   │   ├── douyin_parser.py
│   │   ├── douyin_helper.py
│   │   ├── bilibili_helper.py
│   │   ├── bilibili_subtitle.py
│   │   ├── subtitle_service.py
│   │   ├── asr_service.py           # faster-whisper
│   │   ├── deepseek_service.py
│   │   ├── mindmap_service.py
│   │   ├── summary_chat_service.py
│   │   ├── summary_manager.py
│   │   ├── summary_executor.py
│   │   └── summary_ytdlp.py
│   ├── test_unit.py
│   ├── test_summary_unit.py
│   └── test_summary_extended_unit.py
├── frontend/
│   └── src/
│       ├── App.vue
│       ├── api/
│       │   ├── client.js
│       │   ├── summaryClient.js
│       │   └── summaryExtendedClient.js
│       └── components/
│           ├── VideoResult.vue
│           └── summary/
│               ├── SummaryPanel.vue       # 原版（保留）
│               ├── SummaryPanelTabs.vue   # 四页签版（当前使用）
│               ├── MindMapTree.vue
│               └── tabs/
│                   ├── SummaryOverviewTab.vue
│                   ├── TranscriptTab.vue
│                   ├── MindMapTab.vue
│                   └── ChatTab.vue
├── docker-compose.yml
└── README.md
```

---

## 5. 本地开发与运行

### 环境准备

```bash
# 后端依赖
cd backend
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install

# AI 总结必需：在 backend/.env 配置
# DEEPSEEK_API_KEY=sk-xxx
```

### 启动

```bash
# 后端
cd backend
py -m uvicorn main:app --reload --port 8000

# 前端
cd frontend
npm run dev
```

- 前端：http://localhost:3000
- API 文档：http://127.0.0.1:8000/docs

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | — | **AI 总结必需**，不可提交 Git |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek API 地址 |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 模型名称 |
| `WHISPER_MODEL_SIZE` | `tiny` | ASR 模型（tiny/base/small） |
| `HF_ENDPOINT` | `https://hf-mirror.com` | HuggingFace 镜像（国内） |
| `SUMMARY_MAX_CONCURRENT` | `2` | 最大并发总结任务 |
| `SUMMARY_MAX_DURATION_SECONDS` | `5400` | 总结视频时长上限（90 分钟） |
| `DOWNLOAD_DIR` | `./downloads` | 临时下载目录 |
| `MAX_CONCURRENT` | `3` | 最大并发下载 |
| `FILE_TTL_SECONDS` | `7200` | 文件保留 2 小时 |
| `YTDLP_PROXY` | — | 代理（YouTube 等） |
| `FFMPEG_PATH` | 自动发现 | ffmpeg 目录 |

---

## 6. 关键经验与踩坑记录

### 下载相关

1. **B站 412 反爬**：curl_cffi Cookie 预热 + Edge impersonate
2. **抖音短链/精选页**：yt-dlp 不支持 `jingxuan/knowledge?modal_id=`，需 `DouyinParser` 独立解析
3. **高清合并**：B站/YouTube 需 ffmpeg + ffprobe 同目录
4. **封面防盗链**：后端 `/api/thumbnail` 代理

### AI 总结相关

5. **进度卡 5%**：无字幕走 Whisper 耗时长，需分阶段 `progress` + `status_detail`
6. **解析被阻塞**：Whisper 占满默认线程池 → `summary_executor.py` 独立线程池
7. **Whisper 模型下载失败**：`HF_ENDPOINT` 镜像 + `HF_HUB_DISABLE_XET=1`
8. **yt-dlp 误把弹幕当字幕**：过滤 `danmaku` 等非文本轨道
9. **抖音总结 Unsupported URL**：总结流程改用 `DouyinParser`，不走 yt-dlp
10. **Windows ffmpeg 子进程**：`subprocess` 使用 `encoding=utf-8, errors=replace`

---

## 7. 测试覆盖

| 文件 | 范围 |
|------|------|
| `test_unit.py` | 下载核心单元测试 |
| `test_bilibili.py` | B站解析集成测试 |
| `test_summary_unit.py` | 总结模块单元测试 |
| `test_summary_extended_unit.py` | 思维导图/问答路由注册 |
| `test_parse_integration.py` | 总结进行中解析不阻塞 |

### 验收链接示例

- B站（无字幕，走 Whisper）：`https://www.bilibili.com/video/BV1h5QaY5EaH`
- 抖音精选页：`https://www.douyin.com/jingxuan/knowledge?modal_id=7636306372904209702`

---

## 8. 后续规划（未实现）

| 功能 | 说明 |
|------|------|
| 批量下载 | 多行 URL 队列 |
| 更多平台总结 | YouTube 等 |
| 思维导图导出 | PNG / Markdown |
| 问答流式输出 | SSE 打字机效果 |
| 付费会员 | Pro 功能 gating |
| 推送远程 | 网络恢复后 `git push origin master` |

---

## 9. 合规声明

本工具仅供个人学习研究使用，请尊重视频版权与平台服务条款。

- 不支持登录态/Cookie 导入（降低封号风险）
- 不记录用户 URL 历史
- `DEEPSEEK_API_KEY` 仅存于本地 `backend/.env`，不可提交版本库
