import Link from "next/link";
import {
  Radar,
  Brain,
  Mail,
  Globe,
  Slack,
  TrendingUp,
  ArrowRight,
  Newspaper,
  Star,
  Briefcase,
  Share2,
  BarChart3,
  Zap,
  Shield,
  Clock,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { PricingTier } from "@/lib/types";

const features = [
  {
    icon: Radar,
    title: "Auto-Monitoring",
    description:
      "Continuously scan competitor websites, news, job boards, and social media. No manual effort required.",
  },
  {
    icon: Brain,
    title: "AI Analysis",
    description:
      "Advanced AI synthesizes raw data into strategic insights with impact scores and confidence ratings.",
  },
  {
    icon: Mail,
    title: "Weekly Briefings",
    description:
      "Receive comprehensive weekly intelligence briefings delivered to your inbox or Slack, every Monday.",
  },
  {
    icon: Globe,
    title: "Multi-Source Intel",
    description:
      "Aggregate intelligence from 50+ data sources including websites, reviews, news, social media, and more.",
  },
  {
    icon: Slack,
    title: "Slack Integration",
    description:
      "Get real-time alerts and weekly briefings delivered directly to your team's Slack channel.",
  },
  {
    icon: TrendingUp,
    title: "Predictive Insights",
    description:
      "AI-powered predictions about competitor moves, market shifts, and emerging threats before they happen.",
  },
];

const steps = [
  {
    step: "01",
    title: "Add Competitors",
    description:
      "Simply enter competitor names or domains. Our AI automatically identifies and maps all relevant data sources.",
  },
  {
    step: "02",
    title: "We Monitor 24/7",
    description:
      "Scout AI continuously monitors 50+ data sources, detecting changes, news, hiring signals, and market moves.",
  },
  {
    step: "03",
    title: "Get Briefings",
    description:
      "Receive AI-synthesized weekly briefings with prioritized insights, predictions, and recommended actions.",
  },
];

const dataSources = [
  { icon: Globe, label: "Websites", description: "Pricing, features, messaging changes" },
  { icon: Newspaper, label: "News", description: "Press releases, coverage, funding" },
  { icon: Star, label: "Reviews", description: "G2, Capterra, Trustpilot ratings" },
  { icon: Briefcase, label: "Job Postings", description: "Hiring trends, team growth" },
  { icon: Share2, label: "Social Media", description: "Twitter, LinkedIn activity" },
  { icon: BarChart3, label: "Market Signals", description: "Traffic, downloads, rankings" },
];

const pricingTiers: PricingTier[] = [
  {
    name: "Starter",
    price: 49,
    period: "mo",
    description: "Perfect for startups tracking key competitors",
    competitors: "Up to 3 competitors",
    highlighted: false,
    ctaText: "Start Free Trial",
    features: [
      "3 competitor profiles",
      "Weekly email briefings",
      "Website & news monitoring",
      "Basic AI analysis",
      "7-day data history",
      "Email support",
    ],
  },
  {
    name: "Professional",
    price: 149,
    period: "mo",
    description: "For growing teams that need comprehensive intelligence",
    competitors: "Up to 10 competitors",
    highlighted: true,
    ctaText: "Start Free Trial",
    features: [
      "10 competitor profiles",
      "Weekly email & Slack briefings",
      "All data sources monitored",
      "Advanced AI with predictions",
      "90-day data history",
      "Slack integration",
      "Custom alert rules",
      "Priority support",
    ],
  },
  {
    name: "Enterprise",
    price: 499,
    period: "mo",
    description: "For organizations requiring full competitive intelligence",
    competitors: "Unlimited competitors",
    highlighted: false,
    ctaText: "Contact Sales",
    features: [
      "Unlimited competitor profiles",
      "Daily & weekly briefings",
      "All data sources + custom sources",
      "Enterprise AI with strategic playbooks",
      "Unlimited data history",
      "Slack, email, webhook integrations",
      "API access",
      "Dedicated account manager",
      "Custom onboarding",
      "SSO & SAML",
    ],
  },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-sm">
        <div className="container mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <Radar className="h-7 w-7 text-primary" />
            <span className="text-xl font-bold">Scout AI</span>
          </div>
          <div className="hidden items-center gap-8 md:flex">
            <a
              href="#features"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Features
            </a>
            <a
              href="#how-it-works"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              How It Works
            </a>
            <a
              href="#pricing"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Pricing
            </a>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/sign-in">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link href="/sign-up">
              <Button size="sm">Get Started</Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="hero-gradient relative overflow-hidden">
        <div className="container mx-auto max-w-6xl px-4 py-24 text-center md:py-32">
          <div className="mx-auto max-w-3xl">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border bg-card px-4 py-1.5 text-sm">
              <Zap className="h-3.5 w-3.5 text-primary" />
              <span className="text-muted-foreground">
                AI-Powered Competitive Intelligence
              </span>
            </div>
            <h1 className="text-4xl font-bold tracking-tight md:text-6xl lg:text-7xl">
              AI Competitive{" "}
              <span className="text-primary">Intelligence</span> Agent
            </h1>
            <p className="mt-6 text-lg text-muted-foreground md:text-xl">
              Monitor competitors. Get weekly briefings. Stay ahead.
              <br />
              Scout AI watches your competition 24/7 and delivers actionable
              intelligence straight to your inbox.
            </p>
            <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Link href="/sign-up">
                <Button size="lg" className="gap-2 text-base px-8">
                  Start Free Trial
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <a href="#how-it-works">
                <Button variant="outline" size="lg" className="text-base px-8">
                  See How It Works
                </Button>
              </a>
            </div>
            <div className="mt-12 flex items-center justify-center gap-8 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-primary" />
                No credit card required
              </div>
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-primary" />
                Setup in 2 minutes
              </div>
              <div className="flex items-center gap-2">
                <Check className="h-4 w-4 text-primary" />
                14-day free trial
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="feature-gradient py-24">
        <div className="container mx-auto max-w-6xl px-4">
          <div className="text-center">
            <h2 className="text-3xl font-bold md:text-4xl">
              Everything you need to track competitors
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Powerful AI-driven features that give you an unfair advantage
            </p>
          </div>
          <div className="mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {features.map((feature) => (
              <Card
                key={feature.title}
                className="group transition-all hover:border-primary/30 hover:shadow-md"
              >
                <CardContent className="p-6">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                    <feature.icon className="h-6 w-6 text-primary" />
                  </div>
                  <h3 className="mt-4 text-lg font-semibold">
                    {feature.title}
                  </h3>
                  <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="border-t py-24">
        <div className="container mx-auto max-w-6xl px-4">
          <div className="text-center">
            <h2 className="text-3xl font-bold md:text-4xl">
              How Scout AI Works
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Get competitive intelligence in three simple steps
            </p>
          </div>
          <div className="mt-16 grid gap-8 md:grid-cols-3">
            {steps.map((step, index) => (
              <div key={step.step} className="relative text-center">
                {index < steps.length - 1 && (
                  <div className="absolute left-1/2 top-8 hidden h-0.5 w-full bg-border md:block" />
                )}
                <div className="relative mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-primary text-xl font-bold text-primary-foreground">
                  {step.step}
                </div>
                <h3 className="mt-6 text-xl font-semibold">{step.title}</h3>
                <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Data Sources */}
      <section className="border-t py-24">
        <div className="container mx-auto max-w-6xl px-4">
          <div className="text-center">
            <h2 className="text-3xl font-bold md:text-4xl">
              50+ Data Sources Monitored
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              We aggregate intelligence from every corner of the web
            </p>
          </div>
          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {dataSources.map((source) => (
              <div
                key={source.label}
                className="flex items-center gap-4 rounded-lg border bg-card p-5 transition-all hover:border-primary/30"
              >
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <source.icon className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold">{source.label}</h3>
                  <p className="text-sm text-muted-foreground">
                    {source.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="border-t py-24">
        <div className="container mx-auto max-w-6xl px-4">
          <div className="text-center">
            <h2 className="text-3xl font-bold md:text-4xl">
              Simple, transparent pricing
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Start free. Upgrade when you need more competitors.
            </p>
          </div>
          <div className="mt-16 grid gap-8 md:grid-cols-3 items-start">
            {pricingTiers.map((tier) => (
              <Card
                key={tier.name}
                className={`relative flex flex-col transition-all ${
                  tier.highlighted
                    ? "border-primary shadow-lg shadow-primary/10 md:scale-105"
                    : "hover:border-primary/30"
                }`}
              >
                {tier.highlighted && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground">
                      Most Popular
                    </span>
                  </div>
                )}
                <div className="p-6 text-center">
                  <h3 className="text-xl font-semibold">{tier.name}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {tier.description}
                  </p>
                  <div className="mt-4">
                    <span className="text-4xl font-bold">${tier.price}</span>
                    <span className="text-muted-foreground">
                      /{tier.period}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {tier.competitors}
                  </p>
                </div>
                <div className="flex-1 px-6 pb-2">
                  <ul className="space-y-3">
                    {tier.features.map((feature, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                        <span className="text-sm">{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="p-6 pt-4">
                  <Link href="/sign-up">
                    <Button
                      className="w-full"
                      variant={tier.highlighted ? "default" : "outline"}
                    >
                      {tier.ctaText}
                    </Button>
                  </Link>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t">
        <div className="container mx-auto max-w-6xl px-4 py-24">
          <div className="rounded-2xl bg-primary/5 border border-primary/20 p-12 text-center">
            <h2 className="text-3xl font-bold md:text-4xl">
              Ready to outsmart your competition?
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Join hundreds of companies using Scout AI to stay ahead. Start
              your free trial today.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Link href="/sign-up">
                <Button size="lg" className="gap-2 text-base px-8">
                  Start Your Free Trial
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/sign-in">
                <Button variant="outline" size="lg" className="text-base px-8">
                  Sign In
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-12">
        <div className="container mx-auto max-w-6xl px-4">
          <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
            <div className="flex items-center gap-2">
              <Radar className="h-5 w-5 text-primary" />
              <span className="font-semibold">Scout AI</span>
            </div>
            <p className="text-sm text-muted-foreground">
              &copy; {new Date().getFullYear()} Scout AI. All rights reserved.
            </p>
            <div className="flex gap-6 text-sm text-muted-foreground">
              <a href="#" className="hover:text-foreground transition-colors">
                Privacy
              </a>
              <a href="#" className="hover:text-foreground transition-colors">
                Terms
              </a>
              <a href="#" className="hover:text-foreground transition-colors">
                Contact
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
