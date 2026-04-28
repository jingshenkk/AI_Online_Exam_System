# @File    : run_evaluation.py
# @Describe: 批量评测脚本：对数据集中的90条样本分别跑宽松模式、严格模式、无要点引导评分，结果写回 dataset.json

import os
import sys
import json
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'AI-Exam-Server'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'AI-Exam-Server', '.env'))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ── 提示词（与 llm_service.py 保持一致）────────────────────────────────────

# 无要点引导：直接让模型自由评分，不提供任何评分细则
FREE_SCORE_PROMPT = """
你是阅卷老师，请根据题目和学生答案，给出一个0到{total_score}分的评分，以JSON输出。

题目：{question}
满分：{total_score}分
学生答案：{answer}

评分标准：
- 根据答案的完整性、准确性、逻辑性综合评分
- 完全正确且完整得满分，完全错误或空白得0分
- 部分正确按比例给分

输出格式：
{{
  "score": 得分数值,
  "reason": "评分理由（简短说明）"
}}

只输出JSON，不要输出其他内容。
"""

LLM_SCORE_PROMPT = """
你是阅卷老师，根据评分细则对学生答案逐点打分，以JSON输出。

题目：{question}
评分细则：{points}
学生答案：{answer}

输出格式：
{{
  "point_scores": [
    {{
      "point_id": 得分点ID（整数）,
      "hit": "FULL或MISS",
      "earned": 得分数值,
      "reason": "判定理由"
    }}
  ],
  "total": 总分数值
}}

评分规则：
- 同义表达、合理改写视为正确（FULL，得该点满分）
- 关键概念缺失或逻辑错误（MISS，0分）
- 不要因格式或字面措辞扣分，关注语义是否正确
- hit 只能是 FULL 或 MISS 两种值
- 只输出JSON，不要输出其他内容
"""

# ── 工具函数 ─────────────────────────────────────────────────────────────────

