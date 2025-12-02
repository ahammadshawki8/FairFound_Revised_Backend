from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Session, MentorReview
from .serializers import SessionSerializer, MentorReviewSerializer, MentorListSerializer, ConnectMentorSerializer
from apps.users.models import MentorProfile, FreelancerProfile
from apps.users.serializers import FreelancerProfileSerializer
from apps.roadmap.models import RoadmapStep, Task
from apps.roadmap.serializers import RoadmapStepSerializer, TaskSerializer


class MentorListView(generics.ListAPIView):
    serializer_class = MentorListSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = MentorProfile.objects.filter(is_available=True)
        specialty = self.request.query_params.get('specialty')
        if specialty:
            queryset = queryset.filter(specialties__contains=[specialty])
        return queryset


class MentorDetailView(generics.RetrieveAPIView):
    serializer_class = MentorListSerializer
    queryset = MentorProfile.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class MentorReviewListView(generics.ListCreateAPIView):
    serializer_class = MentorReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return MentorReview.objects.filter(mentor_id=self.kwargs['pk'])

    def perform_create(self, serializer):
        mentor = MentorProfile.objects.get(pk=self.kwargs['pk'])
        serializer.save(reviewer=self.request.user, mentor=mentor)
        # Update mentor's rating
        reviews = MentorReview.objects.filter(mentor=mentor)
        mentor.rating = sum(r.rating for r in reviews) / reviews.count()
        mentor.total_reviews = reviews.count()
        mentor.save()


class ConnectMentorView(APIView):
    def post(self, request, pk):
        try:
            mentor = MentorProfile.objects.get(pk=pk)
            profile = FreelancerProfile.objects.get(user=request.user)
            profile.connected_mentor = mentor
            profile.save()
            request.user.is_pro = True
            request.user.save()
            return Response({'message': 'Connected successfully'})
        except MentorProfile.DoesNotExist:
            return Response({'error': 'Mentor not found'}, status=status.HTTP_404_NOT_FOUND)


class DisconnectMentorView(APIView):
    def delete(self, request, pk):
        try:
            profile = FreelancerProfile.objects.get(user=request.user)
            profile.connected_mentor = None
            profile.save()
            return Response({'message': 'Disconnected successfully'})
        except FreelancerProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)


# Mentee views (for mentors)
class MenteeListView(APIView):
    def get(self, request):
        if request.user.role != 'mentor':
            return Response({'error': 'Not a mentor'}, status=status.HTTP_403_FORBIDDEN)
        try:
            mentor_profile = MentorProfile.objects.get(user=request.user)
            mentees = FreelancerProfile.objects.filter(connected_mentor=mentor_profile)
            data = []
            for mentee in mentees:
                mentee_data = FreelancerProfileSerializer(mentee).data
                mentee_data['user_id'] = mentee.user.id
                mentee_data['roadmap'] = RoadmapStepSerializer(RoadmapStep.objects.filter(user=mentee.user), many=True).data
                mentee_data['tasks'] = TaskSerializer(Task.objects.filter(user=mentee.user), many=True).data
                data.append(mentee_data)
            return Response(data)
        except MentorProfile.DoesNotExist:
            return Response({'error': 'Mentor profile not found'}, status=status.HTTP_404_NOT_FOUND)


class MenteeDetailView(APIView):
    def get(self, request, pk):
        try:
            mentee = FreelancerProfile.objects.get(pk=pk)
            # Verify mentor has access to this mentee
            if request.user.role == 'mentor':
                mentor_profile = MentorProfile.objects.get(user=request.user)
                if mentee.connected_mentor != mentor_profile:
                    return Response({'error': 'Not your mentee'}, status=status.HTTP_403_FORBIDDEN)
            data = FreelancerProfileSerializer(mentee).data
            data['user_id'] = mentee.user.id
            data['roadmap'] = RoadmapStepSerializer(RoadmapStep.objects.filter(user=mentee.user), many=True).data
            data['tasks'] = TaskSerializer(Task.objects.filter(user=mentee.user), many=True).data
            return Response(data)
        except FreelancerProfile.DoesNotExist:
            return Response({'error': 'Mentee not found'}, status=status.HTTP_404_NOT_FOUND)


