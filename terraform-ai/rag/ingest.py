from __future__ import annotations

import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction


def _split_sections(markdown_text: str) -> list[str]:
    sections: list[str] = []
    raw_sections = markdown_text.split("## ")

    for idx, section in enumerate(raw_sections):
        content = section.strip()
        if not content:
            continue
        if idx > 0:
            content = "## " + content

        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        if len(content) > 1400 and len(paragraphs) > 1:
            sections.extend(paragraphs)
        else:
            sections.append(content)

    return sections


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    rules_file = base_dir / "naming_conventions.md"
    chroma_path = base_dir / "chroma_store"

    if not rules_file.exists():
        raise FileNotFoundError(f"Missing file: {rules_file}")

    text = rules_file.read_text(encoding="utf-8")
    chunks = _split_sections(text)

    print(f"[ingest] Loaded {len(chunks)} chunks from naming conventions")

    client = chromadb.PersistentClient(path=str(chroma_path))
    embedding_fn = OpenAIEmbeddingFunction(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model_name="text-embedding-3-small",
    )

    collection = client.get_or_create_collection("naming_conventions", embedding_function=embedding_fn)

    ids = [f"naming-rule-{i+1}" for i in range(len(chunks))]
    metadatas = [{"source": "rag/naming_conventions.md", "chunk": i + 1} for i in range(len(chunks))]

    try:
        # Replace previous contents to keep ingestion deterministic.
        existing = collection.get(include=[])
        existing_ids = existing.get("ids", [])
        if existing_ids:
            collection.delete(ids=existing_ids)
    except Exception:
        pass

    collection.add(ids=ids, documents=chunks, metadatas=metadatas)

    print(f"[ingest] Stored {len(chunks)} chunks in collection 'naming_conventions'")
    print(f"[ingest] Chroma persistent store: {chroma_path}")
    print("[ingest] Completed successfully")


if __name__ == "__main__":
    main()
