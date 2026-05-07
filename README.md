# Quiz Builder - AI-Powered Knowledge Quiz Generator

An MVP web application that generates multiple-choice quizzes on any topic using AI. Built with FastAPI, React, and Claude Sonnet 4.5 via AWS Bedrock.

## How It Works

### 1. User Enters a Topic
The user visits the home page and types a topic (e.g., "Photosynthesis", "Neural Networks", "Ancient Rome") into the input field, then clicks "Generate Quiz".

### 2. Wikipedia Retrieval (Context Injection)
The backend first calls the Wikipedia REST API to fetch a summary for the topic. This summary provides factual reference material that gets injected into the LLM prompt. If Wikipedia has no matching article, the app skips this step and generates the quiz using only the model's training knowledge. This step takes under a second and significantly improves the factual accuracy of generated questions when a Wikipedia article is available.

### 3. LLM Quiz Generation
The backend sends a structured prompt to Claude Sonnet 4.5 via AWS Bedrock, requesting exactly 5 multiple-choice questions in JSON format. The prompt includes the Wikipedia context (if available) and instructs the model to:
- Create questions that test understanding, not just recall
- Provide 4 plausible options (A-D) with one correct answer
- Vary difficulty (2 easy, 2 medium, 1 hard)
- Include a brief explanation for each correct answer

The response is parsed, validated (exactly 5 questions, valid A-D answers), and saved to the SQLite database.

### 4. User Takes the Quiz
The frontend navigates to the quiz page and displays the 5 questions. The API deliberately hides the correct answers at this stage, so users cannot cheat by inspecting network responses. The user selects one answer per question using radio buttons. A progress indicator shows how many questions have been answered.

### 5. Quiz Submission and Scoring
When the user submits, their answers are sent to the backend, which compares each selection against the stored correct answers and computes the score. The result (score, total, correct answers, user answers, and explanations) is saved to the database and returned to the frontend.

### 6. Results Review
The results page displays:
- A color-coded score badge (e.g., 4/5, "Good job!")
- Each question with the user's answer and the correct answer highlighted
- A green left border for correct answers, red for incorrect
- The AI-generated explanation for each question

### 7. Quiz History
Users can browse all past quizzes on the history page, which shows the topic, date, and most recent score for each quiz. From here they can retake any quiz or review their previous results.

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
