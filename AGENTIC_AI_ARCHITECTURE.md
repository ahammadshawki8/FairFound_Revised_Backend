# FairFound Agentic AI Architecture

A complete multi-agent AI system for evaluating and guiding junior frontend developers.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INPUT                                     │
│          (Form Data, CV/Resume PDF, GitHub Username, Portfolio URL)         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT ORCHESTRATOR                                  │
│    Coordinates pipeline execution with retry logic and event emission       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────┬───────────┼───────────┬───────────────┐
        ▼               ▼           ▼           ▼               ▼
┌───────────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
│  CV Parser    │ │   Form    │ │  GitHub   │ │ Portfolio │ │  (Future) │
│  (AI + Rules) │ │ Processor │ │ Collector │ │ Collector │ │  Agents   │
└───────────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│    Skill      │          │    GitHub     │          │   Portfolio   │
│   Scorer      │          │    Scorer     │          │    Scorer     │
│   (35%)       │          │    (25%)      │          │    (20%)      │
└───────────────┘          └───────────────┘          └───────────────┘
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    ▼
                        ┌───────────────────┐
                        │ Score Aggregator  │
                        │  + Experience     │
                        │    Scorer (15%)   │
                        └───────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │  Benchmark  │ │  LLM Judge  │ │ Improvement │
            │    Agent    │ │  (Gemini)   │ │  Generator  │
            └─────────────┘ └─────────────┘ └─────────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPPORTING SYSTEMS                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Monitoring │  │   Memory    │  │  Adaptive   │  │  Explainer  │         │
│  │    Agent    │  │   System    │  │  Learning   │  │    Agent    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DOWNSTREAM SERVICES                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Roadmap   │  │ AI Chatbot  │  │   Human     │  │ AI Insights │         │
│  │  Generator  │  │  (Gemini)   │  │   Review    │  │  Generator  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Agent Inventory

### Data Collection Agents

| Agent | File | Purpose |
|-------|------|---------|
| CVParserAgent | `registered_agents.py` | Parses CV/Resume PDFs using AI + rule-based extraction |
| FormProcessorAgent | `registered_agents.py` | Validates and normalizes user form input |
| GitHubCollectorAgent | `registered_agents.py` | Fetches GitHub metrics via API |
| PortfolioCollectorAgent | `registered_agents.py` | Scrapes portfolio website metadata |

### Scoring Agents

| Agent | Weight | Purpose |
|-------|--------|---------|
| SkillScoringAgent | 35% | Scores technical skills using tiered rubrics |
| GitHubScoringAgent | 25% | Scores GitHub activity and contributions |
| PortfolioScoringAgent | 20% | Scores portfolio quality and projects |
| ExperienceScoringAgent | 15% | Scores experience level (0-2 years scale) |
| Learning Momentum | 5% | Growth trajectory indicator |

### Evaluation Agents

| Agent | Purpose |
|-------|---------|
| ScoreAggregatorAgent | Computes weighted overall score and tier |
| BenchmarkAgent | Compares against synthetic cohort data |
| LLMJudgeAgent | Iterative AI evaluation with confidence loop |
| ImprovementGeneratorAgent | Generates prioritized action items |

---

## Infrastructure Components

### 1. Agent Registry (`registry.py`)

Central registration and discovery system for all agents.

```python
from apps.agents.registry import AgentRegistry

# Register an agent
@AgentRegistry.register(
    agent_id='skill_scorer',
    capabilities=['scoring', 'skills'],
    dependencies=['form_processor']
)
class SkillScoringAgent(ScoringAgent):
    pass

# Discover agents by capability
scoring_agents = AgentRegistry.discover('scoring')

# Get execution order (topologically sorted)
order = AgentRegistry.get_execution_order()

# Get health report
health = AgentRegistry.get_health_report()
```

### 2. Agent Orchestrator (`orchestrator.py`)

Coordinates pipeline execution with dependency awareness and retry logic.

```python
from apps.agents.orchestrator import get_orchestrator, AgentContext

orchestrator = get_orchestrator()

result = orchestrator.execute_pipeline(
    job_id=123,
    user_id=456,
    input_data={
        'form_fields': {'skills': ['react', 'typescript']},
        'github_username': 'johndoe'
    }
)

# Result contains all agent outputs
print(result.status)  # PipelineStatus.COMPLETED
print(result.agents_succeeded)  # 11
print(result.total_time)  # 2.5 seconds
```

Features:
- Dependency-aware execution ordering
- Retry with exponential backoff
- Fallback handling
- Event emission for monitoring

### 3. Event Bus (`events.py`)

Event-driven communication between agents.

