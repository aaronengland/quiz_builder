import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Quiz, Question, QuizResult
from schemas import (
    GenerateRequest,
    QuizOut,
    QuestionOut,
    QuestionWithAnswer,
    SubmitRequest,
    SubmitResponse,
    QuizSummary,
)
from services.quiz_generator import generate_quiz

logger = logging.getLogger("quiz_builder")

router = APIRouter(prefix="/api/quiz", tags=["quiz"])

_bedrock_client = None


def set_bedrock_client(client):
    global _bedrock_client
    _bedrock_client = client


@router.post("/generate", response_model=QuizOut)
async def generate(req: GenerateRequest, db: Session = Depends(get_db)):
    """Generate a new quiz from a topic using AI."""
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Topic cannot be empty")

    try:
        questions_data = await generate_quiz(req.topic.strip(), _bedrock_client)
    except Exception as exc:
        logger.error("Quiz generation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate quiz. Please try again.")

    # Persist quiz and questions
    quiz = Quiz(topic=req.topic.strip())
    db.add(quiz)
    db.flush()

    for q_data in questions_data:
        question = Question(
            quiz_id=quiz.id,
            question_text=q_data["question_text"],
            option_a=q_data["option_a"],
            option_b=q_data["option_b"],
            option_c=q_data["option_c"],
            option_d=q_data["option_d"],
            correct_answer=q_data["correct_answer"],
            explanation=q_data.get("explanation"),
        )
        db.add(question)

    db.commit()
    db.refresh(quiz)

    return QuizOut(
        id=quiz.id,
        topic=quiz.topic,
        created_at=quiz.created_at,
        questions=[
            QuestionOut(
                id=q.id,
                question_text=q.question_text,
                option_a=q.option_a,
                option_b=q.option_b,
                option_c=q.option_c,
                option_d=q.option_d,
            )
            for q in quiz.questions
        ],
    )


@router.get("/{quiz_id}", response_model=QuizOut)
async def get_quiz(quiz_id: int, db: Session = Depends(get_db)):
    """Retrieve a quiz by ID (answers not included)."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    return QuizOut(
        id=quiz.id,
        topic=quiz.topic,
        created_at=quiz.created_at,
        questions=[
            QuestionOut(
                id=q.id,
                question_text=q.question_text,
                option_a=q.option_a,
                option_b=q.option_b,
                option_c=q.option_c,
                option_d=q.option_d,
            )
            for q in quiz.questions
        ],
    )


@router.post("/{quiz_id}/submit", response_model=SubmitResponse)
async def submit_quiz(quiz_id: int, req: SubmitRequest, db: Session = Depends(get_db)):
    """Submit quiz answers and get the score with explanations."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Build a lookup of question_id -> Question
    question_map = {str(q.id): q for q in quiz.questions}

    score = 0
    total = len(quiz.questions)

    for q_id, user_answer in req.answers.items():
        if q_id in question_map and user_answer.upper() == question_map[q_id].correct_answer:
            score += 1

    # Persist result
    result = QuizResult(
        quiz_id=quiz.id,
        score=score,
        total=total,
        answers_json=json.dumps(req.answers),
    )
    db.add(result)
    db.commit()

    return SubmitResponse(
        score=score,
        total=total,
        questions=[
            QuestionWithAnswer(
                id=q.id,
                question_text=q.question_text,
                option_a=q.option_a,
                option_b=q.option_b,
                option_c=q.option_c,
                option_d=q.option_d,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
            )
            for q in quiz.questions
        ],
        user_answers=req.answers,
    )


@router.get("zes", response_model=list[QuizSummary])
async def list_quizzes(db: Session = Depends(get_db)):
    """List all past quizzes with their latest scores."""
    quizzes = db.query(Quiz).order_by(Quiz.created_at.desc()).all()

    summaries = []
    for quiz in quizzes:
        latest_result = (
            db.query(QuizResult)
            .filter(QuizResult.quiz_id == quiz.id)
            .order_by(QuizResult.submitted_at.desc())
            .first()
        )
        summaries.append(
            QuizSummary(
                id=quiz.id,
                topic=quiz.topic,
                created_at=quiz.created_at,
                latest_score=latest_result.score if latest_result else None,
                total=latest_result.total if latest_result else None,
            )
        )

    return summaries
