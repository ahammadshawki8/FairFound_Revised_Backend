from django.urls import path
from .views import (
    ChatListView, ChatMessagesView, SendMessageView, 
    UploadAttachmentView, GetOrCreateChatView, MarkChatReadView, ThreadRepliesView
)
from .ai_views import (
    AIConversationListView, AIConversationDetailView, AIChatView,
    AIClearHistoryView, AIQuickChatView
)

urlpatterns = [
    # User-to-user chat
    path('', ChatListView.as_view(), name='chat_list'),
    path('with/<int:user_id>/', GetOrCreateChatView.as_view(), name='get_or_create_chat'),
    path('<int:pk>/messages/', ChatMessagesView.as_view(), name='chat_messages'),
    path('<int:pk>/messages/send/', SendMessageView.as_view(), name='send_message'),
    path('<int:pk>/messages/<int:message_id>/replies/', ThreadRepliesView.as_view(), name='thread_replies'),
    path('<int:pk>/attachments/', UploadAttachmentView.as_view(), name='upload_attachment'),
    path('<int:pk>/read/', MarkChatReadView.as_view(), name='mark_chat_read'),
    
    # AI Chatbot endpoints
    path('ai/', AIConversationListView.as_view(), name='ai_conversations'),
    path('ai/quick/', AIQuickChatView.as_view(), name='ai_quick_chat'),
    path('ai/chat/', AIChatView.as_view(), name='ai_chat_new'),
    path('ai/<int:pk>/', AIConversationDetailView.as_view(), name='ai_conversation_detail'),
    path('ai/<int:pk>/chat/', AIChatView.as_view(), name='ai_chat'),
    path('ai/<int:pk>/clear/', AIClearHistoryView.as_view(), name='ai_clear_history'),
]
