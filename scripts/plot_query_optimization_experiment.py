from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors as mcolors
from matplotlib import rcParams
from matplotlib.font_manager import FontProperties

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVAL_ROOT = PROJECT_ROOT / "runs" / "eval"
OUTPUT_DIR = PROJECT_ROOT / "runs" / "figures" / "query_optimization_experiment"

SCENES = {
    "主测试集": {
        "without": EVAL_ROOT / "20260430_172612_without_rewrite",
        "with": EVAL_ROOT / "20260430_230707_with_rewrite",
    },
    "口语化子集": {
        "without": EVAL_ROOT / "20260501_000136_conversational_without_rewrite",
        "with": EVAL_ROOT / "20260501_002532_conversational_with_rewrite",
    },
}

LABELS = {"without": "无优化", "with": "查询优化"}
PRIMARY = "#1f3a5f"
SECONDARY = "#5f85a3"
ACCENT = "#dd8452"
ACCENT_GREEN = "#3b8b5f"
ACCENT_RED = "#c44945"
MUTED = "#8f9baa"
GRID = "#d8dee9"
TEXT = "#1f2937"
BG = "#ffffff"


def _load_zh_font() -> FontProperties:
    font_path = PROJECT_ROOT / "assets" / "fonts" / "SourceHanSansSC-Regular.otf"
    if font_path.exists():
        return FontProperties(fname=str(font_path))
    return FontProperties(family="DejaVu Sans")


ZH_FONT = _load_zh_font()
rcParams["axes.unicode_minus"] = False
rcParams["figure.facecolor"] = BG
rcParams["axes.facecolor"] = BG


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def apply_axis_style(ax, grid_axis: str = "y") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#b8c2cc")
    ax.spines["bottom"].set_color("#b8c2cc")
    ax.tick_params(axis="both", colors=TEXT, labelsize=10)
    ax.grid(axis=grid_axis, linestyle="--", linewidth=0.6, color=GRID, alpha=0.9)
    ax.set_axisbelow(True)


def set_axis_fonts(ax) -> None:
    for label in ax.get_xticklabels():
        label.set_fontproperties(ZH_FONT)
    for label in ax.get_yticklabels():
        label.set_fontproperties(ZH_FONT)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_results_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_scene_data() -> dict[str, dict[str, dict]]:
    data: dict[str, dict[str, dict]] = {}
    for scene, variants in SCENES.items():
        data[scene] = {}
        for variant, run_dir in variants.items():
            data[scene][variant] = {
                "summary": load_json(run_dir / "summary.json"),
                "manual": load_json(run_dir / "manual_scoring_summary.json"),
                "results": load_results_csv(run_dir / "results.csv"),
                "run_dir": run_dir.name,
            }
    return data


def compute_confusion(rows: list[dict[str, str]]) -> dict[str, int]:
    tp = fp = fn = tn = 0
    for row in rows:
        should = row["should_refuse"] == "True"
        refused = row["refused"] == "True"
        if should and refused:
            tp += 1
        elif should and not refused:
            fn += 1
        elif not should and refused:
            fp += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def format_pp_delta(before: float, after: float) -> str:
    delta = (after - before) * 100
    return f"{delta:+.1f}pp"


def format_pct_delta(before: float, after: float) -> str:
    if before == 0:
        return "NA"
    delta = (after - before) / before * 100
    return f"{delta:+.1f}%"


