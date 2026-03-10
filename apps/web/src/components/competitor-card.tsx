"use client";

import Link from "next/link";
import { Globe, Clock, TrendingUp } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { formatRelativeTime, getStatusColor } from "@/lib/utils";
import type { Competitor } from "@/lib/types";

interface CompetitorCardProps {
  competitor: Competitor;
}

export function CompetitorCard({ competitor }: CompetitorCardProps) {
  return (
    <Link href={`/competitors/${competitor.id}`}>
      <Card className="group cursor-pointer transition-all hover:border-primary/30 hover:shadow-md">
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <Avatar className="h-10 w-10 rounded-lg">
                <AvatarImage
                  src={competitor.logoUrl}
                  alt={competitor.name}
                />
                <AvatarFallback className="rounded-lg bg-primary/10 text-primary">
                  {competitor.name.substring(0, 2).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div>
                <h3 className="font-semibold group-hover:text-primary transition-colors">
                  {competitor.name}
                </h3>
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Globe className="h-3 w-3" />
                  {competitor.domain}
                </div>
              </div>
            </div>
            <Badge
              className={getStatusColor(competitor.status)}
              variant="outline"
            >
              {competitor.status}
            </Badge>
          </div>

          <div className="mt-4 flex items-center justify-between text-sm">
            <div className="flex items-center gap-1 text-muted-foreground">
              <Clock className="h-3.5 w-3.5" />
              <span>
                {competitor.lastScannedAt
                  ? formatRelativeTime(competitor.lastScannedAt)
                  : "Never scanned"}
              </span>
            </div>
            {competitor.changesCount !== undefined && (
              <div className="flex items-center gap-1 text-muted-foreground">
                <TrendingUp className="h-3.5 w-3.5" />
                <span>{competitor.changesCount} changes</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
