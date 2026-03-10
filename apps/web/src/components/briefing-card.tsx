"use client";

import Link from "next/link";
import { Calendar, FileText, Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate, getStatusColor } from "@/lib/utils";
import type { Briefing } from "@/lib/types";

interface BriefingCardProps {
  briefing: Briefing;
}

export function BriefingCard({ briefing }: BriefingCardProps) {
  return (
    <Link href={`/briefings/${briefing.id}`}>
      <Card className="group cursor-pointer transition-all hover:border-primary/30 hover:shadow-md">
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <h3 className="font-semibold group-hover:text-primary transition-colors">
                {briefing.title}
              </h3>
              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                <Calendar className="h-3.5 w-3.5" />
                <span>
                  {formatDate(briefing.weekStart)} -{" "}
                  {formatDate(briefing.weekEnd)}
                </span>
              </div>
            </div>
            <Badge
              variant="outline"
              className={getStatusColor(briefing.status)}
            >
              {briefing.status}
            </Badge>
          </div>

          {briefing.executiveSummary && (
            <p className="mt-3 text-sm text-muted-foreground line-clamp-2">
              {briefing.executiveSummary}
            </p>
          )}

          <div className="mt-4 flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <FileText className="h-3.5 w-3.5" />
              <span>{briefing.insightsCount} insights</span>
            </div>
            <div className="flex items-center gap-1">
              <Users className="h-3.5 w-3.5" />
              <span>{briefing.competitorsAnalyzed} competitors</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
