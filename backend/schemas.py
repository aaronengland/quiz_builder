from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class GeneratedQuestion(BaseModel):
    """Validates a single question from the LLM response."""
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: Literal["A", "B", "C", "D"]
    explanation: str | None = None


class GenerateRequest(BaseModel):
    topic: str


class QuestionOut(BaseModel):
    id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str


class QuestionWithAnswer(QuestionOut):
    correct_answer: str
    explanation: str | None


class QuizOut(BaseModel):
    id: int
    topic: str
    created_at: datetime
    questions: list[QuestionOut]


class SubmitRequest(BaseModel):
    answers: dict[str, str]


class SubmitResponse(BaseModel):
    score: int
    total: int
    questions: list[QuestionWithAnswer]
    user_answers: dict[str, str]


class QuizSummary(BaseModel):
    id: int
    topic: str
    created_at: datetime
    latest_score: int | None
    total: int | None
