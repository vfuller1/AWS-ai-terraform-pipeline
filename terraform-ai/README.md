# terraform-ai-capstone

A multi-agent AI system that manages the full lifecycle of AWS infrastructure with LangGraph, Terraform, and GitHub Actions.

## Tech Stack
- LangGraph (`StateGraph`) + LangChain
- OpenAI GPT-4o (`langchain-openai`)
- ChromaDB + OpenAI `text-embedding-3-small`
- boto3 (AWS SDK)
- PyGithub
- Infracost CLI (via subprocess)
- GitHub Actions
- LangSmith tracing
- Promptfoo evaluations

## Project Layout

```text
terraform-ai-capstone/
├── agents/
├── workflows/
├── rag/
├── terraform/
├── evals/
├── .github/workflows/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Workflow 1: Provisioning
Path: `workflows/provisioning_graph.py`

Graph:
- `intake_agent` -> `repo_review_agent` -> `naming_rag_agent` -> `planner_agent`
- `planner_agent` success -> `cost_agent` -> `commit_agent`
- `planner_agent` failed -> `alert_agent` -> (`fix_agent` loop or end)
- `commit_agent` -> `apply_agent` in local mode, end in CI mode

Entry point:
- `run_provisioning(user_request: str) -> ProvisioningState`

## Workflow 2: Drift Detection
Path: `workflows/drift_graph.py`

Graph:
- `drift_scan_agent` -> `triage_agent`
- `triage_agent` auto-remediate/open-pr -> `remediation_agent` -> end
- `triage_agent` alert-only -> end

Entry point:
- `run_drift_detection() -> DriftState`

## Workflow 3: Deletion
Path: `workflows/delete_graph.py`

Safety gates:
- Gate 1 dependency scan (impact)
- Gate 2 cost impact (impact)
- Gate 3 GitHub environment approval
- Gate 4 typed confirmation

Graph:
- `delete_intake_agent` -> `impact_agent`
- block -> end
- else -> `await_gates`
- gates passed -> `destroy_agent` -> `audit_agent` -> end

Entry point:
- `run_deletion(user_request: str) -> DeleteState`

## Capstone Requirements Mapping

| Requirement | Satisfied by |
|-------------|-------------|
| >= 2 Workflows | `workflows/provisioning_graph.py`, `workflows/drift_graph.py`, `workflows/delete_graph.py` |
| >= 2 Agents per workflow | W1: 9 agents, W2: 3 agents, W3: 4 agents |
| Agent -> Tool | `agents/naming_rag_agent.py` (ChromaDB), `agents/cost_agent.py` (Infracost), `agents/drift_scan_agent.py` (Terraform toolchain) |
| Agent -> Action | `agents/commit_agent.py` (auto PR), `agents/remediation_agent.py` (auto PR), `agents/audit_agent.py` (S3 + GitHub issue) |
| Agent -> Decision | `agents/repo_review_agent.py`, `agents/triage_agent.py`, `agents/impact_agent.py` |
| Eval + Fine-tuning | `evals/promptfooconfig.yaml`, LangSmith via `LANGCHAIN_TRACING_V2` |

## Environment Variables
Copy `.env.example` to `.env` and fill required values.

## How To Run

```bash
# 1. Install
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env  # fill in keys

# 3. Ingest RAG knowledge base
python rag/ingest.py

# 4. Run Workflow 1 locally
python workflows/provisioning_graph.py "Create an EC2 instance for the API team in us-east-1"

# 5. Run Workflow 2 locally
python workflows/drift_graph.py

# 6. Run Workflow 3 locally
python workflows/delete_graph.py "Delete the EC2 instance prod-infra-ec2-api"

# 7. Run evals
npm install -g promptfoo
cd evals && promptfoo eval
```

## Notes
- All external API/tool calls are wrapped in try/except with graceful fallbacks.
- Every destroy call uses `terraform destroy -target=...`; no full-workspace destroy is used.
- Fix loop maximum retries is 3.
