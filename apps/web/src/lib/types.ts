export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  imageUrl?: string;
  plan: "starter" | "professional" | "enterprise";
  createdAt: string;
  updatedAt: string;
}

export interface Competitor {
  id: string;
  name: string;
  domain: string;
  logoUrl?: string;
  description?: string;
  status: "active" | "pending" | "paused" | "error";
  lastScannedAt?: string;
  createdAt: string;
  updatedAt: string;
  changesCount?: number;
  insightsCount?: number;
}

export interface CompetitorDetail extends Competitor {
  overview: CompetitorOverview;
  changes: Change[];
  news: NewsItem[];
  jobs: JobPosting[];
  reviews: Review[];
  socialPosts: SocialPost[];
}

export interface CompetitorOverview {
  employeeCount?: number;
  employeeGrowth?: number;
  funding?: string;
  techStack?: string[];
  recentChanges: number;
  sentiment: number;
  trendDirection: "up" | "down" | "stable";
}

export interface Change {
  id: string;
  competitorId: string;
  type: "website" | "pricing" | "product" | "team" | "messaging";
  title: string;
  description: string;
  detectedAt: string;
  impact: "critical" | "high" | "medium" | "low";
  url?: string;
}

export interface NewsItem {
  id: string;
  competitorId: string;
  title: string;
  source: string;
  url: string;
  summary: string;
  publishedAt: string;
  sentiment: "positive" | "negative" | "neutral";
}

export interface JobPosting {
  id: string;
  competitorId: string;
  title: string;
  department: string;
  location: string;
  url: string;
  postedAt: string;
  isNew: boolean;
}

export interface Review {
  id: string;
  competitorId: string;
  platform: string;
  rating: number;
  title: string;
  content: string;
  author: string;
  publishedAt: string;
  sentiment: "positive" | "negative" | "neutral";
}

export interface SocialPost {
  id: string;
  competitorId: string;
  platform: "twitter" | "linkedin" | "facebook";
  content: string;
  url: string;
  engagement: number;
  publishedAt: string;
}

export interface Briefing {
  id: string;
  title: string;
  weekStart: string;
  weekEnd: string;
  status: "delivered" | "generating" | "scheduled" | "failed";
  executiveSummary?: string;
  insightsCount: number;
  competitorsAnalyzed: number;
  createdAt: string;
}

export interface BriefingDetail extends Briefing {
  executiveSummary: string;
  insights: Insight[];
  predictiveSignals: PredictiveSignal[];
  recommendedPlays: RecommendedPlay[];
}

export interface Insight {
  id: string;
  briefingId: string;
  competitorId: string;
  competitorName: string;
  title: string;
  description: string;
  impact: "critical" | "high" | "medium" | "low";
  confidence: number;
  category: string;
  sources: string[];
}

export interface PredictiveSignal {
  id: string;
  title: string;
  description: string;
  probability: number;
  timeframe: string;
  relatedCompetitors: string[];
}

export interface RecommendedPlay {
  id: string;
  title: string;
  description: string;
  priority: "critical" | "high" | "medium" | "low";
  effort: "low" | "medium" | "high";
  expectedImpact: string;
}

export interface Integration {
  id: string;
  type: "slack" | "email" | "webhook";
  status: "connected" | "disconnected";
  config: Record<string, string>;
  connectedAt?: string;
}

export interface DeliveryPreferences {
  day: string;
  time: string;
  timezone: string;
}

export interface NotificationPreferences {
  emailBriefings: boolean;
  emailAlerts: boolean;
  slackBriefings: boolean;
  slackAlerts: boolean;
  criticalOnly: boolean;
}

export interface PricingTier {
  name: string;
  price: number;
  period: string;
  description: string;
  competitors: string;
  features: string[];
  highlighted: boolean;
  ctaText: string;
  priceId?: string;
}

// ---------------------------------------------------------------------------
// Workspace types
// ---------------------------------------------------------------------------

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  ownerId: string;
  plan: "starter" | "growth" | "enterprise";
  logoUrl?: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface WorkspaceMember {
  id: string;
  workspaceId: string;
  userId: string;
  role: "owner" | "admin" | "member" | "viewer";
  invitedEmail?: string;
  inviteStatus: "pending" | "accepted" | "declined";
  createdAt: string;
}

export interface WorkspaceUsage {
  workspaceId: string;
  competitorsCount: number;
  briefingsGenerated: number;
  alertsSent: number;
  searchesPerformed: number;
  apiCalls: number;
  maxCompetitors: number;
  maxBriefingsPerMonth: number;
  maxAlertsPerMonth: number;
  maxSearchesPerMonth: number;
  periodStart: string;
  updatedAt: string;
}

// ---------------------------------------------------------------------------
// Alert types
// ---------------------------------------------------------------------------

export interface Alert {
  id: string;
  workspaceId: string;
  competitorId?: string;
  alertType: "change" | "news" | "job" | "review" | "social" | "insight";
  severity: "critical" | "high" | "medium" | "low";
  title: string;
  summary?: string;
  significanceScore: number;
  deliveredVia?: string[];
  deliveredAt?: string;
  isRead: boolean;
  createdAt: string;
}

// ---------------------------------------------------------------------------
// Timeline types
// ---------------------------------------------------------------------------

export interface TimelineEvent {
  type: "change" | "news" | "job" | "review" | "social";
  id: string;
  title: string;
  summary?: string;
  severity?: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface CompetitorTimeline {
  competitorId: string;
  competitorName: string;
  events: TimelineEvent[];
  total: number;
}

// ---------------------------------------------------------------------------
// Search types
// ---------------------------------------------------------------------------

export interface SearchResult {
  id: string;
  sourceType: string;
  sourceId: string;
  contentText: string;
  similarity: number;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  total: number;
}

// ---------------------------------------------------------------------------
// Admin types
// ---------------------------------------------------------------------------

export interface AgentHealth {
  agentName: string;
  lastRun?: string;
  status: "running" | "success" | "failed" | "no_runs";
  errorCount: number;
  totalRuns: number;
  avgDurationSeconds?: number;
  lastError?: string;
}

export interface AuditLogEntry {
  id: string;
  workspaceId?: string;
  userId?: string;
  action: string;
  resource: string;
  resourceId?: string;
  metadata?: Record<string, unknown>;
  ipAddress?: string;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Referral types
// ---------------------------------------------------------------------------

export interface Referral {
  id: string;
  referralCode: string;
  referredEmail?: string;
  status: "pending" | "signed_up" | "converted" | "rewarded";
  rewardApplied: boolean;
  createdAt: string;
}
