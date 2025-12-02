from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, FreelancerProfile, MentorProfile
from .serializers import (CustomTokenObtainPairSerializer, UserSerializer, 
                          UserRegistrationSerializer, FreelancerProfileSerializer, MentorProfileSerializer)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {'refresh': str(refresh), 'access': str(refresh.access_token)}
        }, status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Successfully logged out'})
        except Exception:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(APIView):
    def get(self, request):
        data = UserSerializer(request.user).data
        if request.user.role == 'freelancer':
            try:
                profile = FreelancerProfile.objects.get(user=request.user)
                data['profile'] = FreelancerProfileSerializer(profile).data
            except FreelancerProfile.DoesNotExist:
                pass
        elif request.user.role == 'mentor':
            try:
                profile = MentorProfile.objects.get(user=request.user)
                data['profile'] = MentorProfileSerializer(profile).data
            except MentorProfile.DoesNotExist:
                pass
        return Response(data)


class FreelancerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = FreelancerProfileSerializer

    def get_object(self):
        profile, _ = FreelancerProfile.objects.get_or_create(user=self.request.user)
        return profile


class MentorProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = MentorProfileSerializer

    def get_object(self):
        profile, _ = MentorProfile.objects.get_or_create(user=self.request.user)
        return profile


class AvatarUploadView(APIView):
    def post(self, request):
        if 'avatar' not in request.FILES:
            return Response({'error': 'No avatar file provided'}, status=status.HTTP_400_BAD_REQUEST)
        request.user.avatar = request.FILES['avatar']
        request.user.save()
        return Response({'avatar_url': request.user.avatar.url})
