"""
Corporate Standard Module: lender_report
This module is part of the ARIA core framework.
"""
import logging
from datetime import datetime
from typing import Dict
from app.skills.generate_lender_memo import generate_lender_memo
from app.plugins.report_generator import ReportGenerator
from app.database.db_manager import SessionLocal
from app.database.models import LenderReport

async def run_lender_report(state: Dict) -> Dict:
    """
    Sub-agente que gera o parecer sobreecrito do SBA (Lender Underwriting Memo),
    chama o plugin gerador de PDFs/HTMLs e salva o registro na base de dados local.
    """
    logging.info("Iniciando sub-agente: Lender Report")
    
    tax_year = state.get("tax_year", datetime.now().year)
    credit_profile = state.get("credit_profile")

    if not credit_profile:
        logging.warning("Credit profile não encontrado no estado. Lender Report cancelado.")
        return {**state, "errors": state.get("errors", []) + ["Credit profile ausente"]}

    # Chama a skill que gera a narrativa e decisão de underwriting
    memo_res = await generate_lender_memo(credit_profile, tax_year)

    # Prepara dados do relatório para persistir
    decision = memo_res["decision"]
    summary = memo_res["summary"]
    citations = memo_res["citations"]

    report_data = {
        "tax_year": tax_year,
        "score": credit_profile.get("score", 70),
        "rating": credit_profile.get("rating", "BBB"),
        "lender_decision": decision,
        "summary": summary,
        "dscr": credit_profile.get("dscr", 1.25),
        "current_ratio": credit_profile.get("current_ratio", 1.2),
        "quick_ratio": credit_profile.get("quick_ratio", 1.0),
        "net_profit_margin": credit_profile.get("net_profit_margin", 0.05),
        "dso_days": credit_profile.get("dso_days", 30.0),
        "risk_factors": credit_profile.get("risk_factors", [])
    }

    # Aciona o gerador de arquivos (PDF com fallback HTML)
    generator = ReportGenerator()
    generated_file_path = generator.generate_lender_pdf(report_data)

    # Persiste na tabela lender_reports
    db = SessionLocal()
    try:
        report_db = LenderReport(
            tax_year=tax_year,
            overall_score=credit_profile.get("score", 70),
            lender_decision=decision,
            summary=summary,
            report_path=str(generated_file_path.name)
        )
        db.add(report_db)
        db.commit()
        db.refresh(report_db)
        logging.info(f"Lender Report persistido com sucesso: ID {report_db.id}, decisão: {decision}")
    except Exception as e:
        db.rollback()
        logging.error(f"Erro ao salvar registro de Lender Report no banco: {e}")
    finally:
        db.close()

    return {
        **state,
        "lender_decision": decision,
        "lender_memo": summary,
        "citations": citations,
        "report_path": str(generated_file_path.name),
        "completed_steps": state.get("completed_steps", []) + ["lender_report"]
    }
