# tests/test_transaction_monitor.py
import pytest
from app.skills.score_transaction import score_transaction

def test_score_transaction_normal():
    # Histórico de transações normais
    history = [
        {"id": 1, "amount": 100.0, "description": "Office supplies"},
        {"id": 2, "amount": 120.0, "description": "Printer ink"},
        {"id": 3, "amount": 95.0, "description": "Paper cups"},
        {"id": 4, "amount": 110.0, "description": "Notebooks"},
        {"id": 5, "amount": 105.0, "description": "Pens"}
    ]
    
    # Transação sob avaliação dentro do desvio padrão
    tx = {"id": 6, "amount": 108.0, "description": "Stapler"}
    
    res = score_transaction(tx, history)
    
    assert res["score"] < 50.0
    assert len(res["flags"]) == 0
    assert "explanation" in res

def test_score_transaction_outlier():
    # Histórico normal
    history = [
        {"id": 1, "amount": 100.0, "description": "Software subscription"},
        {"id": 2, "amount": 105.0, "description": "Hosting service"},
        {"id": 3, "amount": 98.0, "description": "Domain renewal"},
        {"id": 4, "amount": 102.0, "description": "Email service"},
        {"id": 5, "amount": 101.0, "description": "SSL Certificate"}
    ]
    
    # Transação com valor absurdamente alto (outlier)
    tx = {"id": 6, "amount": 3500.0, "description": "Consulting server maintenance"}
    
    res = score_transaction(tx, history)
    
    # Deve acusar um score alto (anomalia detectada)
    assert res["score"] >= 50.0
    assert "explanation" in res

def test_score_transaction_duplicate():
    history = [
        {"id": 1, "amount": 150.0, "description": "Consulting monthly fee"},
        {"id": 2, "amount": 120.0, "description": "Internet bill"},
        {"id": 3, "amount": 150.0, "description": "Consulting monthly fee"}, # Duplicata histórica
        {"id": 4, "amount": 130.0, "description": "Electricity bill"},
        {"id": 5, "amount": 140.0, "description": "Water bill"}
    ]
    
    # Avaliando transação duplicada de novo
    tx = {"id": 6, "amount": 150.0, "description": "Consulting monthly fee"}
    
    res = score_transaction(tx, history)
    
    assert "duplicate_transaction" in res["flags"]
    assert res["score"] >= 60.0

def test_score_transaction_suspicious_desc():
    history = [
        {"id": 1, "amount": 50.0, "description": "Weekly dinner client"},
        {"id": 2, "amount": 40.0, "description": "Taxi ride client"},
        {"id": 3, "amount": 55.0, "description": "Coffee business talk"},
        {"id": 4, "amount": 45.0, "description": "Parking lot client"},
        {"id": 5, "amount": 48.0, "description": "Dinner meeting"}
    ]
    
    # Transação contendo termo de saque suspeito
    tx = {"id": 6, "amount": 60.0, "description": "Cash withdrawal anonymous"}
    
    res = score_transaction(tx, history)
    
    assert "suspicious_description" in res["flags"]
    assert res["score"] >= 50.0


