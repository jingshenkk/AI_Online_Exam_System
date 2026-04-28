# @File    : generate_dataset.py
# @Describe: 数据集生成脚本：自动生成30道简答题 + 90条不同质量梯度的学生回答 + 评分要点

import os
import sys
import json
import time
import logging

# 将项目根目录加入路径，复用 LLMService
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'AI-Exam-Server'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'AI-Exam-Server', '.env'))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ── 提示词 ──────────────────────────────────────────────────────────────────

QUESTION_GENERATE_PROMPT = """
你是一名计算机专业课教师，请生成{count}道简答题，涵盖计算机网络、操作系统、数据库、数据结构等方向。

要求：
1. 每道题有明确的标准答案（150字以内）
2. 题目难度适中，适合本科生期末考试
3. 标准答案包含3~5个清晰的得分点
4. 每题满分10分

输出格式（严格JSON）：
{{
  "questions": [
    {{
      "id": 题目序号,
      "subject": "所属科目",
      "question": "题目内容",
      "standard_answer": "标准答案",
      "total_score": 10
    }}
  ]
}}

只输出JSON，不要输出其他内容。
"""

RUBRIC_GENERATE_PROMPT = """
你是出题教师，将标准答案拆解为评分细则，以JSON输出。

题目：{question}
标准答案：{standard_answer}
总分：{total_score}

输出格式：
{{
  "points": [
    {{
      "id": 得分点序号（从1开始的整数）,
      "description": "得分点描述",
      "score": 分值,
      "acceptable_expressions": ["同义表达1", "同义表达2"]
    }}
  ]
}}

要求：
1. 所有点分值之和必须等于总分
2. 每个点列出常见同义表达
3. 得分点应该清晰、具体、可判定
4. 只输出JSON，不要输出其他内容
"""

STUDENT_ANSWER_GENERATE_PROMPT = """
你是一名学生，请根据题目和标准答案，分别生成三种质量梯度的学生回答。

题目：{question}
标准答案：{standard_answer}
评分要点：{points}

要求：
- HIGH（高质量）：命中全部或绝大多数得分点，表述清晰，预期得分8~10分
- MEDIUM（中等质量）：命中约一半得分点，有部分遗漏或表述模糊，预期得分4~7分
- LOW（低质量）：基本偏题或严重遗漏，仅命中0~1个得分点，预期得分0~3分

输出格式（严格JSON）：
{{
  "answers": [
    {{
      "quality": "HIGH",
      "answer": "学生回答内容",
      "expected_score_range": [8, 10]
    }},
    {{
      "quality": "MEDIUM",
      "answer": "学生回答内容",
      "expected_score_range": [4, 7]
    }},
    {{
      "quality": "LOW",
      "answer": "学生回答内容",
      "expected_score_range": [0, 3]
    }}
  ]
}}

只输出JSON，不要输出其他内容。
"""

# ── LLM 客户端 ───────────────────────────────────────────────────────────────

def create_llm_client():
    return ChatOpenAI(
        api_key=os.getenv("MODEL_API_KEY"),
        base_url=os.getenv("MODEL_BASE_URL"),
        model="DeepSeek-V3.2",
        temperature=0.7,
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

# ── 生成流程 ─────────────────────────────────────────────────────────────────

def generate_questions(llm, count: int = 30) -> list:
    """批量生成题目（分批次避免超时）"""
    all_questions = []
    batch_size = 10
    batch_count = (count + batch_size - 1) // batch_size

    for batch_index in range(batch_count):
        current_batch_size = min(batch_size, count - len(all_questions))
        logger.info(f"生成题目 batch {batch_index + 1}/{batch_count}，本批 {current_batch_size} 道...")

        prompt = QUESTION_GENERATE_PROMPT.format(count=current_batch_size)
        result = call_llm_with_retry(llm, prompt)

        for question in result['questions']:
            question['id'] = len(all_questions) + 1
            all_questions.append(question)

        logger.info(f"已生成 {len(all_questions)}/{count} 道题目")
        time.sleep(1)

    return all_questions


def generate_rubric_for_question(llm, question: dict) -> list:
    """为单道题生成评分要点"""
    prompt = RUBRIC_GENERATE_PROMPT.format(
        question=question['question'],
        standard_answer=question['standard_answer'],
        total_score=question['total_score']
    )
    result = call_llm_with_retry(llm, prompt)
    return result['points']


def generate_student_answers(llm, question: dict, points: list) -> list:
    """为单道题生成三个梯度的学生回答"""
    points_desc = json.dumps(
        [{'description': p['description'], 'score': p['score']} for p in points],
        ensure_ascii=False
    )
    prompt = STUDENT_ANSWER_GENERATE_PROMPT.format(
        question=question['question'],
        standard_answer=question['standard_answer'],
        points=points_desc
    )
    result = call_llm_with_retry(llm, prompt)
    return result['answers']


def build_dataset(question_count: int = 30, output_path: str = None) -> str:
    """主流程：生成完整数据集"""
    if output_path is None:
        output_path = os.path.join(os.path.dirname(__file__), 'dataset.json')

    llm = create_llm_client()
    dataset = []

    logger.info("=== 第一阶段：生成题目 ===")
    questions = generate_questions(llm, count=question_count)

    logger.info("=== 第二阶段：生成评分要点 + 学生回答 ===")
    for index, question in enumerate(questions):
        logger.info(f"处理题目 {index + 1}/{len(questions)}: {question['question'][:30]}...")

        try:
            points = generate_rubric_for_question(llm, question)
            time.sleep(0.5)

            student_answers = generate_student_answers(llm, question, points)
            time.sleep(0.5)

            # 构建样本条目
            for answer_item in student_answers:
                dataset.append({
                    'question_id': question['id'],
                    'subject': question['subject'],
                    'question': question['question'],
                    'standard_answer': question['standard_answer'],
                    'total_score': question['total_score'],
                    'points': points,
                    'quality': answer_item['quality'],
                    'student_answer': answer_item['answer'],
                    'expected_score_range': answer_item['expected_score_range'],
                    # 人工评分字段（留空，由人工填写）
                    'human_score_1': None,
                    'human_score_2': None,
                    'human_score_3': None,
                    'human_score_avg': None,
                    # AI评分结果字段（由 run_evaluation.py 填写）
                    'lenient_score': None,
                    'strict_score': None,
                    'free_score': None,
                    # 关键词基线（由 baseline_keyword.py 填写）
                    'keyword_score': None,
                })

            logger.info(f"  ✓ 题目 {index + 1} 完成，生成 {len(student_answers)} 条回答")

        except Exception as error:
            logger.error(f"  ✗ 题目 {index + 1} 处理失败: {error}，跳过")
            continue

    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(dataset, file, ensure_ascii=False, indent=2)

    logger.info(f"=== 数据集生成完成 ===")
    logger.info(f"共生成 {len(dataset)} 条样本，保存至: {output_path}")
    logger.info(f"请将 dataset.json 分发给评分人员，填写 human_score_1/2/3 字段后再运行 run_evaluation.py")

    return output_path


if __name__ == '__main__':
    build_dataset(question_count=30)
