"""Integration routes: Slack, email, and webhook configuration."""

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from ..deps import AppSettings, CurrentUser, DbSession
from ..models.integration import Integration
from ..schemas.integration import (
    EmailIntegrationCreate,
    IntegrationListResponse,
    IntegrationRead,
    IntegrationTestResult,
    IntegrationUpdate,
    SlackIntegrationCreate,
    SlackOAuthRequest,
    WebhookIntegrationCreate,
)
from ..services.slack_service import slack_service

router = APIRouter()


@router.get("", response_model=IntegrationListResponse)
async def list_integrations(
    db: DbSession,
    user: CurrentUser,
) -> IntegrationListResponse:
    """List all integrations for the current user."""
    count_q = select(func.count()).where(Integration.user_id == user.id)
    total = (await db.execute(count_q)).scalar() or 0

    query = (
        select(Integration)
        .where(Integration.user_id == user.id)
        .order_by(Integration.created_at.desc())
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return IntegrationListResponse(
        items=[IntegrationRead.model_validate(i) for i in items],
        total=total,
    )


@router.get("/{integration_id}", response_model=IntegrationRead)
async def get_integration(
    integration_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> IntegrationRead:
    """Get a single integration."""
    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.user_id == user.id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    return IntegrationRead.model_validate(integration)


@router.post("/slack", response_model=IntegrationRead, status_code=status.HTTP_201_CREATED)
async def create_slack_integration(
    data: SlackIntegrationCreate,
    db: DbSession,
    user: CurrentUser,
) -> IntegrationRead:
    """Create a Slack integration."""
    integration = Integration(
        user_id=user.id,
        type="slack",
        is_active=data.is_active,
        slack_channel_id=data.slack_channel_id,
        slack_workspace_id=data.slack_workspace_id,
        event_filters=data.event_filters,
        config=data.config,
    )
    db.add(integration)
    await db.flush()
    await db.refresh(integration)
    await db.commit()
    return IntegrationRead.model_validate(integration)


@router.post("/slack/oauth", response_model=IntegrationRead, status_code=status.HTTP_201_CREATED)
async def slack_oauth_callback(
    data: SlackOAuthRequest,
    db: DbSession,
    user: CurrentUser,
) -> IntegrationRead:
    """Complete Slack OAuth flow and create integration."""
    try:
        oauth_response = await slack_service.exchange_code_for_token(
            code=data.code, redirect_uri=data.redirect_uri
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Slack OAuth failed: {exc}",
        )

    incoming_webhook = oauth_response.get("incoming_webhook", {})
    team = oauth_response.get("team", {})

    integration = Integration(
        user_id=user.id,
        type="slack",
        is_active=True,
        slack_channel_id=incoming_webhook.get("channel_id", ""),
        slack_workspace_id=team.get("id"),
        slack_access_token=oauth_response.get("access_token"),
        config={
            "channel_name": incoming_webhook.get("channel"),
            "team_name": team.get("name"),
            "bot_user_id": oauth_response.get("bot_user_id"),
        },
    )
    db.add(integration)
    await db.flush()
    await db.refresh(integration)
    await db.commit()
    return IntegrationRead.model_validate(integration)


@router.post("/email", response_model=IntegrationRead, status_code=status.HTTP_201_CREATED)
async def create_email_integration(
    data: EmailIntegrationCreate,
    db: DbSession,
    user: CurrentUser,
) -> IntegrationRead:
    """Create an email notification integration."""
    integration = Integration(
        user_id=user.id,
        type="email",
        is_active=data.is_active,
        email_address=data.email_address,
        event_filters=data.event_filters,
        config=data.config,
    )
    db.add(integration)
    await db.flush()
    await db.refresh(integration)
    await db.commit()
    return IntegrationRead.model_validate(integration)


@router.post("/webhook", response_model=IntegrationRead, status_code=status.HTTP_201_CREATED)
async def create_webhook_integration(
    data: WebhookIntegrationCreate,
    db: DbSession,
    user: CurrentUser,
) -> IntegrationRead:
    """Create a webhook integration."""
    import secrets

    integration = Integration(
        user_id=user.id,
        type="webhook",
        is_active=data.is_active,
        webhook_url=data.webhook_url,
        webhook_secret=secrets.token_hex(32),
        event_filters=data.event_filters,
        config=data.config,
    )
    db.add(integration)
    await db.flush()
    await db.refresh(integration)
    await db.commit()
    return IntegrationRead.model_validate(integration)


@router.patch("/{integration_id}", response_model=IntegrationRead)
async def update_integration(
    integration_id: uuid.UUID,
    data: IntegrationUpdate,
    db: DbSession,
    user: CurrentUser,
) -> IntegrationRead:
    """Update an integration."""
    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.user_id == user.id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(integration, field, value)

    await db.flush()
    await db.refresh(integration)
    await db.commit()
    return IntegrationRead.model_validate(integration)


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_integration(
    integration_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> None:
    """Delete an integration."""
    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.user_id == user.id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )
    await db.delete(integration)
    await db.commit()


@router.post("/{integration_id}/test", response_model=IntegrationTestResult)
async def test_integration(
    integration_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> IntegrationTestResult:
    """Send a test notification through the integration."""
    result = await db.execute(
        select(Integration).where(
            Integration.id == integration_id,
            Integration.user_id == user.id,
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found",
        )

    try:
        if integration.type == "slack":
            await slack_service.send_message(
                channel=integration.slack_channel_id,
                text="Scout AI test notification - your integration is working!",
                token=integration.slack_access_token,
            )
            return IntegrationTestResult(
                success=True, message="Test message sent to Slack"
            )

        elif integration.type == "email":
            from ..services.email_service import EmailService
            await EmailService.send_email(
                to=integration.email_address,
                subject="Scout AI - Test Notification",
                html="<p>Your email integration is working correctly.</p>",
            )
            return IntegrationTestResult(
                success=True, message="Test email sent"
            )

        elif integration.type == "webhook":
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    integration.webhook_url,
                    json={
                        "event": "test",
                        "message": "Scout AI webhook test",
                    },
                    headers={"X-Scout-Signature": integration.webhook_secret or ""},
                    timeout=10.0,
                )
                if resp.status_code < 400:
                    return IntegrationTestResult(
                        success=True,
                        message=f"Webhook responded with status {resp.status_code}",
                    )
                return IntegrationTestResult(
                    success=False,
                    message=f"Webhook returned status {resp.status_code}",
                )

        return IntegrationTestResult(
            success=False, message=f"Unknown integration type: {integration.type}"
        )
    except Exception as exc:
        return IntegrationTestResult(success=False, message=str(exc))
