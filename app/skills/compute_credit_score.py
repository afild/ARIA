"""
Corporate Standard Module: compute_credit_score
This module is part of the ARIA core framework.
"""
import json
import logging
from typing import Dict, List

def compute_credit_score(afis_transactions: List[Dict], apex_invoices: List[Dict], latest_dso: float) -> Dict:
    """
    Calcula a pontuação de crédito interna (0 a 100) e o respectivo rating financeiro.
    Mapeia e pondera os seguintes indicadores: DSCR, Liquidez Corrente, Margem de Lucro, DSO e Concentração.
    Simula uma decomposição de SHAP values para fins de transparência de explicabilidade.
    """
    # 1. Agrega transações do AFIS para Receitas, Despesas e Lucro Líquido
    gross_revenue = 0.0
    total_expenses = 0.0

    for tx in afis_transactions:
        amount = float(tx.get("amount", 0.0))
        if amount > 0:
            gross_revenue += amount
        else:
            total_expenses += abs(amount)

    net_profit = gross_revenue - total_expenses
    net_profit_margin = (net_profit / gross_revenue) if gross_revenue > 0 else 0.0

    # 2. Agrega faturas do APEX para contas a receber (AR) e contas a pagar (AP)
    ar_balance = 0.0
    ap_balance = 0.0
    customer_volumes = {}

    for inv in apex_invoices:
        inv_type = inv.get("invoice_type", "AR")
        amount = float(inv.get("amount", 0.0))
        status = inv.get("status", "pending")
        
        if status in ["pending", "overdue", "partially_matched"]:
            if inv_type == "AR":
                ar_balance += amount
                client = inv.get("counterparty_name", "Unknown")
                customer_volumes[client] = customer_volumes.get(client, 0.0) + amount
            else:
                ap_balance += amount

    # Calcula Concentração de Recebíveis (maior cliente / total AR)
    max_customer_volume = max(customer_volumes.values()) if customer_volumes else 0.0
    ar_concentration = (max_customer_volume / ar_balance) if ar_balance > 0 else 0.0

    # 3. Calcula Indicadores Chaves de Risco
    
    # DSCR (Debt Service Coverage Ratio)
    # Assumimos um serviço anual da dívida fictício/padrão de $10,000 para a simulação
    annual_debt_service = 10000.0
    # EBITDA aproximado = lucro líquido + despesas financeiras/depreciações (assumindo despesas contábeis básicas)
    ebitda = net_profit if net_profit > 0 else 0.0
    dscr = (ebitda / annual_debt_service) if annual_debt_service > 0 else 1.0

    # Liquidez Corrente (Current Ratio)
    # Caixa operacional (estimado como receita - despesa recente ou assumindo um caixa base de $15,000)
    cash_estimate = max(net_profit, 5000.0) 
    current_assets = cash_estimate + ar_balance
    current_liabilities = max(ap_balance, 1000.0)
    current_ratio = current_assets / current_liabilities

    # Liquidez Seca (Quick Ratio) - assume 80% dos ativos circulantes rápidos
    quick_ratio = (cash_estimate + ar_balance * 0.9) / current_liabilities

    # 4. Motor de Pontuação Ponderado (Score 0-100)
    # Critérios e pontuações individuais (máximo de 20 pontos por critério, exceto DSCR que vale 30 e Concentração que vale 10)
    
    # a) DSCR (30 pontos max)
    if dscr >= 1.5:
        dscr_points = 30.0
    elif dscr >= 1.25:
        dscr_points = 25.0
    elif dscr >= 1.0:
        dscr_points = 15.0
    else:
        dscr_points = 5.0

    # b) Current Ratio (20 pontos max)
    if current_ratio >= 1.5:
        ratio_points = 20.0
    elif current_ratio >= 1.25:
        ratio_points = 16.0
    elif current_ratio >= 1.0:
        ratio_points = 10.0
    else:
        ratio_points = 2.0

    # c) Net Profit Margin (20 pontos max)
    if net_profit_margin >= 0.15:
        margin_points = 20.0
    elif net_profit_margin >= 0.08:
        margin_points = 15.0
    elif net_profit_margin >= 0.0:
        margin_points = 8.0
    else:
        margin_points = 0.0

    # d) DSO (20 pontos max)
    if latest_dso <= 30.0:
        dso_points = 20.0
    elif latest_dso <= 45.0:
        dso_points = 15.0
    elif latest_dso <= 60.0:
        dso_points = 8.0
    else:
        dso_points = 2.0

    # e) Concentração de Recebíveis (10 pontos max)
    if ar_concentration <= 0.15:
        concentration_points = 10.0
    elif ar_concentration <= 0.30:
        concentration_points = 7.0
    elif ar_concentration <= 0.50:
        concentration_points = 4.0
    else:
        concentration_points = 1.0

    # Score Final
    score = int(dscr_points + ratio_points + margin_points + dso_points + concentration_points)
    score = max(min(score, 100), 0)

    # 5. Classificação em Ratings
    if score >= 90:
        rating = "AAA"
    elif score >= 80:
        rating = "AA"
    elif score >= 70:
        rating = "A"
    elif score >= 60:
        rating = "BBB"
    elif score >= 50:
        rating = "BB"
    elif score >= 40:
        rating = "B"
    elif score >= 30:
        rating = "CCC"
    else:
        rating = "D"

    # 6. Simulação de SHAP Values (Drivers de impacto no score)
    # A base neutra é definida em 60 pontos. Calculamos o desvio de cada um.
    shap_explanations = {
        "dscr": dscr_points - 18.0,
        "liquidity": ratio_points - 12.0,
        "margin": margin_points - 12.0,
        "dso": dso_points - 12.0,
        "concentration": concentration_points - 6.0
    }

    # Fatores de risco identificados
    risk_factors = []
    if dscr < 1.25:
        risk_factors.append("DSCR abaixo do patamar mínimo exigido pelo SBA (1.25).")
    if current_ratio < 1.25:
        risk_factors.append("Liquidez de curto prazo tensionada (Current Ratio < 1.25).")
    if latest_dso > 45.0:
        risk_factors.append(f"DSO elevado ({latest_dso:.1f} dias) indicando lentidão no recebimento de faturas.")
    if ar_concentration > 0.25:
        risk_factors.append(f"Risco de Concentração: {ar_concentration*100:.1f}% dos recebíveis alocados em um único cliente.")
    if net_profit_margin < 0.05:
        risk_factors.append("Margem líquida fraca ou deficitária no período fiscal.")

    return {
        "score": score,
        "rating": rating,
        "dscr": dscr,
        "current_ratio": current_ratio,
        "quick_ratio": quick_ratio,
        "net_profit_margin": net_profit_margin,
        "dso_days": latest_dso,
        "ar_concentration": ar_concentration,
        "shap_explanations": shap_explanations,
        "risk_factors": risk_factors
    }
