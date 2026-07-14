# tests/test_credit_scoring.py
import pytest
from app.skills.compute_credit_score import compute_credit_score

def test_compute_credit_score_healthy():
    # EBITDA saudável (lucro de $150K vs serviço da dívida proposta de $10k)
    afis_txs = [
        {"amount": 250000.0, "category": "Revenue"},   # Receita
        {"amount": -100000.0, "category": "Expenses"}  # Despesa
    ]
    
    # Recebíveis saudáveis (AR) de $20k bem distribuídos vs AP de $5k
    apex_invoices = [
        {"invoice_type": "AR", "amount": 2500.0, "status": "pending", "counterparty_name": "Client A"},
        {"invoice_type": "AR", "amount": 2500.0, "status": "pending", "counterparty_name": "Client B"},
        {"invoice_type": "AR", "amount": 2500.0, "status": "pending", "counterparty_name": "Client C"},
        {"invoice_type": "AR", "amount": 2500.0, "status": "pending", "counterparty_name": "Client D"},
        {"invoice_type": "AR", "amount": 2500.0, "status": "pending", "counterparty_name": "Client E"},
        {"invoice_type": "AR", "amount": 2500.0, "status": "pending", "counterparty_name": "Client F"},
        {"invoice_type": "AR", "amount": 2500.0, "status": "pending", "counterparty_name": "Client G"},
        {"invoice_type": "AR", "amount": 2500.0, "status": "pending", "counterparty_name": "Client H"},
        {"invoice_type": "AP", "amount": 5000.0, "status": "pending", "counterparty_name": "Vendor A"}
    ]
    
    latest_dso = 25.0 # DSO baixo (25 dias)

    res = compute_credit_score(afis_txs, apex_invoices, latest_dso)

    assert res["score"] >= 75
    assert res["rating"] in ["AAA", "AA", "A", "BBB"]
    assert res["dscr"] >= 1.5
    assert res["current_ratio"] >= 1.5
    assert len(res["risk_factors"]) == 0
    assert "shap_explanations" in res

def test_compute_credit_score_risk():
    # EBITDA deficitário
    afis_txs = [
        {"amount": 50000.0, "category": "Revenue"},
        {"amount": -65000.0, "category": "Expenses"}
    ]
    
    # AP alto de $35k vs AR de $10k
    apex_invoices = [
        {"invoice_type": "AR", "amount": 10000.0, "status": "pending", "counterparty_name": "Client A"},
        {"invoice_type": "AP", "amount": 35000.0, "status": "pending", "counterparty_name": "Vendor A"}
    ]
    
    latest_dso = 55.0 # DSO alto (55 dias)

    res = compute_credit_score(afis_txs, apex_invoices, latest_dso)

    assert res["score"] < 50
    assert res["rating"] in ["B", "CCC", "D"]
    assert res["dscr"] < 1.0
    assert len(res["risk_factors"]) > 0
    assert any("DSCR" in factor for factor in res["risk_factors"])
    assert any("DSO" in factor for factor in res["risk_factors"])


