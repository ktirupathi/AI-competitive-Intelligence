"use client";

import Link from "next/link";
import {
  ArrowLeft,
  Calendar,
  FileText,
  Users,
  AlertTriangle,
  Target,
  Lightbulb,
  TrendingUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { InsightCard } from "@/components/insight-card";
import { getImpactColor, getStatusColor, formatDate } from "@/lib/utils";
import type {
  BriefingDetail,
  Insight,
  PredictiveSignal,
  RecommendedPlay,
} from "@/lib/types";

const mockBriefing: BriefingDetail = {
  id: "br-1",
  title: "Weekly Intelligence Briefing #12",
  weekStart: "2026-03-02",
  weekEnd: "2026-03-08",
  status: "delivered",
  executiveSummary:
    "This was a high-activity week across your competitive landscape. The most significant development was Acme Corp's launch of a new enterprise AI tier at $999/month, which directly competes with your Professional plan. TechRival closed a $50M Series C led by Sequoia, signaling aggressive expansion plans. CompetitorX posted 15 new roles in European offices, indicating imminent market entry in the EU. Overall competitive pressure is increasing, particularly in the enterprise AI space. We recommend prioritizing your own AI feature rollout and monitoring Acme Corp's enterprise market traction closely.",
  insightsCount: 12,
  competitorsAnalyzed: 7,
  createdAt: "2026-03-09T08:00:00Z",
  insights: [
    {
      id: "ins-1",
      briefingId: "br-1",
      competitorId: "comp-1",
      competitorName: "Acme Corp",
      title: "New Enterprise Tier with AI-Powered Features ($999/mo)",
      description:
        "Acme Corp launched a new enterprise pricing tier at $999/month featuring AI-powered analytics, custom integrations, and dedicated support. This directly competes with your Professional plan and signals a significant upmarket push.",
      impact: "critical",
      confidence: 92,
      category: "Pricing",
      sources: ["acme.com", "TechCrunch", "Twitter"],
    },
    {
      id: "ins-2",
      briefingId: "br-1",
      competitorId: "comp-2",
      competitorName: "TechRival",
      title: "$50M Series C Funding Round Led by Sequoia",
      description:
        "TechRival closed a $50M Series C led by Sequoia Capital. Funds are earmarked for product development and international expansion into EU and APAC markets. This significantly strengthens their competitive position.",
      impact: "high",
      confidence: 98,
      category: "Funding",
      sources: ["Crunchbase", "TechCrunch", "LinkedIn"],
    },
    {
      id: "ins-3",
      briefingId: "br-1",
      competitorId: "comp-3",
      competitorName: "CompetitorX",
      title: "15+ New Roles in European Offices (London & Berlin)",
      description:
        "CompetitorX posted 15 new job listings for London and Berlin offices, including senior sales and engineering roles. This signals aggressive European market expansion planned for Q2 2026.",
      impact: "medium",
      confidence: 85,
      category: "Hiring",
      sources: ["LinkedIn", "Glassdoor"],
    },
    {
      id: "ins-4",
      briefingId: "br-1",
      competitorId: "comp-1",
      competitorName: "Acme Corp",
      title: "Homepage Redesigned to Target SMB Market",
      description:
        "Acme Corp redesigned their homepage with messaging focused on small business customers, adding new SMB case studies and a lower entry-level price point of $19/month.",
      impact: "medium",
      confidence: 78,
      category: "Positioning",
      sources: ["acme.com"],
    },
    {
      id: "ins-5",
      briefingId: "br-1",
      competitorId: "comp-4",
      competitorName: "DataFlow",
      title: "Negative Review Trend: G2 Rating Dropped to 3.8",
      description:
        "DataFlow received 8 negative reviews this week on G2, primarily citing poor customer support and reliability issues. Average rating dropped from 4.2 to 3.8. This creates an opportunity to win over dissatisfied DataFlow customers.",
      impact: "low",
      confidence: 90,
      category: "Reputation",
      sources: ["G2", "Capterra"],
    },
  ],
  predictiveSignals: [
    {
      id: "ps-1",
      title: "Acme Corp likely to acquire AI startup within 90 days",
      description:
        "Based on hiring patterns (5 ML roles), partnerships with AI companies, and the new enterprise AI tier, there is a high probability Acme Corp will make a strategic AI acquisition to accelerate their capabilities.",
      probability: 73,
      timeframe: "60-90 days",
      relatedCompetitors: ["Acme Corp"],
    },
    {
      id: "ps-2",
      title: "TechRival European launch expected Q2 2026",
      description:
        "Fresh funding combined with recent job postings for London-based roles and European compliance certifications suggest TechRival will launch EU operations in Q2 2026.",
      probability: 82,
      timeframe: "2-4 months",
      relatedCompetitors: ["TechRival"],
    },
    {
      id: "ps-3",
      title: "Market price compression in starter segment",
      description:
        "Multiple competitors are introducing lower-priced tiers. Acme Corp's new $19/mo plan and CompetitorX's freemium model suggest price compression in the starter segment over the next quarter.",
      probability: 68,
      timeframe: "1-3 months",
      relatedCompetitors: ["Acme Corp", "CompetitorX"],
    },
  ],
  recommendedPlays: [
    {
      id: "rp-1",
      title: "Accelerate AI Feature Rollout",
      description:
        "Acme Corp's enterprise AI tier creates urgency for your own AI capabilities. Prioritize shipping your AI analytics features to maintain competitive parity in the enterprise segment.",
      priority: "critical",
      effort: "high",
      expectedImpact:
        "Prevent enterprise customer churn and maintain competitive positioning",
    },
    {
      id: "rp-2",
      title: "Launch DataFlow Win-Back Campaign",
      description:
        "DataFlow's declining ratings and customer dissatisfaction create an acquisition opportunity. Launch a targeted campaign offering migration support and a competitive switching offer.",
      priority: "high",
      effort: "medium",
      expectedImpact:
        "Potential to capture 5-10% of DataFlow's dissatisfied customer base",
    },
    {
      id: "rp-3",
      title: "Establish European Presence Before Competitors",
      description:
        "With both TechRival and CompetitorX expanding into Europe, consider accelerating your own EU market entry or partnership strategy to establish presence before competition intensifies.",
      priority: "medium",
      effort: "high",
      expectedImpact:
        "First-mover advantage in underserved European market segments",
    },
    {
      id: "rp-4",
      title: "Review Starter Tier Pricing Strategy",
      description:
        "Monitor the price compression trend in the starter segment. Consider adjusting your entry-level pricing or adding more value at the current price point to remain competitive.",
      priority: "medium",
      effort: "low",
      expectedImpact: "Maintain conversion rates in the starter segment",
    },
  ],
};

export default function BriefingDetailPage() {
  const briefing = mockBriefing;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/briefings">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{briefing.title}</h1>
            <Badge
              variant="outline"
              className={getStatusColor(briefing.status)}
            >
              {briefing.status}
            </Badge>
          </div>
          <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
            <span className="flex items-center gap-1">
              <Calendar className="h-3.5 w-3.5" />
              {formatDate(briefing.weekStart)} -{" "}
              {formatDate(briefing.weekEnd)}
            </span>
            <span className="flex items-center gap-1">
              <FileText className="h-3.5 w-3.5" />
              {briefing.insightsCount} insights
            </span>
            <span className="flex items-center gap-1">
              <Users className="h-3.5 w-3.5" />
              {briefing.competitorsAnalyzed} competitors
            </span>
          </div>
        </div>
      </div>

      {/* Executive Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-primary" />
            Executive Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-muted-foreground">
            {briefing.executiveSummary}
          </p>
        </CardContent>
      </Card>

      {/* Top Insights */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="h-5 w-5 text-orange-500" />
          <h2 className="text-xl font-semibold">Top Insights</h2>
          <Badge variant="secondary">{briefing.insights.length}</Badge>
        </div>
        <div className="space-y-3">
          {briefing.insights.map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      </div>

      {/* Predictive Signals */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="h-5 w-5 text-blue-500" />
          <h2 className="text-xl font-semibold">Predictive Signals</h2>
          <Badge variant="secondary">
            {briefing.predictiveSignals.length}
          </Badge>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {briefing.predictiveSignals.map((signal) => (
            <Card key={signal.id}>
              <CardContent className="p-5 space-y-3">
                <h4 className="font-medium leading-snug">{signal.title}</h4>
                <p className="text-sm text-muted-foreground">
                  {signal.description}
                </p>
                <Separator />
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Probability</span>
                    <span className="font-medium">{signal.probability}%</span>
                  </div>
                  <Progress value={signal.probability} className="h-1.5" />
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Timeframe</span>
                  <span className="font-medium">{signal.timeframe}</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {signal.relatedCompetitors.map((comp) => (
                    <Badge key={comp} variant="secondary" className="text-xs">
                      {comp}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Recommended Plays */}
      <div>
        <div className="flex items-center gap-2 mb-4">
          <Target className="h-5 w-5 text-emerald-500" />
          <h2 className="text-xl font-semibold">Recommended Plays</h2>
          <Badge variant="secondary">
            {briefing.recommendedPlays.length}
          </Badge>
        </div>
        <div className="space-y-3">
          {briefing.recommendedPlays.map((play) => (
            <Card key={play.id}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className={getImpactColor(play.priority)}
                      >
                        {play.priority} priority
                      </Badge>
                      <Badge variant="secondary">
                        {play.effort} effort
                      </Badge>
                    </div>
                    <h4 className="font-semibold">{play.title}</h4>
                    <p className="text-sm text-muted-foreground">
                      {play.description}
                    </p>
                    <div className="flex items-start gap-2 rounded-lg bg-muted/50 p-3">
                      <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-yellow-500" />
                      <p className="text-xs text-muted-foreground">
                        <span className="font-medium text-foreground">
                          Expected Impact:
                        </span>{" "}
                        {play.expectedImpact}
                      </p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
