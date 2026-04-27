from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


class DocumentLoader:
    SUPPORTED_SUFFIXES = {".txt", ".md", ".markdown", ".json", ".jsonl", ".pdf"}

    MARKDOWN_HEADERS = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
        ("####", "h4"),
    ]

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def load_directory(self, directory: str | Path) -> list[Document]:
        root = Path(directory)
        if not root.exists():
            raise FileNotFoundError(f"Knowledge directory not found: {root}")

        documents: list[Document] = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in self.SUPPORTED_SUFFIXES:
                continue

            try:
                documents.extend(self.load_file(path, root_dir=root))
            except Exception as exc:
                self.logger.exception("Failed to load knowledge file %s: %s", path, exc)

        return documents

    def load_file(self, path: str | Path, root_dir: str | Path | None = None) -> list[Document]:
        file_path = Path(path)
        suffix = file_path.suffix.lower()

        if suffix in {".txt"}:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            return [self._build_document(file_path, text, root_dir)]

        if suffix in {".md", ".markdown"}:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            return self._load_markdown(file_path, text, root_dir)

        if suffix == ".json":
            return self._load_json(file_path, root_dir)

        if suffix == ".jsonl":
            return self._load_jsonl(file_path, root_dir)

        if suffix == ".pdf":
            return self._load_pdf(file_path, root_dir)

        return []

    def split_documents(
        self,
        documents: list[Document],
        chunk_size: int = 520,
        chunk_overlap: int = 80,
    ) -> list[Document]:
        if not documents:
            return []

        final_chunks: list[Document] = []

        for doc in documents:
            source_type = str(doc.metadata.get("source_type", "plain"))

            if source_type == "markdown":
                chunks = self._split_markdown_document(
                    doc=doc,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
            else:
                chunks = self._split_plain_document(
                    doc=doc,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )

            final_chunks.extend(chunks)

        return final_chunks

    def _load_markdown(
        self,
        path: Path,
        text: str,
        root_dir: str | Path | None,
    ) -> list[Document]:
        base_doc = self._build_document(path, text, root_dir)
        base_doc.metadata["source_type"] = "markdown"
        return [base_doc]

    def _split_markdown_document(
        self,
        doc: Document,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[Document]:
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.MARKDOWN_HEADERS,
            strip_headers=False,
        )

        try:
            header_docs = markdown_splitter.split_text(doc.page_content)
        except Exception:
            self.logger.exception("Markdown header split failed, fallback to recursive splitter.")
            return self._split_plain_document(doc, chunk_size, chunk_overlap)

        prepared_docs: list[Document] = []
        for header_doc in header_docs:
            metadata = dict(doc.metadata)
            metadata.update(header_doc.metadata)
            metadata["source_type"] = "markdown"

            title = self._title_from_markdown_metadata(metadata) or metadata.get("title")
            if title:
                metadata["title"] = str(title)

            prepared_docs.append(
                Document(
                    page_content=header_doc.page_content.strip(),
                    metadata=metadata,
                )
            )

        return self._split_plain_documents(
            prepared_docs,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def _split_plain_document(
        self,
        doc: Document,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[Document]:
        return self._split_plain_documents(
            [doc],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def _split_plain_documents(
        self,
        documents: list[Document],
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[Document]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", "；", ";", ".", " ", ""],
        )

        chunks: list[Document] = []

        for doc in documents:
            split_docs = splitter.split_documents([doc])

            for index, chunk in enumerate(split_docs):
                content = chunk.page_content.strip()
                if not content:
                    continue

                metadata = dict(chunk.metadata)
                base_doc_id = str(
                    metadata.get("doc_id")
                    or self._hash_text(str(metadata.get("source_path", "")) + content[:500])
                )
                chunk_id = self._hash_text(f"{base_doc_id}:{index}:{content}")

                metadata["doc_id"] = base_doc_id
                metadata["chunk_id"] = chunk_id
                metadata["chunk_index"] = index
                metadata["title"] = metadata.get("title") or self._infer_title(
                    content,
                    str(metadata.get("source_path", "")),
                )

                chunks.append(
                    Document(
                        page_content=content,
                        metadata=metadata,
                    )
                )

        return chunks

    def _load_json(self, path: Path, root_dir: str | Path | None) -> list[Document]:
        data = json.loads(path.read_text(encoding="utf-8"))
        text = self._json_to_text(data)
        doc = self._build_document(path, text, root_dir)
        doc.metadata["source_type"] = "json"
        return [doc]

    def _load_jsonl(self, path: Path, root_dir: str | Path | None) -> list[Document]:
        docs: list[Document] = []
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = line.strip()
            if not line:
                continue

            data = json.loads(line)
            text = self._json_to_text(data)
            doc = self._build_document(path, text, root_dir)
            doc.metadata["line_no"] = line_no
            doc.metadata["doc_id"] = self._hash_text(f"{path}:{line_no}:{text[:500]}")
            doc.metadata["source_type"] = "jsonl"
            docs.append(doc)

        return docs

    def _load_pdf(self, path: Path, root_dir: str | Path | None) -> list[Document]:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF support requires pypdf. Install it with `pip install pypdf`.") from exc

        reader = PdfReader(str(path))
        docs: list[Document] = []

        for page_index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if not text.strip():
                continue

            doc = self._build_document(path, text, root_dir)
            doc.metadata["page"] = page_index + 1
            doc.metadata["doc_id"] = self._hash_text(f"{path}:{page_index}:{text[:500]}")
            doc.metadata["source_type"] = "pdf"
            docs.append(doc)

        return docs

    def _build_document(self, path: Path, text: str, root_dir: str | Path | None) -> Document:
        normalized = text.strip()
        source_path = str(path)

        if root_dir is not None:
            try:
                source_path = str(path.relative_to(Path(root_dir)))
            except ValueError:
                source_path = str(path)

        return Document(
            page_content=normalized,
            metadata={
                "doc_id": self._hash_text(f"{source_path}:{normalized[:500]}"),
                "title": self._infer_title(normalized, path.stem),
                "source_path": source_path,
                "file_name": path.name,
                "file_suffix": path.suffix.lower(),
                "source_type": path.suffix.lower().lstrip("."),
            },
        )

    def _title_from_markdown_metadata(self, metadata: dict[str, Any]) -> str:
        parts = [
            str(metadata.get("h1", "")).strip(),
            str(metadata.get("h2", "")).strip(),
            str(metadata.get("h3", "")).strip(),
            str(metadata.get("h4", "")).strip(),
        ]
        return " / ".join(part for part in parts if part)

    def _json_to_text(self, value: Any) -> str:
        if isinstance(value, str):
            return value

        if isinstance(value, list):
            return "\n".join(self._json_to_text(item) for item in value)

        if isinstance(value, dict):
            lines: list[str] = []
            for key, item in value.items():
                lines.append(f"{key}: {self._json_to_text(item)}")
            return "\n".join(lines)

        return str(value)

    def _infer_title(self, text: str, fallback: str) -> str:
        for line in text.splitlines():
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                return stripped[:80]
        return fallback or "untitled"

    def _hash_text(self, text: str) -> str:
        return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()
