"""
Corporate Standard Module: models
This module is part of the ARIA core framework.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime
from app.database.db_manager import Base

class RiskAlert(Base):
    """
    Corporate Standard Class: RiskAlert.
    """
    __tablename__ = "risk_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(String, nullable=False)        # transaction_anomaly | high_dso | counterparty_risk | credit_drop
    severity = Column(String, nullable=False)          # low | medium | high | critical
    description = Column(String, nullable=False)
    status = Column(String, default="open")            # open | investigating | resolved | false_positive
    transaction_id = Column(Integer, nullable=True)    # ref ao AFIS
    invoice_id = Column(Integer, nullable=True)        # ref ao APEX
    counterparty_name = Column(String, nullable=True)
    score_value = Column(Float, nullable=True)
    resolved_by = Column(String, nullable=True)
    resolution_notes = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class SMECreditScore(Base):
    """
    Corporate Standard Class: SMECreditScore.
    """
    __tablename__ = "sme_credit_scores"

    id = Column(Integer, primary_key=True, index=True)
    tax_year = Column(Integer, nullable=False, index=True)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    score = Column(Integer, nullable=False)            # 0 a 100
    rating = Column(String, nullable=False)            # AAA | AA | A | BBB | BB | B | CCC | D
    dscr = Column(Float, nullable=True)                # Debt Service Coverage Ratio
    current_ratio = Column(Float, nullable=True)       # Liquidez Corrente
    quick_ratio = Column(Float, nullable=True)         # Liquidez Seca
    net_profit_margin = Column(Float, nullable=True)   # Margem de lucro líquido
    dso_days = Column(Float, nullable=True)            # Days Sales Outstanding
    ar_concentration = Column(Float, nullable=True)    # Concentração de recebíveis
    shap_explanations = Column(Text, nullable=True)    # JSON string
    risk_factors = Column(Text, nullable=True)         # JSON array

class LenderReport(Base):
    """
    Corporate Standard Class: LenderReport.
    """
    __tablename__ = "lender_reports"

    id = Column(Integer, primary_key=True, index=True)
    tax_year = Column(Integer, nullable=False)
    overall_score = Column(Integer, nullable=False)
    lender_decision = Column(String, nullable=False)   # approved | conditional | declined
    summary = Column(Text, nullable=False)
    report_path = Column(String, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)

class RiskChatHistory(Base):
    """
    Corporate Standard Class: RiskChatHistory.
    """
    __tablename__ = "risk_chat_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)              # user | assistant
    content = Column(Text, nullable=False)
    citations = Column(Text, nullable=True)            # JSON string array
    created_at = Column(DateTime, default=datetime.utcnow)

class ARIASetting(Base):
    """
    Corporate Standard Class: ARIASetting.
    """
    __tablename__ = "aria_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class NISTAuditLog(Base):
    """
    Corporate Standard Class: NISTAuditLog.
    """
    __tablename__ = "nist_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)        # model_inference | risk_alert_trigger | human_override | database_sync
    component = Column(String, nullable=False)         # orchestrator | transaction_monitor | credit_scoring
    actor = Column(String, nullable=False)             # system | agent | human_user
    description = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)        # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)


