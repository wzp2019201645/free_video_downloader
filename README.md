# 万能视频下载网站

基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp) + FastAPI + Vue 3 + DeepSeek 的万能视频下载与 AI 分析工具。

## 功能

- 粘贴视频链接，一键解析与下载（YouTube、B站、抖音等）
- 选择清晰度/格式，下载到本地
- **AI 视频总结**：摘要、要点、章节大纲
- **四页签结果**：总结摘要 · 字幕文本 · 思维导图 · AI 问答
- **思维导图**：markmap 经典导图展示，支持下载 SVG / 高清 PNG
- **字幕**：统一简体中文；支持下载 SRT / TXT
- 总结结果支持复制 Markdown / 另存为 `.md`
- 响应式 UI，移动端友好

## 快速开始

### 本地开发

**后端**

```bash
cd backend
pip install -r requirements.txt
# 配置 backend/.env：DEEPSEEK_API_KEY=sk-xxx
py -m uvicorn main:app --reload --port 8000
```

**前端**

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

### Docker Compose

```bash
docker compose up -d --build
```

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000/docs

## 项目结构

```
├── docs/                  # 需求、设计、总结文档
│   └── summary.md         # 完整项目总结（推荐阅读）
├── backend/               # FastAPI + yt-dlp + AI 总结
├── frontend/              # Vue 3 + Tailwind CSS
└── docker-compose.yml
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | AI 总结/思维导图/问答必需（`backend/.env`） |
| `WHISPER_MODEL_SIZE` | ASR 模型，默认 `base`（可改为 `tiny`/`small`） |
| `DOWNLOAD_DIR` | 临时下载目录（默认 `./downloads`） |
| `MAX_CONCURRENT` | 最大并发下载（默认 3） |
| `YTDLP_PROXY` | 代理（YouTube 等受限网络） |

完整配置见 [docs/summary.md](docs/summary.md)。

## 注意事项

- 本工具仅供个人学习研究，请尊重视频版权
- B站高清下载需 ffmpeg；Docker 镜像已包含
- 无字幕视频首次总结会下载 Whisper `base` 模型，可能较慢
- 临时文件 2 小时后自动清理

## 文档

- [项目总结](docs/summary.md) — 架构、功能、踩坑、测试
- [需求分析](docs/requirements.md)
- [方案设计](docs/design.md)
