from django.urls import path
from .views import SentimentAnalyzeView, SentimentHistoryView

urlpatterns = [
    path('analyze/', SentimentAnalyzeView.as_view(), name='sentiment_analyze'),
    path('history/', SentimentHistoryView.as_view(), name='sentiment_history'),
]
