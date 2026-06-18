from __future__ import annotations

import json
import os

from github import Github

from agents.llm_utils import extract_code_block, get_llm
from agents.state import ProvisioningState

# CAPSTONE: Agent → Decision
# Decides whether connectivity changes are required for the new resource.


def repo_review_agent(state: ProvisioningState) -> ProvisioningState:
    print("[repo_review_agent] Reviewing repository Terraform files")
    next_state: ProvisioningState = dict(state)

    repo_name = os.getenv("GITHUB_REPO")
    token = os.getenv("GITHUB_TOKEN")
    tf_files: list[dict] = []

    try:
        if not repo_name or not token:
            raise ValueError("Missing GITHUB_REPO or GITHUB_TOKEN")

        gh = Github(token)
        repo = gh.get_repo(repo_name)
        contents = repo.get_contents("")
        queue = list(contents)

        while queue:
            item = queue.pop(0)
            if item.type == "dir":
                queue.extend(repo.get_contents(item.path))
            elif item.path.endswith(".tf"):
                tf_files.append({"path": item.path, "content": item.decoded_content.decode("utf-8", errors="ignore")})

        print(f"[repo_review_agent] Found {len(tf_files)} Terraform files")
    except Exception as exc:
        print(f"[repo_review_agent] Repo fetch failed, continuing with empty context: {exc}")

    next_state["existing_resources"] = tf_files

    decision_prompt = {
        "resource_type": next_state.get("resource_type", "ec2"),
        "resource_name": next_state.get("resource_name", "unknown"),
        "existing_resources": [{"path": f.get("path")} for f in tf_files],
        "instruction": "Return strict JSON with keys: connectivity_needed (bool), connectivity_changes (list[str]), reasoning (str).",
    }

    try:
        llm = get_llm()
        response = llm.invoke(json.dumps(decision_prompt))
        parsed = json.loads(extract_code_block(str(response.content)))
        next_state["connectivity_needed"] = bool(parsed.get("connectivity_needed", False))
        next_state["connectivity_changes"] = list(parsed.get("connectivity_changes", []))
        print("[repo_review_agent] Connectivity decision generated")
    except Exception as exc:
        print(f"[repo_review_agent] Decision failed, defaulting to no connectivity changes: {exc}")
        next_state["connectivity_needed"] = False
        next_state["connectivity_changes"] = []

    return next_state
