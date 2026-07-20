"""
Corporate Standard Module: main
This module is part of the ARIA core framework.
"""
from typing import Any
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.database.db_manager import init_db
from app.rag.vector_store import get_or_create_vector_store
from app.api.router import api_router

# Configuração de Logs básica
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialização do banco local se necessário
    init_db()
    
    # Inicializa RAG (Chroma ou fallback)
    get_or_create_vector_store()
    
    logging.info("ARIA AI Risk Analyzer iniciado e pronto.")
    yield
    logging.info("ARIA AI Risk Analyzer desligando.")

app = FastAPI(
    title="ARIA — AI Risk & Fraud Intelligence Analyzer",
    description="Modulo de gerenciamento de risco, fraudes contábeis e elegibilidade de crédito (SBA)",
    version="0.2.0",
    lifespan=lifespan
)

# Habilita CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra os endpoints da API com prefixo /api
app.include_router(api_router, prefix="/api")

# Monta diretórios estáticos e de relatórios
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

reports_dir = Path(settings.REPORTS_DIR).resolve()
reports_dir.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(reports_dir)), name="reports")

# Redirect root para static/index.html
from fastapi.responses import RedirectResponse
@app.get("/")
def read_root() -> Any:
    """
    Standard corporate docstring for read_root.
    """
    return RedirectResponse(url="/static/index.html")


