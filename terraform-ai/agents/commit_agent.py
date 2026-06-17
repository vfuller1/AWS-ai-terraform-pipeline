from __future__ import annotations

import os

from github import Github

from agents.state import ProvisioningState

# CAPSTONE: Agent → Action
# Commits generated Terraform and creates/updates a GitHub PR with cost and review context.


def _build_pr_body(state: ProvisioningState) -> str:
    fix_notice = "\n> WARNING: Auto-fix was applied. Review changes carefully.\n" if state.get("fix_applied") else ""
    return (
        "## Terraform AI Provisioning Request\n\n"
        "### Resource Details\n"
        "| Field | Value |\n"
        "|---|---|\n"
        f"| Name | {state.get('resource_name', 'unknown')} |\n"
        f"| Type | {state.get('resource_type', 'unknown')} |\n"
        f"| Region | {state.get('resource_region', 'unknown')} |\n"
        f"| Owner | {state.get('created_by', 'unknown')} |\n\n"
        "### Monthly Cost Estimate\n"
        f"- Delta: ${state.get('cost_monthly_delta', 0.0):.2f}/month\n\n"
        "### Cost Breakdown\n"
        "```json\n"
        f"{state.get('cost_breakdown', {})}\n"
        "```\n"
        f"{fix_notice}\n"
        "### Reviewer Checklist\n"
        "- [ ] Validate resource naming and tags\n"
        "- [ ] Validate security controls\n"
        "- [ ] Validate cost impact\n"
        "- [ ] Approve for apply\n"
    )


def commit_agent(state: ProvisioningState) -> ProvisioningState:
    print("[commit_agent] Committing Terraform HCL and opening/updating PR")
    next_state: ProvisioningState = dict(state)

    repo_name = os.getenv("GITHUB_REPO")
    token = os.getenv("GITHUB_TOKEN")
    branch_name = f"terraform-ai/{next_state.get('resource_name', 'resource')}"

    if not repo_name or not token:
        print("[commit_agent] Missing GitHub configuration, skipping remote commit")
        return next_state

    try:
        gh = Github(token)
        repo = gh.get_repo(repo_name)

        base_branch = repo.get_branch("main")
        try:
            repo.get_git_ref(f"heads/{branch_name}")
        except Exception:
            repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=base_branch.commit.sha)

        path = "terraform/main.tf"
        content = next_state.get("terraform_hcl", "")
        commit_sha = None

        try:
            existing = repo.get_contents(path, ref=branch_name)
            resp = repo.update_file(
                path=path,
                message=f"feat(terraform): provision {next_state.get('resource_name', 'resource')}",
                content=content,
                sha=existing.sha,
                branch=branch_name,
            )
            commit_sha = resp.get("commit").sha
        except Exception:
            resp = repo.create_file(
                path=path,
                message=f"feat(terraform): provision {next_state.get('resource_name', 'resource')}",
                content=content,
                branch=branch_name,
            )
            commit_sha = resp.get("commit").sha

        pulls = repo.get_pulls(state="open", head=f"{repo.owner.login}:{branch_name}", base="main")
        pr = None
        if pulls.totalCount > 0:
            pr = pulls[0]
            pr.edit(body=_build_pr_body(next_state))
        else:
            pr = repo.create_pull(
                title=f"[terraform-ai] Provision {next_state.get('resource_name', 'resource')}",
                body=_build_pr_body(next_state),
                head=branch_name,
                base="main",
                draft=False,
            )

        next_state["pr_url"] = pr.html_url
        next_state["pr_number"] = pr.number
        next_state["commit_sha"] = commit_sha
        print(f"[commit_agent] PR ready: {pr.html_url}")
    except Exception as exc:
        print(f"[commit_agent] GitHub commit/PR flow failed: {exc}")

    return next_state
