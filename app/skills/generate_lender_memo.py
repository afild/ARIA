"""
Corporate Standard Module: generate_lender_memo
This module is part of the ARIA core framework.
"""
import logging
from typing import Dict, List
from app.llm_client import get_llm_client
from app.rag.vector_store import get_or_create_vector_store

async def generate_lender_memo(credit_profile: Dict, tax_year: int) -> Dict:
    """
    Gera um parecer detalhado (Lender Underwriting Memo) simulando a análise de crédito de um banco comercial.
    Usa o RAG para embasar as decisões nas diretrizes do SBA e o LLM para redigir o documento.
    Caso offline, utiliza templates heurísticos robustos estruturados por regras.
    """
    llm = get_llm_client()
    vs = get_or_create_vector_store()

    score = credit_profile.get("score", 70)
    rating = credit_profile.get("rating", "BBB")
    dscr = credit_profile.get("dscr", 1.25)
    current_ratio = credit_profile.get("current_ratio", 1.2)
    dso = credit_profile.get("dso_days", 30.0)
    concentration = credit_profile.get("ar_concentration", 0.0)
    risk_factors = credit_profile.get("risk_factors", [])

    # Classifica a decisão preliminar baseada nas diretrizes SBA
    if score >= 75 and dscr >= 1.25 and current_ratio >= 1.25:
        decision = "approved"
        decision_label = "APROVADO (Recomendação Fortemente Favorável)"
    elif dscr >= 1.0 and score >= 55:
        decision = "conditional"
        decision_label = "CONDICIONAL (Requer mitigantes adicionais de colateral/avales)"
    else:
        decision = "declined"
        decision_label = "RECUSADO (Alto risco de inadimplência/Inadequação de fluxo)"

    # RAG: Busca termos relacionados no arquivo de diretrizes
    rag_query = f"dscr underwriting requirements current ratio concentration risk"
    rag_results = vs.query(rag_query, top_k=3)
    citations = [res["citation"] for res in rag_results if "citation" in res]

    # Prepara o contexto de diretrizes
    guidelines_context = "\n".join([f"- {res['text']}" for res in rag_results])

    if not llm.is_llm_mode():
        # Fallback offline estruturado
        summary = (
            f"Análise realizada em modo stand-alone (offline fallback). "
            f"A recomendação de crédito para o ano fiscal {tax_year} é classificada como {decision_label}.\n\n"
            f"Fatores de Análise:\n"
            f"- Cobertura da Dívida (DSCR): {dscr:.2f}. "
            f"{'Atende ao requisito de 1.25 estabelecido pelas diretrizes SBA.' if dscr >= 1.25 else 'Abaixo do limite ideal de 1.25, representando vulnerabilidade de caixa.'}\n"
            f"- Liquidez Corrente: {current_ratio:.2f}. "
            f"{'Nível de ativos circulantes confortável para compromissos de curto prazo.' if current_ratio >= 1.25 else 'Liquidez apertada, indicando necessidade de otimização de capital de giro.'}\n"
            f"- Prazos de Recebimento (DSO): {dso:.1f} dias. "
            f"{'Processo de contas a receber saudável.' if dso <= 30.0 else 'Recebíveis lentos, gerando pressão no fluxo de caixa.'}\n"
            f"- Concentração de Clientes: {concentration*100:.1f}%. "
            f"{'Base de clientes bem diversificada.' if concentration <= 0.25 else 'Risco de dependência severo de faturamento.'}\n\n"
            f"Citações de Referência aplicadas:\n"
            f"{', '.join(citations) if citations else '[SBA SOP 50 10, Sec. 1, 2]'}"
        )
        return {
            "decision": decision,
            "summary": summary,
            "citations": citations
        }

    # Prompt System/User para geração rica pela Claude
    system_prompt = (
        "Você é um Underwriter de Risco de Crédito Comercial especializado nas diretrizes do SBA (Small Business Administration). "
        "Sua resposta deve ser extremamente profissional, objetiva, livre de jargões promocionais e centrada em análise de risco factual."
    )

    prompt = f"""
    Gere um Memorando de Decisão de Crédito (Lender Underwriting Memo) para a empresa analisada com os seguintes parâmetros:
    - Ano Fiscal: {tax_year}
    - Score de Crédito Interno: {score}/100
    - Rating Financeiro: {rating}
    - Decisão Preliminar: {decision_label}
    - DSCR: {dscr:.2f}
    - Liquidez Corrente: {current_ratio:.2f}
    - Days Sales Outstanding (DSO): {dso:.1f} dias
    - Concentração de Recebíveis: {concentration*100:.1f}%
    - Fatores de risco identificados pelo sistema: {json.dumps(risk_factors)}

    Diretrizes SBA aplicáveis do RAG:
    {guidelines_context}

    O memorando deve conter as seguintes seções estruturadas:
    1. DECISÃO E RECOMENDAÇÃO (Resumo e veredito)
    2. ANÁLISE DE CAPACIDADE DE PAGAMENTO (Foco no DSCR e EBITDA)
    3. ANÁLISE DE LIQUIDEZ E CAPITAL DE GIRO (Foco no Current Ratio e DSO)
    4. MITIGANTES E CONDIÇÕES (Ações corretivas sugeridas)

    Responda apenas com base nas informações e diretrizes fornecidas. Inclua as citações correspondentes como [SBA SOP 50 10, Sec. X] nos parágrafos relevantes.
    """

    try:
        summary_response = await llm.complete(prompt, system_prompt)
        return {
            "decision": decision,
            "summary": summary_response,
            "citations": citations
        }
    except Exception as e:
        logging.error(f"Erro ao chamar LLM para Lender Memo: {e}. Executando fallback.")
        return {
            "decision": decision,
            "summary": f"Erro temporário na geração do LLM. Decisão preliminar: {decision_label}. Verifique suas métricas de liquidez e DSCR.",
            "citations": citations
        }
