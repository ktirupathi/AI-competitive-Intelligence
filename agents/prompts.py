"""
Scout AI - Claude Prompt Library

All prompts used by the agent pipeline are centralised here so they can be
versioned, tested, and swapped without touching agent logic.

Each prompt pair is registered in ``PROMPT_VERSIONS`` at the bottom of this
file with a semantic version string.  Agents reference the prompt constants
directly; the version registry is used for auditing, A/B testing, and
migration tracking.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptVersion:
    """Immutable descriptor for a versioned prompt pair."""

    name: str
    version: str
    system: str
    user: str
    description: str = ""

# ---------------------------------------------------------------------------
# Change Classification  (used by web_monitor_agent)
# ---------------------------------------------------------------------------

CHANGE_CLASSIFICATION_SYSTEM = """\
You are a competitive-intelligence analyst specialising in SaaS markets.
Your job is to classify website content changes detected on a competitor's site.
Be precise, analytical, and concise."""

CHANGE_CLASSIFICATION_USER = """\
A change was detected on the competitor's website.

Competitor: {competitor_name}
URL: {url}

Previous content (truncated):
---
{previous_content}
---

Current content (truncated):
---
{current_content}
---

Analyse the change and respond with ONLY valid JSON (no markdown fences):
{{
  "diff_summary": "A 1-3 sentence summary of what changed",
  "significance": "low | medium | high | critical",
  "change_category": "pricing | features | messaging | team | partnerships | legal | other",
  "reasoning": "Brief explanation of your significance rating"
}}

Significance guide:
- low: cosmetic, typo fixes, minor copy tweaks
- medium: notable messaging shift, new testimonial, minor feature mention
- high: new pricing tier, major feature launch, key hire announcement
- critical: acquisition news, pivot announcement, major strategic shift"""

# ---------------------------------------------------------------------------
# News Relevance & Sentiment  (used by news_agent)
# ---------------------------------------------------------------------------

NEWS_ANALYSIS_SYSTEM = """\
You are a competitive-intelligence analyst. Evaluate news articles for their
relevance to competitive positioning in the SaaS market. Be objective and
data-driven."""

NEWS_ANALYSIS_USER = """\
Evaluate the following news item about a competitor.

Competitor: {competitor_name}
Watch keywords: {watch_keywords}

Article title: {title}
Source: {source}
Snippet:
---
{snippet}
---

Respond with ONLY valid JSON (no markdown fences):
{{
  "summary": "2-3 sentence summary of the article's significance",
  "relevance_score": <float 0.0-1.0>,
  "sentiment": "positive | negative | neutral",
  "key_topics": ["topic1", "topic2"]
}}

Relevance guide:
- 0.0-0.3: tangential mention, not competitively meaningful
- 0.3-0.6: somewhat relevant, worth noting
- 0.6-0.8: clearly relevant competitive signal
- 0.8-1.0: high-impact competitive event (funding, acquisition, major launch)"""

# ---------------------------------------------------------------------------
# Job Posting Strategic Signal  (used by job_agent)
# ---------------------------------------------------------------------------

JOB_ANALYSIS_SYSTEM = """\
You are a competitive-intelligence analyst who specialises in reading hiring
signals. Job postings reveal a company's strategic direction, investment areas,
and organisational priorities."""

JOB_ANALYSIS_USER = """\
Analyse the following job posting from a competitor.

Competitor: {competitor_name}
Job Title: {title}
Department: {department}
Location: {location}

Job Description (truncated):
---
{description}
---

Respond with ONLY valid JSON (no markdown fences):
{{
  "seniority": "junior | mid | senior | lead | exec",
  "department": "engineering | product | sales | marketing | operations | data | security | design | other",
  "strategic_signal": "1-2 sentence explanation of what this hire signals about the company's direction",
  "technologies_mentioned": ["tech1", "tech2"],
  "urgency_indicators": "low | medium | high"
}}"""

# ---------------------------------------------------------------------------
# Review Sentiment Analysis  (used by review_agent)
# ---------------------------------------------------------------------------

REVIEW_ANALYSIS_SYSTEM = """\
You are a product analyst who extracts structured insights from software
reviews. Focus on recurring themes, competitive strengths and weaknesses."""

REVIEW_ANALYSIS_USER = """\
Analyse the following software review.

Competitor: {competitor_name}
Platform: {platform}
Rating: {rating}/5
Review title: {title}

Review text:
---
{review_text}
---

Respond with ONLY valid JSON (no markdown fences):
{{
  "sentiment": "positive | negative | mixed | neutral",
  "pros_summary": "Brief summary of positives mentioned",
  "cons_summary": "Brief summary of negatives mentioned",
  "key_themes": ["theme1", "theme2"],
  "competitive_relevance": "How this review relates to competitive positioning (1 sentence)"
}}"""

# ---------------------------------------------------------------------------
# Social Post Classification  (used by social_agent)
# ---------------------------------------------------------------------------

SOCIAL_CLASSIFICATION_SYSTEM = """\
You are a social media analyst specialising in B2B SaaS competitive
intelligence. Classify posts and extract strategic signals."""

SOCIAL_CLASSIFICATION_USER = """\
Classify the following social media post from a competitor.

Competitor: {competitor_name}
Platform: {platform}
Author: {author}

Post content:
---
{content}
---

Engagement: {likes} likes, {comments} comments, {shares} shares

