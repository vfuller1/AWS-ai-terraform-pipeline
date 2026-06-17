from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from github import Github

from agents.state import DriftState

# CAPSTONE: Agent → Tool
# Detects Terraform drift by running plan detailed-exitcode and parsing change events.


def drift_scan_agent(state: DriftState) -> DriftState:
    print("[drift_scan_agent] Scanning for drift")
    next_state: DriftState = dict(state)

    repo_name = os.getenv("GITHUB_REPO")
    token = os.getenv("GITHUB_TOKEN")
    main_tf = ""

    try:
        if repo_name and token:
            gh = Github(token)
            repo = gh.get_repo(repo_name)
            file_obj = repo.get_contents("terraform/main.tf", ref="main")
            main_tf = file_obj.decoded_content.decode("utf-8", errors="ignore")
            print("[drift_scan_agent] Pulled terraform/main.tf from GitHub")
    except Exception as exc:
        print(f"[drift_scan_agent] GitHub fetch failed, using fallback local content: {exc}")

    if not main_tf:
        main_tf = 'resource "null_resource" "noop" {}\n'

    drift_detected = False
    drift_details: list[dict] = []

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tf_dir = Path(tmpdir)
            (tf_dir / "main.tf").write_text(main_tf, encoding="utf-8")

            subprocess.run(["terraform", "init", "-input=false", "-no-color"], cwd=tf_dir, check=True, capture_output=True, text=True)
            result = subprocess.run(
                ["terraform", "plan", "-json", "-detailed-exitcode", "-input=false", "-no-color"],
                cwd=tf_dir,
                capture_output=True,
                text=True,
            )

            if result.returncode == 2:
                drift_detected = True
            elif result.returncode not in (0, 2):
                raise RuntimeError(result.stderr or result.stdout)

            for line in (result.stdout or "").splitlines():
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                if event.get("type") == "planned_change":
                    drift_details.append(event)

            print(f"[drift_scan_agent] Drift detected={drift_detected}, changes={len(drift_details)}")
    except Exception as exc:
        print(f"[drift_scan_agent] Drift scan failed gracefully: {exc}")

    next_state["drift_detected"] = drift_detected
    next_state["drift_details"] = drift_details
    next_state["created_by"] = os.getenv("GITHUB_ACTOR") or os.getenv("USER") or "unknown"
    return next_state
