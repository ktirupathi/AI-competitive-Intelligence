"use client";

import { ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { getImpactColor } from "@/lib/utils";
import type { Insight } from "@/lib/types";

interface InsightCardProps {
  insight: Insight;
  showCompetitor?: boolean;
}

export function InsightCard({ insight, showCompetitor = true }: InsightCardProps) {
  return (
    <Card className="transition-all hover:border-primary/20">
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              {showCompetitor && (
                <span className="text-xs font-medium text-muted-foreground">
                  {insight.competitorName}
                </span>
              )}
              <Badge
                variant="outline"
                className={getImpactColor(insight.impact)}
              >
                {insight.impact}
              </Badge>
              <Badge variant="secondary" className="text-xs">
                {insight.category}
              </Badge>
            </div>
            <h4 className="font-medium leading-snug">{insight.title}</h4>
            <p className="text-sm text-muted-foreground line-clamp-2">
              {insight.description}
            </p>
          </div>
          <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
        </div>

        <div className="mt-3 flex items-center gap-3">
          <div className="flex items-center gap-2 flex-1">
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              Confidence
            </span>
            <Progress value={insight.confidence} className="h-1.5" />
            <span className="text-xs font-medium">{insight.confidence}%</span>
          </div>
          {insight.sources.length > 0 && (
            <span className="text-xs text-muted-foreground">
              {insight.sources.length} source{insight.sources.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
