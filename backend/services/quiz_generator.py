import json
import logging

from services.wikipedia import fetch_wikipedia_summary

logger = logging.getLogger("quiz_builder")


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

    response = bedrock_client.converse(
        modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 2048},
    )

    raw = response["output"]["message"]["content"][0]["text"]

    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]

    data = json.loads(cleaned)
    questions = data["questions"]

    if len(questions) != 5:
        raise ValueError(f"Expected 5 questions, got {len(questions)}")

    for q in questions:
        if q["correct_answer"] not in ("A", "B", "C", "D"):
            raise ValueError(f"Invalid correct_answer: {q['correct_answer']}")

    return questions
