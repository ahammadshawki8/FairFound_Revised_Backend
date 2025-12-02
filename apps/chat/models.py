from django.db import models
from django.conf import settings


class Chat(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chats')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']


class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class Attachment(models.Model):
    TYPE_CHOICES = [('file', 'File'), ('image', 'Image'), ('voice', 'Voice')]

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='chat_attachments/')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='file')
    name = models.CharField(max_length=200)
    size = models.CharField(max_length=50, blank=True)
    duration = models.CharField(max_length=20, blank=True)
