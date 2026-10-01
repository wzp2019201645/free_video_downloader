# 万能视频下载 — 项目总结

> 版本：v2.3 | 更新日期：2026-09-27 | 状态：下载 MVP + AI 总结 + 同屏双栏 + Pro 会员订阅 已交付

## 1. 项目概述

**free_video_downloader** 是一个基于 **yt-dlp + FastAPI + Vue 3 + DeepSeek** 的万能视频下载与 AI 分析 Web 应用。

用户粘贴视频链接，即可：

1. **解析并下载**视频（多平台、多清晰度）
2. **AI 视频总结**（摘要、要点、章节大纲）
3. **字幕/转录**查看、复制，以及下载 SRT / TXT（统一简体中文）
4. **思维导图** markmap 经典展示，支持导出 SVG / 高清 PNG
5. **AI 问答**基于视频内容多轮对话

核心定位：轻量、临时文件模式，下载 + AI 分析同站完成。720p 及以下和仅音频免费、无需登录；1080p 及以上、最佳质量，以及 AI 总结相关能力需要 Pro。会员账号存在本地 SQLite，视频文件仍只临时中转。适合个人学习研究场景。

### 与竞品差异化

| 能力 | BibiGPT / NoteGPT | 本项目 |
|------|-------------------|--------|
| 视频下载 | 弱或无 | ✅ 核心能力 |
| AI 总结 | ✅ | ✅ |
| 思维导图 | ✅ | ✅ markmap + SVG/PNG 导出 |
| 字幕下载 | 常见 SRT | ✅ SRT / TXT（简体） |
| AI 问答 | ✅ | ✅ |
| 同页完成下载+总结 | 通常分离 | ✅ 桌面双栏同屏（左下载 / 右总结） |
| 会员与支付 | 常见积分/订阅 | ✅ 邮箱账号 + Stripe 月付 Pro |

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
| 3 | 简体规范化 | OpenCC `t2s` 统一繁→简；Whisper 默认 `base` + 简体 `initial_prompt` |
| 4 | AI 分析 | DeepSeek 生成结构化 JSON（摘要/要点/章节/标签） |
| 5 | 进度轮询 | `GET /api/summary/tasks/{task_id}` |
| 6 | 结果展示 | 四页签：总结摘要 / 字幕文本 / 思维导图 / AI 问答 |
| 7 | 本地保存 | 复制 Markdown、另存为 `.md`；字幕页导出 SRT / TXT |

**支持平台（总结）：** B站、抖音（含精选页 `modal_id` 链接）

**字幕来源策略：**

```
B站：官方字幕 API → yt-dlp 字幕 → Whisper 语音识别
抖音：DouyinParser 下载音频 → Whisper 语音识别
（入库前统一 OpenCC 繁体 → 简体）
```

### 2.3 思维导图 & AI 问答（第二期扩展）

| 功能 | API / 实现 | 说明 |
|------|------------|------|
| 思维导图 | `POST /api/summary/mindmap` | DeepSeek 生成树形 JSON，服务端缓存 |
| 导图展示 | 前端 markmap | 经典中心分支连线，支持缩放/平移 |
| 导图导出 | 前端 `mindmapExport.js` | 下载 SVG；Canvas 3x 高清 PNG（纯 SVG 路径，兼容 foreignObject） |
| AI 问答 | `POST /api/summary/chat` | 传入 `task_id` + 问题 + 历史，基于视频上下文回答 |

前端四页签组件：

- `SummaryOverviewTab` — 摘要、要点、章节、复制/保存
- `TranscriptTab` — 全文转录、复制、下载 SRT / TXT
- `MindMapTab` — markmap 渲染 + SVG/PNG 导出
- `ChatTab` — 多轮对话界面

### 2.4 平台适配

| 平台 | 下载 | AI 总结 | 关键技术 |
|------|------|---------|----------|
| **通用** | yt-dlp | yt-dlp 字幕 | Python API 直接调用 |
| **YouTube** | ✅ | — | 代理自动检测、URL 规范化 |
| **Bilibili** | ✅ | ✅ | curl_cffi Cookie 预热、Edge impersonate、WBI 字幕 |
| **抖音** | ✅ | ✅ | `douyin_parser.py` 独立解析器；精选页 `modal_id` 链接支持 |

### 2.5 会员与支付（第三期）

免费与 Pro 的分界：

| 能力 | 未登录 / 非会员 | Pro |
|------|-----------------|-----|
| 720p 及以下、仅音频 | 可下载 | 可下载 |
| 1080p 及以上、「最佳质量」 | 锁定 | 可下载 |
| AI 摘要、字幕、思维导图、问答 | 锁定 | 可用 |
| 批量下载 | 未实现 | 未实现 |

