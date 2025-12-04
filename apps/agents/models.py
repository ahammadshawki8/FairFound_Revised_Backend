from django.db import models
from django.conf import settings


class IngestionJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('running', 'Running'), 
        ('done', 'Done'), ('error', 'Error'), ('review', 'Needs Review')
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ingestion_jobs')
    input_data = models.JSONField(default=dict)
    result = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']


class Evidence(models.Model):
    SOURCE_CHOICES = [
        ('cv', 'CV/Resume'), ('github', 'GitHub'), ('portfolio', 'Portfolio'),
        ('linkedin', 'LinkedIn Public'), ('blog', 'Blog/Medium'), ('form', 'Form Input')
    ]
    
    job = models.ForeignKey(IngestionJob, on_delete=models.CASCADE, related_name='evidence')
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    raw_content = models.TextField(blank=True)
    extracted_data = models.JSONField(default=dict)
    confidence = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)


class ScoreSnapshot(models.Model):
    job = models.ForeignKey(IngestionJob, on_delete=models.CASCADE, related_name='scores')
    overall_score = models.FloatField()
    breakdown = models.JSONField(default=dict)
    llm_rationale = models.TextField(blank=True)
    improvements = models.JSONField(default=list)
    confidence = models.FloatField(default=0.0)
    flagged_for_human = models.BooleanField(default=False)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class BenchmarkCohort(models.Model):
    """Stores benchmark data for comparison - from synthetic + real aggregated data"""
    name = models.CharField(max_length=100)  # e.g., "frontend_developer", "python_backend"
    skill_category = models.CharField(max_length=100)
    percentiles = models.JSONField(default=dict)  # {10: 0.3, 25: 0.45, 50: 0.6, 75: 0.75, 90: 0.88}
    avg_hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    avg_experience_years = models.FloatField(default=0)
    common_skills = models.JSONField(default=list)
    sample_size = models.IntegerField(default=0)
    is_synthetic = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['name', 'skill_category']


class SyntheticProfile(models.Model):
    """Synthetic freelancer profiles for benchmarking when real data is sparse"""
    name = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    skills = models.JSONField(default=list)
    experience_years = models.IntegerField(default=0)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    github_repos = models.IntegerField(default=0)
    github_stars = models.IntegerField(default=0)
    portfolio_score = models.FloatField(default=0)
    overall_score = models.FloatField(default=0)
    category = models.CharField(max_length=100)
    source = models.CharField(max_length=100, default='generated')
    created_at = models.DateTimeField(auto_now_add=True)


class HumanReview(models.Model):
    """Human-in-the-loop review of AI agent evaluations"""
    DECISION_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('modified', 'Modified'),
    ]
    
    job = models.ForeignKey(IngestionJob, on_delete=models.CASCADE, related_name='human_reviews')
    score_snapshot = models.ForeignKey(ScoreSnapshot, on_delete=models.CASCADE, related_name='human_reviews', null=True)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='reviews_given')
    
    # AI evaluation data
    ai_confidence = models.FloatField(default=0.0)
    ai_evaluation = models.JSONField(default=dict)
    
    # Human review
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES, default='pending')
    human_confidence = models.FloatField(null=True, blank=True)  # Human's confidence in AI evaluation
    
    # Detailed feedback
    accuracy_rating = models.IntegerField(null=True, blank=True)  # 1-5 scale
    relevance_rating = models.IntegerField(null=True, blank=True)  # 1-5 scale
    actionability_rating = models.IntegerField(null=True, blank=True)  # 1-5 scale
    
    # Modifications
    modified_strengths = models.JSONField(null=True, blank=True)
    modified_weaknesses = models.JSONField(null=True, blank=True)
    modified_recommendations = models.JSONField(null=True, blank=True)
    modified_score = models.FloatField(null=True, blank=True)
    
    # Notes
    review_notes = models.TextField(blank=True)
    disagreement_reasons = models.JSONField(default=list)  # Why human disagrees with AI
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']


