# FairFound Junior Frontend Developer Analysis System

AI-powered analysis and benchmarking system specifically designed for junior frontend developers (0-2 years experience).

## Overview

This system analyzes junior frontend developer profiles and provides:
- Skill assessment with tier classification
- GitHub activity scoring
- Benchmark comparison against 200+ synthetic profiles
- Personalized improvement recommendations
- Market positioning insights

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Analysis Pipeline                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ Form Data│  │ CV Parser│  │ GitHub   │                  │
│  │ (Required)│  │ (Optional)│  │ Collector│                 │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
│       │             │             │                         │
│       └─────────────┼─────────────┘                         │
│                     ▼                                        │
│           ┌─────────────────┐                               │
│           │ Feature Scoring │                               │
│           │ - Skills (35%)  │                               │
│           │ - GitHub (25%)  │                               │
│           │ - Portfolio(20%)│                               │
│           │ - Experience(15%)│                              │
│           │ - Momentum (5%) │                               │
│           └────────┬────────┘                               │
│                    ▼                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ Overall  │  │ Benchmark│  │ LLM      │                  │
│  │ Score    │→ │ Compare  │→ │ Evaluate │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
│                    ▼                                         │
│           ┌─────────────────┐                               │
│           │ Results + Tips  │                               │
│           └─────────────────┘                               │
└─────────────────────────────────────────────────────────────┘
```

## API Endpoints

### Main Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/onboard/` | POST | Submit profile for analysis |
| `/api/agents/jobs/` | GET | List your analysis jobs |
| `/api/agents/jobs/<id>/` | GET | Get job status |
| `/api/agents/jobs/<id>/analysis/` | GET | Get detailed results |
| `/api/agents/jobs/<id>/regenerate/` | POST | Re-run analysis |
| `/api/agents/quick-analyze/` | POST | Quick sync analysis |
| `/api/agents/benchmarks/` | GET | Get benchmark data |

### Admin Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/admin/seed-benchmarks/` | POST | Seed benchmark data |
| `/api/agents/admin/review/queue/` | GET | Review queue |
| `/api/agents/admin/review/<id>/action/` | POST | Review action |

## Scoring System

### Weights (Optimized for Juniors)

| Factor | Weight | Why |
|--------|--------|-----|
| Skills | 35% | Core competency indicator |
| GitHub | 25% | Shows initiative and practice |
| Portfolio | 20% | Demonstrates practical ability |
| Experience | 15% | Less weight since they're junior |
| Momentum | 5% | Growth trajectory |

### Skill Tiers

Skills are categorized and weighted:

- **Essential** (1.0x): HTML, CSS, JavaScript
- **Framework** (1.2x): React, Vue, Angular, Svelte
- **TypeScript** (1.3x): Highly valued differentiator
- **Testing** (1.1x): Jest, Cypress, RTL
- **Modern CSS** (0.8x): Tailwind, Sass, Styled-components
- **Tooling** (0.7x): Git, npm, Webpack, Vite

### Result Tiers

| Tier | Score Range | Description |
|------|-------------|-------------|
| Strong Junior | 70%+ | Ready for junior roles |
| Competent | 50-69% | Solid foundation |
| Developing | 35-49% | Building skills |
| Early Stage | <35% | Just starting |

## Quick Start

### 1. Seed Benchmark Data

```bash
python manage.py seed_benchmarks
```

### 2. Submit for Analysis

```bash
curl -X POST /api/agents/onboard/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "skills": ["html", "css", "javascript", "react"],
    "experience_years": 1,
    "github_username": "johndoe"
  }'
```

### 3. Quick Analysis (Synchronous)

```bash
curl -X POST /api/agents/quick-analyze/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "skills": ["html", "css", "javascript", "react", "typescript"],
    "experience_years": 1.5,
    "github_username": "johndoe"
  }'
```

## Response Example

```json
{
  "overall_score": 0.58,
  "tier": "Competent",
  "percentile": 62,
  "breakdown": {
    "skill_strength": {
      "raw_score": 0.65,
      "level": "solid",
      "details": {
        "matched_skills": {
          "essential": ["html", "css", "javascript"],
          "framework": ["react"],
          "typescript": ["typescript"]
        }
      }
    },
    "github_activity": {
      "raw_score": 0.45,
      "level": "regular"
    }
  },
  "improvements": [
    {
      "priority": 1,
      "area": "GitHub",
      "action": "Commit code daily and build 2-3 public projects",
      "impact": "high"
    }
  ],
  "benchmark": {
    "user_percentile": 62,
    "tier": "Competitive",
    "in_demand_skills": ["react", "typescript", "tailwind"]
  }
}
```

## Benchmark Data

Based on:
- Stack Overflow Developer Survey 2024
- Synthetic Freelance Platform Dataset (Kaggle)

200 synthetic junior frontend profiles with realistic distributions:
- 20% Beginner tier
- 35% Learning tier
- 30% Competent tier
- 15% Strong Junior tier

## Running Tests

```bash
python manage.py test apps.agents
```

## Celery Setup (Optional)

For async processing:

```bash
# Start Redis
redis-server

# Start Celery worker
celery -A fairfound worker -l info
```

Without Celery, analysis runs synchronously.
