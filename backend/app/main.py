import os
import sys
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

BACKEND_ROOT = Path(__file__).resolve().parent.parent
os.chdir(BACKEND_ROOT)
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Asynchronously check and pull the Ollama embedding model on startup
    import asyncio
    from app.ai.embeddings import ensure_model_exists
    
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, ensure_model_exists)
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
