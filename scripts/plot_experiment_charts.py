"""绘制四组实验的多维度对比图表"""

import csv
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import FontProperties

FONT_PATH = "assets/fonts/SourceHanSansSC-Regular.otF"
font = FontProperties(fname=FONT_PATH)
font_bold = FontProperties(fname=FONT_PATH, weight="bold")
matplotlib.rcParams["axes.unicode_minus"] = False

RUNS = [
    ("20260430_172612_without_rewrite", "主测试集-无改写"),
    ("20260430_230707_with_rewrite", "主测试集-启用改写"),
    ("20260501_000136_conversational_without_rewrite", "口语化子集-无改写"),
    ("20260501_002532_conversational_with_rewrite", "口语化子集-启用改写"),
]

SHORT = ["主集-无改写", "主集-改写", "口语化-无改写", "口语化-改写"]
COLORS = ["#4C72B0", "#DD8452", "#4C72B0", "#DD8452"]
HATCHES = ["", "//", "", "//"]
EVAL_DIR = "runs/eval"
OUT_DIR = "runs/figures"


def load_per_question(run_dir):
    path = os.path.join(EVAL_DIR, run_dir, "results.csv")
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def load_summary(run_dir):
    import json
    path = os.path.join(EVAL_DIR, run_dir, "summary.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # merge quality scores from manual_scoring_summary.json if available
    ms_path = os.path.join(EVAL_DIR, run_dir, "manual_scoring_summary.json")
    if os.path.exists(ms_path):
        with open(ms_path, encoding="utf-8") as f:
            ms = json.load(f)
        for k in ["avg_correctness", "avg_completeness", "avg_faithfulness", "avg_retrieval_relevance"]:
            if k in ms:
                data[k] = ms[k]
    return data


# ---------- helpers ----------
def annotate_bars(ax, bars, fmt="{:.1f}", fontsize=8):
    for b in bars:
        h = b.get_height()
        ax.text(b.get_x() + b.get_width() / 2, h + 0.01 * ax.get_ylim()[1],
                fmt.format(h), ha="center", va="bottom", fontsize=fontsize,
                fontproperties=font)


def set_xtick_labels(ax, labels, fontsize=9):
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontproperties=font, fontsize=fontsize)


# ========== Chart 1: 命中率 & 拒答成功率 ==========
def chart_rates(all_summaries):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    hit_rates = [s["target_hit_rate"] * 100 for s in all_summaries]
    refusal_rates = [s["refusal_success_rate"] * 100 for s in all_summaries]

    x = np.arange(4)
    bars1 = ax1.bar(x, hit_rates, color=COLORS, edgecolor="black", linewidth=0.5)
    ax1.set_ylim(0, 110)
    ax1.set_ylabel("命中率 (%)", fontproperties=font, fontsize=10)
    ax1.set_title("目标文档命中率", fontproperties=font_bold, fontsize=12)
    set_xtick_labels(ax1, SHORT)
    annotate_bars(ax1, bars1, "{:.1f}%")
    ax1.axhline(y=100, color="grey", linestyle="--", linewidth=0.5, alpha=0.5)

    bars2 = ax2.bar(x, refusal_rates, color=COLORS, edgecolor="black", linewidth=0.5)
    ax2.set_ylim(0, 110)
    ax2.set_ylabel("拒答成功率 (%)", fontproperties=font, fontsize=10)
    ax2.set_title("拒答成功率", fontproperties=font_bold, fontsize=12)
    set_xtick_labels(ax2, SHORT)
    annotate_bars(ax2, bars2, "{:.1f}%")

    fig.suptitle("命中率与拒答成功率对比", fontproperties=font_bold, fontsize=14, y=1.02)
    fig.tight_layout()
    out = os.path.join(OUT_DIR, "chart_rates.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {out}")


