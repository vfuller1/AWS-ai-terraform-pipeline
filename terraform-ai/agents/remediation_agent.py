from __future__ import annotations

import json
import os

from github import Github

from agents.llm_utils import get_llm
from agents.state import DriftState

# CAPSTONE: Agent → Action
# Generates corrected HCL and opens remediation PR for detected drift.


def remediation_agent(state: DriftState) -> DriftState:
    print("[remediation_agent] Building drift remediation PR")
    next_state: DriftState = dict(state)

    details = next_state.get("drift_details", [])
    corrected_hcl = 'resource "null_resource" "drift_remediation" {}\n'

    try:
        llm = get_llm()
        prompt = (
            "Generate corrected Terraform HCL based on this drift detail JSON. Return only HCL.\n"
            f"{json.dumps(details)}"
        )
        response = llm.invoke(prompt)
        corrected_hcl = str(response.content)
        print("[remediation_agent] Generated corrected HCL")
    except Exception as exc:
        print(f"[remediation_agent] Failed to generate corrected HCL, using fallback: {exc}")

    repo_name = os.getenv("GITHUB_REPO")
    token = os.getenv("GITHUB_TOKEN")

    try:
        if repo_name and token:
            gh = Github(token)
            repo = gh.get_repo(repo_name)
            branch = "terraform-ai/drift-remediation"
            base_branch = repo.get_branch("main")
            try:
                repo.get_git_ref(f"heads/{branch}")
            except Exception:
                repo.create_git_ref(ref=f"refs/heads/{branch}", sha=base_branch.commit.sha)

            path = "terraform/main.tf"
            try:
                existing = repo.get_contents(path, ref=branch)
                repo.update_file(path, "fix(terraform): remediate drift", corrected_hcl, existing.sha, branch=branch)
            except Exception:
                repo.create_file(path, "fix(terraform): remediate drift", corrected_hcl, branch=branch)

            pr_body = (
                "## Drift Remediation\n\n"
                f"Decision: {next_state.get('triage_decision', 'open-pr')}\n\n"
                "### Drifted resources\n"
                f"```json\n{json.dumps(details, indent=2)}\n```\n"
            )
            pulls = repo.get_pulls(state="open", head=f"{repo.owner.login}:{branch}", base="main")
            if pulls.totalCount > 0:
                pr = pulls[0]
                pr.edit(body=pr_body)
            else:
                pr = repo.create_pull(
                    title="[terraform-ai] Drift remediation",
                    body=pr_body,
                    head=branch,
                    base="main",
                )
            next_state["remediation_pr_url"] = pr.html_url
            print(f"[remediation_agent] Remediation PR ready: {pr.html_url}")
    except Exception as exc:
        print(f"[remediation_agent] GitHub remediation flow failed: {exc}")

    return next_state
