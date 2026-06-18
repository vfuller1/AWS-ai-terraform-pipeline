from __future__ import annotations

import os
from typing import Any

from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from agents.llm_utils import extract_code_block, get_llm
from agents.state import ProvisioningState

# CAPSTONE: Agent → Decision
# Extracts provisioning intent fields from natural language using structured parsing.


class IntakeExtraction(BaseModel):
    resource_type: str = Field(description="Resource type: ec2, s3, or vpc")
    resource_region: str = Field(description="AWS region, e.g. us-east-1")
    resource_tags: dict[str, Any] = Field(default_factory=dict)


def intake_agent(state: ProvisioningState) -> ProvisioningState:
    print("[intake_agent] Parsing provisioning request")
    next_state: ProvisioningState = dict(state)

    user_request = next_state.get("user_request", "")
    created_by = os.getenv("GITHUB_ACTOR") or os.getenv("USER") or "unknown"

    parser = PydanticOutputParser(pydantic_object=IntakeExtraction)
    prompt = PromptTemplate(
        template=(
            "Extract provisioning fields from this request:\n"
            "{user_request}\n\n"
            "{format_instructions}"
        ),
        input_variables=["user_request"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    parsed: IntakeExtraction | None = None
    try:
        llm = get_llm()
        response = llm.invoke(prompt.format(user_request=user_request))
        parsed = parser.parse(extract_code_block(str(response.content)))
        print("[intake_agent] LLM extraction successful")
    except Exception as exc:
        print(f"[intake_agent] LLM extraction failed, using fallback: {exc}")

    next_state["resource_type"] = (parsed.resource_type if parsed else "ec2").lower()
    next_state["resource_region"] = parsed.resource_region if parsed else "us-east-1"
    next_state["resource_tags"] = parsed.resource_tags if parsed else {}
    next_state["created_by"] = created_by
    next_state["retry_count"] = 0
    next_state["fix_applied"] = False
    next_state["plan_status"] = "pending"
    next_state["plan_error"] = None
    next_state["apply_status"] = "pending"

    return next_state
