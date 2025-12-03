"""
AI Chatbot Views - Gemini Integration
"""
import os
import json
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from .models import AIConversation, AIMessage

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
if GEMINI_AVAILABLE and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


SYSTEM_PROMPT = """You are a helpful AI assistant for FairFound, a platform that helps freelancers grow their careers through AI-powered insights, mentorship, and community support.

Your capabilities:
- Help users understand the platform features
- Provide career advice for freelancers
- Answer questions about freelancing, pricing, portfolios, and client management
- Give personalized recommendations based on user context
- Explain technical concepts in simple terms

Rules:
1. Be concise and helpful (keep responses under 150 words unless more detail is needed)
2. Reference the current page context when relevant
3. Provide actionable advice
4. Be encouraging but realistic
5. If you don't know something, say so honestly
6. Never make up information about the user's data
"""


class AIConversationListView(APIView):
    """List all AI conversations for the user or create a new one"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversations = AIConversation.objects.filter(user=request.user)
        data = [{
            'id': c.id,
            'title': c.title,
            'created_at': c.created_at.isoformat(),
            'updated_at': c.updated_at.isoformat(),
            'message_count': c.messages.count()
        } for c in conversations]
        return Response(data)

    def post(self, request):
        title = request.data.get('title', 'New Conversation')
        conversation = AIConversation.objects.create(user=request.user, title=title)
        return Response({
            'id': conversation.id,
            'title': conversation.title,
            'created_at': conversation.created_at.isoformat()
        }, status=status.HTTP_201_CREATED)


class AIConversationDetailView(APIView):
    """Get, update, or delete a specific conversation"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            conversation = AIConversation.objects.get(pk=pk, user=request.user)
            messages = [{
                'id': m.id,
                'role': m.role,
                'content': m.content,
                'created_at': m.created_at.isoformat()
            } for m in conversation.messages.all()]
            return Response({
                'id': conversation.id,
                'title': conversation.title,
                'messages': messages,
                'created_at': conversation.created_at.isoformat()
            })
        except AIConversation.DoesNotExist:
            return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, pk):
        try:
            conversation = AIConversation.objects.get(pk=pk, user=request.user)
            if 'title' in request.data:
                conversation.title = request.data['title']
                conversation.save()
            return Response({'id': conversation.id, 'title': conversation.title})
        except AIConversation.DoesNotExist:
            return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        try:
            conversation = AIConversation.objects.get(pk=pk, user=request.user)
            conversation.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except AIConversation.DoesNotExist:
            return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)


class AIChatView(APIView):
    """Send a message to the AI and get a response"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        message = request.data.get('message', '').strip()
        page_context = request.data.get('page_context', '')
        
        if not message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get or create conversation
        if pk:
            try:
                conversation = AIConversation.objects.get(pk=pk, user=request.user)
            except AIConversation.DoesNotExist:
                return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Create new conversation with first message as title
            title = message[:50] + '...' if len(message) > 50 else message
            conversation = AIConversation.objects.create(user=request.user, title=title)

        # Save user message
        user_msg = AIMessage.objects.create(
            conversation=conversation,
            role='user',
            content=message
        )

        # Build chat history for context
        history = list(conversation.messages.exclude(id=user_msg.id).values('role', 'content')[:20])
        
        # Get AI response
        ai_response = self._get_gemini_response(message, page_context, history, request.user)

        # Save AI response
        ai_msg = AIMessage.objects.create(
            conversation=conversation,
            role='assistant',
            content=ai_response
        )

        # Update conversation title if it's the first message
        if conversation.messages.count() == 2:
            conversation.title = message[:50] + '...' if len(message) > 50 else message
            conversation.save()

        return Response({
            'conversation_id': conversation.id,
            'user_message': {
                'id': user_msg.id,
                'role': 'user',
                'content': message,
                'created_at': user_msg.created_at.isoformat()
            },
            'assistant_message': {
                'id': ai_msg.id,
                'role': 'assistant',
                'content': ai_response,
                'created_at': ai_msg.created_at.isoformat()
            }
        })

    def _get_gemini_response(self, message, page_context, history, user):
        """Get response from Gemini API"""
        print(f"[AI CHAT] GEMINI_AVAILABLE: {GEMINI_AVAILABLE}, API_KEY set: {bool(GEMINI_API_KEY)}")
        
        if not GEMINI_AVAILABLE or not GEMINI_API_KEY:
            print("[AI CHAT] Falling back to rule-based responses")
            return self._get_fallback_response(message)

        try:
            # Build context with user info
            user_context = f"User: {user.username}"
            try:
                from apps.users.models import FreelancerProfile
                profile = FreelancerProfile.objects.filter(user=user).first()
                if profile:
                    if profile.title:
                        user_context += f", Role: {profile.title}"
                    if profile.skills:
                        user_context += f", Skills: {', '.join(profile.skills[:5])}"
                    if profile.experience_years:
                        user_context += f", Experience: {profile.experience_years} years"
            except Exception as e:
                print(f"[AI CHAT] Error getting profile: {e}")

            # Build conversation history
            history_text = ""
            for h in history[-10:]:  # Last 10 messages for context
                history_text += f"{h['role'].capitalize()}: {h['content']}\n"

            # Build full prompt
            full_prompt = f"""{SYSTEM_PROMPT}

{user_context}

Current page context: {page_context or 'General'}

Previous conversation:
{history_text}

