# 万能视频下载网站

基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp) + FastAPI + Vue 3 的万能视频下载工具，支持 YouTube、B站、TikTok 等 1000+ 平台。

## 功能

- 粘贴视频链接，一键解析
- 选择清晰度/格式
- 下载到本地（支持手机浏览器）
- 响应式 UI，参考 [codefather painting](https://ai.codefather.cn/painting) 设计风格

## 快速开始

### 方式一：本地开发

**后端**

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**前端**

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

### 方式二：Docker Compose

```bash
docker compose up -d --build
```

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 项目结构

```
├── docs/                  # 需求 & 设计 & 总结文档
│   ├── requirements.md
│   ├── design.md
│   └── summary.md         # 项目总结（MVP 交付沉淀）
├── backend/               # FastAPI + yt-dlp
├── frontend/              # Vue 3 + Tailwind CSS
└── docker-compose.yml
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DOWNLOAD_DIR` | `./downloads` | 临时下载目录 |
| `MAX_CONCURRENT` | `3` | 最大并发下载 |
| `FILE_TTL_SECONDS` | `7200` | 文件保留 2 小时 |
| `CORS_ORIGINS` | `*` | 跨域来源 |

## 注意事项

- 本工具仅供个人学习研究，请尊重视频版权
- 部分平台可能限制下载，属正常现象
- 临时文件 2 小时后自动清理
- **B站下载**：服务端需安装 ffmpeg 才能合并高清视频（音频可直接下载）；Docker 镜像已包含 ffmpeg
- 本地开发可执行：`pip install imageio-ffmpeg` 或 `winget install Gyan.FFmpeg`

## 后续规划

- [ ] 批量下载
- [ ] 字幕 / 音频提取
- [ ] AI 视频总结
- [ ] 付费会员

详见 [docs/requirements.md](docs/requirements.md) 和 [docs/design.md](docs/design.md)。
