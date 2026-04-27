"""Vector store placeholder."""
from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

class LangChainVectorStore:
    def __init__(
            self,
            embedding_model_name: str,
            embedding_model_path: str = "",
    ) ->None:
        model_name = embedding_model_path.strip() or embedding_model_name
        if not model_name:
            raise ValueError("Embedding model name or local path must be provided")

        self.embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs = {"device":"cpu"},
            encode_kwargs = {"normalize_embeddings":True}
        )
        self.store : FAISS|None = None

    
    def build(self,documents:list[Document]) ->None:
        if not documents:
            raise ValueError("Cannot build vector store from empty documents")
        
        self.store = FAISS.from_documents(documents,self.embeddings)

    def save(self,directory:str|Path) -> None:
        if self.store is None:
            raise RuntimeError("Vector Store is not built yet")
        
        path = Path(directory)
        path.mkdir(parents=True,exist_ok=True)
        self.store.save_local(str(path))

    def load(self,directory:str|Path) ->None:
        path = Path(directory)
        if not path.exists():
            raise FileNotFoundError(f"vector store directory not found {path}")
        
        self.store = FAISS.load_local(
            str(path),
            self.embeddings,
            allow_dangerous_deserialization=True
        )

    
    def similarity_search(self,query:str, k:int =6) -> list[Document]:
        if self.store is None :
            raise RuntimeError("vector store is not loaded")

        return self.store.similarity_search(query,k=k)
    
    def similarity_search_with_score(self,query:str,k:int=6) ->list[tuple[Document,float]]:
        if self.store is None:
            raise RuntimeError("vector store is not loaded")
        
        raw_results = self.store.similarity_search_with_score(query,k=k)
        results:list[tuple[Document,float]] = []

        for doc,distance in raw_results:
            results.append((doc,self._distance_to_similarity(float(distance))))

        return results 
    
    def count(self) -> int:
        if self.store is None:
            return 0

        return self.store.index.ntotal
    
    def _distance_to_similarity(self,distance:float) -> float:
        score = 1.0-distance/2.0

        if score<0.0:
            return 0.0
        if score>1.0:
            return 1.0
        return score