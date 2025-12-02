from django.urls import path
from .views import RoadmapListView, RoadmapStepCreateView, RoadmapStepDetailView, GenerateRoadmapView, RoadmapStatusView

urlpatterns = [
    path('', RoadmapListView.as_view(), name='roadmap_list'),
    path('status/', RoadmapStatusView.as_view(), name='roadmap_status'),
    path('steps/', RoadmapStepCreateView.as_view(), name='roadmap_step_create'),
    path('steps/<int:pk>/', RoadmapStepDetailView.as_view(), name='roadmap_step_detail'),
    path('generate/', GenerateRoadmapView.as_view(), name='roadmap_generate'),
]
