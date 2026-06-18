from __future__ import annotations

import os
import re

from langchain_aws import ChatBedrockConverse

_FENCE_RE = re.compile(r"```(?:\w+)?\s*\n(.*?)```", re.DOTALL)

DEFAULT_BEDROCK_MODEL_ID = "us.anthropic.claude-sonnet-4-6"


def extract_code_block(text: str) -> str:
    """Return the contents of the longest fenced code block, or the trimmed text if none is found.

    Some models preface the real payload with a short fenced block (e.g. a file-tree
    sketch) before the actual code/JSON, so picking the first fence is unreliable.
    """
    matches = _FENCE_RE.findall(text)
    if not matches:
        return text.strip()
    return max((m.strip() for m in matches), key=len)


def get_llm(temperature: float = 0) -> ChatBedrockConverse:
    """Build the shared AWS Bedrock (Claude 3.5 Sonnet) chat client used by all agents."""
    return ChatBedrockConverse(
        model=os.getenv("BEDROCK_MODEL_ID", DEFAULT_BEDROCK_MODEL_ID),
        region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        temperature=temperature,
    )
