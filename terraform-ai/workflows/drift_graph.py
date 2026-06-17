from __future__ import annotations

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

from agents.drift_scan_agent import drift_scan_agent
from agents.remediation_agent import remediation_agent
from agents.state import DriftState
from agents.triage_agent import triage_agent

load_dotenv()


def _route_triage(state: DriftState) -> str:
    decision = state.get("triage_decision", "alert-only")
    if decision in {"auto-remediate", "open-pr"}:
        return "remediation_agent"
    return END


def build_graph() -> StateGraph:
    graph = StateGraph(DriftState)

    graph.add_node("drift_scan_agent", drift_scan_agent)
    graph.add_node("triage_agent", triage_agent)
    graph.add_node("remediation_agent", remediation_agent)

    graph.set_entry_point("drift_scan_agent")
    graph.add_edge("drift_scan_agent", "triage_agent")
    graph.add_conditional_edges("triage_agent", _route_triage, {"remediation_agent": "remediation_agent", END: END})
    graph.add_edge("remediation_agent", END)

    return graph


def run_drift_detection() -> DriftState:
    app = build_graph().compile()
    initial_state: DriftState = {"drift_detected": False, "drift_details": []}
    return app.invoke(initial_state)


if __name__ == "__main__":
    result = run_drift_detection()
    print("[drift_graph] Completed with state keys:", sorted(result.keys()))
