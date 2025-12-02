from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Portfolio, PortfolioProject, Proposal
from .serializers import PortfolioSerializer, ProposalSerializer, GenerateProposalSerializer


class PortfolioView(generics.RetrieveUpdateAPIView):
    serializer_class = PortfolioSerializer

    def get_object(self):
        portfolio, _ = Portfolio.objects.get_or_create(user=self.request.user)
        return portfolio


class GeneratePortfolioView(APIView):
    def post(self, request):
        portfolio, _ = Portfolio.objects.get_or_create(user=request.user)
        # Mock AI generation
        portfolio.tagline = "Building digital experiences that matter."
        portfolio.about = "Passionate developer focusing on creating intuitive and performant web applications."
        portfolio.save()
        
        # Create sample projects
        PortfolioProject.objects.filter(portfolio=portfolio).delete()
        projects = [
            {'title': 'E-commerce Dashboard', 'description': 'Analytics dashboard using React and D3.', 'tags': ['React', 'D3', 'Node']},
            {'title': 'Social API', 'description': 'Scalable backend for a social network.', 'tags': ['PostgreSQL', 'Redis', 'Go']},
        ]
        for i, proj in enumerate(projects):
            PortfolioProject.objects.create(portfolio=portfolio, order=i, **proj)
        
        return Response(PortfolioSerializer(portfolio).data)


class ProposalGenerateView(APIView):
    def post(self, request):
        serializer = GenerateProposalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Mock AI generation
        generated = f"Dear {data.get('client_name', 'Hiring Manager')},\n\nI am writing to express my interest in your project.\n\nBest regards"
        
        proposal = Proposal.objects.create(
            user=request.user,
            job_description=data['job_description'],
            client_name=data.get('client_name', ''),
            tone=data.get('tone', 'professional'),
            generated_content=generated
        )
        return Response(ProposalSerializer(proposal).data, status=status.HTTP_201_CREATED)


class ProposalHistoryView(generics.ListAPIView):
    serializer_class = ProposalSerializer

    def get_queryset(self):
        return Proposal.objects.filter(user=self.request.user)
