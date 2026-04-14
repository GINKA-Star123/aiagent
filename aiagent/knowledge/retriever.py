"""Retriever placeholder."""
import re
from dataclasses import dataclass

@dataclass(slots = True)
class RetrievedChunk:
    content: str
    score:int

class SimpleKeyWordRetriever:
    def split_sections(self,text:str) -> list[str]:
        sections = [section.strip() for section in text.split("\n## ") if section.strip()]

        return sections
    
    def retrieve(self,query:str,document_text :str,top_k:int = 3) -> list[RetrievedChunk]:

        query_items = self._tokenize(query)
        sections = self.split_sections(document_text)

        scored: list[RetrievedChunk] = []
        for section in sections:
            score = self._score(query_items,section)
            if score>0:
                scored.append(RetrievedChunk(section,score))

    def _tokenize(self,text:str) -> list[str]:
        text = text.lower()
        tokens = re.split(r"[\s,，。！？!?.:：;；]+",text)
        return [token for token in tokens if token]
    
    def _score(self,query_items:list[str],section:str) ->int:
        section_lower =section.lower()
        return sum(1 for term in query_items if term in section_lower)