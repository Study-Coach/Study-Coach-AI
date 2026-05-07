from __future__ import annotations

import json
import os
import re
from typing import Any

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv() -> bool:
        return False

from .models import AnswerEvaluation, Question, StudyInput
from .prompts import feedback_prompt, question_prompt, recommendation_prompt


load_dotenv()


def generate_questions(study_content: str, difficulty: str) -> list[Question]:
    prompt = question_prompt(study_content, difficulty)
    raw = _call_ai(prompt)
    parsed = _parse_json(raw)

    if isinstance(parsed, list):
        questions = [Question(str(item), _guess_question_type(index)) for index, item in enumerate(parsed[:5])]
        if len(questions) == 5:
            return questions

    return fallback_questions(study_content, difficulty)


def evaluate_answer(question: str, student_answer: str) -> AnswerEvaluation:
    if not student_answer.strip():
        return AnswerEvaluation(question, student_answer, 0, "답변이 비어 있습니다. 핵심 개념을 한 문장이라도 적어보세요.")

    prompt = feedback_prompt(question, student_answer)
    raw = _call_ai(prompt)
    parsed = _parse_json(raw)

    if isinstance(parsed, dict):
        score = _clamp_score(parsed.get("score", 0))
        feedback = str(parsed.get("feedback", "")).strip()
        if feedback:
            return AnswerEvaluation(question, student_answer, score, feedback)

    return fallback_evaluation(question, student_answer)


def generate_recommendation(
    study: StudyInput,
    review_rate: float,
    average_score: float,
    python_analysis: list[str],
) -> str:
    prompt = recommendation_prompt(study, review_rate, average_score, python_analysis)
    raw = _call_ai(prompt)
    if raw:
        return raw.strip()
    return fallback_recommendation(study, review_rate, average_score, python_analysis)


def _call_ai(prompt: str) -> str:
    provider = os.getenv("AI_PROVIDER", "openai").lower().strip()

    try:
        if provider == "gemini":
            return _call_gemini(prompt)
        return _call_openai(prompt)
    except Exception:
        return ""


def _call_openai(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ""

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "너는 한국어로 답하는 AI Study Coach야."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )
    return response.choices[0].message.content or ""


def _call_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return ""

    from google import genai

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        contents=prompt,
    )
    return getattr(response, "text", "") or ""


def _parse_json(text: str) -> Any:
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None


def _clamp_score(value: Any) -> int:
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        score = 0
    return max(0, min(100, score))


def _guess_question_type(index: int) -> str:
    return ["개념 확인", "개념 확인", "비교", "적용", "적용"][index]


def fallback_questions(study_content: str, difficulty: str) -> list[Question]:
    topic = study_content.strip() or "오늘 공부한 내용"
    hard_part = difficulty.strip() or "어려웠던 부분"
    return [
        Question(f"{topic}에서 가장 중요한 개념 2가지를 설명해보세요.", "개념 확인"),
        Question(f"{hard_part}와 관련해 헷갈렸던 이유를 한 문장으로 정리해보세요.", "개념 확인"),
        Question(f"{topic} 안에서 서로 비슷하지만 다른 개념 2개를 비교해보세요.", "비교"),
        Question(f"{topic}을 실제 예시 하나에 적용해 설명해보세요.", "적용"),
        Question(f"{hard_part}를 다시 만났을 때 어떤 순서로 해결할지 적어보세요.", "적용"),
    ]


def fallback_evaluation(question: str, student_answer: str) -> AnswerEvaluation:
    length = len(student_answer.strip())
    if length >= 60:
        score = 82
        feedback = "답변이 충분히 구체적입니다. 핵심 용어를 더 정확히 쓰면 완성도가 올라갑니다."
    elif length >= 25:
        score = 70
        feedback = "핵심 방향은 보입니다. 예시나 이유를 한 문장 더 추가해보세요."
    else:
        score = 55
        feedback = "답변이 짧아서 이해도를 판단하기 어렵습니다. 개념, 이유, 예시 순서로 보완해보세요."
    return AnswerEvaluation(question, student_answer, score, feedback)


def fallback_recommendation(
    study: StudyInput,
    review_rate: float,
    average_score: float,
    python_analysis: list[str],
) -> str:
    analysis = "\n".join(f"- {item}" for item in python_analysis)
    return (
        f"1. {study.subject}에서 오늘 어려웠던 부분을 10분 동안 다시 읽어보세요.\n"
        f"2. 평균 점수 {average_score:.1f}점과 복습률 {review_rate:.1f}%를 기준으로 틀린 문제를 먼저 복습하세요.\n"
        "3. 비슷한 예제 2개를 직접 풀고, 답을 한 문장으로 설명해보세요.\n"
        "4. 내일 공부를 시작하기 전에 오늘 문제 5개를 빠르게 다시 확인하세요.\n\n"
        f"분석 근거:\n{analysis}"
    )
