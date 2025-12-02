from rest_framework import serializers
from .models import ProfileAnalysis, SentimentAnalysis


class ProfileAnalysisSerializer(serializers.ModelSerializer):
    pricing_suggestion = serializers.SerializerMethodField()
    metrics = serializers.SerializerMethodField()

    class Meta:
        model = ProfileAnalysis
        fields = ['id', 'global_readiness_score', 'market_percentile', 'projected_earnings',
                  'strengths', 'weaknesses', 'opportunities', 'threats', 'skill_gaps',
                  'pricing_suggestion', 'metrics', 'created_at']

    def get_pricing_suggestion(self, obj):
        return {'current': float(obj.pricing_current), 'recommended': float(obj.pricing_recommended), 'reasoning': obj.pricing_reasoning}

    def get_metrics(self, obj):
        return {'portfolioScore': obj.portfolio_score, 'githubScore': obj.github_score, 
                'communicationScore': obj.communication_score, 'techStackScore': obj.tech_stack_score}


class ProfileAnalysisInputSerializer(serializers.Serializer):
    name = serializers.CharField()
    title = serializers.CharField()
    bio = serializers.CharField(allow_blank=True)
    skills = serializers.ListField(child=serializers.CharField())
    experience_years = serializers.IntegerField()
    hourly_rate = serializers.DecimalField(max_digits=10, decimal_places=2)


class SentimentAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = SentimentAnalysis
        fields = ['id', 'review_text', 'sentiment', 'confidence', 'keywords', 'actionable_steps', 'created_at']


class SentimentInputSerializer(serializers.Serializer):
    reviews = serializers.ListField(child=serializers.CharField())