Respond with ONLY valid JSON (no markdown fences):
{{
  "post_type": "announcement | hiring | product_launch | thought_leadership | partnership | event | other",
  "summary": "1-2 sentence summary of the post's significance",
  "engagement_score": <float 0.0-1.0 normalised engagement level>,
  "strategic_relevance": "low | medium | high",
  "key_topics": ["topic1", "topic2"]
}}"""

# ---------------------------------------------------------------------------
# Insight Generation / Briefing Synthesis  (used by synthesis_agent)
# ---------------------------------------------------------------------------

SYNTHESIS_SYSTEM = """\
You are the lead competitive-intelligence strategist for a SaaS company.
You synthesise signals from multiple sources — website changes, news articles,
job postings, product reviews, and social media — into a coherent strategic
briefing. You also incorporate signal clusters and predictions from the
analysis pipeline. Your analysis must be:

1. Evidence-based: every insight must reference specific signals
2. Actionable: recommendations should be concrete and prioritised
3. Predictive: identify emerging trends before they become obvious
4. Balanced: acknowledge uncertainty with calibrated confidence scores
5. Cluster-aware: reference signal clusters to strengthen correlations

You always output structured JSON."""

SYNTHESIS_USER = """\
Generate a comprehensive competitive intelligence briefing from the
following signals collected over the monitoring period.

## Website Changes
{changes_json}

## News Items
{news_json}

## Job Postings
{jobs_json}

## Product Reviews
{reviews_json}

## Social Media Posts
{social_json}

## Signal Clusters (correlated patterns)
{clusters_json}

## Predictions (from analysis pipeline)
{predictions_json}

## Competitors Monitored
{competitors_json}

---

Produce a briefing as ONLY valid JSON (no markdown fences) with this exact schema:
{{
  "executive_summary": "3-5 sentence executive overview of the most important developments",
  "top_insights": [
    {{
      "title": "Short insight title",
      "description": "Detailed description with evidence",
      "impact_score": <float 0.0-1.0>,
      "confidence_score": <float 0.0-1.0>,
      "category": "product | pricing | strategy | talent | market | partnerships",
      "sources": ["source reference 1", "source reference 2"]
    }}
  ],
  "predictive_signals": [
    {{
      "signal": "What we predict will happen",
      "confidence": <float 0.0-1.0>,
      "timeframe": "e.g. next 30 days, Q2 2025",
      "evidence": ["supporting evidence 1", "supporting evidence 2"]
    }}
  ],
  "recommended_plays": [
    {{
      "action": "Specific recommended action",
      "rationale": "Why this action matters now",
      "priority": "high | medium | low",
      "effort": "low | medium | high"
    }}
  ],
  "competitor_summaries": [
    {{
      "name": "Competitor name",
      "domain": "competitor.com",
      "key_changes": ["change 1", "change 2"],
      "threat_level": "low | moderate | high | critical"
    }}
  ]
}}

Guidelines:
- Include 3-7 top insights, sorted by impact_score descending
- Include 2-5 predictive signals
- Include 3-7 recommended plays
- One competitor_summary per monitored competitor
- Be specific — avoid generic advice
- Confidence scores should reflect actual evidence strength
- impact_score reflects potential business impact, not just novelty"""

# ---------------------------------------------------------------------------
# Delivery formatting  (used by delivery_agent for Slack blocks)
# ---------------------------------------------------------------------------

BRIEFING_SLACK_FORMAT = """\
:rotating_light: *Scout AI Competitive Intelligence Briefing*
Generated: {generated_at}

*Executive Summary*
{executive_summary}

*Top Insights*
{insights_block}

*Predictive Signals*
{signals_block}

*Recommended Plays*
{plays_block}

_Full briefing delivered via email. Reply in-thread for discussion._"""


# ---------------------------------------------------------------------------
# Prompt Version Registry
# ---------------------------------------------------------------------------
# Every prompt pair is registered here with a semver string.
# Bump the version whenever a prompt is materially changed.

PROMPT_VERSIONS: dict[str, PromptVersion] = {
    "change_classification": PromptVersion(
        name="change_classification",
        version="1.0.0",
        system=CHANGE_CLASSIFICATION_SYSTEM,
        user=CHANGE_CLASSIFICATION_USER,
        description="Classify website content changes by significance and category.",
    ),
    "news_analysis": PromptVersion(
        name="news_analysis",
        version="1.0.0",
        system=NEWS_ANALYSIS_SYSTEM,
        user=NEWS_ANALYSIS_USER,
        description="Evaluate news relevance and sentiment for competitive signals.",
    ),
    "job_analysis": PromptVersion(
        name="job_analysis",
        version="1.0.0",
        system=JOB_ANALYSIS_SYSTEM,
        user=JOB_ANALYSIS_USER,
        description="Extract strategic hiring signals from job postings.",
    ),
    "review_analysis": PromptVersion(
        name="review_analysis",
        version="1.0.0",
        system=REVIEW_ANALYSIS_SYSTEM,
        user=REVIEW_ANALYSIS_USER,
        description="Analyse software reviews for competitive insights.",
    ),
    "social_classification": PromptVersion(
        name="social_classification",
        version="1.0.0",
        system=SOCIAL_CLASSIFICATION_SYSTEM,
        user=SOCIAL_CLASSIFICATION_USER,
        description="Classify social media posts and extract strategic signals.",
    ),
    "synthesis": PromptVersion(
        name="synthesis",
        version="1.0.0",
        system=SYNTHESIS_SYSTEM,
        user=SYNTHESIS_USER,
        description="Generate comprehensive briefing from all collected signals.",
    ),
}


def get_prompt(name: str) -> PromptVersion:
    """Look up a prompt by name. Raises ``KeyError`` if not found."""
    return PROMPT_VERSIONS[name]


def list_prompt_versions() -> dict[str, str]:
    """Return a dict mapping prompt name to version string."""
    return {name: pv.version for name, pv in PROMPT_VERSIONS.items()}
