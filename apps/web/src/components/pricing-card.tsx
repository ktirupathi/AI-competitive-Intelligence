"use client";

import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { PricingTier } from "@/lib/types";

interface PricingCardProps {
  tier: PricingTier;
  onSelect?: (tier: PricingTier) => void;
}

export function PricingCard({ tier, onSelect }: PricingCardProps) {
  return (
    <Card
      className={cn(
        "relative flex flex-col transition-all",
        tier.highlighted
          ? "border-primary shadow-lg shadow-primary/10 scale-105"
          : "hover:border-primary/30"
      )}
    >
      {tier.highlighted && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground">
            Most Popular
          </span>
        </div>
      )}
      <CardHeader className="text-center">
        <CardTitle className="text-xl">{tier.name}</CardTitle>
        <CardDescription>{tier.description}</CardDescription>
        <div className="mt-4">
          <span className="text-4xl font-bold">${tier.price}</span>
          <span className="text-muted-foreground">/{tier.period}</span>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          {tier.competitors}
        </p>
      </CardHeader>
      <CardContent className="flex-1">
        <ul className="space-y-3">
          {tier.features.map((feature, index) => (
            <li key={index} className="flex items-start gap-2">
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              <span className="text-sm">{feature}</span>
            </li>
          ))}
        </ul>
      </CardContent>
      <CardFooter>
        <Button
          className="w-full"
          variant={tier.highlighted ? "default" : "outline"}
          onClick={() => onSelect?.(tier)}
        >
          {tier.ctaText}
        </Button>
      </CardFooter>
    </Card>
  );
}
