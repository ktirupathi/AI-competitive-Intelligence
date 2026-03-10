"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Globe,
  Clock,
  TrendingUp,
  TrendingDown,
  Users,
  DollarSign,
  Code,
  ExternalLink,
  ThumbsUp,
  ThumbsDown,
  Minus,
  Briefcase,
  MapPin,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import {
  getImpactColor,
  getStatusColor,
  formatDate,
  formatRelativeTime,
} from "@/lib/utils";
import type {
  CompetitorDetail,
  Change,
  NewsItem,
  JobPosting,
  Review,
  SocialPost,
} from "@/lib/types";

const mockCompetitor: CompetitorDetail = {
  id: "comp-1",
  name: "Acme Corp",
  domain: "acme.com",
  description:
    "Enterprise software platform for workflow automation. Founded in 2018, headquartered in San Francisco.",
  status: "active",
  lastScannedAt: "2026-03-10T06:30:00Z",
  createdAt: "2025-11-15T00:00:00Z",
  updatedAt: "2026-03-10T06:30:00Z",
  changesCount: 24,
  insightsCount: 8,
  overview: {
    employeeCount: 350,
    employeeGrowth: 12,
    funding: "$85M Series B",
    techStack: ["React", "Python", "AWS", "PostgreSQL", "Redis", "Kubernetes"],
    recentChanges: 24,
    sentiment: 72,
    trendDirection: "up",
  },
  changes: [],
  news: [],
  jobs: [],
  reviews: [],
  socialPosts: [],
};

const mockChanges: Change[] = [
  {
    id: "ch-1",
    competitorId: "comp-1",
    type: "pricing",
    title: "New Enterprise Tier Added ($999/mo)",
    description:
      "Added a new enterprise pricing tier at $999/month featuring AI-powered analytics, custom integrations, and dedicated support.",
    detectedAt: "2026-03-09T14:00:00Z",
    impact: "critical",
    url: "https://acme.com/pricing",
  },
  {
    id: "ch-2",
    competitorId: "comp-1",
    type: "website",
    title: "Homepage Redesigned with SMB Focus",
    description:
      "Complete homepage redesign targeting small business customers. New messaging emphasizes ease of use and quick setup.",
    detectedAt: "2026-03-07T10:00:00Z",
    impact: "high",
  },
  {
    id: "ch-3",
    competitorId: "comp-1",
    type: "product",
    title: "New API v3 Documentation Published",
    description:
      "Published comprehensive API v3 documentation with GraphQL support and improved webhook system.",
    detectedAt: "2026-03-05T16:00:00Z",
    impact: "medium",
  },
  {
    id: "ch-4",
    competitorId: "comp-1",
    type: "messaging",
    title: 'Tagline Changed to "Automate Everything"',
    description:
      'Updated brand tagline from "Streamline Your Workflow" to "Automate Everything" across all pages.',
    detectedAt: "2026-03-03T09:00:00Z",
    impact: "low",
  },
];

const mockNews: NewsItem[] = [
  {
    id: "n-1",
    competitorId: "comp-1",
    title: "Acme Corp Announces AI-Powered Enterprise Suite",
    source: "TechCrunch",
    url: "https://techcrunch.com/acme-enterprise",
    summary:
      "Acme Corp unveiled its new AI-powered enterprise suite, targeting large organizations with automated workflow capabilities.",
    publishedAt: "2026-03-09T12:00:00Z",
    sentiment: "positive",
  },
  {
    id: "n-2",
    competitorId: "comp-1",
    title: "Acme Corp Faces Criticism Over Data Handling Practices",
    source: "The Verge",
    url: "https://theverge.com/acme-data",
    summary:
      "Privacy advocates raised concerns about Acme Corp's data handling practices following a transparency report.",
    publishedAt: "2026-03-06T08:00:00Z",
    sentiment: "negative",
  },
  {
    id: "n-3",
    competitorId: "comp-1",
    title: "Acme Corp Partners with Salesforce for CRM Integration",
    source: "VentureBeat",
    url: "https://venturebeat.com/acme-salesforce",
    summary:
      "New strategic partnership brings native Salesforce integration to Acme Corp's platform.",
    publishedAt: "2026-03-02T14:00:00Z",
    sentiment: "positive",
  },
];

const mockJobs: JobPosting[] = [
  {
    id: "j-1",
    competitorId: "comp-1",
    title: "Senior ML Engineer",
    department: "Engineering",
    location: "San Francisco, CA",
    url: "https://acme.com/careers/ml-engineer",
    postedAt: "2026-03-08T00:00:00Z",
    isNew: true,
  },
  {
    id: "j-2",
    competitorId: "comp-1",
    title: "VP of Sales, Enterprise",
    department: "Sales",
    location: "New York, NY",
    url: "https://acme.com/careers/vp-sales",
    postedAt: "2026-03-07T00:00:00Z",
    isNew: true,
  },
  {
    id: "j-3",
    competitorId: "comp-1",
    title: "Product Designer",
    department: "Design",
    location: "Remote",
    url: "https://acme.com/careers/designer",
    postedAt: "2026-03-05T00:00:00Z",
    isNew: false,
  },
  {
    id: "j-4",
    competitorId: "comp-1",
    title: "DevOps Engineer",
    department: "Engineering",
    location: "San Francisco, CA",
    url: "https://acme.com/careers/devops",
    postedAt: "2026-03-03T00:00:00Z",
    isNew: false,
  },
];

