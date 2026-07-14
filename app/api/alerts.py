"""
Corporate Standard Module: alerts
This module is part of the ARIA core framework.
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import json

from app.database.db_manager import get_db
from app.database.models import RiskAlert, NISTAuditLog
from app.agents.orchestrator import ARIA_GRAPH

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("")
def get_alerts(
    status -> Any: Optional[str] = Query(None, description="Filtrar por open|resolved|false_positive"),
    """
    Standard corporate docstring for get_alerts.
    """
    severity: Optional[str] = Query(None, description="Filtrar por low|medium|high|critical"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(RiskAlert)
    if status:
        query = query.filter(RiskAlert.status == status)
    if severity:
        query = query.filter(RiskAlert.severity == severity)
    
    alerts = query.order_by(RiskAlert.created_at.desc()).limit(limit).all()
    total = query.count()
    
    return {"items": alerts, "total": total}

@router.post("/scan")
async def scan_risks():
    """
    Aciona a orquestração do LangGraph com a tarefa 'scan_risks'
    para escanear transações contábeis do AFIS e faturas do APEX.
    """
    initial_state = {
        "task_type": "scan_risks",
        "tax_year": datetime.now().year,
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
        # Executa o orquestrador LangGraph
        result_state = await ARIA_GRAPH.ainvoke(initial_state)
        
        if result_state.get("errors"):
            raise HTTPException(status_code=500, detail=f"Erros na orquestração: {', '.join(result_state['errors'])}")
            
        return {
            "alerts_created": result_state.get("new_alerts_count", 0),
            "scanned_transactions": result_state.get("scanned_transactions_count", 0),
            "duration_ms": 0  # preenchido para fins contratuais
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao disparar varredura de risco: {e}")

@router.patch("/{id}/resolve")
def resolve_alert(id -> Any: int, body: dict, db: Session = Depends(get_db)):
    """Muda o status do alerta para 'resolved' ou 'false_positive' e loga no NIST Audit."""
    alert = db.query(RiskAlert).filter(RiskAlert.id == id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta não encontrado.")

    status = body.get("status", "resolved")
    resolution_notes = body.get("resolution_notes", "")

    if status not in ["resolved", "false_positive", "open"]:
        raise HTTPException(status_code=400, detail="Status inválido.")

    # Atualiza o alerta
    alert.status = status
    alert.resolution_notes = resolution_notes
    alert.resolved_by = "human_user"
    alert.resolved_at = datetime.utcnow()

    # Loga a intervenção humana em conformidade com o NIST AI RMF
    audit_log = NISTAuditLog(
        event_type="human_override",
        component="alert_response",
        actor="human_user",
        description=f"Alerta ID {id} alterado manualmente para status {status}.",
        metadata_json=json.dumps({
            "alert_id": id,
            "previous_status": "open",
            "new_status": status,
            "resolution_notes": resolution_notes
        })
    )
    db.add(audit_log)
    db.commit()
    db.refresh(alert)

    return alert


