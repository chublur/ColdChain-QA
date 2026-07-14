# ColdChain-QA

冷链物流智能问答系统（RAG + QLoRA），面向医药冷链合规场景。

## 技术栈

- **后端**: FastAPI + SSE 流式输出
- **向量库**: PostgreSQL + pgvector
- **Embedding**: bge-small-zh-v1.5（CPU 推理）
- **LLM**: Qwen2.5-3B（Ollama 本地推理）
- **微调**: QLoRA 4bit（RTX 4060 8GB）
- **前端**: Vue3 可嵌入页面（后续开发）

## 快速开始

```bash
# 1. 环境
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 2. 配置
copy .env.example .env

# 3. 启动 PostgreSQL + Ollama
docker compose up -d

# 4. 拉取基座模型（3B 轻量化，适合 4060）
ollama pull qwen2.5:3b

# 5. 放入冷链 PDF 到 data/raw/，然后入库
python scripts/ingest_all.py

# 6. 启动 API
uvicorn src.api:app --reload --port 8000
```

## API 示例

```bash
# 非流式问答
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -H "x-api-key: change-me-in-production" \
  -d '{"question": "疫苗冷链运输温度范围？", "model": "base"}'

# SSE 流式（Vue3 EventSource 调用）
curl -N "http://localhost:8000/api/ask/stream?question=疫苗运输温度范围" \
  -H "x-api-key: change-me-in-production"
```

## LoRA 微调

```bash
pip install -r requirements-train.txt
python training/export_dataset.py --input data/sft/qa_pairs.json
python training/train_lora.py
python training/merge_lora.py
# 详见 docs/DEVELOPMENT_FLOW.md 阶段 4
```

多次微调指标对比见 **[docs/FINETUNE_RESULTS.md](docs/FINETUNE_RESULTS.md)**（Run1 epochs=3 vs Run2 epochs=2）。

## 项目结构

```
ColdChain-QA/
├── src/           # 核心业务（ingest / rag / llm / eval / api）
├── training/      # LoRA 训练
├── data/          # 原始文档 + SFT 数据 + 评估集
├── scripts/       # 入库 / 评估 CLI
├── sql/           # pgvector 初始化
├── docs/          # 开发流程文档
└── frontend/      # Vue3 嵌入页面（后续）
```

## 开发流程

完整流程图与分阶段指南见 **[docs/DEVELOPMENT_FLOW.md](docs/DEVELOPMENT_FLOW.md)**。
