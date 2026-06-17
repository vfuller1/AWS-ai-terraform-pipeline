from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from langchain_openai import ChatOpenAI

from agents.llm_utils import extract_code_block
from agents.state import ProvisioningState

# CAPSTONE: Agent → Action
# Generates Terraform HCL and validates it by running terraform init/plan.


def _render_fallback_hcl(state: ProvisioningState) -> str:
    resource_type = state.get("resource_type", "ec2")
    name = state.get("resource_name", "prod-infra-ec2-main")
    region = state.get("resource_region", "us-east-1")
    created_by = state.get("created_by", "unknown")
    created_date = date.today().isoformat()
    return (
        f'terraform {{\n  required_version = ">= 1.5.0"\n}}\n\n'
        'provider "aws" {\n'
        f'  region = "{region}"\n'
        '}\n\n'
        'locals {\n'
        f'  resource_type = "{resource_type}"\n'
        '}\n\n'
        'resource "null_resource" "placeholder" {\n'
        '  triggers = {\n'
        f'    name = "{name}"\n'
        f'    Owner = "{created_by}"\n'
        f'    CreatedDate = "{created_date}"\n'
        '    ManagedBy = "terraform-ai"\n'
        '    Environment = "prod"\n'
        '  }\n'
        '}\n'
    )


def planner_agent(state: ProvisioningState) -> ProvisioningState:
    print("[planner_agent] Generating Terraform and running plan")
    next_state: ProvisioningState = dict(state)

    prompt = (
        "Generate Terraform HCL for AWS resource provisioning. Include tags Owner=var.created_by, "
        "CreatedDate=var.created_date, ManagedBy=\"terraform-ai\", Environment=\"prod\". "
        f"Resource type: {next_state.get('resource_type', 'ec2')}, "
        f"Region: {next_state.get('resource_region', 'us-east-1')}, "
        f"Name: {next_state.get('resource_name', 'prod-infra-ec2-main')}, "
        f"Extra tags: {next_state.get('resource_tags', {})}."
    )

    hcl = ""
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        response = llm.invoke(prompt)
        hcl = extract_code_block(str(response.content))
        print("[planner_agent] LLM produced Terraform HCL")
    except Exception as exc:
        print(f"[planner_agent] LLM HCL generation failed, using fallback: {exc}")
        hcl = _render_fallback_hcl(next_state)

    next_state["terraform_hcl"] = hcl

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tf_dir = Path(tmpdir)
            (tf_dir / "main.tf").write_text(hcl, encoding="utf-8")

            subprocess.run(["terraform", "init", "-input=false", "-no-color"], cwd=tf_dir, check=True, capture_output=True, text=True)
            plan_result = subprocess.run(
                [
                    "terraform",
                    "plan",
                    "-input=false",
                    "-no-color",
                    "-json",
                    f"-var=created_by={next_state.get('created_by', 'unknown')}",
                    f"-var=created_date={date.today().isoformat()}",
                ],
                cwd=tf_dir,
                capture_output=True,
                text=True,
            )

            if plan_result.returncode == 0:
                next_state["plan_status"] = "success"
                next_state["plan_error"] = None
            else:
                next_state["plan_status"] = "failed"
                next_state["plan_error"] = plan_result.stderr or plan_result.stdout

            try:
                parsed_json = json.loads(plan_result.stdout) if plan_result.stdout else {}
                next_state["terraform_plan_json"] = json.dumps(parsed_json)
            except Exception:
                next_state["terraform_plan_json"] = plan_result.stdout or "{}"

            print(f"[planner_agent] Plan status: {next_state.get('plan_status')}")
    except Exception as exc:
        print(f"[planner_agent] Terraform planning failed: {exc}")
        next_state["plan_status"] = "failed"
        next_state["plan_error"] = str(exc)
        next_state["terraform_plan_json"] = "{}"

    return next_state
