from __future__ import annotations

import os
from pathlib import Path

import boto3
import chromadb
from chromadb.utils.embedding_functions import AmazonBedrockEmbeddingFunction


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
    session = boto3.Session(region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    embedding_fn = AmazonBedrockEmbeddingFunction(
        session=session,
        model_name=os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v1"),
    )

    try:
        # Drop any collection built with a previous (different-dimension) embedding function.
        client.delete_collection("naming_conventions")
    except Exception:
        pass

    collection = client.get_or_create_collection("naming_conventions", embedding_function=embedding_fn)

    ids = [f"naming-rule-{i+1}" for i in range(len(chunks))]
    metadatas = [{"source": "rag/naming_conventions.md", "chunk": i + 1} for i in range(len(chunks))]

    collection.add(ids=ids, documents=chunks, metadatas=metadatas)

    print(f"[ingest] Stored {len(chunks)} chunks in collection 'naming_conventions'")
    print(f"[ingest] Chroma persistent store: {chroma_path}")
    print("[ingest] Completed successfully")


if __name__ == "__main__":
    main()
