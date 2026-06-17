from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from github import Github

from agents.state import ProvisioningState

# CAPSTONE: Agent → Action
# Applies Terraform after approval and records result back to PR.


def apply_agent(state: ProvisioningState) -> ProvisioningState:
    print("[apply_agent] Applying Terraform changes")
    next_state: ProvisioningState = dict(state)

    hcl = next_state.get("terraform_hcl", "")
    if not hcl.strip():
        next_state["apply_status"] = "failed"
        next_state["apply_output"] = "No Terraform HCL available"
        return next_state

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tf_dir = Path(tmpdir)
            (tf_dir / "main.tf").write_text(hcl, encoding="utf-8")

            subprocess.run(["terraform", "init", "-input=false", "-no-color"], cwd=tf_dir, check=True, capture_output=True, text=True)
            result = subprocess.run(
                ["terraform", "apply", "-auto-approve", "-input=false", "-no-color"],
                cwd=tf_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                next_state["apply_status"] = "success"
                next_state["apply_output"] = result.stdout
            else:
                next_state["apply_status"] = "failed"
                next_state["apply_output"] = result.stderr or result.stdout

            print(f"[apply_agent] Apply status: {next_state.get('apply_status')}")
    except Exception as exc:
        next_state["apply_status"] = "failed"
        next_state["apply_output"] = str(exc)
        print(f"[apply_agent] Terraform apply failed: {exc}")

    repo_name = os.getenv("GITHUB_REPO")
    token = os.getenv("GITHUB_TOKEN")
    pr_number = next_state.get("pr_number")

    try:
        if repo_name and token and pr_number:
            gh = Github(token)
            repo = gh.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            pr.create_issue_comment(f"Apply result: {next_state.get('apply_status')}\n\n```\n{next_state.get('apply_output', '')}\n```")
            if next_state.get("apply_status") == "success":
                pr.merge(merge_method="squash")
            print("[apply_agent] PR updated with apply outcome")
    except Exception as exc:
        print(f"[apply_agent] Failed to update PR: {exc}")

    return next_state
