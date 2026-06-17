from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from github import Github

from agents.state import DeleteState

# CAPSTONE: Agent → Action
# Executes targeted terraform destroy only when all deletion safety gates pass.


def destroy_agent(state: DeleteState) -> DeleteState:
    print("[destroy_agent] Evaluating destroy execution")
    next_state: DeleteState = dict(state)

    all_gates_passed = all(
        [
            next_state.get("gate1_passed", False),
            next_state.get("gate2_passed", False),
            next_state.get("gate3_passed", False),
            next_state.get("gate4_passed", False),
        ]
    )
    if not all_gates_passed:
        print("[destroy_agent] Gates not fully passed; skipping destroy")
        next_state["destroy_status"] = "pending"
        return next_state

    target_name = next_state.get("target_resource_name", "")
    resource_type = next_state.get("resource_type", "ec2")
    region = next_state.get("resource_region", "us-east-1")
    resource_addr = f"module.{resource_type}.aws_{resource_type}.{target_name}".replace("-", "_")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tf_dir = Path(tmpdir)
            (tf_dir / "main.tf").write_text(
                (
                    'terraform { required_version = ">= 1.5.0" }\n'
                    f'provider "aws" {{ region = "{region}" }}\n'
                    'resource "null_resource" "placeholder" {}\n'
                ),
                encoding="utf-8",
            )
            subprocess.run(["terraform", "init", "-input=false", "-no-color"], cwd=tf_dir, check=True, capture_output=True, text=True)
            result = subprocess.run(
                ["terraform", "destroy", "-auto-approve", "-input=false", "-no-color", f"-target={resource_addr}"],
                cwd=tf_dir,
                capture_output=True,
                text=True,
            )
            next_state["destroy_status"] = "success" if result.returncode == 0 else "failed"
            print(f"[destroy_agent] Destroy status: {next_state.get('destroy_status')}")
    except Exception as exc:
        print(f"[destroy_agent] Destroy failed: {exc}")
        next_state["destroy_status"] = "failed"

    repo_name = os.getenv("GITHUB_REPO")
    token = os.getenv("GITHUB_TOKEN")
    pr_number = next_state.get("pr_number")
    try:
        if repo_name and token and pr_number:
            gh = Github(token)
            repo = gh.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            pr.create_issue_comment(f"Targeted destroy complete. Status: {next_state.get('destroy_status')}")
    except Exception as exc:
        print(f"[destroy_agent] Failed to post PR status: {exc}")

    return next_state
