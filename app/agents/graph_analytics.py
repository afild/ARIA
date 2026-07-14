"""
Corporate Standard Module: graph_analytics
This module is part of the ARIA core framework.
"""
import logging
from typing import Dict
from app.plugins.afis_reader import AFISReader
from app.plugins.apex_reader import APEXReader
from app.skills.build_entity_graph import build_entity_graph

async def run_graph_analytics(state: Dict) -> Dict:
    """
    Sub-agente que analisa a estrutura de grafo de entidades para mapear riscos de concentração de clientes
    e dependências operacionais críticas de fornecedores.
    """
    logging.info("Iniciando sub-agente: Graph Analytics")
    
    afis = AFISReader()
    apex = APEXReader()
    
    transactions = afis.get_all_transactions() if afis.is_connected() else []
    invoices = apex.get_all_invoices() if apex.is_connected() else []

    # Chama a skill para estruturar o grafo
    graph_data = build_entity_graph(transactions, invoices)

    # Identifica contrapartes com alto risco
    high_risk_partners = []
    for node in graph_data.get("nodes", []):
        if node.get("risk_level") in ["high", "critical"]:
            high_risk_partners.append(node)

    return {
        **state,
        "graph_data": graph_data,
        "high_risk_partners": high_risk_partners,
        "completed_steps": state.get("completed_steps", []) + ["graph_analytics"]
    }


