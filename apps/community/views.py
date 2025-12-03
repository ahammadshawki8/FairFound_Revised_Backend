from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import Post, PostLike, Comment
from .serializers import PostSerializer, CommentSerializer
from apps.users.models import FreelancerProfile, User
from apps.roadmap.models import Task


class PostListCreateView(generics.ListCreateAPIView):
    serializer_class = PostSerializer
    queryset = Post.objects.all()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PostSerializer
    queryset = Post.objects.all()

    def get_queryset(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return Post.objects.filter(author=self.request.user)
        return Post.objects.all()


class PostLikeView(APIView):
    def post(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
            like, created = PostLike.objects.get_or_create(post=post, user=request.user)
            if not created:
                like.delete()
                return Response({'liked': False})
            return Response({'liked': True})
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)


class PostCommentView(generics.CreateAPIView):
    serializer_class = CommentSerializer

    def perform_create(self, serializer):
        post = Post.objects.get(pk=self.kwargs['pk'])
        serializer.save(author=self.request.user, post=post)


class PodMembersView(APIView):
    """Get pod members - freelancers under the same mentor"""
    def get(self, request):
        try:
            profile = FreelancerProfile.objects.get(user=request.user)
            mentor = profile.connected_mentor
            
            if not mentor:
                return Response({'members': [], 'mentor_name': None})
            
            # Get all freelancers under the same mentor
            pod_members = FreelancerProfile.objects.filter(connected_mentor=mentor)
            
            # Calculate stats for each member
            today = timezone.now().date()
            week_start = today - timedelta(days=today.weekday())
            
            members_data = []
            for member in pod_members:
                # Tasks completed this week
                tasks_this_week = Task.objects.filter(
                    user=member.user,
                    status='completed',
                    updated_at__date__gte=week_start
                ).count()
                
                # Total tasks completed
                total_tasks = Task.objects.filter(
                    user=member.user,
                    status='completed'
                ).count()
                
                # Calculate streak (consecutive days with completed tasks)
                streak = 0
                check_date = today
                while True:
                    has_task = Task.objects.filter(
                        user=member.user,
                        status='completed',
                        updated_at__date=check_date
                    ).exists()
                    if has_task:
                        streak += 1
                        check_date -= timedelta(days=1)
                    else:
                        break
                
                members_data.append({
                    'id': member.id,
                    'user_id': member.user.id,
                    'name': member.user.username,
                    'avatar_url': member.user.avatar.url if member.user.avatar else None,
                    'title': member.title or 'Freelancer',
                    'tasks_this_week': tasks_this_week,
                    'total_tasks': total_tasks,
                    'streak': streak,
                    'is_me': member.user == request.user
                })
            
            return Response({
                'members': members_data,
                'mentor_name': mentor.user.username,
                'mentor_title': mentor.title
            })
        except FreelancerProfile.DoesNotExist:
            return Response({'members': [], 'mentor_name': None})


class HeatmapDataView(APIView):
    """Get heatmap data for task completions over the last year"""
    def get(self, request):
        today = timezone.now().date()
        year_ago = today - timedelta(days=365)
        
        # Get all completed tasks for the user in the last year
        completed_tasks = Task.objects.filter(
            user=request.user,
            status='completed',
            updated_at__date__gte=year_ago
        ).values('updated_at__date').annotate(count=Count('id'))
        
        # Create a dict for quick lookup
        task_counts = {item['updated_at__date']: item['count'] for item in completed_tasks}
        
        # Generate heatmap data for 52 weeks
        weeks = []
        for week in range(51, -1, -1):
            days = []
            for day in range(7):
                date = today - timedelta(days=week * 7 + (6 - day))
                count = task_counts.get(date, 0)
                
                # Calculate level (0-4) based on count
                if count == 0:
                    level = 0
                elif count == 1:
                    level = 1
                elif count == 2:
                    level = 2
                elif count <= 4:
                    level = 3
                else:
                    level = 4
                
                days.append({
                    'date': date.isoformat(),
                    'count': count,
                    'level': level
                })
            weeks.append(days)
        
        # Calculate total contributions
        total = sum(task_counts.values())
        
        return Response({
            'weeks': weeks,
            'total_contributions': total
        })


class RecentActivityView(APIView):
    """Get recent task completions from pod members"""
    def get(self, request):
        try:
            profile = FreelancerProfile.objects.get(user=request.user)
            mentor = profile.connected_mentor
            
            if not mentor:
                return Response({'activities': []})
            
            # Get all freelancers under the same mentor
            pod_users = FreelancerProfile.objects.filter(
                connected_mentor=mentor
            ).values_list('user_id', flat=True)
            
            # Get recent completed tasks from pod members
            recent_tasks = Task.objects.filter(
                user_id__in=pod_users,
                status='completed'
            ).select_related('user', 'step').order_by('-updated_at')[:20]
            
            activities = []
            for task in recent_tasks:
                # Calculate time ago
                delta = timezone.now() - task.updated_at
                if delta.days == 0:
                    if delta.seconds < 3600:
                        time_ago = f"{delta.seconds // 60} minutes ago"
                    else:
                        time_ago = f"{delta.seconds // 3600} hours ago"
                elif delta.days == 1:
                    time_ago = "Yesterday"
                else:
                    time_ago = f"{delta.days} days ago"
                
                activities.append({
                    'id': task.id,
                    'user_id': task.user.id,
                    'user_name': task.user.username,
                    'user_avatar': task.user.avatar.url if task.user.avatar else None,
                    'task_title': task.title,
                    'step_title': task.step.title if task.step else 'General Task',
                    'completed_at': task.updated_at.isoformat(),
                    'time_ago': time_ago,
                    'is_me': task.user == request.user
                })
            
            return Response({'activities': activities})
        except FreelancerProfile.DoesNotExist:
            return Response({'activities': []})
