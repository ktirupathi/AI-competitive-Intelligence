"use client";

import { useState } from "react";
import {
  Building2,
  CheckCircle2,
  ChevronRight,
  Globe,
  Sparkles,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface OnboardingWizardProps {
  onComplete: () => void;
  onAddCompetitor: (competitor: { name: string; domain: string }) => Promise<void>;
}

const STEPS = [
  { id: "welcome", title: "Welcome", icon: Sparkles },
  { id: "competitor", title: "Add Competitor", icon: Building2 },
  { id: "ready", title: "All Set", icon: CheckCircle2 },
] as const;

export function OnboardingWizard({
  onComplete,
  onAddCompetitor,
}: OnboardingWizardProps) {
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleAddCompetitor = async () => {
    if (!name.trim() || !domain.trim()) {
      setError("Both name and domain are required.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await onAddCompetitor({ name: name.trim(), domain: domain.trim() });
      setStep(2);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to add competitor."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <Card className="w-full max-w-lg mx-4 border-zinc-800 bg-zinc-900">
        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 pt-6 px-6">
          {STEPS.map((s, i) => (
            <div key={s.id} className="flex items-center gap-2">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium transition-colors",
                  i <= step
                    ? "bg-primary text-primary-foreground"
                    : "bg-zinc-800 text-zinc-500"
                )}
              >
                {i < step ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : (
                  i + 1
                )}
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={cn(
                    "h-px w-12 transition-colors",
                    i < step ? "bg-primary" : "bg-zinc-800"
                  )}
                />
              )}
            </div>
          ))}
        </div>

        <CardContent className="p-6 pt-8">
          {/* Step 0: Welcome */}
          {step === 0 && (
            <div className="text-center space-y-4">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                <Sparkles className="h-8 w-8 text-primary" />
              </div>
              <h2 className="text-xl font-bold text-zinc-100">
                Welcome to Scout AI
              </h2>
              <p className="text-sm text-zinc-400 max-w-sm mx-auto">
                Set up your competitive intelligence in under a minute.
                We&apos;ll monitor your competitors and deliver weekly
                AI-powered briefings.
              </p>
              <div className="grid grid-cols-3 gap-3 pt-2">
                {[
                  { icon: Globe, label: "Website monitoring" },
                  { icon: Building2, label: "Job & news tracking" },
                  { icon: Zap, label: "AI-powered insights" },
                ].map(({ icon: Icon, label }) => (
                  <div
                    key={label}
                    className="flex flex-col items-center gap-2 rounded-lg border border-zinc-800 p-3"
                  >
                    <Icon className="h-5 w-5 text-zinc-400" />
                    <span className="text-xs text-zinc-500">{label}</span>
                  </div>
                ))}
              </div>
              <Button className="w-full mt-4" onClick={() => setStep(1)}>
                Get Started
                <ChevronRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          )}

          {/* Step 1: Add first competitor */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="text-center mb-2">
                <h2 className="text-xl font-bold text-zinc-100">
                  Add your first competitor
                </h2>
                <p className="text-sm text-zinc-400 mt-1">
                  We&apos;ll start monitoring them right away.
                </p>
              </div>
              <div className="space-y-3">
                <div>
                  <Label htmlFor="onboard-name">Company name</Label>
                  <Input
                    id="onboard-name"
                    placeholder="e.g. Acme Corp"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    disabled={loading}
                  />
                </div>
                <div>
                  <Label htmlFor="onboard-domain">Website domain</Label>
                  <Input
                    id="onboard-domain"
                    placeholder="e.g. acme.com"
                    value={domain}
                    onChange={(e) => setDomain(e.target.value)}
                    disabled={loading}
                  />
                </div>
              </div>
              {error && (
                <p className="text-sm text-red-400">{error}</p>
              )}
              <div className="flex gap-3 pt-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => {
                    setStep(2); // Skip
                  }}
                  disabled={loading}
                >
                  Skip for now
                </Button>
                <Button
                  className="flex-1"
                  onClick={handleAddCompetitor}
                  disabled={loading}
                >
                  {loading ? "Adding..." : "Add Competitor"}
                </Button>
              </div>
            </div>
          )}

          {/* Step 2: All set */}
          {step === 2 && (
            <div className="text-center space-y-4">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/10">
                <CheckCircle2 className="h-8 w-8 text-emerald-500" />
              </div>
              <h2 className="text-xl font-bold text-zinc-100">
                You&apos;re all set!
              </h2>
              <p className="text-sm text-zinc-400 max-w-sm mx-auto">
                Scout AI is now monitoring your competitive landscape. Your
                first briefing will arrive within 24 hours.
              </p>
              <Button className="w-full mt-4" onClick={onComplete}>
                Go to Dashboard
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
