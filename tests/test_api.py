# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_system_status():
    response = client.get("/api/system/status")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "ai_mode" in data
    assert "afis_connected" in data
    assert "apex_connected" in data
    assert "database_records" in data

def test_get_alerts():
    response = client.get("/api/alerts")
    assert response.status_code == 200
    
    data = response.json()
    assert "items" in data
    assert "total" in data

def test_get_credit_score_default():
    response = client.get("/api/credit/score")
    assert response.status_code == 200
    
    data = response.json()
    assert "score" in data
    assert "rating" in data
    assert "risk_factors" in data

def test_get_graph_connections():
    response = client.get("/api/graph/connections")
    assert response.status_code == 200
    
    data = response.json()
    assert "nodes" in data
    assert "edges" in data

def test_chat_history():
    response = client.get("/api/chat/history/test_session")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


