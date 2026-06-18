from __future__ import annotations

import os
import re

from langchain_aws import ChatBedrockConverse

_FENCE_RE = re.compile(r"```(?:\w+)?\s*\n(.*?)```", re.DOTALL)

DEFAULT_BEDROCK_MODEL_ID = "us.anthropic.claude-sonnet-4-6"


def extract_code_block(text: str) -> str:
    """Return the contents of the first fenced code block, or the trimmed text if none is found."""
    match = _FENCE_RE.search(text)
    return match.group(1).strip() if match else text.strip()


def get_llm(temperature: float = 0) -> ChatBedrockConverse:
    """Build the shared AWS Bedrock (Claude 3.5 Sonnet) chat client used by all agents."""
    return ChatBedrockConverse(
        model=os.getenv("BEDROCK_MODEL_ID", DEFAULT_BEDROCK_MODEL_ID),
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        temperature=temperature,
    )
