import json
import logging

from pydantic import ValidationError

from schemas import GeneratedQuestion
from services.wikipedia import fetch_wikipedia_summary

logger = logging.getLogger("quiz_builder")

MAX_RETRIES = 3


def _parse_and_validate(raw: str) -> list[dict]:
    """Parse LLM JSON response and validate each question through Pydantic."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]

    data = json.loads(cleaned)
    questions = data["questions"]

    if len(questions) != 5:
        raise ValueError(f"Expected 5 questions, got {len(questions)}")

    validated = [GeneratedQuestion(**q).model_dump() for q in questions]
    return validated


def _call_bedrock(bedrock_client, prompt: str) -> list[dict]:
    """Call Bedrock and retry until the output passes validation."""
    for attempt in range(1, MAX_RETRIES + 1):
        response = bedrock_client.converse(
            modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 2048},
        )

        raw = response["output"]["message"]["content"][0]["text"]

        try:
            return _parse_and_validate(raw)
        except (json.JSONDecodeError, KeyError, ValueError, ValidationError) as exc:
            logger.warning(
                "LLM output validation failed (attempt %d/%d): %s",
                attempt, MAX_RETRIES, exc,
            )
            if attempt == MAX_RETRIES:
                raise ValueError(
                    f"LLM output failed validation after {MAX_RETRIES} attempts"
                ) from exc


def _build_prompt(topic: str, wiki_context: str | None) -> str:
    context_block = ""
    if wiki_context:
        context_block = (
            "\nUse the following reference material to ensure factual accuracy:\n"
            "---\n"
            f"{wiki_context}\n"
            "---\n"
        )

    return f"""Generate a quiz about: {topic}
{context_block}
Create exactly 5 multiple-choice questions. Each question must have 4 options (A-D) with exactly one correct answer.

Respond with ONLY valid JSON in this exact format:
{{
  "questions": [
    {{
      "question_text": "...",
      "option_a": "...",
      "option_b": "...",
      "option_c": "...",
      "option_d": "...",
      "correct_answer": "A",
      "explanation": "Brief explanation of why the correct answer is right and why the others are wrong."
    }}
  ]
}}

Rules:
- Questions should test understanding, not just recall
- Distractors should be plausible but clearly wrong
- Vary question difficulty (2 easy, 2 medium, 1 hard)
- Explanations should be 1-2 sentences
- correct_answer must be exactly one of: A, B, C, D"""


async def generate_quiz(topic: str, bedrock_client) -> list[dict]:
    """Call Bedrock to generate 5 quiz questions for the given topic."""
    wiki_context = await fetch_wikipedia_summary(topic)

    if wiki_context:
        logger.info("Wikipedia context retrieved for '%s' (%d chars)", topic, len(wiki_context))
    else:
        logger.info("No Wikipedia context for '%s', generating without retrieval", topic)

    prompt = _build_prompt(topic, wiki_context)
    questions = _call_bedrock(bedrock_client, prompt)

    # Verify factual accuracy with a second LLM call
    questions = await _verify_questions(questions, topic, wiki_context, bedrock_client)

    return questions


def _build_verification_prompt(questions: list[dict], topic: str, wiki_context: str | None) -> str:
    context_block = ""
    if wiki_context:
        context_block = (
            "\nReference material:\n"
            "---\n"
            f"{wiki_context}\n"
            "---\n"
        )

    questions_json = json.dumps(questions, indent=2)

    return f"""You are a fact-checker. Review the following quiz questions about "{topic}" and verify that each question's correct_answer is factually accurate.
{context_block}
Questions to verify:
{questions_json}

For each question, determine if the marked correct_answer is truly correct. If a question has an incorrect correct_answer, fix it by changing the correct_answer field to the right letter and updating the explanation.

Respond with ONLY valid JSON in this exact format:
{{
  "questions": [
    {{
      "question_text": "...",
      "option_a": "...",
      "option_b": "...",
      "option_c": "...",
      "option_d": "...",
      "correct_answer": "A",
      "explanation": "..."
    }}
  ]
}}

Return all 5 questions. Keep questions unchanged if they are correct. Only modify questions that have factual errors."""


async def _verify_questions(
    questions: list[dict],
    topic: str,
    wiki_context: str | None,
    bedrock_client,
) -> list[dict]:
    """Make a second LLM call to fact-check the generated questions."""
    prompt = _build_verification_prompt(questions, topic, wiki_context)

    try:
        verified = _call_bedrock(bedrock_client, prompt)
        logger.info("Quiz verification complete for '%s'", topic)
        return verified

    except Exception as exc:
        logger.warning("Verification failed for '%s': %s. Using unverified questions.", topic, exc)
        return questions
