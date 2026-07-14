"""
Corporate Standard Module: advisor_chat
This module is part of the ARIA core framework.
"""
import logging
import json
from typing import Dict
from app.llm_client import get_llm_client
from app.rag.vector_store import get_or_create_vector_store
from app.database.db_manager import SessionLocal
from app.database.models import RiskChatHistory

async def run_advisor_chat(state: Dict) -> Dict:
    """
    Sub-agente responsável pelo chat consultivo do ARIA (AI Risk & Credit Advisor).
    Consulta o ChromaDB para fundamentar as respostas nas diretrizes oficiais SBA e
    chama a API do LLM (ou fallback local). Salva o diálogo no banco.
    """
    logging.info("Iniciando sub-agente: Advisor Chat")

    session_id = state.get("session_id", "default")
    user_question = state.get("user_question", "")

    if not user_question:
        return {**state, "llm_response": "Nenhuma pergunta recebida."}

    # 1. Consulta o RAG (ChromaDB / Fallback Text Search)
    vs = get_or_create_vector_store()
    rag_results = vs.query(user_question, top_k=3)
    citations = [res["citation"] for res in rag_results if "citation" in res]

    # Prepara o contexto de diretrizes
    guidelines_context = "\n".join([f"- {res['text']}" for res in rag_results])

    llm = get_llm_client()

    # 2. Constrói o Prompt do Chat
    system_prompt = (
        "Você é o ARIA AI Risk Advisor, um assistente financeiro especialista em análise de risco e diretrizes "
        "de empréstimos para pequenas e médias empresas (PMEs) americanas (framework SBA SOP 50 10). "
        "Responda apenas com base nas diretrizes e informações fornecidas. Seja curto, direto e cite explicitamente "
        "as referências das diretrizes em formato [SBA SOP 50 10, Sec. X] no corpo de sua resposta."
    )

    prompt = f"""
    Pergunta do Usuário: {user_question}

    Diretrizes de referência recuperadas do RAG:
    {guidelines_context}

    Se o contexto recuperado não contiver informações relevantes sobre a pergunta do usuário e o score de similaridade for baixo, responda com a mensagem de recusa padrão exata:
    "Não há dados estruturados suficientes nas diretrizes SBA para emitir esse parecer. Recomendamos consultar seu agente financeiro."

    Caso contrário, redija sua resposta estruturada.
    """

    response_text = ""
    # Se RAG não retornou resultados e não estamos em modo LLM, ou similaridade foi muito baixa, aplica recusa
    if not rag_results:
        response_text = "Não há dados estruturados suficientes nas diretrizes SBA para emitir esse parecer. Recomendamos consultar seu agente financeiro."
    else:
        try:
            response_text = await llm.complete(prompt, system_prompt)
        except Exception as e:
            logging.error(f"Erro na consulta do LLM do Advisor Chat: {e}")
            response_text = "Não há dados estruturados suficientes nas diretrizes SBA para emitir esse parecer. Recomendamos consultar seu agente financeiro."

    # 3. Salva no banco de dados local a conversa (tanto o user quanto o assistant)
    db = SessionLocal()
    try:
        user_msg = RiskChatHistory(
            session_id=session_id,
            role="user",
            content=user_question,
            citations=None
        )
        assistant_msg = RiskChatHistory(
            session_id=session_id,
            role="assistant",
            content=response_text,
            citations=json.dumps(citations)
        )
        db.add(user_msg)
        db.add(assistant_msg)
        db.commit()
    except Exception as e:
        db.rollback()
        logging.error(f"Erro ao persistir histórico do chat: {e}")
    finally:
        db.close()

    return {
        **state,
        "llm_response": response_text,
        "citations": citations,
        "completed_steps": state.get("completed_steps", []) + ["advisor_chat"]
    }