```python
from apps.agents.events import get_event_bus, EventTypes, on

bus = get_event_bus()

# Subscribe to events
@on(EventTypes.LOW_CONFIDENCE)
def handle_low_confidence(event):
    print(f"Low confidence detected: {event.data}")

# Publish events
bus.publish(AgentEvent(
    event_type=EventTypes.SCORE_CALCULATED,
    agent_id='score_aggregator',
    job_id=123,
    data={'score': 0.65, 'confidence': 0.75}
))

# Get event history
history = bus.get_history(event_type='score_calculated', limit=50)
```

Standard Event Types:
- `pipeline_started`, `pipeline_completed`, `pipeline_failed`
- `agent_started`, `agent_completed`, `agent_failed`
- `score_calculated`, `low_confidence`, `high_confidence`
- `review_requested`, `review_completed`
- `feedback_received`, `weights_updated`
- `anomaly_detected`, `performance_degraded`

### 4. Agent Memory (`memory.py`)

Persistent memory for learning from past interactions.

```python
from apps.agents.memory import get_memory

memory = get_memory()

# Store an interaction
entry_id = memory.store_interaction(
    agent_id='llm_judge',
    context={'skills': ['react'], 'tier': 'Developing'},
    decision={'score': 0.55, 'strengths': [...]},
    confidence=0.82
)

# Record outcome (from human review)
memory.record_outcome(entry_id, outcome='approved', feedback={...})

# Find similar past cases
similar = memory.retrieve_similar_cases(
    context={'skills': ['react', 'vue'], 'tier': 'Developing'},
    limit=5
)

# Get agent accuracy
accuracy = memory.get_agent_accuracy('llm_judge')
# {'accuracy': 0.87, 'approved': 45, 'rejected': 5, 'modified': 8}
```

### 5. Monitoring Agent (`monitoring.py`)

Performance tracking and anomaly detection.

```python
from apps.agents.monitoring import get_monitor

monitor = get_monitor()

# Track execution
monitor.track_execution(
    agent_id='skill_scorer',
    success=True,
    execution_time=0.15,
    confidence=0.9
)

# Detect anomalies
anomalies = monitor.detect_anomalies()
# [{'type': 'performance_drop', 'agent_id': 'github_collector', ...}]

# Get dashboard metrics
metrics = monitor.get_dashboard_metrics()

# Get alerts
alerts = monitor.get_alerts(severity=AlertSeverity.WARNING)
```

Monitored Metrics:
- Success rate per agent
- Execution time (avg, min, max)
- Confidence score distribution
- Error types and frequency

Alert Thresholds:
- Success rate < 90% → Warning
- Success rate < 75% → Critical
- Execution time > 5s → Warning
- Confidence < 0.7 → Warning

### 6. Adaptive Learning (`adaptive.py`)

Learns and adjusts weights based on feedback.

```python
from apps.agents.adaptive import get_adaptive_agent

adaptive = get_adaptive_agent()

# Learn from human reviews
updates = adaptive.learn_from_human_reviews(time_window=timedelta(days=30))
# [WeightUpdate(component='skill_strength', change=+0.02, reason='...')]

# Apply weight updates
new_weights = adaptive.apply_weight_updates(updates, min_confidence=0.5)

# Get personalized recommendations for a user
personalization = adaptive.personalize_for_user(user_id=123)
# {'focus_areas': ['github_activity'], 'recommendations': [...]}

# Get market trends
from apps.agents.adaptive import MarketTrendAnalyzer
analyzer = MarketTrendAnalyzer()
trends = analyzer.get_skill_trends(['react', 'typescript'])
```

### 7. Explainer Agent (`explainer.py`)

Generates human-readable explanations for AI decisions.

```python
from apps.agents.explainer import get_explainer

explainer = get_explainer()

explanation = explainer.explain_score(score_result, benchmark)

# Natural language summary
print(explanation.summary)
# "Your overall score is 65% (Competent tier). You have solid skills..."

# Key factors
print(explanation.key_factors)
# ["Your strongest area is Technical Skills (78%)",
#  "Your biggest opportunity is GitHub Activity (35%)"]

# Counterfactuals (what-if scenarios)
print(explanation.counterfactuals)
# [{"scenario": "If you improved GitHub Activity by 20%",
#   "new_total": 72, "action": "Commit code 3-4 times per week"}]

# Decision tree for visualization
tree = explainer.generate_decision_tree(score_result)
```

### 8. CV Parser Agent (`parsers.py`, `registered_agents.py`)

AI-enhanced CV/Resume parsing that extracts structured information from PDFs.

