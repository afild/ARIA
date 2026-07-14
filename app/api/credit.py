"""
Corporate Standard Module: credit
This module is part of the ARIA core framework.
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

from app.database.db_manager import get_db
from app.database.models import SMECreditScore, LenderReport
from app.agents.orchestrator import ARIA_GRAPH
from app.config import settings

router = APIRouter(prefix="/credit", tags=["Credit"])

@router.get("/score")
def get_latest_score(year -> Any: Optional[int] = Query(None), db: Session = Depends(get_db)):
    """Busca o credit score mais recente ou do ano especificado."""
    query = db.query(SMECreditScore)
    if year:
        query = query.filter(SMECreditScore.tax_year == year)
    
    score_record = query.order_by(SMECreditScore.calculated_at.desc()).first()
    if not score_record:
        # Se não houver scores calculados, tenta disparar um cálculo básico sob demanda para não vir vazio
        return {
            "score": 0,
            "rating": "N/A",
            "dscr": 0.0,
            "current_ratio": 0.0,
            "quick_ratio": 0.0,
            "net_profit_margin": 0.0,
            "dso_days": 30.0,
            "ar_concentration": 0.0,
            "shap_explanations": {},
            "risk_factors": ["Nenhum score calculado no banco de dados. Clique em Calcular Score."]
        }

    return {
        "id": score_record.id,
        "tax_year": score_record.tax_year,
        "score": score_record.score,
        "rating": score_record.rating,
        "dscr": score_record.dscr,
        "current_ratio": score_record.current_ratio,
        "quick_ratio": score_record.quick_ratio,
        "net_profit_margin": score_record.net_profit_margin,
        "dso_days": score_record.dso_days,
        "ar_concentration": score_record.ar_concentration,
        "shap_explanations": json.loads(score_record.shap_explanations) if score_record.shap_explanations else {},
        "risk_factors": json.loads(score_record.risk_factors) if score_record.risk_factors else [],
        "calculated_at": score_record.calculated_at
    }

@router.post("/calculate")
async def calculate_credit_score(body: dict):
    """Calcula e atualiza o Credit Score da PME usando o orquestrador."""
    year = body.get("year", datetime.now().year)

    initial_state = {
        "task_type": "calculate_credit",
        "tax_year": year,
        "session_id": None,
        "user_question": None,
        "scanned_transactions_count": 0,
        "new_alerts_count": 0,
        "calculated_score": None,
        "credit_rating": None,
        "shap_explanations": {},
        "graph_data": {},
        "lender_decision": None,
        "lender_memo": None,
        "llm_response": None,
        "citations": [],
        "errors": [],
        "completed_steps": [],
        "anomalous_transactions": [],
        "high_risk_partners": [],
        "credit_profile": None,
        "report_path": None
    }

    try:
        result_state = await ARIA_GRAPH.ainvoke(initial_state)
        
        if result_state.get("errors"):
            raise HTTPException(status_code=500, detail=f"Erros no cálculo: {', '.join(result_state['errors'])}")

        return result_state.get("credit_profile", {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao computar credit score: {e}")

@router.post("/lender-report")
async def generate_lender_report(body: dict):
    """Gera o memorando de crédito (Lender Underwriting Report) e exporta PDF/HTML."""
    year = body.get("year", datetime.now().year)

    initial_state = {
        "task_type": "generate_lender_report",
        "tax_year": year,
        "session_id": None,
        "user_question": None,
        "scanned_transactions_count": 0,
        "new_alerts_count": 0,
        "calculated_score": None,
        "credit_rating": None,
        "shap_explanations": {},
        "graph_data": {},
        "lender_decision": None,
        "lender_memo": None,
        "llm_response": None,
        "citations": [],
        "errors": [],
        "completed_steps": [],
        "anomalous_transactions": [],
        "high_risk_partners": [],
        "credit_profile": None,
        "report_path": None
    }

    try:
        result_state = await ARIA_GRAPH.ainvoke(initial_state)
        
        if result_state.get("errors"):
            raise HTTPException(status_code=500, detail=f"Erros na geração do laudo: {', '.join(result_state['errors'])}")

        # Salva o LenderReport
        report_path = result_state.get("report_path")
        return {
            "decision": result_state.get("lender_decision"),
            "summary": result_state.get("lender_memo"),
            "report_path": report_path,
            "download_url": f"/api/credit/lender-report/download?filename={report_path}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar laudo de crédito: {e}")

@router.get("/lender-report/download")
def download_lender_report(filename -> Any: str):
    """Fornece o arquivo de relatório gerado (PDF ou HTML) para download."""
    reports_dir = Path(settings.REPORTS_DIR).resolve()
    file_path = reports_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")

    # Define o content-type correto
    media_type = "application/pdf" if file_path.suffix == ".pdf" else "text/html"
    return FileResponse(path=str(file_path), filename=filename, media_type=media_type)


