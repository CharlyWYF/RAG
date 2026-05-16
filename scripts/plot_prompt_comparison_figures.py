from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import numpy as np
from matplotlib import rcParams
from matplotlib.font_manager import FontProperties


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "runs" / "figures" / "prompt_comparison"
FONT_PATH = PROJECT_ROOT / "assets" / "fonts" / "SourceHanSansSC-Regular.otf"

RUN_CONFIGS = [
    ("20260507_094531_prompt_v1", "prompt_v1"),
    ("20260430_230707_with_rewrite", "prompt_v2"),
]

PALETTE = {
    "prompt_v1": "#F2A65A",
    "prompt_v2": "#2A9D8F",
}
TEXT = "#243447"
GRID = "#D8E1E8"
BG = "#FBFCFE"
ACCENT_RED = "#D1495B"
ACCENT_GOLD = "#E9C46A"
ACCENT_BLUE = "#4E79A7"

CATEGORY_EN = {
    "机制类": "Mechanism",
    "定义类": "Definition",
    "对比类": "Comparison",
    "综合类": "Comprehensive",
    "证据不足类": "Insufficient Evidence",
    "字段类": "Field",
    "安全类": "Security",
    "私有协议类": "Private Protocol",
    "规则类": "Rule",
    "综合": "Cross-Protocol",
}


@dataclass
class RunMetrics:
    run_dir: str
    label: str
    auto_summary: dict
    manual_summary: dict
    auto_rows: list[dict[str, str]]
    manual_rows: list[dict[str, str]]

    @property
    def correctness(self) -> float:
        return float(self.manual_summary["avg_correctness"])

    @property
    def completeness(self) -> float:
        return float(self.manual_summary["avg_completeness"])

    @property
    def faithfulness(self) -> float:
        return float(self.manual_summary["avg_faithfulness"])

    @property
    def relevance(self) -> float:
        return float(self.manual_summary["avg_retrieval_relevance"])

    @property
    def refusal_success_rate(self) -> float:
        return float(self.auto_summary["refusal_success_rate"])

    @property
    def target_hit_rate(self) -> float:
        return float(self.auto_summary["target_hit_rate"])

    @property
    def avg_total_seconds(self) -> float:
        return float(self.auto_summary["avg_total_seconds"])

    @property
    def avg_first_token_seconds(self) -> float:
        return float(self.auto_summary["avg_first_token_seconds"])

    @property
    def answerable_only_completeness(self) -> float:
        kept = [
            row for row in self.manual_rows
            if self._row_by_id(row["id"]).get("refused", "").strip() != "True"
        ]
        return _avg(kept, "completeness_score")

    @property
    def refused_count(self) -> int:
        return sum(1 for row in self.auto_rows if row.get("refused", "").strip() == "True")

    @property
    def confusion_counts(self) -> tuple[int, int, int, int]:
        tp = fp = fn = tn = 0
        for row in self.auto_rows:
            should_refuse = row.get("should_refuse", "").strip() == "True"
            refused = row.get("refused", "").strip() == "True"
            if should_refuse and refused:
                tp += 1
            elif should_refuse and not refused:
                fn += 1
            elif not should_refuse and refused:
                fp += 1
            else:
                tn += 1
        return tp, fp, fn, tn

    def _row_by_id(self, row_id: str) -> dict[str, str]:
        for row in self.auto_rows:
            if row.get("id") == row_id:
                return row
        raise KeyError(row_id)


def _avg(rows: list[dict[str, str]], key: str) -> float:
    if not rows:
        return 0.0
    return sum(float(row.get(key, 0) or 0) for row in rows) / len(rows)


def _load_font() -> FontProperties:
    font_path = FONT_PATH
    if font_path.exists():
        return FontProperties(fname=str(font_path))
    return FontProperties(family="DejaVu Sans")


