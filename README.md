# Quiz Builder - AI-Powered Knowledge Quiz Generator

**[Live Demo](https://6s9kx6uqpp.us-west-2.awsapprunner.com/)**

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
   - Pydantic validates the request body, ensuring topic is a non-empty string. Rejects malformed requests with a 422 error.

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

5. **Validate LLM Output**
   - `backend/services/quiz_generator.py`
   - `backend/schemas.py`
   - Parses the JSON response and validates each question through a Pydantic model (`GeneratedQuestion`). Enforces: exactly 5 questions, all fields present, `correct_answer` must be A/B/C/D, correct data types for every field.

6. **Fact-Check Verification**
   - `backend/services/quiz_generator.py`
   - A second LLM call reviews each question against the Wikipedia context and checks whether the marked correct answer is factually accurate. Sends the following prompt:
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

**Deployment:** Multi-stage Docker build (Node for frontend, Python for backend) pushed to AWS ECR via a SageMaker notebook, then deployed on ECS Express. Health check at `/api/health`.

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

3. **SQLite for persistence** - Eliminates external dependencies while demonstrating proper ORM usage and relational modeling. Switching to PostgreSQL only requires changing the connection string.

4. **Session storage for results** - After submission, the full result is stored in `sessionStorage` so the results page loads instantly without an extra API call.

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

Upload the repo to SageMaker and run `notebook-ecr-image.ipynb` to build and push the Docker image to ECR. Then create an ECS Express service pointing to the ECR image with:
- Container port: 5000
- Health check path: `/api/health`
- Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
