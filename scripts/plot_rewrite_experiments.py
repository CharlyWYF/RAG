from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import rcParams
from matplotlib.font_manager import FontProperties

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EVAL_ROOT = PROJECT_ROOT / "runs" / "eval"
OUTPUT_DIR = PROJECT_ROOT / "runs" / "figures" / "final_experiments"

GROUPS = {
    "Main Test Set": {
        "No Rewrite": EVAL_ROOT / "20260430_172612_without_rewrite",
        "With Rewrite": EVAL_ROOT / "20260430_230707_with_rewrite",
    },
    "Conversational Subset": {
        "No Rewrite": EVAL_ROOT / "20260501_000136_conversational_without_rewrite",
        "With Rewrite": EVAL_ROOT / "20260501_002532_conversational_with_rewrite",
    },
}


def _load_zh_font() -> FontProperties:
    return FontProperties(family="Times New Roman")


rcParams["axes.unicode_minus"] = False
rcParams["figure.facecolor"] = "white"
rcParams["axes.facecolor"] = "white"
ZH_FONT = _load_zh_font()
ZH_FONT_BOLD = FontProperties(family="Times New Roman", weight="bold")

PRIMARY = "#1f3a5f"
SECONDARY = "#4e79a7"
ACCENT = "#f28e2b"
ACCENT_RED = "#e15759"
GRID = "#d8dee9"
TEXT = "#1f2937"


def apply_axis_style(ax, grid_axis: str = "y") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#b8c2cc")
    ax.spines["bottom"].set_color("#b8c2cc")
    ax.tick_params(axis="both", colors=TEXT, labelsize=10)
    ax.grid(axis=grid_axis, linestyle="--", linewidth=0.6, color=GRID, alpha=0.8)
    ax.set_axisbelow(True)


def set_axis_fonts(ax) -> None:
    for label in ax.get_xticklabels():
        label.set_fontproperties(ZH_FONT)
    for label in ax.get_yticklabels():
        label.set_fontproperties(ZH_FONT)


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_group_data() -> dict[str, dict[str, dict[str, dict]]]:
    data: dict[str, dict[str, dict[str, dict]]] = {}
    for scene, variants in GROUPS.items():
        data[scene] = {}
        for variant, path in variants.items():
            auto = json.loads((path / "summary.json").read_text(encoding="utf-8"))
            manual = json.loads((path / "manual_scoring_summary.json").read_text(encoding="utf-8"))
            data[scene][variant] = {"auto": auto, "manual": manual}
    return data


def plot_scene_hit_and_source(data: dict[str, dict[str, dict[str, dict]]]) -> None:
    scenes = list(data.keys())
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.8), sharey=False)

    for ax, scene in zip(axes, scenes):
        variants = ["No Rewrite", "With Rewrite"]
        hit_rates = [float(data[scene][v]["auto"]["target_hit_rate"]) for v in variants]
        source_counts = [float(data[scene][v]["auto"]["avg_unique_source_count"]) for v in variants]
        x = range(len(variants))
        bars = ax.bar(x, hit_rates, color=[SECONDARY, PRIMARY], width=0.56)
        ax.set_title(scene, fontweight='bold', fontproperties=ZH_FONT_BOLD, fontsize=15, color=TEXT)
        ax.set_xticks(list(x))
        ax.set_xticklabels(variants)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("Target Hit Rate", fontproperties=ZH_FONT, color=TEXT)
        apply_axis_style(ax, grid_axis="y")
        set_axis_fonts(ax)

        ax2 = ax.twinx()
        ax2.plot(list(x), source_counts, color=ACCENT, marker="o", linewidth=2.0)
        ax2.set_ylabel("Avg Unique Source Count", fontproperties=ZH_FONT, color=TEXT)
        ax2.tick_params(axis="y", colors=TEXT)
        for label in ax2.get_yticklabels():
            label.set_fontproperties(ZH_FONT)

        for bar, value in zip(bars, hit_rates):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 0.015, f"{value:.2f}", ha="center", va="bottom", color=TEXT, fontproperties=ZH_FONT)
        for idx, value in enumerate(source_counts):
            ax2.text(idx, value + 0.04, f"{value:.2f}", color=ACCENT, ha="center", va="bottom", fontproperties=ZH_FONT)

    fig.suptitle("Query Rewrite Impact on Hit Rate and Source Coverage", fontweight='bold', fontproperties=ZH_FONT_BOLD, fontsize=17, color=TEXT)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUTPUT_DIR / "exp01_scene_hit_and_source.png", dpi=240)
    fig.savefig(OUTPUT_DIR / "exp01_scene_hit_and_source.svg", dpi=240)
    plt.close(fig)