产品约定：

- 月付订阅，可取消；`active` 且 `cancel_at_period_end` 时用到当前周期结束
- 测试价格为每月 ¥19 CNY（Stripe `unit_amount=1900`、`currency=cny`、`interval=month`）。价格与币种只认服务端环境变量里的 Price，不接受前端传入金额
- 身份是邮箱 + 密码，会员绑在账号上

支付路径：

1. 前端跳转 Stripe Hosted Checkout（`mode=subscription`），卡号不经过本站
2. 成功回跳后，后端用 Checkout Session 再向 Stripe 核对一次，才写入会员
3. 取消、续费、扣款失败靠 Webhook。本机没有公网 IP 时，用 Stripe CLI `stripe listen --forward-to localhost:8000/api/billing/webhook`

权限判定（前后端同一套规则，`services/entitlements.py` 与 `frontend/src/utils/membership.js` 必须一起改）：

- 格式：`bestaudio/best` 免费；`bestvideo[height<=N]+bestaudio/best` 仅在 `N<=720` 时免费；「最佳质量」`bestvideo+bestaudio/best` 以及任何无法识别的 format id 都要 Pro
- 会员：状态为 `active` 或 `trialing`，且 `price_id` 等于当前 `STRIPE_PRICE_ID`。`past_due`、`unpaid`、`canceled` 不算会员

已在页面验证：Pro 账号选择「最佳质量 · .mp4」后按钮为「下载到本地」，`POST /api/download` 返回 200，文件可保存。非会员同一项仍显示「会员专享」。

### 2.6 前端体验

- **UI 风格**：浅灰背景 + 蓝色主色 `#1677FF`，参考 codefather painting
- **响应式**：移动端单列堆叠；桌面端解析后为双栏同屏（左约 40% 视频信息/紧凑下载，右约 60% AI 总结四页签）
- **组件流**：`HeroSection` → 同屏工作区（`VideoResult` + `SummaryPanelTabs`）；总结仍为手动「开始 AI 总结」
- **账号**：顶栏登录 / 邮箱；Pro 为实心按钮，非会员为「开通 Pro」。登录、开通会员各一个对话框
- **保存优化**：Chrome/Edge `showSaveFilePicker` 原生对话框

实现要点：密码用 scrypt，接口不回传密码。会话是 HttpOnly、SameSite=Lax 的 Cookie `fvd_session`（HMAC，14 天）。创建下载前检查格式；创建总结、思维导图和问答前要求有效会员。查询已有总结任务不再单独拦截。同一用户同时只有一笔未完成的 Checkout；已经是会员不能再订一笔；欠费去客户门户，而不是再开一笔订阅。测试模式密钥与正式事件不能混用。

---

## 3. 技术架构

```
浏览器 (Vue 3 + Tailwind + Vite)
    │  /api/* (开发时代理到 :8000)
    ▼
FastAPI 后端
    ├── main.py                    — 路由、CORS、生命周期、下载门禁
    ├── register_summary.py        — 注册 AI 总结路由（开闭原则）
    ├── register_summary_extended.py — 注册思维导图/问答路由
    ├── register_billing.py        — 注册登录与 Stripe 路由
    ├── billing_config.py          — 会员与 Stripe 配置（backend/.env）
    ├── task_manager.py            — 下载任务队列、并发、清理
    ├── ytdlp_service.py           — yt-dlp 封装（下载核心，未改逻辑）
    ├── summary_manager.py         — AI 总结任务管理
    ├── summary_executor.py        — 独立线程池（避免阻塞解析）
    └── services/
        ├── subtitle_service.py    — 字幕编排（平台 API → yt-dlp → ASR）
        ├── text_normalize.py      — OpenCC 繁→简
        ├── asr_service.py         — faster-whisper（默认 base）
        ├── deepseek_service.py    — DeepSeek 总结
        ├── mindmap_service.py     — DeepSeek 思维导图
        ├── summary_chat_service.py— DeepSeek 问答
        ├── douyin_parser.py       — 抖音独立解析（无 Cookie）
        ├── bilibili_subtitle.py   — B站字幕 API
        ├── membership_db.py       — SQLite：用户、会员、事件去重、未完成 Checkout
        ├── billing_service.py     — Stripe Checkout / Portal / Webhook
        ├── entitlements.py        — 清晰度与会员判定
        ├── access.py              — Cookie 会话，下载与 AI 入口校验
        ├── passwords.py           — scrypt
        └── session_token.py       — HMAC 会话令牌
            │
            ▼
    yt-dlp / requests / faster-whisper / OpenCC / DeepSeek API / Stripe
```

