"""
Corporate Standard Module: nist_audit
This module is part of the ARIA core framework.
"""
import logging
import json
from typing import Dict
from app.database.db_manager import SessionLocal
from app.database.models import NISTAuditLog

async def run_nist_audit(state: Dict) -> Dict:
    """
    Sub-agente responsável pela trilha de auditoria e conformidade (NIST AI RMF 1.0 Compliance Audit Trail).
    Registra as inferências de IA, anomalias e decisões de underwriting executadas no banco de dados.
    """
    logging.info("Iniciando sub-agente: NIST Audit")

    event_type = "model_inference"
    component = "orchestrator"
    actor = "agent"
    description = "Varredura de risco e auditoria concluída com sucesso."
    
    # Monta metadados enriquecidos para o log
    metadata = {
        "completed_steps": state.get("completed_steps", []),
        "scanned_transactions": state.get("scanned_transactions_count", 0),
        "new_alerts": state.get("new_alerts_count", 0),
        "errors": state.get("errors", [])
    }

    task = state.get("task_type")
    if task == "scan_risks":
        event_type = "risk_alert_trigger"
        component = "transaction_monitor"
        description = f"Análise de transações concluída. {metadata['scanned_transactions']} escaneadas, {metadata['new_alerts']} alertas gerados."
    elif task == "calculate_credit":
        event_type = "model_inference"
        component = "credit_scoring"
        description = f"Credit Score calculado: {state.get('calculated_score')} (Rating: {state.get('credit_rating')})."
        metadata["score"] = state.get("calculated_score")
        metadata["rating"] = state.get("credit_rating")
    elif task == "generate_lender_report":
        event_type = "human_override" if state.get("user_override") else "model_inference"
        component = "lender_report"
        description = f"Dossiê Lender Readiness gerado. Decisão de underwriting: {state.get('lender_decision')}."
        metadata["lender_decision"] = state.get("lender_decision")
        metadata["report_path"] = state.get("report_path")
    elif task == "advisor_chat":
        event_type = "model_inference"
        component = "advisor_chat"
        description = "Consulta ao AI Risk Advisor processada."
        metadata["session_id"] = state.get("session_id")

    db = SessionLocal()
    try:
        audit_log = NISTAuditLog(
            event_type=event_type,
            component=component,
            actor=actor,
            description=description,
            metadata_json=json.dumps(metadata)
        )
        db.add(audit_log)
        db.commit()
        logging.info(f"NIST Audit Trail: evento {event_type} gravado com sucesso.")
    except Exception as e:
        db.rollback()
        logging.error(f"Erro ao persistir log de auditoria NIST: {e}")
    finally:
        db.close()

    return {
        **state,
        "completed_steps": state.get("completed_steps", []) + ["nist_audit"]
    }
