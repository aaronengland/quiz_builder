#!/usr/bin/env python3
"""
Seth Beckett Bot - AI Software Engineer at Entrata
===================================================
A mock interviewer that simulates Seth Beckett reviewing your Quiz Builder project.
Prepares you for your 1-hour technical presentation at Entrata.

Usage:
    python seth_beckett_bot.py
    python seth_beckett_bot.py --rounds 10
"""

import argparse
import random
import textwrap

# ---------------------------------------------------------------------------
# Seth's persona and knowledge base
# ---------------------------------------------------------------------------

SETH_INTRO = """
================================================================================
  SETH BECKETT BOT  -  AI Software Engineer @ Entrata
================================================================================

Hey, I'm Seth. I work on AI engineering at Entrata, where we build things like
ELI+ (our agentic property management system with 100+ embedded AI agents) and
other ML/NLP products on top of AWS infrastructure.

I've reviewed your Quiz Builder repo and the challenge spec. Let's walk through
your project like we would in the actual interview. I'll ask you questions about
your architecture, AI integration, design tradeoffs, and how you'd scale this.

I'll give you feedback after each answer so you can sharpen your responses
before the real thing.

Type your answer and press Enter (or type 'skip' to see my suggested answer).
Type 'quit' to end the session.
================================================================================
"""

