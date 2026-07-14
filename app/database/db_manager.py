"""
Corporate Standard Module: db_manager
This module is part of the ARIA core framework.
"""
import sqlite3
import logging
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.config import settings

# Conexão SQLAlchemy
engine = create_engine(
    f"sqlite:///{settings.ARIA_DB_PATH}",
    connect_args={"check_same_thread": False}
)

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: sqlite3.Connection, connection_record: object) -> None:
    """
    Configura pragmas de concorrência e resiliência (WAL e Normal Synchronous).
    Permite leituras enquanto gravações estão ocorrendo sem database locks agressivos.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db() -> None:
    """
    Inicializa o banco de dados do ARIA usando schema.sql caso ele não exista.
    Garante resiliência ao carregar esquemas necessários sem subscrever logs atuais.
    """
    db_path = Path(settings.ARIA_DB_PATH)
    schema_path = Path(__file__).parent / "schema.sql"
    
    if not db_path.exists():
        logging.info("Inicializando banco de dados ARIA a partir de schema.sql...")
        if schema_path.exists():
            with sqlite3.connect(db_path) as conn:
                with open(schema_path, "r", encoding="utf-8") as f:
                    conn.executescript(f.read())
            logging.info("Banco de dados ARIA criado com sucesso.")
        else:
            logging.error(f"schema.sql não encontrado no caminho {schema_path}")
    else:
        # Garante que as tabelas de logs existam mesmo se o arquivo DB já existir de execuções parciais
        if schema_path.exists():
            try:
                with sqlite3.connect(db_path) as conn:
                    with open(schema_path, "r", encoding="utf-8") as f:
                        conn.executescript(f.read())
            except Exception as e:
                logging.warning(f"Erro ao re-rodar schema.sql (Pode ser ignorado se tabelas já existem): {e}")

def get_db() -> Generator[Session, None, None]:
    """
    Dependency para injeção de sessão local nos endpoints do FastAPI.
    Garante o fechamento da sessão no bloco finally, prevenindo connection leaks na camada HTTP.
    
    Yields:
        Session: Sessão ativa do SQLAlchemy conectada ao banco SQLite.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()



