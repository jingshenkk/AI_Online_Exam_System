# @File    : analyze_prompt_comparison.py
# @Describe: 提示词工程对比实验结果分析：原始prompt vs 改进prompt的指标对比

import os
import json
import logging
import math

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ── 统计计算函数 ──────────────────────────────────────────────────────────────

def compute_mean(values: list) -> float:
    return sum(values) / len(values)

def compute_pearson(x_values: list, y_values: list) -> float:
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
    return round(sum(abs(p - a) for p, a in zip(predicted, actual)) / len(predicted), 4)

def compute_rmse(predicted: list, actual: list) -> float:
    return round(math.sqrt(sum((p - a) ** 2 for p, a in zip(predicted, actual)) / len(predicted)), 4)

def compute_consistency_rate(predicted: list, actual: list, tolerance: float = 1.0) -> float:
    consistent_count = sum(1 for p, a in zip(predicted, actual) if abs(p - a) <= tolerance)
    return round(consistent_count / len(predicted) * 100, 2)

# ── 分析逻辑 ──────────────────────────────────────────────────────────────────

def analyze_method(valid_samples: list, score_field: str) -> dict:
    """按质量梯度分组分析某种评分方法"""
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

def print_comparison_table(all_results: dict):
    """打印原始 vs 改进的对比表格"""
    groups = ['ALL', 'HIGH', 'MEDIUM', 'LOW']

    print("\n" + "=" * 90)
    print("【提示词工程对比实验结果】")
    print("=" * 90)

    for group in groups:
        print(f"\n▶ 质量梯度：{group}")
        print(f"{'方法':<24} {'样本数':>6} {'皮尔逊r':>10} {'MAE':>8} {'RMSE':>8} {'一致率(±1分)':>14} {'AI均分':>8} {'人工均分':>10}")
        print("-" * 90)

        for method_name, method_data in all_results.items():
            group_data = method_data.get(group)
            if group_data is None:
                continue
            print(
                f"{method_name:<24} "
                f"{group_data['count']:>6} "
                f"{group_data['pearson_r']:>10.4f} "
                f"{group_data['mae']:>8.4f} "
                f"{group_data['rmse']:>8.4f} "
                f"{group_data['consistency_rate']:>13.2f}% "
                f"{group_data['avg_ai_score']:>8.2f} "
                f"{group_data['avg_human_score']:>10.2f}"
            )

    # 打印改进幅度
    print("\n" + "=" * 90)
    print("【改进幅度分析（改进版 vs 原始版）】")
    print("=" * 90)

    comparison_pairs = [
        ('原始-宽松(Zero-shot)', '改进-宽松(Few-shot)', '宽松模式改进'),
        ('原始-严格(Zero-shot)', '改进-严格(Few-shot)', '严格模式改进'),
    ]

    for original_key, enhanced_key, label in comparison_pairs:
        if original_key not in all_results or enhanced_key not in all_results:
            continue
        print(f"\n▶ {label}")
        print(f"{'梯度':<10} {'Δr':>10} {'ΔMAE':>10} {'ΔRMSE':>10} {'Δ一致率':>12}")
        print("-" * 55)

        for group in groups:
            original = all_results[original_key].get(group)
            enhanced = all_results[enhanced_key].get(group)
            if original is None or enhanced is None:
                continue

            delta_r = enhanced['pearson_r'] - original['pearson_r']
            delta_mae = enhanced['mae'] - original['mae']
            delta_rmse = enhanced['rmse'] - original['rmse']
            delta_consistency = enhanced['consistency_rate'] - original['consistency_rate']

            # 标注方向：r 越高越好，MAE/RMSE 越低越好，一致率越高越好
            r_arrow = "↑" if delta_r > 0 else ("↓" if delta_r < 0 else "=")
            mae_arrow = "↓" if delta_mae < 0 else ("↑" if delta_mae > 0 else "=")
            rmse_arrow = "↓" if delta_rmse < 0 else ("↑" if delta_rmse > 0 else "=")
            con_arrow = "↑" if delta_consistency > 0 else ("↓" if delta_consistency < 0 else "=")

            print(
                f"{group:<10} "
                f"{delta_r:>+8.4f}{r_arrow:>2} "
                f"{delta_mae:>+8.4f}{mae_arrow:>2} "
                f"{delta_rmse:>+8.4f}{rmse_arrow:>2} "
                f"{delta_consistency:>+10.2f}%{con_arrow:>2}"
            )

    print("\n" + "=" * 90)

