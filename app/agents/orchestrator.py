"""
Corporate Standard Module: orchestrator
This module is part of the ARIA core framework.
"""
import logging
from typing import TypedDict, List, Optional, Literal, Callable, Any
from langgraph.graph import StateGraph, END

# Importa os sub-agentes
from app.agents.transaction_monitor import run_transaction_monitor
from app.agents.graph_analytics import run_graph_analytics
from app.agents.credit_scoring import run_credit_scoring
from app.agents.lender_report import run_lender_report
from app.agents.alert_response import run_alert_response
from app.agents.nist_audit import run_nist_audit
from app.agents.advisor_chat import run_advisor_chat

# Define a estrutura exata do estado compartilhado (TypedDict)
class ARIAAgentState(TypedDict):
    """
    Corporate Standard Class: ARIAAgentState.
    """
    task_type: Literal["scan_risks", "calculate_credit", "generate_lender_report", "advisor_chat"]
    tax_year: int
    session_id: Optional[str]
    user_question: Optional[str]
    user_override: Optional[bool]

    # Dados Intermediários
    scanned_transactions_count: int
    new_alerts_count: int
    calculated_score: Optional[int]
    credit_rating: Optional[str]
    shap_explanations: Optional[dict]
    graph_data: Optional[dict]
    lender_decision: Optional[str]
    lender_memo: Optional[str]
    llm_response: Optional[str]
    citations: List[str]
    report_path: Optional[str]

    # Dados temporários de fluxo
    anomalous_transactions: List[dict]
    high_risk_partners: List[dict]
    credit_profile: Optional[dict]

    # Status
    errors: List[str]
    completed_steps: List[str]

def safe_node(func: Callable[[ARIAAgentState], dict]) -> Callable[[ARIAAgentState], dict]:
    """
    Decorador/Wrapper para execução segura de nós do LangGraph.
    Captura exceções para impedir que o StateGraph inteiro caia, 
    registrando o erro na lista state["errors"].
    
    Args:
        func: A função do nó original do LangGraph.
        
    Returns:
        Callable: A função wrapper protegida por try/catch.
    """
    def wrapper(state: ARIAAgentState) -> dict:
        """
        Standard corporate docstring for wrapper.
        """
        try:
            return func(state)
        except Exception as e:
            error_msg = f"Error in node {func.__name__}: {str(e)}"
            logging.error(error_msg)
            # Retorna o erro acrescentado à lista para tratamento no router/fallback
            errors = state.get("errors", []) + [error_msg]
            return {"errors": errors}
    return wrapper

def build_aria_graph() -> StateGraph:
    """
    Cria e compila o grafo de orquestração LangGraph para o ARIA.
    Todos os nós são encapsulados por safe_node para garantir resiliência Staff-level.
    
    Returns:
        StateGraph: O grafo compilado e pronto para execução.
    """
    graph = StateGraph(ARIAAgentState)

    # Adiciona os nodes de forma segura
    graph.add_node("transaction_monitor", safe_node(run_transaction_monitor))
    graph.add_node("graph_analytics", safe_node(run_graph_analytics))
    graph.add_node("credit_scoring", safe_node(run_credit_scoring))
    graph.add_node("lender_report", safe_node(run_lender_report))
    graph.add_node("alert_response", safe_node(run_alert_response))
    graph.add_node("nist_audit", safe_node(run_nist_audit))
    graph.add_node("advisor_chat", safe_node(run_advisor_chat))

    # Roteamento condicional no entrypoint
    def route_entry(state: ARIAAgentState) -> str:
        """
        Standard corporate docstring for route_entry.
        """
        tt = state.get("task_type")
        logging.info(f"Orquestrador ARIA: Roteando entrypoint para tarefa '{tt}'")
        if tt == "scan_risks":
            return "transaction_monitor"
        elif tt == "calculate_credit":
            return "credit_scoring"
        elif tt == "generate_lender_report":
            return "credit_scoring"  # credit score é dependência obrigatória do lender report
        elif tt == "advisor_chat":
            return "advisor_chat"
        return END

    graph.set_conditional_entry_point(
        route_entry,
        {
            "transaction_monitor": "transaction_monitor",
            "credit_scoring": "credit_scoring",
            "advisor_chat": "advisor_chat",
            END: END
        }
    )

    # Fluxo principal de risco e anomalias
    graph.add_edge("transaction_monitor", "graph_analytics")
    graph.add_edge("graph_analytics", "alert_response")
    graph.add_edge("alert_response", "nist_audit")
    graph.add_edge("nist_audit", END)

    # Roteamento condicional após credit_scoring
    def route_after_credit(state: ARIAAgentState) -> str:
        """
        Standard corporate docstring for route_after_credit.
        """
        tt = state.get("task_type")
        if tt == "generate_lender_report":
            return "lender_report"
        return "nist_audit"

    graph.add_conditional_edges(
        "credit_scoring",
        route_after_credit,
        {
            "lender_report": "lender_report",
            "nist_audit": "nist_audit"
        }
    )
    graph.add_edge("lender_report", "nist_audit")
    graph.add_edge("advisor_chat", "nist_audit")

    return graph.compile()

# Compila a instância global do Grafo
ARIA_GRAPH = build_aria_graph()


