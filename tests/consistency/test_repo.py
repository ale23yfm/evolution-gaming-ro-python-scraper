"""Consistency tests: repo identity, root files, workflow naming, version.

These run everywhere and assert the repo matches the Python template
conventions (equivalent of the template consistency job in the Node.js
workflows).
"""

import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]

EXPECTED_ROOT_FILES = [
    ".gitignore",
    "CHANGELOG.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "pytest.ini",
    "requirements.txt",
]

REQUIRED_AI_DOCS = [
    "AGENTS.md",
    "INSTRUCTIONS.md",
    "VERIFY.md",
    "MAINTENANCE.md",
    "JOB_MODEL.md",
    "COMPANY_MODEL.md",
]


def test_required_root_files_exist():
    missing = [f for f in EXPECTED_ROOT_FILES if not (ROOT / f).exists()]
    assert not missing, f"Missing root files: {missing}"


def test_ai_docs_exist():
    ai_dir = ROOT / "ai"
    missing = [f for f in REQUIRED_AI_DOCS if not (ai_dir / f).exists()]
    assert not missing, f"Missing ai docs: {missing}"


def test_workflow_naming():
    wf = ROOT / ".github" / "workflows"
    if not wf.exists():
        import pytest
        pytest.skip("no workflows yet")
    required = ["job-seeker-ro-spider.yml", "automation-testing.yml"]
    missing = [f for f in required if not (wf / f).exists()]
    assert not missing, f"Missing workflows: {missing}"


def test_repo_identity_in_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "e-infra" in readme.lower()
    assert "peviitor" in readme.lower()


def test_repo_identity_in_config(company_config):
    assert company_config["company"]


def test_changelog_has_current_version():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "[1.0.0]" in changelog


def test_gitignore_excludes_python_artifacts():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in ("__pycache__", ".pytest_cache", "*.py[cod]"):
        assert pattern in gitignore, f".gitignore missing pattern: {pattern}"
