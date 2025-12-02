from django.db import models
from django.conf import settings


class RoadmapStep(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('in-progress', 'In Progress'), ('completed', 'Completed')]
    TYPE_CHOICES = [('skill', 'Skill'), ('project', 'Project'), ('branding', 'Branding')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='roadmap_steps')
    title = models.CharField(max_length=200)
    description = models.TextField()
    duration = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='skill')
    mentor_approved = models.BooleanField(default=False)
    mentor_notes = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']


class Task(models.Model):
    STATUS_CHOICES = [('pending', 'Pending'), ('review', 'Review'), ('completed', 'Completed')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')
    step = models.ForeignKey(RoadmapStep, on_delete=models.CASCADE, related_name='tasks', null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date']
