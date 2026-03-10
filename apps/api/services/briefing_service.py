"""Service layer for briefing generation and retrieval."""

import logging
import uuid
from datetime import datetime, timedelta, timezone

import anthropic
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models.briefing import Briefing
from ..models.change import Change
from ..models.competitor import Competitor
from ..models.insight import Insight
from ..models.news import NewsItem
from ..models.user import User

logger = logging.getLogger(__name__)
settings = get_settings()


class BriefingService:
    """Handles briefing generation and retrieval."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.anthropic_client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key
        )

    async def list_briefings(
        self,
        user_id: uuid.UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Briefing], int]:
        """List briefings for a user with pagination."""
        count_q = select(func.count()).where(Briefing.user_id == user_id)
        total = (await self.db.execute(count_q)).scalar() or 0

        query = (
            select(Briefing)
            .where(Briefing.user_id == user_id)
            .order_by(Briefing.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_briefing(
        self, briefing_id: uuid.UUID, user_id: uuid.UUID
    ) -> Briefing | None:
        """Get a single briefing by ID."""
        query = select(Briefing).where(
            Briefing.id == briefing_id,
            Briefing.user_id == user_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def generate_briefing(
        self,
        user: User,
        competitor_ids: list[uuid.UUID] | None = None,
        frequency: str = "weekly",
    ) -> Briefing:
        """Generate a competitive intelligence briefing using Claude."""
        period_days = {"daily": 1, "weekly": 7, "monthly": 30}.get(frequency, 7)
        period_start = datetime.now(timezone.utc) - timedelta(days=period_days)
        period_end = datetime.now(timezone.utc)

        # Fetch competitors
        comp_query = select(Competitor).where(Competitor.user_id == user.id)
        if competitor_ids:
            comp_query = comp_query.where(Competitor.id.in_(competitor_ids))
        competitors = list((await self.db.execute(comp_query)).scalars().all())

        if not competitors:
            raise ValueError("No competitors found to generate briefing for.")

        comp_ids = [c.id for c in competitors]

        # Gather recent changes
        changes = list(
            (
                await self.db.execute(
                    select(Change)
                    .where(
                        Change.competitor_id.in_(comp_ids),
                        Change.detected_at >= period_start,
                    )
                    .order_by(Change.significance_score.desc())
                    .limit(50)
                )
            )
            .scalars()
            .all()
        )

        # Gather recent insights
        insights = list(
            (
                await self.db.execute(
                    select(Insight)
                    .where(
                        Insight.competitor_id.in_(comp_ids),
                        Insight.created_at >= period_start,
                    )
                    .order_by(Insight.confidence.desc())
                    .limit(30)
                )
            )
            .scalars()
            .all()
        )

        # Gather recent news
        news_items = list(
            (
                await self.db.execute(
                    select(NewsItem)
                    .where(
                        NewsItem.competitor_id.in_(comp_ids),
                        NewsItem.discovered_at >= period_start,
                    )
                    .order_by(NewsItem.relevance_score.desc())
                    .limit(30)
                )
            )
            .scalars()
            .all()
        )

        # Build context for LLM
        context = self._build_briefing_context(
            competitors, changes, insights, news_items, frequency
        )

        # Generate with Claude
        executive_summary, full_content, sections = await self._call_llm(context)

        # Create briefing record
        briefing = Briefing(
            user_id=user.id,
            title=f"{frequency.capitalize()} Competitive Intelligence Briefing",
            frequency=frequency,
            executive_summary=executive_summary,
            full_content=full_content,
            sections=sections,
            period_start=period_start,
            period_end=period_end,
            status="generated",
            competitor_count=len(competitors),
            insight_count=len(insights),
            change_count=len(changes),
        )
        self.db.add(briefing)
        await self.db.flush()
        await self.db.refresh(briefing)

        logger.info("Generated briefing %s for user %s", briefing.id, user.id)
        return briefing

    def _build_briefing_context(
        self,
        competitors: list[Competitor],
        changes: list[Change],
        insights: list[Insight],
        news_items: list[NewsItem],
        frequency: str,
    ) -> str:
        """Build structured context string for the LLM prompt."""
        parts = [
            f"Generate a {frequency} competitive intelligence briefing.\n",
            "## Competitors Monitored",
        ]
        for c in competitors:
            parts.append(f"- {c.name} ({c.domain}): {c.description or 'N/A'}")

        parts.append("\n## Key Changes Detected")
        if changes:
            for ch in changes[:20]:
                parts.append(
                    f"- [{ch.severity.upper()}] {ch.title} "
                    f"(type: {ch.change_type}, score: {ch.significance_score:.2f})"
                )
                if ch.summary:
                    parts.append(f"  Summary: {ch.summary}")
        else:
            parts.append("- No significant changes detected this period.")

        parts.append("\n## AI Insights")
        if insights:
            for ins in insights[:15]:
                parts.append(
                    f"- [{ins.category}] {ins.title} "
                    f"(severity: {ins.severity}, confidence: {ins.confidence:.0%})"
                )
                parts.append(f"  {ins.summary}")
        else:
            parts.append("- No new insights this period.")

        parts.append("\n## News & Press")
        if news_items:
            for n in news_items[:15]:
                parts.append(
                    f"- {n.title} (source: {n.source or 'unknown'}, "
                    f"sentiment: {n.sentiment or 'unknown'})"
                )
        else:
            parts.append("- No relevant news this period.")

        return "\n".join(parts)

    async def _call_llm(self, context: str) -> tuple[str, str, dict]:
        """Call Claude to generate the briefing content."""
        system_prompt = (
            "You are Scout AI, an expert competitive intelligence analyst. "
            "Generate a well-structured briefing from the provided data. "
            "Return your response in the following format:\n\n"
            "## Executive Summary\n(2-3 paragraph high-level summary)\n\n"
            "## Key Findings\n(Bulleted key findings)\n\n"
            "## Competitor-by-Competitor Analysis\n(Section per competitor)\n\n"
            "## Strategic Recommendations\n(Actionable recommendations)\n\n"
            "## Outlook\n(What to watch for next period)\n\n"
            "Be concise, data-driven, and actionable."
        )

        message = await self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": context}],
        )

        full_content = message.content[0].text

        # Extract executive summary (first section)
        executive_summary = ""
        if "## Executive Summary" in full_content:
            parts = full_content.split("## Executive Summary", 1)
            if len(parts) > 1:
                rest = parts[1]
                next_heading = rest.find("\n## ")
                executive_summary = rest[:next_heading].strip() if next_heading > 0 else rest.strip()

        sections = {
            "raw_output": full_content,
            "model": "claude-sonnet-4-20250514",
            "tokens_used": message.usage.input_tokens + message.usage.output_tokens,
        }

        return executive_summary, full_content, sections