```python
from apps.agents.parsers import parse_cv_with_ai, parse_cv_complete

# AI-enhanced parsing (uses Gemini if available)
result = parse_cv_with_ai('/path/to/resume.pdf')

print(result['personal_info'])
# {'name': 'John Doe', 'email': 'john@example.com', 'github': 'https://github.com/johndoe'}

print(result['all_skills'])
# ['react', 'typescript', 'python', 'postgresql', 'docker']

print(result['experience'])
# [{'title': 'Frontend Developer', 'company': 'Tech Corp', 'years': 2}]

print(result['experience_years'])  # 3
print(result['seniority_level'])   # 'junior'
print(result['method'])            # 'ai' or 'rule_based'
```

Extracted Data:
- Personal info (name, email, phone, location, social links)
- Skills by category (frontend, backend, database, tools)
- Work experience with duration and technologies
- Education history
- Projects and certifications
- Total years of experience
- Seniority level assessment

The CV Parser integrates with:
- **SkillScoringAgent** - Combines CV skills with form input
- **ExperienceScoringAgent** - Uses CV experience if higher than form input

### 9. Multi-Agent Collaboration (`collaboration.py`)

Consensus building when multiple agents evaluate.

```python
from apps.agents.collaboration import ConsensusAgent, ConsensusMethod

consensus = ConsensusAgent()

# Build consensus from multiple opinions
result = consensus.build_consensus(
    opinions=[opinion1, opinion2, opinion3],
    method=ConsensusMethod.WEIGHTED_AVERAGE
)

print(result.final_score)  # 0.68
print(result.agreement_level)  # 0.85
print(result.conflicts_resolved)  # [{'type': 'score_disagreement', ...}]
```

Consensus Methods:
- `MAJORITY_VOTE` - Bucket scores into tiers, use majority
- `WEIGHTED_AVERAGE` - Weight by confidence and agent accuracy
- `HIGHEST_CONFIDENCE` - Use opinion with highest confidence
- `DEBATE` - Iterative refinement with outlier adjustment

---

## LLM-as-a-Judge Implementation

The LLM Judge uses an iterative confidence loop:

```
┌─────────────────────────────────────────────────────────────┐
│                    CONFIDENCE LOOP                          │
│                                                             │
│  ┌──────────────┐                                           │
│  │   Initial    │                                           │
│  │  Evaluation  │                                           │
│  └──────┬───────┘                                           │
│         │                                                   │
│         ▼                                                   │
│  ┌──────────────┐     confidence < 0.8?                     │
│  │  Confidence  │────────────────────┐                      │
│  │    Check     │                    │ YES                  │
│  └──────┬───────┘                    │                      │
│         │ NO                         ▼                      │
│         │                   ┌──────────────┐                │
│         │                   │ Consistency  │                │
│         │                   │    Check     │                │
│         │                   └──────┬───────┘                │
│         │                          │                        │
│         │                          ▼                        │
│         │                   ┌──────────────┐                │
│         │                   │   Refine     │                │
│         │                   │  Evaluation  │────┐           │
│         │                   └──────────────┘    │           │
│         │                          ▲            │           │
│         │                          └────────────┘           │
│         │                       (max 3 iterations)          │
│         ▼                                                   │
│  ┌──────────────┐                                           │
│  │    Final     │                                           │
│  │  Evaluation  │                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

Configuration:
- `CONFIDENCE_THRESHOLD = 0.8`
- `MAX_ITERATIONS = 3`

---

## Scoring Rubrics

### Skill Tiers & Weights

| Tier | Skills | Weight |
|------|--------|--------|
| Essential | HTML, CSS, JavaScript | 1.0 |
| Framework | React, Vue, Angular, Svelte | 1.2 |
| TypeScript | TypeScript | 1.3 |
| Testing | Jest, Cypress, RTL, Vitest | 1.1 |
| Modern CSS | Tailwind, Sass, Styled-Components | 0.8 |
| Tooling | Git, npm, Webpack, Vite | 0.7 |
| Bonus | Next.js, GraphQL, Accessibility | 0.9 |

### Overall Tier Classification

| Tier | Score Range | Interpretation |
|------|-------------|----------------|
| Strong Junior | ≥ 70% | Ready for junior roles |
| Competent | 50-69% | Solid foundation |
| Developing | 35-49% | Building skills |
| Early Stage | < 35% | Just starting |

---

## API Endpoints

### Core Analysis
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/onboard/` | POST | Submit profile for analysis |
| `/api/agents/latest-analysis/` | GET | Get latest analysis |
| `/api/agents/jobs/{id}/analysis/` | GET | Get detailed analysis |
| `/api/agents/quick-analyze/` | POST | Quick synchronous analysis |

