"""
Corporate Standard Module: llm_client
This module is part of the ARIA core framework.
"""
import os
import json
import logging
from typing import AsyncGenerator, Type, TypeVar, Any
from pydantic import BaseModel, ValidationError
from app.config import settings

T = TypeVar('T', bound=BaseModel)

class LLMClient:
    """
    Cliente unificado para chamadas LLM à Anthropic Claude com fallback offline baseado em regras.
    Inclui suporte robusto a Structured Parsing e mitigação de alucinação de esquemas.
    """

    def __init__(self) -> None:
        """
        Standard corporate docstring for __init__.
        """
        self.api_key: str = os.environ.get("ANTHROPIC_API_KEY") or settings.ANTHROPIC_API_KEY
        self.model: str = settings.LLM_MODEL
        self.temperature: float = settings.LLM_TEMPERATURE
        self.max_tokens: int = settings.LLM_MAX_TOKENS

    def is_llm_mode(self) -> bool:
        """Retorna True se houver chave de API configurada para usar Claude."""
        return bool(self.api_key)

    async def complete(self, prompt: str, system_prompt: str = "") -> str:
        """
        Chamada síncrona/assíncrona de completions com fallback de regras.
        
        Args:
            prompt (str): A entrada principal do usuário ou dados.
            system_prompt (str): Prompt de sistema (contexto/instruções).
            
        Returns:
            str: O texto puro gerado pelo LLM.
        """
        if not self.is_llm_mode():
            return self._offline_fallback(prompt, system_prompt)

        try:
            import httpx
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            data = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": system_prompt,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=data
                )
                if response.status_code == 200:
                    res_json = response.json()
                    return res_json["content"][0]["text"]
                else:
                    logging.error(f"Erro na API da Anthropic ({response.status_code}): {response.text}")
                    return self._offline_fallback(prompt, system_prompt)
        except Exception as e:
            logging.error(f"Exceção ao chamar LLM: {e}. Entrando em modo offline fallback.")
            return self._offline_fallback(prompt, system_prompt)

    async def complete_structured(self, prompt: str, system_prompt: str, response_model: Type[T]) -> T:
        """
        Garante que o output do LLM siga estritamente o esquema Pydantic fornecido (Structured Parsing).
        
        Args:
            prompt (str): A entrada do usuário.
            system_prompt (str): Contexto (será injetado o schema).
            response_model (Type[BaseModel]): A classe Pydantic para validação do JSON.
            
        Returns:
            BaseModel: Uma instância validada do response_model.
        """
        schema_json = response_model.schema_json()
        structured_system = (
            f"{system_prompt}\n\n"
            f"You MUST return ONLY a valid JSON object matching this JSON schema:\n{schema_json}\n"
            f"Do not include markdown blocks, explanations, or any other text before or after the JSON."
        )
        
        raw_text = await self.complete(prompt, system_prompt=structured_system)
        
        # Tentativa agressiva de encontrar e parsear o bloco JSON
        try:
            # Caso o LLM tenha inserido blocos de markdown ```json ... ```
            clean_text = raw_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
                
            clean_text = clean_text.strip()
            data = json.loads(clean_text)
            return response_model(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            logging.error(f"Erro de parsing estruturado ou alucinação do LLM: {e}")
            logging.error(f"Raw output: {raw_text}")
            
            # Retorna um fallback robusto usando um modelo sintético/vazio se falhar
            # Permite a progressão no LangGraph sem crashar a máquina de estados
            logging.warning("Iniciando modo fallback estruturado instanciando schema padrão.")
            # Um contorno: retorna valores nulos se o schema permitir, ou delega o erro pro fluxo 
            # (neste caso, instanciaremos usando construct sem validar rigorosamente, 
            # ou deixaremos o orchestrator tratar, dependendo da necessidade).
            # Para segurança máxima: raise para ser tratado no try/except do orchestrator (safe_node)
            raise ValueError(f"Failed to parse LLM structured output: {e}")

    async def complete_stream(self, prompt: str, system_prompt: str = "") -> AsyncGenerator[str, None]:
        """Streaming SSE das completions da Claude com fallback instantâneo."""
        if not self.is_llm_mode():
            fallback_text = self._offline_fallback(prompt, system_prompt)
            # Simula streaming no fallback enviando palavras aos poucos
            words = fallback_text.split(" ")
            for i in range(0, len(words), 3):
                chunk = " ".join(words[i:i+3]) + " "
                yield chunk
                import asyncio
                await asyncio.sleep(0.05)
            return

        try:
            import httpx
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            data = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": system_prompt,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST",
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=data
                ) as stream:
                    if stream.status_code != 200:
                        fallback_text = self._offline_fallback(prompt, system_prompt)
                        yield f"[Fallback] {fallback_text}"
                        return

                    async for line in stream.iter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data:"):
                            continue
                        
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            event = json.loads(data_str)
                            if event.get("type") == "content_block_delta":
                                delta = event.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                        except Exception:
                            continue
        except Exception as e:
            logging.error(f"Erro no stream do LLM: {e}")
            fallback_text = self._offline_fallback(prompt, system_prompt)
            yield f"[Fallback] {fallback_text}"

    def _offline_fallback(self, prompt: str, system_prompt: str) -> str:
        """Gera respostas heurísticas lógicas baseadas em regras de negócio para PMEs."""
        prompt_lower = prompt.lower()
        
        # Identifica o assunto da pergunta e aplica a heurística
        if "dscr" in prompt_lower:
            return (
                "O Debt Service Coverage Ratio (DSCR) é uma métrica chave usada por bancos (especialmente SBA) "
                "para avaliar a elegibilidade de crédito. Um DSCR >= 1.25 indica que a empresa gera fluxo de caixa "
                "suficiente para cobrir 125% do serviço da dívida proposta. "
                "Se o seu DSCR estiver abaixo de 1.25, recomendamos renegociar despesas correntes, alongar os prazos "
                "de pagamentos de empréstimos existentes ou aumentar o aporte de capital próprio. [SBA SOP 50 10, Sec. 1]"
            )
        elif "dso" in prompt_lower or "recebíveis" in prompt_lower or "cobrança" in prompt_lower:
            return (
                "Days Sales Outstanding (DSO) mede o tempo médio que o negócio leva para receber pagamentos após a venda. "
                "De acordo com as boas práticas e diretrizes de crédito do SBA, um DSO acima de 45 dias representa um risco "
                "alto para o fluxo de caixa. Recomendamos implementar réguas de cobrança automatizadas (como as do APEX) "
                "e revisar a política de prazos concedida aos clientes com maior atraso. [SBA SOP 50 10, Sec. 3]"
            )
        elif "fraude" in prompt_lower or "anomalia" in prompt_lower or "suspeito" in prompt_lower:
            return (
                "O sistema ARIA identificou possíveis desvios ou anomalias transacionais usando algoritmos estatísticos. "
                "Padrões de transferências rápidas ou faturas duplicadas representam alto risco operacional e devem ser "
                "revisados no menu 'Alerts' por um operador humano antes de aprovar novas transações contábeis. [SBA SOP 50 10, Sec. 5]"
            )
        elif "lender" in prompt_lower or "empréstimo" in prompt_lower or "banco" in prompt_lower:
            return (
                "Para preparar a empresa para captar recursos em bancos sob o framework SBA, certifique-se de que: "
                "1) Seu Credit Score interno esteja na faixa de bom/excelente (acima de 70). "
                "2) O DSCR seja superior a 1.25. "
                "3) A concentração de recebíveis em um único cliente não ultrapasse 25% do faturamento total. "
                "Gerando o relatório 'Lender Readiness Report', você obterá um dossiê completo de conformidade. [SBA SOP 50 10, Sec. 4]"
            )
        
        # Resposta genérica padrão inteligente baseada no contexto do sistema
        return (
            "Esta é uma análise do Advisor do ARIA. De acordo com as diretrizes do SBA SOP 50 10, a saúde financeira "
            "do negócio deve ser monitorada através de índices de liquidez (Current Ratio > 1.25) e DSCR. "
            "Se você estiver buscando crédito ou revisando riscos operacionais, consulte o painel de métricas "
            "e verifique os alertas pendentes de auditoria. Para decisões críticas, consulte um CPA licenciado."
        )

# Instância Singleton
llm_client_instance: Any = None

def get_llm_client() -> LLMClient:
    """
    Retorna a instância singleton do LLMClient.
    
    Returns:
        LLMClient: O cliente global instanciado.
    """
    global llm_client_instance
    if llm_client_instance is None:
        llm_client_instance = LLMClient()
    return llm_client_instance