# ========== Chart 2: 耗时堆叠柱状图 ==========
def chart_latency(all_summaries):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5), sharey=True)

    groups = [(0, 1, "主测试集", ax1), (2, 3, "口语化子集", ax2)]

    for i, j, gname, ax in groups:
        labels = [SHORT[i], SHORT[j]]
        rewrite = [all_summaries[i]["avg_rewrite_seconds"], all_summaries[j]["avg_rewrite_seconds"]]
        retrieve = [all_summaries[i]["avg_retrieve_seconds"], all_summaries[j]["avg_retrieve_seconds"]]
        generate = [all_summaries[i]["avg_generate_answer_seconds"], all_summaries[j]["avg_generate_answer_seconds"]]
        # overhead = total - rewrite - retrieve - generate
        overhead = [
            all_summaries[i]["avg_total_seconds"] - rewrite[0] - retrieve[0] - generate[0],
            all_summaries[j]["avg_total_seconds"] - rewrite[1] - retrieve[1] - generate[1],
        ]
        x = np.arange(2)
        w = 0.45
        ax.bar(x, overhead, w, label="其他开销", color="#C7C7C7", edgecolor="black", linewidth=0.5)
        ax.bar(x, rewrite, w, bottom=overhead, label="改写", color="#55A868", edgecolor="black", linewidth=0.5)
        ax.bar(x, retrieve, w, bottom=[o + r for o, r in zip(overhead, rewrite)],
               label="检索", color="#4C72B0", edgecolor="black", linewidth=0.5)
        ax.bar(x, generate, w,
               bottom=[o + r + ret for o, r, ret in zip(overhead, rewrite, retrieve)],
               label="生成", color="#DD8452", edgecolor="black", linewidth=0.5)

        set_xtick_labels(ax, labels)
        ax.set_title(gname, fontproperties=font_bold, fontsize=12)
        ax.set_ylabel("秒 (s)", fontproperties=font, fontsize=10)
        ax.legend(prop=font, fontsize=8, loc="upper left")

    fig.suptitle("各阶段耗时分解", fontproperties=font_bold, fontsize=14, y=1.02)
    fig.tight_layout()
    out = os.path.join(OUT_DIR, "chart_latency.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {out}")


# ========== Chart 3: 质量评分对比 ==========
def chart_quality(all_summaries):
    metrics = ["avg_correctness", "avg_completeness", "avg_faithfulness", "avg_retrieval_relevance"]
    metric_labels = ["正确性", "完整性", "忠实度", "检索相关性"]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharey=True)

    for ax_idx, (i, j, gname) in enumerate([(0, 1, "主测试集"), (2, 3, "口语化子集")]):
        ax = axes[ax_idx]
        x = np.arange(len(metrics))
        w = 0.32
        vals_i = [all_summaries[i][m] for m in metrics]
        vals_j = [all_summaries[j][m] for m in metrics]

        b1 = ax.bar(x - w / 2, vals_i, w, label=SHORT[i], color="#4C72B0",
                     edgecolor="black", linewidth=0.5)
        b2 = ax.bar(x + w / 2, vals_j, w, label=SHORT[j], color="#DD8452",
                     edgecolor="black", linewidth=0.5)

        ax.set_ylim(0, 2.5)
        ax.set_xticks(x)
        ax.set_xticklabels(metric_labels, fontproperties=font, fontsize=9)
        ax.set_title(gname, fontproperties=font_bold, fontsize=12)
        ax.set_ylabel("平均分 (0-2)", fontproperties=font, fontsize=10)
        ax.legend(prop=font, fontsize=8)

        # annotate diffs
        for k in range(len(metrics)):
            diff = vals_j[k] - vals_i[k]
            sign = "+" if diff >= 0 else ""
            color = "#2ca02c" if diff > 0 else "#d62728" if diff < 0 else "grey"
            ax.text(x[k], max(vals_i[k], vals_j[k]) + 0.05,
                    f"{sign}{diff:.2f}", ha="center", fontsize=8,
                    fontproperties=font, color=color)

    fig.suptitle("质量评分对比", fontproperties=font_bold, fontsize=14, y=1.02)
    fig.tight_layout()
    out = os.path.join(OUT_DIR, "chart_quality.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {out}")


