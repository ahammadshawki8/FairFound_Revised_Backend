from django.urls import path
from .views import MenteeListView, MenteeDetailView, MenteeStepCreateView, MenteeTaskCreateView, MenteeGenerateRoadmapView

urlpatterns = [
    path('', MenteeListView.as_view(), name='mentee_list'),
    path('<int:pk>/', MenteeDetailView.as_view(), name='mentee_detail'),
    path('<int:pk>/steps/', MenteeStepCreateView.as_view(), name='mentee_step_create'),
    path('<int:pk>/tasks/', MenteeTaskCreateView.as_view(), name='mentee_task_create'),
    path('<int:pk>/generate-roadmap/', MenteeGenerateRoadmapView.as_view(), name='mentee_generate_roadmap'),
]
