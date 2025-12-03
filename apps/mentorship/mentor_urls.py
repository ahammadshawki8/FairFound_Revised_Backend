from django.urls import path
from .views import MentorListView, MentorDetailView, MentorReviewListView, ConnectMentorView, DisconnectMentorView, MentorAvailabilityView

urlpatterns = [
    path('', MentorListView.as_view(), name='mentor_list'),
    path('availability/', MentorAvailabilityView.as_view(), name='mentor_availability'),
    path('<int:pk>/', MentorDetailView.as_view(), name='mentor_detail'),
    path('<int:pk>/reviews/', MentorReviewListView.as_view(), name='mentor_reviews'),
    path('<int:pk>/connect/', ConnectMentorView.as_view(), name='mentor_connect'),
    path('<int:pk>/disconnect/', DisconnectMentorView.as_view(), name='mentor_disconnect'),
]