const mockReviews: Review[] = [
  {
    id: "r-1",
    competitorId: "comp-1",
    platform: "G2",
    rating: 4,
    title: "Great platform but pricey for small teams",
    content:
      "Acme Corp has been instrumental in automating our workflows. The new AI features are impressive, though the pricing can be steep for smaller teams.",
    author: "John D.",
    publishedAt: "2026-03-08T00:00:00Z",
    sentiment: "positive",
  },
  {
    id: "r-2",
    competitorId: "comp-1",
    platform: "Capterra",
    rating: 3,
    title: "Good features, needs better support",
    content:
      "The product itself is solid, but customer support has been slow to respond. Took 3 days to get a reply on a critical issue.",
    author: "Sarah M.",
    publishedAt: "2026-03-05T00:00:00Z",
    sentiment: "neutral",
  },
  {
    id: "r-3",
    competitorId: "comp-1",
    platform: "G2",
    rating: 5,
    title: "Best workflow automation tool we've used",
    content:
      "After trying multiple tools, Acme Corp stands out. The integration ecosystem is unmatched and the AI features are game-changing.",
    author: "Mike R.",
    publishedAt: "2026-03-01T00:00:00Z",
    sentiment: "positive",
  },
];

const mockSocial: SocialPost[] = [
  {
    id: "s-1",
    competitorId: "comp-1",
    platform: "twitter",
    content:
      "Excited to announce our new Enterprise AI Suite! Automate complex workflows with the power of AI. Learn more at acme.com/enterprise",
    url: "https://twitter.com/acmecorp/status/123",
    engagement: 847,
    publishedAt: "2026-03-09T15:00:00Z",
  },
  {
    id: "s-2",
    competitorId: "comp-1",
    platform: "linkedin",
    content:
      "We're hiring! Join our growing team - 15 new roles open across engineering, sales, and design. Check out careers at acme.com/careers",
    url: "https://linkedin.com/acme/post/456",
    engagement: 1243,
    publishedAt: "2026-03-07T10:00:00Z",
  },
  {
    id: "s-3",
    competitorId: "comp-1",
    platform: "twitter",
    content:
      "Thrilled to partner with @Salesforce to bring seamless CRM integration to our platform. The future of automation is here.",
    url: "https://twitter.com/acmecorp/status/789",
    engagement: 523,
    publishedAt: "2026-03-02T16:00:00Z",
  },
];

const getSentimentIcon = (sentiment: string) => {
  switch (sentiment) {
    case "positive":
      return <ThumbsUp className="h-3.5 w-3.5 text-emerald-500" />;
    case "negative":
      return <ThumbsDown className="h-3.5 w-3.5 text-red-500" />;
    default:
      return <Minus className="h-3.5 w-3.5 text-yellow-500" />;
  }
};

