"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Users,
  FileText,
  TrendingUp,
  Clock,
  ArrowRight,
  Calendar,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { InsightCard } from "@/components/insight-card";
import { getImpactColor, formatDate, formatRelativeTime } from "@/lib/utils";
import type { Insight, Briefing } from "@/lib/types";

const mockBriefing: Briefing = {
  id: "br-1",
  title: "Weekly Intelligence Briefing",
  weekStart: "2026-03-02",
  weekEnd: "2026-03-08",
  status: "delivered",
  executiveSummary:
    "This week saw significant activity across your competitive landscape. Acme Corp announced a new enterprise tier with AI features, while TechRival raised a $50M Series C. Key hiring signals suggest CompetitorX is expanding into the European market.",
  insightsCount: 12,
  competitorsAnalyzed: 7,
  createdAt: "2026-03-09T08:00:00Z",
};

const mockInsights: Insight[] = [
  {
    id: "ins-1",
    briefingId: "br-1",
    competitorId: "comp-1",
    competitorName: "Acme Corp",
    title: "New Enterprise Tier with AI-Powered Features Announced",
    description:
      "Acme Corp launched a new enterprise pricing tier ($999/mo) featuring AI-powered analytics and custom integrations. This directly competes with our Professional plan.",
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
    title: "$50M Series C Funding Round Closed",
    description:
      "TechRival closed a $50M Series C led by Sequoia Capital. Funds earmarked for product development and international expansion into EU and APAC markets.",
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
    title: "Hiring 15+ Roles in European Offices",
    description:
      "CompetitorX posted 15 new job listings for London and Berlin offices, signaling aggressive European market expansion in Q2 2026.",
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
    title: "Website Messaging Shift Toward SMB Market",
    description:
      "Acme Corp redesigned their homepage to target small businesses, adding new SMB-specific case studies and a lower entry-level price point.",
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
    title: "Negative Review Trend on G2 Platform",
    description:
      "DataFlow received 8 negative reviews in the past week on G2, primarily citing poor customer support and reliability issues. Average rating dropped from 4.2 to 3.8.",
    impact: "low",
    confidence: 90,
    category: "Reputation",
    sources: ["G2", "Capterra"],
  },
];

export default function DashboardPage() {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setCurrentTime(new Date()), 60000);
    return () => clearInterval(interval);
  }, []);

  const nextBriefingDate = new Date("2026-03-16T08:00:00Z");
  const daysUntilBriefing = Math.ceil(
    (nextBriefingDate.getTime() - currentTime.getTime()) / 86400000
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Your competitive intelligence overview
          </p>
        </div>
        <Button variant="outline" size="sm" className="gap-2">
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">
                  Competitors Tracked
                </p>
                <p className="text-2xl font-bold">7</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Users className="h-5 w-5 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">
                  Insights This Week
                </p>
                <p className="text-2xl font-bold">12</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-500/10">
                <TrendingUp className="h-5 w-5 text-orange-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Data Freshness</p>
                <p className="text-2xl font-bold">2h ago</p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10">
                <Clock className="h-5 w-5 text-emerald-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Next Briefing</p>
                <p className="text-2xl font-bold">
                  {daysUntilBriefing > 0
                    ? `${daysUntilBriefing}d`
                    : "Today"}
                </p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10">
                <Calendar className="h-5 w-5 text-blue-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Latest Briefing */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <CardTitle className="text-lg">Latest Briefing</CardTitle>
              <Link href={`/briefings/${mockBriefing.id}`}>
                <Button variant="ghost" size="sm" className="gap-1">
                  View Full Briefing
                  <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-3">
                <Calendar className="h-3.5 w-3.5" />
                <span>
                  {formatDate(mockBriefing.weekStart)} -{" "}
                  {formatDate(mockBriefing.weekEnd)}
                </span>
                <Badge
                  variant="outline"
                  className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                >
                  {mockBriefing.status}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {mockBriefing.executiveSummary}
              </p>
              <div className="mt-4 flex gap-4 text-sm text-muted-foreground">
                <span className="flex items-center gap-1">
                  <FileText className="h-3.5 w-3.5" />
                  {mockBriefing.insightsCount} insights
                </span>
                <span className="flex items-center gap-1">
                  <Users className="h-3.5 w-3.5" />
                  {mockBriefing.competitorsAnalyzed} competitors analyzed
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Top Insights */}
          <div>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Top Insights</h2>
              <Link href="/briefings">
                <Button variant="ghost" size="sm" className="gap-1">
                  View All
                  <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </div>
            <div className="space-y-3">
              {mockInsights.slice(0, 5).map((insight) => (
                <InsightCard key={insight.id} insight={insight} />
              ))}
            </div>
          </div>
        </div>

        {/* Right Sidebar */}
        <div className="space-y-6">
          {/* Next Briefing Schedule */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Next Briefing</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                  <Calendar className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <p className="font-medium">Monday, Mar 16</p>
                  <p className="text-sm text-muted-foreground">
                    8:00 AM EST
                  </p>
                </div>
              </div>
              <div className="mt-4 rounded-lg bg-muted/50 p-3">
                <p className="text-xs text-muted-foreground">
                  Analyzing data from 7 competitors across 50+ sources.
                  Briefing will be delivered to your inbox and Slack.
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Critical Alerts */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-red-500" />
                Critical Alerts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={getImpactColor("critical")}
                    >
                      critical
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      2h ago
                    </span>
                  </div>
                  <p className="mt-2 text-sm font-medium">
                    Acme Corp launched enterprise AI tier
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Direct pricing competition detected
                  </p>
                </div>
                <div className="rounded-lg border border-orange-500/20 bg-orange-500/5 p-3">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={getImpactColor("high")}
                    >
                      high
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      1d ago
                    </span>
                  </div>
                  <p className="mt-2 text-sm font-medium">
                    TechRival closed $50M funding round
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Expanding into your market
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Competitor Activity */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  {
                    name: "Acme Corp",
                    action: "Pricing page updated",
                    time: "2h ago",
                  },
                  {
                    name: "TechRival",
                    action: "Press release published",
                    time: "5h ago",
                  },
                  {
                    name: "CompetitorX",
                    action: "12 new job postings",
                    time: "1d ago",
                  },
                  {
                    name: "DataFlow",
                    action: "New feature launched",
                    time: "2d ago",
                  },
                ].map((activity, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium">{activity.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {activity.action}
                      </p>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {activity.time}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