# Each question has: category, question text, what Seth is looking for,
# a suggested strong answer, and follow-up probes.
QUESTION_BANK = [
    # ---- Architecture & Design ----
    {
        "category": "Architecture",
        "question": (
            "Walk me through the high-level architecture of your quiz builder. "
            "How do the pieces fit together?"
        ),
        "what_seth_wants": (
            "A clear, concise walkthrough: React frontend -> FastAPI backend -> "
            "SQLite via SQLAlchemy -> Claude Sonnet 4.5 via AWS Bedrock, plus "
            "Wikipedia for context injection. Seth wants to see you can articulate "
            "the data flow without rambling."
        ),
        "suggested_answer": (
            "The app has three layers. The React frontend (Vite + React Router) "
            "handles four routes: topic input, quiz taking, results, and history. "
            "It talks to a FastAPI backend over a REST API. When a user submits a "
            "topic, the backend fetches a Wikipedia summary for grounding, then "
            "makes two LLM calls to Claude Sonnet 4.5 via AWS Bedrock: one to "
            "generate the quiz, one to fact-check it. Both calls have retry logic "
            "with Pydantic validation. Results persist to SQLite through SQLAlchemy. "
            "The whole thing ships as a single Docker image on App Runner."
        ),
        "follow_ups": [
            "Why did you choose a monolithic Docker image instead of separate services?",
            "How does the frontend communicate with the backend in development vs. production?",
        ],
    },
    {
        "category": "Architecture",
        "question": (
            "I see you're using FastAPI. Why FastAPI over Flask or Django? "
            "What specifically does it give you here?"
        ),
        "what_seth_wants": (
            "Concrete reasons tied to THIS project, not generic 'FastAPI is modern' "
            "talking points. Seth wants to hear about Pydantic validation (used "
            "heavily), async support (Wikipedia call), and auto-generated docs."
        ),
        "suggested_answer": (
            "Three reasons specific to this project. First, Pydantic integration: "
            "I validate data at every boundary, including incoming requests, LLM output, "
            "and API responses. FastAPI makes that native. Second, async support: the "
            "Wikipedia fetch is async with httpx, so it doesn't block. Third, the "
            "auto-generated /docs endpoint was useful during development for testing "
            "endpoints. Flask would need me to bolt all of that on manually. Django "
            "would bring a lot of machinery I don't need, like its ORM, admin panel, "
            "and template engine."
        ),
        "follow_ups": [
            "Are you actually leveraging async throughout, or just for the Wikipedia call?",
            "If Entrata's stack was Flask-based, would you still advocate for FastAPI?",
        ],
    },
    # ---- AI / LLM Integration ----
    {
        "category": "AI Integration",
        "question": (
            "You're making two LLM calls per quiz: generate and verify. "
            "Walk me through why, and what happens when the verification fails."
        ),
        "what_seth_wants": (
            "Seth wants to see that you understand the tradeoff: doubling latency "
            "and cost for better accuracy. He also wants to know the fallback "
            "behavior (uses unverified questions) and that you thought about "
            "whether that's acceptable."
        ),
        "suggested_answer": (
            "The first call generates the quiz. The second call acts as a "
            "fact-checker, reviewing each question against the Wikipedia context "
            "and correcting any wrong answers. This roughly doubles the Bedrock "
            "cost and adds 3-5 seconds of latency, but it catches cases where the "
            "model generates a plausible-sounding but incorrect answer. If the "
            "verification call fails validation after 3 retries, the app falls back "
            "to the original unverified questions rather than failing entirely. "
            "That's a deliberate choice: a slightly less accurate quiz is better "
            "than no quiz at all."
        ),
        "follow_ups": [
            "Have you measured how often the verification step actually catches errors?",
            "Could you combine generation and verification into a single prompt?",
            "At Entrata scale, doubling LLM calls is a real cost concern. How would you optimize?",
        ],
    },
    {
        "category": "AI Integration",
        "question": (
            "Why Claude Sonnet 4.5 specifically? You had access to any public model."
        ),
        "what_seth_wants": (
            "A thoughtful model selection rationale, not just 'it's the best.' "
            "Seth wants to hear about structured output reliability, the Bedrock "
            "integration advantage, and the cost/quality/latency tradeoff vs. "
            "Haiku and Opus."
        ),
        "suggested_answer": (
            "Three factors. First, structured output quality: Sonnet 4.5 reliably "
            "produces well-formed JSON, which is critical because I'm parsing LLM "
            "output programmatically. Second, AWS-native integration: Bedrock means "
            "credentials flow through IAM with no separate API keys to manage. "
            "Third, the cost/latency sweet spot: Haiku would be faster and cheaper "
            "but produces weaker distractors and explanations. Opus would be higher "
            "quality but adds latency and cost that isn't justified for a 5-question "
            "quiz. Sonnet sits in the middle."
        ),
        "follow_ups": [
            "Did you consider using Bedrock's tool_use for structured output instead of raw JSON prompting?",
            "What if Bedrock has an outage? Do you have a fallback model strategy?",
        ],
    },
    {
        "category": "AI Integration",
        "question": (
            "How do you handle the case where the LLM returns malformed JSON? "
            "Walk me through the retry logic."
        ),
        "what_seth_wants": (
            "Seth is testing whether your retry logic is real engineering or just "
            "a try/except with a loop. He wants to hear about Pydantic validation "
            "of the parsed output, the 3-attempt limit, and what specifically gets "
            "validated (5 questions, correct_answer in A-D, all fields present)."
        ),
        "suggested_answer": (
            "Every LLM response goes through a pipeline: strip markdown code fences "
            "if present, parse as JSON, then validate through a Pydantic model. The "
            "Pydantic model enforces exactly 5 questions, all required fields present, "
            "correct_answer must be one of A/B/C/D, and correct data types throughout. "
            "If any step fails, I retry the same prompt, up to 3 total attempts. Each "
            "retry is a fresh LLM call, not a re-parse. Only after all 3 fail does "
            "the user see an error. For the verification step, the fallback is gentler: "
            "use the unverified questions instead of erroring out."
        ),
        "follow_ups": [
            "Why retry the same prompt? Wouldn't it be better to modify the prompt on retry?",
            "Have you considered using temperature adjustments on retries?",
        ],
    },
    {
        "category": "AI Integration",
        "question": (
            "You're using Wikipedia for context injection. Why the summary endpoint "
            "instead of the full article? And why not a proper RAG pipeline?"
        ),
        "what_seth_wants": (
            "Seth wants to see you understand the RAG spectrum and made a deliberate "
            "choice, not that you couldn't build RAG. He's looking for: summary has "
            "higher signal-to-noise, fits in prompt without chunking, and you know "
            "what the full RAG path would look like."
        ),
        "suggested_answer": (
            "The summary endpoint returns 1-3 concise paragraphs, which is the "
            "highest-signal content for any topic. It fits entirely in the prompt "
            "without chunking, and a single API call takes about 100ms. A full "
            "article would include noise like 'See also' sections and footnotes "
            "that don't improve question quality. For this MVP, the summary gives "
            "roughly 80% of the accuracy benefit at maybe 10% of the complexity. "
            "If I needed to support longer sources like textbook chapters, I'd build "
            "a RAG pipeline: chunk the documents with overlap, embed with Titan "
            "Embeddings via Bedrock, store in a vector database like OpenSearch "
            "Serverless or pgvector, and retrieve the top-k chunks at query time."
        ),
        "follow_ups": [
            "What happens when Wikipedia doesn't have an article for the topic?",
            "How would you evaluate whether the RAG pipeline actually improves quiz quality?",
        ],
    },
    # ---- Data & Security ----
    {
        "category": "Data & Security",
        "question": (
            "SQLite for a deployed app. Convince me that's not a problem."
        ),
        "what_seth_wants": (
            "Seth isn't necessarily against SQLite here; he wants to see you "
            "understand its limitations AND why it's appropriate for this context. "
            "Key points: single-writer is fine for this use pattern, the ORM "
            "abstracts the engine, and the migration path is a one-line change."
        ),
        "suggested_answer": (
            "For this MVP, SQLite is the right call. The write pattern is one quiz "
            "generation at a time, which avoids SQLite's single-writer limitation. "
            "It makes the app fully self-contained, so a reviewer can clone and run "
            "without provisioning a database server. Despite using SQLite, I still "
            "use SQLAlchemy with proper relational modeling, foreign keys, and "
            "cascading deletes. Switching to PostgreSQL on RDS only requires "
            "changing the DATABASE_URL connection string in the environment; no "
            "code changes needed because SQLAlchemy abstracts the engine. That "
            "would be the first change for production."
        ),
        "follow_ups": [
            "What happens to the SQLite data when your App Runner container restarts?",
            "How would you handle database migrations if you added a new column?",
        ],
    },
    {
        "category": "Data & Security",
        "question": (
            "How do you prevent users from cheating? Could someone inspect "
            "network traffic and see the answers before submitting?"
        ),
        "what_seth_wants": (
            "Seth wants to hear about the two different Pydantic response schemas: "
            "QuestionOut (no answers) vs. QuestionWithAnswer (after submit). This "
            "is a clean pattern that shows you think about API design."
        ),
        "suggested_answer": (
            "I use two different Pydantic schemas for the same data. When a user "
            "fetches a quiz, the GET endpoint returns questions through QuestionOut, "
            "which deliberately omits correct_answer and explanation. Those fields "
            "only appear in the response from the POST submit endpoint, after the "
            "user has committed their answers. So even if you open dev tools and "
            "inspect the network response, you won't see answers before submission."
        ),
        "follow_ups": [
            "What if someone just calls the submit endpoint with empty answers to see the correct ones?",
            "How would you handle this differently if there were real stakes, like a certification exam?",
        ],
    },
    # ---- Scaling & Production ----
    {
        "category": "Production Readiness",
        "question": (
            "If I told you Entrata wanted to ship this to our 20,000+ apartment "
            "communities tomorrow, what would need to change?"
        ),
        "what_seth_wants": (
            "A prioritized list, not a kitchen sink. Seth wants to see you can "
            "triage: auth and rate limiting first (security), then database swap "
            "(reliability), then caching and monitoring (efficiency). Bonus if "
            "you mention cost controls on the Bedrock API."
        ),
        "suggested_answer": (
            "In priority order: (1) Authentication, probably Cognito since we're "
            "already on AWS, to know who's generating quizzes. (2) Rate limiting "
            "on the generate endpoint to control Bedrock costs; one user hammering "
            "the API could run up a real bill. (3) Swap SQLite for PostgreSQL on "
            "RDS for concurrent writes and persistent storage across container "
            "restarts. (4) Split the Docker image: React build goes to CloudFront/S3 "
            "for CDN caching, API runs separately on App Runner or ECS. (5) Add "
            "CloudWatch monitoring, especially latency and error rates on the "
            "Bedrock calls. (6) Cache Wikipedia summaries, since popular topics "
            "will get repeated."
        ),
        "follow_ups": [
            "How would you handle the cold start latency for the first quiz generation?",
            "What's your strategy for cost monitoring on the Bedrock API?",
        ],
    },
    {
        "category": "Production Readiness",
        "question": (
            "You mentioned this was a 2-day timeline. What tradeoffs did you make, "
            "and which ones would you undo first?"
        ),
        "what_seth_wants": (
            "Honest self-assessment. Seth respects candidates who can clearly "
            "articulate what they cut and why. He's also testing whether your "
            "tradeoffs were strategic or just things you ran out of time for."
        ),
        "suggested_answer": (
            "Four main tradeoffs. SQLite over a managed database, knowing the "
            "migration is a one-line change. No authentication, since it's not "
            "needed for a demo. Wikipedia summary instead of full RAG, which gives "
            "80% of the accuracy at 10% of the complexity. And minimal CSS, since "
            "the spec said UI polish isn't the priority. First thing I'd undo: "
            "add authentication, because without it you can't do rate limiting, "
            "usage tracking, or any kind of personalization. Second: swap the "
            "database, because SQLite data doesn't survive container restarts."
        ),
        "follow_ups": [
            "If you had one more day, what single feature would you add?",
            "What's one thing you'd do differently if you started over?",
        ],
    },
    # ---- Code Quality & Patterns ----
    {
        "category": "Code Quality",
        "question": (
            "I noticed you're using Pydantic pretty heavily. Walk me through "
            "how you use it across the stack and why."
        ),
        "what_seth_wants": (
            "Seth wants to see that Pydantic isn't just for request validation. "
            "You use it for: request validation, LLM output validation, response "
            "serialization with field hiding, and app configuration. That's a "
            "strong pattern."
        ),
        "suggested_answer": (
            "Pydantic serves four roles in this app. First, request validation: "
            "GenerateRequest and SubmitRequest validate incoming API data. Second, "
            "LLM output validation: GeneratedQuestion enforces the schema on every "
            "LLM response, which drives the retry logic. Third, response "
            "serialization: QuestionOut hides answers while QuestionWithAnswer "
            "reveals them, same data, different views. Fourth, app configuration: "
            "pydantic-settings manages environment variables with type safety and "
            "defaults. The pattern is: validate at every boundary, fail fast, and "
            "give clear errors."
        ),
        "follow_ups": [
            "Have you looked at Pydantic's model_validator for cross-field validation?",
            "How does Pydantic interact with SQLAlchemy? Any friction?",
        ],
    },
    {
        "category": "Code Quality",
        "question": (
            "You're prompting the LLM with a raw JSON format instruction instead "
            "of using Bedrock's tool_use. Why?"
        ),
        "what_seth_wants": (
            "Seth wants to see you know tool_use exists and made a conscious choice. "
            "The strong answer: for this simple, fixed schema, JSON prompting with "
            "Pydantic validation is simpler and sufficient. Tool_use adds complexity "
            "that's warranted for dynamic or multi-tool scenarios."
        ),
        "suggested_answer": (
            "I know Bedrock supports tool_use for structured output, but for this "
            "use case, JSON prompting is simpler and works reliably. The schema is "
            "fixed and small: 5 questions with known fields. The prompt explicitly "
            "specifies the format, and Pydantic validates the output. Tool_use "
            "would add complexity in the prompt construction and response parsing "
            "without a clear benefit here. Where tool_use shines is when the model "
            "needs to choose between multiple tools or when the schema is dynamic. "
            "For a single, static JSON format, raw prompting with validation is "
            "simpler."
        ),
        "follow_ups": [
            "What about Claude's built-in JSON mode? Have you experimented with that?",
            "At what point would you switch to tool_use?",
        ],
    },
    # ---- Entrata-specific / AI Engineering ----
    {
        "category": "AI Engineering",
        "question": (
            "At Entrata we're building agentic systems with 100+ AI agents. "
            "How does the thinking behind your quiz builder translate to that "
            "kind of multi-agent architecture?"
        ),
        "what_seth_wants": (
            "Seth is probing whether you can think beyond this MVP. He wants to "
            "hear you connect your patterns (retry logic, validation, fallbacks, "
            "two-step verification) to broader agent design principles."
        ),
        "suggested_answer": (
            "Several patterns transfer directly. The retry-with-validation loop "
            "is essential for any agent that needs structured output; you can't "
            "trust an LLM to get the format right every time. The two-step pattern, "
            "generate then verify, maps to agent architectures where one agent "
            "proposes actions and another validates them before execution. The "
            "graceful fallback (use unverified questions if verification fails) is "
            "critical in multi-agent systems where one agent's failure shouldn't "
            "cascade. And the Pydantic boundary validation pattern applies anywhere "
            "agents pass data to each other: define a contract, validate at the "
            "boundary, fail fast."
        ),
        "follow_ups": [
            "How would you handle state management across multiple agents?",
            "What observability would you want for a multi-agent system?",
        ],
    },
    {
        "category": "AI Engineering",
        "question": (
            "How do you think about prompt engineering as a discipline? "
            "What makes a good prompt for a production system vs. a one-off?"
        ),
        "what_seth_wants": (
            "Seth wants to see maturity here. Key points: production prompts need "
            "to be deterministic/parseable, tested against edge cases, and "
            "versioned. The quiz builder prompts are a good example: explicit "
            "format, clear rules, grounding context."
        ),
        "suggested_answer": (
            "For production, three things matter that don't matter for one-offs. "
            "First, parseable output: the prompt must produce output your code can "
            "reliably consume, which is why I specify the exact JSON schema and "
            "validate with Pydantic. Second, grounding: injecting Wikipedia context "
            "reduces hallucination because the model has real facts to reference "
            "instead of relying purely on training data. Third, specificity in "
            "constraints: I specify exact counts (5 questions), valid values "
            "(A/B/C/D), difficulty distribution (2 easy, 2 medium, 1 hard), and "
            "output length (1-2 sentence explanations). Vague prompts work fine "
            "interactively but fail unpredictably in production."
        ),
        "follow_ups": [
            "How would you A/B test different prompts to measure quality?",
            "Do you version your prompts? How would you manage prompt changes in production?",
        ],
    },
    {
        "category": "AI Engineering",
        "question": (
            "If the quiz builder needed to support topics in languages other "
            "than English, what changes would that require?"
        ),
        "what_seth_wants": (
            "A practical answer covering: Wikipedia has language-specific endpoints, "
            "Claude handles multilingual well, but Pydantic validation of "
            "correct_answer (A-D) stays the same. Shows you think about i18n."
        ),
        "suggested_answer": (
            "Three changes. First, the Wikipedia call: switch the endpoint to the "
            "target language's Wikipedia (e.g., es.wikipedia.org for Spanish). "
            "Second, the prompt: add an instruction to generate questions in the "
            "target language. Claude handles multilingual generation well. Third, "
            "the frontend: the UI labels and navigation would need translation. "
            "What stays the same: the Pydantic validation (correct_answer is still "
            "A-D regardless of language), the database schema, and the retry logic. "
            "The biggest risk is that factual accuracy may vary by language because "
            "Wikipedia coverage differs."
        ),
        "follow_ups": [
            "How would you detect the user's language preference?",
        ],
    },
    # ---- Deployment & DevOps ----
    {
        "category": "Deployment",
        "question": (
            "Walk me through your deployment pipeline. How does code get from "
            "your machine to App Runner?"
        ),
        "what_seth_wants": (
            "Seth wants to understand the Docker multi-stage build + ECR + "
            "App Runner flow. He'll also be curious about why SageMaker "
            "notebooks for the build step."
        ),
        "suggested_answer": (
            "It's a multi-stage Docker build. First stage uses Node to build "
            "the React frontend into static files. Second stage uses Python, "
            "copies the built frontend in, installs backend dependencies, and "
            "runs Gunicorn with Uvicorn workers. I push the image to ECR using "
            "a SageMaker notebook, which was convenient because the AWS credentials "
            "and Docker runtime are already available there. App Runner pulls from "
            "ECR and runs the container with a health check on /api/health. "
            "Environment variables (AWS credentials for Bedrock) are configured "
            "in the App Runner service."
        ),
        "follow_ups": [
            "Would you set up CI/CD with GitHub Actions if this were a real project?",
            "Why SageMaker for the build? That's a bit unusual.",
        ],
    },
    # ---- Behavioral / Communication ----
    {
        "category": "Communication",
        "question": (
            "What's the one thing about this project you're most proud of, "
            "and what's the one thing you'd change?"
        ),
        "what_seth_wants": (
            "Authentic self-reflection. Seth wants to see technical pride "
            "balanced with honest self-criticism. Avoid false modesty and "
            "avoid arrogance."
        ),
        "suggested_answer": (
            "Most proud of the two-step LLM verification pattern. It's a simple "
            "idea, generate then fact-check, but it meaningfully improves quiz "
            "accuracy and demonstrates a pattern that scales to more complex AI "
            "systems. The fallback behavior (use unverified questions if "
            "verification fails) shows I thought about failure modes. What I'd "
            "change: I'd add proper error states in the frontend. Right now if "
            "the backend is slow or fails, the UX isn't great. Loading states, "
            "timeout handling, and retry-from-the-UI would make it more polished."
        ),
        "follow_ups": [
            "Tell me about a technical decision you went back and forth on.",
        ],
    },
    {
        "category": "Communication",
        "question": (
            "If you joined Entrata's AI team, what would you want to learn "
            "in your first 30 days?"
        ),
        "what_seth_wants": (
            "Curiosity and humility. Seth wants to see that you'd ramp up on "
            "their domain (property management), their existing AI systems "
            "(ELI+, Colleen AI), and their engineering culture before proposing "
            "changes."
        ),
        "suggested_answer": (
            "First, I'd want to understand the domain: how property management "
            "workflows actually work, what problems ELI+ solves for property "
            "managers, and where the pain points are. Second, the existing AI "
            "infrastructure: how the 100+ agents are orchestrated, what models "
            "you're using, how you handle evaluation and monitoring. Third, the "
            "engineering culture: how you ship, how you review, how you decide "
            "what to build. I'd rather spend the first few weeks understanding "
            "the system before proposing changes."
        ),
        "follow_ups": [],
    },
]