export default function CompetitorDetailPage() {
  const competitor = mockCompetitor;
  const overview = competitor.overview;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/competitors">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <Avatar className="h-12 w-12 rounded-lg">
          <AvatarFallback className="rounded-lg bg-primary/10 text-primary text-lg">
            {competitor.name.substring(0, 2).toUpperCase()}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{competitor.name}</h1>
            <Badge
              variant="outline"
              className={getStatusColor(competitor.status)}
            >
              {competitor.status}
            </Badge>
          </div>
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <Globe className="h-3.5 w-3.5" />
              {competitor.domain}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              Last scanned{" "}
              {competitor.lastScannedAt
                ? formatRelativeTime(competitor.lastScannedAt)
                : "never"}
            </span>
          </div>
        </div>
        <Button variant="outline" size="sm" className="gap-2">
          <ExternalLink className="h-3.5 w-3.5" />
          Visit Website
        </Button>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="changes">
            Changes ({mockChanges.length})
          </TabsTrigger>
          <TabsTrigger value="news">News ({mockNews.length})</TabsTrigger>
          <TabsTrigger value="jobs">Jobs ({mockJobs.length})</TabsTrigger>
          <TabsTrigger value="reviews">
            Reviews ({mockReviews.length})
          </TabsTrigger>
          <TabsTrigger value="social">
            Social ({mockSocial.length})
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6 mt-6">
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardContent className="p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10">
                    <Users className="h-5 w-5 text-blue-500" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">
                      {overview.employeeCount}
                    </p>
                    <p className="text-xs text-muted-foreground">Employees</p>
                  </div>
                </div>
                {overview.employeeGrowth !== undefined && (
                  <div className="mt-2 flex items-center gap-1 text-xs text-emerald-500">
                    <TrendingUp className="h-3 w-3" />+
                    {overview.employeeGrowth}% this quarter
                  </div>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10">
                    <DollarSign className="h-5 w-5 text-emerald-500" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{overview.funding}</p>
                    <p className="text-xs text-muted-foreground">Funding</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-500/10">
                    <TrendingUp className="h-5 w-5 text-orange-500" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold">
                      {overview.recentChanges}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Changes (30d)
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-500/10">
                    {overview.trendDirection === "up" ? (
                      <TrendingUp className="h-5 w-5 text-purple-500" />
                    ) : (
                      <TrendingDown className="h-5 w-5 text-purple-500" />
                    )}
                  </div>
                  <div>
                    <p className="text-2xl font-bold">
                      {overview.sentiment}%
                    </p>
                    <p className="text-xs text-muted-foreground">Sentiment</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {competitor.description && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">About</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {competitor.description}
                </p>
              </CardContent>
            </Card>
          )}

          {overview.techStack && overview.techStack.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Code className="h-4 w-4" />
                  Tech Stack
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {overview.techStack.map((tech) => (
                    <Badge key={tech} variant="secondary">
                      {tech}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Changes Tab */}
        <TabsContent value="changes" className="mt-6">
          <div className="space-y-3">
            {mockChanges.map((change) => (
              <Card key={change.id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          className={getImpactColor(change.impact)}
                        >
                          {change.impact}
                        </Badge>
                        <Badge variant="secondary">{change.type}</Badge>
                        <span className="text-xs text-muted-foreground">
                          {formatRelativeTime(change.detectedAt)}
                        </span>
                      </div>
                      <h4 className="font-medium">{change.title}</h4>
                      <p className="text-sm text-muted-foreground">
                        {change.description}
                      </p>
                    </div>
                    {change.url && (
                      <a
                        href={change.url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Button variant="ghost" size="icon">
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </a>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* News Tab */}
        <TabsContent value="news" className="mt-6">
          <div className="space-y-3">
            {mockNews.map((item) => (
              <Card key={item.id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        {getSentimentIcon(item.sentiment)}
                        <span className="text-xs font-medium text-muted-foreground">
                          {item.source}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {formatDate(item.publishedAt)}
                        </span>
                      </div>
                      <h4 className="font-medium">{item.title}</h4>
                      <p className="text-sm text-muted-foreground">
                        {item.summary}
                      </p>
                    </div>
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Button variant="ghost" size="icon">
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </a>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Jobs Tab */}
        <TabsContent value="jobs" className="mt-6">
          <div className="space-y-3">
            {mockJobs.map((job) => (
              <Card key={job.id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <Briefcase className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="text-xs font-medium">
                          {job.department}
                        </span>
                        {job.isNew && (
                          <Badge className="bg-primary/10 text-primary border-primary/20">
                            New
                          </Badge>
                        )}
                      </div>
                      <h4 className="font-medium">{job.title}</h4>
                      <div className="flex items-center gap-1 text-sm text-muted-foreground">
                        <MapPin className="h-3 w-3" />
                        {job.location}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-xs text-muted-foreground">
                        {formatRelativeTime(job.postedAt)}
                      </span>
                      <a
                        href={job.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block mt-1"
                      >
                        <Button variant="ghost" size="sm" className="gap-1">
                          View
                          <ExternalLink className="h-3 w-3" />
                        </Button>
                      </a>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Reviews Tab */}
        <TabsContent value="reviews" className="mt-6">
          <div className="space-y-3">
            {mockReviews.map((review) => (
              <Card key={review.id}>
                <CardContent className="p-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getSentimentIcon(review.sentiment)}
                        <Badge variant="secondary">{review.platform}</Badge>
                        <div className="flex items-center gap-0.5">
                          {Array.from({ length: 5 }).map((_, i) => (
                            <div
                              key={i}
                              className={`h-3 w-3 rounded-sm ${
                                i < review.rating
                                  ? "bg-yellow-500"
                                  : "bg-muted"
                              }`}
                            />
                          ))}
                        </div>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {formatDate(review.publishedAt)}
                      </span>
                    </div>
                    <h4 className="font-medium">{review.title}</h4>
                    <p className="text-sm text-muted-foreground">
                      {review.content}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      by {review.author}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Social Tab */}
        <TabsContent value="social" className="mt-6">
          <div className="space-y-3">
            {mockSocial.map((post) => (
              <Card key={post.id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">{post.platform}</Badge>
                        <span className="text-xs text-muted-foreground">
                          {formatRelativeTime(post.publishedAt)}
                        </span>
                      </div>
                      <p className="text-sm">{post.content}</p>
                      <p className="text-xs text-muted-foreground">
                        {post.engagement.toLocaleString()} engagements
                      </p>
                    </div>
                    <a
                      href={post.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Button variant="ghost" size="icon">
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </a>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
