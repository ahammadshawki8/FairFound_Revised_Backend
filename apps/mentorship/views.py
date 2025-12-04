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


class MentorPublicAvailabilityView(APIView):
    """Get a specific mentor's availability (public endpoint for booking)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        try:
            mentor = MentorProfile.objects.get(pk=pk)
            return Response({
                'slots': mentor.availability_slots or [],
                'session_duration': mentor.session_duration,
                'timezone': mentor.timezone,
            })
        except MentorProfile.DoesNotExist:
            return Response({'error': 'Mentor not found'}, status=status.HTTP_404_NOT_FOUND)


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
            from apps.analysis.services import generate_roadmap_with_gemini
            from apps.roadmap.models import RoadmapStep, Task
            from datetime import date, timedelta
            
            mentor = MentorProfile.objects.get(pk=pk)
            profile = FreelancerProfile.objects.get(user=request.user)
            profile.connected_mentor = mentor
            profile.save()
            request.user.is_pro = True
            request.user.save()
            
            # Generate personalized roadmap with tasks using Gemini
            user_skills = profile.skills or []
            # Get skill gaps from latest analysis if available
            skill_gaps = []
            try:
                from apps.agents.models import AgentRun
                latest_run = AgentRun.objects.filter(user=request.user).order_by('-created_at').first()
                if latest_run and latest_run.benchmark_result:
                    skill_gaps = latest_run.benchmark_result.get('market_insights', {}).get('skill_gaps', [])
            except:
                pass
            
            # Use default skill gaps if none found
            if not skill_gaps:
                skill_gaps = ['Advanced React', 'TypeScript', 'System Design']
            
            # Delete existing roadmap and tasks
            Task.objects.filter(user=request.user).delete()
            RoadmapStep.objects.filter(user=request.user).delete()
            
            # Generate new roadmap with Gemini (includes tasks)
            steps_data = generate_roadmap_with_gemini({}, skill_gaps, user_skills)
            
            created_steps = []
            total_tasks = 0
            for i, step_data in enumerate(steps_data):
                step = RoadmapStep.objects.create(
                    user=request.user,
                    order=i,
                    title=step_data.get('title', ''),
                    description=step_data.get('description', ''),
                    duration=step_data.get('duration', '1 week'),
                    status=step_data.get('status', 'pending'),
                    type=step_data.get('type', 'skill'),
                    mentor_approved=True,
                )
                created_steps.append(step)
                
                # Create tasks for this step
                tasks_data = step_data.get('tasks', [])
                for j, task_data in enumerate(tasks_data):
                    Task.objects.create(
                        user=request.user,
                        step=step,
                        title=task_data.get('title', f'Task {j+1}'),
                        description=task_data.get('description', ''),
                        due_date=date.today() + timedelta(days=7 * (i + 1) + j * 2),
                        status='pending',
                    )
                    total_tasks += 1
            
            return Response({
                'message': 'Connected successfully',
                'roadmap_generated': True,
                'steps_count': len(created_steps),
                'tasks_count': total_tasks
            })
        except MentorProfile.DoesNotExist:
            return Response({'error': 'Mentor not found'}, status=status.HTTP_404_NOT_FOUND)


class DisconnectMentorView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def _disconnect(self, request, pk):
        """Internal method to handle disconnect logic"""
        print(f"[MENTORSHIP] Disconnect request from user {request.user.username} for mentor ID {pk}")
        
        try:
            mentor = MentorProfile.objects.get(pk=pk)
            print(f"[MENTORSHIP] Found mentor: {mentor.user.username}")
            
            profile = FreelancerProfile.objects.get(user=request.user)
            print(f"[MENTORSHIP] Found freelancer profile, current mentor: {profile.connected_mentor}")
            
            # Verify user is connected to this mentor
            if profile.connected_mentor != mentor:
                print(f"[MENTORSHIP] ❌ User not connected to this mentor. Connected to: {profile.connected_mentor_id}")
                return Response({'error': 'Not connected to this mentor'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Clear the connection
            profile.connected_mentor = None
            profile.save()
            print(f"[MENTORSHIP] ✅ Cleared connected_mentor for {request.user.username}")
            
            # Update user's pro status
            request.user.is_pro = False
            request.user.save()
            print(f"[MENTORSHIP] ✅ Updated is_pro to False for {request.user.username}")
            
            print(f"[MENTORSHIP] ✅ Successfully disconnected {request.user.username} from mentor {mentor.user.username}")
            
            return Response({
                'message': 'Disconnected successfully',
                'mentor_id': pk,
                'mentee_removed': True
            })
        except MentorProfile.DoesNotExist:
            print(f"[MENTORSHIP] ❌ Mentor with ID {pk} not found")
            return Response({'error': 'Mentor not found'}, status=status.HTTP_404_NOT_FOUND)
        except FreelancerProfile.DoesNotExist:
            print(f"[MENTORSHIP] ❌ Freelancer profile not found for user {request.user.username}")
            return Response({'error': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, pk):
        print(f"[MENTORSHIP] DELETE request received for mentor {pk}")
        return self._disconnect(request, pk)
    
    def post(self, request, pk):
        print(f"[MENTORSHIP] POST request received for mentor {pk}")
        return self._disconnect(request, pk)


class MyReviewsView(APIView):
    """Get reviews for the currently logged-in mentor"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if request.user.role != 'mentor':
            return Response({'error': 'Not a mentor'}, status=status.HTTP_403_FORBIDDEN)
        try:
            mentor_profile = MentorProfile.objects.get(user=request.user)
            reviews = MentorReview.objects.filter(mentor=mentor_profile).order_by('-created_at')
            serializer = MentorReviewSerializer(reviews, many=True)
            return Response(serializer.data)
        except MentorProfile.DoesNotExist:
            return Response({'error': 'Mentor profile not found'}, status=status.HTTP_404_NOT_FOUND)


