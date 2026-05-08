import logging
import os
import sys

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

from config import get_settings
from database import engine, Base
from routes.quiz import router as quiz_router, set_bedrock_client

# Load .env from project root (one level up from backend/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("quiz_builder")


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    # Create database tables
    Base.metadata.create_all(bind=engine)

    app = FastAPI(
        title="Quiz Builder API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    # Bedrock client
    bedrock = boto3.client(
        "bedrock-runtime",
        region_name=os.environ.get("AWS_REGION", "us-west-2"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", ""),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
    )
    set_bedrock_client(bedrock)

    # Quiz routes
    app.include_router(quiz_router)

    # Serve React frontend (SPA catch-all)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    FRONTEND_BUILD = os.path.join(BASE_DIR, "frontend_build")

    if os.path.exists(FRONTEND_BUILD):
        app.mount(
            "/assets",
            StaticFiles(directory=os.path.join(FRONTEND_BUILD, "assets")),
            name="static-assets",
        )

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            if full_path.startswith("api/"):
                return JSONResponse(
                    status_code=404,
                    content={"error": "Not found"},
                )

            file_path = os.path.join(FRONTEND_BUILD, full_path)
            if full_path and os.path.isfile(file_path):
                return FileResponse(file_path)

            return FileResponse(os.path.join(FRONTEND_BUILD, "index.html"))
    else:
        logger.warning("Frontend build directory not found: %s", FRONTEND_BUILD)

    logger.info("Quiz Builder FastAPI app initialized")
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.is_dev,
    )
