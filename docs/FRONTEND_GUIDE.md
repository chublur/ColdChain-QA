# 冷链物流智能问答系统 · 前端操作指南

> Vue3 + Vite · SSE 流式对话 · 知识库管理 · 数字人助手

---

## 一、环境要求

| 依赖 | 版本要求 |
|------|---------|
| Node.js | ≥ 18 |
| npm | ≥ 9 |
| 后端 API | FastAPI 运行于 `http://localhost:8000` |
| Docker | PostgreSQL + Ollama 已启动 |

---

## 二、快速启动

### 1. 启动后端服务

```powershell
# 项目根目录
docker compose up -d
.\.venv\Scripts\python.exe -m uvicorn src.api:app --reload --port 8000
```

确认健康检查：

```powershell
curl http://localhost:8000/health
```

### 2. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

浏览器访问：**http://localhost:5173**

> 开发模式下 Vite 已配置代理，`/api` 和 `/health` 自动转发到 `localhost:8000`，无需额外处理 CORS。

### 3. 配置 API Key（可选）

编辑 `frontend/.env.development`：

```env
VITE_API_BASE=
VITE_API_KEY=change-me-in-production
```

`VITE_API_BASE` 留空表示使用相对路径（走 Vite 代理）。生产部署时改为实际 API 地址。

---

## 三、页面功能说明

### 3.1 整体布局

```
┌─────────────────────────────────────────────────────────┐
│  顶部：系统名称 + 知识库状态（文档数 / 分块数）            │
├──────────┬──────────────────────────┬───────────────────┤
│ 左侧面板  │      中间：对话区          │  右侧面板          │
│ · 知识库  │  · 消息列表（流式渲染）    │ · 数字人助手       │
│ · 模型切换│  · 输入框 + 发送/停止     │ · 引用来源         │
└──────────┴──────────────────────────┴───────────────────┘
```

### 3.2 智能问答

1. 在底部输入框输入问题，按 **Enter** 发送（Shift+Enter 换行）
2. 系统自动执行 RAG 检索 → LLM 流式生成
3. 回答按 **【结论】【依据】【处置建议】** 三段式展示
4. 右侧实时显示检索到的法规 / SOP 引用来源
5. 数字人头像在生成时会播放「说话」动画

**快捷问题示例：**

- 疫苗冷链运输温度范围是多少？
- GSP 对冷藏药品储存有什么要求？
- 运输途中温度超标应如何处理？

### 3.3 模型切换

| 选项 | 说明 |
|------|------|
| **Base** | 原始 Qwen2.5-3B，需 `ollama pull qwen2.5:3b` |
| **LoRA** | 微调版 `coldchain-qwen2.5:3b`，需完成 LoRA 训练后部署 |

**检索范围** 可按文档类型过滤：法规标准 / SOP 流程 / 设备验证。

### 3.4 知识库管理

- **上传**：点击「+ 上传」，支持 `pdf / docx / txt / md`
- **去重**：同名文件自动覆盖更新
- **删除**：点击文档右侧 × 按钮
- 上传后顶部状态栏的分块数会刷新

也可通过命令行批量入库：

```powershell
.\.venv\Scripts\python.exe scripts\ingest_all.py
```

### 3.5 反馈评价

每条 AI 回答完成后，可点击 **👍 / 👎** 提交反馈，数据写入 `feedback` 表，用于 LoRA 训练闭环：

```powershell
.\.venv\Scripts\python.exe scripts\export_feedback.py --merge-existing
```

---

## 四、接口对接说明

### 4.1 SSE 流式问答

前端通过 `POST /api/ask/stream` 获取流式回答：

| 事件 | 数据 | 前端处理 |
|------|------|---------|
| `retrieval` | `{ sources: [...] }` | 渲染右侧引用来源面板 |
| `token` | `{ text: "片段" }` | 追加到回答区（打字机效果） |
| `done` | `{ latency_ms: 1234 }` | 显示耗时，结束加载状态 |
| `error` | `{ message: "..." }` | 展示错误信息 |

实现代码见 `frontend/src/composables/useSSE.ts`。

### 4.2 REST 接口一览

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/health` | 系统健康状态 |
| POST | `/api/ask` | 非流式问答 |
| POST | `/api/ask/stream` | SSE 流式问答 |
| GET | `/api/documents` | 文档列表 |
| DELETE | `/api/documents/{id}` | 删除文档 |
| POST | `/api/ingest` | 上传入库 |
| POST | `/api/feedback` | 提交反馈 |

所有 `/api/*` 接口需在 Header 中携带：

```
x-api-key: change-me-in-production
```

### 4.3 请求示例

```bash
# 流式问答
curl -N -X POST http://localhost:8000/api/ask/stream \
  -H "Content-Type: application/json" \
  -H "x-api-key: change-me-in-production" \
  -d '{"question": "疫苗冷链运输温度范围？", "model": "base"}'

# 上传文档
curl -X POST http://localhost:8000/api/ingest \
  -H "x-api-key: change-me-in-production" \
  -F "file=@data/raw/sample_gsp_regulation.txt"
```

---

## 五、生产构建

```powershell
cd frontend
npm run build
```

产物在 `frontend/dist/`，可部署到 Nginx / 静态服务器。

**Nginx 反向代理示例：**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_buffering off;  # SSE 必须关闭缓冲
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

生产环境需在 `.env.production` 中配置：

```env
VITE_API_BASE=https://your-api-domain.com
VITE_API_KEY=your-production-key
```

同时确保后端 `.env` 的 `CORS_ORIGINS` 包含前端域名。

---

## 六、常见问题

### Q: 页面显示「连接中…」不变？

检查后端是否启动：`curl http://localhost:8000/health`

### Q: 发送问题后长时间无响应？

1. 确认 Ollama 运行：`docker ps | findstr ollama`
2. 确认模型已拉取：`docker exec coldchain-ollama ollama list`
3. 首次提问会下载 Embedding 模型，需等待

### Q: 回答没有引用来源？

知识库为空，请上传文档或运行 `scripts/ingest_all.py`

### Q: LoRA 模型切换后报错？

LoRA 模型尚未训练部署，请先完成 `training/train_lora.py` 或切换回 Base

### Q: CORS 跨域错误？

开发模式使用 Vite 代理（`npm run dev`）不会有此问题。生产部署需配置 `CORS_ORIGINS`。

---

## 七、项目结构

```
frontend/
├── src/
│   ├── api/client.ts          # API 封装
│   ├── composables/useSSE.ts  # SSE 流式解析
│   ├── components/
│   │   ├── ChatWidget.vue     # 对话主组件
│   │   ├── MessageList.vue    # 消息列表
│   │   ├── SourcePanel.vue    # 引用来源
│   │   ├── ModelSwitch.vue    # 模型/检索切换
│   │   ├── DocManager.vue     # 知识库管理
│   │   └── AvatarPanel.vue    # 数字人助手
│   ├── styles/main.css        # 全局样式
│   ├── App.vue                # 页面布局
│   └── main.ts                # 入口
├── .env.development           # 开发环境变量
├── vite.config.ts             # Vite 配置（含 API 代理）
└── package.json
```

---

*文档版本：v1.0 | 更新日期：2026-07-13*
