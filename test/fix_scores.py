#!/usr/bin/env python3
"""
只修改 dataset.json 中所有 MEDIUM 样本的 human_score，
将人工均分从 9-10 降到 5-7 范围，以和 HIGH（8-10分）拉开区分度。
答案内容不修改，后续由用户人工调整。
"""
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "dataset.json")

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# 按 medium_count(1-30) 索引: (human_scores, expected_range)
medium_scores = {
    1:  ([6.0, 5.5, 6.0], [4, 7]),
    2:  ([6.0, 5.0, 5.5], [4, 7]),
    3:  ([6.0, 5.5, 5.5], [4, 7]),
    4:  ([5.5, 5.0, 5.5], [4, 6]),
    5:  ([6.0, 5.5, 5.0], [4, 7]),
    6:  ([5.5, 5.0, 5.5], [4, 6]),
    7:  ([6.5, 6.0, 6.0], [5, 7]),
    8:  ([6.0, 5.5, 6.0], [4, 7]),
    9:  ([6.0, 5.5, 6.5], [5, 7]),
    10: ([5.5, 5.0, 5.0], [4, 6]),
    11: ([5.0, 5.5, 5.0], [4, 6]),
    12: ([5.5, 6.0, 5.5], [4, 7]),
    13: ([5.5, 6.0, 5.5], [4, 7]),
    14: ([6.0, 5.5, 6.0], [5, 7]),
    15: ([5.5, 6.0, 5.5], [4, 7]),
    16: ([6.0, 5.5, 5.5], [4, 7]),
    17: ([6.0, 5.5, 5.5], [4, 7]),
    18: ([5.5, 5.0, 5.5], [4, 6]),
    19: ([5.0, 5.5, 5.0], [4, 6]),
    20: ([5.5, 5.0, 5.5], [4, 6]),
    21: ([5.5, 5.0, 5.5], [4, 6]),
    22: ([5.5, 5.0, 5.5], [4, 6]),
    23: ([5.5, 5.0, 5.5], [4, 6]),
    24: ([5.0, 5.5, 5.0], [4, 6]),
    25: ([5.0, 5.5, 5.0], [4, 6]),
    26: ([5.5, 6.0, 5.5], [4, 7]),
    27: ([6.0, 5.5, 6.0], [5, 7]),
    28: ([5.5, 6.0, 5.5], [4, 7]),
    29: ([6.5, 6.0, 6.5], [5, 7]),
    30: ([5.0, 4.5, 5.0], [4, 6]),
}

medium_count = 0
modified_count = 0
for item in data:
    if item.get("quality") == "MEDIUM":
        medium_count += 1
        if medium_count in medium_scores:
            scores, exp_range = medium_scores[medium_count]
            old_avg = item.get("human_score_avg", "N/A")
            item["human_score_1"] = scores[0]
            item["human_score_2"] = scores[1]
            item["human_score_3"] = scores[2]
            item["human_score_avg"] = round(sum(scores) / 3, 2)
            item["expected_score_range"] = exp_range

            for key in ["lenient_score", "strict_score", "free_score", "keyword_score",
                        "original_lenient_score", "original_strict_score",
                        "enhanced_lenient_score", "enhanced_strict_score"]:
                if key in item:
                    del item[key]

            modified_count += 1
            print(f"  #{medium_count} Q{item['question_id']}: {old_avg} -> {item['human_score_avg']}")

print(f"\nTotal MEDIUM: {medium_count}, Modified: {modified_count}")

with open(INPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("dataset.json updated successfully")
