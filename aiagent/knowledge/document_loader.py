"""Load and split knowledge documents with LangChain markdown splitter."""
from __future__ import annotations

from pathlib import Path
import re

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class DocumentLoader:
    def load_text(self, file_path: str | Path) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document file not found: {path}")

        for encoding in ("utf-8", "utf-8-sig", "gbk"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue

        return path.read_text(encoding="utf-8", errors="ignore")

    def load_directory(self, directory: str | Path) -> list[Document]:
        root = Path(directory)
        if not root.exists():
            return []

        files: list[Path] = []
        files.extend(sorted(root.glob("*.md")))
        files.extend(sorted(root.glob("*.txt")))

        documents: list[Document] = []
        for path in files:
            if not path.is_file():
                continue

            text = self.load_text(path).strip()
            if not text:
                continue

            doc_id = self._build_doc_id(path)

            if path.suffix.lower() == ".md":
                documents.extend(self._load_markdown_documents(path=path, text=text, doc_id=doc_id))
            else:
                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "doc_id": doc_id,
                            "title": path.stem,
                            "source_path": str(path),
                            "file_name": path.name,
                            "heading_path": [path.stem],
                            "section_level": 0,
                        },
                    )
                )

        return documents

    def split_documents(
        self,
        documents: list[Document],
        chunk_size: int = 520,
        chunk_overlap: int = 80,
    ) -> list[Document]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n",
                "\n",
                "。",
                "！",
                "？",
                "，",
                " ",
                "",
                "."
            ],
        )

        split_docs: list[Document] = []
        chunk_counter: dict[str, int] = {}

        for doc in documents:
            section_docs = splitter.split_documents([doc])

            for split_doc in section_docs:
                content = split_doc.page_content.strip()
                if not content:
                    continue

                metadata = dict(split_doc.metadata)
                title = str(metadata.get("title", "untitled"))
                doc_id = str(metadata.get("doc_id", "unknown"))
                section_key = f"{doc_id}::{title}"
                order = chunk_counter.get(section_key, 0)

                metadata["chunk_id"] = self._build_chunk_id(doc_id=doc_id, title=title, order=order)
                metadata["chunk_order"] = order

                split_docs.append(
                    Document(
                        page_content=content,
                        metadata=metadata,
                    )
                )

                chunk_counter[section_key] = order + 1

        return split_docs

    def _load_markdown_documents(self, path: Path, text: str, doc_id: str) -> list[Document]:
        headers_to_split_on = [
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
            ("####", "h4"),
        ]

        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False,
        )

        docs = splitter.split_text(text)
        normalized_docs: list[Document] = []

        for doc in docs:
            metadata = dict(doc.metadata)

            heading_path = [
                metadata[key]
                for key in ("h1", "h2", "h3", "h4")
                if key in metadata and str(metadata[key]).strip()
            ]

            title = heading_path[-1] if heading_path else path.stem
            section_level = len(heading_path)

            normalized_docs.append(
                Document(
                    page_content=doc.page_content.strip(),
                    metadata={
                        "doc_id": doc_id,
                        "title": title,
                        "source_path": str(path),
                        "file_name": path.name,
                        "heading_path": heading_path or [path.stem],
                        "section_level": section_level,
                    },
                )
            )

        return normalized_docs

    def _build_doc_id(self, path: Path) -> str:
        return re.sub(r"[^a-zA-Z0-9_-]", "_", path.stem.lower())

    def _build_chunk_id(self, doc_id: str, title: str, order: int) -> str:
        safe_title = re.sub(r"[^a-zA-Z0-9_\u4e00-\u9fff-]", "_", title.lower()).strip("_")
        safe_title = safe_title[:40] if safe_title else "section"
        return f"{doc_id}-{safe_title}-chunk-{order:03d}"

KnowledgeDocumentLoader = DocumentLoader