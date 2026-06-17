from __future__ import annotations

import re

_FENCE_RE = re.compile(r"```(?:\w+)?\s*\n(.*?)```", re.DOTALL)


def extract_code_block(text: str) -> str:
    """Return the contents of the first fenced code block, or the trimmed text if none is found."""
    match = _FENCE_RE.search(text)
    return match.group(1).strip() if match else text.strip()
