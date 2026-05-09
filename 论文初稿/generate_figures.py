#!/usr/bin/env python3
"""
论文图片生成脚本 — 共生成7张图

数据图表(散点图/柱状图)用 matplotlib 生成；
架构图/流程图/ER图用 HTML+CSS 制作，通过 playwright 截图导出高清PNG。
"""

import json
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# 中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti']
plt.rcParams['axes.unicode_minus'] = False

BASE = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(BASE, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)

# ============================================================
# HTML截图：用 playwright 将 HTML 文件导出为高清 PNG
# ============================================================

def screenshot_html(html_filename, png_filename, scale=2):
    """用 playwright 将 HTML 文件截图为 PNG"""
    from playwright.sync_api import sync_playwright

    html_path = os.path.join(FIG_DIR, html_filename)
    png_path = os.path.join(FIG_DIR, png_filename)

    if not os.path.exists(html_path):
        print(f"  [跳过] {html_filename} 不存在")
        return

    file_url = f"file://{os.path.abspath(html_path)}"

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(device_scale_factor=scale)
        page.goto(file_url, wait_until='networkidle')
        page.wait_for_timeout(500)

        # 获取内容实际尺寸，按内容裁剪
        content_box = page.evaluate("""() => {
            const body = document.body;
            const html = document.documentElement;
            return {
                width: Math.max(body.scrollWidth, html.scrollWidth),
                height: Math.max(body.scrollHeight, html.scrollHeight)
            };
        }""")
        page.set_viewport_size({
            'width': content_box['width'],
            'height': content_box['height']
        })
        page.wait_for_timeout(300)
        page.screenshot(path=png_path, full_page=True)
        browser.close()

    print(f"  -> {png_filename} ({scale}x 高清)")


