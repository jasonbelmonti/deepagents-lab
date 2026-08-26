"""Project-owned launcher for the unmodified upstream Agent Chat UI."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import NoReturn


UI_RELATIVE_PATH = Path("apps") / "agent-chat-ui"
UI_ENVIRONMENT = {
    "NEXT_PUBLIC_API_URL": "http://127.0.0.1:2024",
    "NEXT_PUBLIC_ASSISTANT_ID": "deepagents_lab",
}
UI_SERVER_ONLY_VARIABLES = (
    "LANGGRAPH_API_URL",
    "NEXT_PUBLIC_AUTH_SCHEME",
)
UI_SERVER_ONLY_PREFIXES = (
    "OPENAI_",
    "LANGSMITH_",
    "LANGCHAIN_",
)
UI_AGENT_DETECTION_VARIABLES = (
    "AI_AGENT",
    "CURSOR_TRACE_ID",
    "CURSOR_AGENT",
    "CURSOR_EXTENSION_HOST_ROLE",
    "GEMINI_CLI",
    "CODEX_SANDBOX",
    "CODEX_CI",
    "CODEX_THREAD_ID",
    "ANTIGRAVITY_AGENT",
    "AUGMENT_AGENT",
    "OPENCODE_CLIENT",
    "CLAUDECODE",
    "CLAUDE_CODE",
    "CLAUDE_CODE_IS_COWORK",
    "REPL_ID",
    "COPILOT_MODEL",
    "COPILOT_ALLOW_ALL",
    "COPILOT_GITHUB_TOKEN",
)
UI_REMOVED_VARIABLES = UI_SERVER_ONLY_VARIABLES + UI_AGENT_DETECTION_VARIABLES


def repository_root() -> Path:
    """Return the checkout containing the package and UI submodule."""
    return Path(__file__).resolve().parents[2]


def submodule_arguments() -> list[str]:
    """Build the command that initializes the exact-pinned UI submodule."""
    return [
        "git",
        "submodule",
        "update",
        "--init",
        "--recursive",
        "--",
        str(UI_RELATIVE_PATH),
    ]


def install_arguments() -> list[str]:
    """Build the upstream frozen-install command."""
    return ["corepack", "pnpm", "install", "--frozen-lockfile"]


def development_arguments() -> list[str]:
    """Build the loopback-only upstream development-server command."""
    return [
        "corepack",
        "pnpm",
        "exec",
        "next",
        "dev",
        "--hostname",
        "127.0.0.1",
        "--port",
        "3000",
    ]


def ui_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return public local UI configuration without inherited credentials."""
    environment = dict(os.environ if source is None else source)
    for variable in tuple(environment):
        if variable in UI_REMOVED_VARIABLES or variable.startswith(
            UI_SERVER_ONLY_PREFIXES
        ):
            environment.pop(variable)
    environment.update(UI_ENVIRONMENT)
    return environment


def main() -> NoReturn:
    """Initialize, install, and replace this process with upstream Agent Chat UI."""
    root = repository_root()
    ui_directory = root / UI_RELATIVE_PATH
    environment = ui_environment()

    subprocess.run(submodule_arguments(), cwd=root, check=True)
    subprocess.run(
        install_arguments(),
        cwd=ui_directory,
        check=True,
        env=environment,
    )
    os.chdir(ui_directory)
    os.execvpe("corepack", development_arguments(), environment)
