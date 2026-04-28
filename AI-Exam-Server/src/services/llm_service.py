
import os
import json
import logging
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── 提示词模板 ──────────────────────────────────────────────────────────────

RUBRIC_GENERATE_TEMPLATE = PromptTemplate(
    input_variables=["question", "standard_answer", "total_score"],
    template="""你是出题教师，将标准答案拆解为评分细则，以JSON输出。

题目：{question}
标准答案：{standard_answer}
总分：{total_score}

输出格式：
{{
  "points": [
    {{
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
4. 只输出JSON，不要输出其他内容"""
)

SCORE_ANSWER_TEMPLATE = PromptTemplate(
    input_variables=["question", "points", "answer"],
    template="""你是阅卷老师，根据评分细则对学生答案逐点打分，以JSON输出。

题目：{question}
评分细则：{points}
学生答案：{answer}

输出格式：
{{
  "point_scores": [
    {{
      "point_id": "得分点ID",
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
)

# ── LLM 服务 ─────────────────────────────────────────────────────────────────

class LLMService:
    """基于 LangChain 的 LLM 服务封装"""

    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=os.getenv("MODEL_API_KEY"),
            base_url=os.getenv("MODEL_BASE_URL"),
            model="DeepSeek-V3.2",
            temperature=0.1,
            max_tokens=64000,
        )
        self.json_parser = JsonOutputParser()

        # 构建 LangChain 链：PromptTemplate → LLM → JsonOutputParser
        self.rubric_chain = RUBRIC_GENERATE_TEMPLATE | self.llm | self.json_parser
        self.score_chain = SCORE_ANSWER_TEMPLATE | self.llm | self.json_parser

    def generate_rubric(self, question_content, standard_answer, total_score):
        """通过 LangChain 链生成评分细则"""
        for attempt in range(3):
            try:
                result = self.rubric_chain.invoke({
                    "question": question_content,
                    "standard_answer": standard_answer,
                    "total_score": str(total_score),
                })
                if 'points' in result:
                    return result
                logger.warning(f"LLM返回格式不正确，重试 {attempt + 1}/3")
            except Exception as error:
                logger.error(f"评分细则生成失败 (attempt {attempt + 1}): {error}")

        raise Exception("评分细则生成失败，已重试3次")

    def score_answer(self, student_answer, question, points, max_retries=3):
        """通过 LangChain 链对学生答案进行评分"""
        points_desc = [
            {
                "id": str(p.id),
                "description": p.description,
                "score": p.score,
                "acceptable": p.acceptable_expressions
            }
            for p in points
        ]

        for attempt in range(max_retries):
            try:
                result = self.score_chain.invoke({
                    "question": question.topic,
                    "points": json.dumps(points_desc, ensure_ascii=False),
                    "answer": student_answer[:2000],
                })
                if 'point_scores' in result and 'total' in result:
                    return result
                logger.warning(f"LLM返回格式不正确，重试 {attempt + 1}/{max_retries}")
            except Exception as error:
                logger.error(f"LLM评分失败 (attempt {attempt + 1}): {error}")

        raise Exception(f"LLM评分失败，已重试 {max_retries} 次")
