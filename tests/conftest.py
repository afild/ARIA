# tests/conftest.py
import sys
import os
from pathlib import Path
import pytest

# Adiciona a pasta raiz do ARIA ao path do Python
root_dir = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(root_dir))

# Configura variáveis de ambiente exclusivas para a suíte de testes
os.environ["ARIA_DB_PATH"] = "aria_test.db"
os.environ["AFIS_DB_PATH"] = "afis_test.db"
os.environ["APEX_DB_PATH"] = "apex_test.db"
os.environ["PORT"] = "8009"
os.environ["DEBUG"] = "true"

@pytest.fixture(scope="session", autouse=True)
def clean_test_dbs():
    """Garante que arquivos de bancos de teste sejam limpos antes e depois dos testes."""
    db_files = ["aria_test.db", "afis_test.db", "apex_test.db"]
    for db in db_files:
        p = Path(db)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
                
    # Inicializa o banco de dados do ARIA de testes
    from app.database.db_manager import init_db
    init_db()
                
    yield
    
    for db in db_files:
        p = Path(db)
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass


