# @File    : baseline_keyword.py
# @Describe: 关键词匹配基线评分脚本：使用 jieba 分词 + 关键词命中率计算得分，作为传统方法对比基线

import os
import json
import logging
import re

import jieba

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 停用词列表（常见无意义词，不参与关键词匹配）
STOP_WORDS = {
    '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
    '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
    '自己', '这', '那', '它', '他', '她', '们', '与', '及', '或', '但', '而', '因为',
    '所以', '如果', '虽然', '但是', '然后', '因此', '其中', '通过', '可以', '能够',
    '进行', '实现', '使用', '方式', '方法', '系统', '数据', '信息', '过程', '结果',
    '主要', '基本', '一般', '具体', '相关', '不同', '各种', '包括', '需要', '对于',
}


def tokenize_and_filter(text: str) -> set:
    """分词并过滤停用词和单字符词，返回有效词集合"""
    tokens = jieba.cut(text)
    return {
        token.strip()
        for token in tokens
        if len(token.strip()) >= 2 and token.strip() not in STOP_WORDS
    }


def extract_keywords_from_standard_answer(standard_answer: str, points: list) -> list:
    """
    从标准答案和评分要点中提取关键词列表。
    优先从每个得分点的描述中提取，再补充标准答案中的词。
    返回每个得分点对应的关键词集合列表，用于按点计分。
    """
    point_keywords = []
    for point in points:
        # 合并得分点描述 + 同义表达
        point_text = point['description']
        acceptable = point.get('acceptable_expressions', [])
        combined_text = point_text + '。' + '。'.join(acceptable)

        keywords = tokenize_and_filter(combined_text)
        point_keywords.append({
            'point_id': point['id'],
            'score': point['score'],
            'keywords': keywords,
        })

    return point_keywords


def keyword_score_sample(sample: dict) -> float:
    """
    对单条样本进行关键词匹配评分。

    评分逻辑：
    - 对每个得分点，计算学生回答中命中该点关键词的比例
    - 命中率 >= 0.5 则得该点满分，否则按比例得分（最低0）
    - 汇总所有得分点得分
    """
    points = sample['points']
    student_answer = sample['student_answer']
    total_score = float(sample['total_score'])

    student_tokens = tokenize_and_filter(student_answer)

    if not student_tokens:
        return 0.0

    point_keyword_groups = extract_keywords_from_standard_answer(sample['standard_answer'], points)

    earned_score = 0.0
    for group in point_keyword_groups:
        point_keywords = group['keywords']
        point_max_score = float(group['score'])

        if not point_keywords:
            continue

        hit_count = len(student_tokens & point_keywords)
        hit_ratio = hit_count / len(point_keywords)

        # 命中率 >= 50% 得满分，否则按比例
        if hit_ratio >= 0.5:
            earned_score += point_max_score
        else:
            earned_score += point_max_score * hit_ratio

    return round(min(earned_score, total_score), 1)


def run_keyword_baseline(
    dataset_path: str = None,
    output_path: str = None,
    resume: bool = True
):
    """
    对数据集中所有样本运行关键词匹配基线评分，结果写入 keyword_score 字段。

    Args:
        dataset_path: 数据集路径，默认 test/dataset.json
        output_path:  输出路径，默认覆盖原文件
        resume:       True 时跳过已有 keyword_score 的样本
    """
    if dataset_path is None:
        dataset_path = os.path.join(os.path.dirname(__file__), 'dataset.json')
    if output_path is None:
        output_path = dataset_path

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"数据集文件不存在: {dataset_path}，请先运行 generate_dataset.py")

    with open(dataset_path, 'r', encoding='utf-8') as file:
        dataset = json.load(file)

    logger.info(f"加载数据集：{len(dataset)} 条样本，开始关键词基线评分...")

    success_count = 0
    skip_count = 0

    for index, sample in enumerate(dataset):
        if resume and sample.get('keyword_score') is not None:
            skip_count += 1
            continue

        try:
            score = keyword_score_sample(sample)
            sample['keyword_score'] = score
            success_count += 1

            if (index + 1) % 10 == 0:
                logger.info(f"进度: {index + 1}/{len(dataset)}")

        except Exception as error:
            logger.error(f"样本 {index + 1} 评分失败: {error}")
            sample['keyword_score'] = 0.0

    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(dataset, file, ensure_ascii=False, indent=2)

    logger.info("=== 关键词基线评分完成 ===")
    logger.info(f"成功: {success_count}，跳过（已有结果）: {skip_count}")
    logger.info(f"结果已保存至: {output_path}")
    logger.info("下一步：运行 analyze_results.py 计算统计指标")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='关键词匹配基线评分脚本')
    parser.add_argument('--dataset', type=str, default=None, help='数据集路径')
    parser.add_argument('--output', type=str, default=None, help='输出路径')
    parser.add_argument('--no-resume', action='store_true', help='重新评分所有样本')
    args = parser.parse_args()

    run_keyword_baseline(
        dataset_path=args.dataset,
        output_path=args.output,
        resume=not args.no_resume
    )
