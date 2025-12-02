from django.contrib import admin
from .models import RoadmapStep, Task

@admin.register(RoadmapStep)
class RoadmapStepAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'status', 'type', 'order']

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'status', 'due_date', 'step']
