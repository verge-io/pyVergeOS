"""Regression tests for declared runtime dependencies."""

import pathlib
import re

_PYPROJECT = pathlib.Path(__file__).resolve().parents[2] / "pyproject.toml"


def _project_dependencies() -> list[str]:
    """Return requirement strings from the ``[project]`` dependencies table."""
    in_project = False
    in_dependencies = False
    dependencies: list[str] = []

    for line in _PYPROJECT.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_dependencies:
                break
            in_project = stripped == "[project]"
            continue
        if not in_project:
            continue
        if stripped.startswith("dependencies"):
            in_dependencies = True
            continue
        if not in_dependencies:
            continue
        if stripped.startswith("]"):
            break
        match = re.fullmatch(r'"([^"]+)",?', stripped)
        if match:
            dependencies.append(match.group(1))

    return dependencies


def test_urllib3_dependency_floor_is_1_26() -> None:
    """requests>=2.28.0 allows urllib3 1.25, which has no Retry.allowed_methods."""
    urllib3_reqs = [req for req in _project_dependencies() if req.startswith("urllib3")]

    assert urllib3_reqs == ["urllib3>=1.26"]
