from rest_framework import serializers
from .models import Portfolio, PortfolioProject, Proposal


class PortfolioProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioProject
        fields = ['id', 'title', 'description', 'tags', 'image', 'url', 'order']


class PortfolioSerializer(serializers.ModelSerializer):
    projects = PortfolioProjectSerializer(many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = ['id', 'tagline', 'about', 'projects', 'created_at', 'updated_at']


class GeneratePortfolioSerializer(serializers.Serializer):
    pass  # Uses profile data


class ProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proposal
        fields = ['id', 'job_description', 'client_name', 'tone', 'generated_content', 'created_at']


class GenerateProposalSerializer(serializers.Serializer):
    job_description = serializers.CharField()
    client_name = serializers.CharField(required=False, allow_blank=True)
    tone = serializers.CharField(default='professional')