def try_plot_comparison(all_results: dict, valid_samples: list, output_dir: str):
    """绘制对比图表"""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm

        chinese_fonts = ['PingFang SC', 'Heiti TC', 'STHeiti', 'SimHei', 'Microsoft YaHei']
        available_font = None
        for font_name in chinese_fonts:
            if any(font_name in f.name for f in fm.fontManager.ttflist):
                available_font = font_name
                break
        if available_font:
            plt.rcParams['font.family'] = available_font
        plt.rcParams['axes.unicode_minus'] = False

        methods_to_plot = list(all_results.keys())
        bar_colors = ['#C44E52', '#DD8452', '#4C72B0', '#55A868']

        # 柱状图：ALL 组核心指标对比
        fig, axes = plt.subplots(1, 3, figsize=(16, 5))
        fig.suptitle('提示词工程对比：原始(Zero-shot) vs 改进(Few-shot)', fontsize=14)

        pearson_values = [all_results[m]['ALL']['pearson_r'] for m in methods_to_plot]
        mae_values = [all_results[m]['ALL']['mae'] for m in methods_to_plot]
        consistency_values = [all_results[m]['ALL']['consistency_rate'] for m in methods_to_plot]

        short_labels = ['原始-宽松', '原始-严格', '改进-宽松', '改进-严格']

        axes[0].bar(short_labels, pearson_values, color=bar_colors)
        axes[0].set_title('皮尔逊相关系数 r（越高越好）')
        axes[0].set_ylim(0.85, 1.0)
        for bar, value in zip(axes[0].patches, pearson_values):
            axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.003,
                         f'{value:.4f}', ha='center', fontsize=9)

        axes[1].bar(short_labels, mae_values, color=bar_colors)
        axes[1].set_title('平均绝对误差 MAE（越低越好）')
        for bar, value in zip(axes[1].patches, mae_values):
            axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                         f'{value:.4f}', ha='center', fontsize=9)

        axes[2].bar(short_labels, consistency_values, color=bar_colors)
        axes[2].set_title('评分一致率 ±1分（越高越好）')
        axes[2].set_ylim(60, 100)
        for bar, value in zip(axes[2].patches, consistency_values):
            axes[2].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                         f'{value:.1f}%', ha='center', fontsize=9)

        for axis in axes:
            axis.tick_params(axis='x', labelsize=8)

        plt.tight_layout()
        bar_path = os.path.join(output_dir, 'prompt_comparison_metrics.png')
        plt.savefig(bar_path, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"对比柱状图已保存: {bar_path}")

        # 分梯度柱状图：MEDIUM 和 LOW 样本的 MAE 对比（差异最明显的地方）
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        fig.suptitle('中/低质量答案评分精度对比（提示词工程效果最明显的区间）', fontsize=13)

        for axis_index, group in enumerate(['MEDIUM', 'LOW']):
            mae_group = [all_results[m][group]['mae'] for m in methods_to_plot]
            con_group = [all_results[m][group]['consistency_rate'] for m in methods_to_plot]

            bar_width = 0.35
            x_positions = range(len(short_labels))

            bars_mae = axes[axis_index].bar(
                [pos - bar_width / 2 for pos in x_positions], mae_group,
                bar_width, label='MAE', color='#DD8452', alpha=0.85
            )

            axis_twin = axes[axis_index].twinx()
            bars_con = axis_twin.bar(
                [pos + bar_width / 2 for pos in x_positions], con_group,
                bar_width, label='一致率%', color='#4C72B0', alpha=0.85
            )

            axes[axis_index].set_title(f'{group} 质量样本')
            axes[axis_index].set_ylabel('MAE（越低越好）')
            axis_twin.set_ylabel('一致率%（越高越好）')
            axes[axis_index].set_xticks(list(x_positions))
            axes[axis_index].set_xticklabels(short_labels, fontsize=8)
            axes[axis_index].legend(loc='upper left', fontsize=8)
            axis_twin.legend(loc='upper right', fontsize=8)

        plt.tight_layout()
        detail_path = os.path.join(output_dir, 'prompt_comparison_detail.png')
        plt.savefig(detail_path, dpi=150, bbox_inches='tight')
        plt.close()
        logger.info(f"分梯度对比图已保存: {detail_path}")

    except ImportError:
        logger.warning("matplotlib 未安装，跳过图表生成。")

def run_analysis(dataset_path: str = None, output_dir: str = None):
    """主分析流程"""
    if dataset_path is None:
        dataset_path = os.path.join(os.path.dirname(__file__), 'dataset.json')
    if output_dir is None:
        output_dir = os.path.dirname(__file__)

    with open(dataset_path, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    # 检查必要字段
    required_fields = [
        'human_score_avg',
        'original_lenient_score', 'original_strict_score',
        'enhanced_lenient_score', 'enhanced_strict_score',
    ]
    valid_samples = [
        sample for sample in dataset
        if all(sample.get(field) is not None for field in required_fields)
    ]
    missing_count = len(dataset) - len(valid_samples)

    if not valid_samples:
        logger.error("没有可分析的样本。请先运行 run_prompt_comparison.py 完成评分。")
        return

    logger.info(f"有效样本数: {len(valid_samples)}，跳过（字段缺失）: {missing_count}")

    method_configs = {
        '原始-宽松(Zero-shot)': 'original_lenient_score',
        '原始-严格(Zero-shot)': 'original_strict_score',
        '改进-宽松(Few-shot)': 'enhanced_lenient_score',
        '改进-严格(Few-shot)': 'enhanced_strict_score',
    }

    all_results = {}
    for method_name, score_field in method_configs.items():
        all_results[method_name] = analyze_method(valid_samples, score_field)

    print_comparison_table(all_results)

    results_path = os.path.join(output_dir, 'prompt_comparison_results.json')
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    logger.info(f"分析结果已保存至: {results_path}")

    try_plot_comparison(all_results, valid_samples, output_dir)

    logger.info("=== 提示词对比分析完成 ===")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='提示词工程对比实验分析脚本')
    parser.add_argument('--dataset', type=str, default=None, help='数据集路径')
    parser.add_argument('--output-dir', type=str, default=None, help='输出目录')
    args = parser.parse_args()

    run_analysis(dataset_path=args.dataset, output_dir=args.output_dir)
