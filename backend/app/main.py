import os
import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import analysis
from app.routers import ai_chat
from app.routers import workspaces
from app.auth.auth_router import router as auth_router
from app.middleware.auth import AuthMiddleware

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent
os.chdir(BACKEND_ROOT)
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eagerly initialise the embedding provider so misconfiguration
    # surfaces at startup rather than on the first user request.
    from app.ai.embeddings import get_embedding_provider

    provider = get_embedding_provider()
    logger.info(
        "Embedding provider ready: %s (dim=%d)",
        settings.embedding_provider,
        provider.dimension,
    )
    yield


app = FastAPI(
    title="WhatsApp Chat Analyzer API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(AuthMiddleware)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(analysis.router)
app.include_router(ai_chat.router)
app.include_router(workspaces.router)


@app.get("/health")
def health():
    return {"status": "ok"}
