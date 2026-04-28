# @File    : analyze_results.py
# @Describe: 统计分析脚本：计算皮尔逊相关系数、MAE、一致率，输出对比表格和可视化图表

import os
import json
import logging
import math

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ── 统计计算函数（不依赖 scipy，手动实现）────────────────────────────────────

def compute_mean(values: list) -> float:
    return sum(values) / len(values)


def compute_pearson(x_values: list, y_values: list) -> float:
    """计算皮尔逊相关系数"""
    assert len(x_values) == len(y_values) and len(x_values) > 1

    x_mean = compute_mean(x_values)
    y_mean = compute_mean(y_values)

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    x_std = math.sqrt(sum((x - x_mean) ** 2 for x in x_values))
    y_std = math.sqrt(sum((y - y_mean) ** 2 for y in y_values))

    if x_std == 0 or y_std == 0:
        return 0.0

    return round(numerator / (x_std * y_std), 4)


def compute_mae(predicted: list, actual: list) -> float:
    """计算平均绝对误差"""
    return round(sum(abs(p - a) for p, a in zip(predicted, actual)) / len(predicted), 4)


def compute_consistency_rate(predicted: list, actual: list, tolerance: float = 1.0) -> float:
    """
    计算评分一致率。
    定义：AI评分与人工评分差距在 tolerance 分以内视为一致（满分10分，默认容差1分）。
    """
    consistent_count = sum(1 for p, a in zip(predicted, actual) if abs(p - a) <= tolerance)
    return round(consistent_count / len(predicted) * 100, 2)


def compute_rmse(predicted: list, actual: list) -> float:
    """计算均方根误差"""
    return round(math.sqrt(sum((p - a) ** 2 for p, a in zip(predicted, actual)) / len(predicted)), 4)

# ── 数据加载与校验 ────────────────────────────────────────────────────────────

def load_valid_samples(dataset_path: str) -> tuple:
    """
    加载数据集，过滤出三种评分方法和人工评分均已完成的样本。
    返回 (valid_samples, missing_fields_count)
    """
    with open(dataset_path, 'r', encoding='utf-8') as file:
        dataset = json.load(file)

    required_fields = ['human_score_avg', 'lenient_score', 'strict_score', 'keyword_score', 'free_score']
    valid_samples = []
    missing_count = 0

    for sample in dataset:
        if all(sample.get(field) is not None for field in required_fields):
            valid_samples.append(sample)
        else:
            missing_count += 1
            missing = [f for f in required_fields if sample.get(f) is None]
            logger.debug(f"样本缺少字段 {missing}，跳过")

    return valid_samples, missing_count


def fill_human_score_avg(dataset_path: str) -> int:
    """
    自动计算 human_score_avg（如果 human_score_1/2/3 已填写但 avg 为空）。
    返回更新的样本数量。
    """
    with open(dataset_path, 'r', encoding='utf-8') as file:
        dataset = json.load(file)

    updated_count = 0
    for sample in dataset:
        if sample.get('human_score_avg') is not None:
            continue

        scores = [
            sample.get('human_score_1'),
            sample.get('human_score_2'),
            sample.get('human_score_3'),
        ]
        filled_scores = [s for s in scores if s is not None]

        if filled_scores:
            sample['human_score_avg'] = round(sum(filled_scores) / len(filled_scores), 1)
            updated_count += 1

    if updated_count > 0:
        with open(dataset_path, 'w', encoding='utf-8') as file:
            json.dump(dataset, file, ensure_ascii=False, indent=2)
        logger.info(f"已自动计算 {updated_count} 条样本的 human_score_avg")

    return updated_count

# ── 分析主流程 ────────────────────────────────────────────────────────────────