def plot_overall_tradeoff(data: dict[str, dict[str, dict]]) -> None:
    metrics = [
        ("target_hit_rate", "目标文档命中率", "rate"),
        ("avg_unique_source_count", "平均唯一来源数", "count"),
        ("avg_first_token_seconds", "平均首字响应时间 (s)", "time"),
    ]
    scenes = list(data.keys())
    fig, axes = plt.subplots(1, 3, figsize=(15.2, 5.8))

    for ax, (field, title, metric_type) in zip(axes, metrics):
        x = np.arange(len(scenes))
        width = 0.28
        before_vals = [float(data[s]["without"]["summary"][field]) for s in scenes]
        after_vals = [float(data[s]["with"]["summary"][field]) for s in scenes]
        ax.bar(x - width / 2, before_vals, width=width, color=SECONDARY, label="无优化")
        ax.bar(x + width / 2, after_vals, width=width, color=PRIMARY, label="查询优化")
        ax.set_title(title, fontproperties=ZH_FONT, fontsize=14, color=TEXT)
        ax.set_xticks(x)
        ax.set_xticklabels(scenes)
        if metric_type == "rate":
            ax.set_ylim(0, 1.08)
        elif metric_type == "count":
            ax.set_ylim(0, max(after_vals) * 1.35)
        else:
            ax.set_ylim(0, max(after_vals) * 1.30)
        apply_axis_style(ax, "y")
        set_axis_fonts(ax)

        for idx, (before, after) in enumerate(zip(before_vals, after_vals)):
            y = max(before, after)
            if metric_type == "rate":
                delta_text = format_pp_delta(before, after)
                text_y = y + 0.04
                before_text = f"{before * 100:.1f}%"
                after_text = f"{after * 100:.1f}%"
            else:
                delta_text = format_pct_delta(before, after)
                text_y = y + (0.16 if metric_type == "count" else 0.32)
                before_text = f"{before:.2f}"
                after_text = f"{after:.2f}"
            delta_color = ACCENT_GREEN if after >= before else ACCENT_RED
            ax.text(idx, text_y, delta_text, ha="center", va="bottom", color=delta_color, fontproperties=ZH_FONT, fontsize=11)
            ax.text(idx - width / 2, before + (0.015 if metric_type == "rate" else 0.05), before_text, ha="center", va="bottom", color=TEXT, fontproperties=ZH_FONT, fontsize=9)
            ax.text(idx + width / 2, after + (0.015 if metric_type == "rate" else 0.05), after_text, ha="center", va="bottom", color=TEXT, fontproperties=ZH_FONT, fontsize=9)

    legend = axes[0].legend(frameon=False, loc="upper left", bbox_to_anchor=(0.0, 1.18))
    for text in legend.get_texts():
        text.set_fontproperties(ZH_FONT)
    fig.suptitle("查询优化对检索命中、来源覆盖与响应效率的总体影响", fontproperties=ZH_FONT, fontsize=17, color=TEXT, y=0.87)
    fig.tight_layout(rect=[0, 0, 1, 0.84])
    fig.savefig(OUTPUT_DIR / "fig01_overall_tradeoff.png", dpi=240)
    plt.close(fig)


def plot_manual_quality(data: dict[str, dict[str, dict]]) -> None:
    metrics = [
        ("avg_correctness", "正确性"),
        ("avg_completeness", "完整性"),
        ("avg_faithfulness", "忠实性"),
        ("avg_retrieval_relevance", "检索相关性"),
    ]
    scenes = list(data.keys())
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.6), sharey=True)

    for ax, scene in zip(axes, scenes):
        x = np.arange(len(metrics))
        width = 0.34
        before_vals = [float(data[scene]["without"]["manual"][field]) for field, _ in metrics]
        after_vals = [float(data[scene]["with"]["manual"][field]) for field, _ in metrics]
        ax.bar(x - width / 2, before_vals, width=width, color=SECONDARY, label="无优化")
        ax.bar(x + width / 2, after_vals, width=width, color=PRIMARY, label="查询优化")
        ax.set_title(scene, fontproperties=ZH_FONT, fontsize=14, color=TEXT)
        ax.set_xticks(x)
        ax.set_xticklabels([label for _, label in metrics], rotation=10)
        ax.set_ylim(0, 2.12)
        apply_axis_style(ax, "y")
        set_axis_fonts(ax)
        for idx, (before, after) in enumerate(zip(before_vals, after_vals)):
            delta = after - before
            delta_text = f"{delta:+.2f}"
            color = ACCENT_GREEN if delta >= 0 else ACCENT_RED
            ax.text(idx, max(before, after) + 0.08, delta_text, ha="center", va="bottom", color=color, fontproperties=ZH_FONT, fontsize=10)

    legend = axes[0].legend(frameon=False, loc="upper left", bbox_to_anchor=(0.0, 1.18))
    for text in legend.get_texts():
        text.set_fontproperties(ZH_FONT)
    fig.suptitle("查询优化对人工评分质量维度的影响", fontproperties=ZH_FONT, fontsize=17, color=TEXT, y=0.90)
    fig.tight_layout(rect=[0, 0, 1, 0.86])
    fig.savefig(OUTPUT_DIR / "fig02_manual_quality.png", dpi=240)
    plt.close(fig)


