from __future__ import annotations

import os

from github import Github

from agents.llm_utils import extract_code_block, get_llm
from agents.state import ProvisioningState

# CAPSTONE: Agent → Action
# Applies automatic Terraform fixes from plan errors and commits to PR branch.


def fix_agent(state: ProvisioningState) -> ProvisioningState:
    print("[fix_agent] Evaluating fix attempt")
    next_state: ProvisioningState = dict(state)

    retry_count = int(next_state.get("retry_count", 0))
    if retry_count >= 3:
        print("[fix_agent] Max retries reached, escalating to human")
        next_state["plan_status"] = "failed"
        return next_state

    try:
        llm = get_llm()
        prompt = (
            "Fix this Terraform HCL based on the plan error. Return only corrected HCL.\n\n"
            f"Plan error:\n{next_state.get('plan_error', '')}\n\n"
            f"Current HCL:\n{next_state.get('terraform_hcl', '')}"
        )
        response = llm.invoke(prompt)
        fixed_hcl = extract_code_block(str(response.content))
        next_state["terraform_hcl"] = fixed_hcl
        print("[fix_agent] LLM produced corrected HCL")
    except Exception as exc:
        print(f"[fix_agent] Failed to generate corrected HCL: {exc}")

    retry_count += 1
    next_state["retry_count"] = retry_count
    next_state["fix_applied"] = True
    next_state["plan_status"] = "pending"

    repo_name = os.getenv("GITHUB_REPO")
    token = os.getenv("GITHUB_TOKEN")
    pr_number = next_state.get("pr_number")

    try:
        if repo_name and token and pr_number:
            gh = Github(token)
            repo = gh.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            branch = pr.head.ref
            path = "terraform/main.tf"

            try:
                existing = repo.get_contents(path, ref=branch)
                repo.update_file(
                    path=path,
                    message=f"fix(terraform): auto-correct plan error [attempt {retry_count}]",
                    content=next_state.get("terraform_hcl", ""),
                    sha=existing.sha,
                    branch=branch,
                )
            except Exception:
                repo.create_file(
                    path=path,
                    message=f"fix(terraform): auto-correct plan error [attempt {retry_count}]",
                    content=next_state.get("terraform_hcl", ""),
                    branch=branch,
                )
            print("[fix_agent] Updated PR branch with fix")
    except Exception as exc:
        print(f"[fix_agent] GitHub update failed: {exc}")

    return next_state
