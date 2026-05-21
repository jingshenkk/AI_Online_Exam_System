# @File    : run_prompt_comparison.py
# @Describe: 提示词工程对比实验：原始prompt(zero-shot) vs 改进prompt(few-shot+分层结构)

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

# ── 原始提示词（zero-shot，与 run_evaluation.py 一致）──────────────────────

ORIGINAL_PROMPT = """你是阅卷老师，根据评分细则对学生答案逐点打分，以JSON输出。

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
- 只输出JSON，不要输出其他内容"""

# ── 改进版提示词（few-shot + 角色-任务-约束-示例四层结构）─────────────────

ENHANCED_PROMPT = """## 角色
你是一名经验丰富的高校阅卷教师，擅长根据评分标准客观判定学生简答题作答的语义正确性。

## 任务
根据给定的评分细则，逐点判断学生答案是否命中每个得分点，输出结构化的JSON评分结果。

## 评分细则
{points}

## 题目
{question}

## 学生答案
{answer}

## 约束
1. 每个得分点独立判定，不受其他得分点的判定结果影响
2. 语义等价即视为命中（FULL）：学生用不同措辞、同义词、上位概念表达了相同含义，均应判为FULL
3. 关键概念缺失、事实错误或逻辑矛盾才判为MISS
4. 严禁因格式、标点、语序差异扣分
5. 严禁给出评分细则之外的额外加分或扣分
6. hit字段只能取 "FULL" 或 "MISS" 两个值
7. total字段必须等于所有earned字段之和

## 评分示例

假设评分细则为：
[{{"id":1,"description":"提到氧化磷酸化过程","score":3,"acceptable":["氧化磷酸化","有氧呼吸第三阶段","电子传递链产生ATP"]}},{{"id":2,"description":"提到线粒体是场所","score":2,"acceptable":["线粒体内膜","线粒体基质"]}}]

学生答案："线粒体通过有氧呼吸中的电子传递产生大量ATP，是细胞的能量工厂"

正确的评分输出：
{{"point_scores":[{{"point_id":1,"hit":"FULL","earned":3,"reason":"有氧呼吸中的电子传递涵盖了氧化磷酸化的概念"}},{{"point_id":2,"hit":"FULL","earned":2,"reason":"明确提到线粒体作为场所"}}],"total":5}}

学生答案："细胞通过呼吸作用获得能量"

正确的评分输出：
{{"point_scores":[{{"point_id":1,"hit":"MISS","earned":0,"reason":"仅提及呼吸作用，未涉及氧化磷酸化或电子传递链的具体过程"}},{{"point_id":2,"hit":"MISS","earned":0,"reason":"未提到线粒体"}}],"total":0}}

## 输出格式
严格按以下JSON格式输出，不要输出任何其他内容：
{{
  "point_scores": [
    {{
      "point_id": 得分点ID（整数）,
      "hit": "FULL或MISS",
      "earned": 得分数值,
      "reason": "判定理由（一句话）"
    }}
  ],
  "total": 总分数值
}}"""

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

def score_with_prompt(llm, prompt_template: str, sample: dict) -> dict:
    """用指定的 prompt 模板评分一次"""
    prompt = prompt_template.format(
        question=sample['question'],
        points=build_points_desc(sample['points']),
        answer=sample['student_answer'][:2000]
    )
    return call_llm_with_retry(llm, prompt)

def lenient_with_prompt(llm, prompt_template: str, sample: dict) -> float:
    """宽松模式：单次评分"""
    result = score_with_prompt(llm, prompt_template, sample)
    return round(float(result['total']), 1)

def strict_with_prompt(llm, prompt_template: str, sample: dict) -> float:
    """严格模式：三次投票"""
    points = sample['points']
    results = []
    for _ in range(3):
        result = score_with_prompt(llm, prompt_template, sample)
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
        full_count = votes.count('FULL')
        if full_count >= 2:
            total_score += float(point['score'])

    return round(total_score, 1)

# ── 单条样本评分 ──────────────────────────────────────────────────────────────

