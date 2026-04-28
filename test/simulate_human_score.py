# @File    : simulate_human_score.py
# @Describe: 用 GPT-5.1 模拟人类阅卷，为 dataset.json 填写 human_score / human_score_avg 字段
#            设计原则：只给题目 + 参考答案 + 学生回答，不给评分要点，模拟真实老师的主观判断

import os
import sys
import json
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'AI-Exam-Server', '.env'))

from openai import OpenAI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ── GPT-5.1 配置 ──────────────────────────────────────────────────────────────

GPT5_CONFIG = dict(
    api_key=os.getenv("MATRIX_API_KEY_V2"),
    base_url=os.getenv("MATRIX_BASE_URL"),
    model="gpt-5.1",
    reasoning_effort="high",
    max_completion_tokens=32678,
)

# ── 提示词 ────────────────────────────────────────────────────────────────────
# 设计原则：
#   1. 不给评分要点，让模型像真实老师一样综合判断
#   2. 强调语义理解，不因措辞/格式扣分
#   3. 要求给出评分理由，增加可信度
#   4. 输出结构化 JSON，便于解析

HUMAN_SCORE_PROMPT = """你是一位有丰富经验的大学教师，正在批改期末考试的简答题。

【题目】
{question}

【参考答案】
{standard_answer}

【满分】
{total_score} 分

【学生作答】
{student_answer}

---

请像真实老师批改试卷一样，给这道题打分。评分时请注意：

1. **关注语义，不拘泥于措辞**：学生用不同的词语表达了相同的意思，视为正确；不要因为和参考答案字面不同就扣分。
2. **允许合理简化**：学生的表述比参考答案简洁但核心正确，不扣分。
3. **部分正确给部分分**：答对了一部分内容，按比例给分，不要非黑即白。
4. **不因格式扣分**：答案顺序不同、没有分点列举，只要内容正确就不扣分。
5. **错误内容扣分**：明显的概念错误、逻辑错误、关键内容缺失，酌情扣分。
6. **空白或完全无关得 0 分**。

请输出以下 JSON 格式（只输出 JSON，不要输出其他内容）：
{{
  "score": 你给出的分数（数值，精确到0.5分，不超过满分 {total_score}），
  "reason": "简短的评分理由，说明哪些内容答对了、哪些扣分了"
}}"""

# ── 核心函数 ──────────────────────────────────────────────────────────────────

def create_client() -> OpenAI:
    return OpenAI(
        api_key=GPT5_CONFIG['api_key'],
        base_url=GPT5_CONFIG['base_url'],
    )


def parse_json_response(response_text: str) -> dict:
    text = response_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


def call_gpt5_with_retry(client: OpenAI, prompt: str, max_retries: int = 3) -> dict:
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=GPT5_CONFIG['model'],
                reasoning_effort=GPT5_CONFIG['reasoning_effort'],
                max_completion_tokens=GPT5_CONFIG['max_completion_tokens'],
                messages=[{"role": "user", "content": prompt}],
            )
            return parse_json_response(response.choices[0].message.content)
        except json.JSONDecodeError as error:
            logger.warning(f"JSON解析失败 (attempt {attempt + 1}/{max_retries}): {error}")
        except Exception as error:
            logger.warning(f"API调用失败 (attempt {attempt + 1}/{max_retries}): {error}")
        if attempt < max_retries - 1:
            time.sleep(3)
    raise RuntimeError(f"GPT-5.1 调用失败，已重试 {max_retries} 次")


def score_once(client: OpenAI, sample: dict) -> float:
    """调用一次 GPT-5.1 打分，返回分数"""
    prompt = HUMAN_SCORE_PROMPT.format(
        question=sample['question'],
        standard_answer=sample['standard_answer'],
        total_score=sample['total_score'],
        student_answer=sample['student_answer'][:3000],
    )
    result = call_gpt5_with_retry(client, prompt)
    raw_score = float(result['score'])
    clamped_score = round(min(raw_score, float(sample['total_score'])), 1)
    logger.debug(f"    单次得分={clamped_score}，理由：{result.get('reason', '')[:60]}")
    return clamped_score


def human_score_sample(sample: dict, num_rounds: int) -> dict:
    """
    对单条样本打 num_rounds 次分，取平均值作为最终人工评分。
    多轮打分模拟不同老师/不同时间的评分差异，平均后更稳定。

    Returns:
        {'scores': [float, ...], 'avg': float}
    """
    client = create_client()
    scores = []
    for round_index in range(num_rounds):
        score = score_once(client, sample)
        scores.append(score)
        if round_index < num_rounds - 1:
            time.sleep(1)  # 轮次间稍作间隔，避免完全相同的响应
    avg = round(sum(scores) / len(scores), 2)
    return {'scores': scores, 'avg': avg}