def wrap_text(text, width=80, indent="  "):
    """Wrap text for terminal display."""
    lines = textwrap.wrap(text, width=width - len(indent))
    return "\n".join(f"{indent}{line}" for line in lines)


def print_section(header, content, char="-"):
    """Print a formatted section."""
    print(f"\n  {char * 3} {header} {char * 3}")
    print(wrap_text(content))
    print()


def get_feedback(user_answer, question):
    """Generate simple feedback based on key concepts Seth is looking for."""
    if not user_answer.strip():
        return "You didn't provide an answer. In the real interview, silence is worse than an imperfect answer."

    answer_lower = user_answer.lower()
    what_seth_wants = question["what_seth_wants"].lower()

    # Check for key concepts mentioned
    key_concepts = []
    concept_checks = {
        "pydantic": ["pydantic", "validation", "schema"],
        "retry": ["retry", "retries", "3 attempts", "three attempts"],
        "wikipedia": ["wikipedia", "wiki", "context injection", "grounding"],
        "bedrock": ["bedrock", "aws"],
        "fallback": ["fallback", "graceful", "falls back"],
        "sonnet": ["sonnet", "claude"],
        "sqlalchemy": ["sqlalchemy", "orm"],
        "sqlite": ["sqlite"],
        "docker": ["docker", "container"],
        "async": ["async", "httpx"],
    }

    mentioned = []
    missed = []

    for concept, keywords in concept_checks.items():
        if any(kw in what_seth_wants for kw in keywords):
            if any(kw in answer_lower for kw in keywords):
                mentioned.append(concept)
            else:
                missed.append(concept)

    feedback_parts = []

    if mentioned:
        feedback_parts.append(
            f"Good - you covered: {', '.join(mentioned)}."
        )

    if missed:
        feedback_parts.append(
            f"You might want to also mention: {', '.join(missed)}."
        )

    word_count = len(user_answer.split())
    if word_count > 200:
        feedback_parts.append(
            "Your answer is pretty long. In a 1-hour interview with multiple "
            "questions, aim for 30-60 seconds per initial answer. Let Seth "
            "ask follow-ups if he wants more detail."
        )
    elif word_count < 20:
        feedback_parts.append(
            "That's quite brief. You want to give enough detail to show depth "
            "of understanding without being asked to elaborate on everything."
        )

    return " ".join(feedback_parts) if feedback_parts else (
        "Decent answer. Compare it against the suggested response below to "
        "see if you missed anything."
    )