def evaluate_single_sample(
    sample: dict,
    index: int,
    total: int,
    save_lock: threading.Lock,
    dataset: list,
    output_path: str,
    completed_counter: list,
) -> tuple:
    """对单条样本分别用原始prompt和改进prompt评分"""

    need_original_lenient = sample.get('original_lenient_score') is None
    need_original_strict = sample.get('original_strict_score') is None
    need_enhanced_lenient = sample.get('enhanced_lenient_score') is None
    need_enhanced_strict = sample.get('enhanced_strict_score') is None

    if not any([need_original_lenient, need_original_strict, need_enhanced_lenient, need_enhanced_strict]):
        return ('skip', index)

    llm = create_llm_client()

    logger.info(
        f"[{index + 1}/{total}] 题目{sample['question_id']} "
        f"质量={sample['quality']} 答案：{sample['student_answer'][:25]}..."
    )

    try:
        # ── 原始 prompt ──
        if need_original_lenient:
            sample['original_lenient_score'] = lenient_with_prompt(llm, ORIGINAL_PROMPT, sample)
            logger.info(f"  [{index + 1}] 原始-宽松={sample['original_lenient_score']}")

        if need_original_strict:
            sample['original_strict_score'] = strict_with_prompt(llm, ORIGINAL_PROMPT, sample)
            logger.info(f"  [{index + 1}] 原始-严格={sample['original_strict_score']}")

        # ── 改进版 prompt ──
        if need_enhanced_lenient:
            sample['enhanced_lenient_score'] = lenient_with_prompt(llm, ENHANCED_PROMPT, sample)
            logger.info(f"  [{index + 1}] 改进-宽松={sample['enhanced_lenient_score']}")

        if need_enhanced_strict:
            sample['enhanced_strict_score'] = strict_with_prompt(llm, ENHANCED_PROMPT, sample)
            logger.info(f"  [{index + 1}] 改进-严格={sample['enhanced_strict_score']}")

        with save_lock:
            completed_counter[0] += 1
            if completed_counter[0] % 5 == 0:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(dataset, f, ensure_ascii=False, indent=2)
                logger.info(f"  进度已保存（已完成 {completed_counter[0]}/{total}）")

        return ('success', index)

    except Exception as error:
        logger.error(f"  [{index + 1}] 评分失败: {error}")
        return ('error', index)

# ── 主流程 ───────────────────────────────────────────────────────────────────

def run_prompt_comparison(dataset_path: str = None, output_path: str = None, max_workers: int = 3):
    """
    对比实验主流程：用原始prompt和改进prompt分别对数据集评分。

    新增字段：
    - original_lenient_score: 原始prompt宽松模式
    - original_strict_score: 原始prompt严格模式
    - enhanced_lenient_score: 改进prompt宽松模式
    - enhanced_strict_score: 改进prompt严格模式
    """
    if dataset_path is None:
        dataset_path = os.path.join(os.path.dirname(__file__), 'dataset.json')
    if output_path is None:
        output_path = dataset_path

    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    total = len(dataset)
    pending_indices = []
    skip_count = 0

    for index, sample in enumerate(dataset):
        needs_work = any(
            sample.get(field) is None
            for field in ['original_lenient_score', 'original_strict_score',
                          'enhanced_lenient_score', 'enhanced_strict_score']
        )
        if needs_work:
            pending_indices.append(index)
        else:
            skip_count += 1

    logger.info(f"提示词对比实验：{total} 条样本，待处理={len(pending_indices)}，跳过={skip_count}，并发数={max_workers}")

    if not pending_indices:
        logger.info("所有样本已评分完毕。")
        return

    save_lock = threading.Lock()
    completed_counter = [0]
    success_count = 0
    error_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                evaluate_single_sample,
                dataset[index], index, total,
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

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    logger.info("=== 提示词对比实验完成 ===")
    logger.info(f"成功: {success_count}，跳过: {skip_count}，失败: {error_count}")
    logger.info(f"结果已保存至: {output_path}")
    logger.info("下一步：运行 analyze_prompt_comparison.py 分析对比结果")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='提示词工程对比实验脚本')
    parser.add_argument('--dataset', type=str, default=None, help='数据集路径')
    parser.add_argument('--output', type=str, default=None, help='输出路径')
    parser.add_argument('--workers', type=int, default=3, help='并发线程数（默认3，严格模式每条要调3次LLM，不宜过高）')
    args = parser.parse_args()

    run_prompt_comparison(
        dataset_path=args.dataset,
        output_path=args.output,
        max_workers=args.workers,
    )