def plot_latency_breakdown(data: dict[str, dict[str, dict]]) -> None:
    rows = []
    for scene in data:
        for variant in ("without", "with"):
            summary = data[scene][variant]["summary"]
            rows.append(
                {
                    "label": f"{scene}\n{LABELS[variant]}",
                    "rewrite": float(summary.get("avg_rewrite_seconds", 0.0)),
                    "retrieve": float(summary.get("avg_retrieve_seconds", 0.0)),
                    "generate": float(summary.get("avg_generate_answer_seconds", 0.0)),
                    "first_token": float(summary.get("avg_first_token_seconds", 0.0)),
                }
            )

    fig, ax = plt.subplots(figsize=(12.8, 6.2))
    y = np.arange(len(rows))
    rewrite_vals = np.array([r["rewrite"] for r in rows])
    retrieve_vals = np.array([r["retrieve"] for r in rows])
    generate_vals = np.array([r["generate"] for r in rows])
    first_vals = np.array([r["first_token"] for r in rows])

    ax.barh(y, rewrite_vals, color=ACCENT, label="改写")
    ax.barh(y, retrieve_vals, left=rewrite_vals, color=SECONDARY, label="检索")
    ax.barh(y, generate_vals, left=rewrite_vals + retrieve_vals, color=PRIMARY, label="生成")
    ax.scatter(first_vals, y, color=ACCENT_RED, s=48, zorder=3, label="首字响应时间")

    for idx, row in enumerate(rows):
        total = row["rewrite"] + row["retrieve"] + row["generate"]
        ax.text(total + 0.12, idx, f"{total:.2f}s", va="center", ha="left", color=TEXT, fontproperties=ZH_FONT, fontsize=10)
        ax.text(row["first_token"] + 0.08, idx - 0.17, f"{row['first_token']:.2f}s", va="center", ha="left", color=ACCENT_RED, fontproperties=ZH_FONT, fontsize=9)

    ax.set_yticks(y)
    ax.set_yticklabels([r["label"] for r in rows])
    ax.invert_yaxis()
    ax.set_xlabel("平均耗时 (s)", fontproperties=ZH_FONT, color=TEXT)
    apply_axis_style(ax, "x")
    set_axis_fonts(ax)
    legend = ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0.0, 1.10), ncol=4)
    for text in legend.get_texts():
        text.set_fontproperties(ZH_FONT)
    fig.suptitle("查询优化的时延构成与首字响应变化", fontproperties=ZH_FONT, fontsize=17, color=TEXT, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(OUTPUT_DIR / "fig03_latency_breakdown.png", dpi=240)
    plt.close(fig)


def draw_confusion_matrix(ax, matrix: np.ndarray, title: str) -> None:
    cmap = plt.cm.Blues
    ax.imshow(matrix, cmap=cmap, vmin=0, vmax=max(1, matrix.max()))
    labels = [["TN\n正常回答", "FP\n误拒"], ["FN\n应拒未拒", "TP\n正确拒答"]]
    for i in range(2):
        for j in range(2):
            value = int(matrix[i, j])
            text_color = "white" if value > matrix.max() / 2 else TEXT
            ax.text(j, i, f"{labels[i][j]}\n{value}", ha="center", va="center", fontsize=11, fontproperties=ZH_FONT, color=text_color)
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["预测回答", "预测拒答"])
    ax.set_yticklabels(["真实应答", "真实应拒"])
    set_axis_fonts(ax)
    ax.set_title(title, fontproperties=ZH_FONT, fontsize=13, color=TEXT, pad=10)


def plot_refusal_matrices(data: dict[str, dict[str, dict]]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 8.6))
    fig.suptitle("查询优化前后保守回答行为对比", fontproperties=ZH_FONT, fontsize=17, color=TEXT, y=0.98)
    order = [
        ("主测试集", "without"),
        ("主测试集", "with"),
        ("口语化子集", "without"),
        ("口语化子集", "with"),
    ]
    for ax, (scene, variant) in zip(axes.flat, order):
        confusion = compute_confusion(data[scene][variant]["results"])
        matrix = np.array(
            [
                [confusion["tn"], confusion["fp"]],
                [confusion["fn"], confusion["tp"]],
            ]
        )
        title = f"{scene} - {LABELS[variant]}"
        draw_confusion_matrix(ax, matrix, title)

        tp = confusion["tp"]
        fp = confusion["fp"]
        fn = confusion["fn"]
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        ax.text(
            0.5,
            -0.24,
            f"Precision={precision:.2f}  Recall={recall:.2f}",
            ha="center",
            va="center",
            transform=ax.transAxes,
            color=MUTED,
            fontproperties=ZH_FONT,
            fontsize=10,
        )

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUTPUT_DIR / "fig04_refusal_matrices.png", dpi=240)
    plt.close(fig)


