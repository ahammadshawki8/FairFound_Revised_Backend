from django.urls import path
from .views import (
    NotificationListView, MarkReadView, MarkAllReadView, 
    DeleteNotificationView, ClearAllNotificationsView, BulkNotificationView
)

urlpatterns = [
    path('', NotificationListView.as_view(), name='notification_list'),
    path('<int:pk>/', DeleteNotificationView.as_view(), name='delete_notification'),
    path('<int:pk>/read/', MarkReadView.as_view(), name='mark_read'),
    path('read-all/', MarkAllReadView.as_view(), name='mark_all_read'),
    path('clear-all/', ClearAllNotificationsView.as_view(), name='clear_all'),
    path('bulk/', BulkNotificationView.as_view(), name='bulk_notification'),
]