# ========== Chart 4: 来源多样性 ==========
def chart_sources(all_summaries):
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(4)
    vals = [s["avg_unique_source_count"] for s in all_summaries]
    bars = ax.bar(x, vals, color=COLORS, edgecolor="black", linewidth=0.5, width=0.55)

    for i, (b, v) in enumerate(zip(bars, vals)):
        if i % 2 == 1:
            diff = v - vals[i - 1]
            ax.text(b.get_x() + b.get_width() / 2, v + 0.05,
                    f"+{diff:.2f}", ha="center", fontsize=9,
                    fontproperties=font, color="#2ca02c", fontweight="bold")

    set_xtick_labels(ax, SHORT)
    ax.set_ylim(0, 4.5)
    ax.set_ylabel("平均唯一来源数", fontproperties=font, fontsize=10)
    ax.set_title("检索来源多样性对比", fontproperties=font_bold, fontsize=14)
    fig.tight_layout()
    out = os.path.join(OUT_DIR, "chart_sources.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {out}")


# ========== Chart 5: 每题耗时分布 (箱线图) ==========
def chart_latency_boxplot(all_rows):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5), sharey=True)

    for ax, (i, j, gname) in zip([ax1, ax2],
                                   [(0, 1, "主测试集"), (2, 3, "口语化子集")]):
        data_i = [float(r["total_seconds"]) for r in all_rows[i]]
        data_j = [float(r["total_seconds"]) for r in all_rows[j]]

        bp = ax.boxplot([data_i, data_j], tick_labels=[SHORT[i], SHORT[j]],
                        patch_artist=True, widths=0.5, showfliers=False,
                        medianprops=dict(color="black", linewidth=1.5))
        for patch, c in zip(bp["boxes"], ["#4C72B0", "#DD8452"]):
            patch.set_facecolor(c)
            patch.set_alpha(0.7)

        ax.set_title(gname, fontproperties=font_bold, fontsize=12)
        ax.set_ylabel("总耗时 (s)", fontproperties=font, fontsize=10)
        for label in ax.get_xticklabels():
            label.set_fontproperties(font)
            label.set_fontsize(9)

        # annotate median
        for k, d in enumerate([data_i, data_j]):
            med = np.median(d)
            ax.text(k + 1, med, f"  中位数 {med:.1f}s", va="center",
                    fontsize=8, fontproperties=font)

    fig.suptitle("每题总耗时分布", fontproperties=font_bold, fontsize=14, y=1.02)
    fig.tight_layout()
    out = os.path.join(OUT_DIR, "chart_latency_boxplot.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {out}")


# ========== Chart 6: 按题型/协议分组命中率 ==========
def chart_hit_by_group(all_rows):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

    # --- 按 question_type ---
    for ax_idx, (i, j, gname) in enumerate([(0, 1, "主测试集"), (2, 3, "口语化子集")]):
        ax = [ax1, ax2][ax_idx]
        types = sorted(set(r["question_type"] for r in all_rows[i]))
        x = np.arange(len(types))
        w = 0.32

        hit_i, hit_j = [], []
        for t in types:
            ri = [r for r in all_rows[i] if r["question_type"] == t]
            rj = [r for r in all_rows[j] if r["question_type"] == t]
            hit_i.append(sum(1 for r in ri if r["target_hit"].strip() == "True") / len(ri) * 100 if ri else 0)
            hit_j.append(sum(1 for r in rj if r["target_hit"].strip() == "True") / len(rj) * 100 if rj else 0)

        ax.bar(x - w / 2, hit_i, w, label=SHORT[i], color="#4C72B0",
               edgecolor="black", linewidth=0.5)
        ax.bar(x + w / 2, hit_j, w, label=SHORT[j], color="#DD8452",
               edgecolor="black", linewidth=0.5)

        ax.set_xticks(x)
        ax.set_xticklabels(types, fontproperties=font, fontsize=8, rotation=15)
        ax.set_ylim(0, 115)
        ax.set_ylabel("命中率 (%)", fontproperties=font, fontsize=10)
        ax.set_title(gname, fontproperties=font_bold, fontsize=12)
        ax.legend(prop=font, fontsize=8)

    fig.suptitle("按题型命中率对比", fontproperties=font_bold, fontsize=14, y=1.02)
    fig.tight_layout()
    out = os.path.join(OUT_DIR, "chart_hit_by_type.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {out}")