class AIInsight(models.Model):
    """AI-generated insights stored from Gemini"""
    INSIGHT_TYPES = [
        ('market_trend', 'Market Trend'),
        ('skill_gap', 'Skill Gap'),
        ('career_advice', 'Career Advice'),
        ('learning_path', 'Learning Path'),
        ('salary_insight', 'Salary Insight'),
        ('project_suggestion', 'Project Suggestion'),
        ('swot_analysis', 'SWOT Analysis'),
        ('salary_comparison', 'Salary Comparison'),
        ('skill_demand', 'Skill Demand'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_insights')
    job = models.ForeignKey(IngestionJob, on_delete=models.CASCADE, related_name='insights', null=True, blank=True)
    insight_type = models.CharField(max_length=30, choices=INSIGHT_TYPES)
    title = models.CharField(max_length=300)
    content = models.TextField()
    metadata = models.JSONField(default=dict)
    relevance_score = models.FloatField(default=0.8)
    is_read = models.BooleanField(default=False)
    is_bookmarked = models.BooleanField(default=False)
    generated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['user', 'insight_type']),
            models.Index(fields=['user', 'is_read']),
        ]


# ============================================
# AGENTIC AI INFRASTRUCTURE MODELS
# ============================================

class AgentInteraction(models.Model):
    """
    Stores agent interactions for memory and learning.
    Used by the AgentMemory system to learn from past decisions.
    """
    agent_id = models.CharField(max_length=100, db_index=True)
    context_hash = models.CharField(max_length=32, db_index=True)  # For similarity matching
    context = models.JSONField(default=dict)  # Input context
    decision = models.JSONField(default=dict)  # Agent's decision/output
    confidence = models.FloatField(default=0.0)
    
    # Outcome tracking
    outcome = models.CharField(max_length=50, null=True, blank=True)  # approved, rejected, modified
    feedback = models.JSONField(null=True, blank=True)  # Human feedback details
    outcome_recorded_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['agent_id', 'context_hash']),
            models.Index(fields=['agent_id', 'outcome']),
            models.Index(fields=['created_at']),
        ]


class AgentMetric(models.Model):
    """
    Stores execution metrics for agent monitoring.
    Used by the MonitoringAgent to track performance.
    """
    agent_id = models.CharField(max_length=100, db_index=True)
    success = models.BooleanField(default=True)
    execution_time = models.FloatField(default=0.0)  # seconds
    confidence = models.FloatField(default=0.0)
    error = models.TextField(null=True, blank=True)
    
    # Additional metadata
    job_id = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['agent_id', 'created_at']),
            models.Index(fields=['agent_id', 'success']),
        ]


class AgentWeightHistory(models.Model):
    """
    Tracks changes to scoring weights over time.
    Used by the AdaptiveLearningAgent.
    """
    weights = models.JSONField(default=dict)  # Current weights
    previous_weights = models.JSONField(default=dict)  # Previous weights
    changes = models.JSONField(default=dict)  # What changed and why
    
    # Learning context
    trigger = models.CharField(max_length=100)  # What triggered the update
    reviews_analyzed = models.IntegerField(default=0)
    confidence = models.FloatField(default=0.0)
    
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']


class AgentAlert(models.Model):
    """
    Stores alerts generated by the monitoring system.
    """
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    agent_id = models.CharField(max_length=100, db_index=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    message = models.TextField()
    metric = models.CharField(max_length=100)
    current_value = models.FloatField()
    threshold = models.FloatField()
    
    # Resolution tracking
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['agent_id', 'severity']),
            models.Index(fields=['acknowledged', 'created_at']),
        ]


class PipelineExecution(models.Model):
    """
    Tracks complete pipeline executions.
    Used by the AgentOrchestrator.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partial'),
    ]
    
    job = models.ForeignKey(
        IngestionJob, 
        on_delete=models.CASCADE, 
        related_name='pipeline_executions'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Execution details
    agents_executed = models.IntegerField(default=0)
    agents_succeeded = models.IntegerField(default=0)
    agents_failed = models.IntegerField(default=0)
    total_time = models.FloatField(default=0.0)  # seconds
    
    # Results
    results = models.JSONField(default=dict)  # Per-agent results
    errors = models.JSONField(default=list)  # List of errors
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']


class AgentEvent(models.Model):
    """
    Stores events from the event bus for auditing and replay.
    """
    event_type = models.CharField(max_length=100, db_index=True)
    agent_id = models.CharField(max_length=100, db_index=True)
    job_id = models.IntegerField(null=True, blank=True, db_index=True)
    
    data = models.JSONField(default=dict)
    priority = models.IntegerField(default=1)
    correlation_id = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['job_id', 'created_at']),
        ]