### Agentic Infrastructure
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/agents/registry/` | GET | List registered agents |
| `/api/agents/agents/{id}/health/` | GET | Get agent health |
| `/api/agents/monitoring/dashboard/` | GET | Monitoring metrics |
| `/api/agents/monitoring/alerts/` | GET/DELETE | View/clear alerts |
| `/api/agents/monitoring/anomalies/` | GET | Detect anomalies |

### Memory & Learning
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/memory/` | GET | Agent memory stats |
| `/api/agents/memory/similar-cases/` | POST | Find similar cases |
| `/api/agents/learning/` | GET/POST | View/apply weight updates |
| `/api/agents/learning/personalization/` | GET | User personalization |
| `/api/agents/learning/market-trends/` | GET | Skill market trends |

### Explainability
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/explain/{job_id}/` | GET | Score explanation |
| `/api/agents/explain/{job_id}/counterfactuals/` | GET | What-if scenarios |
| `/api/agents/explain/{job_id}/decision-tree/` | GET | Decision tree data |

### Human Review
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/agents/human-review/` | GET | List pending reviews |
| `/api/agents/human-review/{job_id}/` | GET | Review details |
| `/api/agents/human-review/{job_id}/submit/` | POST | Submit review |

---

## Database Models

### Core Models
- `IngestionJob` - Analysis job tracking
- `Evidence` - Collected data from sources
- `ScoreSnapshot` - Score results
- `HumanReview` - Human validation records
- `AIInsight` - Generated insights

### Infrastructure Models
- `AgentInteraction` - Agent decisions for learning
- `AgentMetric` - Execution metrics
- `AgentWeightHistory` - Weight change history
- `AgentAlert` - Monitoring alerts
- `PipelineExecution` - Pipeline run tracking
- `AgentEvent` - Event audit log

---

## File Structure

```
apps/agents/
├── __init__.py              # Module initialization
├── apps.py                  # Django app config with startup
├── models.py                # All database models
├── views.py                 # Main API views
├── agentic_views.py         # Infrastructure API endpoints
├── urls.py                  # URL routes
├── serializers.py           # DRF serializers
│
├── base.py                  # Base agent classes
├── registry.py              # Agent registration & discovery
├── orchestrator.py          # Pipeline coordinator
├── events.py                # Event bus
├── memory.py                # Agent memory system
├── monitoring.py            # Performance tracking
├── collaboration.py         # Multi-agent consensus
├── adaptive.py              # Adaptive learning
├── explainer.py             # Decision explanations
├── registered_agents.py     # All agent implementations
│
├── scoring.py               # Scoring algorithms
├── collectors.py            # Data collection
├── llm_judge.py             # LLM-as-a-Judge
├── synthetic_data.py        # Benchmark data
└── tasks.py                 # Celery tasks
```

---

## Setup

### 1. Run Migrations
```bash
python manage.py makemigrations agents --name agentic_infrastructure
python manage.py migrate
```

### 2. Install Dependencies
```bash
pip install pdfplumber  # For CV/PDF parsing
pip install google-generativeai  # For Gemini AI
```

### 3. Environment Variables
```env
GEMINI_API_KEY=your-gemini-api-key
GITHUB_TOKEN=your-github-token  # Optional, for higher rate limits
```

### 3. Verify Agent Registration
```python
from apps.agents.registry import AgentRegistry

health = AgentRegistry.get_health_report()
print(f"Registered agents: {health['total_agents']}")
```

---

## Usage Example

```python
from apps.agents.orchestrator import get_orchestrator
from apps.agents.explainer import get_explainer

# Execute pipeline
orchestrator = get_orchestrator()
result = orchestrator.execute_pipeline(
    job_id=1,
    user_id=1,
    input_data={
        'form_fields': {
            'skills': ['react', 'typescript', 'tailwind'],
            'experience_years': 1.5
        },
        'github_username': 'developer123'
    }
)

# Get explanation
explainer = get_explainer()
score_result = result.results['score_aggregator'].data['score_result']
explanation = explainer.explain_score(score_result)

print(explanation.summary)
print(explanation.counterfactuals)
```

---

## Architecture Principles

1. **Separation of Concerns** - Each agent has a single responsibility
2. **Loose Coupling** - Agents communicate via events, not direct calls
3. **Dependency Injection** - Agents declare dependencies, orchestrator resolves
4. **Graceful Degradation** - Fallbacks when agents fail
5. **Observability** - All executions tracked and monitored
6. **Explainability** - Every decision can be explained
7. **Continuous Learning** - System improves from human feedback