EN_FONT = _load_font()
rcParams["axes.unicode_minus"] = False
rcParams["figure.facecolor"] = BG
rcParams["axes.facecolor"] = BG
rcParams["savefig.facecolor"] = BG


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_run_metrics(run_dir: str, label: str) -> RunMetrics:
    base = PROJECT_ROOT / "runs" / "eval" / run_dir
    return RunMetrics(
        run_dir=run_dir,
        label=label,
        auto_summary=load_json(base / "summary.json"),
        manual_summary=load_json(base / "manual_scoring_summary.json"),
        auto_rows=load_csv(base / "results.csv"),
        manual_rows=load_csv(base / "manual_scoring_draft.csv"),
    )


def style_axis(ax, grid_axis: str = "y") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#B9C6D2")
    ax.spines["bottom"].set_color("#B9C6D2")
    ax.tick_params(colors=TEXT, labelsize=10)
    ax.grid(axis=grid_axis, color=GRID, linestyle="--", linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)
    for label in ax.get_xticklabels():
        label.set_fontproperties(EN_FONT)
    for label in ax.get_yticklabels():
        label.set_fontproperties(EN_FONT)


def annotate_bar_values(ax, bars, formatter="{:.2f}", dy=0.03, color=TEXT) -> None:
    ymax = ax.get_ylim()[1]
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + ymax * dy,
            formatter.format(height),
            ha="center",
            va="bottom",
            fontproperties=EN_FONT,
            fontsize=10,
            color=color,
        )


