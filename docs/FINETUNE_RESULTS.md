# ColdChain-QA LoRA 微调实验对比

> 记录多次 QLoRA 微调的超参、训练曲线与评估指标，便于回归对比与简历量化引用。  
> 评估协议：固定 15 题子集 `data/sft/test_cases_eval15.json`；`USE_LOCAL_LLM=1` 本地 transformers（base=原版 Qwen2.5-3B-Instruct，lora=合并权重）；RAG 检索同库样例文档。

---

## 1. 实验总览

| 轮次 | 日期 | Epochs | r / α | 训练损失 | adapter 目录 | 合并模型 | 评估报告 |
|------|------|--------|-------|----------|--------------|----------|----------|
| **Run1** | 2026-07-14 | 3 | 8 / 16 | 1.217 | `models/lora_adapter/`（归档 `cache/finetune_runs/run1_adapter/`） | `models/merged/` | `cache/finetune_runs/run1_epochs3_r8.json` |
| **Run2** | 2026-07-14 | 2 | 8 / 16 | 1.635 | `models/lora_adapter_run2/` | `models/merged_run2/` | `cache/finetune_runs/run2_epochs2_r8.json` |

共用配置：

- 基座：`Qwen2.5-3B-Instruct`（本地 `.cache/models/Qwen2.5-3B-Instruct`）
- 数据：`data/sft/train.jsonl`，**300** 条冷链 SFT（温度约 37% / 法规约 93% / 三段式 100%）
- 训练：QLoRA 4bit，`batch=1 × grad_accum=8`，`lr=2e-4`，`max_seq_len=1536`，RTX 4060 8GB
- Embedding：`bge-small-zh-v1.5`（CPU）

**Run2 动机**：Run1 出现「格式/法规好、语义准确率相对 base 下降」；将 epoch 从 3→2，减轻对模板化答案的过拟合。

---

## 2. 指标定义（与 `src/eval/metrics.py` 一致）

| 字段 | 含义 |
|------|------|
| `accuracy` | 语义相似度 ≥ 0.75 的题目比例 |
| `avg_semantic` | 回答与期望答案的平均语义相似度 |
| `avg_temp_accuracy` | 温度数值命中率（仅 `check_temp=true`） |
| `avg_regulation_cite` | 法规关键词引用率（GSP / GB / 规范等） |
| `avg_format` | 【结论】【依据】三段式格式合规率 |
| `avg_latency_ms` | 平均端到端耗时（含检索+生成） |
| `improvement` | 对正向指标：`lora − base`；延迟：`base − lora`（越大越快） |

---

## 3. Run1 详细结果（epochs=3）

### 3.1 训练

| 项 | 值 |
|----|-----|
| steps | 114 |
| train_runtime | ~664 s |
| final train_loss | **1.217** |
| 末段 mean_token_accuracy | ~0.86 |

### 3.2 base vs lora（15 题）

| 指标 | base | lora (Run1) | 提升 Δ |
|------|------|-------------|--------|
| 准确率 (semantic≥0.75) | 66.67% | 33.33% | **-33.34%** |
| 平均语义相似度 | 0.7492 | 0.7276 | -0.0216 |
| 平均温度准确率 | 0.6667 | 0.8333 | **+0.1666** |
| 平均法规引用率 | 0.9333 | 1.0000 | **+0.0667** |
| 平均格式合规率 | 1.0000 | 1.0000 | 0 |
| 平均延迟 (ms) | 86482 | 73779 | **+12703（更快）** |

### 3.3 Run1 结论

- **上升**：温度准确率、法规引用率、推理耗时。
- **下降**：语义准确率（阈值 0.75 下比例显著掉点）。
- **解读**：强约束三段式 + 高法规模板后，回答更「像 SOP」，但与短期望句的向量相似度波动变大。

---

## 4. Run2 详细结果（epochs=2）

### 4.1 训练

| 项 | 值 |
|----|-----|
| steps | 76 |
| train_runtime | ~484 s |
| final train_loss | **1.635** |
| 末段 mean_token_accuracy | ~0.81 |

### 4.2 base vs lora（15 题）