def plot_first_token_boxplot(data: dict[str, dict[str, dict]]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 5.2), sharey=True)

    for ax, scene in zip(axes, data.keys()):
        without = [float(r["first_token_seconds"]) for r in data[scene]["without"]["results"]]
        with_opt = [float(r["first_token_seconds"]) for r in data[scene]["with"]["results"]]
        bp = ax.boxplot(
            [without, with_opt],
            tick_labels=["无优化", "查询优化"],
            patch_artist=True,
            widths=0.5,
            showfliers=False,
            medianprops=dict(color="black", linewidth=1.5),
        )
        for patch, color in zip(bp["boxes"], [SECONDARY, PRIMARY]):
            patch.set_facecolor(color)
            patch.set_alpha(0.72)

        ax.axhline(y=8, color=ACCENT_RED, linestyle="--", linewidth=1.2, alpha=0.8)
        ax.text(2.42, 8.18, "8s", fontsize=9, fontproperties=ZH_FONT, color=ACCENT_RED, ha="center")
        ax.set_title(scene, fontproperties=ZH_FONT, fontsize=14, color=TEXT)
        ax.set_ylabel("首字响应时间 (s)", fontproperties=ZH_FONT, color=TEXT)
        apply_axis_style(ax, "y")
        set_axis_fonts(ax)

        for idx, values in enumerate([without, with_opt], start=1):
            median = float(np.median(values))
            ax.text(idx, median - 0.5, f"中位数 {median:.2f}s", va="top", ha="center", fontsize=9, fontproperties=ZH_FONT, color=TEXT)

    fig.suptitle("首字响应时间分布对比", fontproperties=ZH_FONT, fontsize=17, color=TEXT, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(OUTPUT_DIR / "fig09_first_token_boxplot.png", dpi=240)
    plt.close(fig)


def plot_hit_by_question_type(data: dict[str, dict[str, dict]]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13.8, 5.6))

    for ax, scene in zip(axes, data.keys()):
        without_rows = data[scene]["without"]["results"]
        with_rows = data[scene]["with"]["results"]
        question_types = sorted({r["question_type"] for r in without_rows} | {r["question_type"] for r in with_rows})
        x = np.arange(len(question_types))
        width = 0.34
        without_hit = []
        with_hit = []

        for qtype in question_types:
            wr = [r for r in without_rows if r["question_type"] == qtype]
            xr = [r for r in with_rows if r["question_type"] == qtype]
            w_hit = (sum(r["target_hit"] == "True" for r in wr) / len(wr) * 100) if wr else 0.0
            x_hit = (sum(r["target_hit"] == "True" for r in xr) / len(xr) * 100) if xr else 0.0
            without_hit.append(w_hit)
            with_hit.append(x_hit)

        bars1 = ax.bar(x - width / 2, without_hit, width=width, color=SECONDARY, label="无优化")
        bars2 = ax.bar(x + width / 2, with_hit, width=width, color=PRIMARY, label="查询优化")
        ax.set_xticks(x)
        ax.set_xticklabels(question_types, rotation=18)
        ax.set_ylim(0, 115)
        ax.set_ylabel("目标文档命中率 (%)", fontproperties=ZH_FONT, color=TEXT)
        ax.set_title(scene, fontproperties=ZH_FONT, fontsize=14, color=TEXT)
        apply_axis_style(ax, "y")
        set_axis_fonts(ax)

        for idx, (b1, b2) in enumerate(zip(bars1, bars2)):
            delta = with_hit[idx] - without_hit[idx]
            if abs(delta) >= 0.1:
                color = ACCENT_GREEN if delta > 0 else ACCENT_RED
                ax.text(idx, max(without_hit[idx], with_hit[idx]) + 3.0, f"{delta:+.0f}pp", ha="center", va="bottom", color=color, fontproperties=ZH_FONT, fontsize=9)

    legend = axes[0].legend(frameon=False, loc="upper right")
    for text in legend.get_texts():
        text.set_fontproperties(ZH_FONT)
    fig.suptitle("按题型观察查询优化对命中率的影响", fontproperties=ZH_FONT, fontsize=17, color=TEXT, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(OUTPUT_DIR / "fig10_hit_by_question_type.png", dpi=240)
    plt.close(fig)


def plot_question_type_delta(data: dict[str, dict[str, dict]]) -> None:
    before = data["主测试集"]["without"]["manual"]["by_question_type"]
    after = data["主测试集"]["with"]["manual"]["by_question_type"]
    question_types = [
        qtype
        for qtype, values in after.items()
        if int(values.get("count", 0)) >= 3
    ]
    metrics = [
        ("avg_correctness", "正确性"),
        ("avg_completeness", "完整性"),
        ("avg_faithfulness", "忠实性"),
        ("avg_retrieval_relevance", "检索相关性"),
    ]
    matrix = np.array(
        [
            [float(after[q][field]) - float(before[q][field]) for field, _ in metrics]
            for q in question_types
        ]
    )

    fig, ax = plt.subplots(figsize=(9.8, 5.8))
    vmax = max(0.35, float(np.abs(matrix).max()))
    norm = mcolors.TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
    im = ax.imshow(matrix, cmap="RdBu_r", norm=norm, aspect="auto")

    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            val = matrix[i, j]
            color = "white" if abs(val) > vmax * 0.55 else TEXT
            ax.text(j, i, f"{val:+.2f}", ha="center", va="center", color=color, fontproperties=ZH_FONT, fontsize=10)

    ax.set_xticks(np.arange(len(metrics)))
    ax.set_xticklabels([label for _, label in metrics], rotation=0)
    ax.set_yticks(np.arange(len(question_types)))
    ax.set_yticklabels(question_types)
    set_axis_fonts(ax)
    ax.set_title("主测试集中不同题型的人工评分增益分布", fontproperties=ZH_FONT, fontsize=17, color=TEXT, pad=12)
    cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.04)
    cbar.ax.tick_params(labelsize=9, colors=TEXT)
    for label in cbar.ax.get_yticklabels():
        label.set_fontproperties(ZH_FONT)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig05_question_type_delta_main.png", dpi=240)
    plt.close(fig)


