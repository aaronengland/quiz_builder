# Quiz Builder
## AI-Powered Knowledge Quiz Generator

**[Web App](https://6s9kx6uqpp.us-west-2.awsapprunner.com/)**

An MVP web application that generates multiple-choice quizzes on any topic using AI. Built with FastAPI, React, and Claude Sonnet 4.5 via AWS Bedrock.

## Project Structure

```
quiz_builder/
├── backend/
│   ├── config.py                  # Pydantic settings (port, dev mode, database URL)
│   ├── database.py                # SQLAlchemy engine, session factory, and base class
│   ├── main.py                    # FastAPI app factory, Bedrock client setup, SPA serving
│   ├── models.py                  # ORM models (Quiz, Question, QuizResult)
│   ├── schemas.py                 # Pydantic request/response models for API validation
│   ├── routes/
│   │   └── quiz.py                # API endpoints (generate, get, submit, list)
│   └── services/
│       ├── quiz_generator.py      # Bedrock prompt construction, API call, response parsing
│       └── wikipedia.py           # Wikipedia REST API client for topic context retrieval
└── frontend/
    ├── vite.config.js             # Vite config with /api proxy to backend
    └── src/
        ├── main.jsx               # React entry point with BrowserRouter
        ├── App.jsx                # Route definitions and navbar
        ├── components/
        │   ├── QuestionCard.jsx   # Single question with radio button options
        │   └── ScoreDisplay.jsx   # Color-coded score badge
        └── pages/
            ├── Home.jsx           # Topic input and quiz generation trigger
            ├── Quiz.jsx           # Answer selection and submission
            ├── Results.jsx        # Score review with explanations
            └── History.jsx        # Past quiz list with retake/review links
```

## How It Works

1. **User Enters a Topic**
   - `frontend/src/pages/Home.jsx`
   - User types a topic (e.g., "Photosynthesis", "Neural Networks", "Ancient Rome") and clicks "Generate Quiz".

2. **Validate Request**
   - `backend/schemas.py`
   - Pydantic validates the request body, ensuring topic is a non-empty string with a maximum length of 200 characters. Rejects malformed requests with a 422 error.

3. **Wikipedia Retrieval**
   - `backend/services/wikipedia.py`
   - Calls the Wikipedia REST API at `https://en.wikipedia.org/api/rest_v1/page/summary/{topic}` to fetch a plain-text summary. This is a free, public API that requires no authentication. The summary is injected into the LLM prompt as grounding context. 5-second timeout. If no article is found or the request times out, continues without context.

4. **LLM Quiz Generation**
   - `backend/services/quiz_generator.py`
   - Sends the following prompt to Claude Sonnet 4.5 via AWS Bedrock (Wikipedia context injected when available):
   ```
   Generate a quiz about: {topic}

   Use the following reference material to ensure factual accuracy:
   ---
   {wikipedia_summary}
   ---

   Create exactly 5 multiple-choice questions. Each question must have
   4 options (A-D) with exactly one correct answer.

   Respond with ONLY valid JSON in this exact format:
   {
     "questions": [
       {
         "question_text": "...",
         "option_a": "...",
         "option_b": "...",
         "option_c": "...",
         "option_d": "...",
         "correct_answer": "A",
         "explanation": "Brief explanation of why the correct answer
                         is right and why the others are wrong."
       }
     ]
   }

   Rules:
   - Questions should test understanding, not just recall
   - Distractors should be plausible but clearly wrong
   - Vary question difficulty (2 easy, 2 medium, 1 hard)
   - Explanations should be 1-2 sentences
   - correct_answer must be exactly one of: A, B, C, D
   ```

5. **Validate LLM Output (with retry)**
   - `backend/services/quiz_generator.py`
   - `backend/schemas.py`
   - Parses the JSON response and validates each question through a Pydantic model (`GeneratedQuestion`). Enforces: exactly 5 questions, all fields present, `correct_answer` must be A/B/C/D, correct data types for every field.
   - If validation fails (malformed JSON, missing fields, wrong types, invalid answer letter), the app automatically retries the LLM call up to 3 times. Each retry sends the same prompt and re-validates the new response. The app only returns an error to the user if all 3 attempts fail validation.

6. **Fact-Check Verification (with retry)**
   - `backend/services/quiz_generator.py`
   - A second LLM call reviews each question against the Wikipedia context and checks whether the marked correct answer is factually accurate. The same retry logic applies: if the verification output fails Pydantic validation, it retries up to 3 times. If all retries fail, the app falls back to the original unverified questions. Sends the following prompt:
   ```
   You are a fact-checker. Review the following quiz questions about
   "{topic}" and verify that each question's correct_answer is
   factually accurate.

   Reference material:
   ---
   {wikipedia_summary}
   ---

   Questions to verify:
   {generated_questions_json}

   For each question, determine if the marked correct_answer is truly
   correct. If a question has an incorrect correct_answer, fix it by
   changing the correct_answer field to the right letter and updating
   the explanation.

   Return all 5 questions. Keep questions unchanged if they are
   correct. Only modify questions that have factual errors.
   ```
   - The output is re-validated through Pydantic. If the verification call fails for any reason, falls back to the original unverified questions.

7. **Persist to Database**
   - `backend/routes/quiz.py`
   - `backend/models.py`
   - `backend/database.py`
   - Saves the quiz and its questions to SQLite via SQLAlchemy. Returns the quiz to the frontend with correct answers hidden.

8. **User Takes the Quiz**
   - `frontend/src/pages/Quiz.jsx`
   - `frontend/src/components/QuestionCard.jsx`
   - Displays 5 questions with radio buttons for A-D. The API deliberately omits correct answers at this stage so users cannot cheat by inspecting network responses. A progress indicator tracks how many questions have been answered.

9. **Submit and Score**
   - `backend/routes/quiz.py`
   - `backend/schemas.py`
   - Pydantic validates the submitted answers. The backend compares each selection against the stored correct answers, computes the score, and persists the result to the database.

10. **Results Review**
    - `frontend/src/pages/Results.jsx`
    - `frontend/src/components/ScoreDisplay.jsx`
    - Displays a color-coded score badge (e.g., 4/5, "Good job!"). Each question shows the user's answer vs. the correct answer with a green/red border and the AI-generated explanation.

11. **Quiz History**
    - `frontend/src/pages/History.jsx`
    - `backend/routes/quiz.py`
    - Browse all past quizzes with topics, dates, and most recent scores. Retake or review any quiz.

## System Architecture

**Frontend:** React 18 + Vite + React Router. Four routes: home (topic input), quiz (answer questions), results (score + explanations), and history (past quizzes). Component-level state with `useState`/`useEffect` hooks. Vite dev server proxies `/api` requests to the backend.

**Backend:** FastAPI with a modular structure. Quiz generation and Wikipedia retrieval are isolated services, separate from the API routes. SQLAlchemy ORM manages persistence. In production, Gunicorn runs 2 Uvicorn ASGI workers and serves the built React assets as static files.

**Database:** SQLite via SQLAlchemy. Three tables:
- `quizzes` - topic and timestamp
- `questions` - question text, options A-D, correct answer, explanation (foreign key to quizzes)
- `quiz_results` - score, total, user answers as JSON (foreign key to quizzes)

**Deployment:** Multi-stage Docker build (Node for frontend, Python for backend) pushed to AWS ECR via a SageMaker notebook, then deployed on App Runner. Health check at `/api/health`.

## AI Tool Selection

**Model:** Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`) via AWS Bedrock.

**Why this model:**
- **Structured output quality** - Reliably produces well-formed JSON, critical for programmatic quiz parsing
- **Factual accuracy** - Strong reasoning produces plausible distractors and accurate correct answers, especially with Wikipedia context
- **AWS-native integration** - Bedrock avoids managing API keys for a separate service; credentials flow through IAM
- **Cost/latency balance** - Better question quality than Haiku at acceptable latency (~3-5s per generation)

## Key Design Decisions

1. **Answers hidden until submission** - The `GET /api/quiz/{id}` endpoint omits `correct_answer` and `explanation`. These are only returned after submission, preventing cheating via browser dev tools.

2. **JSON prompt strategy** - Rather than using Bedrock's tool_use for structured output, the prompt explicitly requests JSON and the backend strips markdown code fences if present. Simpler and sufficient for this format.

3. **SQLite for persistence** - SQLite was chosen for this MVP for several reasons:
   - **Zero infrastructure** - No external database server to provision, configure, or pay for. The database is a single file that lives alongside the application.
   - **Self-contained demo** - A reviewer can clone the repo, install dependencies, and run the app immediately without setting up a database service.
   - **Sufficient for the use case** - This is a single-user quiz app with low write volume. SQLite handles concurrent reads well and the write pattern (one quiz generation at a time) avoids SQLite's single-writer limitation.
   - **Proper ORM usage** - Despite using SQLite, the app uses SQLAlchemy with relational models, foreign keys, and cascading deletes, demonstrating production-grade data modeling.
   - **Easy migration path** - Switching to PostgreSQL (e.g., Amazon RDS) only requires changing the `DATABASE_URL` connection string in the environment. No code changes needed because SQLAlchemy abstracts the database engine. This would be the natural next step if the app needed to support multiple concurrent users or persistent storage across container restarts.

4. **Wikipedia summary vs. full article (chunking)** - The app uses Wikipedia's `/page/summary/` endpoint, which returns a concise 1-3 paragraph extract. This was a deliberate choice:
   - **No chunking needed** - The summary is short enough to fit entirely in the LLM prompt alongside the generation instructions, well within the model's context window.
   - **Higher signal-to-noise ratio** - The summary contains the most relevant facts about a topic without filler. Feeding the entire Wikipedia article would include sections (e.g., "See also", "References", footnotes) that add noise without improving question quality.
   - **Lower latency** - A single lightweight API call (~100ms) vs. fetching and processing a full article.
   - **Scaling to longer sources** - If the app needed to support longer documents (e.g., textbook chapters, research papers, or full Wikipedia articles), the approach would change:
     1. Split the document into overlapping chunks (e.g., 500-token windows with 50-token overlap)
     2. Generate embeddings for each chunk using an embedding model (e.g., Amazon Titan Embeddings via Bedrock)
     3. Store embeddings in a vector database (e.g., Amazon OpenSearch Serverless, Pinecone, or pgvector)
     4. At query time, embed the user's topic, retrieve the top-k most relevant chunks via similarity search, and inject only those chunks into the prompt
   - This retrieval-augmented generation (RAG) pipeline would improve accuracy for niche topics while keeping prompt size manageable. For this MVP, the Wikipedia summary provides sufficient grounding without that complexity.

5. **Session storage for results** - After submission, the full result is stored in `sessionStorage` so the results page loads instantly without an extra API call.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/quiz/generate` | Generate a quiz from a topic |
| `GET` | `/api/quiz/{id}` | Get quiz (answers hidden) |
| `POST` | `/api/quiz/{id}/submit` | Submit answers, get score + explanations |
| `GET` | `/api/quizzes` | List past quizzes with scores |

## Setup

### Prerequisites
- Python 3.11+
- Node.js 20+
- AWS credentials with Bedrock access

### Environment Variables

Create a `.env` file in the project root:

```
AWS_ACCESS_KEY_ID=your-access-key-here
AWS_SECRET_ACCESS_KEY=your-secret-key-here
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0  # optional, defaults to Sonnet 4.5
```

### Local Development

```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` (proxies API to backend on port 5000).

### Docker

```bash
docker build -t quiz-builder-image .
docker run -p 5000:5000 \
  -e AWS_ACCESS_KEY_ID=your-key \
  -e AWS_SECRET_ACCESS_KEY=your-secret \
  -e AWS_REGION=us-west-2 \
  quiz-builder-image
```

Visit `http://localhost:5000`.

### AWS Deployment

Upload the repo to SageMaker and run `notebook-ecr-image.ipynb` to build and push the Docker image to ECR. Then create an App Runner service pointing to the ECR image with:
- Container port: 5000
- Health check path: `/api/health`
- Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`

## Anticipated Q&A

**Q: Why did you choose Claude Sonnet 4.5 over other models?**
Sonnet 4.5 hits the right balance for this use case. It reliably produces well-formed JSON (critical since the app parses LLM output programmatically), has strong factual reasoning for generating accurate quiz questions, and integrates natively with AWS Bedrock so there are no external API keys to manage. Haiku would be faster and cheaper but produces lower-quality distractors and explanations. Opus would be higher quality but adds latency and cost that isn't justified for a 5-question quiz.

**Q: How do you prevent hallucinations in the generated questions?**
Three layers: (1) Wikipedia context injection grounds the LLM in factual source material before generation, (2) a second LLM call acts as a fact-checker, reviewing each question against the Wikipedia context and correcting any inaccurate answers, and (3) Pydantic validation ensures the output structure is correct. The verification step is the most important - it catches cases where the model generates a plausible-sounding but incorrect answer.

**Q: What happens if the LLM returns malformed output?**
Every LLM call is wrapped in retry logic. The response is parsed and validated through a Pydantic model that enforces the exact schema: 5 questions, all fields present, `correct_answer` must be A/B/C/D, correct data types. If validation fails, the app retries the same prompt up to 3 times. Only after all retries are exhausted does it return an error. For the verification step specifically, if all retries fail, the app falls back to the original unverified questions rather than failing entirely.

**Q: Why SQLite instead of PostgreSQL or DynamoDB?**
SQLite is the right choice for an MVP demo. It requires zero infrastructure (no database server to provision), makes the app fully self-contained (a reviewer can clone and run immediately), and is sufficient for the write pattern (one quiz generation at a time). The app still uses SQLAlchemy with proper relational modeling, foreign keys, and cascading deletes. Switching to PostgreSQL only requires changing the `DATABASE_URL` connection string - no code changes - because SQLAlchemy abstracts the database engine. That would be the natural next step for multi-user or persistent storage needs.

**Q: Why didn't you use chunking for the Wikipedia content?**
The app uses Wikipedia's summary endpoint, which returns a concise 1-3 paragraph extract. This is intentionally short enough to fit entirely in the prompt without chunking, and has a higher signal-to-noise ratio than a full article. If the app needed to support longer sources (textbook chapters, research papers), I would implement a RAG pipeline: split documents into overlapping chunks, generate embeddings via Amazon Titan Embeddings, store them in a vector database, and retrieve only the most relevant chunks at query time via similarity search.

**Q: How do you prevent users from cheating?**
The `GET /api/quiz/{id}` endpoint returns questions through the `QuestionOut` Pydantic schema, which deliberately omits the `correct_answer` and `explanation` fields. These are only returned by the `POST /api/quiz/{id}/submit` endpoint after the user has committed their answers. Even inspecting the network response in browser dev tools won't reveal the answers before submission.

**Q: Why FastAPI over Flask or Django?**
FastAPI provides automatic request/response validation through Pydantic (which we use extensively), built-in async support (needed for the Wikipedia API call), auto-generated API docs at `/docs`, and strong type hints throughout. Flask would require adding these capabilities manually. Django would bring unnecessary complexity (admin panel, ORM migrations, template engine) for a lightweight API.

**Q: How would you scale this for production?**
Several changes: (1) swap SQLite for PostgreSQL on Amazon RDS for concurrent writes and persistent storage, (2) add user authentication (e.g., Cognito or Supabase Auth), (3) add rate limiting to prevent abuse of the Bedrock API, (4) cache Wikipedia summaries to reduce external API calls for repeated topics, (5) implement a full RAG pipeline for richer source material, and (6) add monitoring/observability with CloudWatch or similar.

**Q: Why a monolithic Docker image instead of separate frontend/backend services?**
For an MVP, a single container simplifies deployment (one App Runner service, one health check, one set of env vars). The frontend is just static files served by FastAPI, so there is no runtime overhead. In production, you would split them: serve the React build from CloudFront/S3 for global CDN caching, and run the API separately. But for a demo, the monolith is simpler to deploy and review.

**Q: What tradeoffs did you make for the 2-day timeline?**
The main tradeoffs were: (1) SQLite over a managed database, knowing the migration path is a one-line change, (2) no authentication since it is not required for the demo, (3) Wikipedia summary instead of a full RAG pipeline, which provides 80% of the accuracy benefit at 10% of the complexity, and (4) minimal UI styling since the instructions explicitly said UI polish is not the priority. Each tradeoff was chosen to maximize functionality within the time constraint while keeping a clear path to production improvements.

**Q: How do you ensure data type consistency across the stack?**
Pydantic models validate data at every boundary: incoming API requests (`GenerateRequest`, `SubmitRequest`), LLM output (`GeneratedQuestion`), and API responses (`QuizOut`, `SubmitResponse`). This means malformed data is caught immediately at the point of entry rather than causing downstream errors. SQLAlchemy column types provide a second layer of enforcement at the database level. Input length is also constrained (topic is capped at 200 characters) to prevent abuse of the LLM API.

**Q: What if you need to swap the LLM model?**
The Bedrock model ID is configurable via the `BEDROCK_MODEL_ID` environment variable, defaulting to Claude Sonnet 4.5. Switching to a different model (e.g., Haiku for lower cost, or a newer Claude release) only requires changing this environment variable. No code changes needed.
