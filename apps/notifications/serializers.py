from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    time = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'type', 'read', 'time', 'created_at']

    def get_time(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        
        diff = timezone.now() - obj.created_at
        if diff < timedelta(minutes=1):
            return 'Just now'
        elif diff < timedelta(hours=1):
            return f'{int(diff.seconds / 60)}m ago'
        elif diff < timedelta(days=1):
            return f'{int(diff.seconds / 3600)}h ago'
        return f'{diff.days}d ago'
