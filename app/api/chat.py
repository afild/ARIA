"""
Corporate Standard Module: chat
This module is part of the ARIA core framework.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
import json
import logging
from datetime import datetime

from app.database.db_manager import get_db, SessionLocal
from app.database.models import RiskChatHistory
from app.rag.vector_store import get_or_create_vector_store
from app.llm_client import get_llm_client
import contextlib

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.get("/history/{session_id}")
def get_chat_history(session_id: str, db: Session = Depends(get_db)) -> List[dict]:
    """
    Retorna as mensagens de chat ordenadas cronologicamente.
    
    Args:
        session_id (str): ID único da sessão do usuário/analista.
        db (Session): Sessão do banco de dados injetada via FastAPI.
        
    Returns:
        List[dict]: Lista de mensagens do histórico formatadas em dicionário.
    """
    messages = db.query(RiskChatHistory).filter(
        RiskChatHistory.session_id == session_id
    ).order_by(RiskChatHistory.created_at.asc()).all()
    
    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "citations": json.loads(msg.citations) if msg.citations else [],
            "created_at": msg.created_at
        }
        for msg in messages
    ]

@router.delete("/history/{session_id}")
def clear_chat_history(session_id: str, db: Session = Depends(get_db)) -> dict:
    """
    Limpa o histórico do chat de uma sessão.
    
    Args:
        session_id (str): ID único da sessão do usuário/analista.
        db (Session): Sessão do banco de dados.
        
    Returns:
        dict: Status de deleção caso suceda.
    """
    try:
        db.query(RiskChatHistory).filter(RiskChatHistory.session_id == session_id).delete()
        db.commit()
        return {"status": "deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao limpar histórico: {e}")

@router.post("/message")
async def send_chat_message(
    session_id: str = Body(...),
    message: str = Body(...),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    Processa uma mensagem do usuário, realiza busca RAG e transmite a resposta do LLM via SSE.
    Registra a conversa na base local de histórico.
    
    Args:
        session_id (str): ID da sessão.
        message (str): Mensagem do usuário.
        db (Session): Sessão ativa do BD.
        
    Returns:
        StreamingResponse: Stream SSE com chunks da resposta.
    """
    vs = get_or_create_vector_store()
    llm = get_llm_client()

    # 1. Consulta o RAG
    rag_results = vs.query(message, top_k=3)
    citations = [res["citation"] for res in rag_results if "citation" in res]
    guidelines_context = "\n".join([f"- {res['text']}" for res in rag_results])

    # 2. Registra a pergunta do usuário no banco local
    try:
        user_msg = RiskChatHistory(
            session_id=session_id,
            role="user",
            content=message,
            citations=None
        )
        db.add(user_msg)
        db.commit()
    except Exception as e:
        db.rollback()
        logging.error(f"Erro ao gravar pergunta no histórico: {e}")

    # 3. Define a lógica de streaming SSE
    async def sse_generator():
        # Caso não haja resultados RAG (similaridade muito baixa ou coleção vazia), aplica recusa padrão
        if not rag_results:
            recusal = "Não há dados estruturados suficientes nas diretrizes SBA para emitir esse parecer. Recomendamos consultar seu agente financeiro."
            # Envia como SSE chunk
            yield f"data: {json.dumps({'text': recusal})}\n\n"
            # Grava no banco
            _save_assistant_msg(session_id, recusal, citations)
            return

        # Constrói prompt
        system_prompt = (
            "Você é o ARIA AI Risk Advisor, um assistente especialista em análise de risco e diretrizes "
            "de empréstimos para pequenas e médias empresas (PMEs) americanas (framework SBA SOP 50 10). "
            "Responda apenas com base nas diretrizes e informações fornecidas. Seja curto, direto e cite explicitamente "
            "as referências das diretrizes em formato [SBA SOP 50 10, Sec. X] no corpo de sua resposta."
        )

        prompt = f"""
        Pergunta do Usuário: {message}

        Diretrizes de referência recuperadas do RAG:
        {guidelines_context}

        Se o contexto recuperado não contiver informações relevantes sobre a pergunta do usuário e o score de similaridade for baixo, responda com a mensagem de recusa padrão exata:
        "Não há dados estruturados suficientes nas diretrizes SBA para emitir esse parecer. Recomendamos consultar seu agente financeiro."

        Caso contrário, redija sua resposta estruturada.
        """

        full_response_text = ""
        try:
            async for chunk in llm.complete_stream(prompt, system_prompt):
                full_response_text += chunk
                yield f"data: {json.dumps({'text': chunk})}\n\n"
            
            # Grava a resposta completa do assistente no banco
            _save_assistant_msg(session_id, full_response_text, citations)
        except Exception as e:
            logging.error(f"Erro no streaming do LLM do Advisor Chat: {e}")
            error_msg = "Não há dados estruturados suficientes nas diretrizes SBA para emitir esse parecer. Recomendamos consultar seu agente financeiro."
            yield f"data: {json.dumps({'text': error_msg})}\n\n"
            _save_assistant_msg(session_id, error_msg, citations)

    def _save_assistant_msg(sess_id: str, content: str, cites: list) -> None:
        """
        Salva assíncronamente no BD a resposta do assistente.
        Utiliza contextlib.closing para garantir o fechamento seguro da sessão de DB
        fora do ciclo de vida da requisição HTTP, prevenindo session leaks.
        """
        with contextlib.closing(SessionLocal()) as db_session:
            try:
                assistant_msg = RiskChatHistory(
                    session_id=sess_id,
                    role="assistant",
                    content=content,
                    citations=json.dumps(cites)
                )
                db_session.add(assistant_msg)
                db_session.commit()
            except Exception as err:
                db_session.rollback()
                logging.error(f"Erro ao salvar resposta no banco de dados: {err}")

    return StreamingResponse(sse_generator(), media_type="text/event-stream")



