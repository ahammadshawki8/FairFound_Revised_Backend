from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import ProfileAnalysis, SentimentAnalysis
from .serializers import ProfileAnalysisSerializer, ProfileAnalysisInputSerializer, SentimentAnalysisSerializer, SentimentInputSerializer
from .services import analyze_profile_with_gemini, analyze_sentiment_with_gemini


class AnalyzeProfileView(APIView):
    def post(self, request):
        serializer = ProfileAnalysisInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = analyze_profile_with_gemini(serializer.validated_data)
        analysis = ProfileAnalysis.objects.create(user=request.user, **result)
        return Response(ProfileAnalysisSerializer(analysis).data, status=status.HTTP_201_CREATED)


class AnalysisHistoryView(generics.ListAPIView):
    serializer_class = ProfileAnalysisSerializer

    def get_queryset(self):
        return ProfileAnalysis.objects.filter(user=self.request.user)


class SentimentAnalyzeView(APIView):
    def post(self, request):
        serializer = SentimentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        results = analyze_sentiment_with_gemini(serializer.validated_data['reviews'])
        analyses = []
        for result in results:
            analysis = SentimentAnalysis.objects.create(user=request.user, **result)
            analyses.append(analysis)
        return Response(SentimentAnalysisSerializer(analyses, many=True).data, status=status.HTTP_201_CREATED)


class SentimentHistoryView(generics.ListAPIView):
    serializer_class = SentimentAnalysisSerializer

    def get_queryset(self):
        return SentimentAnalysis.objects.filter(user=self.request.user)
