"use client";

import { useState } from "react";
import { Search, LayoutGrid, List } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { CompetitorCard } from "@/components/competitor-card";
import { AddCompetitorDialog } from "@/components/add-competitor-dialog";
import type { Competitor } from "@/lib/types";

const mockCompetitors: Competitor[] = [
  {
    id: "comp-1",
    name: "Acme Corp",
    domain: "acme.com",
    description: "Enterprise software platform for workflow automation",
    status: "active",
    lastScannedAt: "2026-03-10T06:30:00Z",
    createdAt: "2025-11-15T00:00:00Z",
    updatedAt: "2026-03-10T06:30:00Z",
    changesCount: 24,
    insightsCount: 8,
  },
  {
    id: "comp-2",
    name: "TechRival",
    domain: "techrival.io",
    description: "AI-first data analytics and business intelligence",
    status: "active",
    lastScannedAt: "2026-03-10T05:15:00Z",
    createdAt: "2025-12-01T00:00:00Z",
    updatedAt: "2026-03-10T05:15:00Z",
    changesCount: 18,
    insightsCount: 6,
  },
  {
    id: "comp-3",
    name: "CompetitorX",
    domain: "competitorx.com",
    description: "Cloud-native platform for developer teams",
    status: "active",
    lastScannedAt: "2026-03-10T04:00:00Z",
    createdAt: "2025-12-10T00:00:00Z",
    updatedAt: "2026-03-10T04:00:00Z",
    changesCount: 31,
    insightsCount: 11,
  },
  {
    id: "comp-4",
    name: "DataFlow",
    domain: "dataflow.dev",
    description: "Real-time data pipeline and ETL platform",
    status: "active",
    lastScannedAt: "2026-03-09T22:00:00Z",
    createdAt: "2026-01-05T00:00:00Z",
    updatedAt: "2026-03-09T22:00:00Z",
    changesCount: 9,
    insightsCount: 3,
  },
  {
    id: "comp-5",
    name: "CloudNova",
    domain: "cloudnova.io",
    description: "Multi-cloud infrastructure management",
    status: "active",
    lastScannedAt: "2026-03-10T03:45:00Z",
    createdAt: "2026-01-20T00:00:00Z",
    updatedAt: "2026-03-10T03:45:00Z",
    changesCount: 15,
    insightsCount: 5,
  },
  {
    id: "comp-6",
    name: "InsightPro",
    domain: "insightpro.ai",
    description: "Market research and competitive intelligence tools",
    status: "pending",
    lastScannedAt: undefined,
    createdAt: "2026-03-08T00:00:00Z",
    updatedAt: "2026-03-08T00:00:00Z",
    changesCount: 0,
    insightsCount: 0,
  },
  {
    id: "comp-7",
    name: "NexGen Solutions",
    domain: "nexgen.co",
    description: "Next-generation SaaS platform for enterprises",
    status: "active",
    lastScannedAt: "2026-03-10T01:30:00Z",
    createdAt: "2026-02-01T00:00:00Z",
    updatedAt: "2026-03-10T01:30:00Z",
    changesCount: 7,
    insightsCount: 2,
  },
];

export default function CompetitorsPage() {
  const [search, setSearch] = useState("");
  const [competitors] = useState<Competitor[]>(mockCompetitors);

  const filtered = competitors.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.domain.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Competitors</h1>
          <p className="text-muted-foreground">
            {competitors.length} competitors tracked
          </p>
        </div>
        <AddCompetitorDialog />
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search competitors..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-1">
          <Button variant="ghost" size="icon" className="text-primary">
            <LayoutGrid className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon">
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filtered.map((competitor) => (
          <CompetitorCard key={competitor.id} competitor={competitor} />
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Search className="h-12 w-12 text-muted-foreground/50" />
          <h3 className="mt-4 text-lg font-semibold">No competitors found</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Try adjusting your search or add a new competitor.
          </p>
        </div>
      )}
    </div>
  );
}
