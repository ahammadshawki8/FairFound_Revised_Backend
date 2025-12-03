from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import RoadmapStep, Task
from .serializers import RoadmapStepSerializer, TaskSerializer, GenerateRoadmapSerializer
from apps.analysis.services import generate_roadmap_with_gemini
from apps.users.models import FreelancerProfile


class RoadmapListView(generics.ListAPIView):
    serializer_class = RoadmapStepSerializer

    def get_queryset(self):
        return RoadmapStep.objects.filter(user=self.request.user)


class RoadmapStepCreateView(generics.CreateAPIView):
    serializer_class = RoadmapStepSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class RoadmapStepDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RoadmapStepSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'mentor':
            # Mentors can access steps of their mentees
            from apps.users.models import MentorProfile
            try:
                mentor_profile = MentorProfile.objects.get(user=user)
                mentee_users = FreelancerProfile.objects.filter(connected_mentor=mentor_profile).values_list('user', flat=True)
                return RoadmapStep.objects.filter(user__in=mentee_users)
            except MentorProfile.DoesNotExist:
                return RoadmapStep.objects.none()
        return RoadmapStep.objects.filter(user=user)


class GenerateRoadmapView(APIView):
    """
    Generate a personalized roadmap with tasks using Gemini AI.
    Deletes existing roadmap and creates new one.
    """
    def post(self, request):
        from datetime import date, timedelta
        
        serializer = GenerateRoadmapSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        skill_gaps = serializer.validated_data['skill_gaps']
        
        # Get user's current skills from profile
        user_skills = []
        try:
            profile = FreelancerProfile.objects.get(user=request.user)
            user_skills = profile.skills or []
        except FreelancerProfile.DoesNotExist:
            pass
        
        # Delete existing roadmap steps and tasks for this user
        Task.objects.filter(user=request.user).delete()
        RoadmapStep.objects.filter(user=request.user).delete()
        
        # Generate new roadmap with Gemini (now includes tasks)
        steps_data = generate_roadmap_with_gemini({}, skill_gaps, user_skills)
        
        # Create new steps and tasks in database
        steps = []
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
            )
            steps.append(step)
            
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
            'message': f'Generated {len(steps)} roadmap steps with {total_tasks} tasks',
            'steps': RoadmapStepSerializer(steps, many=True).data
        }, status=status.HTTP_201_CREATED)


class RoadmapStatusView(APIView):
    """Check if user has a roadmap and return summary"""
    def get(self, request):
        steps = RoadmapStep.objects.filter(user=request.user)
        if not steps.exists():
            return Response({
                'has_roadmap': False,
                'message': 'No roadmap generated yet'
            })
        
        completed = steps.filter(status='completed').count()
        in_progress = steps.filter(status='in-progress').count()
        pending = steps.filter(status='pending').count()
        
        return Response({
            'has_roadmap': True,
            'total_steps': steps.count(),
            'completed': completed,
            'in_progress': in_progress,
            'pending': pending,
            'progress_percentage': round((completed / steps.count()) * 100) if steps.count() > 0 else 0
        })


class TaskListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'mentor':
            # Mentors can access tasks of their mentees
            from apps.users.models import MentorProfile, FreelancerProfile
            try:
                mentor_profile = MentorProfile.objects.get(user=user)
                mentee_users = FreelancerProfile.objects.filter(connected_mentor=mentor_profile).values_list('user', flat=True)
                return Task.objects.filter(user__in=mentee_users)
            except MentorProfile.DoesNotExist:
                return Task.objects.none()
        return Task.objects.filter(user=user)


class TaskStatusUpdateView(APIView):
    def put(self, request, pk):
        try:
            user = request.user
            
            # Check if user is a mentor updating their mentee's task
            if user.role == 'mentor':
                from apps.users.models import MentorProfile, FreelancerProfile
                try:
                    mentor_profile = MentorProfile.objects.get(user=user)
                    mentee_users = FreelancerProfile.objects.filter(connected_mentor=mentor_profile).values_list('user', flat=True)
                    task = Task.objects.get(pk=pk, user__in=mentee_users)
                except MentorProfile.DoesNotExist:
                    return Response({'error': 'Mentor profile not found'}, status=status.HTTP_404_NOT_FOUND)
            else:
                # Regular user updating their own task
                task = Task.objects.get(pk=pk, user=user)
            
            old_status = task.status
            task.status = request.data.get('status', task.status)
            if 'feedback' in request.data:
                task.feedback = request.data['feedback']
            task.save()
            
            print(f"[ROADMAP] Task {pk} status updated: {old_status} -> {task.status}")
            
            return Response(TaskSerializer(task).data)
        except Task.DoesNotExist:
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)
