"""
AI Chatbot Views - Gemini Integration for Freelancer Career Assistant
"""
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


def get_gemini_api_key():
    """Get Gemini API key from Django settings"""
    return getattr(settings, 'GEMINI_API_KEY', '') or ''


def get_configured_model():
    """Get a configured Gemini model instance"""
    api_key = get_gemini_api_key()
    if GEMINI_AVAILABLE and api_key and api_key not in ['', 'your-gemini-api-key']:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-2.0-flash')
    return None


SYSTEM_PROMPT = """You are FairFound AI, an expert freelance career coach and assistant. You help freelancers succeed in their careers with practical, actionable advice.

Your expertise includes:
- Freelance pricing strategies and rate negotiation
- Portfolio optimization and project showcasing
- Client acquisition and relationship management
- Skill development roadmaps for developers
- Personal branding and online presence
- Proposal writing and pitching techniques
- Time management and productivity for freelancers
- Contract negotiation and scope management
- Building passive income streams
- Transitioning from employment to freelancing

Personality:
- Supportive but direct - give honest feedback
- Data-driven - reference market rates and industry trends
- Action-oriented - always provide specific next steps
- Encouraging - celebrate wins and progress

Response Guidelines:
1. Keep responses concise (100-200 words) unless detailed explanation needed
2. Use bullet points for actionable items
3. Reference the user's skills/experience when giving advice
4. Provide specific examples and numbers when discussing rates
5. If asked about the platform, explain FairFound features helpfully
6. For technical questions outside freelancing, briefly answer then redirect to career growth
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
        model = get_configured_model()
        
        if not model:
            print("[AI CHAT] Gemini not available, using fallback")
            return self._get_fallback_response(message)

        try:
            # Build rich user context
            user_context = self._build_user_context(user)

            # Build conversation history
            history_text = ""
            for h in history[-10:]:
                history_text += f"{h['role'].capitalize()}: {h['content']}\n"

            # Build full prompt
            full_prompt = f"""{SYSTEM_PROMPT}

USER PROFILE:
{user_context}

CURRENT PAGE: {page_context or 'Dashboard'}

CONVERSATION HISTORY:
{history_text}

USER MESSAGE: {message}

Provide a helpful, personalized response:"""

            print(f"[AI CHAT] Calling Gemini API with user context...")
            response = model.generate_content(full_prompt)
            
            if response.text:
                print(f"[AI CHAT] ✅ Gemini response received")
                return response.text.strip()
            return "I couldn't process that request. Could you try rephrasing your question?"

        except Exception as e:
            print(f"[AI CHAT] ❌ Gemini API Error: {e}")
            return self._get_fallback_response(message)
    
    def _build_user_context(self, user):
        """Build detailed user context for personalized responses"""
        context_parts = [f"Username: {user.username}"]
        
        try:
            from apps.users.models import FreelancerProfile
            from apps.agents.models import IngestionJob
            
            profile = FreelancerProfile.objects.filter(user=user).first()
            if profile:
                if profile.title:
                    context_parts.append(f"Title: {profile.title}")
                if profile.skills:
                    context_parts.append(f"Skills: {', '.join(profile.skills[:8])}")
                if profile.experience_years:
                    context_parts.append(f"Experience: {profile.experience_years} years")
                if profile.hourly_rate:
                    context_parts.append(f"Current Rate: ${profile.hourly_rate}/hr")
                if profile.bio:
                    context_parts.append(f"Bio: {profile.bio[:200]}")
            
            # Get latest analysis data
            latest_job = IngestionJob.objects.filter(user=user, status='done').first()
            if latest_job and latest_job.result:
                result = latest_job.result
                score = result.get('score_result', {})
                if score.get('tier'):
                    context_parts.append(f"Skill Tier: {score.get('tier')}")
                if score.get('overall_score'):
                    context_parts.append(f"Readiness Score: {int(score.get('overall_score', 0) * 100)}%")
                benchmark = result.get('benchmark', {})
                if benchmark.get('user_percentile'):
                    context_parts.append(f"Market Percentile: {benchmark.get('user_percentile')}th")
                    
        except Exception as e:
            print(f"[AI CHAT] Error building context: {e}")
        
        return "\n".join(context_parts)

    def _get_fallback_response(self, message):
        """Smart fallback responses when Gemini is unavailable"""
        lower_msg = message.lower()
        
        # Pricing & Rates
        if any(word in lower_msg for word in ['price', 'rate', 'earning', 'money', 'charge', 'hourly', 'salary']):
            return """**Pricing Strategy Tips:**

