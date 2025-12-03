from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from .models import Chat, Message, Attachment
from .serializers import ChatSerializer, MessageSerializer
from apps.users.models import User


class ChatListView(generics.ListAPIView):
    serializer_class = ChatSerializer

    def get_queryset(self):
        return Chat.objects.filter(participants=self.request.user)


class GetOrCreateChatView(APIView):
    """Get or create a chat with a specific user"""
    def post(self, request, user_id):
        try:
            other_user = User.objects.get(pk=user_id)
            
            # Find existing chat between these two users
            existing_chat = Chat.objects.filter(participants=request.user).filter(participants=other_user).first()
            
            if existing_chat:
                return Response(ChatSerializer(existing_chat, context={'request': request}).data)
            
            # Create new chat
            chat = Chat.objects.create()
            chat.participants.add(request.user, other_user)
            chat.save()
            
            return Response(ChatSerializer(chat, context={'request': request}).data, status=status.HTTP_201_CREATED)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


class ChatMessagesView(generics.ListAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        chat = Chat.objects.get(pk=self.kwargs['pk'], participants=self.request.user)
        # Mark messages as read
        chat.messages.exclude(sender=self.request.user).update(is_read=True)
        # Only return top-level messages (not thread replies)
        return chat.messages.filter(thread__isnull=True)


class SendMessageView(APIView):
    def post(self, request, pk):
        try:
            chat = Chat.objects.get(pk=pk, participants=request.user)
            thread_id = request.data.get('thread_id')
            thread = None
            if thread_id:
                thread = Message.objects.get(pk=thread_id, chat=chat)
            
            message = Message.objects.create(
                chat=chat, 
                sender=request.user, 
                text=request.data.get('text', ''),
                thread=thread
            )
            # Update chat timestamp
            chat.save()
            return Response(MessageSerializer(message, context={'request': request}).data, status=status.HTTP_201_CREATED)
        except Chat.DoesNotExist:
            return Response({'error': 'Chat not found'}, status=status.HTTP_404_NOT_FOUND)
        except Message.DoesNotExist:
            return Response({'error': 'Thread message not found'}, status=status.HTTP_404_NOT_FOUND)


class UploadAttachmentView(APIView):
    def post(self, request, pk):
        try:
            chat = Chat.objects.get(pk=pk, participants=request.user)
            message = Message.objects.create(chat=chat, sender=request.user, text=request.data.get('text', ''))
            
            if 'file' in request.FILES:
                file = request.FILES['file']
                file_type = request.data.get('type', 'file')
                
                # Calculate duration for voice messages (placeholder - would need audio processing)
                duration = ''
                if file_type == 'voice':
                    duration = request.data.get('duration', '0:00')
                
                # Format file size
                size_bytes = file.size
                if size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                
                Attachment.objects.create(
                    message=message,
                    file=file,
                    name=file.name,
                    type=file_type,
                    size=size_str,
                    duration=duration
                )
            
            # Update chat timestamp
            chat.save()
            return Response(MessageSerializer(message, context={'request': request}).data, status=status.HTTP_201_CREATED)
        except Chat.DoesNotExist:
            return Response({'error': 'Chat not found'}, status=status.HTTP_404_NOT_FOUND)


class MarkChatReadView(APIView):
    """Mark all messages in a chat as read"""
    def put(self, request, pk):
        try:
            chat = Chat.objects.get(pk=pk, participants=request.user)
            count = chat.messages.exclude(sender=request.user).filter(is_read=False).update(is_read=True)
            return Response({'message': f'Marked {count} messages as read'})
        except Chat.DoesNotExist:
            return Response({'error': 'Chat not found'}, status=status.HTTP_404_NOT_FOUND)


class ThreadRepliesView(generics.ListAPIView):
    """Get replies to a specific message (thread)"""
    serializer_class = MessageSerializer

    def get_queryset(self):
        chat = Chat.objects.get(pk=self.kwargs['pk'], participants=self.request.user)
        return Message.objects.filter(chat=chat, thread_id=self.kwargs['message_id'])
