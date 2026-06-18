from __future__ import annotations

import json

from agents.llm_utils import get_llm
from agents.state import DriftState

# CAPSTONE: Agent → Decision
# Classifies drift into auto-remediate, open-pr, or alert-only categories.


def triage_agent(state: DriftState) -> DriftState:
    print("[triage_agent] Triage drift details")
    next_state: DriftState = dict(state)

    details = next_state.get("drift_details", [])
    if not details:
        next_state["triage_decision"] = "alert-only"
        return next_state

    prompt = (
        "Decide drift remediation path from this JSON list.\n"
        "Rules: auto-remediate for tag changes only; open-pr for security group/IAM changes; "
        "alert-only for deletions/encryption changes.\n"
        "Return only one token: auto-remediate, open-pr, or alert-only.\n\n"
        f"Drift details:\n{json.dumps(details)}"
    )

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        decision = str(response.content).strip().lower()
        if decision not in {"auto-remediate", "open-pr", "alert-only"}:
            decision = "open-pr"
        next_state["triage_decision"] = decision
        print(f"[triage_agent] Decision={decision}")
    except Exception as exc:
        print(f"[triage_agent] LLM triage failed, using conservative default open-pr: {exc}")
        next_state["triage_decision"] = "open-pr"

    return next_state
