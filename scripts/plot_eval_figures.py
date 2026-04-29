from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib import rcParams
from matplotlib.font_manager import FontProperties


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SUMMARY = PROJECT_ROOT / "runs" / "eval" / "20260429_173324" / "summary.json"
DEFAULT_RESULTS = PROJECT_ROOT / "runs" / "eval" / "20260429_173324" / "results.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "runs" / "figures"


def load_results(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _load_zh_font() -> FontProperties:
    font_path = PROJECT_ROOT / "assets" / "fonts" / "SourceHanSansSC-Regular.otf"
    if font_path.exists():
        return FontProperties(fname=str(font_path))
    return FontProperties(family="DejaVu Sans")


rcParams["axes.unicode_minus"] = False
rcParams["figure.facecolor"] = "white"
rcParams["axes.facecolor"] = "white"
ZH_FONT = _load_zh_font()

PRIMARY = "#1f3a5f"
SECONDARY = "#4e79a7"
ACCENT = "#f28e2b"
ACCENT_RED = "#e15759"
GRID = "#d8dee9"
TEXT = "#1f2937"


def apply_axis_style(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#b8c2cc")
    ax.spines["bottom"].set_color("#b8c2cc")
    ax.tick_params(axis="both", colors=TEXT, labelsize=10)
    ax.grid(axis="x", linestyle="--", linewidth=0.6, color=GRID, alpha=0.8)
    ax.set_axisbelow(True)


def set_axis_fonts(ax) -> None:
    for label in ax.get_xticklabels():
        label.set_fontproperties(ZH_FONT)
    for label in ax.get_yticklabels():
        label.set_fontproperties(ZH_FONT)


def load_summary(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def format_seconds_label(value: float) -> str:
    if value <= 0.05:
        return "<0.01s"
    return f"{value:.2f}s"


def plot_section_distribution(summary: dict, output_dir: Path) -> None:
    mapping = {
        "rfc_questions": "RFC 标准题",
        "refusal_questions": "保守回答题",
        "sut_demo_questions": "SUT 演示题",
    }
    data = summary.get("section_distribution", {})
    labels = [mapping.get(key, key) for key in data.keys()]
    values = list(data.values())
    colors = [PRIMARY, ACCENT, SECONDARY]

    fig, ax = plt.subplots(figsize=(7, 7))
    wedges, texts = ax.pie(
        values,
        startangle=90,
        colors=colors[: len(values)],
        wedgeprops={"width": 0.42, "edgecolor": "white"},
    )
    total = sum(values)
    centre_text = f"总题数\n{total}"
    ax.text(0, 0, centre_text, ha="center", va="center", fontproperties=ZH_FONT, fontsize=18, color=TEXT)
    legend = ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False)
    for text in legend.get_texts():
        text.set_fontproperties(ZH_FONT)
    ax.set_title("测试问题集总体构成", fontproperties=ZH_FONT, fontsize=16, color=TEXT)
    fig.tight_layout()
    fig.savefig(output_dir / "fig01_section_distribution.png", dpi=220)
    plt.close(fig)


def plot_protocol_distribution(summary: dict, output_dir: Path) -> None:
    data = summary.get("protocol_distribution", {})
    items = sorted(data.items(), key=lambda x: x[1], reverse=True)
    labels = [k for k, _ in items]
    values = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(labels, values, color=SECONDARY)
    ax.set_title("测试问题集在不同协议类别上的分布", fontproperties=ZH_FONT, fontsize=16, color=TEXT)
    ax.set_xlabel("题目数量", fontproperties=ZH_FONT, color=TEXT)
    apply_axis_style(ax)
    set_axis_fonts(ax)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(output_dir / "fig02_protocol_distribution.png", dpi=220)
    plt.close(fig)


def plot_question_type_distribution(summary: dict, output_dir: Path) -> None:
    data = summary.get("question_type_distribution", {})
    items = sorted(data.items(), key=lambda x: x[1], reverse=True)
    labels = [k for k, _ in items]
    values = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(labels, values, color=PRIMARY)
    ax.set_title("测试问题集在不同题型上的分布", fontproperties=ZH_FONT, fontsize=16, color=TEXT)
    ax.set_xlabel("题目数量", fontproperties=ZH_FONT, color=TEXT)
    apply_axis_style(ax)
    set_axis_fonts(ax)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(output_dir / "fig04_question_type_distribution.png", dpi=220)
    plt.close(fig)


def plot_timing_composition(summary: dict, output_dir: Path) -> None:
    first_token = float(summary.get("avg_first_token_seconds", 0.0))
    total = float(summary.get("avg_total_seconds", 0.0))

    stages = [
        ("加载配置", float(summary.get("avg_load_settings_seconds", 0.0)), "#6c8ebf"),
        ("查询改写", float(summary.get("avg_rewrite_seconds", 0.0)), SECONDARY),
        ("初始化检索器", float(summary.get("avg_init_retriever_seconds", 0.0)), "#7fb069"),
        ("向量检索", float(summary.get("avg_retrieve_seconds", 0.0)), PRIMARY),
        ("初始化大模型", float(summary.get("avg_init_llm_seconds", 0.0)), "#9c89b8"),
        ("生成最终回答", float(summary.get("avg_generate_answer_seconds", 0.0)), ACCENT),
    ]

    known = sum(value for _, value, _ in stages)
    other = max(total - known, 0.0)
    if other > 0:
        stages.append(("其他开销", other, "#9aa5b1"))

    fig, ax = plt.subplots(figsize=(7.8, 10.8))
    x = 0.32
    width = 0.12
    bottom = 0.0
    centers: list[tuple[str, float, str, float]] = []

    for label, value, color in stages:
        ax.bar([x], [value], bottom=[bottom], width=width, color=color, edgecolor="white", linewidth=1.0)
        centers.append((label, bottom + value / 2, color, value))
        bottom += value

    ax.vlines(x, 0, total, colors="#6b7280", linewidth=1.0, alpha=0.45)

    for label, center_y, color, value in centers:
        ax.scatter([x], [center_y], color="white", s=24, zorder=3, edgecolors=color, linewidths=1.1)
        ax.plot([x + 0.07, x + 0.17], [center_y, center_y], color=color, linewidth=1.1)
        ax.text(
            x + 0.19,
            center_y,
            f"{label}\n阶段耗时 {format_seconds_label(value)}",
            va="center",
            ha="left",
            color=TEXT,
            fontproperties=ZH_FONT,
            fontsize=10.2,
        )

    ax.hlines(first_token, x - 0.11, x + 0.11, colors=ACCENT_RED, linestyles="--", linewidth=2.6, path_effects=[pe.Stroke(linewidth=4.2, foreground="white"), pe.Normal()])
    first_token_text = ax.text(
        x + 0.29,
        first_token,
        f"首字响应时间\n累计 {format_seconds_label(first_token)}",
        va="center",
        ha="left",
        color=ACCENT_RED,
        fontproperties=ZH_FONT,
        fontsize=12.8,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": ACCENT_RED, "linewidth": 1.6},
    )
    first_token_text.set_path_effects([pe.Stroke(linewidth=2.0, foreground="white"), pe.Normal()])
    ax.annotate(
        "",
        xy=(x + 0.11, first_token),
        xytext=(x + 0.27, first_token),
        arrowprops={"arrowstyle": "->", "color": ACCENT_RED, "lw": 1.8},
    )

    ax.annotate(
        f"总耗时\n累计 {format_seconds_label(total)}",
        xy=(x, total),
        xytext=(x + 0.24, total + max(total * 0.04, 0.18)),
        color=TEXT,
        fontproperties=ZH_FONT,
        fontsize=11.5,
        ha="left",
        va="bottom",
        arrowprops={"arrowstyle": "->", "color": TEXT, "lw": 1.2},
    )

    ax.set_title("问答流程平均耗时阶段时间轴", fontproperties=ZH_FONT, fontsize=16, color=TEXT)
    ax.set_ylabel("秒", fontproperties=ZH_FONT, color=TEXT)
    ax.set_xlim(0.04, 1.02)
    ax.set_ylim(0, total * 1.18 if total > 0 else 1)
    ax.set_xticks([])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_color("#b8c2cc")
    ax.tick_params(axis="y", colors=TEXT, labelsize=10)
    ax.grid(axis="y", linestyle="--", linewidth=0.6, color=GRID, alpha=0.7)
    set_axis_fonts(ax)
    fig.tight_layout()
    fig.savefig(output_dir / "fig03_timing_timeline.png", dpi=220)
    plt.close(fig)


def plot_protocol_hit_rate(summary: dict, output_dir: Path) -> None:
    data = summary.get("by_protocol", {})
    items = sorted(data.items(), key=lambda x: x[1].get("target_hit_rate", 0.0), reverse=True)
    labels = [k for k, _ in items]
    values = [float(v.get("target_hit_rate", 0.0)) for _, v in items]

    fig, ax = plt.subplots(figsize=(10, 6))
    y_positions = list(range(len(labels)))
    ax.hlines(y_positions, [0] * len(values), values, color=SECONDARY, linewidth=2.4)
    ax.plot(values, y_positions, "o", color=ACCENT, markersize=8)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, 1.05)
    ax.set_title("不同协议类别的目标文档命中率", fontproperties=ZH_FONT, fontsize=16, color=TEXT)
    ax.set_xlabel("命中率", fontproperties=ZH_FONT, color=TEXT)
    apply_axis_style(ax)
    set_axis_fonts(ax)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(output_dir / "fig06_protocol_hit_rate.png", dpi=220)
    plt.close(fig)


def plot_protocol_avg_total_time(summary: dict, output_dir: Path) -> None:
    data = summary.get("by_protocol", {})
    items = sorted(data.items(), key=lambda x: x[1].get("avg_total_seconds", 0.0), reverse=True)
    labels = [k for k, _ in items]
    values = [float(v.get("avg_total_seconds", 0.0)) for _, v in items]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(labels, values, color=PRIMARY)
    ax.set_title("不同协议类别的平均总耗时", fontproperties=ZH_FONT, fontsize=16, color=TEXT)
    ax.set_xlabel("秒", fontproperties=ZH_FONT, color=TEXT)
    apply_axis_style(ax)
    set_axis_fonts(ax)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(output_dir / "fig07_protocol_avg_total_time.png", dpi=220)
    plt.close(fig)


def plot_refusal_summary(results: list[dict], output_dir: Path) -> None:
    tp = sum(1 for row in results if row.get("should_refuse") and row.get("refused"))
    fn = sum(1 for row in results if row.get("should_refuse") and not row.get("refused"))
    fp = sum(1 for row in results if not row.get("should_refuse") and row.get("refused"))
    tn = sum(1 for row in results if not row.get("should_refuse") and not row.get("refused"))

    matrix = [[tp, fn], [fp, tn]]
    row_labels = ["应保守回答", "不应保守回答"]
    col_labels = ["系统保守回答", "系统正常回答"]

    fig, ax = plt.subplots(figsize=(7.2, 6.4))
    im = ax.imshow(matrix, cmap="Blues")

    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(col_labels, fontproperties=ZH_FONT)
    ax.set_yticklabels(row_labels, fontproperties=ZH_FONT)
    ax.set_title("系统保守回答行为混淆矩阵", fontproperties=ZH_FONT, fontsize=16, color=TEXT)

    for i in range(2):
        for j in range(2):
            value = matrix[i][j]
            ax.text(j, i, str(value), ha="center", va="center", color="white" if value > max(tp, fn, fp, tn) / 2 else TEXT, fontproperties=ZH_FONT, fontsize=16)

    ax.set_xlabel("系统输出", fontproperties=ZH_FONT, color=TEXT)
    ax.set_ylabel("题目真实要求", fontproperties=ZH_FONT, color=TEXT, labelpad=8)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.subplots_adjust(left=0.20, bottom=0.12, right=0.88, top=0.90)
    fig.savefig(output_dir / "fig08_refusal_confusion_matrix.png", dpi=220)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate paper-ready experiment figures from evaluation summary")
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    summary = load_summary(args.summary)
    results = load_results(args.results)
    ensure_output_dir(args.output_dir)

    plot_section_distribution(summary, args.output_dir)
    plot_protocol_distribution(summary, args.output_dir)
    plot_timing_composition(summary, args.output_dir)
    plot_question_type_distribution(summary, args.output_dir)
    plot_protocol_hit_rate(summary, args.output_dir)
    plot_protocol_avg_total_time(summary, args.output_dir)
    plot_refusal_summary(results, args.output_dir)

    print(f"[OK] 论文版图表已生成到: {args.output_dir}")


if __name__ == "__main__":
    main()