class MenteeStepCreateView(APIView):
    """Create a roadmap step for a mentee (mentor only)"""
    def post(self, request, pk):
        if request.user.role != 'mentor':
            return Response({'error': 'Not a mentor'}, status=status.HTTP_403_FORBIDDEN)
        try:
            from apps.users.models import User
            mentee_user = User.objects.get(pk=pk)
            mentee_profile = FreelancerProfile.objects.get(user=mentee_user)
            mentor_profile = MentorProfile.objects.get(user=request.user)
            
            if mentee_profile.connected_mentor != mentor_profile:
                return Response({'error': 'Not your mentee'}, status=status.HTTP_403_FORBIDDEN)
            
            # Get the next order number
            max_order = RoadmapStep.objects.filter(user=mentee_user).order_by('-order').first()
            next_order = (max_order.order + 1) if max_order else 0
            
            step = RoadmapStep.objects.create(
                user=mentee_user,
                title=request.data.get('title', ''),
                description=request.data.get('description', ''),
                duration=request.data.get('duration', '1 week'),
                status=request.data.get('status', 'pending'),
                type=request.data.get('type', 'skill'),
                mentor_approved=True,
                mentor_notes=request.data.get('mentor_notes', ''),
                order=next_order,
            )
            return Response(RoadmapStepSerializer(step).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MenteeTaskCreateView(APIView):
    """Create a task for a mentee (mentor only)"""
    def post(self, request, pk):
        if request.user.role != 'mentor':
            return Response({'error': 'Not a mentor'}, status=status.HTTP_403_FORBIDDEN)
        try:
            from apps.users.models import User
            from datetime import date, timedelta
            mentee_user = User.objects.get(pk=pk)
            mentee_profile = FreelancerProfile.objects.get(user=mentee_user)
            mentor_profile = MentorProfile.objects.get(user=request.user)
            
            if mentee_profile.connected_mentor != mentor_profile:
                return Response({'error': 'Not your mentee'}, status=status.HTTP_403_FORBIDDEN)
            
            step_id = request.data.get('step_id')
            step = None
            if step_id:
                step = RoadmapStep.objects.get(pk=step_id, user=mentee_user)
            
            due_date = request.data.get('due_date')
            if not due_date:
                due_date = (date.today() + timedelta(days=7)).isoformat()
            
            task = Task.objects.create(
                user=mentee_user,
                step=step,
                title=request.data.get('title', ''),
                description=request.data.get('description', ''),
                due_date=due_date,
                status=request.data.get('status', 'pending'),
            )
            return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MenteeGenerateRoadmapView(APIView):
    """Generate a full roadmap with tasks for a mentee using Gemini"""
    def post(self, request, pk):
        if request.user.role != 'mentor':
            return Response({'error': 'Not a mentor'}, status=status.HTTP_403_FORBIDDEN)
        try:
            from apps.users.models import User
            from apps.analysis.services import generate_roadmap_with_gemini
            from datetime import date, timedelta
            
            mentee_user = User.objects.get(pk=pk)
            mentee_profile = FreelancerProfile.objects.get(user=mentee_user)
            mentor_profile = MentorProfile.objects.get(user=request.user)
            
            if mentee_profile.connected_mentor != mentor_profile:
                return Response({'error': 'Not your mentee'}, status=status.HTTP_403_FORBIDDEN)
            
            skill_gaps = request.data.get('skill_gaps', [])
            user_skills = mentee_profile.skills or []
            
            # Delete existing roadmap and tasks
            RoadmapStep.objects.filter(user=mentee_user).delete()
            Task.objects.filter(user=mentee_user).delete()
            
            # Generate new roadmap
            steps_data = generate_roadmap_with_gemini({}, skill_gaps, user_skills)
            
            created_steps = []
            for i, step_data in enumerate(steps_data):
                step = RoadmapStep.objects.create(
                    user=mentee_user,
                    order=i,
                    title=step_data.get('title', ''),
                    description=step_data.get('description', ''),
                    duration=step_data.get('duration', '1 week'),
                    status=step_data.get('status', 'pending'),
                    type=step_data.get('type', 'skill'),
                    mentor_approved=True,
                )
                
                # Create 2-3 tasks for each step
                task_titles = _generate_tasks_for_step(step_data)
                for j, task_title in enumerate(task_titles):
                    Task.objects.create(
                        user=mentee_user,
                        step=step,
                        title=task_title['title'],
                        description=task_title['description'],
                        due_date=date.today() + timedelta(days=7 * (i + 1) + j * 2),
                        status='pending',
                    )
                
                created_steps.append(step)
            
            return Response({
                'message': f'Generated {len(created_steps)} steps with tasks',
                'steps': RoadmapStepSerializer(created_steps, many=True).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


def _generate_tasks_for_step(step_data):
    """Generate task suggestions based on step type"""
    step_type = step_data.get('type', 'skill')
    title = step_data.get('title', '')
    
    if step_type == 'skill':
        return [
            {'title': f'Complete tutorial on {title}', 'description': 'Watch video tutorials and take notes on key concepts'},
            {'title': f'Practice exercises for {title}', 'description': 'Complete hands-on coding exercises to reinforce learning'},
            {'title': f'Build mini-project using {title}', 'description': 'Create a small project demonstrating the new skill'},
        ]
    elif step_type == 'project':
        return [
            {'title': 'Set up project structure', 'description': 'Initialize repository, configure tools, and plan architecture'},
            {'title': 'Implement core features', 'description': 'Build the main functionality of the project'},
            {'title': 'Add polish and deploy', 'description': 'Add styling, write README, and deploy to production'},
        ]
    else:  # branding
        return [
            {'title': 'Update profile content', 'description': 'Revise bio, skills, and experience sections'},
            {'title': 'Add project showcases', 'description': 'Document and showcase your best work with screenshots'},
        ]


# Session views
class SessionListCreateView(generics.ListCreateAPIView):
    serializer_class = SessionSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'mentor':
            return Session.objects.filter(mentor=user)
        return Session.objects.filter(mentee=user)

    def perform_create(self, serializer):
        serializer.save(mentee=self.request.user)


class SessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SessionSerializer
    queryset = Session.objects.all()


class SessionStatusView(APIView):
    def put(self, request, pk):
        try:
            session = Session.objects.get(pk=pk)
            session.status = request.data.get('status', session.status)
            session.save()
            return Response(SessionSerializer(session).data)
        except Session.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)
