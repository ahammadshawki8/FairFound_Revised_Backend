from django.contrib import admin
from .models import ProfileAnalysis, SentimentAnalysis

@admin.register(ProfileAnalysis)
class ProfileAnalysisAdmin(admin.ModelAdmin):
    list_display = ['user', 'global_readiness_score', 'market_percentile', 'created_at']

@admin.register(SentimentAnalysis)
class SentimentAnalysisAdmin(admin.ModelAdmin):
    list_display = ['user', 'sentiment', 'confidence', 'created_at']
