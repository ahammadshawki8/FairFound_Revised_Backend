from rest_framework import serializers
from .models import Session, MentorReview
from apps.users.models import MentorProfile, FreelancerProfile
from apps.users.serializers import MentorProfileSerializer


class SessionSerializer(serializers.ModelSerializer):
    mentee_name = serializers.CharField(source='mentee.username', read_only=True)
    mentee_avatar = serializers.SerializerMethodField()
    mentor_name = serializers.CharField(source='mentor.username', read_only=True)

    class Meta:
        model = Session
        fields = ['id', 'mentor', 'mentee', 'mentee_name', 'mentee_avatar', 'mentor_name',
                  'date', 'time', 'duration', 'topic', 'status', 'notes', 'meeting_link', 'created_at']

    def get_mentee_avatar(self, obj):
        if obj.mentee.avatar:
            return obj.mentee.avatar.url
        return None


class MentorReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True)
    reviewer_avatar = serializers.SerializerMethodField()

    class Meta:
        model = MentorReview
        fields = ['id', 'mentor', 'reviewer', 'reviewer_name', 'reviewer_avatar', 'rating', 'comment', 'helpful', 'created_at']

    def get_reviewer_avatar(self, obj):
        if obj.reviewer.avatar:
            return obj.reviewer.avatar.url
        return None


class MentorListSerializer(MentorProfileSerializer):
    available = serializers.BooleanField(source='is_available')
    reviews = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    class Meta(MentorProfileSerializer.Meta):
        fields = MentorProfileSerializer.Meta.fields + ['available', 'reviews', 'average_rating']

    def get_reviews(self, obj):
        reviews = MentorReview.objects.filter(mentor=obj)[:5]  # Latest 5 reviews
        return MentorReviewSerializer(reviews, many=True).data

    def get_average_rating(self, obj):
        reviews = MentorReview.objects.filter(mentor=obj)
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 2)
        return float(obj.rating)


class ConnectMentorSerializer(serializers.Serializer):
    mentor_id = serializers.IntegerField()
