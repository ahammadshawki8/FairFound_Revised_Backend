from django.urls import path
from .views import SessionListCreateView, SessionDetailView, SessionStatusView

urlpatterns = [
    path('', SessionListCreateView.as_view(), name='session_list_create'),
    path('<int:pk>/', SessionDetailView.as_view(), name='session_detail'),
    path('<int:pk>/status/', SessionStatusView.as_view(), name='session_status'),
]
