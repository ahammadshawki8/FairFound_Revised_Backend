from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """List all notifications for the current user"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        unread_count = queryset.filter(read=False).count()
        return Response({
            'notifications': serializer.data,
            'unread_count': unread_count,
            'total_count': queryset.count()
        })


class MarkReadView(APIView):
    """Mark a single notification as read"""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
            notification.read = True
            notification.save()
            return Response(NotificationSerializer(notification).data)
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)


class MarkAllReadView(APIView):
    """Mark all notifications as read"""
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        count = Notification.objects.filter(user=request.user, read=False).update(read=True)
        return Response({
            'message': 'All notifications marked as read',
            'count': count
        })


class DeleteNotificationView(APIView):
    """Delete a single notification"""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
            notification.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)


class ClearAllNotificationsView(APIView):
    """Delete all notifications for the current user"""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        count = Notification.objects.filter(user=request.user).delete()[0]
        return Response({
            'message': 'All notifications cleared',
            'count': count
        })


# Helper function to create notifications
def create_notification(user, title, message, notification_type='info'):
    """
    Create a notification for a user.
    Can be called from other apps to send notifications.
    """
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=notification_type
    )
