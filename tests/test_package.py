from importlib.metadata import version

import deepagents_lab


def test_package_metadata_matches_module_version() -> None:
    assert deepagents_lab.__version__ == version("deepagents-lab") == "0.1.0"
