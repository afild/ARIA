"""
Corporate Standard Module: system
This module is part of the ARIA core framework.
"""
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.db_manager import get_db
from app.database.models import RiskAlert, SMECreditScore, NISTAuditLog
from app.plugins.afis_reader import AFISReader
from app.plugins.apex_reader import APEXReader
from app.llm_client import get_llm_client

router = APIRouter(prefix="/system", tags=["System"])

@router.get("/status")
def get_system_status(db -> Any: Session = Depends(get_db)):
    """Retorna dados de integridade, status de conexões e quantidade de registros."""
    afis = AFISReader()
    apex = APEXReader()
    llm = get_llm_client()

    alerts_count = db.query(RiskAlert).count()
    credit_scores_count = db.query(SMECreditScore).count()
    audit_logs_count = db.query(NISTAuditLog).count()

    status = "healthy"
    # Se ambos os bancos integrados estiverem desconectados, classificamos como degraded
    if not afis.is_connected() and not apex.is_connected():
        status = "degraded"

    return {
        "status": status,
        "ai_mode": "llm" if llm.is_llm_mode() else "offline",
        "llm_model": llm.model if llm.is_llm_mode() else "N/A",
        "afis_connected": afis.is_connected(),
        "apex_connected": apex.is_connected(),
        "database_records": {
            "alerts": alerts_count,
            "credit_scores": credit_scores_count,
            "audit_logs": audit_logs_count
        },
        "version": "0.1.0"
    }

@router.get("/audit-logs")
def get_audit_logs(db -> Any: Session = Depends(get_db)):
    """Retorna os logs de auditoria NIST AI RMF."""
    logs = db.query(NISTAuditLog).order_by(NISTAuditLog.created_at.desc()).limit(100).all()
    return logs