# ============================================================
# 图3.3 四种评分方法散点图对比
# ============================================================
def gen_scatter():
    print("生成 图3.3 散点图...")
    with open(os.path.join(BASE, '..', 'test', 'dataset.json'), 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 提取数据
    human = [s['human_score_avg'] for s in data if 'human_score_avg' in s]
    lenient = [s.get('lenient_score', 0) for s in data if 'human_score_avg' in s]
    strict = [s.get('strict_score', 0) for s in data if 'human_score_avg' in s]
    free = [s.get('free_score', 0) for s in data if 'human_score_avg' in s]
    keyword = [s.get('keyword_score', 0) for s in data if 'human_score_avg' in s]

    fig, axes = plt.subplots(2, 2, figsize=(10, 9))
    configs = [
        (axes[0,0], lenient, '宽松模式', '#2196F3'),
        (axes[0,1], strict,  '严格模式', '#4CAF50'),
        (axes[1,0], free,    '无要点引导', '#FF9800'),
        (axes[1,1], keyword, '关键词基线', '#F44336'),
    ]

    for ax, ai_scores, title, color in configs:
        ax.scatter(human, ai_scores, c=color, alpha=0.6, s=50, edgecolors='white', linewidth=0.5)
        ax.plot([0, 10], [0, 10], 'k--', alpha=0.3, linewidth=1)
        ax.set_xlim(-0.5, 10.5)
        ax.set_ylim(-0.5, 10.5)
        ax.set_xlabel('人工评分 (分)', fontsize=10)
        ax.set_ylabel('AI评分 (分)', fontsize=10)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.2)

        # 计算并显示相关系数
        r = np.corrcoef(human, ai_scores)[0, 1]
        ax.text(0.05, 0.95, f'r = {r:.4f}', transform=ax.transAxes,
                fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    fig.suptitle('图3.3 四种评分方法散点图对比', fontsize=14, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(os.path.join(FIG_DIR, 'fig3_3_scatter.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("  -> fig3_3_scatter.png")


# ============================================================
# 图3.4 四种评分方法核心指标柱状图
# ============================================================
def gen_bar():
    print("生成 图3.4 柱状图...")
    with open(os.path.join(BASE, '..', 'test', 'analysis_results.json'), 'r', encoding='utf-8') as f:
        stats = json.load(f)

    methods = ['宽松模式(Lenient)', '严格模式(Strict)', '无要点引导(Free)', '关键词基线(Keyword)']
    labels = ['宽松模式', '严格模式', '无要点引导', '关键词基线']
    colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336']

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    # 子图1: 皮尔逊相关系数
    vals = [stats[m]['ALL']['pearson_r'] for m in methods]
    bars = axes[0].bar(labels, vals, color=colors, edgecolor='white', linewidth=1.2)
    axes[0].set_ylabel('皮尔逊相关系数 (r)', fontsize=10)
    axes[0].set_title('相关性', fontsize=12, fontweight='bold')
    axes[0].set_ylim(0, 1.1)
    for bar, v in zip(bars, vals):
        axes[0].text(bar.get_x() + bar.get_width()/2, v + 0.02, f'{v:.4f}',
                     ha='center', fontsize=8)

    # 子图2: MAE
    vals = [stats[m]['ALL']['mae'] for m in methods]
    bars = axes[1].bar(labels, vals, color=colors, edgecolor='white', linewidth=1.2)
    axes[1].set_ylabel('平均绝对误差 (分)', fontsize=10)
    axes[1].set_title('MAE', fontsize=12, fontweight='bold')
    for bar, v in zip(bars, vals):
        axes[1].text(bar.get_x() + bar.get_width()/2, v + 0.05, f'{v:.4f}',
                     ha='center', fontsize=8)

    # 子图3: 一致率
    vals = [stats[m]['ALL']['consistency_rate'] for m in methods]
    bars = axes[2].bar(labels, vals, color=colors, edgecolor='white', linewidth=1.2)
    axes[2].set_ylabel('一致率 (%)', fontsize=10)
    axes[2].set_title('评分一致率 (±1分)', fontsize=12, fontweight='bold')
    axes[2].set_ylim(0, 100)
    for bar, v in zip(bars, vals):
        axes[2].text(bar.get_x() + bar.get_width()/2, v + 1.5, f'{v:.2f}%',
                     ha='center', fontsize=8)

    for ax in axes:
        ax.tick_params(axis='x', rotation=15)
        ax.grid(axis='y', alpha=0.2)

    fig.suptitle('图3.4 四种评分方法核心指标柱状图对比', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, 'fig3_4_bar.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print("  -> fig3_4_bar.png")


# ============================================================
# 以下5张图用 HTML + playwright 截图生成
# ============================================================

def gen_html_figures():
    """将5张HTML架构/流程图截图为高清PNG"""
    html_to_png = [
        ('fig1_1_framework.html', 'fig1_1_framework.png', '图1.1 研究内容框架图'),
        ('fig3_1_flow.html',      'fig3_1_flow.png',      '图3.1 智能评分方案流程图'),
        ('fig3_2_vote.html',      'fig3_2_vote.png',      '图3.2 投票流程图'),
        ('fig4_1_arch.html',      'fig4_1_arch.png',      '图4.1 系统架构图'),
        ('fig4_2_er.html',        'fig4_2_er.png',        '图4.2 数据库ER图'),
    ]
    for html_file, png_file, desc in html_to_png:
        print(f"生成 {desc}...")
        screenshot_html(html_file, png_file, scale=2)


# ============================================================
# 主函数
# ============================================================
if __name__ == '__main__':
    print(f"输出目录: {FIG_DIR}\n")

    # 数据图表 (matplotlib)
    gen_scatter()        # 图3.3 散点图
    gen_bar()            # 图3.4 柱状图

    # 架构/流程图 (HTML + playwright 截图)
    gen_html_figures()   # 图1.1, 3.1, 3.2, 4.1, 4.2

    print(f"\n全部完成！共生成 7 张图片，保存在 {FIG_DIR}")