User: {message}
Assistant:"""

            print(f"[AI CHAT] Calling Gemini API...")
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(full_prompt)
            
            if response.text:
                print(f"[AI CHAT] Got Gemini response: {response.text[:100]}...")
                return response.text.strip()
            return "I'm sorry, I couldn't process that. Could you try rephrasing?"

        except Exception as e:
            print(f"[AI CHAT] Gemini API Error: {e}")
            return self._get_fallback_response(message)

    def _get_fallback_response(self, message):
        """Fallback responses when Gemini is unavailable"""
        lower_msg = message.lower()
        
        if any(word in lower_msg for word in ['roadmap', 'task', 'plan']):
            return "Based on your current roadmap, I recommend focusing on completing your pending tasks first. Your next step should be to work on the skills marked as 'in-progress'. Would you like specific tips on any particular task?"
        
        if any(word in lower_msg for word in ['mentor', 'mentorship', 'coach']):
            return "Looking at your profile, connecting with a mentor could accelerate your growth significantly. I'd suggest browsing mentors who specialize in your skill gaps. Would you like me to explain what to look for in a mentor?"
        
        if any(word in lower_msg for word in ['portfolio', 'project', 'work']):
            return "Your portfolio is key to landing clients. I suggest adding more case studies with measurable outcomes. Would you like tips on how to present your projects effectively?"
        
        if any(word in lower_msg for word in ['price', 'rate', 'earning', 'money', 'charge']):
            return "Based on your skills and experience, you might be undercharging. Consider researching market rates for your specialty and gradually increasing your rates as you build your portfolio."
        
        if any(word in lower_msg for word in ['help', 'what can you do', 'features']):
            return "I'm your AI assistant! I can help you understand the platform, give career advice, explain features, and provide personalized recommendations for your freelance journey. Just ask me anything!"
        
        if any(word in lower_msg for word in ['hello', 'hi', 'hey']):
            return "Hello! I'm here to help you navigate FairFound and grow your freelance career. What would you like to know?"
        
        return "I'm here to help you navigate FairFound and grow your freelance career. Is there something specific you'd like to know more about?"


class AIClearHistoryView(APIView):
    """Clear all messages in a conversation"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            conversation = AIConversation.objects.get(pk=pk, user=request.user)
            count = conversation.messages.count()
            conversation.messages.all().delete()
            return Response({'message': f'Cleared {count} messages'})
        except AIConversation.DoesNotExist:
            return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)


class AIQuickChatView(APIView):
    """Quick chat without saving to conversation history (for floating chatbot)"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = request.data.get('message', '').strip()
        page_context = request.data.get('page_context', '')
        history = request.data.get('history', [])
        
        if not message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get AI response
        response = self._get_gemini_response(message, page_context, history, request.user)
        
        return Response({
            'response': response
        })

    def _get_gemini_response(self, message, page_context, history, user):
        """Get response from Gemini API"""
        print(f"[AI CHAT] GEMINI_AVAILABLE: {GEMINI_AVAILABLE}, API_KEY set: {bool(GEMINI_API_KEY)}")
        
        if not GEMINI_AVAILABLE or not GEMINI_API_KEY:
            print("[AI CHAT] Falling back to rule-based responses")
            return self._get_fallback_response(message)

        try:
            # Build user context
            user_context = f"User: {user.username}"
            try:
                from apps.users.models import FreelancerProfile
                profile = FreelancerProfile.objects.filter(user=user).first()
                if profile:
                    if profile.title:
                        user_context += f", Role: {profile.title}"
                    if profile.skills:
                        user_context += f", Skills: {', '.join(profile.skills[:5])}"
                    if profile.experience_years:
                        user_context += f", Experience: {profile.experience_years} years"
            except Exception as e:
                print(f"[AI CHAT] Error getting profile: {e}")

            history_text = "\n".join([f"{h['role'].capitalize()}: {h['content']}" for h in history[-10:]])

            full_prompt = f"""{SYSTEM_PROMPT}

{user_context}

Current page context: {page_context or 'General'}

Previous conversation:
{history_text}

User: {message}
Assistant:"""

            print(f"[AI CHAT] Calling Gemini API...")
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(full_prompt)
            
            if response.text:
                print(f"[AI CHAT] Got Gemini response: {response.text[:100]}...")
                return response.text.strip()
            return "I'm sorry, I couldn't process that. Could you try rephrasing?"

        except Exception as e:
            print(f"[AI CHAT] Gemini API Error: {e}")
            return self._get_fallback_response(message)

    def _get_fallback_response(self, message):
        """Fallback responses when Gemini is unavailable"""
        lower_msg = message.lower()
        
        if any(word in lower_msg for word in ['roadmap', 'task', 'plan']):
            return "Based on your current roadmap, I recommend focusing on completing your pending tasks first. Would you like specific tips on any particular task?"
        
        if any(word in lower_msg for word in ['mentor', 'mentorship']):
            return "Connecting with a mentor could accelerate your growth significantly. Browse mentors who specialize in your skill gaps!"
        
        if any(word in lower_msg for word in ['portfolio', 'project']):
            return "Your portfolio is key to landing clients. Add case studies with measurable outcomes for best results."
        
        if any(word in lower_msg for word in ['price', 'rate', 'earning']):
            return "Research market rates for your specialty and gradually increase your rates as you build your portfolio."
        
        if any(word in lower_msg for word in ['help', 'what can you do']):
            return "I'm your AI assistant! I can help with career advice, explain features, and provide personalized recommendations."
        
        if any(word in lower_msg for word in ['hello', 'hi', 'hey']):
            return "Hello! I'm here to help you grow your freelance career. What would you like to know?"
        
        return "I'm here to help you navigate FairFound. Is there something specific you'd like to know?"
