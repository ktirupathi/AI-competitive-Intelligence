"""
Scout AI - Delivery Agent

Delivers the generated briefing via email (Resend), Slack (Bolt), and/or
generic webhook. Each channel is attempted independently so a failure in one
does not block the others.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx

from agents.config import settings
from agents.prompts import BRIEFING_SLACK_FORMAT
from agents.state import Briefing, DeliveryResult, PipelineState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Email delivery via Resend
# ---------------------------------------------------------------------------


async def _deliver_email(
    briefing: Briefing, recipient: str
) -> DeliveryResult:
    """Send the briefing as a formatted HTML email via the Resend API."""
    now = datetime.now(timezone.utc).isoformat()

    if not settings.resend.api_key:
        return {
            "channel": "email",
            "success": False,
            "message": "Resend API key not configured",
            "delivered_at": now,
        }

    html_body = _briefing_to_html(briefing)

    payload = {
        "from": settings.resend.from_address,
        "to": [recipient],
        "subject": f"Scout AI Briefing — {briefing.get('generated_at', 'now')[:10]}",
        "html": html_body,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.resend.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            logger.info("Email sent to %s (id=%s)", recipient, data.get("id"))
            return {
                "channel": "email",
                "success": True,
                "message": f"Email sent (id={data.get('id')})",
                "delivered_at": now,
            }
    except Exception as exc:
        logger.error("Email delivery failed: %s", exc)
        return {
            "channel": "email",
            "success": False,
            "message": str(exc),
            "delivered_at": now,
        }


def _briefing_to_html(briefing: Briefing) -> str:
    """Convert a briefing dict into a styled HTML email body."""
    insights_rows = ""
    for ins in briefing.get("top_insights", []):
        impact_pct = int(ins["impact_score"] * 100)
        conf_pct = int(ins["confidence_score"] * 100)
        insights_rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;"><strong>{ins['title']}</strong></td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{ins['description']}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;text-align:center;">{impact_pct}%</td>
            <td style="padding:8px;border-bottom:1px solid #eee;text-align:center;">{conf_pct}%</td>
        </tr>"""

    signals_items = ""
    for sig in briefing.get("predictive_signals", []):
        conf_pct = int(sig["confidence"] * 100)
        signals_items += f"<li><strong>{sig['signal']}</strong> ({conf_pct}% confidence, {sig['timeframe']})</li>"

    plays_items = ""
    for play in briefing.get("recommended_plays", []):
        priority_color = {"high": "#e74c3c", "medium": "#f39c12", "low": "#27ae60"}.get(
            play["priority"], "#999"
        )
        plays_items += (
            f'<li><span style="color:{priority_color};font-weight:bold;">'
            f'[{play["priority"].upper()}]</span> '
            f'<strong>{play["action"]}</strong> — {play["rationale"]} '
            f'(Effort: {play["effort"]})</li>'
        )

    competitor_rows = ""
    for cs in briefing.get("competitor_summaries", []):
        changes = ", ".join(cs["key_changes"]) if cs["key_changes"] else "No notable changes"
        competitor_rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #eee;"><strong>{cs['name']}</strong></td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{cs['domain']}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{changes}</td>
            <td style="padding:8px;border-bottom:1px solid #eee;">{cs['threat_level'].upper()}</td>
        </tr>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:800px;margin:0 auto;padding:20px;color:#333;">
        <div style="background:#1a1a2e;color:white;padding:24px;border-radius:8px 8px 0 0;">
            <h1 style="margin:0;font-size:24px;">Scout AI Competitive Intelligence Briefing</h1>
            <p style="margin:8px 0 0;opacity:0.8;">Generated: {briefing.get('generated_at', 'N/A')}</p>
        </div>

        <div style="padding:24px;background:#f9f9fb;border-radius:0 0 8px 8px;">
            <h2 style="color:#1a1a2e;">Executive Summary</h2>
            <p style="line-height:1.6;">{briefing.get('executive_summary', '')}</p>

            <h2 style="color:#1a1a2e;">Top Insights</h2>
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="background:#eee;">
                        <th style="padding:8px;text-align:left;">Insight</th>
                        <th style="padding:8px;text-align:left;">Details</th>
                        <th style="padding:8px;text-align:center;">Impact</th>
                        <th style="padding:8px;text-align:center;">Confidence</th>
                    </tr>
                </thead>
                <tbody>{insights_rows}</tbody>
            </table>

            <h2 style="color:#1a1a2e;">Predictive Signals</h2>
            <ul style="line-height:1.8;">{signals_items or '<li>No predictive signals generated</li>'}</ul>

            <h2 style="color:#1a1a2e;">Recommended Plays</h2>
            <ul style="line-height:1.8;">{plays_items or '<li>No recommendations generated</li>'}</ul>

            <h2 style="color:#1a1a2e;">Competitor Overview</h2>
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="background:#eee;">
                        <th style="padding:8px;text-align:left;">Name</th>
                        <th style="padding:8px;text-align:left;">Domain</th>
                        <th style="padding:8px;text-align:left;">Key Changes</th>
                        <th style="padding:8px;text-align:left;">Threat</th>
                    </tr>
                </thead>
                <tbody>{competitor_rows}</tbody>
            </table>

            <hr style="margin:24px 0;border:none;border-top:1px solid #ddd;">
            <p style="font-size:12px;color:#999;text-align:center;">
                Generated by Scout AI &middot; Competitive Intelligence Platform
            </p>
        </div>
    </body>
    </html>
    """


# ---------------------------------------------------------------------------
# Slack delivery via Slack Bolt / Web API
# ---------------------------------------------------------------------------


async def _deliver_slack(
    briefing: Briefing, channel: str
) -> DeliveryResult:
    """Post the briefing summary to a Slack channel via the Web API."""
    now = datetime.now(timezone.utc).isoformat()

    if not settings.slack.bot_token:
        return {
            "channel": "slack",
            "success": False,
            "message": "Slack bot token not configured",
            "delivered_at": now,
        }

    # Build readable Slack message
    insights_block = ""
    for i, ins in enumerate(briefing.get("top_insights", [])[:5], 1):
        impact_pct = int(ins["impact_score"] * 100)
        insights_block += f"{i}. *{ins['title']}* (Impact: {impact_pct}%)\n   {ins['description'][:120]}\n"

    signals_block = ""
    for sig in briefing.get("predictive_signals", [])[:3]:
        conf_pct = int(sig["confidence"] * 100)
        signals_block += f"- {sig['signal']} ({conf_pct}% confidence, {sig['timeframe']})\n"

    plays_block = ""
    for play in briefing.get("recommended_plays", [])[:5]:
        emoji = {"high": ":red_circle:", "medium": ":large_orange_circle:", "low": ":large_green_circle:"}.get(
            play["priority"], ":white_circle:"
        )
        plays_block += f"{emoji} *{play['action']}* — {play['rationale'][:100]}\n"

    text = BRIEFING_SLACK_FORMAT.format(
        generated_at=briefing.get("generated_at", "now"),
        executive_summary=briefing.get("executive_summary", "N/A"),
        insights_block=insights_block or "_No insights_",
        signals_block=signals_block or "_No signals_",
        plays_block=plays_block or "_No plays_",
    )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://slack.com/api/chat.postMessage",
                json={
                    "channel": channel,
                    "text": text,
                    "mrkdwn": True,
                },
                headers={
                    "Authorization": f"Bearer {settings.slack.bot_token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                timeout=10,
            )
            data = resp.json()
            if data.get("ok"):
                logger.info("Slack message posted to %s (ts=%s)", channel, data.get("ts"))
                return {
                    "channel": "slack",
                    "success": True,
                    "message": f"Posted to {channel} (ts={data.get('ts')})",
                    "delivered_at": now,
                }
            else:
                error = data.get("error", "unknown")
                logger.error("Slack API error: %s", error)
                return {
                    "channel": "slack",
                    "success": False,
                    "message": f"Slack API error: {error}",
                    "delivered_at": now,
                }
    except Exception as exc:
        logger.error("Slack delivery failed: %s", exc)
        return {
            "channel": "slack",
            "success": False,
            "message": str(exc),
            "delivered_at": now,
        }


# ---------------------------------------------------------------------------
# Webhook delivery
# ---------------------------------------------------------------------------


async def _deliver_webhook(
    briefing: Briefing, webhook_url: str
) -> DeliveryResult:
    """POST the full briefing JSON to a configured webhook endpoint."""
    now = datetime.now(timezone.utc).isoformat()

    if not webhook_url:
        return {
            "channel": "webhook",
            "success": False,
            "message": "Webhook URL not configured",
            "delivered_at": now,
        }

    payload = json.dumps(briefing, default=str).encode("utf-8")
    headers: Dict[str, str] = {"Content-Type": "application/json"}

    # Sign payload if a secret is configured
    if settings.webhook.secret:
        signature = hmac.new(
            settings.webhook.secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        headers["X-Scout-Signature"] = f"sha256={signature}"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                webhook_url,
                content=payload,
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            logger.info("Webhook delivered to %s (status=%d)", webhook_url, resp.status_code)
            return {
                "channel": "webhook",
                "success": True,
                "message": f"Delivered (HTTP {resp.status_code})",
                "delivered_at": now,
            }
    except Exception as exc:
        logger.error("Webhook delivery failed: %s", exc)
        return {
            "channel": "webhook",
            "success": False,
            "message": str(exc),
            "delivered_at": now,
        }


# ---------------------------------------------------------------------------
# Core agent function
# ---------------------------------------------------------------------------


async def delivery_agent(state: PipelineState) -> PipelineState:
    """
    LangGraph node: deliver the briefing via all configured channels.

    Reads:
        state["briefing"], state["user_email"], state["slack_channel"],
        state["webhook_url"]
    Writes:
        state["delivery_results"]
    """
    briefing = state.get("briefing")
    errors: List[Dict[str, Any]] = list(state.get("errors", []))

    if not briefing:
        logger.warning("No briefing to deliver")
        return {
            "delivery_results": [],
            "errors": errors,
        }

    results: List[DeliveryResult] = []

    # --- Email ---
    user_email = state.get("user_email")
    if user_email:
        result = await _deliver_email(briefing, user_email)
        results.append(result)
    else:
        logger.info("No user_email configured — skipping email delivery")

    # --- Slack ---
    slack_channel = state.get("slack_channel") or settings.slack.default_channel
    if settings.slack.bot_token:
        result = await _deliver_slack(briefing, slack_channel)
        results.append(result)
    else:
        logger.info("Slack not configured — skipping Slack delivery")

    # --- Webhook ---
    webhook_url = state.get("webhook_url") or (settings.webhook.url or "")
    if webhook_url:
        result = await _deliver_webhook(briefing, webhook_url)
        results.append(result)
    else:
        logger.info("No webhook URL configured — skipping webhook delivery")

    # Log summary
    success_count = sum(1 for r in results if r["success"])
    logger.info(
        "Delivery complete: %d/%d channels successful", success_count, len(results)
    )

    return {
        "delivery_results": results,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "errors": errors,
    }
