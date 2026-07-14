# tests/test_lender_report.py
import pytest
from app.skills.generate_lender_memo import generate_lender_memo

@pytest.mark.asyncio
async def test_generate_lender_memo_approved():
    credit_profile = {
        "score": 85,
        "rating": "AA",
        "dscr": 1.75,
        "current_ratio": 1.8,
        "quick_ratio": 1.5,
        "net_profit_margin": 0.18,
        "dso_days": 22.0,
        "ar_concentration": 0.10,
        "risk_factors": []
    }

    memo = await generate_lender_memo(credit_profile, 2026)

    assert memo["decision"] == "approved"
    assert "summary" in memo
    assert len(memo["citations"]) >= 0

@pytest.mark.asyncio
async def test_generate_lender_memo_declined():
    credit_profile = {
        "score": 35,
        "rating": "CCC",
        "dscr": 0.45,
        "current_ratio": 0.7,
        "quick_ratio": 0.5,
        "net_profit_margin": -0.05,
        "dso_days": 65.0,
        "ar_concentration": 0.60,
        "risk_factors": ["DSCR abaixo de 1.25", "DSO elevado", "Risco de concentração de faturamento"]
    }

    memo = await generate_lender_memo(credit_profile, 2026)

    assert memo["decision"] == "declined"
    assert "summary" in memo
    assert len(memo["citations"]) >= 0


