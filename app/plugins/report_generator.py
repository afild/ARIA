"""
Corporate Standard Module: report_generator
This module is part of the ARIA core framework.
"""
from typing import Any
import logging
import jinja2
from pathlib import Path
from app.config import settings

class ReportGenerator:
    """Plugin de geração de relatórios de risco e crédito utilizando Jinja2 e WeasyPrint (com fallback)."""

    def __init__(self) -> Any:
        """
        Standard corporate docstring for __init__.
        """
        self.reports_dir = Path(settings.REPORTS_DIR)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_lender_pdf(self, report_data: dict) -> Path:
        """
        Gera o PDF de Lender Readiness a partir de um template HTML.
        Se o WeasyPrint falhar devido a dependências do GTK, salva o HTML correspondente como fallback.
        """
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>ARIA - Lender Readiness Report</title>
            <style>
                body {
                    font-family: 'Inter', Arial, sans-serif;
                    color: #1e1e2f;
                    line-height: 1.6;
                    padding: 40px;
                    background-color: #ffffff;
                }
                .header {
                    border-bottom: 2px solid #6b21a8;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }
                .title {
                    font-size: 28px;
                    color: #6b21a8;
                    margin: 0;
                    font-weight: bold;
                }
                .subtitle {
                    font-size: 14px;
                    color: #6b7280;
                    margin-top: 5px;
                }
                .kpi-container {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 30px;
                    gap: 20px;
                }
                .kpi-card {
                    flex: 1;
                    background: #f3f4f6;
                    padding: 20px;
                    border-radius: 8px;
                    text-align: center;
                    border: 1px solid #e5e7eb;
                }
                .kpi-value {
                    font-size: 24px;
                    font-weight: bold;
                    color: #111827;
                }
                .kpi-label {
                    font-size: 12px;
                    color: #4b5563;
                    margin-top: 5px;
                }
                .section {
                    margin-bottom: 30px;
                }
                .section-title {
                    font-size: 18px;
                    color: #1f2937;
                    border-bottom: 1px solid #e5e7eb;
                    padding-bottom: 5px;
                    margin-bottom: 15px;
                    font-weight: 600;
                }
                .decision-approved {
                    color: #059669;
                    font-weight: bold;
                }
                .decision-conditional {
                    color: #d97706;
                    font-weight: bold;
                }
                .decision-declined {
                    color: #dc2626;
                    font-weight: bold;
                }
                .factor-list {
                    padding-left: 20px;
                }
                .factor-item {
                    margin-bottom: 8px;
                }
                .footer {
                    margin-top: 50px;
                    text-align: center;
                    font-size: 11px;
                    color: #9ca3af;
                    border-top: 1px solid #e5e7eb;
                    padding-top: 15px;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <div class="title">ARIA — AI Risk & Fraud Intelligence Analyzer</div>
                <div class="subtitle">Lender Readiness & Underwriting Memo | Ano Fiscal: {{ tax_year }}</div>
            </div>

            <div class="kpi-container">
                <div class="kpi-card">
                    <div class="kpi-value">{{ score }}/100</div>
                    <div class="kpi-label">Credit Score Interno</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">{{ rating }}</div>
                    <div class="kpi-label">Financial Rating</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">
                        <span class="decision-{{ lender_decision|lower }}">{{ lender_decision.upper() }}</span>
                    </div>
                    <div class="kpi-label">Decisão de Underwriting</div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">Resumo Executivo de Risco</div>
                <p>{{ summary }}</p>
            </div>

            <div class="section">
                <div class="section-title">Métricas Financeiras Analisadas</div>
                <table>
                    <tr>
                        <td style="width: 250px; font-weight: bold;">Debt Service Coverage Ratio (DSCR):</td>
                        <td>{{ dscr|round(2) if dscr else 'N/A' }} (mínimo exigido SBA: 1.25)</td>
                    </tr>
                    <tr>
                        <td style="font-weight: bold;">Liquidez Corrente:</td>
                        <td>{{ current_ratio|round(2) if current_ratio else 'N/A' }}</td>
                    </tr>
                    <tr>
                        <td style="font-weight: bold;">Liquidez Seca:</td>
                        <td>{{ quick_ratio|round(2) if quick_ratio else 'N/A' }}</td>
                    </tr>
                    <tr>
                        <td style="font-weight: bold;">Margem de Lucro Líquido:</td>
                        <td>{{ (net_profit_margin * 100)|round(1) if net_profit_margin else 'N/A' }}%</td>
                    </tr>
                    <tr>
                        <td style="font-weight: bold;">Days Sales Outstanding (DSO):</td>
                        <td>{{ dso_days|round(1) if dso_days else 'N/A' }} dias</td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <div class="section-title">Fatores de Risco Relevantes</div>
                <ul class="factor-list">
                    {% for factor in risk_factors %}
                    <li class="factor-item">{{ factor }}</li>
                    {% else %}
                    <li class="factor-item">Nenhum fator de risco severo identificado. A empresa apresenta boa estabilidade.</li>
                    {% endfor %}
                </ul>
            </div>

            <div class="footer">
                ARIA Risk Management Module. Gerado automaticamente em {{ date }}.<br>
                <em>Aviso: Este relatório simula a perspectiva de um analista de crédito com base nas diretrizes SBA. Nenhuma decisão de crédito real é garantida.</em>
            </div>
        </body>
        </html>
        """
        
        # Prepara dados para o template
        from datetime import datetime
        template_vars = {
            "tax_year": report_data.get("tax_year", 2026),
            "score": report_data.get("score", 75),
            "rating": report_data.get("rating", "BBB"),
            "lender_decision": report_data.get("lender_decision", "conditional"),
            "summary": report_data.get("summary", "Sem resumo executivo disponível."),
            "dscr": report_data.get("dscr", 1.25),
            "current_ratio": report_data.get("current_ratio", 1.5),
            "quick_ratio": report_data.get("quick_ratio", 1.2),
            "net_profit_margin": report_data.get("net_profit_margin", 0.10),
            "dso_days": report_data.get("dso_days", 30.0),
            "risk_factors": report_data.get("risk_factors", []),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Renderiza HTML via Jinja2
        template = jinja2.Template(html_template)
        rendered_html = template.render(template_vars)

        pdf_path = self.reports_dir / f"lender_readiness_{template_vars['tax_year']}.pdf"
        html_path = self.reports_dir / f"lender_readiness_{template_vars['tax_year']}.html"

        # Tenta WeasyPrint
        try:
            from weasyprint import HTML
            HTML(string=rendered_html).write_pdf(str(pdf_path))
            logging.info(f"Relatório PDF gerado com sucesso em: {pdf_path}")
            return pdf_path
        except Exception as e:
            # Caso Weasyprint ou dependências do GTK falhem, fazemos fallback salvando o HTML
            logging.warning(f"Falha ao rodar WeasyPrint ({e}). Salvando HTML como fallback.")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(rendered_html)
            # Retorna o arquivo HTML renomeando a extensão para sinalizar no backend
            return html_path
