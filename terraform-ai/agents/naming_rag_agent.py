from __future__ import annotations

import os
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from langchain_openai import ChatOpenAI

from agents.state import ProvisioningState

# CAPSTONE: Agent → Tool
# Uses ChromaDB retrieval to enforce naming convention rules before resource creation.


DEFAULT_RULES = [
    "Use lowercase letters, numbers, and hyphens only.",
    "Use format: {env}-{team}-{resource_type}-{descriptor}.",
    "Maximum length is 63 characters.",
    "Name must start with a letter.",
]


def naming_rag_agent(state: ProvisioningState) -> ProvisioningState:
    print("[naming_rag_agent] Retrieving naming rules from ChromaDB")
    next_state: ProvisioningState = dict(state)

    rules = list(DEFAULT_RULES)
    try:
        base_dir = Path(__file__).resolve().parent.parent
        chroma_path = str(base_dir / "rag" / "chroma_store")
        client = chromadb.PersistentClient(path=chroma_path)
        embedding_fn = OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model_name="text-embedding-3-small",
        )
        collection = client.get_collection("naming_conventions", embedding_function=embedding_fn)
        query_text = (
            f"resource_type={next_state.get('resource_type', 'ec2')}, "
            f"region={next_state.get('resource_region', 'us-east-1')}"
        )
        result = collection.query(query_texts=[query_text], n_results=4)
        docs = result.get("documents", [[]])[0]
        if docs:
            rules = [d.strip() for d in docs if d.strip()]
        print(f"[naming_rag_agent] Retrieved {len(rules)} naming rules")
    except Exception as exc:
        print(f"[naming_rag_agent] Chroma retrieval failed, using defaults: {exc}")

    next_state["naming_rules"] = rules

    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        prompt = (
            "Generate a single AWS resource name compliant with these rules:\n"
            f"Rules: {rules}\n"
            f"Resource type: {next_state.get('resource_type', 'ec2')}\n"
            "Output only the final name in format {env}-{team}-{resource_type}-{descriptor}, lowercase, max 63 chars."
        )
        response = llm.invoke(prompt)
        candidate = str(response.content).strip().splitlines()[0].strip().lower()
        candidate = "".join(ch for ch in candidate if ch.isalnum() or ch == "-")
        if not candidate or len(candidate) > 63 or not candidate[0].isalpha():
            raise ValueError("Generated name violated constraints")
        next_state["resource_name"] = candidate
        print(f"[naming_rag_agent] Name selected: {candidate}")
    except Exception as exc:
        fallback = f"prod-infra-{next_state.get('resource_type', 'ec2')}-main"[:63]
        print(f"[naming_rag_agent] Name generation failed, using fallback '{fallback}': {exc}")
        next_state["resource_name"] = fallback

    return next_state
