"""brain/llm.py — llama.cpp subprocess wrapper optimised for low-RAM devices.

Clawpx4 calls the llama-cli binary (shipped with llama.cpp) via subprocess so
that no additional Python bindings are required and the process terminates after
each inference, reclaiming memory immediately.

Environment variables (loaded from .env via python-dotenv):
    LLAMA_BINARY       – path to the llama-cli executable
    LLAMA_MODEL_PATH   – path to the GGUF model file
    LLAMA_THREADS      – CPU threads (default 4)
    LLAMA_MAX_TOKENS   – tokens to generate (default 512)
    LLAMA_CTX_SIZE     – context window in tokens (default 2048)
    LLAMA_GPU_LAYERS   – GPU layers (default 0 = CPU-only)
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_SYSTEM_PROMPT = (
    "You are Clawpx4, a helpful AI assistant running locally on a Termux "
    "device. Be concise and accurate. When you cannot answer, say so."
)


class LlamaBackend:
    """Thin wrapper around the llama-cli binary for single-shot inference."""

    def __init__(
        self,
        binary: Optional[str] = None,
        model_path: Optional[str] = None,
        threads: int = 4,
        max_tokens: int = 512,
        ctx_size: int = 2048,
        gpu_layers: int = 0,
    ) -> None:
        self.binary = binary or os.getenv("LLAMA_BINARY", "llama-cli")
        self.model_path = model_path or os.getenv("LLAMA_MODEL_PATH", "")
        self.threads = int(os.getenv("LLAMA_THREADS", threads))
        self.max_tokens = int(os.getenv("LLAMA_MAX_TOKENS", max_tokens))
        self.ctx_size = int(os.getenv("LLAMA_CTX_SIZE", ctx_size))
        self.gpu_layers = int(os.getenv("LLAMA_GPU_LAYERS", gpu_layers))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        user_message: str,
        history: Optional[List[dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate a response for *user_message*.

        Args:
            user_message: The latest user input.
            history:      List of ``{"role": "user"|"assistant", "content": str}``
                          conversation turns (most recent last).
            system_prompt: Override the default system prompt.

        Returns:
            The model's text response, stripped of leading/trailing whitespace.

        Raises:
            RuntimeError: If the model binary fails or no model path is set.
        """
        if not self.model_path:
            raise RuntimeError(
                "LLAMA_MODEL_PATH is not set. "
                "Please configure it in your .env file."
            )

        prompt = self._build_prompt(
            user_message,
            history or [],
            system_prompt or _DEFAULT_SYSTEM_PROMPT,
        )
        return self._run_inference(prompt)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        user_message: str,
        history: List[dict],
        system_prompt: str,
    ) -> str:
        """Assemble a ChatML-style prompt string."""
        parts: List[str] = [f"<|im_start|>system\n{system_prompt}<|im_end|>"]
        for turn in history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            parts.append(f"<|im_start|>{role}\n{content}<|im_end|>")
        parts.append(f"<|im_start|>user\n{user_message}<|im_end|>")
        parts.append("<|im_start|>assistant\n")
        return "\n".join(parts)

    def _run_inference(self, prompt: str) -> str:
        """Invoke llama-cli and return its stdout, stripped."""
        cmd = [
            self.binary,
            "--model", self.model_path,
            "--threads", str(self.threads),
            "--ctx-size", str(self.ctx_size),
            "--n-predict", str(self.max_tokens),
            "--n-gpu-layers", str(self.gpu_layers),
            "--log-disable",
            "--prompt", prompt,
        ]
        logger.debug("llama-cli cmd: %s", " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"llama-cli binary not found at '{self.binary}'. "
                "Install llama.cpp and set LLAMA_BINARY in .env."
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("llama-cli timed out after 120 seconds.")

        if result.returncode != 0:
            logger.error("llama-cli stderr: %s", result.stderr)
            raise RuntimeError(
                f"llama-cli exited with code {result.returncode}: {result.stderr[:200]}"
            )

        # The binary echoes the prompt; strip it from the output.
        output = result.stdout
        if prompt in output:
            output = output[output.index(prompt) + len(prompt):]
        return output.strip()


# Module-level singleton (lazy init)
_backend: Optional[LlamaBackend] = None


def get_backend() -> LlamaBackend:
    """Return the module-level :class:`LlamaBackend` singleton."""
    global _backend
    if _backend is None:
        _backend = LlamaBackend()
    return _backend


def generate_response(
    user_message: str,
    history: Optional[List[dict]] = None,
    system_prompt: Optional[str] = None,
) -> str:
    """Convenience function — generate a response using the singleton backend."""
    return get_backend().generate(user_message, history, system_prompt)
