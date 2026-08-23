"""Minimal live DeepAgents invocation through the OpenAI API."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from deepagents import create_deep_agent

DEFAULT_MODEL = "openai:gpt-5.4"


class MissingApiKeyError(RuntimeError):
    """Raised when a live invocation has no OpenAI credential."""


def invoke_live(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Invoke a DeepAgents graph once and return its final assistant text."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise MissingApiKeyError(
            "OPENAI_API_KEY is not set; export it in this shell before running."
        )

    agent = create_deep_agent(model=model)
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    return result["messages"][-1].text


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send one prompt to a real model through DeepAgents."
    )
    parser.add_argument("prompt", help="Prompt to send to the agent.")
    parser.add_argument(
        "--model",
        default=os.environ.get("DEEPAGENTS_LAB_MODEL", DEFAULT_MODEL),
        help=f"Provider-qualified model name (default: {DEFAULT_MODEL}).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the live invocation command."""
    args = _parser().parse_args(argv)
    try:
        response = invoke_live(args.prompt, model=args.model)
    except MissingApiKeyError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(response)
    return 0
