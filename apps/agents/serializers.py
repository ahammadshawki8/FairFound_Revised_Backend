"""
Serializers for Junior Frontend Developer Analysis
"""
from rest_framework import serializers
from .models import IngestionJob, Evidence, ScoreSnapshot, BenchmarkCohort, AIInsight


class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidence
        fields = ['id', 'source', 'extracted_data', 'confidence', 'created_at']


class ScoreSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreSnapshot
        fields = [
            'id', 'overall_score', 'breakdown', 'llm_rationale', 
            'improvements', 'confidence', 'flagged_for_human', 'created_at'
        ]


class IngestionJobSerializer(serializers.ModelSerializer):
    evidence = EvidenceSerializer(many=True, read_only=True)
    scores = ScoreSnapshotSerializer(many=True, read_only=True)
    latest_score = serializers.SerializerMethodField()
    tier = serializers.SerializerMethodField()
    percentile = serializers.SerializerMethodField()

    class Meta:
        model = IngestionJob
        fields = [
            'id', 'status', 'result', 'evidence', 'scores', 
            'latest_score', 'tier', 'percentile',
            'error_message', 'created_at', 'updated_at'
        ]

    def get_latest_score(self, obj):
        latest = obj.scores.first()
        if latest:
            return {
                'overall_score': latest.overall_score,
                'confidence': latest.confidence,
                'flagged': latest.flagged_for_human
            }
        return None

    def get_tier(self, obj):
        if obj.result:
            return obj.result.get('score_result', {}).get('tier', 'Unknown')
        return None

    def get_percentile(self, obj):
        if obj.result:
            return obj.result.get('benchmark', {}).get('user_percentile', 0)
        return None


class OnboardingInputSerializer(serializers.Serializer):
    """Input serializer for junior frontend developer onboarding"""
    # Required
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    
    # Skills (allow empty for initial onboarding)
    skills = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list,
        help_text="List of technical skills (e.g., ['react', 'javascript', 'css'])"
    )
    
    # Experience (no max limit)
    experience_years = serializers.FloatField(
        min_value=0, 
        required=False,
        default=0,
        help_text="Years of experience"
    )
    
    # Optional profile info
    title = serializers.CharField(max_length=200, required=False, allow_blank=True, default='Junior Frontend Developer')
    bio = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(max_length=200, required=False, allow_blank=True)
    hourly_rate = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    
    # External links
    github_username = serializers.CharField(
        max_length=100, 
        required=False,
        allow_blank=True,
        help_text="GitHub username (not full URL)"
    )
    portfolio_url = serializers.URLField(required=False, allow_blank=True)
    
    # Portfolio details
    project_count = serializers.IntegerField(min_value=0, required=False, default=0)
    has_live_demos = serializers.BooleanField(required=False, default=False)
    
    # CV upload
    cv_file = serializers.FileField(required=False)

    def validate_skills(self, value):
        """Normalize skills to lowercase"""
        return [skill.lower().strip() for skill in value if skill.strip()]

    def validate_github_username(self, value):
        """Extract username if full URL provided"""
        if value and 'github.com/' in value:
            return value.split('github.com/')[-1].strip('/')
        return value


class ScoreAnalysisSerializer(serializers.Serializer):
    """Serializer for score analysis response"""
    job_id = serializers.IntegerField()
    status = serializers.CharField()
    category = serializers.CharField()
    overall_score = serializers.FloatField()
    tier = serializers.CharField()
    tier_color = serializers.CharField()
    breakdown = serializers.DictField()
    benchmark = serializers.DictField()
    percentile = serializers.IntegerField()
    evaluation = serializers.DictField()
    improvements = serializers.ListField()
    skills_detected = serializers.ListField()
    confidence = serializers.FloatField()
    data_sources = serializers.ListField()
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField()


class BenchmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = BenchmarkCohort
        fields = [
            'id', 'name', 'skill_category', 'percentiles', 
            'avg_hourly_rate', 'avg_experience_years', 
            'common_skills', 'sample_size', 'is_synthetic'
        ]


class HumanReviewSerializer(serializers.Serializer):
    """Serializer for human review actions"""
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    notes = serializers.CharField(required=False, allow_blank=True)


class QuickAnalyzeSerializer(serializers.Serializer):
    """Serializer for quick analysis endpoint"""
    skills = serializers.ListField(
        child=serializers.CharField(),
        min_length=1
    )
    github_username = serializers.CharField(required=False)
    experience_years = serializers.FloatField(min_value=0, default=0)


class AIInsightSerializer(serializers.ModelSerializer):
    """Serializer for AI insights"""
    class Meta:
        model = AIInsight
        fields = [
            'id', 'insight_type', 'title', 'content', 'metadata',
            'relevance_score', 'is_read', 'is_bookmarked', 
            'generated_at', 'expires_at'
        ]
        read_only_fields = ['id', 'generated_at']
