"""
Corporate Standard Module: score_transaction
This module is part of the ARIA core framework.
"""
import numpy as np
import logging
from typing import Dict, List

# Tenta importar Isolation Forest do scikit-learn
SKLEARN_AVAILABLE = False
try:
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    logging.warning("scikit-learn não disponível. Skill score_transaction usará z-score.")

def score_transaction(tx: Dict, history: List[Dict], contamination: float = 0.05) -> Dict:
    """
    Calcula um score de anomalia (0 a 100) para uma transação comparada a um histórico de transações.
    Retorna um dicionário com o score, explicação da anomalia e flags de suspeita.
    """
    amount = float(tx.get("amount", 0.0))
    desc = tx.get("description", "").lower()
    
    # Flags básicas de suspeita (heurística imediata)
    flags = []
    
    # 1. Flag de duplicata suspeita no histórico recente
    duplicates = [h for h in history if abs(float(h.get("amount", 0.0)) - amount) < 0.01 
                  and h.get("description", "").lower() == desc 
                  and h.get("id") != tx.get("id")]
    if len(duplicates) > 0:
        flags.append("duplicate_transaction")

    # 2. Flag de transferências suspeitas com descrições genéricas
    suspicious_keywords = ["cash", "draw", "transfer", "anonymous", "undocumented", "personal", "saque"]
    if any(kw in desc for kw in suspicious_keywords):
        flags.append("suspicious_description")

    # Se não temos histórico suficiente, usamos apenas heurísticas e z-score simplificado
    if len(history) < 5:
        # Sem histórico suficiente: o score é puramente baseado nas flags
        base_score = 15.0
        if "duplicate_transaction" in flags:
            base_score += 40.0
        if "suspicious_description" in flags:
            base_score += 25.0
        
        explanation = "Histórico insuficiente para cálculo de desvio estatístico. "
        if flags:
            explanation += f"Flags acionadas: {', '.join(flags)}."
        else:
            explanation += "Nenhuma flag acionada. Transação de baixo risco."
            
        return {
            "score": float(base_score),
            "flags": flags,
            "explanation": explanation
        }

    # Extrai valores de despesa/receita do histórico
    history_amounts = [float(h.get("amount", 0.0)) for h in history]
    
    # Fallback se sklearn não estiver disponível ou falhar
    if not SKLEARN_AVAILABLE:
        # Usar Z-score clássico
        mean_amount = np.mean(history_amounts)
        std_amount = np.std(history_amounts)
        if std_amount == 0:
            z_score = 0.0
        else:
            z_score = abs(amount - mean_amount) / std_amount
            
        anomaly_score = min(z_score * 20.0, 100.0) # Normaliza z-score para escala de 0 a 100
        
        # Pondera com as flags
        if "duplicate_transaction" in flags:
            anomaly_score = max(anomaly_score, 65.0)
        if "suspicious_description" in flags:
            anomaly_score = max(anomaly_score, 50.0)

        explanation = f"Cálculo baseado em desvio padrão (Z-Score: {z_score:.2f}). "
        if anomaly_score > 75:
            explanation += f"Desvio incomum do valor médio (${mean_amount:.2f})."
        else:
            explanation += "Valor dentro dos parâmetros normais do histórico."

        return {
            "score": float(anomaly_score),
            "flags": flags,
            "explanation": explanation
        }

    try:
        # Prepara dados para o Isolation Forest (reshape 2D array)
        X_train = np.array(history_amounts).reshape(-1, 1)
        X_test = np.array([[amount]])

        # Treina o modelo
        clf = IsolationForest(contamination=contamination, random_state=42)
        clf.fit(X_train)
        
        # Isolation Forest score: valores menores são mais anômalos. score_samples retorna entre [-1.0, 0.0] aprox.
        raw_score = clf.score_samples(X_test)[0]
        
        # Mapeia o raw_score (geralmente entre -0.8 e -0.3) para uma escala de 0 a 100
        # Onde 100 é extremamente anômalo e 0 é perfeitamente normal
        normalized_score = (1.0 - (raw_score + 1.0)) * 100.0
        normalized_score = max(min(normalized_score, 100.0), 0.0)

        # Ajusta score pelas flags
        if "duplicate_transaction" in flags:
            normalized_score = max(normalized_score, 70.0)
        if "suspicious_description" in flags:
            normalized_score = max(normalized_score, 55.0)

        mean_amount = np.mean(history_amounts)
        if normalized_score > 70.0:
            explanation = f"Isolation Forest detectou outlier. Valor de ${amount:.2f} desvia significativamente da média de ${mean_amount:.2f}."
        else:
            explanation = "Padrão de transação estatisticamente normal."

        return {
            "score": float(normalized_score),
            "flags": flags,
            "explanation": explanation
        }
    except Exception as e:
        logging.error(f"Erro ao rodar Isolation Forest: {e}. Executando z-score manual.")
        # Z-score como plano C
        mean_amount = np.mean(history_amounts)
        std_amount = np.std(history_amounts) or 1.0
        z_score = abs(amount - mean_amount) / std_amount
        anomaly_score = min(z_score * 20.0, 100.0)
        return {
            "score": float(anomaly_score),
            "flags": flags,
            "explanation": f"Fallback Z-Score: valor de ${amount:.2f} com desvio {z_score:.2f}."
        }


