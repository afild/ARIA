# run.py
import sys
import os
from pathlib import Path
import logging

# Adiciona o diretório atual ao path do Python para permitir importações absolutas de app.
current_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(current_dir))

# Carrega variáveis de ambiente antes de qualquer importação interna
env_file = current_dir / ".env"
if env_file.exists():
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

def check_dependencies():
    """Valida se todas as dependências críticas estão instaladas."""
    required = ["fastapi", "uvicorn", "langchain", "langgraph", "chromadb", 
                "sentence_transformers", "sklearn", "xgboost", "shap", "networkx"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)
            
    if missing:
        print(f"❌ Dependências ausentes: {', '.join(missing)}")
        print("   Por favor execute: pip install -r requirements.txt")
        sys.exit(1)

def initialize_database():
    """Inicializa o banco SQLite do ARIA (aria_risk.db)."""
    from app.database.db_manager import init_db
    init_db()
    print("✅ Banco de dados SQLite ARIA inicializado com sucesso.")

def check_connections():
    """Verifica e reporta as conexões com AFIS e APEX."""
    from app.plugins.afis_reader import AFISReader
    from app.plugins.apex_reader import APEXReader
    
    afis = AFISReader()
    apex = APEXReader()
    
    print(f"📡 AFIS Connected: {afis.is_connected()} (Caminho: {afis.db_path})")
    print(f"📡 APEX Connected: {apex.is_connected()} (Caminho: {apex.db_path})")

def initialize_rag():
    """Carrega ou inicializa a coleção vetorial de diretrizes SBA."""
    from app.rag.vector_store import get_or_create_vector_store
    vs = get_or_create_vector_store()
    print("✅ Módulo RAG inicializado com sucesso.")

if __name__ == "__main__":
    check_dependencies()
    initialize_database()
    check_connections()
    initialize_rag()

    port = int(os.environ.get("PORT", 8003))
    host = os.environ.get("HOST", "127.0.0.1")
    ai_mode = "LLM (Claude 3.5)" if os.environ.get("ANTHROPIC_API_KEY") else "Offline Heuristic Fallback"

    print("=" * 65)
    print("   ARIA — AI Risk & Fraud Intelligence Analyzer")
    print("=" * 65)
    print(f"   AI Mode   : {ai_mode}")
    print(f"   Dashboard : http://{host}:{port}/static/index.html")
    print(f"   API Docs  : http://{host}:{port}/docs")
    print("=" * 65)

    import uvicorn
    uvicorn.run("app.main:app", host=host, port=port, reload=False)


