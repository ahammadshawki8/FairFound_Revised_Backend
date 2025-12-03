from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [('freelancer', 'Freelancer'), ('mentor', 'Mentor')]
    
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='freelancer')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    is_pro = models.BooleanField(default=False)
    xp = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    streak = models.IntegerField(default=0)
    last_activity = models.DateField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']


class FreelancerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='freelancer_profile')
    title = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    skills = models.JSONField(default=list)
    experience_years = models.IntegerField(default=0)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    github_username = models.CharField(max_length=100, blank=True)
    portfolio_url = models.URLField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    connected_mentor = models.ForeignKey('MentorProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='mentees')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class MentorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mentor_profile')
    title = models.CharField(max_length=200, blank=True)
    company = models.CharField(max_length=200, blank=True)
    bio = models.TextField(blank=True)
    specialties = models.JSONField(default=list)
    rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_reviews = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)
    session_duration = models.IntegerField(default=45)
    timezone = models.CharField(max_length=50, default='America/New_York')
    # Availability slots: [{"day": "monday", "startTime": "09:00", "endTime": "17:00"}, ...]
    availability_slots = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
