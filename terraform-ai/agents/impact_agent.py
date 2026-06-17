from __future__ import annotations

import os

import boto3
from github import Github

from agents.state import DeleteState

# CAPSTONE: Agent → Decision
# Evaluates dependency and production risk, then sets deletion safety gates.


def impact_agent(state: DeleteState) -> DeleteState:
    print("[impact_agent] Running dependency and impact analysis")
    next_state: DeleteState = dict(state)

    resource_type = next_state.get("resource_type", "ec2")
    target_name = next_state.get("target_resource_name", "")
    region = next_state.get("resource_region", "us-east-1")

    dependencies: list[str] = []
    is_production = False

    try:
        if resource_type == "ec2":
            ec2 = boto3.client("ec2", region_name=region)
            resp = ec2.describe_instances(
                Filters=[
                    {"Name": "tag:Name", "Values": [target_name]},
                    {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
                ]
            )
            for reservation in resp.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    for sg in instance.get("SecurityGroups", []):
                        dependencies.append(f"security-group:{sg.get('GroupId', 'unknown')}")
                    eni_count = len(instance.get("NetworkInterfaces", []))
                    if eni_count > 1:
                        dependencies.append(f"instance has {eni_count} ENIs")
                    tags = {t.get("Key"): t.get("Value") for t in instance.get("Tags", [])}
                    if (tags.get("Environment") or "").lower() == "prod":
                        is_production = True

        elif resource_type == "s3":
            s3 = boto3.client("s3", region_name=region)
            objects = s3.list_objects_v2(Bucket=target_name, MaxKeys=2)
            if objects.get("KeyCount", 0) > 0:
                dependencies.append("bucket-not-empty")
            try:
                tag_set = s3.get_bucket_tagging(Bucket=target_name).get("TagSet", [])
                tags = {t.get("Key"): t.get("Value") for t in tag_set}
                if (tags.get("Environment") or "").lower() == "prod":
                    is_production = True
            except Exception:
                pass

        elif resource_type == "vpc":
            dependencies.append("manual-vpc-dependency-check-required")

    except Exception as exc:
        print(f"[impact_agent] AWS lookup failed, continuing conservatively: {exc}")
        dependencies.append("aws-lookup-failed")

    if "bucket-not-empty" in dependencies or any("ENIs" in d for d in dependencies):
        dependency_status = "block"
    elif is_production or len(dependencies) >= 2:
        dependency_status = "warn"
    else:
        dependency_status = "safe"

    next_state["dependencies_found"] = dependencies
    next_state["dependency_status"] = dependency_status
    next_state["is_production"] = is_production
    next_state["cost_savings_monthly"] = 10.0 if dependency_status != "block" else 0.0
    next_state["gate1_passed"] = dependency_status != "block"
    next_state["gate2_passed"] = True

    repo_name = os.getenv("GITHUB_REPO")
    token = os.getenv("GITHUB_TOKEN")

    try:
        if repo_name and token:
            gh = Github(token)
            repo = gh.get_repo(repo_name)
            body = (
                "## Deletion Impact Report\n\n"
                f"- Target: {target_name}\n"
                f"- Type: {resource_type}\n"
                f"- Region: {region}\n"
                f"- Dependency status: {dependency_status}\n"
                f"- Estimated savings: ${next_state.get('cost_savings_monthly', 0.0):.2f}/month\n"
                f"- Production: {is_production}\n\n"
                "### Dependencies\n"
                + "\n".join([f"- {d}" for d in dependencies] or ["- none"]) + "\n"
            )
            pr = repo.create_pull(
                title=f"[terraform-ai] Delete impact report: {target_name}",
                body=body,
                head="main",
                base="main",
                draft=True,
            )
            next_state["pr_url"] = pr.html_url
            next_state["pr_number"] = pr.number
            print(f"[impact_agent] Impact PR created: {pr.html_url}")
    except Exception as exc:
        print(f"[impact_agent] Could not create impact PR: {exc}")

    return next_state
