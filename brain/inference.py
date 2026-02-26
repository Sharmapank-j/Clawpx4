"""brain/inference.py — Public inference interface for Clawpx4.

This module is the single entry-point that the rest of the codebase uses to
generate text.  It delegates to :mod:`brain.llm` (llama.cpp subprocess
wrapper) and keeps the calling code decoupled from the backend details.

Usage::

    from brain.inference import generate

    reply = generate("What is the capital of France?")
"""

from __future__ import annotations

from typing import List, Optional

from brain.llm import generate_response


def generate(
    user_message: str,
    history: Optional[List[dict]] = None,
    system_prompt: Optional[str] = None,
) -> str:
    """Generate a response for *user_message*.

    Args:
        user_message:  The latest message from the user.
        history:       Previous conversation turns as a list of dicts with
                       ``{"role": "user"|"assistant", "content": str}``.
                       Most-recent turn last.
        system_prompt: Optional override for the default system prompt.

    Returns:
        The model's response as a plain string.

    Raises:
        RuntimeError: If the LLM backend is unavailable or misconfigured.
    """
    return generate_response(
        user_message=user_message,
        history=history,
        system_prompt=system_prompt,
    )