# ========== Chart 7: 首字响应时间箱线图 ==========
def chart_first_token_boxplot(all_rows):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5), sharey=True)

    for ax, (i, j, gname) in zip([ax1, ax2],
                                   [(0, 1, "主测试集"), (2, 3, "口语化子集")]):
        data_i = [float(r["first_token_seconds"]) for r in all_rows[i]]
        data_j = [float(r["first_token_seconds"]) for r in all_rows[j]]

        bp = ax.boxplot([data_i, data_j], tick_labels=[SHORT[i], SHORT[j]],
                        patch_artist=True, widths=0.5, showfliers=False,
                        medianprops=dict(color="black", linewidth=1.5))
        for patch, c in zip(bp["boxes"], ["#4C72B0", "#DD8452"]):
            patch.set_facecolor(c)
            patch.set_alpha(0.7)

        ax.axhline(y=8, color="#d62728", linestyle="--", linewidth=1.5, alpha=0.8)
        ax.text(2.45, 8.15, "8s", fontsize=9, fontproperties=font_bold,
                color="#d62728", ha="center")

        ax.set_title(gname, fontproperties=font_bold, fontsize=12)
        ax.set_ylabel("首字响应时间 (s)", fontproperties=font, fontsize=10)
        for label in ax.get_xticklabels():
            label.set_fontproperties(font)
            label.set_fontsize(9)

        for k, d in enumerate([data_i, data_j]):
            med = np.median(d)
            ax.text(k + 1, med, f"  中位数 {med:.1f}s", va="center",
                    fontsize=8, fontproperties=font)

    fig.suptitle("首字响应时间分布", fontproperties=font_bold, fontsize=14, y=1.02)
    fig.tight_layout()
    out = os.path.join(OUT_DIR, "chart_first_token_boxplot.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {out}")


# ========== Chart 8: 首 token 延迟 vs 生成时间 散点图 ==========
def chart_latency_scatter(all_rows):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

    for ax, (i, j, gname) in zip([ax1, ax2],
                                   [(0, 1, "主测试集"), (2, 3, "口语化子集")]):
        for idx, c, m, lab in [(i, "#4C72B0", "o", SHORT[i]),
                                (j, "#DD8452", "s", SHORT[j])]:
            ft = [float(r["first_token_seconds"]) for r in all_rows[idx]]
            gen = [float(r["generate_answer_seconds"]) for r in all_rows[idx]]
            ax.scatter(ft, gen, c=c, marker=m, label=lab, alpha=0.6, s=30,
                       edgecolors="black", linewidth=0.3)

        ax.set_xlabel("首 token 延迟 (s)", fontproperties=font, fontsize=10)
        ax.set_ylabel("答案生成耗时 (s)", fontproperties=font, fontsize=10)
        ax.set_title(gname, fontproperties=font_bold, fontsize=12)
        ax.legend(prop=font, fontsize=8)

    fig.suptitle("首 token 延迟 vs 答案生成耗时", fontproperties=font_bold, fontsize=14, y=1.02)
    fig.tight_layout()
    out = os.path.join(OUT_DIR, "chart_latency_scatter.png")
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Saved {out}")


# ========== main ==========
if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)

    all_summaries = []
    all_rows = []
    for run_dir, _ in RUNS:
        all_summaries.append(load_summary(run_dir))
        all_rows.append(load_per_question(run_dir))

    chart_rates(all_summaries)
    chart_latency(all_summaries)
    chart_quality(all_summaries)
    chart_sources(all_summaries)
    chart_latency_boxplot(all_rows)
    chart_first_token_boxplot(all_rows)
    chart_hit_by_group(all_rows)
    chart_latency_scatter(all_rows)

    print("\nAll charts generated.")
