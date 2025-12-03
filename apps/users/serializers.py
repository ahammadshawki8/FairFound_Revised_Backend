from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, FreelancerProfile, MentorProfile


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['role'] = user.role
        token['username'] = user.username
        return token


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'role', 'avatar', 'is_pro', 'xp', 'level', 'streak']
        read_only_fields = ['id', 'xp', 'level', 'streak']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password_confirm', 'role']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match'})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        if user.role == 'freelancer':
            FreelancerProfile.objects.create(user=user)
        elif user.role == 'mentor':
            MentorProfile.objects.create(user=user)
        return user


class FreelancerProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    avatar_url = serializers.SerializerMethodField()
    connected_mentor_details = serializers.SerializerMethodField()

    class Meta:
        model = FreelancerProfile
        fields = ['id', 'name', 'email', 'avatar_url', 'title', 'bio', 'skills', 'experience_years', 
                  'hourly_rate', 'github_username', 'portfolio_url', 'location', 'connected_mentor', 
                  'connected_mentor_details', 'created_at']

    def get_avatar_url(self, obj):
        if obj.user.avatar:
            return obj.user.avatar.url
        return None

    def get_connected_mentor_details(self, obj):
        if obj.connected_mentor:
            mentor = obj.connected_mentor
            return {
                'id': mentor.id,
                'user_id': mentor.user.id,
                'name': mentor.user.username,
                'title': mentor.title,
                'company': mentor.company,
                'specialties': mentor.specialties,
                'rate': float(mentor.rate),
                'rating': float(mentor.rating),
                'image_url': mentor.user.avatar.url if mentor.user.avatar else None,
            }
        return None


class MentorProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    image_url = serializers.SerializerMethodField()
    mentee_count = serializers.SerializerMethodField()

    class Meta:
        model = MentorProfile
        fields = ['id', 'user_id', 'name', 'image_url', 'title', 'company', 'bio', 'specialties', 'rate', 
                  'rating', 'total_reviews', 'is_available', 'session_duration', 'timezone', 'mentee_count']
        read_only_fields = ['id', 'user_id', 'rating', 'total_reviews']

    def get_image_url(self, obj):
        if obj.user.avatar:
            return obj.user.avatar.url
        return None

    def get_mentee_count(self, obj):
        return obj.mentees.count()
