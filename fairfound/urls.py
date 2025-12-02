from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
    path('api/profile/', include('apps.users.profile_urls')),
    path('api/analysis/', include('apps.analysis.urls')),
    path('api/roadmap/', include('apps.roadmap.urls')),
    path('api/tasks/', include('apps.roadmap.task_urls')),
    path('api/mentors/', include('apps.mentorship.mentor_urls')),
    path('api/mentees/', include('apps.mentorship.mentee_urls')),
    path('api/sessions/', include('apps.mentorship.session_urls')),
    path('api/portfolio/', include('apps.portfolio.urls')),
    path('api/proposals/', include('apps.portfolio.proposal_urls')),
    path('api/sentiment/', include('apps.analysis.sentiment_urls')),
    path('api/community/', include('apps.community.urls')),
    path('api/chats/', include('apps.chat.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/payments/', include('apps.payments.urls')),
    path('api/agents/', include('apps.agents.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
