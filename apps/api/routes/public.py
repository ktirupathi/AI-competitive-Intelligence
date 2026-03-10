"""Public routes: shared insight pages and exports."""

import secrets
import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from ..deps import CurrentUser, DbSession
from ..models.insight import Insight
from ..models.competitor import Competitor
from ..schemas.export import ExportRequest, PublicInsightRead

router = APIRouter()


@router.get("/insight/{public_token}", response_model=PublicInsightRead)
async def get_public_insight(
    public_token: str,
    db: DbSession,
) -> PublicInsightRead:
    """Get a publicly shared insight by its token. No auth required."""
    result = await db.execute(
        select(Insight).where(
            Insight.public_token == public_token,
            Insight.is_public.is_(True),
        )
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found or not publicly shared",
        )
    return PublicInsightRead.model_validate(insight)


@router.post("/insights/{insight_id}/share", status_code=status.HTTP_200_OK)
async def share_insight(
    insight_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> dict[str, str]:
    """Make an insight publicly shareable and return its public URL."""
    # Verify the insight belongs to one of the user's competitors
    comp_ids_q = select(Competitor.id).where(Competitor.user_id == user.id)
    comp_result = await db.execute(comp_ids_q)
    comp_ids = [row[0] for row in comp_result.all()]

    result = await db.execute(
        select(Insight).where(
            Insight.id == insight_id,
            Insight.competitor_id.in_(comp_ids),
        )
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        )

    if not insight.public_token:
        insight.public_token = secrets.token_urlsafe(32)
    insight.is_public = True
    await db.commit()

    return {
        "public_token": insight.public_token,
        "public_url": f"/insight/{insight.public_token}",
    }


@router.post("/insights/{insight_id}/unshare", status_code=status.HTTP_200_OK)
async def unshare_insight(
    insight_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> dict[str, str]:
    """Remove public sharing from an insight."""
    comp_ids_q = select(Competitor.id).where(Competitor.user_id == user.id)
    comp_result = await db.execute(comp_ids_q)
    comp_ids = [row[0] for row in comp_result.all()]

    result = await db.execute(
        select(Insight).where(
            Insight.id == insight_id,
            Insight.competitor_id.in_(comp_ids),
        )
    )
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insight not found",
        )

    insight.is_public = False
    await db.commit()
    return {"status": "unshared"}


@router.post("/export")
async def export_report(
    data: ExportRequest,
    db: DbSession,
    user: CurrentUser,
) -> dict:
    """Export a report in the requested format.

    Returns the generated content or a download URL.
    """
    from ..models.briefing import Briefing

    if data.briefing_id:
        result = await db.execute(
            select(Briefing).where(
                Briefing.id == data.briefing_id,
                Briefing.user_id == user.id,
            )
        )
        briefing = result.scalar_one_or_none()
        if not briefing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Briefing not found",
            )

        content = briefing.full_content or briefing.executive_summary or ""

        if data.format == "markdown":
            return {
                "format": "markdown",
                "content": content,
                "filename": f"briefing-{briefing.id}.md",
            }
        elif data.format == "pdf":
            # PDF generation would use a library like weasyprint or reportlab
            return {
                "format": "pdf",
                "status": "generating",
                "message": "PDF export will be available via email shortly.",
            }
        elif data.format == "notion":
            return {
                "format": "notion",
                "content": content,
                "message": "Copy this markdown content into Notion.",
            }

    return {"error": "No briefing_id or competitor_id provided"}
