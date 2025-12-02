from django.urls import path
from .views import FreelancerProfileView, AvatarUploadView

urlpatterns = [
    path('', FreelancerProfileView.as_view(), name='profile'),
    path('avatar/', AvatarUploadView.as_view(), name='avatar_upload'),
]
