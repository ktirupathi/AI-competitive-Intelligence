/**
 * Zod validation schemas for frontend input validation.
 *
 * These mirror the backend Pydantic schemas to provide
 * client-side validation before API calls.
 */
import { z } from "zod";

// ---------------------------------------------------------------------------
// Competitor schemas
// ---------------------------------------------------------------------------

const domainRegex = /^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$/;

export const competitorCreateSchema = z.object({
  name: z
    .string()
    .min(1, "Competitor name is required")
    .max(255, "Name must be 255 characters or fewer"),
  domain: z
    .string()
    .min(1, "Domain is required")
    .max(255, "Domain must be 255 characters or fewer")
    .regex(domainRegex, "Please enter a valid domain (e.g., example.com)"),
  description: z.string().max(2000).optional().nullable(),
  industry: z.string().max(255).optional().nullable(),
  track_website: z.boolean().default(true),
  track_news: z.boolean().default(true),
  track_jobs: z.boolean().default(true),
  track_reviews: z.boolean().default(true),
  track_social: z.boolean().default(true),
});

export const competitorUpdateSchema = competitorCreateSchema.partial();

export type CompetitorCreateInput = z.infer<typeof competitorCreateSchema>;
export type CompetitorUpdateInput = z.infer<typeof competitorUpdateSchema>;

// ---------------------------------------------------------------------------
// Search schemas
// ---------------------------------------------------------------------------

export const searchSchema = z.object({
  query: z
    .string()
    .min(1, "Search query is required")
    .max(500, "Query must be 500 characters or fewer"),
  source_type: z
    .enum(["insight", "briefing", "news_item", "snapshot", "review", "social_post"])
    .optional()
    .nullable(),
  limit: z.number().int().min(1).max(100).default(20),
});

export type SearchInput = z.infer<typeof searchSchema>;

// ---------------------------------------------------------------------------
// Workspace schemas
// ---------------------------------------------------------------------------

export const workspaceCreateSchema = z.object({
  name: z
    .string()
    .min(1, "Workspace name is required")
    .max(255, "Name must be 255 characters or fewer"),
  plan: z.enum(["starter", "growth", "enterprise"]).default("starter"),
});

export const workspaceInviteSchema = z.object({
  email: z.string().email("Please enter a valid email address").max(320),
  role: z.enum(["admin", "member", "viewer"]).default("member"),
});

export type WorkspaceCreateInput = z.infer<typeof workspaceCreateSchema>;
export type WorkspaceInviteInput = z.infer<typeof workspaceInviteSchema>;

// ---------------------------------------------------------------------------
// Webhook payload validation
// ---------------------------------------------------------------------------

export const webhookConfigSchema = z.object({
  url: z.string().url("Please enter a valid URL"),
  secret: z.string().min(16, "Secret must be at least 16 characters").optional(),
});

export type WebhookConfigInput = z.infer<typeof webhookConfigSchema>;

// ---------------------------------------------------------------------------
// Settings schemas
// ---------------------------------------------------------------------------

export const settingsUpdateSchema = z.object({
  timezone: z.string().max(64).optional(),
  briefing_frequency: z.enum(["daily", "weekly", "monthly"]).optional(),
  notification_prefs: z
    .object({
      emailBriefings: z.boolean().optional(),
      emailAlerts: z.boolean().optional(),
      slackBriefings: z.boolean().optional(),
      slackAlerts: z.boolean().optional(),
      criticalOnly: z.boolean().optional(),
    })
    .optional(),
});

export type SettingsUpdateInput = z.infer<typeof settingsUpdateSchema>;

// ---------------------------------------------------------------------------
// Export schemas
// ---------------------------------------------------------------------------

export const exportRequestSchema = z.object({
  format: z.enum(["pdf", "markdown", "notion"]),
  briefing_id: z.string().uuid().optional(),
  competitor_id: z.string().uuid().optional(),
});

export type ExportRequestInput = z.infer<typeof exportRequestSchema>;
