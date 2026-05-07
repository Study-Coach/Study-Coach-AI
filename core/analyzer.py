from __future__ import annotations

import base64
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.font_manager as font_manager
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    font_manager = None
    plt = None

try:
    import pandas as pd
except ModuleNotFoundError:
    pd = None

from .models import AnswerEvaluation


def calculate_average_score(evaluations: list[AnswerEvaluation]) -> float:
    if not evaluations:
        return 0.0
    return round(sum(item.score for item in evaluations) / len(evaluations), 1)


def calculate_review_rate(total_questions: int, answered_count: int) -> float:
    if total_questions <= 0:
        return 0.0
    return round(answered_count / total_questions * 100, 1)


def analyze_study(
    review_rate: float,
    focus_score: int,
    study_minutes: int,
    average_score: float,
) -> list[str]:
    results: list[str] = []
    if review_rate < 70:
        results.append("복습률이 낮아서 오늘 문제를 다시 풀 필요가 있음")
    if focus_score <= 2:
        results.append("집중도가 낮아서 짧은 시간으로 나누어 공부하는 것이 좋음")
    if study_minutes < 30:
        results.append("공부 시간이 부족해서 최소 30분 이상 복습이 필요함")
    if average_score < 70:
        results.append("평균 점수가 낮아서 개념 복습이 필요함")
    return results or ["학습 흐름이 양호하므로 다음 개념으로 넘어가도 됨"]


def records_to_dataframe(records: list[dict]) -> pd.DataFrame:
    if pd is None:
        raise RuntimeError("pandas가 설치되어 있지 않습니다. pip install -r requirements.txt를 실행하세요.")

    if not records:
        return pd.DataFrame(
            columns=[
                "id",
                "created_at",
                "subject",
                "study_minutes",
                "focus_score",
                "average_score",
                "review_rate",
            ]
        )
    frame = pd.DataFrame(records)
    frame["created_at"] = pd.to_datetime(frame["created_at"])
    return frame


def summarize_by_subject(records: list[dict]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for record in records:
        totals[record["subject"]] += int(record["study_minutes"])
    return dict(totals)


def create_dashboard_charts(records: list[dict], output_dir: str | Path) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    subject_chart = output_path / "subject_minutes.png"
    review_chart = output_path / "daily_review_rate.png"

    if pd is None or plt is None:
        _save_placeholder_png(subject_chart)
        _save_placeholder_png(review_chart)
        return {"subject_minutes": subject_chart, "daily_review_rate": review_chart}

    _configure_korean_font()
    frame = records_to_dataframe(records)

    if frame.empty:
        _save_empty_chart(subject_chart, "과목별 공부 시간")
        _save_empty_chart(review_chart, "날짜별 복습률")
        return {"subject_minutes": subject_chart, "daily_review_rate": review_chart}

    _save_subject_minutes_chart(frame, subject_chart)
    _save_daily_review_chart(frame, review_chart)
    return {"subject_minutes": subject_chart, "daily_review_rate": review_chart}


def _configure_korean_font() -> None:
    if plt is None or font_manager is None:
        return

    candidates = [
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/malgunbd.ttf"),
        Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
        Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
    ]
    for font_path in candidates:
        if font_path.exists():
            font_name = font_manager.FontProperties(fname=str(font_path)).get_name()
            plt.rcParams["font.family"] = font_name
            plt.rcParams["axes.unicode_minus"] = False
            return


def _save_subject_minutes_chart(frame: pd.DataFrame, path: Path) -> None:
    subject_minutes = frame.groupby("subject")["study_minutes"].sum().sort_values()
    height = max(3.2, min(5.4, 1.0 + len(subject_minutes) * 0.55))

    fig, ax = plt.subplots(figsize=(8.5, height))
    bars = ax.barh(subject_minutes.index, subject_minutes.values, color="#3b82f6", height=0.52)

    ax.set_title("과목별 공부 시간", fontsize=15, pad=14, weight="bold")
    ax.set_xlabel("공부 시간(분)", labelpad=8)
    ax.set_ylabel("")
    ax.grid(axis="x", color="#d8dee9", linewidth=0.8, alpha=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    max_value = max(float(subject_minutes.max()), 1.0)
    ax.set_xlim(0, max_value * 1.18)
    ax.bar_label(bars, labels=[f"{int(value)}분" for value in subject_minutes.values], padding=6)

    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _save_daily_review_chart(frame: pd.DataFrame, path: Path) -> None:
    daily = (
        frame.assign(date=frame["created_at"].dt.strftime("%Y-%m-%d"))
        .groupby("date")["review_rate"]
        .mean()
        .sort_index()
    )

    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    x_values = list(daily.index)
    y_values = list(daily.values)
    positions = list(range(len(x_values)))

    if len(daily) == 1:
        ax.bar(positions, y_values, color="#16a34a", width=0.34)
        ax.set_xlim(-0.65, 0.65)
    else:
        ax.plot(positions, y_values, color="#16a34a", linewidth=2.2, marker="o", markersize=7)

    for x_position, y_value in zip(positions, y_values, strict=False):
        ax.annotate(
            f"{y_value:.0f}%",
            (x_position, y_value),
            textcoords="offset points",
            xytext=(0, 9),
            ha="center",
            fontsize=10,
        )

    ax.set_title("날짜별 평균 복습률", fontsize=15, pad=14, weight="bold")
    ax.set_xlabel("날짜", labelpad=8)
    ax.set_ylabel("복습률(%)", labelpad=8)
    ax.set_ylim(0, 105)
    ax.set_xticks(positions)
    ax.set_xticklabels(x_values)
    ax.grid(axis="y", color="#d8dee9", linewidth=0.8, alpha=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", rotation=0)

    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _save_empty_chart(path: Path, title: str) -> None:
    if plt is None:
        _save_placeholder_png(path)
        return

    _configure_korean_font()
    fig, ax = plt.subplots(figsize=(8.5, 3.2))
    ax.set_title(title, fontsize=15, pad=14, weight="bold")
    ax.text(0.5, 0.5, "저장된 기록이 없습니다", ha="center", va="center", fontsize=12)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _save_placeholder_png(path: Path) -> None:
    # 1x1 PNG placeholder used only before chart dependencies are installed.
    png_data = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
        "/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
    path.write_bytes(base64.b64decode(png_data))


def format_created_at(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value
