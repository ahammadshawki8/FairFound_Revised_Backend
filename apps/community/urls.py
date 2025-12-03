from django.urls import path
from .views import (
    PostListCreateView, PostDetailView, PostLikeView, PostCommentView,
    PodMembersView, HeatmapDataView, RecentActivityView
)

urlpatterns = [
    path('posts/', PostListCreateView.as_view(), name='post_list_create'),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post_detail'),
    path('posts/<int:pk>/like/', PostLikeView.as_view(), name='post_like'),
    path('posts/<int:pk>/comment/', PostCommentView.as_view(), name='post_comment'),
    path('pod/', PodMembersView.as_view(), name='pod_members'),
    path('heatmap/', HeatmapDataView.as_view(), name='heatmap_data'),
    path('activity/', RecentActivityView.as_view(), name='recent_activity'),
]
