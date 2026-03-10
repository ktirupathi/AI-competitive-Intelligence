"use client";

import { useState } from "react";
import { FileText, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BriefingCard } from "@/components/briefing-card";
import type { Briefing } from "@/lib/types";

const mockBriefings: Briefing[] = [
  {
    id: "br-1",
    title: "Weekly Intelligence Briefing #12",
    weekStart: "2026-03-02",
    weekEnd: "2026-03-08",
    status: "delivered",
    executiveSummary:
      "This week saw significant activity: Acme Corp announced a new enterprise tier with AI features, TechRival raised a $50M Series C, and CompetitorX is expanding into the European market with 15+ new hires.",
    insightsCount: 12,
    competitorsAnalyzed: 7,
    createdAt: "2026-03-09T08:00:00Z",
  },
  {
    id: "br-2",
    title: "Weekly Intelligence Briefing #11",
    weekStart: "2026-02-23",
    weekEnd: "2026-03-01",
    status: "delivered",
    executiveSummary:
      "Relatively quiet week with minor website updates across competitors. DataFlow launched a new feature set and CloudNova updated their pricing page. No critical changes detected.",
    insightsCount: 6,
    competitorsAnalyzed: 7,
    createdAt: "2026-03-02T08:00:00Z",
  },
  {
    id: "br-3",
    title: "Weekly Intelligence Briefing #10",
    weekStart: "2026-02-16",
    weekEnd: "2026-02-22",
    status: "delivered",
    executiveSummary:
      "Major week: CompetitorX launched a freemium tier, potentially disrupting the market. Acme Corp's CEO published a thought leadership piece on AI in enterprise. Multiple hiring signals detected.",
    insightsCount: 15,
    competitorsAnalyzed: 7,
    createdAt: "2026-02-23T08:00:00Z",
  },
  {
    id: "br-4",
    title: "Weekly Intelligence Briefing #9",
    weekStart: "2026-02-09",
    weekEnd: "2026-02-15",
    status: "delivered",
    executiveSummary:
      "TechRival announced a strategic partnership with a major cloud provider. Several competitors updated their product documentation, signaling upcoming feature releases.",
    insightsCount: 9,
    competitorsAnalyzed: 7,
    createdAt: "2026-02-16T08:00:00Z",
  },
  {
    id: "br-5",
    title: "Weekly Intelligence Briefing #8",
    weekStart: "2026-02-02",
    weekEnd: "2026-02-08",
    status: "delivered",
    executiveSummary:
      "NexGen Solutions entered our competitive space with an aggressive pricing strategy. Review sentiment across competitors remained stable. Key hiring signals in ML/AI roles across the board.",
    insightsCount: 11,
    competitorsAnalyzed: 6,
    createdAt: "2026-02-09T08:00:00Z",
  },
  {
    id: "br-next",
    title: "Weekly Intelligence Briefing #13",
    weekStart: "2026-03-09",
    weekEnd: "2026-03-15",
    status: "scheduled",
    insightsCount: 0,
    competitorsAnalyzed: 0,
    createdAt: "2026-03-09T00:00:00Z",
  },
];

export default function BriefingsPage() {
  const [briefings] = useState<Briefing[]>(mockBriefings);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Briefings</h1>
          <p className="text-muted-foreground">
            Your weekly competitive intelligence reports
          </p>
        </div>
        <Button variant="outline" size="sm" className="gap-2">
          <Filter className="h-3.5 w-3.5" />
          Filter
        </Button>
      </div>

      <div className="space-y-4">
        {briefings.map((briefing) => (
          <BriefingCard key={briefing.id} briefing={briefing} />
        ))}
      </div>

      {briefings.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <FileText className="h-12 w-12 text-muted-foreground/50" />
          <h3 className="mt-4 text-lg font-semibold">No briefings yet</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Your first briefing will be generated once you add competitors.
          </p>
        </div>
      )}
    </div>
  );
}
