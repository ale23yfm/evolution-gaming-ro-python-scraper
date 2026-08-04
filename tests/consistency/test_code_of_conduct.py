"""Consistency tests for CODE_OF_CONDUCT.md.

These assert the Code of Conduct stays a full Contributor Covenant 2.1
document and keeps the Asociația Oportunități și Cariere specifics
(values, reporting channel).
"""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
CODE_OF_CONDUCT_PATH = ROOT / "CODE_OF_CONDUCT.md"

REQUIRED_SECTIONS = [
    "## Our Pledge",
    "## Our Standards",
    "## Scope",
    "## Enforcement Responsibilities",
    "## Enforcement",
    "## Attribution",
]

ENFORCEMENT_STEPS = [
    "1. **Correction**",
    "2. **Warning**",
    "3. **Temporary Ban**",
    "4. **Permanent Ban**",
]

VALUES = ["Transparency", "Collaboration", "Accessibility", "Innovation"]


def _code_of_conduct() -> str:
    return CODE_OF_CONDUCT_PATH.read_text(encoding="utf-8")


def test_code_of_conduct_required_sections():
    coc = _code_of_conduct()
    missing = [s for s in REQUIRED_SECTIONS if s not in coc]
    assert not missing, f"CODE_OF_CONDUCT.md missing required sections: {missing}"


def test_code_of_conduct_full_enforcement_procedure():
    coc = _code_of_conduct()
    missing = [s for s in ENFORCEMENT_STEPS if s not in coc]
    assert not missing, f"CODE_OF_CONDUCT.md missing enforcement steps: {missing}"


def test_code_of_conduct_has_association_values():
    coc = _code_of_conduct()
    missing = [v for v in VALUES if v not in coc]
    assert not missing, f"CODE_OF_CONDUCT.md missing association values: {missing}"


def test_code_of_conduct_reporting_channel():
    coc = _code_of_conduct()
    assert "aocpeviitor@gmail.com" in coc, "CODE_OF_CONDUCT.md must list the reporting email"
    assert "https://discord.gg/KPMkdUfQNu" in coc, "CODE_OF_CONDUCT.md must list the Discord community"


def test_code_of_conduct_attribution():
    coc = _code_of_conduct()
    assert "Contributor Covenant" in coc, "CODE_OF_CONDUCT.md must credit the Contributor Covenant"
    assert "version 2.1" in coc, "CODE_OF_CONDUCT.md must state the adapted version"