def write_metrics_csv(data: dict[str, dict[str, dict]]) -> None:
    rows: list[dict[str, str | float]] = []
    for scene in data:
        before_summary = data[scene]["without"]["summary"]
        after_summary = data[scene]["with"]["summary"]
        before_manual = data[scene]["without"]["manual"]
        after_manual = data[scene]["with"]["manual"]
        rows.extend(
            [
                {
                    "scene": scene,
                    "metric": "target_hit_rate",
                    "before": before_summary["target_hit_rate"],
                    "after": after_summary["target_hit_rate"],
                    "delta": after_summary["target_hit_rate"] - before_summary["target_hit_rate"],
                },
                {
                    "scene": scene,
                    "metric": "avg_unique_source_count",
                    "before": before_summary["avg_unique_source_count"],
                    "after": after_summary["avg_unique_source_count"],
                    "delta": after_summary["avg_unique_source_count"] - before_summary["avg_unique_source_count"],
                },
                {
                    "scene": scene,
                    "metric": "avg_first_token_seconds",
                    "before": before_summary["avg_first_token_seconds"],
                    "after": after_summary["avg_first_token_seconds"],
                    "delta": after_summary["avg_first_token_seconds"] - before_summary["avg_first_token_seconds"],
                },
                {
                    "scene": scene,
                    "metric": "refusal_success_rate",
                    "before": before_summary["refusal_success_rate"],
                    "after": after_summary["refusal_success_rate"],
                    "delta": after_summary["refusal_success_rate"] - before_summary["refusal_success_rate"],
                },
                {
                    "scene": scene,
                    "metric": "avg_correctness",
                    "before": before_manual["avg_correctness"],
                    "after": after_manual["avg_correctness"],
                    "delta": after_manual["avg_correctness"] - before_manual["avg_correctness"],
                },
                {
                    "scene": scene,
                    "metric": "avg_completeness",
                    "before": before_manual["avg_completeness"],
                    "after": after_manual["avg_completeness"],
                    "delta": after_manual["avg_completeness"] - before_manual["avg_completeness"],
                },
                {
                    "scene": scene,
                    "metric": "avg_faithfulness",
                    "before": before_manual["avg_faithfulness"],
                    "after": after_manual["avg_faithfulness"],
                    "delta": after_manual["avg_faithfulness"] - before_manual["avg_faithfulness"],
                },
                {
                    "scene": scene,
                    "metric": "avg_retrieval_relevance",
                    "before": before_manual["avg_retrieval_relevance"],
                    "after": after_manual["avg_retrieval_relevance"],
                    "delta": after_manual["avg_retrieval_relevance"] - before_manual["avg_retrieval_relevance"],
                },
            ]
        )

    out_path = OUTPUT_DIR / "query_optimization_metrics.csv"
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["scene", "metric", "before", "after", "delta"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ensure_output_dir(OUTPUT_DIR)
    data = load_scene_data()
    plot_overall_tradeoff(data)
    plot_manual_quality(data)
    plot_latency_breakdown(data)
    plot_refusal_matrices(data)
    plot_first_token_boxplot(data)
    plot_hit_by_question_type(data)
    plot_question_type_delta(data)
    write_metrics_csv(data)
    print(f"[OK] 查询优化实验图表已生成到: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
