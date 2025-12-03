from django.db import models
from django.conf import settings


class AIConversation(models.Model):
    """AI Chatbot conversation history"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_conversations')
    title = models.CharField(max_length=200, default='New Conversation')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class AIMessage(models.Model):
    """Individual message in an AI conversation"""
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]
    
    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"


class Chat(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chats')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def get_other_participant(self, user):
        """Get the other participant in a 1-on-1 chat"""
        return self.participants.exclude(id=user.id).first()


class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    # Threading support
    thread = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    @property
    def reply_count(self):
        return self.replies.count()


class Attachment(models.Model):
    TYPE_CHOICES = [('file', 'File'), ('image', 'Image'), ('voice', 'Voice')]

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='chat_attachments/')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='file')
    name = models.CharField(max_length=200)
    size = models.CharField(max_length=50, blank=True)
    duration = models.CharField(max_length=20, blank=True)
