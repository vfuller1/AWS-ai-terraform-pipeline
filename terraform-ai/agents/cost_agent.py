from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from agents.state import ProvisioningState

# CAPSTONE: Agent → Tool
# Calls Infracost CLI to estimate monthly cost impact from terraform plan JSON.


def cost_agent(state: ProvisioningState) -> ProvisioningState:
    print("[cost_agent] Estimating monthly cost delta")
    next_state: ProvisioningState = dict(state)

    plan_json = next_state.get("terraform_plan_json", "{}")
    next_state["cost_monthly_delta"] = 0.0
    next_state["cost_breakdown"] = {}

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "plan.json"
            out_path = Path(tmpdir) / "infracost.json"
            plan_path.write_text(plan_json, encoding="utf-8")

            subprocess.run(
                [
                    "infracost",
                    "breakdown",
                    "--path",
                    str(plan_path),
                    "--format",
                    "json",
                    "--out-file",
                    str(out_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            data = json.loads(out_path.read_text(encoding="utf-8"))
            projects = data.get("projects", [])
            total = 0.0
            for project in projects:
                totals = project.get("breakdown", {}).get("totalMonthlyCost", "0")
                try:
                    total += float(totals)
                except Exception:
                    continue
            next_state["cost_monthly_delta"] = total
            next_state["cost_breakdown"] = data
            print(f"[cost_agent] Infracost monthly delta: {total}")
    except Exception as exc:
        print(f"[cost_agent] Infracost not available or failed, using fallback: {exc}")
        next_state["cost_monthly_delta"] = 0.0
        next_state["cost_breakdown"] = {"note": "infracost unavailable"}

    return next_state
