"""Conformity tests for the root README.md.

These assert the README stays aligned with the template conventions and
the decisions made for this repo (English content, official company link,
correct license owner, consistent badges).
"""

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
README_PATH = ROOT / "README.md"

REQUIRED_SECTIONS = ["## Overview", "## Features", "## License", "## Managed By", "## Disclaimer"]

ROMANIAN_DIACRITICS = "ăâîșțĂÂÎȘȚ"
ROMANIAN_PHRASES = [
    "un scraper pentru",
    "menținând",
    "despre companie",
    "proiectul automatizează",
    "locuri de muncă",
]


def _readme() -> str:
    return README_PATH.read_text(encoding="utf-8")


def _section(readme: str, title: str) -> str:
    start = readme.index(title)
    rest = readme[start:]
    match = re.search(r"\n## ", rest)
    if match:
        return rest[: match.start()]
    return rest


def test_readme_has_required_sections():
    readme = _readme()
    missing = [s for s in REQUIRED_SECTIONS if s not in readme]
    assert not missing, f"README.md missing required sections: {missing}"


def test_readme_content_is_english():
    readme = _readme()
    diacritics = [ch for ch in ROMANIAN_DIACRITICS if ch in readme]
    assert not diacritics, f"README.md contains Romanian diacritics: {diacritics}"
    found = [p for p in ROMANIAN_PHRASES if p in readme.lower()]
    assert not found, f"README.md contains Romanian phrases: {found}"


def test_readme_company_link_points_to_official_careers():
    readme = _readme()
    assert "https://careers.evolution.com/romania/en/" in readme, "README.md must link the EVOLUTION official careers page"
    assert "electrogrup.applytojob.com" not in readme, "README.md must not link the electrogrup applytojob board"


def test_readme_license_owner():
    readme = _readme()
    license_section = _section(readme, "## License")
    assert "Alexandra Ifrim" in license_section, "License section must credit Alexandra Ifrim"
    assert "MIT" in license_section, "License section must mention the MIT license"


def test_readme_badges_match_repo():
    readme = _readme()
    assert "https://ale23yfm.github.io/evolution-gaming-ro-python-scraper/" in readme, "README.md must link the GitHub Pages site"
    wf = ROOT / ".github" / "workflows" / "job-seeker-ro-spider.yml"
    if not wf.exists():
        pytest.skip("workflow file not present")
    match = re.search(r"^name:\s*(.+)$", wf.read_text(encoding="utf-8"), re.M)
    assert match, "workflow must have a name"
    workflow_name = match.group(1).strip()
    assert f"[![{workflow_name}]" in readme, f"README.md badge label must match workflow name {workflow_name!r}"