# ── 并发处理单条样本 ──────────────────────────────────────────────────────────

def process_single_sample(
    sample: dict,
    index: int,
    total: int,
    num_rounds: int,
    save_lock: threading.Lock,
    dataset: list,
    output_path: str,
    completed_counter: list,
) -> tuple:
    """
    Returns:
        ('success' | 'skip' | 'error', index)
    """
    if sample.get('human_score_avg') is not None:
        return ('skip', index)

    logger.info(
        f"[{index + 1}/{total}] 题目{sample['question_id']} "
        f"质量={sample['quality']} 答案：{sample['student_answer'][:25]}..."
    )

    try:
        result = human_score_sample(sample, num_rounds)

        # 写入各轮分数（兼容 analyze_results.py 的 fill_human_score_avg 逻辑）
        for round_index, round_score in enumerate(result['scores'], start=1):
            sample[f'human_score_{round_index}'] = round_score

        # 直接写入均值，analyze_results.py 优先使用此字段
        sample['human_score_avg'] = result['avg']

        logger.info(
            f"  [{index + 1}] 各轮={result['scores']}，均值={result['avg']}"
        )

        with save_lock:
            completed_counter[0] += 1
            if completed_counter[0] % 10 == 0:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(dataset, f, ensure_ascii=False, indent=2)
                logger.info(f"  进度已保存（已完成 {completed_counter[0]}/{total}）")

        return ('success', index)

    except Exception as error:
        logger.error(f"  [{index + 1}] 打分失败: {error}")
        return ('error', index)


# ── 主流程 ────────────────────────────────────────────────────────────────────

def run_human_scoring(
    dataset_path: str = None,
    output_path: str = None,
    num_rounds: int = 3,
    max_workers: int = 5,
    resume: bool = True,
):
    """
    用 GPT-5.1 模拟人类阅卷，为数据集填写 human_score_avg 字段。

    Args:
        dataset_path: 数据集路径，默认 test/dataset.json
        output_path:  输出路径，默认覆盖原文件
        num_rounds:   每条样本打几轮分（取均值），默认 3 轮
        max_workers:  并发线程数，默认 5
        resume:       跳过已有 human_score_avg 的样本
    """
    if dataset_path is None:
        dataset_path = os.path.join(os.path.dirname(__file__), 'dataset.json')
    if output_path is None:
        output_path = dataset_path

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"数据集不存在: {dataset_path}，请先运行 generate_dataset.py")

    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    pending_indices = []
    skip_count = 0
    for index, sample in enumerate(dataset):
        if resume and sample.get('human_score_avg') is not None:
            skip_count += 1
        else:
            pending_indices.append(index)

    total = len(dataset)
    logger.info(
        f"数据集共 {total} 条，待打分={len(pending_indices)}，"
        f"跳过={skip_count}，每条打 {num_rounds} 轮，并发={max_workers}"
    )

    if not pending_indices:
        logger.info("所有样本已有人工评分，无需处理。")
        return

    save_lock = threading.Lock()
    completed_counter = [0]
    success_count = 0
    error_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                process_single_sample,
                dataset[index], index, total, num_rounds,
                save_lock, dataset, output_path, completed_counter
            ): index
            for index in pending_indices
        }

        for future in as_completed(futures):
            status, sample_index = future.result()
            if status == 'success':
                success_count += 1
            elif status == 'error':
                error_count += 1

    # 最终保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    logger.info("=== 人工评分模拟完成 ===")
    logger.info(f"成功: {success_count}，跳过: {skip_count}，失败: {error_count}")
    logger.info(f"结果已保存至: {output_path}")
    logger.info("下一步：运行 run_evaluation.py 跑 AI 评分，再运行 analyze_results.py 分析")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='GPT-5.1 模拟人类阅卷打分')
    parser.add_argument('--dataset', type=str, default=None, help='数据集路径')
    parser.add_argument('--output', type=str, default=None, help='输出路径（默认覆盖原文件）')
    parser.add_argument('--rounds', type=int, default=3, help='每条样本打几轮分取均值，默认 3')
    parser.add_argument('--workers', type=int, default=3, help='并发线程数，默认 5')
    parser.add_argument('--no-resume', action='store_true', help='重新打分所有样本（忽略已有结果）')
    args = parser.parse_args()

    run_human_scoring(
        dataset_path=args.dataset,
        output_path=args.output,
        num_rounds=args.rounds,
        max_workers=args.workers,
        resume=not args.no_resume,
    )
