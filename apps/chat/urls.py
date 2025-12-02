from django.urls import path
from .views import ChatListView, ChatMessagesView, SendMessageView, UploadAttachmentView

urlpatterns = [
    path('', ChatListView.as_view(), name='chat_list'),
    path('<int:pk>/messages/', ChatMessagesView.as_view(), name='chat_messages'),
    path('<int:pk>/messages/send/', SendMessageView.as_view(), name='send_message'),
    path('<int:pk>/attachments/', UploadAttachmentView.as_view(), name='upload_attachment'),
]