### 开闭原则（OCP）实践

| 层次 | 策略 |
|------|------|
| 下载核心 | `ytdlp_service.py`、`task_manager.py` 保持稳定 |
| AI 总结 | 新增 `register_summary.py` + 独立 services，main.py 一行注册 |
| 思维导图/问答 | 新增 `register_summary_extended.py`，不修改原有 summary 模块 |
| 会员 | 新增 `register_billing.py`。下载任务仍在内存；只在创建下载和创建总结前做权限校验 |
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
| POST | `/api/summary/chat` | AI 问答（需 Pro） |
| POST | `/api/auth/register` | 注册并登录 |
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/logout` | 退出 |
| GET | `/api/auth/me` | 当前用户；未登录返回 `{user:null}` |
| GET | `/api/billing/plan` | 是否已配置、价格展示 |
| POST | `/api/billing/checkout` | 创建或复用 Checkout |
| POST | `/api/billing/portal` | Stripe 客户门户（取消、改卡） |
| POST | `/api/billing/confirm` | 回跳后向 Stripe 核对会话 |
| POST | `/api/billing/webhook` | Stripe 事件（原始 body + 签名） |

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
│   ├── billing_config.py        # Stripe / 会话配置（.env）
│   ├── .env.example             # 密钥占位，可提交
│   ├── register_summary.py
│   ├── register_summary_extended.py
│   ├── register_billing.py
│   ├── models/
│   │   ├── schemas.py
│   │   ├── summary_schemas.py
│   │   ├── summary_extended_schemas.py
│   │   └── billing_schemas.py
│   ├── routes/
│   │   ├── summary_router.py
│   │   ├── summary_extended_router.py
│   │   ├── auth_router.py
│   │   └── billing_router.py
│   ├── services/
│   │   ├── ytdlp_service.py         # 下载核心
│   │   ├── task_manager.py
│   │   ├── douyin_parser.py
│   │   ├── douyin_helper.py
│   │   ├── bilibili_helper.py
│   │   ├── bilibili_subtitle.py
│   │   ├── subtitle_service.py
│   │   ├── asr_service.py           # faster-whisper（默认 base）
│   │   ├── text_normalize.py        # OpenCC 繁→简
│   │   ├── deepseek_service.py
│   │   ├── mindmap_service.py
│   │   ├── summary_chat_service.py
│   │   ├── summary_manager.py
│   │   ├── summary_executor.py
│   │   ├── summary_ytdlp.py
│   │   ├── membership_db.py
│   │   ├── billing_service.py
│   │   ├── entitlements.py
│   │   ├── access.py
│   │   ├── passwords.py
│   │   └── session_token.py
│   ├── test_unit.py
│   ├── test_summary_unit.py
│   ├── test_text_normalize_integration.py
│   ├── test_summary_extended_unit.py
│   └── test_membership_unit.py
├── frontend/
│   └── src/
│       ├── App.vue
│       ├── api/
│       │   ├── client.js
│       │   ├── summaryClient.js
│       │   ├── summaryExtendedClient.js
│       │   └── authClient.js
│       ├── auth/
│       │   └── store.js             # 登录态、会员弹窗、支付回跳
│       ├── utils/
│       │   ├── downloadBlob.js      # 通用文件下载
│       │   ├── subtitleExport.js    # SRT / TXT 生成
│       │   ├── mindmapMarkdown.js   # 树 → markmap Markdown
│       │   ├── mindmapExport.js     # SVG/PNG 可靠导出
│       │   └── membership.js        # 与后端 entitlements 对齐
│       └── components/
│           ├── VideoResult.vue            # 同屏左栏；Pro 才放开高清
│           ├── AuthDialog.vue
│           ├── MembershipDialog.vue
│           ├── AppHeader.vue
│           └── summary/
│               ├── SummaryPanel.vue       # 原版（保留）
│               ├── SummaryPanelTabs.vue   # 同屏右栏四页签（手动总结）
│               └── tabs/
│                   ├── SummaryOverviewTab.vue
│                   ├── TranscriptTab.vue
│                   ├── MindMapTab.vue     # markmap + 导出
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

# 在 backend/.env 配置（从 .env.example 复制）
# DEEPSEEK_API_KEY=sk-xxx
# STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET / STRIPE_PRICE_ID
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
| `WHISPER_MODEL_SIZE` | `base` | ASR 模型（tiny/base/small）；base 更准、首次下载更大 |
| `HF_ENDPOINT` | `https://hf-mirror.com` | HuggingFace 镜像（国内） |
| `SUMMARY_MAX_CONCURRENT` | `2` | 最大并发总结任务 |
| `SUMMARY_MAX_DURATION_SECONDS` | `5400` | 总结视频时长上限（90 分钟） |
| `DOWNLOAD_DIR` | `./downloads` | 临时下载目录 |
| `MAX_CONCURRENT` | `3` | 最大并发下载 |
| `FILE_TTL_SECONDS` | `7200` | 文件保留 2 小时 |
| `YTDLP_PROXY` | — | 代理（YouTube 等） |
| `FFMPEG_PATH` | 自动发现 | ffmpeg 目录 |
| `STRIPE_SECRET_KEY` | — | 测试密钥 `sk_test_`，不可提交 Git |
| `STRIPE_WEBHOOK_SECRET` | — | `stripe listen` 打印的 `whsec_` |
| `STRIPE_PRICE_ID` | — | 每月 ¥19 CNY 的 `price_`；币种或金额不符会拒绝 |
| `PUBLIC_APP_URL` | `http://localhost:3000` | 支付完成回跳地址，不要用 `127.0.0.1` |
| `SESSION_SECRET` | 自动生成 | 不填则写入 `backend/data/session_secret` |
| `STRIPE_PROXY` | — | 打不开 Stripe 时再填，不复用 yt-dlp 的 Windows 代理 |
| `MEMBERSHIP_DATA_DIR` | `backend/data` | SQLite `membership.db` 所在目录 |

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
11. **字幕繁体不便阅读**：入库前 OpenCC `t2s`；Whisper 加简体 `initial_prompt`
12. **思维导图导出无反应**：markmap 使用 `foreignObject`，`html-to-image` 易静默失败 → 导出前转为纯 SVG `<text>`，PNG 走 Canvas 3x；优先 `showSaveFilePicker` 保留用户手势

