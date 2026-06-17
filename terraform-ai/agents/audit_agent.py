from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import boto3
from github import Github

from agents.state import DeleteState

# CAPSTONE: Agent → Action
# Persists deletion audit records in S3 and GitHub issues for immutable history.


def audit_agent(state: DeleteState) -> DeleteState:
    print("[audit_agent] Recording deletion audit")
    next_state: DeleteState = dict(state)

    now = datetime.now(timezone.utc)
    record = {
        "timestamp": now.isoformat(),
        "created_by": next_state.get("created_by"),
        "resource_name": next_state.get("target_resource_name"),
        "resource_type": next_state.get("resource_type"),
        "resource_region": next_state.get("resource_region"),
        "destroy_status": next_state.get("destroy_status"),
        "dependency_status": next_state.get("dependency_status"),
        "dependencies_found": next_state.get("dependencies_found", []),
        "cost_savings_monthly": next_state.get("cost_savings_monthly", 0.0),
    }

    audit_bucket = os.getenv("AUDIT_S3_BUCKET")
    if audit_bucket:
        try:
            key = (
                f"terraform-ai/audit/deletions/{now.strftime('%Y/%m/%d')}/"
                f"{next_state.get('target_resource_name', 'resource')}-{int(now.timestamp())}.json"
            )
            s3 = boto3.client("s3")
            s3.put_object(Bucket=audit_bucket, Key=key, Body=json.dumps(record, indent=2).encode("utf-8"))
            next_state["audit_record_url"] = f"s3://{audit_bucket}/{key}"
            print(f"[audit_agent] Audit record uploaded: {next_state['audit_record_url']}")
        except Exception as exc:
            print(f"[audit_agent] Failed to upload S3 audit record: {exc}")

    repo_name = os.getenv("GITHUB_REPO")
    token = os.getenv("GITHUB_TOKEN")
    try:
        if repo_name and token:
            gh = Github(token)
            repo = gh.get_repo(repo_name)
            issue = repo.create_issue(
                title=f"[audit] Deleted: {next_state.get('target_resource_name', 'resource')}",
                body=f"```json\n{json.dumps(record, indent=2)}\n```",
                labels=["audit"],
            )
            if not next_state.get("audit_record_url"):
                next_state["audit_record_url"] = issue.html_url
            print(f"[audit_agent] Audit issue created: {issue.html_url}")
    except Exception as exc:
        print(f"[audit_agent] Failed to create audit issue: {exc}")

    return next_state