def plot_scene_quality(data: dict[str, dict[str, dict[str, dict]]]) -> None:
    scenes = list(data.keys())
    metrics = [
        ("Correctness", "avg_correctness", PRIMARY),
        ("Completeness", "avg_completeness", ACCENT),
        ("Faithfulness", "avg_faithfulness", SECONDARY),
        ("Retrieval Relevance", "avg_retrieval_relevance", ACCENT_RED),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    for ax, (title, field, color) in zip(axes.flat, metrics):
        x = range(len(scenes))
        width = 0.32
        baseline = [float(data[s]["No Rewrite"]["manual"][field]) for s in scenes]
        rewrite = [float(data[s]["With Rewrite"]["manual"][field]) for s in scenes]
        ax.bar([i - width / 2 for i in x], baseline, width=width, color=SECONDARY, label="No Rewrite")
        ax.bar([i + width / 2 for i in x], rewrite, width=width, color=color, label="With Rewrite")
        ax.set_title(title, fontweight='bold', fontproperties=ZH_FONT_BOLD, fontsize=14, color=TEXT)
        ax.set_xticks(list(x))
        ax.set_xticklabels(scenes)
        ax.set_ylim(0, 2.1)
        apply_axis_style(ax, grid_axis="y")
        set_axis_fonts(ax)
    legend = axes[0, 0].legend(frameon=False, loc="lower right")
    for text in legend.get_texts():
        text.set_fontproperties(ZH_FONT)
    fig.suptitle("Query Rewrite Impact on Manual Scores", fontweight='bold', fontproperties=ZH_FONT_BOLD, fontsize=17, color=TEXT)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(OUTPUT_DIR / "exp02_scene_quality.png", dpi=240)
    fig.savefig(OUTPUT_DIR / "exp02_scene_quality.svg", dpi=240)
    plt.close(fig)


def plot_scene_timing_and_refusal(data: dict[str, dict[str, dict[str, dict]]]) -> None:
    scenes = list(data.keys())
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.8))

    for ax, scene in zip(axes, scenes):
        variants = ["No Rewrite", "With Rewrite"]
        total = [float(data[scene][v]["auto"]["avg_total_seconds"]) for v in variants]
        first_token = [float(data[scene][v]["auto"]["avg_first_token_seconds"]) for v in variants]
        x = range(len(variants))
        width = 0.32
        ax.bar([i - width / 2 for i in x], total, width=width, color=PRIMARY, label="Avg Total Time")
        ax.bar([i + width / 2 for i in x], first_token, width=width, color=ACCENT, label="Avg First Token Latency")
        ax.set_title(scene, fontweight='bold', fontproperties=ZH_FONT_BOLD, fontsize=15, color=TEXT)
        ax.set_xticks(list(x))
        ax.set_xticklabels(variants)
        ax.set_ylabel("Seconds", fontproperties=ZH_FONT, color=TEXT)
        apply_axis_style(ax, grid_axis="y")
        set_axis_fonts(ax)
    legend = axes[0].legend(frameon=False, loc="upper left")
    for text in legend.get_texts():
        text.set_fontproperties(ZH_FONT)
    fig.suptitle("Latency Cost of Query Rewrite", fontweight='bold', fontproperties=ZH_FONT_BOLD, fontsize=17, color=TEXT)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUTPUT_DIR / "exp03_scene_timing.png", dpi=240)
    fig.savefig(OUTPUT_DIR / "exp03_scene_timing.svg", dpi=240)
    plt.close(fig)


def plot_refusal_summary(data: dict[str, dict[str, dict[str, dict]]]) -> None:
    scenes = list(data.keys())
    fig, ax = plt.subplots(figsize=(9, 5.6))
    x = range(len(scenes))
    width = 0.32
    baseline = [float(data[s]["No Rewrite"]["auto"]["refusal_success_rate"]) for s in scenes]
    rewrite = [float(data[s]["With Rewrite"]["auto"]["refusal_success_rate"]) for s in scenes]
    ax.bar([i - width / 2 for i in x], baseline, width=width, color=SECONDARY, label="No Rewrite")
    ax.bar([i + width / 2 for i in x], rewrite, width=width, color=ACCENT_RED, label="With Rewrite")
    ax.set_xticks(list(x))
    ax.set_xticklabels(scenes)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Refusal Success Rate", fontproperties=ZH_FONT, color=TEXT)
    ax.set_title("Query Rewrite Impact on Refusal Capability", fontweight='bold', fontproperties=ZH_FONT_BOLD, fontsize=16, color=TEXT)
    apply_axis_style(ax, grid_axis="y")
    set_axis_fonts(ax)
    legend = ax.legend(frameon=False, loc="upper right")
    for text in legend.get_texts():
        text.set_fontproperties(ZH_FONT)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "exp04_refusal_summary.png", dpi=240)
    fig.savefig(OUTPUT_DIR / "exp04_refusal_summary.svg", dpi=240)
    plt.close(fig)


def main() -> None:
    ensure_output_dir(OUTPUT_DIR)
    data = load_group_data()
    plot_scene_hit_and_source(data)
    plot_scene_quality(data)
    plot_scene_timing_and_refusal(data)
    plot_refusal_summary(data)
    print(f"[OK] 查询改写正式实验组合图表已生成到: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