class MentorAvailabilityView(APIView):
    """Get or update mentor's availability settings"""
    
    def get(self, request):
        if request.user.role != 'mentor':
            return Response({'error': 'Not a mentor'}, status=status.HTTP_403_FORBIDDEN)
        try:
            profile = MentorProfile.objects.get(user=request.user)
            return Response({
                'slots': profile.availability_slots or [],
                'session_duration': profile.session_duration,
                'timezone': profile.timezone,
            })
        except MentorProfile.DoesNotExist:
            return Response({'error': 'Mentor profile not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def put(self, request):
        if request.user.role != 'mentor':
            return Response({'error': 'Not a mentor'}, status=status.HTTP_403_FORBIDDEN)
        try:
            profile = MentorProfile.objects.get(user=request.user)
            
            if 'slots' in request.data:
                profile.availability_slots = request.data['slots']
            if 'session_duration' in request.data:
                profile.session_duration = request.data['session_duration']
            if 'timezone' in request.data:
                profile.timezone = request.data['timezone']
            
            profile.save()
            return Response({
                'message': 'Availability updated successfully',
                'slots': profile.availability_slots,
                'session_duration': profile.session_duration,
                'timezone': profile.timezone,
            })
        except MentorProfile.DoesNotExist:
            return Response({'error': 'Mentor profile not found'}, status=status.HTTP_404_NOT_FOUND)


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
                # Include analysis data
                mentee_data['analysis'] = _get_mentee_analysis(mentee.user)
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
            # Include analysis data
            data['analysis'] = _get_mentee_analysis(mentee.user)
            return Response(data)
        except FreelancerProfile.DoesNotExist:
            return Response({'error': 'Mentee not found'}, status=status.HTTP_404_NOT_FOUND)


def _get_mentee_analysis(user):
    """Get analysis data for a mentee from their latest ingestion job"""
    try:
        from apps.agents.models import IngestionJob, ScoreSnapshot
        latest_job = IngestionJob.objects.filter(user=user, status='done').order_by('-created_at').first()
        if latest_job:
            # Get the score snapshot for this job
            score = ScoreSnapshot.objects.filter(job=latest_job).first()
            if score:
                breakdown = score.breakdown or {}
                result = latest_job.result or {}
                evaluation = result.get('evaluation', {})
                benchmark = result.get('benchmark', {})
                
                return {
                    'overall_score': round((score.overall_score or 0) * 100),
                    'percentile': benchmark.get('percentile', 0),
                    'strengths': evaluation.get('strengths', []),
                    'weaknesses': evaluation.get('areas_for_improvement', []),
                    'skill_gaps': benchmark.get('market_insights', {}).get('skill_gaps', []),
                    'summary': evaluation.get('summary', ''),
                    'market_position': evaluation.get('market_position', {}),
                    'metrics': {
                        'portfolio_score': round((breakdown.get('portfolio_quality', {}).get('raw_score', 0.5)) * 100),
                        'github_score': round((breakdown.get('github_activity', {}).get('raw_score', 0.5)) * 100),
                        'skill_score': round((breakdown.get('skill_strength', {}).get('raw_score', 0.5)) * 100),
                        'experience_score': round((breakdown.get('experience_depth', {}).get('raw_score', 0.5)) * 100),
                    }
                }
    except Exception as e:
        print(f"Error getting mentee analysis: {e}")
    return None


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
            
            # Generate new roadmap with Gemini (includes tasks in response)
            steps_data = generate_roadmap_with_gemini({}, skill_gaps, user_skills)
            
            created_steps = []
            total_tasks = 0
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
                
                # Use Gemini-generated tasks from step_data
                tasks_data = step_data.get('tasks', [])
                for j, task_data in enumerate(tasks_data):
                    Task.objects.create(
                        user=mentee_user,
                        step=step,
                        title=task_data.get('title', f'Task {j+1}'),
                        description=task_data.get('description', ''),
                        due_date=date.today() + timedelta(days=7 * (i + 1) + j * 2),
                        status='pending',
                    )
                    total_tasks += 1
                
                created_steps.append(step)
            
            return Response({
                'message': f'Generated {len(created_steps)} steps with {total_tasks} tasks',
                'steps': RoadmapStepSerializer(created_steps, many=True).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MenteeGenerateSingleStepView(APIView):
    """Generate a single roadmap step with tasks using Gemini for preview"""
    def post(self, request, pk):
        if request.user.role != 'mentor':
            return Response({'error': 'Not a mentor'}, status=status.HTTP_403_FORBIDDEN)
        try:
            from apps.users.models import User
            from apps.analysis.services import generate_single_step_with_gemini
            
            mentee_user = User.objects.get(pk=pk)
            mentee_profile = FreelancerProfile.objects.get(user=mentee_user)
            mentor_profile = MentorProfile.objects.get(user=request.user)
            
            if mentee_profile.connected_mentor != mentor_profile:
                return Response({'error': 'Not your mentee'}, status=status.HTTP_403_FORBIDDEN)
            
            skill_gaps = request.data.get('skill_gaps', [])
            user_skills = request.data.get('user_skills', [])
            existing_steps = list(RoadmapStep.objects.filter(user=mentee_user).values_list('title', flat=True))
            
            # Generate single step with Gemini
            step_data = generate_single_step_with_gemini(skill_gaps, user_skills, existing_steps)
            
            return Response(step_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MenteeCreateStepWithTasksView(APIView):
    """Create a roadmap step with tasks after mentor review"""
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
            
            # Get the next order number
            last_step = RoadmapStep.objects.filter(user=mentee_user).order_by('-order').first()
            next_order = (last_step.order + 1) if last_step else 0
            
            # Create the step
            step = RoadmapStep.objects.create(
                user=mentee_user,
                order=next_order,
                title=request.data.get('title', ''),
                description=request.data.get('description', ''),
                duration=request.data.get('duration', '1 week'),
                type=request.data.get('type', 'skill'),
                status='pending',
                mentor_approved=True,
            )
            
            # Create tasks for this step
            tasks_data = request.data.get('tasks', [])
            created_tasks = []
            for i, task_data in enumerate(tasks_data):
                task = Task.objects.create(
                    user=mentee_user,
                    step=step,
                    title=task_data.get('title', f'Task {i+1}'),
                    description=task_data.get('description', ''),
                    due_date=date.today() + timedelta(days=7 + i * 2),
                    status='pending',
                )
                created_tasks.append(task)
            
            return Response({
                'message': f'Created step with {len(created_tasks)} tasks',
                'step': RoadmapStepSerializer(step).data
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
