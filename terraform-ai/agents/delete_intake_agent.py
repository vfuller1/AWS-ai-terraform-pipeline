from __future__ import annotations

import os

from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from agents.llm_utils import extract_code_block, get_llm
from agents.state import DeleteState

# CAPSTONE: Agent → Decision
# Extracts target deletion metadata and initializes gate flags.


class DeleteExtraction(BaseModel):
    target_resource_name: str = Field(description="Name of resource to delete")
    resource_type: str = Field(description="Resource type: ec2, s3, or vpc")
    resource_region: str = Field(description="AWS region")


def delete_intake_agent(state: DeleteState) -> DeleteState:
    print("[delete_intake_agent] Parsing deletion request")
    next_state: DeleteState = dict(state)

    user_request = next_state.get("user_request", "")

    parser = PydanticOutputParser(pydantic_object=DeleteExtraction)
    prompt = PromptTemplate(
        template=(
            "Extract deletion fields from this request:\n"
            "{user_request}\n\n"
            "{format_instructions}"
        ),
        input_variables=["user_request"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    parsed: DeleteExtraction | None = None
    try:
        llm = get_llm()
        response = llm.invoke(prompt.format(user_request=user_request))
        parsed = parser.parse(extract_code_block(str(response.content)))
        print("[delete_intake_agent] LLM extraction successful")
    except Exception as exc:
        print(f"[delete_intake_agent] LLM extraction failed, using fallback: {exc}")

    next_state["target_resource_name"] = parsed.target_resource_name if parsed else "prod-infra-ec2-main"
    next_state["resource_type"] = (parsed.resource_type if parsed else "ec2").lower()
    next_state["resource_region"] = parsed.resource_region if parsed else "us-east-1"
    next_state["created_by"] = os.getenv("GITHUB_ACTOR") or os.getenv("USER") or "unknown"
    next_state["dependencies_found"] = []
    next_state["dependency_status"] = None
    next_state["cost_savings_monthly"] = 0.0
    next_state["is_production"] = False
    next_state["typed_confirmation"] = None
    next_state["gate1_passed"] = False
    next_state["gate2_passed"] = False
    next_state["gate3_passed"] = False
    next_state["gate4_passed"] = False
    next_state["destroy_status"] = "pending"

    return next_state
