"""
Corporate Standard Module: explain_risk
This module is part of the ARIA core framework.
"""
from typing import Dict, List

def explain_risk(shap_explanations: Dict[str, float], score: int) -> List[Dict]:
    """
    Traduz os SHAP values (pesos das features) em uma narrativa em linguagem natural explicável para o usuário.
    Retorna uma lista de dicionários contendo o nome da variável, o impacto (positivo/negativo) e a descrição do impacto.
    """
    explanations = []
    
    # Mapeamento de nomes amigáveis das features
    feature_names = {
        "dscr": "Cobertura da Dívida (DSCR)",
        "liquidity": "Liquidez Corrente",
        "margin": "Margem de Lucro Líquido",
        "dso": "Dias de Recebimento (DSO)",
        "concentration": "Concentração de Recebíveis"
    }

    for key, val in shap_explanations.items():
        name = feature_names.get(key, key)
        impact = "positive" if val >= 0 else "negative"
        points = abs(int(val))
        
        # Cria a descrição descritiva de acordo com o impacto
        if key == "dscr":
            if val >= 0:
                desc = f"Sua excelente capacidade de cobertura de dívida adicionou +{points} pontos ao score."
            else:
                desc = f"A fragilidade no fluxo de caixa para pagar obrigações reduziu -{points} pontos do score."
        elif key == "liquidity":
            if val >= 0:
                desc = f"A boa liquidez de curto prazo (caixa e faturas a receber vs a pagar) aumentou seu score em +{points} pontos."
            else:
                desc = f"O baixo índice de liquidez circulante reduziu -{points} pontos do seu score."
        elif key == "margin":
            if val >= 0:
                desc = f"A lucratividade operacional saudável elevou a pontuação em +{points} pontos."
            else:
                desc = f"A baixa margem de lucro líquido ou prejuízo reduziu a pontuação em -{points} pontos."
        elif key == "dso":
            if val >= 0:
                desc = f"A rapidez no recebimento de faturas (baixo DSO) beneficiou o score em +{points} pontos."
            else:
                desc = f"A demora em receber de seus clientes (alto DSO) removeu -{points} pontos do seu score."
        elif key == "concentration":
            if val >= 0:
                desc = f"A diversificação na carteira de faturamento de clientes garantiu +{points} pontos adicionais."
            else:
                desc = f"A dependência elevada de poucos clientes principais gerou uma penalidade de -{points} pontos."
        else:
            desc = f"Impacto de {'+' if val >= 0 else '-'}{points} pontos no score final."

        explanations.append({
            "feature": key,
            "name": name,
            "impact": impact,
            "points": points,
            "description": desc
        })

    # Ordena pelo impacto absoluto (maiores impactos primeiro)
    explanations.sort(key=lambda x: x["points"], reverse=True)
    return explanations
