"""
Corporate Standard Module: credit_scoring
This module is part of the ARIA core framework.
"""
import logging
import json
from datetime import datetime
from typing import Dict
from app.plugins.afis_reader import AFISReader
from app.plugins.apex_reader import APEXReader
from app.skills.compute_credit_score import compute_credit_score
from app.database.db_manager import SessionLocal
from app.database.models import SMECreditScore

async def run_credit_scoring(state: Dict) -> Dict:
    """
    Sub-agente que compila as métricas financeiras consolidadas da PME e calcula seu Credit Score e Rating.
    Salva o histórico no banco de dados local aria_risk.db.
    """
    logging.info("Iniciando sub-agente: Credit Scoring")
    
    tax_year = state.get("tax_year", datetime.now().year)
    
    afis = AFISReader()
    apex = APEXReader()
    
    # Busca dados históricos dos plugins
    transactions = afis.get_all_transactions() if afis.is_connected() else []
    invoices = apex.get_all_invoices() if apex.is_connected() else []
    dso = apex.get_latest_dso()

    # Roda o motor de cálculo da skill
    res = compute_credit_score(transactions, invoices, dso)

    # Persiste o resultado no banco local
    db = SessionLocal()
    try:
        score_db = SMECreditScore(
            tax_year=tax_year,
            score=res["score"],
            rating=res["rating"],
            dscr=res["dscr"],
            current_ratio=res["current_ratio"],
            quick_ratio=res["quick_ratio"],
            net_profit_margin=res["net_profit_margin"],
            dso_days=res["dso_days"],
            ar_concentration=res["ar_concentration"],
            shap_explanations=json.dumps(res["shap_explanations"]),
            risk_factors=json.dumps(res["risk_factors"])
        )
        db.add(score_db)
        db.commit()
        db.refresh(score_db)
        logging.info(f"Credit Score calculado para {tax_year}: {res['score']} ({res['rating']}) salvo com ID {score_db.id}")
    except Exception as e:
        db.rollback()
        logging.error(f"Erro ao salvar Credit Score no banco de dados: {e}")
    finally:
        db.close()

    # Atualiza o estado
    return {
        **state,
        "calculated_score": res["score"],
        "credit_rating": res["rating"],
        "shap_explanations": res["shap_explanations"],
        "credit_profile": res,
        "completed_steps": state.get("completed_steps", []) + ["credit_scoring"]
    }
