"""
Corporate Standard Module: config
This module is part of the ARIA core framework.
"""
from pydantic_settings import BaseSettings
from pathlib import Path
import os

class Settings(BaseSettings):
    """
    Corporate Standard Class: Settings.
    """
    # Caminhos
    BASE_DIR: Path = Path(__file__).parent.parent
    ARIA_DB_PATH: str = "aria_risk.db"
    AFIS_DB_PATH: str = "../AFIS/afis_finance.db"   # relativo ao monorepo
    APEX_DB_PATH: str = "../APEX/apex_ar.db"        # relativo ao monorepo
    CHROMA_PATH: str = "app/rag/chroma_db"
    SBA_GUIDELINES_PATH: str = "app/rag/sba_guidelines"
    REPORTS_DIR: str = "data/reports"

    # LLM
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "claude-3-5-sonnet-20241022"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.1

    # RAG
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    RAG_TOP_K: int = 3
    RAG_SCORE_THRESHOLD: float = 0.65

    # Configurações de Risco do Usuário
    ANOMALY_SENSITIVITY: float = 0.05
    CRITICAL_ALERT_THRESHOLD: float = 0.75

    # Servidor
    HOST: str = "127.0.0.1"
    PORT: int = 8003
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    class Config:
        """
        Corporate Standard Class: Config.
        """
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# Sobrescreve caminhos de banco com base em variáveis de ambiente se presentes
if os.environ.get("AFIS_DB_PATH"):
    settings.AFIS_DB_PATH = os.environ.get("AFIS_DB_PATH")
if os.environ.get("APEX_DB_PATH"):
    settings.APEX_DB_PATH = os.environ.get("APEX_DB_PATH")
if os.environ.get("PORT"):
    settings.PORT = int(os.environ.get("PORT"))
