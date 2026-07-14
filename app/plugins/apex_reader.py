"""
Corporate Standard Module: apex_reader
This module is part of the ARIA core framework.
"""
from typing import Any
import sqlite3
import logging
from pathlib import Path
from app.config import settings

class APEXReader:
    """Plugin de leitura de dados de faturas, dunning e DSO do APEX em modo estritamente read-only."""

    def __init__(self) -> Any:
        """
        Standard corporate docstring for __init__.
        """
        self.db_path = Path(settings.APEX_DB_PATH).resolve()

    def is_connected(self) -> bool:
        """Verifica se o arquivo do banco de dados do APEX está presente."""
        return self.db_path.exists()

    def get_all_invoices(self) -> list[dict]:
        """
        Retorna todas as faturas cadastradas no APEX.
        AP = A Pagar, AR = A Receber.
        """
        if not self.is_connected():
            logging.warning(f"APEX database não encontrado em {self.db_path}. Retornando lista vazia.")
            return []

        query = """
            SELECT id, invoice_number, invoice_type, counterparty_name, amount, due_date, status, fraud_score, created_at
            FROM invoices
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(query)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logging.error(f"Erro ao buscar faturas no APEX: {e}")
            return []

    def get_latest_dso(self) -> float:
        """
        Busca o último Days Sales Outstanding calculado no APEX.
        Caso não exista, retorna uma estimativa padrão de 30.0 dias.
        """
        if not self.is_connected():
            return 30.0

        query = """
            SELECT dso_days 
            FROM dso_snapshots 
            ORDER BY snapshot_date DESC 
            LIMIT 1
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute(query)
                row = cur.fetchone()
                return float(row[0]) if row else 30.0
        except Exception as e:
            logging.error(f"Erro ao buscar DSO no APEX: {e}")
            return 30.0

    def get_counterparties_stats(self) -> list[dict]:
        """
        Retorna estatísticas de contrapartes registradas no APEX.
        """
        if not self.is_connected():
            return []

        query = """
            SELECT name, type, credit_limit, avg_payment_days, on_time_rate, fraud_flag, risk_score
            FROM counterparties
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute(query)
                return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logging.error(f"Erro ao obter contrapartes do APEX: {e}")
            return []


