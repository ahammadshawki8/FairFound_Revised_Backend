from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView, RegisterView, LogoutView, 
    CurrentUserView, FreelancerProfileView, MentorProfileView, AvatarUploadView
)

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('signup/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('profile/', FreelancerProfileView.as_view(), name='freelancer_profile'),
    path('mentor-profile/', MentorProfileView.as_view(), name='mentor_profile'),
    path('avatar/', AvatarUploadView.as_view(), name='avatar_upload'),
]
