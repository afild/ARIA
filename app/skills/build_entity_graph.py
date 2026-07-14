"""
Corporate Standard Module: build_entity_graph
This module is part of the ARIA core framework.
"""
import logging
from typing import List, Dict

# Tenta importar NetworkX
NETWORKX_AVAILABLE = False
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    logging.warning("NetworkX não disponível. build_entity_graph usará processamento manual.")

def build_entity_graph(transactions: List[Dict], invoices: List[Dict]) -> Dict:
    """
    Constrói a rede de relacionamentos financeiros a partir de transações do AFIS e faturas do APEX.
    Identifica centralidade, volumes financeiros e sinaliza nós com risco de dependência ou fraude.
    Retorna uma estrutura JSON {"nodes": [...], "edges": [...]}.
    """
    # Nós representam: PME Principal, Clientes (AR) e Fornecedores (AP)
    nodes_map = {}
    edges_map = {}
    
    # Adiciona nó da própria PME
    nodes_map["SME_CORE"] = {
        "id": "SME_CORE",
        "label": "Minha Empresa",
        "type": "core",
        "volume": 0.0,
        "risk_level": "low",
        "description": "Nó central operacional."
    }

    # Processa faturas do APEX para identificar clientes/fornecedores e volumes
    for inv in invoices:
        partner = inv.get("counterparty_name")
        if not partner:
            continue
        
        # Tipo da fatura: AP (fornecedor), AR (cliente)
        inv_type = inv.get("invoice_type", "AR")
        amount = float(inv.get("amount", 0.0))
        fraud_score = float(inv.get("fraud_score", 0.0))

        partner_id = f"PARTNER_{partner.upper().replace(' ', '_')}"

        if partner_id not in nodes_map:
            nodes_map[partner_id] = {
                "id": partner_id,
                "label": partner,
                "type": "vendor" if inv_type == "AP" else "customer",
                "volume": 0.0,
                "risk_level": "low",
                "description": ""
            }

        # Acumula volume financeiro do parceiro
        nodes_map[partner_id]["volume"] += amount
        nodes_map["SME_CORE"]["volume"] += amount

        # Atualiza nível de risco baseado em fraude do APEX
        if fraud_score > 0.75:
            nodes_map[partner_id]["risk_level"] = "critical"
        elif fraud_score > 0.50 and nodes_map[partner_id]["risk_level"] != "critical":
            nodes_map[partner_id]["risk_level"] = "medium"

        # Adiciona ou atualiza aresta
        edge_key = (partner_id, "SME_CORE") if inv_type == "AR" else ("SME_CORE", partner_id)
        if edge_key not in edges_map:
            edges_map[edge_key] = {
                "source": edge_key[0],
                "target": edge_key[1],
                "volume": 0.0,
                "count": 0,
                "type": "receivable" if inv_type == "AR" else "payable"
            }
        edges_map[edge_key]["volume"] += amount
        edges_map[edge_key]["count"] += 1

    # Se NetworkX estiver disponível, podemos usá-lo para rodar análises de grafo avançadas
    if NETWORKX_AVAILABLE:
        try:
            G = nx.DiGraph()
            # Adiciona nós e arestas ao grafo direcionado
            for nid, ndata in nodes_map.items():
                G.add_node(nid, **ndata)
            for ekey, edata in edges_map.items():
                G.add_edge(ekey[0], ekey[1], **edata)

            # Calcula centralidade de grau de entrada/saída
            in_degree_cent = nx.in_degree_centrality(G)
            out_degree_cent = nx.out_degree_centrality(G)

            for nid in nodes_map:
                if nid != "SME_CORE":
                    # Identifica risco de concentração (dependência de faturamento > 25%)
                    total_sme_volume = nodes_map["SME_CORE"]["volume"]
                    partner_volume = nodes_map[nid]["volume"]
                    
                    if total_sme_volume > 0:
                        concentration_pct = (partner_volume / total_sme_volume) * 100
                    else:
                        concentration_pct = 0.0
                    
                    # Se representa mais de 25% do faturamento da empresa
                    if nodes_map[nid]["type"] == "customer" and concentration_pct > 25.0:
                        nodes_map[nid]["risk_level"] = "high"
                        nodes_map[nid]["description"] = f"Risco de Concentração: Representa {concentration_pct:.1f}% do faturamento."
                    elif nodes_map[nid]["risk_level"] == "low" and concentration_pct > 15.0:
                        nodes_map[nid]["risk_level"] = "medium"
                        nodes_map[nid]["description"] = f"Concentração moderada ({concentration_pct:.1f}%)."
                    
                    # Adiciona dados de centralidade
                    nodes_map[nid]["in_centrality"] = float(in_degree_cent.get(nid, 0.0))
                    nodes_map[nid]["out_centrality"] = float(out_degree_cent.get(nid, 0.0))
        except Exception as e:
            logging.error(f"Erro ao analisar grafo com NetworkX: {e}")

    # Formata a saída final
    formatted_nodes = list(nodes_map.values())
    formatted_edges = [
        {
            "source": edata["source"],
            "target": edata["target"],
            "volume": float(edata["volume"]),
            "count": edata["count"],
            "type": edata["type"]
        }
        for edata in edges_map.values()
    ]

    return {
        "nodes": formatted_nodes,
        "edges": formatted_edges
    }


