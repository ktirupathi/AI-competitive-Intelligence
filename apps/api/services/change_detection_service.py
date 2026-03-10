"""Change detection service for comparing website snapshots.

Uses diff-based comparison and LLM classification to identify meaningful
changes between website crawls.
"""

import difflib
import json
import logging
from typing import Any

import anthropic

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ChangeDetectionService:
    """Detect and classify changes between website snapshots."""

    def __init__(self) -> None:
        self.anthropic_client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key
        )

    @staticmethod
    def detect_changes(old_content: str, new_content: str) -> dict[str, Any]:
        """Compare two content snapshots and return structured diff information.

        Returns a dict with:
            - has_changes: bool
            - similarity_ratio: float (0-1)
            - additions: list of added lines
            - deletions: list of removed lines
            - diff_text: unified diff string (truncated)
        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        ratio = matcher.ratio()

        diff = list(
            difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile="previous",
                tofile="current",
                lineterm="",
            )
        )

        additions = [
            line[1:].strip() for line in diff if line.startswith("+") and not line.startswith("+++")
        ]
        deletions = [
            line[1:].strip() for line in diff if line.startswith("-") and not line.startswith("---")
        ]

        # Truncate diff for storage
        diff_text = "\n".join(diff[:200])

        return {
            "has_changes": ratio < 0.99,
            "similarity_ratio": ratio,
            "additions": additions[:50],
            "deletions": deletions[:50],
            "diff_text": diff_text[:10000],
        }

    async def classify_change_with_llm(
        self,
        competitor_name: str,
        page_url: str,
        old_content: str,
        new_content: str,
        diff_summary: str | None = None,
    ) -> dict[str, Any]:
        """Use Claude to classify the significance and type of a content change.

        Returns a dict with:
            - change_type: str (pricing|features|messaging|team|partnerships|legal|other)
            - severity: str (low|medium|high|critical)
            - significance_score: float (0.0-1.0)
            - title: str
            - summary: str
            - reasoning: str
        """
        # Auto-generate diff summary if not provided
        if not diff_summary:
            diff_info = self.detect_changes(old_content, new_content)
            diff_summary = diff_info["diff_text"][:3000]

        prompt = (
            f"Analyze this website content change for competitive intelligence.\n\n"
            f"Competitor: {competitor_name}\n"
            f"Page: {page_url}\n\n"
            f"--- PREVIOUS CONTENT (truncated) ---\n{old_content[:2500]}\n\n"
            f"--- CURRENT CONTENT (truncated) ---\n{new_content[:2500]}\n\n"
            f"--- DIFF ---\n{diff_summary[:2000]}\n\n"
            "Respond with ONLY valid JSON (no markdown fences):\n"
            "{\n"
            '  "change_type": "pricing | features | messaging | team | partnerships | legal | other",\n'
            '  "severity": "low | medium | high | critical",\n'
            '  "significance_score": 0.0 to 1.0,\n'
            '  "title": "Brief title (max 100 chars)",\n'
            '  "summary": "1-2 sentence description of what changed and why it matters",\n'
            '  "reasoning": "Why you assigned this severity level"\n'
            "}\n\n"
            "Severity guide:\n"
            "- low: cosmetic, typo fixes, minor copy tweaks\n"
            "- medium: notable messaging shift, new testimonial, minor feature mention\n"
            "- high: new pricing tier, major feature launch, key hire announcement\n"
            "- critical: acquisition news, pivot announcement, major strategic shift"
        )

        try:
            response = await self.anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                lines = raw.split("\n")
                lines = [ln for ln in lines if not ln.strip().startswith("```")]
                raw = "\n".join(lines)
            return json.loads(raw)
        except (json.JSONDecodeError, IndexError, anthropic.APIError) as exc:
            logger.error("LLM change classification failed for %s: %s", page_url, exc)
            return {
                "change_type": "other",
                "severity": "medium",
                "significance_score": 0.5,
                "title": "Content change detected",
                "summary": "Automated classification unavailable",
                "reasoning": f"Classification error: {exc}",
            }
