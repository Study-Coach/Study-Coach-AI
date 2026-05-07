from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class StudyInput:
    subject: str
    study_minutes: int
    focus_score: int
    study_content: str
    difficulty: str


@dataclass(slots=True)
class Question:
    text: str
    question_type: str = "review"


@dataclass(slots=True)
class AnswerEvaluation:
    question: str
    answer: str
    score: int
    feedback: str


@dataclass(slots=True)
class StudyRecord:
    id: int
    created_at: datetime
    subject: str
    study_minutes: int
    focus_score: int
    study_content: str
    difficulty: str
    average_score: float
    review_rate: float
    recommendation: str

