"""RAG pipeline placeholder."""
from pathlib import Path

from aiagent.knowledge.document_loader import KnowledgeDocumentLoader
from aiagent.knowledge.retriever import RetrievedChunk,SimpleKeyWordRetriever   
from config.paths import DATA_DIR

class RAGPipeline:
    def __init__(
            self,
            loader: KnowledgeDocumentLoader,
            retriever: SimpleKeyWordRetriever
    ):
        self.loader = loader
        self.retriever = retriever
        self.knowledge_file = DATA_DIR / "knowledge" /"public" /"streaming_basics.md"
        self._cached_document :str|None = None
    
    def retrieve(self,query:str,top_k:int = 3) -> list[RetrievedChunk]:
        document = self._get_document()
        return self.retriever.retrieve(query,document,top_k)
    
    def format_for_prompt(self,query:str,top_k:int =3 ) ->str:
        chunks = self.retrieve(query,top_k)
        if not chunks :
            return "无额外知识击中"
        
        lines = []
        for idx,chunk in enumerate(chunks,start=1):
            lines.append(f"[知识{idx}]\n{chunk.content}")
        return "\n""\n".join(lines)
    
    def _get_document(self) ->str:
        if self._cached_document is None:
            self._cached_document = self.loader.load_markdown(self.knowledge_file)
        return self._cached_document