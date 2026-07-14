"""
Corporate Standard Module: vector_store
This module is part of the ARIA core framework.
"""
from typing import Any
import os
import logging
import re
from pathlib import Path
from app.config import settings

# Estrutura para busca offline de fallback se o chromadb/sentence-transformers falharem ou não puderem ser importados
class SimpleTextSearchStore:
    """Fallback simples para busca textual por regex/palavras-chave em caso de ausência do ChromaDB."""

    def __init__(self, file_path -> Any: Path):
        """
        Standard corporate docstring for __init__.
        """
        self.chunks = []
        self.file_path = file_path
        self.load_documents()

    def load_documents(self) -> Any:
        """
        Standard corporate docstring for load_documents.
        """
        if not self.file_path.exists():
            logging.error(f"Arquivo de diretrizes não encontrado em {self.file_path}")
            return
        
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Divide o arquivo em blocos baseados em parágrafos ou marcações [SBA SOP...]
            raw_chunks = re.split(r'\n\s*\n', content.strip())
            for chunk in raw_chunks:
                chunk = chunk.strip()
                if chunk:
                    # Extrai a citação do início do texto, ex: [SBA SOP 50 10, Sec. 1]
                    citation_match = re.match(r'^\[([^\]]+)\]', chunk)
                    citation = citation_match.group(0) if citation_match else "[SBA Guidelines]"
                    self.chunks.append({
                        "text": chunk,
                        "citation": citation
                    })
            logging.info(f"RAG Fallback: {len(self.chunks)} chunks carregados de {self.file_path.name}")
        except Exception as e:
            logging.error(f"Erro ao carregar documentos no SimpleTextSearchStore: {e}")

    def query(self, text: str, top_k: int = 3) -> list[dict]:
        """Faz um match simples de palavras-chave para simular o RAG."""
        words = set(re.findall(r'\w+', text.lower()))
        scored_chunks = []

        for chunk in self.chunks:
            chunk_text_lower = chunk["text"].lower()
            # Calcula interseção simples de termos
            match_count = sum(1 for word in words if word in chunk_text_lower)
            score = match_count / max(len(words), 1)
            # Dá peso extra se houver termos chaves exatos (como dscr, ltv, dso, etc.)
            for term in ["dscr", "liquidez", "dso", "concentração", "fraude"]:
                if term in text.lower() and term in chunk_text_lower:
                    score += 0.2
            
            scored_chunks.append((score, chunk))

        # Ordena por pontuação decrescente
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        # Filtra pelo threshold de 0.65 (simulado)
        results = []
        for score, chunk in scored_chunks[:top_k]:
            normalized_score = min(score, 1.0)
            if normalized_score >= 0.50:  # threshold levemente menor no fallback para garantir respostas
                results.append({
                    "text": chunk["text"],
                    "citation": chunk["citation"],
                    "score": normalized_score
                })
        return results

# Tenta importar ChromaDB e SentenceTransformers
CHROMA_AVAILABLE = False
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    CHROMA_AVAILABLE = True
except ImportError:
    logging.warning("ChromaDB ou SentenceTransformers não estão instalados. Usando SimpleTextSearchStore como fallback.")

class ARIAVectorStore:
    """
    Corporate Standard Class: ARIAVectorStore.
    """
    def __init__(self) -> Any:
        """
        Standard corporate docstring for __init__.
        """
        self.guidelines_file = Path(settings.SBA_GUIDELINES_PATH) / "sba_sop_50_10.txt"
        self.chroma_path = Path(settings.CHROMA_PATH)
        self.fallback_store = SimpleTextSearchStore(self.guidelines_file)
        self.collection = None
        self.client = None
        self.model = None

        if CHROMA_AVAILABLE:
            try:
                # Inicializa cliente ChromaDB
                self.chroma_path.mkdir(parents=True, exist_ok=True)
                self.client = chromadb.PersistentClient(path=str(self.chroma_path))
                
                # Inicializa o modelo de embeddings
                logging.info("Carregando modelo de embeddings sentence-transformers...")
                self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
                
                # Cria ou obtém a collection
                self.collection = self.client.get_or_create_collection(
                    name="sba_guidelines",
                    metadata={"hnsw:space": "cosine"}
                )

                # Indexa se a collection estiver vazia
                if self.collection.count() == 0:
                    self.index_documents()
            except Exception as e:
                logging.error(f"Erro ao inicializar ChromaDB: {e}. Fallback ativado.")
                self.collection = None

    def index_documents(self) -> Any:
        """Indexa o arquivo de diretrizes SBA no ChromaDB."""
        if not self.guidelines_file.exists():
            logging.error(f"Arquivo {self.guidelines_file} não existe para indexação.")
            return

        try:
            with open(self.guidelines_file, "r", encoding="utf-8") as f:
                content = f.read()

            raw_chunks = re.split(r'\n\s*\n', content.strip())
            ids = []
            documents = []
            embeddings = []
            metadatas = []

            for idx, chunk in enumerate(raw_chunks):
                chunk = chunk.strip()
                if not chunk:
                    continue

                citation_match = re.match(r'^\[([^\]]+)\]', chunk)
                citation = citation_match.group(1) if citation_match else "SBA Guidelines"

                ids.append(f"doc_{idx}")
                documents.append(chunk)
                embeddings.append(self.model.encode(chunk).tolist())
                metadatas.append({"citation": citation})

            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            logging.info(f"ChromaDB: {len(documents)} chunks indexados com sucesso.")
        except Exception as e:
            logging.error(f"Erro ao indexar documentos no ChromaDB: {e}")

    def query(self, query_text: str, top_k: int = 3) -> list[dict]:
        """Faz a consulta ao banco vetorial. Caso o Chroma não esteja disponível, usa o SimpleTextSearchStore."""
        if not CHROMA_AVAILABLE or self.collection is None:
            return self.fallback_store.query(query_text, top_k)

        try:
            query_embedding = self.model.encode(query_text).tolist()
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )

            formatted_results = []
            if results and results["documents"]:
                for idx in range(len(results["documents"][0])):
                    doc = results["documents"][0][idx]
                    meta = results["metadatas"][0][idx]
                    distance = results["distances"][0][idx]
                    # Converte distância cosseno para score de similaridade (1 - distância)
                    score = 1.0 - distance
                    
                    formatted_results.append({
                        "text": doc,
                        "citation": f"[{meta['citation']}]",
                        "score": score
                    })

            # Ordena por similaridade
            formatted_results.sort(key=lambda x: x["score"], reverse=True)
            return [res for res in formatted_results if res["score"] >= settings.RAG_SCORE_THRESHOLD]

        except Exception as e:
            logging.error(f"Erro ao consultar ChromaDB: {e}. Executando query no store de fallback.")
            return self.fallback_store.query(query_text, top_k)

# Instância Singleton
vector_store_instance = None

def get_or_create_vector_store() -> ARIAVectorStore:
    """
    Standard corporate docstring for get_or_create_vector_store.
    """
    global vector_store_instance
    if vector_store_instance is None:
        vector_store_instance = ARIAVectorStore()
    return vector_store_instance