def plot_manual_score_overview(runs: list[RunMetrics], output_dir: Path) -> None:
    metrics = [
        ("correctness", "Correctness"),
        ("completeness", "Completeness"),
        ("faithfulness", "Faithfulness"),
        ("relevance", "Retrieval Relevance"),
    ]
    x = np.arange(len(metrics))
    width = 0.22

    fig, ax = plt.subplots(figsize=(11.8, 5.9))
    offsets = [(idx - (len(runs) - 1) / 2) * width for idx in range(len(runs))]
    values_by_run: list[list[float]] = []
    for idx, run in enumerate(runs):
        values = [getattr(run, name) for name, _ in metrics]
        values_by_run.append(values)
        bars = ax.bar(
            x + offsets[idx],
            values,
            width=width,
            color=PALETTE[run.label],
            edgecolor="white",
            linewidth=1.0,
            label=run.label,
        )
        annotate_bar_values(ax, bars)

    ax.set_xticks(x)
    ax.set_xticklabels([label for _, label in metrics], fontproperties=EN_FONT, fontsize=11)
    ax.set_ylim(0, 2.32)
    ax.set_ylabel("Average Manual Score (0-2)", fontproperties=EN_FONT, fontsize=11, color=TEXT)
    ax.set_title("Manual Score Comparison: prompt_v1 vs prompt_v2", fontproperties=EN_FONT, fontsize=16, color=TEXT, pad=14)
    style_axis(ax)

    if len(runs) == 2:
        base_values = values_by_run[0]
        improved_values = values_by_run[1]
        for idx, (base_v, new_v) in enumerate(zip(base_values, improved_values)):
            rel_delta = ((new_v - base_v) / base_v * 100) if base_v else 0.0
            delta_color = "#2A9D8F" if rel_delta >= 0 else "#D1495B"
            label = f"{rel_delta:+.1f}%"
            ax.text(
                x[idx],
                max(base_v, new_v) + 0.16,
                label,
                ha="center",
                va="bottom",
                fontproperties=EN_FONT,
                fontsize=10.5,
                color=delta_color,
                bbox={"boxstyle": "round,pad=0.2", "facecolor": "white", "edgecolor": delta_color, "linewidth": 1.0},
            )

    legend = ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.04), ncol=2)
    for text in legend.get_texts():
        text.set_fontproperties(EN_FONT)

    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(output_dir / "fig01_manual_score_overview.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_refusal_confusion(runs: list[RunMetrics], output_dir: Path) -> None:
    labels = [run.label for run in runs]
    tp = np.array([run.confusion_counts[0] for run in runs])
    fp = np.array([run.confusion_counts[1] for run in runs])
    fn = np.array([run.confusion_counts[2] for run in runs])
    tn = np.array([run.confusion_counts[3] for run in runs])

    fig, ax = plt.subplots(figsize=(11.8, 5.8))
    y = np.arange(len(labels))
    ax.barh(y, tp, color="#2A9D8F", edgecolor="white", height=0.55, label="Correct Refusal (TP)")
    ax.barh(y, fn, left=tp, color="#F4A261", edgecolor="white", height=0.55, label="Missed Refusal (FN)")
    ax.barh(y, fp, left=tp + fn, color="#E76F51", edgecolor="white", height=0.55, label="False Refusal (FP)")
    ax.barh(y, tn, left=tp + fn + fp, color="#B8C5D6", edgecolor="white", height=0.55, label="Correct Answer (TN)")

    for idx, run in enumerate(runs):
        success = run.refusal_success_rate * 100
        ax.text(
            67.1,
            idx,
            f"Refusal Rate {success:.0f}%",
            va="center",
            ha="right",
            fontproperties=EN_FONT,
            fontsize=10.5,
            color=TEXT,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#D7E0E7"},
        )

    ax.set_xlim(0, 68)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontproperties=EN_FONT, fontsize=11)
    ax.set_xlabel("Number of Questions (66 total)", fontproperties=EN_FONT, fontsize=11, color=TEXT)
    ax.set_title("Refusal Behavior Comparison: prompt_v1 vs prompt_v2", fontproperties=EN_FONT, fontsize=16, color=TEXT)
    style_axis(ax, grid_axis="x")
    ax.invert_yaxis()
    legend = ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.2), ncol=4)
    for text in legend.get_texts():
        text.set_fontproperties(EN_FONT)

    fig.tight_layout()
    fig.savefig(output_dir / "fig02_refusal_confusion_comparison.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_refusal_confusion_matrix(runs: list[RunMetrics], output_dir: Path) -> None:
    fig, axes = plt.subplots(1, len(runs), figsize=(10.8, 4.9), constrained_layout=False)
    if len(runs) == 1:
        axes = [axes]

    for ax, run in zip(axes, runs):
        tp, fp, fn, tn = run.confusion_counts
        matrix = np.array([
            [tp, fn],
            [fp, tn],
        ], dtype=float)

        im = ax.imshow(matrix, cmap="YlGnBu", vmin=0, vmax=max(1, matrix.max()))

        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["System Refused", "System Answered"], fontproperties=EN_FONT, fontsize=10)
        ax.set_yticklabels(["Should Refuse", "Should Not Refuse"], fontproperties=EN_FONT, fontsize=10)
        ax.set_title(run.label, fontproperties=EN_FONT, fontsize=14, color=TEXT, pad=10)

        total = matrix.sum()
        for i in range(2):
            for j in range(2):
                count = int(matrix[i, j])
                ratio = count / total * 100 if total else 0.0
                text_color = "white" if matrix[i, j] > matrix.max() * 0.55 else TEXT
                ax.text(
                    j,
                    i,
                    f"{count}\n{ratio:.1f}%",
                    ha="center",
                    va="center",
                    fontproperties=EN_FONT,
                    fontsize=11,
                    color=text_color,
                )

        for spine in ax.spines.values():
            spine.set_edgecolor("#B9C6D2")
            spine.set_linewidth(1.0)

        ax.tick_params(length=0)

        success = run.refusal_success_rate * 100
        ax.text(
            0.5,
            -0.18,
            f"Refusal Rate: {success:.0f}%",
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontproperties=EN_FONT,
            fontsize=10.5,
            color=TEXT,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#D7E0E7"},
        )

    fig.subplots_adjust(left=0.08, right=0.86, bottom=0.18, top=0.82, wspace=0.32)
    cax = fig.add_axes([0.89, 0.22, 0.025, 0.56])
    cbar = fig.colorbar(im, cax=cax)
    cbar.ax.tick_params(labelsize=9, colors=TEXT)
    fig.suptitle("Refusal Confusion Matrix Comparison: prompt_v1 vs prompt_v2", fontproperties=EN_FONT, fontsize=16, color=TEXT, y=0.98)
    fig.savefig(output_dir / "fig02_refusal_confusion_matrix.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_capability_profile(runs: list[RunMetrics], output_dir: Path) -> None:
    labels = ["Correctness", "Refusal Capability", "Response Efficiency"]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fastest = min(run.avg_first_token_seconds for run in runs)

    fig = plt.figure(figsize=(10.2, 6.8))
    ax = plt.subplot(111, polar=True)
    ax.set_facecolor(BG)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontproperties=EN_FONT, fontsize=12, color=TEXT)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], fontproperties=EN_FONT, fontsize=9, color="#6B7C8E")
    ax.yaxis.grid(True, linestyle="--", linewidth=0.8, color=GRID)
    ax.xaxis.grid(True, linestyle="--", linewidth=0.8, color=GRID)
    ax.spines["polar"].set_color("#B9C6D2")

    for run in runs:
        values = [
            run.correctness / 2.0,
            run.refusal_success_rate,
            fastest / run.avg_first_token_seconds,
        ]
        values += values[:1]
        color = PALETTE[run.label]
        ax.plot(angles, values, color=color, linewidth=2.8, label=run.label)
        ax.fill(angles, values, color=color, alpha=0.20)
        ax.scatter(angles[:-1], values[:-1], color=color, s=55, edgecolor="white", linewidth=1.0, zorder=3)

    ax.set_title("Three-Dimensional Capability Profile: prompt_v1 vs prompt_v2", fontproperties=EN_FONT, fontsize=16, color=TEXT, pad=24)

    legend = ax.legend(loc="upper right", bbox_to_anchor=(1.24, 1.13), frameon=False)
    for text in legend.get_texts():
        text.set_fontproperties(EN_FONT)

    summary_lines = []
    for run in runs:
        summary_lines.append(
            f"{run.label}: Correctness {run.correctness:.2f}, Refusal {run.refusal_success_rate * 100:.0f}%, First Token {run.avg_first_token_seconds:.2f}s"
        )
    note = "\n".join(summary_lines) + "\nNote: Response Efficiency = Fastest First Token / Current First Token"
    fig.text(
        0.5,
        0.06,
        note,
        ha="center",
        va="center",
        fontproperties=EN_FONT,
        fontsize=10.2,
        color=TEXT,
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "white", "edgecolor": "#D7E0E7"},
    )

    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(output_dir / "fig03_capability_profile.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_question_type_focus(runs: list[RunMetrics], output_dir: Path) -> None:
    focus_types = [
        ("对比类", "Comparison"),
        ("机制类", "Mechanism"),
        ("综合类", "Comprehensive"),
    ]
    metrics = [
        ("avg_correctness", "Correctness"),
        ("avg_completeness", "Completeness"),
        ("avg_faithfulness", "Faithfulness"),
        ("avg_retrieval_relevance", "Retrieval Relevance"),
    ]

    fig, axes = plt.subplots(1, len(focus_types), figsize=(14.2, 5.8), sharex=True)
    if len(focus_types) == 1:
        axes = [axes]

    y_positions = np.arange(len(metrics))[::-1]

    for ax, (type_key, title) in zip(axes, focus_types):
        left_run, right_run = runs[0], runs[1]
        left_stats = left_run.manual_summary["by_question_type"][type_key]
        right_stats = right_run.manual_summary["by_question_type"][type_key]

        ax.set_title(
            f"{title}\n(n={left_stats['count']})",
            fontproperties=EN_FONT,
            fontsize=14,
            color=TEXT,
            pad=10,
        )

        for idx, ((metric_key, metric_label), y) in enumerate(zip(metrics, y_positions)):
            left_val = float(left_stats[metric_key])
            right_val = float(right_stats[metric_key])
            delta = right_val - left_val
            delta_color = "#2A9D8F" if delta >= 0 else "#D1495B"

            ax.plot(
                [left_val, right_val],
                [y, y],
                color="#C4CFDA",
                linewidth=3.0,
                solid_capstyle="round",
                zorder=1,
            )
            ax.scatter(left_val, y, s=90, color=PALETTE[left_run.label], edgecolor="white", linewidth=1.2, zorder=3)
            ax.scatter(right_val, y, s=90, color=PALETTE[right_run.label], edgecolor="white", linewidth=1.2, zorder=3)

            ax.text(
                left_val - 0.03,
                y + 0.16,
                f"{left_val:.2f}",
                ha="right",
                va="center",
                fontproperties=EN_FONT,
                fontsize=9.5,
                color=TEXT,
            )
            ax.text(
                right_val + 0.03,
                y + 0.16,
                f"{right_val:.2f}",
                ha="left",
                va="center",
                fontproperties=EN_FONT,
                fontsize=9.5,
                color=TEXT,
            )
            ax.text(
                max(left_val, right_val) + 0.08,
                y,
                f"{delta:+.2f}",
                ha="left",
                va="center",
                fontproperties=EN_FONT,
                fontsize=9.8,
                color=delta_color,
                bbox={"boxstyle": "round,pad=0.18", "facecolor": "white", "edgecolor": delta_color, "linewidth": 0.9},
            )

        ax.set_yticks(y_positions)
        ax.set_yticklabels([label for _, label in metrics], fontproperties=EN_FONT, fontsize=10.5)
        ax.set_xlim(1.15, 2.08)
        ax.set_xlabel("Average Score (0-2)", fontproperties=EN_FONT, fontsize=10.5, color=TEXT)
        style_axis(ax, grid_axis="x")

    handles = [
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=PALETTE[runs[0].label], markeredgecolor="white", markersize=10, label=runs[0].label),
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=PALETTE[runs[1].label], markeredgecolor="white", markersize=10, label=runs[1].label),
    ]
    legend = fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 1.02), ncol=2, frameon=False)
    for text in legend.get_texts():
        text.set_fontproperties(EN_FONT)

    fig.suptitle("Manual Score Differences by Question Type: prompt_v1 vs prompt_v2", fontproperties=EN_FONT, fontsize=16, color=TEXT, y=1.06)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(output_dir / "fig04_question_type_focus.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def export_metric_table(runs: list[RunMetrics], output_dir: Path) -> None:
    out_path = output_dir / "prompt_comparison_metrics.csv"
    fieldnames = [
        "label",
        "run_dir",
        "avg_correctness",
        "avg_completeness",
        "avg_completeness_without_refused",
        "avg_faithfulness",
        "avg_retrieval_relevance",
        "target_hit_rate",
        "refusal_success_rate",
        "avg_total_seconds",
        "avg_first_token_seconds",
        "refused_count",
        "tp",
        "fp",
        "fn",
        "tn",
    ]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for run in runs:
            tp, fp, fn, tn = run.confusion_counts
            writer.writerow({
                "label": run.label,
                "run_dir": run.run_dir,
                "avg_correctness": f"{run.correctness:.6f}",
                "avg_completeness": f"{run.completeness:.6f}",
                "avg_completeness_without_refused": f"{run.answerable_only_completeness:.6f}",
                "avg_faithfulness": f"{run.faithfulness:.6f}",
                "avg_retrieval_relevance": f"{run.relevance:.6f}",
                "target_hit_rate": f"{run.target_hit_rate:.6f}",
                "refusal_success_rate": f"{run.refusal_success_rate:.6f}",
                "avg_total_seconds": f"{run.avg_total_seconds:.6f}",
                "avg_first_token_seconds": f"{run.avg_first_token_seconds:.6f}",
                "refused_count": run.refused_count,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
            })


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot paper-ready comparison figures for baseline / prompt_v1 / prompt_v2")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    runs = [load_run_metrics(run_dir, label) for run_dir, label in RUN_CONFIGS]

    export_metric_table(runs, args.output_dir)
    plot_manual_score_overview(runs, args.output_dir)
    plot_refusal_confusion_matrix(runs, args.output_dir)
    plot_refusal_confusion(runs, args.output_dir)
    plot_capability_profile(runs, args.output_dir)
    plot_question_type_focus(runs, args.output_dir)

    print(f"[OK] Figures saved to: {args.output_dir}")


if __name__ == "__main__":
    main()
