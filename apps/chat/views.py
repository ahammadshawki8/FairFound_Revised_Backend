from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Chat, Message, Attachment
from .serializers import ChatSerializer, MessageSerializer


class ChatListView(generics.ListAPIView):
    serializer_class = ChatSerializer

    def get_queryset(self):
        return Chat.objects.filter(participants=self.request.user)


class ChatMessagesView(generics.ListAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        chat = Chat.objects.get(pk=self.kwargs['pk'], participants=self.request.user)
        # Mark messages as read
        chat.messages.exclude(sender=self.request.user).update(is_read=True)
        return chat.messages.all()


class SendMessageView(APIView):
    def post(self, request, pk):
        try:
            chat = Chat.objects.get(pk=pk, participants=request.user)
            message = Message.objects.create(chat=chat, sender=request.user, text=request.data.get('text', ''))
            return Response(MessageSerializer(message, context={'request': request}).data, status=status.HTTP_201_CREATED)
        except Chat.DoesNotExist:
            return Response({'error': 'Chat not found'}, status=status.HTTP_404_NOT_FOUND)


class UploadAttachmentView(APIView):
    def post(self, request, pk):
        try:
            chat = Chat.objects.get(pk=pk, participants=request.user)
            message = Message.objects.create(chat=chat, sender=request.user, text=request.data.get('text', ''))
            
            if 'file' in request.FILES:
                file = request.FILES['file']
                Attachment.objects.create(
                    message=message,
                    file=file,
                    name=file.name,
                    type=request.data.get('type', 'file'),
                    size=str(file.size)
                )
            return Response(MessageSerializer(message, context={'request': request}).data, status=status.HTTP_201_CREATED)
        except Chat.DoesNotExist:
            return Response({'error': 'Chat not found'}, status=status.HTTP_404_NOT_FOUND)
