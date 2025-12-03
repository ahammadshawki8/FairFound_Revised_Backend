from rest_framework import serializers
from .models import Chat, Message, Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ['id', 'type', 'name', 'url', 'size', 'duration']

    def get_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    sender_avatar = serializers.SerializerMethodField()
    attachments = AttachmentSerializer(many=True, read_only=True)
    is_me = serializers.SerializerMethodField()
    thread_id = serializers.IntegerField(source='thread.id', read_only=True, allow_null=True)
    reply_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender', 'sender_name', 'sender_avatar', 'text', 'is_read', 
                  'attachments', 'is_me', 'thread_id', 'reply_count', 'created_at']

    def get_is_me(self, obj):
        request = self.context.get('request')
        return request and obj.sender == request.user

    def get_sender_avatar(self, obj):
        if obj.sender.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.sender.avatar.url)
            return obj.sender.avatar.url
        return None


class ChatSerializer(serializers.ModelSerializer):
    participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    last_message_time = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = ['id', 'participant', 'last_message', 'last_message_time', 'unread_count', 'updated_at']

    def get_participant(self, obj):
        request = self.context.get('request')
        other = obj.participants.exclude(id=request.user.id).first()
        if other:
            avatar_url = None
            if other.avatar:
                avatar_url = request.build_absolute_uri(other.avatar.url) if request else other.avatar.url
            return {
                'id': other.id, 
                'name': other.username, 
                'avatarUrl': avatar_url,
                'role': other.role
            }
        return None

    def get_last_message(self, obj):
        msg = obj.messages.last()
        if msg:
            if msg.attachments.exists():
                att = msg.attachments.first()
                if att.type == 'voice':
                    return '🎤 Voice message'
                elif att.type == 'image':
                    return '📷 Image'
                return f'📎 {att.name}'
            return msg.text
        return ''

    def get_last_message_time(self, obj):
        msg = obj.messages.last()
        return msg.created_at if msg else obj.updated_at

    def get_unread_count(self, obj):
        request = self.context.get('request')
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
