"""
URL routes for Junior Frontend Developer Analysis API
"""
from django.urls import path
from .views import (
    OnboardingSubmitView, JobListView, JobDetailView,
    ScoreAnalysisView, LatestAnalysisView, BenchmarkView, RegenerateView,
    QuickAnalyzeView, ReviewQueueView, ReviewActionView,
    SeedBenchmarksView, AIInsightsListView, AIInsightDetailView, WeeklyStatsView
)

urlpatterns = [
    # Main analysis endpoints
    path('onboard/', OnboardingSubmitView.as_view(), name='onboard_submit'),
    path('latest-analysis/', LatestAnalysisView.as_view(), name='latest_analysis'),
    path('jobs/', JobListView.as_view(), name='job_list'),
    path('jobs/<int:pk>/', JobDetailView.as_view(), name='job_detail'),
    path('jobs/<int:job_id>/analysis/', ScoreAnalysisView.as_view(), name='score_analysis'),
    path('jobs/<int:job_id>/regenerate/', RegenerateView.as_view(), name='regenerate'),
    
    # Quick analysis (synchronous, for demos)
    path('quick-analyze/', QuickAnalyzeView.as_view(), name='quick_analyze'),
    
    # Benchmark data
    path('benchmarks/', BenchmarkView.as_view(), name='benchmarks'),
    
    # Weekly stats for dashboard
    path('weekly-stats/', WeeklyStatsView.as_view(), name='weekly_stats'),
    
    # AI Insights endpoints
    path('insights/', AIInsightsListView.as_view(), name='insights_list'),
    path('insights/<int:insight_id>/', AIInsightDetailView.as_view(), name='insight_detail'),
    
    # Admin endpoints
    path('admin/review/queue/', ReviewQueueView.as_view(), name='review_queue'),
    path('admin/review/<int:job_id>/action/', ReviewActionView.as_view(), name='review_action'),
    path('admin/seed-benchmarks/', SeedBenchmarksView.as_view(), name='seed_benchmarks'),
]
