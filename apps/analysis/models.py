from django.db import models
from django.conf import settings


class ProfileAnalysis(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analyses')
    global_readiness_score = models.IntegerField(default=0)
    market_percentile = models.IntegerField(default=0)
    projected_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    strengths = models.JSONField(default=list)
    weaknesses = models.JSONField(default=list)
    opportunities = models.JSONField(default=list)
    threats = models.JSONField(default=list)
    skill_gaps = models.JSONField(default=list)
    pricing_current = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pricing_recommended = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pricing_reasoning = models.TextField(blank=True)
    portfolio_score = models.IntegerField(default=0)
    github_score = models.IntegerField(default=0)
    communication_score = models.IntegerField(default=0)
    tech_stack_score = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class SentimentAnalysis(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sentiment_analyses')
    review_text = models.TextField()
    sentiment = models.CharField(max_length=20)
    confidence = models.DecimalField(max_digits=3, decimal_places=2)
    keywords = models.JSONField(default=list)
    actionable_steps = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
