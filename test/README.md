# AI 评分实验脚本使用说明

## 目录结构

```
test/
├── generate_dataset.py   # Step 1：生成题目、要点、学生回答
├── run_evaluation.py     # Step 3：AI 评分（宽松 + 严格模式）
├── baseline_keyword.py   # Step 3：关键词匹配基线评分
├── analyze_results.py    # Step 4：统计分析 + 输出图表
├── dataset.json          # 数据集（运行后自动生成）
├── analysis_results.json # 分析结果（运行后自动生成）
├── scatter_comparison.png
└── metrics_comparison.png
```

---

## 依赖安装

```bash
pip install langchain langchain-openai python-dotenv jieba
# 可选，用于生成图表
pip install matplotlib
```

---

## 使用流程

### Step 1：生成数据集

```bash
cd test
python generate_dataset.py
```

运行完成后生成 `dataset.json`，包含：
- 30 道简答题，每题含标准答案和评分要点
- 每题 3 条不同质量梯度的学生回答（HIGH / MEDIUM / LOW）
- 共 90 条样本

### Step 2：人工评分（必须手动完成）

打开 `dataset.json`，为每条样本填写以下字段：

```json
"human_score_1": 8,
"human_score_2": 7,
"human_score_3": 8
```

- 找 2~3 位同学，每人独立对学生回答按 0~10 分打分
- 可以将 dataset.json 导出为 Excel 分发，回收后手动填回
- `human_score_avg` 字段**无需手动填写**，analyze_results.py 会自动计算均值

### Step 3：运行 AI 评分 + 基线评分

```bash
# AI 评分（宽松 + 严格模式，支持断点续跑）
python run_evaluation.py

# 只跑宽松模式
python run_evaluation.py --mode lenient

# 只跑严格模式
python run_evaluation.py --mode strict

# 关键词匹配基线（本地运行，无需调用 API）
python baseline_keyword.py
```

两个脚本均支持**断点续跑**，中途中断后重新运行会自动跳过已评分的样本。

### Step 4：统计分析

```bash
python analyze_results.py
```

输出内容：
- 终端打印对比表格（皮尔逊 r、MAE、RMSE、一致率）
- 保存 `analysis_results.json`
- 保存 `scatter_comparison.png`（散点图）
- 保存 `metrics_comparison.png`（柱状图）

---

## 实验设计说明

| 对比组 | 说明 |
|---|---|
| 宽松模式（Lenient） | 单次 LLM 评分，基于要点命中 |
| 严格模式（Strict） | 三次 LLM 投票，多数票决定 |
| 关键词基线（Keyword） | jieba 分词 + 关键词命中率，传统方法 |

**评估指标：**
- **皮尔逊相关系数 r**：越接近 1 表示与人工评分越一致
- **MAE（平均绝对误差）**：越小越好，单位为分
- **RMSE（均方根误差）**：对大误差更敏感
- **一致率（±1分）**：AI 与人工评分差距在 1 分以内的比例

---

## 注意事项
严格模式每条样本调用 3 次 API，90 条共 270 次，注意 API 费用和限流
关键词基线无需 API，可以先跑完再等人工评分
分析脚本只统计**三种评分和人工评分均已完成**的样本
