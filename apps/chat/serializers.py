from rest_framework import serializers
from .models import Chat, Message, Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ['id', 'type', 'name', 'url', 'size', 'duration']

    def get_url(self, obj):
        return obj.file.url if obj.file else None


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    is_me = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'sender', 'sender_name', 'text', 'is_read', 'attachments', 'is_me', 'created_at']

    def get_is_me(self, obj):
        request = self.context.get('request')
        return request and obj.sender == request.user


class ChatSerializer(serializers.ModelSerializer):
    participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = ['id', 'participant', 'last_message', 'unread_count', 'updated_at']

    def get_participant(self, obj):
        request = self.context.get('request')
        other = obj.participants.exclude(id=request.user.id).first()
        if other:
            return {'id': other.id, 'name': other.username, 'avatarUrl': other.avatar.url if other.avatar else None}
        return None

    def get_last_message(self, obj):
        msg = obj.messages.last()
        return msg.text if msg else ''

    def get_unread_count(self, obj):
        request = self.context.get('request')
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
