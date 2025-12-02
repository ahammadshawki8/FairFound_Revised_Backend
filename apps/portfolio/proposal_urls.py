from django.urls import path
from .views import ProposalGenerateView, ProposalHistoryView

urlpatterns = [
    path('generate/', ProposalGenerateView.as_view(), name='proposal_generate'),
    path('history/', ProposalHistoryView.as_view(), name='proposal_history'),
]
