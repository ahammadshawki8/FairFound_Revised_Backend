from django.urls import path
from .views import AnalyzeProfileView, AnalysisHistoryView

urlpatterns = [
    path('profile/', AnalyzeProfileView.as_view(), name='analyze_profile'),
    path('history/', AnalysisHistoryView.as_view(), name='analysis_history'),
]
