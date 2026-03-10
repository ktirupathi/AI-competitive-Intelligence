# Scout AI - Competitive Intelligence Platform

An AI-powered competitive intelligence platform that automatically monitors competitors across multiple data sources, synthesizes signals into strategic insights, and delivers actionable briefings via email, Slack, and webhooks.

Built with a **LangGraph multi-agent pipeline** on the backend, a **FastAPI + Celery** API layer, and a **Next.js 14** dashboard frontend.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
  - [High-Level Architecture Diagram](#high-level-architecture-diagram)
  - [Agent Pipeline (LangGraph)](#agent-pipeline-langgraph)
  - [Backend API](#backend-api)
  - [Frontend Dashboard](#frontend-dashboard)
  - [Infrastructure](#infrastructure)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Setup](#environment-setup)
  - [Running with Docker Compose](#running-with-docker-compose)
  - [Running Locally (Without Docker)](#running-locally-without-docker)
- [Configuration](#configuration)
  - [Required API Keys](#required-api-keys)
  - [Pipeline Tuning](#pipeline-tuning)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Deployment](#deployment)
- [License](#license)

---

## Overview

Scout AI continuously monitors your competitors by:

1. **Scraping websites** for pricing, product, and messaging changes
2. **Searching news** for press mentions, funding rounds, and acquisitions
3. **Tracking job postings** to detect hiring patterns and strategic direction
4. **Analyzing reviews** on G2 and Capterra for sentiment and themes
5. **Monitoring social media** on LinkedIn and Twitter/X for engagement and announcements

All collected signals are synthesized by Claude (Anthropic) into a structured briefing containing an executive summary, scored insights, predictive signals, and prioritized recommended plays. Briefings are delivered automatically via email, Slack, or webhook.

---

## Architecture

### High-Level Architecture Diagram

```
                         +-------------------+
                         |   Next.js 14 UI   |  (port 3000)
                         |  Clerk Auth, Stripe|
                         +---------+---------+
                                   |
                                   | REST API calls
                                   v
                         +---------+---------+
                         |   FastAPI Server   |  (port 8000)
                         |  Routes, Services  |
                         +---------+---------+
                            |             |
                   +--------+             +--------+
                   v                               v
          +--------+--------+             +--------+--------+
          | PostgreSQL 16   |             |   Redis 7       |
          | + pgvector ext  |             |  (task broker)  |
          +--------+--------+             +--------+--------+
                                                   |
                                          +--------+--------+
                                          | Celery Workers  |
                                          | + Celery Beat   |
                                          +--------+--------+
                                                   |
                                          +--------+--------+
                                          | LangGraph Agent |
                                          |    Pipeline     |
                                          +-----------------+
                                            |  |  |  |  |
                           +----------------+--+--+--+--+----------------+
                           v       v       v       v       v             v
                        Web     News     Job    Review  Social      Synthesis
                       Monitor  Agent   Agent   Agent   Agent        Agent
                                                                       |
                                                                       v
                                                                   Delivery
                                                                    Agent
                                                                   /  |  \
                                                                  v   v   v
                                                              Email Slack Webhook
```

### Agent Pipeline (LangGraph)

The core intelligence engine is a **LangGraph StateGraph** that orchestrates six specialized agents. The pipeline supports two execution modes:

**Parallel mode (default):** All five collection agents run concurrently in a fan-out pattern, then results merge into synthesis and delivery sequentially.

```
START -> [web_monitor, news, job, review, social] (parallel) -> synthesis -> delivery -> END
```

**Sequential mode:** Each agent runs one after the other. Useful for debugging or when API rate limits are tight.

```
START -> web_monitor -> news -> jobs -> reviews -> social -> synthesis -> delivery -> END
```

#### Agent Descriptions

| Agent | File | Purpose | Data Sources |
|---|---|---|---|
| **Web Monitor** | `agents/web_monitor_agent.py` | Scrapes competitor websites, detects content changes via SHA-256 hashing, classifies significance using Claude Haiku | Firecrawl API (primary), plain HTTP (fallback) |
| **News** | `agents/news_agent.py` | Searches for competitor mentions, scores relevance and sentiment | Serper.dev Google Search API |
| **Job Posting** | `agents/job_agent.py` | Monitors careers pages, identifies hiring patterns and strategic signals | Careers page scraping |
| **Review** | `agents/review_agent.py` | Extracts review sentiment, pros/cons, and recurring themes | G2, Capterra |
| **Social** | `agents/social_agent.py` | Classifies post types and tracks engagement metrics | LinkedIn, Twitter/X |
| **Synthesis** | `agents/synthesis_agent.py` | Correlates all signals into insights, predictions, and recommendations | Claude Sonnet (all collected data) |
| **Delivery** | `agents/delivery_agent.py` | Delivers formatted briefings via configured channels | Resend (email), Slack Web API, Webhooks |

#### Pipeline State

A typed `PipelineState` (defined in `agents/state.py`) flows through the entire graph. Each agent reads specific keys and writes back its results. Key state fields:

- **Input:** `competitors`, `user_email`, `slack_channel`, `webhook_url`, `previous_snapshots`
- **Collection:** `snapshots`, `changes`, `news_items`, `job_postings`, `reviews`, `social_posts`
- **Synthesis:** `insights`, `briefing` (executive summary, top insights, predictive signals, recommended plays, competitor summaries)
- **Delivery:** `delivery_results`
- **Metadata:** `run_id`, `started_at`, `finished_at`, `errors`

#### Prompt Management

All Claude prompts are centralized in `agents/prompts.py` for easy versioning and testing. This includes prompts for change classification, news analysis, job analysis, review sentiment, social classification, and briefing synthesis.

### Backend API

The backend is a **FastAPI** application serving RESTful endpoints:

| Route Group | Prefix | Purpose |
|---|---|---|
| Auth | `/api/auth` | Clerk webhook handling, user sync |
| Competitors | `/api/competitors` | CRUD for tracked competitors |
| Briefings | `/api/briefings` | View and manage generated briefings |
| Insights | `/api/insights` | Browse scored insights |
| Integrations | `/api/integrations` | Manage Slack, email, webhook configs |
| Settings | `/api/settings` | User preferences (schedule, timezone, notifications) |
| Billing | `/api/billing` | Stripe subscription management |
| Health | `/health` | Health check for load balancers |

Background task scheduling is handled by **Celery** with **Redis** as the broker:
- **Celery Worker:** Executes the LangGraph agent pipeline and briefing generation tasks
- **Celery Beat:** Triggers scheduled monitoring runs based on user-configured briefing schedules

### Frontend Dashboard

The frontend is a **Next.js 14** application (App Router) with:

- **Clerk** for authentication (sign-in/sign-up)
- **Stripe** for billing and subscription plans
- **Radix UI** + **Tailwind CSS** for the component library
- **Recharts** for data visualization

Dashboard pages:

| Page | Route | Description |
|---|---|---|
| Dashboard | `/dashboard` | Overview with key metrics and recent activity |
| Competitors | `/competitors` | List and manage tracked competitors |
| Competitor Detail | `/competitors/[id]` | Deep dive into a single competitor's signals |
| Briefings | `/briefings` | Browse all generated briefings |
| Briefing Detail | `/briefings/[id]` | Full briefing with insights, predictions, plays |
| Integrations | `/integrations` | Configure Slack, email, webhook delivery |
| Settings | `/settings` | Account preferences, notification schedule |

### Infrastructure

- **Docker Compose** for local development (PostgreSQL + pgvector, Redis, API, Celery worker, Celery beat, Web)
- **Terraform** (AWS) for production deployment:
  - **RDS PostgreSQL 16** with encryption and automated backups
  - **ElastiCache Redis 7** for task queuing
  - **S3** with versioning and encryption for snapshot/screenshot storage
  - **VPC** with private subnets for database and cache isolation
- **Nginx** reverse proxy configuration included (`infra/docker/`)

---

## Project Structure

```
AI-competitive-Intelligence/
├── agents/                          # LangGraph agent pipeline
│   ├── __init__.py
│   ├── config.py                    # Centralized settings (env vars + defaults)
│   ├── pipeline.py                  # LangGraph StateGraph construction & runner
│   ├── state.py                     # Typed state schema (PipelineState, data models)
│   ├── prompts.py                   # All Claude prompt templates
│   ├── web_monitor_agent.py         # Website scraping & change detection
│   ├── news_agent.py                # News search & relevance scoring
│   ├── job_agent.py                 # Job posting monitoring
│   ├── review_agent.py              # G2/Capterra review analysis
│   ├── social_agent.py              # LinkedIn/Twitter monitoring
│   ├── synthesis_agent.py           # Signal correlation & briefing generation
│   └── delivery_agent.py            # Email, Slack, webhook delivery
│
├── apps/
│   ├── api/                         # FastAPI backend
│   │   ├── Dockerfile
│   │   ├── main.py                  # App entry point (CORS, Sentry, Langfuse)
│   │   ├── config.py                # API settings (pydantic-settings)
│   │   ├── database.py              # SQLAlchemy async engine setup
│   │   ├── celery_app.py            # Celery configuration
│   │   ├── deps.py                  # FastAPI dependency injection
│   │   ├── requirements.txt         # Python dependencies
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── briefing.py
│   │   │   ├── change.py
│   │   │   ├── competitor.py
│   │   │   ├── embedding.py
│   │   │   ├── insight.py
│   │   │   ├── integration.py
│   │   │   ├── job_posting.py
│   │   │   ├── news.py
│   │   │   ├── review.py
│   │   │   ├── snapshot.py
│   │   │   ├── social_post.py
│   │   │   └── user.py
│   │   ├── routes/                  # API route handlers
│   │   │   ├── auth.py
│   │   │   ├── billing.py
│   │   │   ├── briefings.py
│   │   │   ├── competitors.py
│   │   │   ├── insights.py
│   │   │   ├── integrations.py
│   │   │   └── settings.py
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   │   ├── billing.py
│   │   │   ├── briefing.py
│   │   │   ├── competitor.py
│   │   │   ├── insight.py
│   │   │   ├── integration.py
│   │   │   └── settings.py
│   │   ├── services/                # Business logic layer
│   │   │   ├── briefing_service.py
│   │   │   ├── competitor_service.py
│   │   │   ├── email_service.py
│   │   │   ├── slack_service.py
│   │   │   └── stripe_service.py
│   │   └── tasks/                   # Celery async tasks
│   │       ├── briefing_generation.py
│   │       └── monitoring.py
│   │
│   └── web/                         # Next.js 14 frontend
│       ├── Dockerfile
│       ├── package.json
│       ├── next.config.js
│       ├── tailwind.config.ts
│       ├── tsconfig.json
│       └── src/
│           ├── app/                 # App Router pages
│           │   ├── layout.tsx
│           │   ├── page.tsx         # Landing page
│           │   ├── globals.css
│           │   ├── sign-in/
│           │   ├── sign-up/
│           │   └── (dashboard)/     # Authenticated layout group
│           │       ├── layout.tsx
│           │       ├── dashboard/
│           │       ├── competitors/
│           │       ├── briefings/
│           │       ├── integrations/
│           │       └── settings/
│           ├── components/          # React components
│           │   ├── sidebar.tsx
│           │   ├── topbar.tsx
│           │   ├── competitor-card.tsx
│           │   ├── briefing-card.tsx
│           │   ├── insight-card.tsx
│           │   ├── pricing-card.tsx
│           │   ├── add-competitor-dialog.tsx
│           │   └── ui/              # Radix UI primitives
│           ├── lib/
│           │   ├── api.ts           # API client
│           │   ├── types.ts         # TypeScript type definitions
│           │   └── utils.ts         # Utility functions
│           └── middleware.ts        # Clerk auth middleware
│
├── database/
│   └── migrations/
│       └── 001_initial.sql          # Full PostgreSQL schema (pgvector)
│
├── infra/
│   ├── docker/
│   │   ├── Dockerfile.nginx
│   │   └── nginx.conf
│   └── terraform/
│       └── main.tf                  # AWS infrastructure (RDS, ElastiCache, S3, VPC)
│
├── docker-compose.yml               # Local development orchestration
├── .env.example                     # Environment variable template
├── .gitignore
└── LICENSE                          # MIT License
```

---

## Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| **Python 3.11** | Runtime |
| **LangGraph** | Multi-agent pipeline orchestration |
| **Anthropic Claude** | Sonnet for synthesis, Haiku for classification |
| **FastAPI** | REST API framework |
| **SQLAlchemy 2.0** (async) | ORM with asyncpg driver |
| **Celery 5** | Distributed task queue |
| **Redis 7** | Task broker and caching |
| **PostgreSQL 16 + pgvector** | Database with vector embeddings |
| **Firecrawl** | Web scraping service |
| **Serper.dev** | Google Search API for news |
| **Playwright** | Browser automation for advanced scraping |
| **Sentry** | Error tracking and performance monitoring |
| **Langfuse** | LLM observability and tracing |

### Frontend
| Technology | Purpose |
|---|---|
| **Next.js 14** (App Router) | React framework |
| **TypeScript** | Type safety |
| **Tailwind CSS** | Utility-first styling |
| **Radix UI** | Accessible component primitives |
| **Recharts** | Data visualization |
| **Clerk** | Authentication |
| **Stripe** | Subscription billing |

### Infrastructure
| Technology | Purpose |
|---|---|
| **Docker + Docker Compose** | Containerization |
| **Terraform** | Infrastructure as Code (AWS) |
| **Nginx** | Reverse proxy |
| **AWS RDS** | Managed PostgreSQL |
| **AWS ElastiCache** | Managed Redis |
| **AWS S3** | Object storage |

---

## Getting Started

### Prerequisites

- **Docker** and **Docker Compose** (recommended for quickest setup)
- Or, for local development:
  - Python 3.11+
  - Node.js 18+
  - PostgreSQL 16 with the `pgvector` and `uuid-ossp` extensions
  - Redis 7

### Environment Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/your-org/AI-competitive-Intelligence.git
   cd AI-competitive-Intelligence
   ```

2. Copy the environment template and fill in your API keys:

   ```bash
   cp .env.example .env
   ```

3. Edit `.env` with your actual credentials (see [Required API Keys](#required-api-keys) below).

### Running with Docker Compose

This is the fastest way to get the full stack running:

```bash
# Start all services (PostgreSQL, Redis, API, Celery worker, Celery beat, Web)
docker compose up --build

# Or run in detached mode
docker compose up --build -d
```

Once running:
- **Frontend dashboard:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API docs (dev mode):** http://localhost:8000/api/docs
- **Health check:** http://localhost:8000/health

To stop all services:

```bash
docker compose down
```

To stop and remove all data volumes:

```bash
docker compose down -v
```

### Running Locally (Without Docker)

#### 1. Start PostgreSQL and Redis

Make sure PostgreSQL 16 and Redis 7 are running locally. Create the database:

```sql
CREATE DATABASE scout_ai;
\c scout_ai
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
```

Run the initial migration:

```bash
psql -U scout -d scout_ai -f database/migrations/001_initial.sql
```

#### 2. Start the Backend API

```bash
cd apps/api
pip install -r requirements.txt
playwright install chromium

# Start the API server
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Start Celery Workers

In separate terminals:

```bash
# Worker (processes pipeline tasks)
celery -A apps.api.celery_app worker --loglevel=info --concurrency=4

# Beat scheduler (triggers scheduled runs)
celery -A apps.api.celery_app beat --loglevel=info
```

#### 4. Start the Frontend

```bash
cd apps/web
npm install
npm run dev
```

The frontend will be available at http://localhost:3000.

---

## Configuration

### Required API Keys

At minimum, the following keys are needed for core functionality:

| Variable | Service | Required For | How to Obtain |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic | All AI analysis and synthesis | [console.anthropic.com](https://console.anthropic.com) |
| `CLERK_SECRET_KEY` | Clerk | User authentication | [clerk.com](https://clerk.com) |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk | Frontend auth | Same Clerk dashboard |

Optional but recommended for full functionality:

| Variable | Service | Required For |
|---|---|---|
| `FIRECRAWL_API_KEY` | Firecrawl | High-quality web scraping (falls back to plain HTTP) |
| `SEARCH_API_KEY` | Serper.dev | News search via Google |
| `RESEND_API_KEY` | Resend | Email briefing delivery |
| `SLACK_BOT_TOKEN` | Slack | Slack briefing delivery |
| `STRIPE_SECRET_KEY` | Stripe | Subscription billing |
| `SENTRY_DSN` | Sentry | Error tracking |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | Langfuse | LLM observability |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | AWS | S3 snapshot storage |

### Pipeline Tuning

These settings in `agents/config.py` control pipeline behavior:

| Setting | Default | Description |
|---|---|---|
| `max_concurrent_competitors` | 5 | Number of competitors processed in parallel |
| `min_change_significance` | 0.3 | Minimum significance score to keep a detected change (0.0-1.0) |
| `snapshot_ttl_hours` | 24 | Hours before a cached snapshot is considered stale |
| `agent_max_retries` | 3 | Retry attempts per agent before marking as failed |
| `agent_retry_delay_seconds` | 2.0 | Base delay between retries (multiplied by attempt number) |

Claude model configuration:

| Setting | Default | Description |
|---|---|---|
| `synthesis_model` | `claude-sonnet-4-20250514` | Model used for briefing synthesis |
| `classification_model` | `claude-haiku-4-5-20251001` | Model used for classification tasks (change, news, reviews) |
| `max_tokens_synthesis` | 8192 | Max output tokens for synthesis |
| `temperature_synthesis` | 0.3 | Temperature for synthesis (lower = more focused) |
| `temperature_classification` | 0.1 | Temperature for classification (low for consistency) |

---

## API Reference

The API is served under the `/api/v1` prefix by default. When running in development mode (`debug=True`), interactive documentation is available:

- **Swagger UI:** http://localhost:8000/api/docs
- **ReDoc:** http://localhost:8000/api/redoc
- **OpenAPI JSON:** http://localhost:8000/api/openapi.json

### Key Endpoints

```
GET    /health                    # Health check

POST   /api/auth/webhook          # Clerk webhook for user sync
GET    /api/competitors           # List tracked competitors
POST   /api/competitors           # Add a new competitor
GET    /api/competitors/:id       # Get competitor details
DELETE /api/competitors/:id       # Remove a competitor

GET    /api/briefings             # List briefings
GET    /api/briefings/:id         # Get full briefing
POST   /api/briefings/generate    # Trigger on-demand briefing generation

GET    /api/insights              # List insights (filterable)

GET    /api/integrations          # List configured integrations
PUT    /api/integrations/:provider # Update integration config

GET    /api/settings              # Get user settings
PUT    /api/settings              # Update user settings

POST   /api/billing/checkout      # Create Stripe checkout session
POST   /api/billing/webhook       # Stripe webhook handler
GET    /api/billing/portal        # Stripe customer portal URL
```

---

## Database Schema

The PostgreSQL database uses the `pgvector` extension for embedding storage and similarity search. Key tables:

| Table | Purpose |
|---|---|
| `users` | User accounts (synced from Clerk), plan info, notification preferences |
| `competitors` | Tracked competitors per user (name, domain, metadata) |
| `snapshots` | Website content captures with content hashes |
| `changes` | Detected content diffs with significance scores |
| `news_items` | News articles with relevance and sentiment scores |
| `job_postings` | Job listings with department and seniority tracking |
| `reviews` | Product reviews from G2/Capterra with sentiment |
| `social_posts` | Social media posts with engagement metrics |
| `insights` | AI-generated scored insights |
| `briefings` | Complete briefing documents (executive summary, plays, predictions) |
| `embeddings` | Vector embeddings (1536-dim) for semantic search across all content types |
| `integrations` | Per-user delivery channel configurations |

The full schema is in `database/migrations/001_initial.sql`.

---

## Deployment

### Production (AWS with Terraform)

1. Configure Terraform backend and variables:

   ```bash
   cd infra/terraform
   ```

2. Set the required variables (or create a `terraform.tfvars` file):

   ```hcl
   aws_region  = "us-east-1"
   environment = "production"
   db_password = "your-secure-password"
   ```

3. Deploy infrastructure:

   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

   This provisions:
   - VPC with private subnets
   - RDS PostgreSQL 16 (encrypted, 7-day backups)
   - ElastiCache Redis 7
   - S3 bucket (versioned, encrypted, no public access)

4. Build and deploy application containers to your preferred container orchestrator (ECS, EKS, or similar) using the Dockerfiles in `apps/api/Dockerfile` and `apps/web/Dockerfile`.

### Docker (Self-Hosted)

For self-hosted deployments, use the included `docker-compose.yml` with production-appropriate environment variables and an Nginx reverse proxy (config in `infra/docker/nginx.conf`).

---

## Database Migrations

Scout AI uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations.

### Setup

Alembic reads `DATABASE_URL` from the environment. Set it before running any commands:

```bash
export DATABASE_URL="postgresql+asyncpg://scout:scout_secret@localhost:5432/scout_ai"
```

### Common Commands

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration (autogenerate from model changes)
alembic revision --autogenerate -m "description_of_change"

# Downgrade one revision
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history --verbose
```

### Docker

The API service in `docker-compose.yml` automatically runs `alembic upgrade head` before starting, ensuring the database schema is always up to date.

---

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

Copyright (c) 2026 Venkata_KT