| 指标 | base | lora (Run2) | 提升 Δ |
|------|------|-------------|--------|
| 准确率 (semantic≥0.75) | 66.67% | 60.00% | **-6.67%** |
| 平均语义相似度 | 0.7492 | 0.7523 | **+0.0031** |
| 平均温度准确率 | 0.6667 | 0.6667 | 0 |
| 平均法规引用率 | 0.9333 | 1.0000 | **+0.0667** |
| 平均格式合规率 | 1.0000 | 0.9333 | -0.0667 |
| 平均延迟 (ms) | 45605 | 36438 | **+9167（更快）** |

### 4.3 Run2 结论

- 相对 Run1，**语义 accuracy 掉点大幅收窄**（-33% → -6.7%），平均语义相似度略高于 base。
- 法规引用仍稳在 100%；温度准确率与 base 持平（未再现 Run1 的 +16.7%）。
- 格式合规略降（0.93），符合「少训一轮、少背模板」的预期。

---

## 5. 跨轮次对比（相对 base 的提升 Δ）

| 指标 | Run1 Δ | Run2 Δ | 更优轮次 |
|------|--------|--------|----------|
| accuracy | -0.3334 | **-0.0667** | **Run2**（掉点更小） |
| avg_semantic | -0.0216 | **+0.0031** | **Run2** |
| avg_temp_accuracy | **+0.1666** | 0 | **Run1** |
| avg_regulation_cite | +0.0667 | +0.0667 | 持平 |
| avg_format | **0** | -0.0667 | **Run1** |
| avg_latency_ms（越大越快） | **+12703** | +9167 | **Run1**（本机负载不同，仅参考） |

### 选用建议

| 目标 | 推荐 |
|------|------|
| 温控数值更准、演示 SOP 格式 | **Run1**（`models/merged`） |
| 语义对齐更好、少过拟合模板 | **Run2**（`models/merged_run2`） |
| 法规引用 | 两轮均可（均为 +6.7pp 至 100%） |

---

## 6. 复现命令

```powershell
cd E:\Learning\ColdChain-QA
. .\scripts\use_e_cache.ps1

# ---- Run2 示例 ----
$env:LORA_EPOCHS=2
$env:LORA_BASE_MODEL="E:\Learning\ColdChain-QA\.cache\models\Qwen2.5-3B-Instruct"
$env:LORA_OUTPUT_DIR="E:\Learning\ColdChain-QA\models\lora_adapter_run2"
$env:ACCELERATE_MIXED_PRECISION="no"
$env:HF_HUB_OFFLINE=1
.venv\Scripts\python.exe training/train_lora.py

$env:MERGED_OUTPUT_DIR="E:\Learning\ColdChain-QA\models\merged_run2"
.venv\Scripts\python.exe training/merge_lora.py

$env:USE_LOCAL_LLM=1
$env:LORA_MERGED_DIR="E:\Learning\ColdChain-QA\models\merged_run2"
.venv\Scripts\python.exe scripts/evaluate.py --model compare `
  --test data/sft/test_cases_eval15.json `
  --output cache/finetune_runs/run2_epochs2_r8.json
```

完整训练 / 合并 / Ollama 导入流程见 [DEVELOPMENT_FLOW.md](./DEVELOPMENT_FLOW.md) 阶段 4–5。

---

## 7. 产物清单

```
cache/finetune_runs/
  run1_meta.json
  run1_epochs3_r8.json
  run1_adapter/
  run2_meta.json
  run2_epochs2_r8.json
models/
  lora_adapter/          # Run1
  lora_adapter_run2/     # Run2
  merged/                # Run1 合并
  merged_run2/           # Run2 合并
docs/
  FINETUNE_RESULTS.md    # 本文档
```

---

## 8. 后续实验建议

1. **数据**：增加短答/非模板回答与「文档未提及」样本，平衡格式过拟合。  
2. **超参**：试 `epochs=2, lr=1e-4` 或 `r=16` 作为 Run3。  
3. **评估**：升到全量 40 题 `test_cases.json`，并补 faithfulness。  
4. **部署**：合并模型转 GGUF 后 `ollama create -f Modelfile`。

---

*文档版本：v0.2 | 更新日期：2026-07-14*
