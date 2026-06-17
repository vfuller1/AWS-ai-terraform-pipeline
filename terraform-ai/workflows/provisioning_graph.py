from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

from agents.alert_agent import alert_agent
from agents.apply_agent import apply_agent
from agents.commit_agent import commit_agent
from agents.cost_agent import cost_agent
from agents.fix_agent import fix_agent
from agents.intake_agent import intake_agent
from agents.naming_rag_agent import naming_rag_agent
from agents.planner_agent import planner_agent
from agents.repo_review_agent import repo_review_agent
from agents.state import ProvisioningState

load_dotenv()


def _route_plan(state: ProvisioningState) -> str:
    return "cost_agent" if state.get("plan_status") == "success" else "alert_agent"


def _route_alert(state: ProvisioningState) -> str:
    decision = state.get("user_decision")
    if decision == "fix":
        return "fix_agent"
    if decision == "abandon":
        return END
    return END


def _route_fix(state: ProvisioningState) -> str:
    return "planner_agent" if int(state.get("retry_count", 0)) < 3 else END


def _route_after_commit(_: ProvisioningState) -> str:
    # In CI, apply is handled by a separate environment-gated GitHub Actions job.
    if os.getenv("GITHUB_ACTIONS"):
        return END
    return "apply_agent"


def build_graph() -> StateGraph:
    graph = StateGraph(ProvisioningState)

    graph.add_node("intake_agent", intake_agent)
    graph.add_node("repo_review_agent", repo_review_agent)
    graph.add_node("naming_rag_agent", naming_rag_agent)
    graph.add_node("planner_agent", planner_agent)
    graph.add_node("alert_agent", alert_agent)
    graph.add_node("fix_agent", fix_agent)
    graph.add_node("cost_agent", cost_agent)
    graph.add_node("commit_agent", commit_agent)
    graph.add_node("apply_agent", apply_agent)

    graph.set_entry_point("intake_agent")

    graph.add_edge("intake_agent", "repo_review_agent")
    graph.add_edge("repo_review_agent", "naming_rag_agent")
    graph.add_edge("naming_rag_agent", "planner_agent")

    graph.add_conditional_edges("planner_agent", _route_plan, {"cost_agent": "cost_agent", "alert_agent": "alert_agent"})
    graph.add_conditional_edges("alert_agent", _route_alert, {"fix_agent": "fix_agent", END: END})
    graph.add_conditional_edges("fix_agent", _route_fix, {"planner_agent": "planner_agent", END: END})

    graph.add_edge("cost_agent", "commit_agent")
    graph.add_conditional_edges("commit_agent", _route_after_commit, {"apply_agent": "apply_agent", END: END})
    graph.add_edge("apply_agent", END)

    return graph


def run_provisioning(user_request: str) -> ProvisioningState:
    app = build_graph().compile()
    initial_state: ProvisioningState = {
        "user_request": user_request,
        "plan_status": "pending",
        "retry_count": 0,
        "fix_applied": False,
        "apply_status": "pending",
    }
    result = app.invoke(initial_state)
    return result


if __name__ == "__main__":
    request = " ".join(sys.argv[1:]).strip() or "Create an EC2 instance for the API team in us-east-1"
    final_state = run_provisioning(request)
    print("[provisioning_graph] Completed with state keys:", sorted(final_state.keys()))
