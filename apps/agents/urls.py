"""
URL routes for Junior Frontend Developer Analysis API
"""
from django.urls import path
from .views import (
    OnboardingSubmitView, JobListView, JobDetailView,
    ScoreAnalysisView, LatestAnalysisView, BenchmarkView, RegenerateView,
    QuickAnalyzeView, ReviewQueueView, ReviewActionView,
    SeedBenchmarksView, AIInsightsListView, AIInsightDetailView, WeeklyStatsView,
    HumanReviewListView, HumanReviewDetailView, HumanReviewSubmitView, HumanReviewStatsView
)
from .agentic_views import (
    AgentRegistryView, AgentHealthView, MonitoringDashboardView,
    AlertsView, AnomalyDetectionView, AgentMemoryView, SimilarCasesView,
    AdaptiveLearningView, PersonalizationView, ScoreExplanationView,
    CounterfactualView, DecisionTreeView, EventHistoryView,
    WeightHistoryView, MarketTrendsView
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
    
    # Human-in-the-Loop Review endpoints
    path('human-review/', HumanReviewListView.as_view(), name='human_review_list'),
    path('human-review/stats/', HumanReviewStatsView.as_view(), name='human_review_stats'),
    path('human-review/<int:job_id>/', HumanReviewDetailView.as_view(), name='human_review_detail'),
    path('human-review/<int:job_id>/submit/', HumanReviewSubmitView.as_view(), name='human_review_submit'),
    
    # Admin endpoints
    path('admin/review/queue/', ReviewQueueView.as_view(), name='review_queue'),
    path('admin/review/<int:job_id>/action/', ReviewActionView.as_view(), name='review_action'),
    path('admin/seed-benchmarks/', SeedBenchmarksView.as_view(), name='seed_benchmarks'),
    
    # ============================================
    # AGENTIC AI INFRASTRUCTURE ENDPOINTS
    # ============================================
    
    # Agent Registry & Health
    path('agents/registry/', AgentRegistryView.as_view(), name='agent_registry'),
    path('agents/<str:agent_id>/health/', AgentHealthView.as_view(), name='agent_health'),
    
    # Monitoring & Alerts
    path('monitoring/dashboard/', MonitoringDashboardView.as_view(), name='monitoring_dashboard'),
    path('monitoring/alerts/', AlertsView.as_view(), name='monitoring_alerts'),
    path('monitoring/anomalies/', AnomalyDetectionView.as_view(), name='anomaly_detection'),
    
    # Agent Memory & Learning
    path('memory/', AgentMemoryView.as_view(), name='agent_memory'),
    path('memory/<str:agent_id>/', AgentMemoryView.as_view(), name='agent_memory_detail'),
    path('memory/similar-cases/', SimilarCasesView.as_view(), name='similar_cases'),
    
    # Adaptive Learning
    path('learning/', AdaptiveLearningView.as_view(), name='adaptive_learning'),
    path('learning/personalization/', PersonalizationView.as_view(), name='personalization'),
    path('learning/weights-history/', WeightHistoryView.as_view(), name='weight_history'),
    path('learning/market-trends/', MarketTrendsView.as_view(), name='market_trends'),
    
    # Explainability
    path('explain/<int:job_id>/', ScoreExplanationView.as_view(), name='score_explanation'),
    path('explain/<int:job_id>/counterfactuals/', CounterfactualView.as_view(), name='counterfactuals'),
    path('explain/<int:job_id>/decision-tree/', DecisionTreeView.as_view(), name='decision_tree'),
    
    # Events
    path('events/', EventHistoryView.as_view(), name='event_history'),
]
