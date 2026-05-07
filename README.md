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

```
                      ┌─────────────────────────────┐
                      │   User Enters a Topic        │
                      │   (Home.jsx)                 │
                      └──────────────┬──────────────┘
                                     │
                                     v
                      ┌─────────────────────────────┐
                      │   Validate Request           │
                      │   (schemas.py)               │
                      │                              │
                      │   Pydantic validates the     │
                      │   request body, ensuring     │
                      │   topic is a non-empty       │
                      │   string. Rejects malformed  │
                      │   requests with a 422 error. │
                      └──────────────┬──────────────┘
                                     │
                                     v
                      ┌─────────────────────────────┐
                      │   Wikipedia Retrieval        │
                      │   (wikipedia.py)             │
                      │                              │
                      │   Calls Wikipedia REST API   │
                      │   to fetch a plain-text      │
                      │   summary for the topic.     │
                      │   5-second timeout. If no    │
                      │   article found or timeout,  │
                      │   continues without context. │
                      └──────────────┬──────────────┘
                                     │
                                     v
                      ┌─────────────────────────────┐
                      │   LLM Quiz Generation        │
                      │   (quiz_generator.py)        │
                      │                              │
                      │   Sends structured prompt    │
                      │   to Claude Sonnet 4.5 via   │
                      │   AWS Bedrock with Wikipedia │
                      │   context injected. Requests │
                      │   5 questions in JSON.       │
                      └──────────────┬──────────────┘
                                     │
                                     v
                      ┌─────────────────────────────┐
                      │   Validate LLM Output        │
                      │   (quiz_generator.py,        │
                      │    schemas.py)               │
                      │                              │
                      │   Parses JSON response and   │
                      │   validates each question    │
                      │   through Pydantic model.    │
                      │   Enforces: 5 questions,     │
                      │   all fields present, valid  │
                      │   A/B/C/D answer, correct    │
                      │   data types.                │
                      └──────────────┬──────────────┘
                                     │
                                     v
                      ┌─────────────────────────────┐
                      │   Fact-Check Verification    │
                      │   (quiz_generator.py)        │
                      │                              │
                      │   Second LLM call reviews    │
                      │   each question against the  │
                      │   Wikipedia context. Fixes   │
                      │   incorrect answers and      │
                      │   updates explanations.      │
                      │   Output re-validated        │
                      │   through Pydantic. Falls    │
                      │   back to originals on       │
                      │   failure.                   │
                      └──────────────┬──────────────┘
                                     │
                                     v
                      ┌─────────────────────────────┐
                      │   Persist to Database        │
                      │   (routes/quiz.py,           │
                      │    models.py, database.py)   │
                      │                              │
                      │   Saves quiz and questions   │
                      │   to SQLite via SQLAlchemy.  │
                      │   Returns quiz to frontend   │
                      │   with answers hidden.       │
                      └──────────────┬──────────────┘
                                     │
                                     v
                      ┌─────────────────────────────┐
                      │   User Takes the Quiz        │
                      │   (Quiz.jsx,                 │
                      │    QuestionCard.jsx)         │
                      │                              │
                      │   Displays 5 questions with  │
                      │   radio buttons. Correct     │
                      │   answers hidden from API    │
                      │   response. Tracks progress. │
                      └──────────────┬──────────────┘
                                     │
                                     v
                      ┌─────────────────────────────┐
                      │   Submit and Score           │
                      │   (routes/quiz.py,           │
                      │    schemas.py)               │
                      │                              │
                      │   Pydantic validates the     │
                      │   submitted answers. Backend │
                      │   compares against stored    │
                      │   correct answers, computes  │
                      │   score, persists result.    │
                      └──────────────┬──────────────┘
                                     │
                                     v
                      ┌─────────────────────────────┐
                      │   Results Review             │
                      │   (Results.jsx,              │
                      │    ScoreDisplay.jsx)         │
                      │                              │
                      │   Color-coded score badge.   │
                      │   Each question shows user   │
                      │   answer vs. correct answer  │
                      │   with AI explanation.       │
                      └──────────────┬──────────────┘
                                     │
                                     v
                      ┌─────────────────────────────┐
                      │   Quiz History               │
                      │   (History.jsx,              │
                      │    routes/quiz.py)           │
                      │                              │
                      │   Browse past quizzes with   │
                      │   topics, dates, and scores. │
                      │   Retake or review any quiz. │
                      └─────────────────────────────┘
```

## System Architecture

```
┌─────────────┐       ┌──────────────────┐       ┌──────────────┐
│  React SPA  │──────>│  FastAPI Backend  │──────>│  AWS Bedrock  │
│  (Vite)     │  /api │                  │       │  (Claude 4.5) │
└─────────────┘       │  - Quiz routes   │       └──────────────┘
                      │  - SQLite/SA     │
                      │  - SPA serving   │──────>┌──────────────┐
                      └──────────────────┘       │  Wikipedia   │
                                                 │  REST API    │
                                                 └──────────────┘
```

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