def create_llm_client():
    return ChatOpenAI(
        api_key=os.getenv("MODEL_API_KEY"),
        base_url=os.getenv("MODEL_BASE_URL"),
        model="DeepSeek-V3.2",
        temperature=0.1,
        max_tokens=64000,
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


def call_llm_with_retry(llm, prompt: str, max_retries: int = 3) -> dict:
    for attempt in range(max_retries):
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            return parse_json_response(response.content)
        except json.JSONDecodeError as error:
            logger.warning(f"JSON解析失败 (attempt {attempt + 1}/{max_retries}): {error}")
        except Exception as error:
            logger.warning(f"LLM调用失败 (attempt {attempt + 1}/{max_retries}): {error}")
        if attempt < max_retries - 1:
            time.sleep(2)
    raise RuntimeError(f"LLM调用失败，已重试 {max_retries} 次")


def build_points_desc(points: list) -> str:
    """将要点列表序列化为 prompt 中的描述字符串"""
    return json.dumps(
        [
            {
                "id": p['id'],
                "description": p['description'],
                "score": p['score'],
                "acceptable": p.get('acceptable_expressions', [])
            }
            for p in points
        ],
        ensure_ascii=False
    )

# ── 评分逻辑 ─────────────────────────────────────────────────────────────────

def score_once(llm, question_text: str, points: list, student_answer: str) -> dict:
    """调用一次 LLM 评分，返回原始结果"""
    prompt = LLM_SCORE_PROMPT.format(
        question=question_text,
        points=build_points_desc(points),
        answer=student_answer[:2000]
    )
    return call_llm_with_retry(llm, prompt)


def free_score(llm, sample: dict) -> float:
    """无要点引导模式：直接把题目+答案扔给模型，不提供评分细则"""
    prompt = FREE_SCORE_PROMPT.format(
        question=sample['question'],
        total_score=sample['total_score'],
        answer=sample['student_answer'][:2000]
    )
    result = call_llm_with_retry(llm, prompt)
    raw_score = float(result['score'])
    # 防止模型返回超出满分的值
    return round(min(raw_score, float(sample['total_score'])), 1)


def lenient_score(llm, sample: dict) -> float:
    """宽松模式：单次 LLM 评分"""
    result = score_once(llm, sample['question'], sample['points'], sample['student_answer'])
    return round(float(result['total']), 1)


def strict_score(llm, sample: dict) -> float:
    """严格模式：三次 LLM 投票，逐点取多数票"""
    points = sample['points']
    results = []
    for round_index in range(3):
        result = score_once(llm, sample['question'], points, sample['student_answer'])
        results.append(result)
        time.sleep(0.3)

    total_score = 0.0
    for point in points:
        point_id = point['id']
        votes = []
        for result in results:
            matched = next(
                (ps for ps in result['point_scores'] if str(ps['point_id']) == str(point_id)),
                None
            )
            if matched:
                votes.append(matched['hit'])

        # 多数票决定（FULL >= 2 则得分，否则 0）
        full_count = votes.count('FULL')
        if full_count >= 2:
            total_score += float(point['score'])

    return round(total_score, 1)

# ── 并发评分单条样本 ──────────────────────────────────────────────────────────

def evaluate_single_sample(
    sample: dict,
    index: int,
    total: int,
    mode: str,
    save_lock: threading.Lock,
    dataset: list,
    output_path: str,
    completed_counter: list,
) -> tuple:
    """
    对单条样本执行所有需要的评分方法，线程安全地写回结果。

    Returns:
        (status, index) 其中 status 为 'success' | 'skip' | 'error'
    """
    need_lenient = mode in ('lenient', 'all') and sample.get('lenient_score') is None
    need_strict = mode in ('strict', 'all') and sample.get('strict_score') is None
    need_free = mode in ('free', 'all') and sample.get('free_score') is None

    if not need_lenient and not need_strict and not need_free:
        return ('skip', index)

    # 每个线程独立创建 LLM 客户端，避免共享状态
    llm = create_llm_client()

    logger.info(
        f"[{index + 1}/{total}] 开始 题目{sample['question_id']} "
        f"质量={sample['quality']} 答案：{sample['student_answer'][:25]}..."
    )

    try:
        if need_lenient:
            sample['lenient_score'] = lenient_score(llm, sample)
            logger.info(f"  [{index + 1}] 宽松={sample['lenient_score']}")

        if need_strict:
            sample['strict_score'] = strict_score(llm, sample)
            logger.info(f"  [{index + 1}] 严格={sample['strict_score']}")

        if need_free:
            sample['free_score'] = free_score(llm, sample)
            logger.info(f"  [{index + 1}] 无要点={sample['free_score']}")

        # 每完成 10 条自动保存一次（线程安全）
        with save_lock:
            completed_counter[0] += 1
            if completed_counter[0] % 10 == 0:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(dataset, f, ensure_ascii=False, indent=2)
                logger.info(f"  进度已保存（已完成 {completed_counter[0]}/{total}）")

        return ('success', index)

    except Exception as error:
        logger.error(f"  [{index + 1}] 评分失败: {error}")
        return ('error', index)


# ── 主流程 ───────────────────────────────────────────────────────────────────

def run_evaluation(
    dataset_path: str = None,
    output_path: str = None,
    mode: str = 'all',
    resume: bool = True,
    max_workers: int = 5,
):
    """
    对数据集跑 AI 评分（支持并发）。

    Args:
        dataset_path: 数据集 JSON 路径，默认 test/dataset.json
        output_path:  结果输出路径，默认覆盖写回 dataset_path
        mode:         'lenient' | 'strict' | 'free' | 'all'
                      all = 宽松 + 严格 + 无要点引导，三种全跑
        resume:       True 时跳过已有评分的样本（断点续跑）
        max_workers:  并发线程数，默认 5
    """
    if dataset_path is None:
        dataset_path = os.path.join(os.path.dirname(__file__), 'dataset.json')
    if output_path is None:
        output_path = dataset_path

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"数据集文件不存在: {dataset_path}，请先运行 generate_dataset.py")

    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    # resume 模式：过滤出需要处理的样本索引
    pending_indices = []
    skip_count = 0
    for index, sample in enumerate(dataset):
        need_lenient = mode in ('lenient', 'all') and sample.get('lenient_score') is None
        need_strict = mode in ('strict', 'all') and sample.get('strict_score') is None
        need_free = mode in ('free', 'all') and sample.get('free_score') is None
        if resume and not need_lenient and not need_strict and not need_free:
            skip_count += 1
        else:
            pending_indices.append(index)

    total = len(dataset)
    logger.info(
        f"加载数据集：{total} 条样本，模式={mode}，"
        f"待处理={len(pending_indices)}，跳过={skip_count}，并发数={max_workers}"
    )

    if not pending_indices:
        logger.info("所有样本已评分完毕，无需处理。")
        return

    save_lock = threading.Lock()
    completed_counter = [0]  # 用列表包装以便在线程中修改
    success_count = 0
    error_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                evaluate_single_sample,
                dataset[index], index, total, mode,
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

    logger.info("=== 评测完成 ===")
    logger.info(f"成功: {success_count}，跳过（已有结果）: {skip_count}，失败: {error_count}")
    logger.info(f"结果已保存至: {output_path}")
    logger.info("下一步：运行 analyze_results.py 计算统计指标")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='批量 AI 评分脚本（支持并发）')
    parser.add_argument('--dataset', type=str, default=None, help='数据集路径')
    parser.add_argument('--output', type=str, default=None, help='输出路径（默认覆盖原文件）')
    parser.add_argument(
        '--mode', type=str, default='all',
        choices=['lenient', 'strict', 'free', 'all'],
        help='评分模式：lenient=宽松, strict=严格, free=无要点引导, all=全部'
    )
    parser.add_argument('--no-resume', action='store_true', help='不断点续跑，重新评分所有样本')
    parser.add_argument('--workers', type=int, default=4, help='并发线程数，默认 5')
    args = parser.parse_args()

    run_evaluation(
        dataset_path=args.dataset,
        output_path=args.output,
        mode=args.mode,
        resume=not args.no_resume,
        max_workers=args.workers,
    )
