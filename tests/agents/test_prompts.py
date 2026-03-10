"""Tests for prompt versioning."""

from __future__ import annotations

import pytest

from agents.prompts import (
    PROMPT_VERSIONS,
    PromptVersion,
    get_prompt,
    list_prompt_versions,
)


class TestPromptVersionRegistry:
    """Tests for the PROMPT_VERSIONS registry."""

    def test_all_prompts_registered(self) -> None:
        expected = {
            "change_classification",
            "news_analysis",
            "job_analysis",
            "review_analysis",
            "social_classification",
            "synthesis",
        }
        assert set(PROMPT_VERSIONS.keys()) == expected

    def test_all_versions_are_semver(self) -> None:
        import re
        semver = re.compile(r"^\d+\.\d+\.\d+$")
        for name, pv in PROMPT_VERSIONS.items():
            assert semver.match(pv.version), f"{name} has invalid version: {pv.version}"

    def test_all_prompts_have_system_and_user(self) -> None:
        for name, pv in PROMPT_VERSIONS.items():
            assert pv.system, f"{name} has empty system prompt"
            assert pv.user, f"{name} has empty user prompt"

    def test_prompt_version_is_frozen(self) -> None:
        pv = PROMPT_VERSIONS["synthesis"]
        with pytest.raises(AttributeError):
            pv.version = "2.0.0"  # type: ignore[misc]

    def test_get_prompt_returns_correct_version(self) -> None:
        pv = get_prompt("news_analysis")
        assert isinstance(pv, PromptVersion)
        assert pv.name == "news_analysis"

    def test_get_prompt_raises_on_unknown(self) -> None:
        with pytest.raises(KeyError):
            get_prompt("nonexistent_prompt")

    def test_list_prompt_versions(self) -> None:
        versions = list_prompt_versions()
        assert isinstance(versions, dict)
        assert all(isinstance(v, str) for v in versions.values())
        assert "synthesis" in versions