• Research competitors on Upwork/Fiverr in your niche
• Start at market rate, increase 10-15% every 3-6 months
• Value-based pricing often beats hourly for experienced freelancers
• Junior devs: $25-45/hr, Mid-level: $50-85/hr, Senior: $100+/hr

**Quick wins to justify higher rates:**
- Add case studies with ROI metrics
- Get client testimonials
- Specialize in a high-demand niche"""

        # Roadmap & Learning
        if any(word in lower_msg for word in ['roadmap', 'task', 'plan', 'learn', 'skill']):
            return """**Your Learning Roadmap:**

Focus on completing tasks in order - each builds on the previous. Here's my advice:

• **Prioritize**: Finish 'in-progress' items before starting new ones
• **Practice**: Build mini-projects for each skill you learn
• **Document**: Add completed projects to your portfolio immediately

Check your Roadmap page for personalized next steps based on your skill gaps!"""

        # Mentorship
        if any(word in lower_msg for word in ['mentor', 'mentorship', 'coach', 'guidance']):
            return """**Finding the Right Mentor:**

A good mentor can accelerate your growth by 2-3x. Look for:

• **Relevant experience**: Someone who's done what you want to do
• **Communication style**: Regular check-ins work best
• **Actionable feedback**: They should give specific, practical advice

Browse our Mentors page - filter by your skill gaps for best matches!"""

        # Portfolio
        if any(word in lower_msg for word in ['portfolio', 'project', 'showcase', 'work']):
            return """**Portfolio Optimization Tips:**

Your portfolio is your #1 sales tool. Make it count:

• **Quality > Quantity**: 3-5 excellent projects beat 10 mediocre ones
• **Show process**: Include problem → solution → results
• **Add metrics**: "Increased conversion by 40%" beats "Built a website"
• **Live demos**: Working links are essential

Use our Portfolio Builder to create compelling case studies!"""

        # Clients
        if any(word in lower_msg for word in ['client', 'customer', 'proposal', 'pitch', 'job']):
            return """**Client Acquisition Strategy:**

• **Niche down**: Specialists earn 2-3x more than generalists
• **Warm outreach**: LinkedIn connections convert better than cold emails
• **Show don't tell**: Send a quick audit or suggestion with your pitch
• **Follow up**: 80% of deals close after 5+ touchpoints

Pro tip: Your best clients come from referrals - always ask happy clients!"""

        # Greetings
        if any(word in lower_msg for word in ['hello', 'hi', 'hey', 'start']):
            return """Hey there! 👋 I'm your FairFound AI assistant.

I can help you with:
• **Pricing** - What to charge for your services
• **Portfolio** - How to showcase your work
• **Skills** - What to learn next
• **Clients** - How to find and keep them
• **Mentorship** - Finding the right guidance

What would you like to work on today?"""

        # Help
        if any(word in lower_msg for word in ['help', 'what can you', 'feature', 'how do']):
            return """**I'm here to help you succeed as a freelancer!**

Ask me about:
• 💰 Pricing strategies and rate negotiation
• 📁 Portfolio optimization
• 🎯 Skill development roadmaps
• 🤝 Client acquisition techniques
• 👨‍🏫 Finding the right mentor
• 📈 Growing your freelance business

Just type your question and I'll give you actionable advice!"""

        # Default
        return """I'm your freelance career assistant! I can help with:

• Pricing and rates
• Portfolio building
• Skill development
• Client acquisition
• Career strategy

What specific challenge are you facing today?"""


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

        # Get AI response using shared logic
        chat_view = AIChatView()
        response = chat_view._get_gemini_response(message, page_context, history, request.user)
        
        return Response({
            'response': response
        })
