from __future__ import annotations

import json
import os
from urllib import request

from github import Github

from agents.state import ProvisioningState

# CAPSTONE: Agent → Action
# Creates PR alerts and notifies stakeholders when terraform plan fails.


def alert_agent(state: ProvisioningState) -> ProvisioningState:
    print("[alert_agent] Handling failed plan notification")
    next_state: ProvisioningState = dict(state)

    pr_number = next_state.get("pr_number")
    pr_url = next_state.get("pr_url")
    repo_name = os.getenv("GITHUB_REPO")
    token = os.getenv("GITHUB_TOKEN")

    try:
        if repo_name and token:
            gh = Github(token)
            repo = gh.get_repo(repo_name)

            if pr_number:
                pr = repo.get_pull(pr_number)
            else:
                title = f"[terraform-ai] Plan failed for {next_state.get('resource_name', 'resource')}"
                body = "Automated PR created due to failed plan.\n\nAwaiting user decision."
                pr = repo.create_pull(title=title, body=body, head="main", base="main", draft=True)
                pr_number = pr.number
                pr_url = pr.html_url

            comment = (
                "Terraform plan failed.\n\n"
                f"Error:\n```\n{next_state.get('plan_error', 'unknown')}\n```\n\n"
                "Reply with one of:\n"
                "- terraform-ai: fix it\n"
                "- terraform-ai: abandon\n"
            )
            pr.create_issue_comment(comment)
            print("[alert_agent] PR comment posted")
    except Exception as exc:
        print(f"[alert_agent] GitHub alert flow failed: {exc}")

    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if webhook_url:
        try:
            payload = {
                "text": f"Terraform plan failed for {next_state.get('resource_name', 'resource')}. PR: {pr_url or 'n/a'}"
            }
            req = request.Request(
                webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            request.urlopen(req, timeout=10)
            print("[alert_agent] Slack notification sent")
        except Exception as exc:
            print(f"[alert_agent] Slack notification failed: {exc}")

    next_state["pr_number"] = pr_number
    next_state["pr_url"] = pr_url
    next_state["user_decision"] = None
    return next_state
