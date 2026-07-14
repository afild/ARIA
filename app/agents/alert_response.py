"""
Corporate Standard Module: alert_response
This module is part of the ARIA core framework.
"""
import logging
from typing import Dict
from app.database.db_manager import SessionLocal
from app.database.models import RiskAlert

async def run_alert_response(state: Dict) -> Dict:
    """
    Sub-agente que consolida anomalias e vulnerabilidades contábeis/financeiras detectadas e as
    transforma em alertas na base de dados, simulando webhooks de integração.
    """
    logging.info("Iniciando sub-agente: Alert Response")
    
    anomalous_txs = state.get("anomalous_transactions", [])
    high_risk_partners = state.get("high_risk_partners", [])
    
    db = SessionLocal()
    new_alerts_count = 0

    try:
        # 1. Registra alertas para transações anômalas identificadas
        for tx in anomalous_txs:
            # Verifica se o alerta para esta transação específica já existe no DB para não duplicar
            exists = db.query(RiskAlert).filter(
                RiskAlert.transaction_id == tx["transaction_id"],
                RiskAlert.alert_type == "transaction_anomaly"
            ).first()
            
            if not exists:
                severity = "critical" if tx["score"] >= 80.0 else ("high" if tx["score"] >= 70.0 else "medium")
                alert = RiskAlert(
                    alert_type="transaction_anomaly",
                    severity=severity,
                    description=f"Transação suspeita: {tx['description']}. {tx['explanation']}",
                    transaction_id=tx["transaction_id"],
                    score_value=tx["score"],
                    status="open"
                )
                db.add(alert)
                new_alerts_count += 1

                # Simula envio de webhook para alertas críticos/altos
                if severity in ["high", "critical"]:
                    logging.info(f"🚨 [ALERT SIMULATOR - Slack/Webhook] DISPARADO Alerta de Risco {severity.upper()} para transação {tx['transaction_id']}!")

        # 2. Registra alertas para contrapartes com alto risco
        for partner in high_risk_partners:
            # Verifica duplicata
            exists = db.query(RiskAlert).filter(
                RiskAlert.counterparty_name == partner["label"],
                RiskAlert.alert_type == "counterparty_risk"
            ).first()

            if not exists:
                severity = "high" if partner["risk_level"] == "high" else "medium"
                alert = RiskAlert(
                    alert_type="counterparty_risk",
                    severity=severity,
                    description=partner.get("description", f"Contraparte {partner['label']} sinalizada com risco."),
                    counterparty_name=partner["label"],
                    score_value=80.0 if severity == "high" else 50.0,
                    status="open"
                )
                db.add(alert)
                new_alerts_count += 1

                if severity == "high":
                    logging.info(f"🚨 [ALERT SIMULATOR - Slack/Webhook] Concentração de receita crítica ou vulnerabilidade com {partner['label']}!")

        db.commit()
        logging.info(f"Alert Response finalizado. {new_alerts_count} novos alertas registrados no DB.")
    except Exception as e:
        db.rollback()
        logging.error(f"Erro ao registrar alertas no Alert Response: {e}")
    finally:
        db.close()

    return {
        **state,
        "new_alerts_count": new_alerts_count,
        "completed_steps": state.get("completed_steps", []) + ["alert_response"]
    }
