"""绘制四组实验的拒答 Confusion Matrix"""

import csv
import os
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import FontProperties
import numpy as np

FONT_PATH = "assets/fonts/SourceHanSansSC-Regular.otf"
font = FontProperties(fname=FONT_PATH)
font_bold = FontProperties(fname=FONT_PATH, weight="bold")
matplotlib.rcParams["axes.unicode_minus"] = False

RUNS = [
    ("20260430_172612_without_rewrite", "主测试集 - 无改写"),
    ("20260430_230707_with_rewrite", "主测试集 - 启用改写"),
    ("20260501_000136_conversational_without_rewrite", "口语化子集 - 无改写"),
    ("20260501_002532_conversational_with_rewrite", "口语化子集 - 启用改写"),
]

EVAL_DIR = "runs/eval"


def load_results(run_dir):
    path = os.path.join(EVAL_DIR, run_dir, "results.csv")
    rows = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def compute_confusion(rows):
    tp = tn = fp = fn = 0
    for r in rows:
        should = r["should_refuse"].strip() == "True"
        did = r["refused"].strip() == "True"
        if should and did:
            tp += 1
        elif not should and not did:
            tn += 1
        elif not should and did:
            fp += 1
        else:
            fn += 1
    return tp, fp, fn, tn


def draw_confusion_matrix(ax, tp, fp, fn, tn, title):
    matrix = np.array([[tn, fp], [fn, tp]])
    labels = [["TN\n正确回答", "FP\n误拒答"], ["FN\n过度自信", "TP\n正确拒答"]]

    cmap = plt.cm.Blues
    ax.imshow(matrix, cmap=cmap, vmin=0)

    for i in range(2):
        for j in range(2):
            val = matrix[i, j]
            text_color = "white" if val > matrix.max() / 2 else "black"
            ax.text(j, i, f"{labels[i][j]}\n\n{val}",
                    ha="center", va="center", fontsize=11,
                    fontproperties=font_bold, color=text_color)

    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["实际回答", "实际拒答"], fontsize=10, fontproperties=font)
    ax.set_yticklabels(["应答", "应拒"], fontsize=10, fontproperties=font)
    ax.set_xlabel("预测", fontsize=10, fontproperties=font)
    ax.set_ylabel("真实", fontsize=10, fontproperties=font)
    ax.set_title(title, fontsize=12, fontproperties=font_bold, pad=10)


fig, axes = plt.subplots(2, 2, figsize=(10, 8))
fig.suptitle("拒答行为 Confusion Matrix", fontsize=14, fontproperties=font_bold, y=0.98)

for idx, (run_dir, label) in enumerate(RUNS):
    rows = load_results(run_dir)
    tp, fp, fn, tn = compute_confusion(rows)
    draw_confusion_matrix(axes[idx // 2][idx % 2], tp, fp, fn, tn, label)
    total = tp + fp + fn + tn
    acc = (tp + tn) / total * 100 if total else 0
    precision = tp / (tp + fp) * 100 if (tp + fp) else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) else 0
    print(f"{label}: TP={tp} FP={fp} FN={fn} TN={tn} | Acc={acc:.1f}% Prec={precision:.1f}% Recall={recall:.1f}%")

plt.tight_layout(rect=[0, 0, 1, 0.95])
out_path = "runs/figures/refusal_confusion_matrix_comparison.png"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
fig.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"\nSaved to {out_path}")
plt.close()