def analyze_by_quality(valid_samples: list, method_name: str, score_field: str) -> dict:
    """按质量梯度分组分析某种评分方法的指标"""
    quality_groups = {'HIGH': [], 'MEDIUM': [], 'LOW': [], 'ALL': []}

    for sample in valid_samples:
        human_score = float(sample['human_score_avg'])
        ai_score = float(sample[score_field])
        quality = sample['quality']

        quality_groups[quality].append((ai_score, human_score))
        quality_groups['ALL'].append((ai_score, human_score))

    results = {}
    for group_name, pairs in quality_groups.items():
        if len(pairs) < 2:
            continue
        predicted = [p[0] for p in pairs]
        actual = [p[1] for p in pairs]
        results[group_name] = {
            'count': len(pairs),
            'pearson_r': compute_pearson(predicted, actual),
            'mae': compute_mae(predicted, actual),
            'rmse': compute_rmse(predicted, actual),
            'consistency_rate': compute_consistency_rate(predicted, actual, tolerance=1.0),
            'avg_ai_score': round(compute_mean(predicted), 2),
            'avg_human_score': round(compute_mean(actual), 2),
        }

    return results


def print_comparison_table(method_results: dict):
    """打印对比表格"""
    methods = list(method_results.keys())
    groups = ['ALL', 'HIGH', 'MEDIUM', 'LOW']

    print("\n" + "=" * 80)
    print("【实验结果对比表】")
    print("=" * 80)

    for group in groups:
        print(f"\n▶ 质量梯度：{group}")
        print(f"{'方法':<16} {'样本数':>6} {'皮尔逊r':>10} {'MAE':>8} {'RMSE':>8} {'一致率(±1分)':>14} {'AI均分':>8} {'人工均分':>10}")
        print("-" * 80)

        for method_name in methods:
            group_data = method_results[method_name].get(group)
            if group_data is None:
                continue
            print(
                f"{method_name:<16} "
                f"{group_data['count']:>6} "
                f"{group_data['pearson_r']:>10.4f} "
                f"{group_data['mae']:>8.4f} "
                f"{group_data['rmse']:>8.4f} "
                f"{group_data['consistency_rate']:>13.2f}% "
                f"{group_data['avg_ai_score']:>8.2f} "
                f"{group_data['avg_human_score']:>10.2f}"
            )

    print("\n" + "=" * 80)


def save_results_to_json(method_results: dict, output_path: str):
    """将分析结果保存为 JSON，方便后续引用"""
    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(method_results, file, ensure_ascii=False, indent=2)
    logger.info(f"分析结果已保存至: {output_path}")


