# Quiz Builder - AI-Powered Knowledge Quiz Generator

An MVP web application that generates multiple-choice quizzes on any topic using AI. Built with FastAPI, React, and Claude Sonnet 4 via AWS Bedrock.

## System Architecture

```
┌─────────────┐       ┌──────────────────┐       ┌──────────────┐
│  React SPA  │──────>│  FastAPI Backend  │──────>│  AWS Bedrock  │
│  (Vite)     │  /api │                  │       │  (Claude S4)  │
└─────────────┘       │  - Quiz routes   │       └──────────────┘
                      │  - SQLite/SA     │
                      │  - SPA serving   │──────>┌──────────────┐
                      └──────────────────┘       │  Wikipedia   │
                                                 │  REST API    │
                                                 └──────────────┘
```

**Frontend:** React 18 + Vite + React Router. A single-page application with four routes: home (topic input), quiz (answer questions), results (score + explanations), and history (past quizzes). Component-level state with `useState`/`useEffect` hooks. The Vite dev server proxies `/api` requests to the backend.

**Backend:** FastAPI with a modular structure. The quiz generation service is separated from API routes, and the Wikipedia retrieval service is isolated from the generation logic. SQLAlchemy ORM manages persistence. In production, Gunicorn runs 2 Uvicorn ASGI workers and serves the built React assets as static files.

**Database:** SQLite via SQLAlchemy. Three tables: `quizzes` (topic + timestamp), `questions` (text, options A-D, correct answer, explanation), and `quiz_results` (score, user answers as JSON). SQLite requires no external service, keeping the app fully self-contained.

**Deployment:** Multi-stage Docker build (Node for frontend, Python for backend) pushed to AWS ECR via a SageMaker notebook, then deployed on ECS Express. Health check at `/api/health`.

## AI Tool Selection

**Model:** Claude Sonnet 4 (`us.anthropic.claude-sonnet-4-20250514-v1:0`) via AWS Bedrock.

**Reasoning:**
- **Structured output quality** - Sonnet 4 reliably produces well-formed JSON without extra formatting, which is critical for programmatic quiz parsing
- **Factual accuracy** - Strong reasoning capabilities produce plausible distractors and accurate correct answers, especially when augmented with Wikipedia context
- **AWS-native integration** - Bedrock avoids managing API keys for a separate service; credentials flow through IAM, matching the existing deployment infrastructure
- **Cost/latency balance** - Sonnet offers better question quality than Haiku at an acceptable latency (~3-5s per quiz generation)

**Retrieval augmentation:** Before generating questions, the app fetches a Wikipedia summary for the topic via the REST API (`/api/rest_v1/page/summary/{topic}`). This context is injected into the prompt to improve factual accuracy. The retrieval is best-effort; if Wikipedia has no article, the quiz is still generated using the model's training knowledge.

## Key Design Decisions

1. **Answers hidden until submission** - The `GET /api/quiz/{id}` endpoint deliberately omits `correct_answer` and `explanation` fields. These are only returned by the `POST /submit` endpoint after the user has committed their answers. This prevents cheating via browser dev tools.

2. **JSON prompt strategy** - Rather than using Bedrock's tool_use/function_calling for structured output, the prompt explicitly requests JSON and the backend strips markdown code fences if present. This is simpler and sufficient for the quiz format.

3. **SQLite for persistence** - For an MVP, SQLite eliminates external dependencies while still demonstrating proper ORM usage, migrations readiness, and relational data modeling. Switching to PostgreSQL only requires changing the connection string.

4. **Session storage for results** - After submitting a quiz, the full result (including correct answers and user selections) is stored in `sessionStorage` so the results page loads instantly without an extra API call.

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

Visit `http://localhost:5173` for the dev frontend (proxies API to backend on port 5000).

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

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/quiz/generate` | Generate a quiz from a topic |
| `GET` | `/api/quiz/{id}` | Get quiz (answers hidden) |
| `POST` | `/api/quiz/{id}/submit` | Submit answers, get score + explanations |
| `GET` | `/api/quizzes` | List past quizzes with scores |

## Bonus Features

- **Wikipedia retrieval** for improved factual accuracy
- **Persistent quiz history** with SQLite (browse and retake past quizzes)
- **Answer explanations** generated by AI for each question