def run_session(num_rounds=None):
    """Run an interactive mock interview session."""
    print(SETH_INTRO)

    # Shuffle questions but keep a good mix of categories
    questions = list(QUESTION_BANK)
    random.shuffle(questions)

    if num_rounds:
        questions = questions[:num_rounds]

    total = len(questions)

    for i, q in enumerate(questions, 1):
        print(f"  [{i}/{total}]  Category: {q['category']}")
        print(f"  {'=' * 70}")
        print()
        print(f"  Seth: {q['question']}")
        print()

        # Get user's answer
        print("  Your answer (press Enter twice to submit, or type 'skip'/'quit'):")
        lines = []
        while True:
            try:
                line = input("  > ")
            except EOFError:
                return
            if line.strip().lower() == "quit":
                print("\n  Good luck tomorrow! You've got this.\n")
                return
            if line.strip().lower() == "skip":
                lines = []
                break
            if line == "" and lines and lines[-1] == "":
                lines.pop()  # Remove trailing empty line
                break
            lines.append(line)

        user_answer = "\n".join(lines).strip()

        # Feedback
        if user_answer:
            feedback = get_feedback(user_answer, q)
            print_section("Seth's feedback", feedback)
        else:
            print("\n  (Skipped)\n")

        # What Seth is looking for
        print_section("What Seth is looking for", q["what_seth_wants"], char="*")

        # Suggested strong answer
        print_section("Suggested answer", q["suggested_answer"], char="+")

        # Follow-ups
        if q["follow_ups"]:
            print("  --- Possible follow-ups Seth might ask ---")
            for fu in q["follow_ups"]:
                print(f"    - {fu}")
            print()

        if i < total:
            print(f"  {'_' * 70}")
            try:
                input("  Press Enter for the next question...")
            except EOFError:
                return
            print()

    print("\n" + "=" * 76)
    print("  SESSION COMPLETE")
    print("=" * 76)
    print()
    print(wrap_text(
        "You've gone through all the questions. A few general tips for tomorrow:"
    ))
    print()
    tips = [
        "Lead with the answer, then explain. Don't build up to a conclusion.",
        "When Seth asks 'why,' give the reason tied to THIS project, not generic best practices.",
        "It's fine to say 'I considered X but chose Y because...' - that shows decision-making.",
        "If you don't know something, say so. Then say what you'd do to find out.",
        "Have the live app ready to demo. A working demo is worth a thousand slides.",
        "Remember: Seth works on AI agents at scale. Connect your patterns to larger systems.",
    ]
    for j, tip in enumerate(tips, 1):
        print(f"  {j}. {tip}")
    print()
    print("  Good luck tomorrow!\n")


def main():
    parser = argparse.ArgumentParser(
        description="Seth Beckett Bot - Mock interviewer for Quiz Builder presentation"
    )
    parser.add_argument(
        "--rounds", "-r",
        type=int,
        default=None,
        help="Number of questions to ask (default: all)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all questions without starting a session"
    )
    args = parser.parse_args()

    if args.list:
        print("\n  All questions in the bank:\n")
        for i, q in enumerate(QUESTION_BANK, 1):
            print(f"  {i:2d}. [{q['category']}] {q['question'][:80]}...")
        print(f"\n  Total: {len(QUESTION_BANK)} questions\n")
        return

    run_session(args.rounds)


if __name__ == "__main__":
    main()
