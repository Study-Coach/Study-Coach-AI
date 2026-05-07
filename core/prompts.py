from __future__ import annotations

from .models import StudyInput


def question_prompt(study_content: str, difficulty: str) -> str:
    return f"""
너는 고등학생을 위한 복습 문제 생성 AI야.
학생이 오늘 공부한 내용: {study_content}
어려웠던 점: {difficulty}

조건:
1. 오늘 공부한 내용에서만 문제를 만들어줘.
2. 문제는 총 5개 만들어줘.
3. 개념 확인 2개, 비교 문제 1개, 적용 문제 2개로 구성해줘.
4. 정답은 바로 알려주지 말고 문제만 출력해줘.
5. JSON 배열 형식으로 출력해줘.
예시: ["문제1", "문제2", "문제3", "문제4", "문제5"]
""".strip()


def feedback_prompt(question: str, student_answer: str) -> str:
    return f"""
너는 친절하지만 정확한 학습 코치야.

문제:
{question}

학생 답변:
{student_answer}

조건:
1. 점수는 0부터 100까지 정수로 평가해줘.
2. 피드백은 1-2문장으로 짧게 작성해줘.
3. JSON 객체 형식으로 출력해줘.
예시: {{"score": 80, "feedback": "핵심 개념은 맞았지만 예시가 부족합니다."}}
""".strip()


def recommendation_prompt(
    study: StudyInput,
    review_rate: float,
    average_score: float,
    python_analysis: list[str],
) -> str:
    analysis_text = "\n".join(f"- {item}" for item in python_analysis)
    return f"""
너는 학생의 내일 공부 계획을 세워주는 AI Study Coach야.

과목: {study.subject}
오늘 공부 시간: {study.study_minutes}분
집중도: {study.focus_score}/5
복습률: {review_rate:.1f}%
평균 점수: {average_score:.1f}
어려웠던 점: {study.difficulty}

Python 규칙 기반 분석:
{analysis_text}

조건:
1. 내일 바로 실천 가능한 학습 계획을 3-5개 제안해줘.
2. 각 계획은 짧고 구체적으로 작성해줘.
3. 학생이 부담을 느끼지 않도록 격려하는 말투로 작성해줘.
""".strip()

