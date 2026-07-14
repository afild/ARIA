"""
Corporate Standard Module: graph
This module is part of the ARIA core framework.
"""
from typing import Any
from fastapi import APIRouter, HTTPException
from app.plugins.afis_reader import AFISReader
from app.plugins.apex_reader import APEXReader
from app.skills.build_entity_graph import build_entity_graph

router = APIRouter(prefix="/graph", tags=["Graph"])

@router.get("/connections")
def get_graph_connections() -> Any:
    """
    Retorna o mapeamento em grafo dos relacionamentos financeiros entre a PME,
    seus clientes e seus fornecedores para plotagem no frontend.
    """
    afis = AFISReader()
    apex = APEXReader()
    
    try:
        transactions = afis.get_all_transactions() if afis.is_connected() else []
        invoices = apex.get_all_invoices() if apex.is_connected() else []

        graph_data = build_entity_graph(transactions, invoices)
        return graph_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao extrair conexões do grafo: {e}")


