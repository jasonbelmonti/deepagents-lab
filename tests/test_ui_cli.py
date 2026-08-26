from __future__ import annotations

from pathlib import Path

import pytest

from deepagents_lab import ui_cli


class ExecCalled(RuntimeError):
    """Signal that the test double received the process replacement."""


def test_ui_commands_pin_supported_local_operation() -> None:
    assert ui_cli.submodule_arguments() == [
        "git",
        "submodule",
        "update",
        "--init",
        "--recursive",
        "--",
        "apps/agent-chat-ui",
    ]
    assert ui_cli.install_arguments() == [
        "corepack",
        "pnpm",
        "install",
        "--frozen-lockfile",
    ]
    assert ui_cli.development_arguments() == [
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


def test_ui_environment_keeps_public_defaults_and_removes_credentials() -> None:
    environment = ui_cli.ui_environment(
        {
            "PATH": "/usr/bin",
            "OPENAI_API_KEY": "provider-secret",
            "OPENAI_BASE_URL": "https://provider.example",
            "LANGSMITH_API_KEY": "langsmith-secret",
            "LANGSMITH_TRACING": "true",
            "LANGSMITH_PROJECT": "server-project",
            "LANGSMITH_ENDPOINT": "https://langsmith.example",
            "LANGCHAIN_API_KEY": "legacy-langsmith-secret",
            "LANGCHAIN_TRACING_V2": "true",
            "LANGCHAIN_PROJECT": "legacy-server-project",
            "LANGGRAPH_API_URL": "https://remote.example",
            "NEXT_PUBLIC_AUTH_SCHEME": "langsmith-api-key",
            "NEXT_PUBLIC_API_URL": "https://override.example",
            "NEXT_PUBLIC_ASSISTANT_ID": "override-agent",
            "CODEX_CI": "1",
            "CODEX_THREAD_ID": "thread-secret",
        }
    )

    assert environment == {
        "PATH": "/usr/bin",
        "NEXT_PUBLIC_API_URL": "http://127.0.0.1:2024",
        "NEXT_PUBLIC_ASSISTANT_ID": "deepagents_lab",
    }


def test_main_initializes_installs_and_runs_upstream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path("/tmp/deepagents-lab")
    environment = {"PATH": "/usr/bin", **ui_cli.UI_ENVIRONMENT}
    runs: list[tuple[list[str], Path, bool, dict[str, str] | None]] = []
    changed_directories: list[Path] = []
    executions: list[tuple[str, list[str], dict[str, str]]] = []

    monkeypatch.setattr(ui_cli, "repository_root", lambda: root)
    monkeypatch.setattr(ui_cli, "ui_environment", lambda: environment)

    def run(
        arguments: list[str],
        *,
        cwd: Path,
        check: bool,
        env: dict[str, str] | None = None,
    ) -> None:
        runs.append((arguments, cwd, check, env))

    def execvpe(
        executable: str,
        arguments: list[str],
        child_environment: dict[str, str],
    ) -> None:
        executions.append((executable, arguments, child_environment))
        raise ExecCalled

    monkeypatch.setattr(ui_cli.subprocess, "run", run)
    monkeypatch.setattr(ui_cli.os, "chdir", changed_directories.append)
    monkeypatch.setattr(ui_cli.os, "execvpe", execvpe)

    with pytest.raises(ExecCalled):
        ui_cli.main()

    ui_directory = root / "apps" / "agent-chat-ui"
    assert runs == [
        (ui_cli.submodule_arguments(), root, True, None),
        (ui_cli.install_arguments(), ui_directory, True, environment),
    ]
    assert changed_directories == [ui_directory]
    assert executions == [
        ("corepack", ui_cli.development_arguments(), environment)
    ]
