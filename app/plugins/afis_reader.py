"""
Corporate Standard Module: afis_reader
This module is part of the ARIA core framework.
"""
from typing import Any
import sqlite3
import logging
from pathlib import Path
from app.config import settings

class AFISReader:
    """Plugin de leitura de dados financeiros históricos (AFIS Core) em modo estritamente read-only."""

    def __init__(self) -> Any:
        """
        Standard corporate docstring for __init__.
        """
        self.db_path = Path(settings.AFIS_DB_PATH).resolve()

    def is_connected(self) -> bool:
        """Verifica se o arquivo do banco de dados do AFIS está presente no caminho configurado."""
        return self.db_path.exists()

    def get_all_transactions(self) -> list[dict]:
        """
        Retorna todas as transações cadastradas no AFIS.
        Retorna lista de dicionários com chaves: id, date, description, amount, category.
        """
        if not self.is_connected():
            logging.warning(f"AFIS database não encontrado no caminho {self.db_path}. Retornando lista vazia.")
            return []

        query = """
            SELECT id, date, description, amount, category
            FROM transactions
            ORDER BY date DESC
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(query)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logging.error(f"Erro ao buscar transações no AFIS: {e}")
            return []

    def get_transactions_by_period(self, start_date: str, end_date: str) -> list[dict]:
        """
        Retorna transações do AFIS dentro do período especificado (YYYY-MM-DD).
        """
        if not self.is_connected():
            return []

        query = """
            SELECT id, date, description, amount, category
            FROM transactions
            WHERE date BETWEEN ? AND ?
            ORDER BY date DESC
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(query, (start_date, end_date))
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logging.error(f"Erro ao buscar transações por período no AFIS: {e}")
            return []
