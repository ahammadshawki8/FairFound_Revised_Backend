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


class BulkNotificationView(APIView):
    """Send notifications to multiple mentees (mentor only)"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != 'mentor':
            return Response({'error': 'Not a mentor'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            from apps.users.models import MentorProfile, FreelancerProfile, User
            
            mentor_profile = MentorProfile.objects.get(user=request.user)
            mentee_ids = request.data.get('mentee_ids', [])
            title = request.data.get('title', 'Message from your mentor')
            message = request.data.get('message', '')
            notification_type = request.data.get('type', 'info')
            
            if not message:
                return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get mentees connected to this mentor
            if mentee_ids:
                # Send to specific mentees
                mentees = FreelancerProfile.objects.filter(
                    connected_mentor=mentor_profile,
                    id__in=mentee_ids
                )
            else:
                # Send to all mentees
                mentees = FreelancerProfile.objects.filter(connected_mentor=mentor_profile)
            
            created_count = 0
            for mentee in mentees:
                Notification.objects.create(
                    user=mentee.user,
                    title=title,
                    message=message,
                    type=notification_type
                )
                created_count += 1
            
            return Response({
                'message': f'Notification sent to {created_count} mentee(s)',
                'count': created_count
            }, status=status.HTTP_201_CREATED)
        except MentorProfile.DoesNotExist:
            return Response({'error': 'Mentor profile not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
