from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .models import AnswerEvaluation, Question, StudyInput


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "study_coach.db"


def get_connection(db_path: str | Path = DB_PATH) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS study_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                subject TEXT NOT NULL,
                study_minutes INTEGER NOT NULL,
                focus_score INTEGER NOT NULL,
                study_content TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                average_score REAL NOT NULL DEFAULT 0,
                review_rate REAL NOT NULL DEFAULT 0,
                recommendation TEXT NOT NULL DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT NOT NULL,
                FOREIGN KEY (record_id) REFERENCES study_records(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id INTEGER NOT NULL,
                answer_text TEXT NOT NULL,
                score INTEGER NOT NULL,
                feedback TEXT NOT NULL,
                FOREIGN KEY (question_id) REFERENCES questions(id)
            )
            """
        )
        conn.commit()


def save_study_session(
    study: StudyInput,
    questions: Iterable[Question],
    evaluations: Iterable[AnswerEvaluation],
    average_score: float,
    review_rate: float,
    recommendation: str,
) -> int:
    init_db()
    question_list = list(questions)
    evaluation_list = list(evaluations)

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO study_records (
                created_at,
                subject,
                study_minutes,
                focus_score,
                study_content,
                difficulty,
                average_score,
                review_rate,
                recommendation
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now().isoformat(timespec="seconds"),
                study.subject,
                study.study_minutes,
                study.focus_score,
                study.study_content,
                study.difficulty,
                average_score,
                review_rate,
                recommendation,
            ),
        )
        record_id = int(cursor.lastrowid)

        question_ids: list[int] = []
        for question in question_list:
            cursor = conn.execute(
                """
                INSERT INTO questions (record_id, question_text, question_type)
                VALUES (?, ?, ?)
                """,
                (record_id, question.text, question.question_type),
            )
            question_ids.append(int(cursor.lastrowid))

        for question_id, evaluation in zip(question_ids, evaluation_list, strict=False):
            conn.execute(
                """
                INSERT INTO answers (question_id, answer_text, score, feedback)
                VALUES (?, ?, ?, ?)
                """,
                (
                    question_id,
                    evaluation.answer,
                    int(evaluation.score),
                    evaluation.feedback,
                ),
            )

        conn.commit()
        return record_id


def get_recent_records(limit: int = 5) -> list[dict]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM study_records
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_all_records() -> list[dict]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM study_records
            ORDER BY created_at ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_session_detail(record_id: int) -> dict:
    init_db()
    with get_connection() as conn:
        record = conn.execute(
            "SELECT * FROM study_records WHERE id = ?",
            (record_id,),
        ).fetchone()
        if record is None:
            return {}

        rows = conn.execute(
            """
            SELECT
                q.id AS question_id,
                q.question_text,
                q.question_type,
                a.answer_text,
                a.score,
                a.feedback
            FROM questions q
            LEFT JOIN answers a ON a.question_id = q.id
            WHERE q.record_id = ?
            ORDER BY q.id ASC
            """,
            (record_id,),
        ).fetchall()

    return {"record": dict(record), "items": [dict(row) for row in rows]}


def add_sample_data() -> None:
    init_db()
    if get_recent_records(limit=1):
        return

    study = StudyInput(
        subject="프로그래밍",
        study_minutes=50,
        focus_score=4,
        study_content="파이썬 리스트, 반복문, 조건문",
        difficulty="while문 종료 조건이 헷갈림",
    )
    questions = [
        Question("리스트와 튜플의 차이를 설명해보세요.", "개념 확인"),
        Question("for문과 while문은 언제 각각 쓰면 좋은가요?", "비교"),
        Question("조건문에서 elif가 필요한 상황을 예로 들어보세요.", "적용"),
        Question("반복문이 무한 반복되는 이유를 한 가지 말해보세요.", "개념 확인"),
        Question("1부터 10까지의 짝수만 출력하는 방법을 설명해보세요.", "적용"),
    ]
    evaluations = [
        AnswerEvaluation(questions[0].text, "리스트는 바꿀 수 있고 튜플은 못 바꿉니다.", 85, "핵심 차이를 잘 설명했습니다."),
        AnswerEvaluation(questions[1].text, "횟수가 정해지면 for, 조건이면 while을 씁니다.", 90, "사용 기준이 명확합니다."),
        AnswerEvaluation(questions[2].text, "점수 구간을 나눌 때 씁니다.", 80, "예시가 적절합니다."),
        AnswerEvaluation(questions[3].text, "조건이 계속 참이면 끝나지 않습니다.", 88, "무한 반복의 원인을 잘 짚었습니다."),
        AnswerEvaluation(questions[4].text, "range와 if로 나눠서 출력합니다.", 76, "방향은 맞지만 코드 예시가 있으면 더 좋습니다."),
    ]
    save_study_session(
        study,
        questions,
        evaluations,
        average_score=83.8,
        review_rate=100.0,
        recommendation="1. while문 종료 조건을 10분 복습하세요.\n2. 짧은 반복문 예제를 3개 작성하세요.\n3. 조건문과 반복문을 함께 쓰는 문제를 풀어보세요.",
    )

