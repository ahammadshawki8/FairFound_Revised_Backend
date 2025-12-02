from django.contrib import admin
from .models import Chat, Message, Attachment

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ['id', 'created_at', 'updated_at']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['chat', 'sender', 'text', 'is_read', 'created_at']