def try_plot_charts(method_results: dict, valid_samples: list, output_dir: str):
    """尝试绘制散点图和柱状图（需要 matplotlib，若未安装则跳过）"""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm

        # 尝试使用系统中文字体
        chinese_fonts = ['PingFang SC', 'Heiti TC', 'STHeiti', 'SimHei', 'Microsoft YaHei']
        available_font = None
        for font_name in chinese_fonts:
            if any(font_name in f.name for f in fm.fontManager.ttflist):
                available_font = font_name
                break

        if available_font:
            plt.rcParams['font.family'] = available_font
        plt.rcParams['axes.unicode_minus'] = False

        score_fields = {
            '宽松模式(Lenient)': 'lenient_score',
            '严格模式(Strict)': 'strict_score',
            '无要点引导(Free)': 'free_score',
            '关键词基线(Keyword)': 'keyword_score',
        }

        # 图1：散点图（AI评分 vs 人工评分）
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        axes = axes.flatten()
        fig.suptitle('AI评分 vs 人工评分 散点图', fontsize=14)

        for axis, (method_label, score_field) in zip(axes, score_fields.items()):
            ai_scores = [float(s[score_field]) for s in valid_samples if s.get(score_field) is not None]
            human_scores = [float(s['human_score_avg']) for s in valid_samples if s.get(score_field) is not None]

            colors = {'HIGH': 'green', 'MEDIUM': 'orange', 'LOW': 'red'}
            for quality, color in colors.items():
                quality_ai = [float(s[score_field]) for s in valid_samples if s['quality'] == quality and s.get(score_field) is not None]
                quality_human = [float(s['human_score_avg']) for s in valid_samples if s['quality'] == quality and s.get(score_field) is not None]
                axis.scatter(quality_human, quality_ai, c=color, label=quality, alpha=0.6, s=40)

            # 对角线（完美一致线）
            axis.plot([0, 10], [0, 10], 'b--', alpha=0.4, label='完美一致')
            axis.set_xlabel('人工评分')
            axis.set_ylabel('AI评分')
            axis.set_title(method_label)
            axis.legend(fontsize=8)
            axis.set_xlim(-0.5, 10.5)
            axis.set_ylim(-0.5, 10.5)

        plt.tight_layout()
        scatter_path = os.path.join(output_dir, 'scatter_comparison.png')
        plt.savefig(scatter_path, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"散点图已保存: {scatter_path}")

        # 图2：柱状图（各方法 ALL 组的核心指标对比）
        method_labels = list(score_fields.keys())
        pearson_values = [method_results[label]['ALL']['pearson_r'] for label in method_labels]
        mae_values = [method_results[label]['ALL']['mae'] for label in method_labels]
        consistency_values = [method_results[label]['ALL']['consistency_rate'] for label in method_labels]

        fig, axes = plt.subplots(1, 3, figsize=(14, 5))
        fig.suptitle('四种评分方法核心指标对比', fontsize=14)

        bar_colors = ['#4C72B0', '#DD8452', '#C44E52', '#55A868']

        axes[0].bar(method_labels, pearson_values, color=bar_colors)
        axes[0].set_title('皮尔逊相关系数 r（越高越好）')
        axes[0].set_ylim(0, 1.1)
        for bar, value in zip(axes[0].patches, pearson_values):
            axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                         f'{value:.3f}', ha='center', fontsize=10)

        axes[1].bar(method_labels, mae_values, color=bar_colors)
        axes[1].set_title('平均绝对误差 MAE（越低越好）')
        for bar, value in zip(axes[1].patches, mae_values):
            axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                         f'{value:.3f}', ha='center', fontsize=10)

        axes[2].bar(method_labels, consistency_values, color=bar_colors)
        axes[2].set_title('评分一致率 ±1分（越高越好）')
        axes[2].set_ylim(0, 110)
        for bar, value in zip(axes[2].patches, consistency_values):
            axes[2].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                         f'{value:.1f}%', ha='center', fontsize=10)

        for axis in axes:
            axis.tick_params(axis='x', labelsize=8)

        plt.tight_layout()
        bar_path = os.path.join(output_dir, 'metrics_comparison.png')
        plt.savefig(bar_path, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"柱状图已保存: {bar_path}")

    except ImportError:
        logger.warning("matplotlib 未安装，跳过图表生成。如需图表请运行: pip install matplotlib")


def run_analysis(dataset_path: str = None, output_dir: str = None):
    """主分析流程"""
    if dataset_path is None:
        dataset_path = os.path.join(os.path.dirname(__file__), 'dataset.json')
    if output_dir is None:
        output_dir = os.path.dirname(__file__)

    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"数据集文件不存在: {dataset_path}")

    # 自动计算人工评分均值
    fill_human_score_avg(dataset_path)

    valid_samples, missing_count = load_valid_samples(dataset_path)

    if not valid_samples:
        logger.error(
            "没有可分析的完整样本！\n"
            "请确认：\n"
            "  1. 已运行 run_evaluation.py 完成 AI 评分\n"
            "  2. 已运行 baseline_keyword.py 完成关键词基线评分\n"
            "  3. 已在 dataset.json 中填写 human_score_1/2/3 字段"
        )
        return

    logger.info(f"有效样本数: {len(valid_samples)}，跳过（字段缺失）: {missing_count}")

    method_configs = {
        '宽松模式(Lenient)': 'lenient_score',
        '严格模式(Strict)': 'strict_score',
        '无要点引导(Free)': 'free_score',
        '关键词基线(Keyword)': 'keyword_score',
    }

    method_results = {}
    for method_name, score_field in method_configs.items():
        method_results[method_name] = analyze_by_quality(valid_samples, method_name, score_field)

    print_comparison_table(method_results)

    results_json_path = os.path.join(output_dir, 'analysis_results.json')
    save_results_to_json(method_results, results_json_path)

    try_plot_charts(method_results, valid_samples, output_dir)

    logger.info("=== 分析完成 ===")
    logger.info(f"图表和结果文件保存在: {output_dir}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='实验结果统计分析脚本')
    parser.add_argument('--dataset', type=str, default=None, help='数据集路径')
    parser.add_argument('--output-dir', type=str, default=None, help='图表输出目录')
    args = parser.parse_args()

    run_analysis(dataset_path=args.dataset, output_dir=args.output_dir)