### 会员与支付

13. **没有公网也能测支付**：Stripe CLI `stripe listen` 把 Webhook 转到本机，不需要把机器暴露到公网。CLI 窗口要保持打开，`whsec_` 写入 `.env` 后重启后端
14. **不要信任回跳 URL**：`?billing=success` 只是提示。真正开通要靠服务端 `checkout.sessions.retrieve`，以及 Webhook 处理取消和续费
15. **防止重复扣款**：同一用户同时只保留一个未完成 Checkout；Stripe 事件 id 在同一个 SQLite 事务里记账，失败回滚后允许 Stripe 重试；会员写入是按订阅状态覆盖，不是在本地天数上累加
16. **Price 必须是每月 ¥19 CNY**：代码核对 `currency`、`unit_amount`、`interval`。账号不支持人民币时不要偷偷改成美元
17. **Pro 仍被「最佳质量」挡住**：锁定条件必须同时满足「格式需要会员」和「当前用户不是会员」。只判断格式时，已开通的账号点下载会再次打开开通弹窗
18. **新版 Stripe 的周期结束时间**：`current_period_end` 可能在订阅上，也可能在 subscription item 上，两边都要读
19. **密钥**：`sk_`、`whsec_`、`backend/.env`、`backend/data/` 不入库。页面和日志不打印密钥

---

## 7. 测试覆盖

| 文件 | 范围 |
|------|------|
| `test_unit.py` | 下载核心单元测试 |
| `test_bilibili.py` | B站解析集成测试 |
| `test_summary_unit.py` | 总结模块单元测试（含简繁转换、Whisper 默认模型） |
| `test_text_normalize_integration.py` | 字幕 fetch 路径繁→简 |
| `test_summary_extended_unit.py` | 思维导图/问答路由注册 |
| `test_membership_unit.py` | 清晰度门槛、密码、会话、Webhook 去重、Checkout 幂等（不连真 Stripe） |
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
| 思维导图导出 Markdown | PNG/SVG 已交付，可再补 `.md` |
| 问答流式输出 | SSE 打字机效果 |
| 字幕跨语种翻译 | 当前仅繁→简 |
| 更多支付方式 | 当前仅 Stripe 月付。大陆商户若无法注册 Stripe，需要另选渠道 |

---

## 9. 合规声明

本工具仅供个人学习研究使用，请尊重视频版权与平台服务条款。

- 不支持导入视频网站的登录 Cookie（降低封号风险）
- 不记录用户粘贴过的视频链接。Pro 登录态是本站自己的 HttpOnly Cookie
- `DEEPSEEK_API_KEY`、`STRIPE_SECRET_KEY`、`STRIPE_WEBHOOK_SECRET` 只放在本地 `backend/.env`，不可提交版本库
