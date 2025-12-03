from rest_framework import serializers
from .models import RoadmapStep, Task


class TaskSerializer(serializers.ModelSerializer):
    step_id = serializers.PrimaryKeyRelatedField(source='step', queryset=RoadmapStep.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Task
        fields = ['id', 'step_id', 'title', 'description', 'due_date', 'status', 'feedback', 'created_at']


class RoadmapStepSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = RoadmapStep
        fields = ['id', 'title', 'description', 'duration', 'status', 'type', 'resources', 'mentor_approved', 'mentor_notes', 'order', 'tasks', 'created_at']


class GenerateRoadmapSerializer(serializers.Serializer):
    skill_gaps = serializers.ListField(child=serializers.CharField())
