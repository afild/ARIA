"""
Corporate Standard Module: transaction_monitor
This module is part of the ARIA core framework.
"""
import logging
from typing import Dict
from app.plugins.afis_reader import AFISReader
from app.skills.score_transaction import score_transaction

async def run_transaction_monitor(state: Dict) -> Dict:
    """
    Sub-agente que monitora transações do AFIS para apontar desvios e potenciais fraudes.
    Lê o histórico de transações, calcula anomalia para cada transação e retorna a contagem.
    """
    logging.info("Iniciando sub-agente: Transaction Monitor")
    
    afis = AFISReader()
    if not afis.is_connected():
        logging.warning("AFIS Reader offline. Pulando análise transacional.")
        return {**state, "scanned_transactions_count": 0, "errors": state.get("errors", []) + ["AFIS offline"]}

    # Obtém transações
    transactions = afis.get_all_transactions()
    if not transactions:
        return {**state, "scanned_transactions_count": 0}

    # Salva os resultados calculados temporariamente no estado para processamento posterior
    # Para cada transação, calcula o score baseado na própria lista histórica
    scanned_count = 0
    anomalous_transactions = []

    for tx in transactions:
        scanned_count += 1
        res = score_transaction(tx, transactions)
        
        # Se o score for alto, adicionamos para a lista de alertas a serem processados pelo AlertResponse
        if res["score"] >= 65.0:
            anomalous_transactions.append({
                "transaction_id": tx["id"],
                "description": tx["description"],
                "amount": tx["amount"],
                "score": res["score"],
                "explanation": res["explanation"],
                "flags": res["flags"]
            })

    # Adiciona as anomalias detectadas no estado para serem transformadas em alertas reais
    return {
        **state,
        "scanned_transactions_count": scanned_count,
        "completed_steps": state.get("completed_steps", []) + ["transaction_monitor"],
        "anomalous_transactions": anomalous_transactions
    }


