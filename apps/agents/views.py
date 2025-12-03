"""
API Views for Junior Frontend Developer Analysis
"""
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import models
from .models import IngestionJob, ScoreSnapshot, BenchmarkCohort
from .serializers import (
    IngestionJobSerializer, OnboardingInputSerializer, 
    ScoreAnalysisSerializer, BenchmarkSerializer, HumanReviewSerializer
)
from .tasks import run_junior_frontend_pipeline
from .synthetic_data import get_junior_frontend_benchmark


class OnboardingSubmitView(APIView):
    """
    Submit junior frontend developer profile for analysis.
    Runs synchronously for immediate results (no Redis/Celery required).
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from .scoring import (
            calculate_skill_score, calculate_github_score,
            calculate_portfolio_score, calculate_experience_score,
            compute_overall_score, generate_improvements
        )
        from .collectors import fetch_github_metrics
        from .llm_judge import evaluate_junior_frontend
        from .models import Evidence, ScoreSnapshot
        
        print("\n" + "=" * 60)
        print("  ONBOARDING - AGENTIC AI PIPELINE (Synchronous)")
        print("=" * 60)
        
        print(f"\n📥 Received data: {request.data}")
        
        serializer = OnboardingInputSerializer(data=request.data)
        if not serializer.is_valid():
            print(f"❌ Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        print(f"✅ Validated data: {data}")
        
        # Handle CV file upload
        cv_file_path = None
        if 'cv_file' in request.FILES:
            cv_file = request.FILES['cv_file']
            file_name = f'cvs/{request.user.id}_{cv_file.name}'
            cv_file_path = default_storage.save(file_name, ContentFile(cv_file.read()))
        
        # Prepare input data
        input_data = {
            'user_id': request.user.id,
            'cv_file_path': cv_file_path,
            'github_username': data.get('github_username'),
            'portfolio_url': data.get('portfolio_url'),
            'form_fields': {
                'name': data.get('name'),
                'email': data.get('email'),
                'title': data.get('title', 'Junior Frontend Developer'),
                'skills': data.get('skills', []),
                'experience_years': data.get('experience_years', 0),
                'hourly_rate': float(data.get('hourly_rate', 0)) if data.get('hourly_rate') else None,
                'bio': data.get('bio'),
                'location': data.get('location'),
                'project_count': data.get('project_count', 0),
                'has_live_demos': data.get('has_live_demos', False)
            }
        }
        
        # Create job
        job = IngestionJob.objects.create(
            user=request.user,
            input_data=input_data,
            status='running'
        )
        
        print(f"\n📥 Job {job.id} created for user {request.user.id}")
        
        try:
            form_data = input_data.get('form_fields', {})
            skills = form_data.get('skills', [])
            github_username = input_data.get('github_username')
            experience_years = form_data.get('experience_years', 0)
            
            print(f"   Skills: {skills}")
            print(f"   GitHub: {github_username or 'Not provided'}")
            print(f"   Experience: {experience_years} years")
            
            # Store form evidence
            Evidence.objects.create(
                job=job,
                source='form',
                raw_content=str(form_data),
                extracted_data=form_data,
                confidence=1.0
            )
            
            # Calculate scores
            print("\n🎯 [AGENT 1] Skill Scoring Agent")
            skills_data = {'all_skills': [s.lower() for s in skills]}
            skill_result = calculate_skill_score(skills_data)
            print(f"   Result: {skill_result[0]:.3f} ({skill_result[1]})")
            
            print("\n🐙 [AGENT 2] GitHub Scoring Agent")
            github_result = (0.2, 'minimal', {'message': 'No GitHub provided'})
            if github_username:
                github_data = fetch_github_metrics(github_username)
                if not github_data.get('error'):
                    github_result = calculate_github_score(github_data)
                    Evidence.objects.create(
                        job=job,
                        source='github',
                        raw_content=str(github_data)[:2000],
                        extracted_data=github_data,
                        confidence=0.8
                    )
                    print(f"   Result: {github_result[0]:.3f} ({github_result[1]})")
                else:
                    print(f"   ⚠️ GitHub fetch failed: {github_data.get('error')}")
            else:
                print("   SKIPPED (no username)")
            
            print("\n🖼️ [AGENT 3] Portfolio Scoring Agent")
            portfolio_data = {
                'has_projects': bool(input_data.get('portfolio_url')),
                'project_count': form_data.get('project_count', 0),
                'has_live_demos': form_data.get('has_live_demos', False),
                'has_code_links': bool(github_username),
                'quality_score': 0.4 if input_data.get('portfolio_url') else 0.2
            }
            portfolio_result = calculate_portfolio_score(portfolio_data)
            print(f"   Result: {portfolio_result[0]:.3f} ({portfolio_result[1]})")
            
            print("\n⏱️ [AGENT 4] Experience Scoring Agent")
            experience_result = calculate_experience_score(experience_years)
            print(f"   Result: {experience_result[0]:.3f} ({experience_result[1]})")
            
            # Learning momentum
            momentum = 0.5
            if github_username and github_result[0] > 0.3:
                momentum = min(0.9, 0.3 + (github_result[0] * 0.5))
            
            features = {
                'skill': skill_result,
                'github': github_result,
                'portfolio': portfolio_result,
                'experience': experience_result,
                'learning_momentum': momentum
            }
            
            print("\n🧮 [AGENT 5] Score Aggregation Agent")
            score_result = compute_overall_score(features)
            print(f"   ✅ OVERALL SCORE: {score_result['overall_score']:.3f}")
            print(f"   TIER: {score_result['tier']}")
            
            print("\n📊 [AGENT 6] Benchmark Agent")
            benchmark = get_junior_frontend_benchmark(score_result['overall_score'])
            print(f"   Percentile: {benchmark.get('user_percentile')}th")
            
            print("\n🤖 [AGENT 7] LLM Judge Agent")
            structured_data = {'form': form_data, 'github': github_result[2] if len(github_result) > 2 else {}}
            llm_evaluation = evaluate_junior_frontend(structured_data, score_result, benchmark)
            print(f"   Evaluation type: {llm_evaluation.get('evaluation_type', 'unknown')}")
            
            print("\n💡 [AGENT 8] Improvement Generator Agent")
            improvements = generate_improvements(score_result['breakdown'])
            print(f"   Generated {len(improvements)} improvements")
            
            # Save score snapshot
            ScoreSnapshot.objects.create(
                job=job,
                overall_score=score_result['overall_score'],
                breakdown=score_result['breakdown'],
                llm_rationale=llm_evaluation.get('summary', ''),
                improvements=[imp['action'] for imp in improvements],
                confidence=0.85,
                flagged_for_human=False
            )
            
            # Update job with results
            job.result = {
                'score_result': score_result,
                'benchmark': benchmark,
                'llm_evaluation': llm_evaluation,
                'improvements': improvements,
                'skills_detected': skills
            }
            job.status = 'done'
            job.save()
            
            print("\n" + "=" * 60)
            print("  ONBOARDING COMPLETE")
            print(f"  Score: {score_result['overall_score']:.3f} | Tier: {score_result['tier']} | Percentile: {benchmark.get('user_percentile')}th")
            print("=" * 60 + "\n")
            
            # Auto-generate AI insights after successful onboarding
            print("\n💡 [AGENT 9] Auto-generating AI Insights...")
            try:
                insights_count = generate_ai_insights(request.user, job)
                print(f"   ✅ Generated {insights_count} AI insights")
            except Exception as e:
                print(f"   ⚠️ Insights generation failed: {e}")
            
            return Response({
                'job_id': job.id,
                'status': 'done',
                'overall_score': score_result['overall_score'],
                'tier': score_result['tier'],
                'percentile': benchmark.get('user_percentile', 50),
                'breakdown': score_result['breakdown'],
                'improvements': improvements,
                'benchmark': benchmark,
                'evaluation': llm_evaluation
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            job.status = 'error'
            job.error_message = str(e)
            job.save()
            return Response({
                'error': str(e),
                'job_id': job.id,
                'status': 'error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class JobListView(generics.ListAPIView):
    """List user's analysis jobs"""
    serializer_class = IngestionJobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return IngestionJob.objects.filter(user=self.request.user)


class JobDetailView(generics.RetrieveAPIView):
    """Get job status and results"""
    serializer_class = IngestionJobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return IngestionJob.objects.filter(user=self.request.user)


class LatestAnalysisView(APIView):
    """Get the latest analysis for the current user (no job_id needed)"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Fetch the most recent completed analysis for the user"""
        latest_job = IngestionJob.objects.filter(
            user=request.user,
            status='done'
        ).order_by('-created_at').first()

        if not latest_job:
            return Response({
                'has_analysis': False,
                'message': 'No completed analysis found. Please complete onboarding.'
            }, status=status.HTTP_200_OK)

        result = latest_job.result or {}
        latest_score = latest_job.scores.first()

        return Response({
            'has_analysis': True,
            'job_id': latest_job.id,
            'status': latest_job.status,
            'overall_score': latest_score.overall_score if latest_score else 0,
            'tier': result.get('score_result', {}).get('tier', 'Unknown'),
            'tier_color': result.get('score_result', {}).get('tier_color', 'gray'),
            'percentile': result.get('benchmark', {}).get('user_percentile', 0),
            'breakdown': latest_score.breakdown if latest_score else {},
            'benchmark': result.get('benchmark', {}),
            'evaluation': result.get('llm_evaluation', {}),
            'improvements': result.get('improvements', []),
            'skills_detected': result.get('skills_detected', []),
            'created_at': latest_job.created_at.isoformat(),
        })


class ScoreAnalysisView(APIView):
    """Get detailed score analysis for a completed job"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, job_id):
        try:
            job = IngestionJob.objects.get(id=job_id, user=request.user)
            
            if job.status not in ['done', 'review']:
                return Response({
                    'status': job.status,
                    'message': 'Analysis not yet complete' if job.status == 'running' else 'Analysis pending',
                    'error': job.error_message if job.status == 'error' else None
                }, status=status.HTTP_202_ACCEPTED)
            
            result = job.result or {}
            latest_score = job.scores.first()
            
            analysis = {
                'job_id': job.id,
                'status': job.status,
                'category': 'junior_frontend',
                
                # Overall results
                'overall_score': latest_score.overall_score if latest_score else 0,
                'tier': result.get('score_result', {}).get('tier', 'Unknown'),
                'tier_color': result.get('score_result', {}).get('tier_color', 'gray'),
                
                # Detailed breakdown
                'breakdown': latest_score.breakdown if latest_score else {},
                
                # Benchmark comparison
                'benchmark': result.get('benchmark', {}),
                'percentile': result.get('benchmark', {}).get('user_percentile', 0),
                
                # LLM evaluation
                'evaluation': result.get('llm_evaluation', {}),
                
                # Improvements
                'improvements': result.get('improvements', []),
                
                # Skills detected
                'skills_detected': result.get('skills_detected', []),
                
                # Metadata
                'confidence': latest_score.confidence if latest_score else 0,
                'data_sources': result.get('data_sources', []),
                'created_at': job.created_at.isoformat(),
                'completed_at': job.updated_at.isoformat()
            }
            
            return Response(analysis)
            
        except IngestionJob.DoesNotExist:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)


class BenchmarkView(APIView):
    """Get benchmark data for junior frontend developers"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Get user's latest score if available
        user_score = None
        latest_job = IngestionJob.objects.filter(
            user=request.user, 
            status='done'
        ).first()
        
        if latest_job and latest_job.scores.exists():
            user_score = latest_job.scores.first().overall_score
        
        # Get benchmark data
        benchmark = get_junior_frontend_benchmark(user_score or 0.5)
        
        # Add user context if available
        if user_score:
            benchmark['your_score'] = user_score
            benchmark['your_percentile'] = benchmark.get('user_percentile', 50)
        
        return Response(benchmark)


class RegenerateView(APIView):
    """Regenerate analysis for a job"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, job_id):
        try:
            job = IngestionJob.objects.get(id=job_id, user=request.user)
            
            # Reset job
            job.status = 'pending'
            job.error_message = ''
            job.result = None
            job.save()
            
            # Clear old data
            job.evidence.all().delete()
            job.scores.all().delete()
            
            # Restart pipeline
            run_junior_frontend_pipeline.delay(job.id)
            
            return Response({
                'message': 'Analysis restarted',
                'job_id': job.id,
                'status': 'queued'
            })
            
        except IngestionJob.DoesNotExist:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)


class QuickAnalyzeView(APIView):
    """
    Quick analysis endpoint - synchronous for demo purposes.
    Returns immediate results without creating a job.
    Allows unauthenticated access for onboarding flow.
    """
    permission_classes = [permissions.AllowAny]
    parser_classes = [JSONParser]

    def post(self, request):
        from .scoring import (
            calculate_skill_score, calculate_github_score,
            calculate_experience_score, compute_overall_score,
            generate_improvements
        )
        from .collectors import fetch_github_metrics
        
        print("\n" + "=" * 60)
        print("  QUICK ANALYZE - AGENTIC AI PIPELINE (Synchronous)")
        print("=" * 60)
        
        data = request.data
        skills = data.get('skills', [])
        github_username = data.get('github_username')
        experience_years = data.get('experience_years', 0)
        
        print(f"\n📥 INPUT DATA:")
        print(f"   Skills: {skills}")
        print(f"   GitHub: {github_username or 'Not provided'}")
        print(f"   Experience: {experience_years} years")
        
        # Calculate scores
        print("\n" + "-" * 60)
        print("  PHASE 1: RUBRIC-BASED SCORING")
        print("-" * 60)
        
        print("\n🎯 [AGENT 1] Skill Scoring Agent")
        skills_data = {'all_skills': [s.lower() for s in skills]}
        skill_result = calculate_skill_score(skills_data)
        print(f"   Result: {skill_result[0]:.3f} ({skill_result[1]})")
        
        print("\n🐙 [AGENT 2] GitHub Scoring Agent")
        github_result = (0.2, 'minimal', {'message': 'No GitHub provided'})
        if github_username:
            print(f"   Fetching data for: {github_username}")
            github_data = fetch_github_metrics(github_username)
            if not github_data.get('error'):
                github_result = calculate_github_score(github_data)
                print(f"   Result: {github_result[0]:.3f} ({github_result[1]})")
            else:
                print(f"   ⚠️ GitHub fetch failed: {github_data.get('error')}")
        else:
            print("   SKIPPED (no username)")
        
        print("\n🖼️ [AGENT 3] Portfolio Scoring Agent")
        portfolio_result = (0.3, 'basic', {'message': 'Default portfolio score'})
        print(f"   Result: {portfolio_result[0]:.3f} ({portfolio_result[1]})")
        
        print("\n⏱️ [AGENT 4] Experience Scoring Agent")
        experience_result = calculate_experience_score(experience_years)
        print(f"   Result: {experience_result[0]:.3f} ({experience_result[1]})")
        
        features = {
            'skill': skill_result,
            'github': github_result,
            'portfolio': portfolio_result,
            'experience': experience_result,
            'learning_momentum': 0.5
        }
        
        print("\n" + "-" * 60)
        print("  PHASE 2: OVERALL SCORE COMPUTATION")
        print("-" * 60)
        
        print("\n🧮 [AGENT 5] Score Aggregation Agent")
        score_result = compute_overall_score(features)
        print(f"   ✅ OVERALL SCORE: {score_result['overall_score']:.3f}")
        print(f"   TIER: {score_result['tier']}")
        
        print("\n" + "-" * 60)
        print("  PHASE 3: BENCHMARK COMPARISON")
        print("-" * 60)
        
        print("\n📊 [AGENT 6] Benchmark Agent (Synthetic Data)")
        benchmark = get_junior_frontend_benchmark(score_result['overall_score'])
        print(f"   Percentile: {benchmark.get('user_percentile')}th")
        
        print("\n" + "-" * 60)
        print("  PHASE 4: IMPROVEMENT GENERATION")
        print("-" * 60)
        
        print("\n💡 [AGENT 7] Improvement Generator Agent")
        improvements = generate_improvements(score_result['breakdown'])
        print(f"   Generated {len(improvements)} improvements")
        
        print("\n" + "=" * 60)
        print("  QUICK ANALYZE COMPLETE")
        print(f"  Score: {score_result['overall_score']:.3f} | Tier: {score_result['tier']} | Percentile: {benchmark.get('user_percentile')}th")
        print("=" * 60 + "\n")
        
        return Response({
            'overall_score': score_result['overall_score'],
            'tier': score_result['tier'],
            'percentile': benchmark.get('user_percentile', 50),
            'breakdown': score_result['breakdown'],
            'improvements': improvements,
            'benchmark': benchmark
        })


# Admin views
class ReviewQueueView(generics.ListAPIView):
    """List jobs flagged for human review (admin only)"""
    serializer_class = IngestionJobSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return IngestionJob.objects.filter(
            scores__flagged_for_human=True,
            scores__reviewer__isnull=True
        ).distinct()


class ReviewActionView(APIView):
    """Submit human review decision (admin only)"""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, job_id):
        try:
            job = IngestionJob.objects.get(id=job_id)
            score = job.scores.filter(flagged_for_human=True, reviewer__isnull=True).first()
            
            if not score:
                return Response({'error': 'No pending review'}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = HumanReviewSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            
            action = data['action']
            score.reviewer = request.user
            score.review_notes = data.get('notes', '')
            
            if action == 'approve':
                score.flagged_for_human = False
                job.status = 'done'
            elif action == 'reject':
                job.status = 'error'
                job.error_message = f'Rejected: {data.get("notes", "")}'
            
            score.save()
            job.save()
            
            return Response({
                'message': f'Review {action} completed',
                'job_status': job.status
            })
            
        except IngestionJob.DoesNotExist:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)


class SeedBenchmarksView(APIView):
    """Seed benchmark data (admin only)"""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        from .synthetic_data import seed_junior_frontend_benchmarks
        count = seed_junior_frontend_benchmarks()
        return Response({
            'message': f'Seeded {count} junior frontend developer profiles',
            'status': 'success'
        })


# ============================================
# AI INSIGHTS VIEWS
# ============================================

from .models import AIInsight
from .serializers import AIInsightSerializer
from django.utils import timezone
from datetime import timedelta


class AIInsightsListView(APIView):
    """List and generate AI insights for the user"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user's AI insights"""
        insight_type = request.query_params.get('type')
        unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
        
        queryset = AIInsight.objects.filter(user=request.user)
        
        if insight_type and insight_type != 'all':
            queryset = queryset.filter(insight_type=insight_type)
        if unread_only:
            queryset = queryset.filter(is_read=False)
        
        # Filter out expired insights
        queryset = queryset.filter(
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
        )
        
        insights = queryset[:20]
        serializer = AIInsightSerializer(insights, many=True)
        
        return Response({
            'insights': serializer.data,
            'total_count': queryset.count(),
            'unread_count': AIInsight.objects.filter(user=request.user, is_read=False).count()
        })

    def post(self, request):
        """Generate new AI insights using Gemini"""
        print(f"\n[INSIGHTS] Generating insights for user {request.user.id}")
        
        # Get user's latest completed analysis
        latest_job = IngestionJob.objects.filter(
            user=request.user, 
            status='done'
        ).order_by('-created_at').first()
        
        if not latest_job:
            return Response({
                'error': 'No completed analysis found. Please complete onboarding first.',
                'code': 'NO_ANALYSIS',
                'insights_count': 0
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            insights_count = generate_ai_insights(request.user, latest_job)
            return Response({
                'message': f'Generated {insights_count} new insights',
                'insights_count': insights_count
            })
        except Exception as e:
            print(f"[INSIGHTS] Error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIInsightDetailView(APIView):
    """Get, update, or delete a specific insight"""
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, insight_id, user):
        try:
            return AIInsight.objects.get(id=insight_id, user=user)
        except AIInsight.DoesNotExist:
            return None

    def get(self, request, insight_id):
        insight = self.get_object(insight_id, request.user)
        if not insight:
            return Response({'error': 'Insight not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(AIInsightSerializer(insight).data)

    def patch(self, request, insight_id):
        """Update insight (mark as read, bookmark, etc.)"""
        insight = self.get_object(insight_id, request.user)
        if not insight:
            return Response({'error': 'Insight not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AIInsightSerializer(insight, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, insight_id):
        insight = self.get_object(insight_id, request.user)
        if not insight:
            return Response({'error': 'Insight not found'}, status=status.HTTP_404_NOT_FOUND)
        insight.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def generate_ai_insights(user, job):
    """Generate AI insights using Gemini and store in database.
    
    Memory-optimized: Uses rule-based generation by default to avoid
    Render free tier memory limits. Set USE_GEMINI_INSIGHTS=true to enable.
    """
    from .llm_judge import get_gemini_client
    import json
    import gc
    import os
    
    print(f"[INSIGHTS] Generating for job {job.id}")
    
    # Get analysis data
    result = job.result or {}
    score_result = result.get('score_result', {})
    benchmark = result.get('benchmark', {})
    llm_evaluation = result.get('llm_evaluation', {})
    skills = result.get('skills_detected', [])
    
    # Clear old non-bookmarked insights
    AIInsight.objects.filter(user=user, is_bookmarked=False).delete()
    
    # Check if Gemini insights are enabled (disabled by default to save memory)
    use_gemini = os.getenv('USE_GEMINI_INSIGHTS', 'false').lower() == 'true'
    model = get_gemini_client() if use_gemini else None
    
    if model:
        print("   [GEMINI] Using Gemini for insights (memory intensive)")
    else:
        print("   [RULE] Using rule-based insights (memory efficient)")
    
    insights_created = 0
    
    # Reduced set of insights to prevent memory issues (4 instead of 9)
    insight_configs = [
        ('skill_gap', generate_skill_gap_prompt),
        ('career_advice', generate_career_advice_prompt),
        ('learning_path', generate_learning_path_prompt),
        ('project_suggestion', generate_project_suggestion_prompt),
    ]
    
    for insight_type, prompt_generator in insight_configs:
        try:
            if model:
                # Use Gemini (only if explicitly enabled)
                print(f"   [GEMINI] Generating {insight_type}...")
                prompt = prompt_generator(score_result, benchmark, llm_evaluation, skills)
                response = model.generate_content(prompt)
                text = response.text.strip()
                
                # Parse JSON response
                if text.startswith('```json'):
                    text = text[7:]
                if text.startswith('```'):
                    text = text[3:]
                if text.endswith('```'):
                    text = text[:-3]
                
                insight_data = json.loads(text.strip())
                
                # Force garbage collection after each Gemini call
                del response, text
                gc.collect()
            else:
                # Fallback to rule-based (default, memory efficient)
                print(f"   [RULE] Generating {insight_type}...")
                insight_data = generate_fallback_insight(insight_type, score_result, benchmark, llm_evaluation, skills)
            
            # Create insight
            AIInsight.objects.create(
                user=user,
                job=job,
                insight_type=insight_type,
                title=insight_data.get('title', f'{insight_type.replace("_", " ").title()} Insight'),
                content=insight_data.get('content', ''),
                metadata=insight_data.get('metadata', {}),
                relevance_score=insight_data.get('relevance_score', 0.8),
                expires_at=timezone.now() + timedelta(days=7) if insight_type == 'market_trend' else None
            )
            insights_created += 1
            print(f"   ✅ Created {insight_type} insight")
            
        except Exception as e:
            print(f"   ⚠️ Failed to generate {insight_type}: {e}")
    
    return insights_created


def generate_market_trend_prompt(score_result, benchmark, llm_evaluation, skills):
    return f"""
Generate a market trend insight for a junior frontend developer.
User Score: {score_result.get('overall_score', 0):.2f}
User Tier: {score_result.get('tier', 'Unknown')}
Skills: {', '.join(skills[:5])}
Percentile: {benchmark.get('user_percentile', 50)}

Return JSON:
{{
  "title": "Brief title about current frontend market trends",
  "content": "2-3 paragraphs about frontend market trends, demand for React/TypeScript, remote work opportunities, and how the user's skills align with market needs.",
  "metadata": {{
    "trend_direction": "up/stable/down",
    "hot_skills": ["skill1", "skill2"],
    "market_growth": "percentage or description"
  }},
  "relevance_score": 0.9
}}
Return ONLY valid JSON.
"""


def generate_skill_gap_prompt(score_result, benchmark, llm_evaluation, skills):
    breakdown = score_result.get('breakdown', {})
    areas = llm_evaluation.get('areas_for_improvement', [])
    return f"""
Generate a skill gap analysis for a junior frontend developer.
Current Skills: {', '.join(skills[:5])}
Skill Score: {breakdown.get('skill_strength', {}).get('raw_score', 0):.2f}
Areas for Improvement: {', '.join(areas[:3])}

Return JSON:
{{
  "title": "Your Skill Development Priorities",
  "content": "Analysis of skill gaps with specific recommendations. Include what skills to learn next and why they matter for career growth.",
  "metadata": {{
    "priority_skills": ["skill1", "skill2"],
    "current_level": "beginner/intermediate/advanced",
    "time_to_improve": "estimated weeks"
  }},
  "relevance_score": 0.95
}}
Return ONLY valid JSON.
"""


def generate_career_advice_prompt(score_result, benchmark, llm_evaluation, skills):
    return f"""
Generate career advice for a junior frontend developer.
Tier: {score_result.get('tier', 'Developing')}
Percentile: {benchmark.get('user_percentile', 50)}
Strengths: {', '.join(llm_evaluation.get('strengths', [])[:3])}

Return JSON:
{{
  "title": "Career Roadmap for {score_result.get('tier', 'Junior')} Developers",
  "content": "Personalized career advice including next steps, timeline expectations, and how to advance to the next level.",
  "metadata": {{
    "current_stage": "stage name",
    "next_milestone": "what to achieve next",
    "timeline": "estimated months"
  }},
  "relevance_score": 0.9
}}
Return ONLY valid JSON.
"""


def generate_learning_path_prompt(score_result, benchmark, llm_evaluation, skills):
    recommendations = llm_evaluation.get('recommendations', [])
    return f"""
Generate a learning path for a junior frontend developer.
Current Skills: {', '.join(skills[:5])}
Recommendations: {', '.join(recommendations[:3])}

Return JSON:
{{
  "title": "Your 8-Week Learning Plan",
  "content": "Structured learning path with weekly goals, resources, and milestones. Include specific courses, tutorials, and projects to build.",
  "metadata": {{
    "duration_weeks": 8,
    "milestones": ["week 2 goal", "week 4 goal", "week 8 goal"],
    "resources": ["resource1", "resource2"]
  }},
  "relevance_score": 0.85
}}
Return ONLY valid JSON.
"""


def generate_salary_insight_prompt(score_result, benchmark, llm_evaluation, skills):
    return f"""
Generate salary insights for a junior frontend developer.
Percentile: {benchmark.get('user_percentile', 50)}
Average Rate: ${benchmark.get('avg_rate', 35)}/hr
Tier: {score_result.get('tier', 'Developing')}

Return JSON:
{{
  "title": "Your Market Rate Analysis",
  "content": "Analysis of earning potential, rate recommendations, and factors that affect compensation. Include tips for negotiation.",
  "metadata": {{
    "recommended_rate": "$X-Y/hr",
    "market_average": "$Z/hr",
    "growth_potential": "percentage increase possible"
  }},
  "relevance_score": 0.8
}}
Return ONLY valid JSON.
"""


def generate_project_suggestion_prompt(score_result, benchmark, llm_evaluation, skills):
    tier = score_result.get('tier', 'Developing')
    return f"""
Generate project suggestions for a {tier} frontend developer.
Skills: {', '.join(skills[:5])}
Areas to Improve: {', '.join(llm_evaluation.get('areas_for_improvement', [])[:3])}

Return JSON:
{{
  "title": "Portfolio Projects for {tier} Developers",
  "content": "3 specific project ideas with descriptions, technologies to use, and how each project will strengthen the portfolio.",
  "metadata": {{
    "projects": [
      {{"name": "Project 1", "difficulty": "beginner/intermediate", "skills": ["skill1"]}},
      {{"name": "Project 2", "difficulty": "intermediate", "skills": ["skill2"]}}
    ],
    "estimated_time": "2-4 weeks each"
  }},
  "relevance_score": 0.9
}}
Return ONLY valid JSON.
"""


def generate_fallback_insight(insight_type, score_result, benchmark, llm_evaluation, skills=None):
    """Generate rule-based insights when Gemini is unavailable"""
    skills = skills or []
    tier = score_result.get('tier', 'Developing')
    percentile = benchmark.get('user_percentile', 50)
    
    fallbacks = {
        'market_trend': {
            'title': 'Frontend Development Market Outlook',
            'content': f"""The frontend development market continues to show strong demand. React remains the most sought-after framework, with TypeScript adoption growing rapidly.

As a {tier} developer at the {percentile}th percentile, you're well-positioned to capitalize on these trends. Companies are increasingly looking for developers who can build responsive, accessible web applications.

Focus on strengthening your React and TypeScript skills to align with market demands. Remote work opportunities remain abundant in this field.""",
            'metadata': {'trend_direction': 'up', 'hot_skills': ['React', 'TypeScript', 'Next.js']},
            'relevance_score': 0.85
        },
        'skill_gap': {
            'title': 'Your Skill Development Priorities',
            'content': f"""Based on your current profile, here are the key areas to focus on:

1. **TypeScript**: Essential for modern frontend development and most job postings require it.
2. **Testing**: Learn Jest and React Testing Library to write reliable code.
3. **State Management**: Deepen your understanding of Redux or Zustand.

Addressing these gaps will significantly improve your marketability and move you up from the {percentile}th percentile.""",
            'metadata': {'priority_skills': ['TypeScript', 'Testing', 'State Management'], 'current_level': tier.lower()},
            'relevance_score': 0.9
        },
        'career_advice': {
            'title': f'Career Roadmap for {tier} Developers',
            'content': f"""At the {tier} level ({percentile}th percentile), here's your path forward:

**Current Stage**: Building foundational skills and portfolio
**Next Milestone**: Land your first junior frontend role or freelance projects

**Action Plan**:
- Complete 2-3 polished portfolio projects
- Contribute to open source to gain visibility
- Network on LinkedIn and Twitter with other developers
- Apply to junior positions even if you don't meet all requirements

**Timeline**: With consistent effort, expect to advance to the next tier in 6-12 months.""",
            'metadata': {'current_stage': tier, 'next_milestone': 'Junior Role', 'timeline': '6-12 months'},
            'relevance_score': 0.88
        },
        'learning_path': {
            'title': 'Your 8-Week Learning Plan',
            'content': f"""**Week 1-2**: TypeScript Fundamentals
- Complete TypeScript course on freeCodeCamp
- Convert one existing project to TypeScript

**Week 3-4**: Testing
- Learn Jest basics
- Add tests to your main project

**Week 5-6**: Advanced React Patterns
- Study custom hooks and context
- Build a complex component library

**Week 7-8**: Portfolio Polish
- Deploy all projects with proper documentation
- Create detailed case studies

**Resources**: freeCodeCamp, Frontend Masters, Scrimba""",
            'metadata': {'duration_weeks': 8, 'milestones': ['TypeScript', 'Testing', 'Portfolio'], 'resources': ['freeCodeCamp', 'Frontend Masters']},
            'relevance_score': 0.85
        },
        'salary_insight': {
            'title': 'Your Market Rate Analysis',
            'content': f"""**Your Position**: {percentile}th percentile among junior frontend developers

**Recommended Rate Range**: ${max(20, benchmark.get('avg_rate', 35) - 15)}-${benchmark.get('avg_rate', 35) + 10}/hour

**Market Context**: The average junior frontend developer earns ${benchmark.get('avg_rate', 35)}/hour. Your rate should reflect your skill level and portfolio quality.

**Tips to Increase Your Rate**:
- Build a strong portfolio with live demos
- Get testimonials from clients or colleagues
- Specialize in a high-demand area (e.g., React + TypeScript)
- Improve your GitHub presence

**Growth Potential**: With skill improvements, you could reach ${benchmark.get('avg_rate', 35) + 25}/hour within 12 months.""",
            'metadata': {'recommended_rate': f"${max(20, benchmark.get('avg_rate', 35) - 15)}-{benchmark.get('avg_rate', 35) + 10}/hr", 'market_average': f"${benchmark.get('avg_rate', 35)}/hr"},
            'relevance_score': 0.8
        },
        'project_suggestion': {
            'title': f'Portfolio Projects for {tier} Developers',
            'content': f"""Here are 3 projects to strengthen your portfolio:

**1. Task Management Dashboard**
Build a Trello-like app with drag-and-drop, user authentication, and real-time updates.
*Skills*: React, TypeScript, Firebase/Supabase
*Time*: 2-3 weeks

**2. E-commerce Product Page**
Create a responsive product page with cart functionality, filters, and checkout flow.
*Skills*: React, State Management, API Integration
*Time*: 2 weeks

**3. Personal Blog with CMS**
Build a blog with markdown support, categories, and a simple admin panel.
*Skills*: Next.js, MDX, Tailwind CSS
*Time*: 2-3 weeks

Each project should have a live demo, clean code, and detailed README.""",
            'metadata': {'projects': [{'name': 'Task Dashboard', 'difficulty': 'intermediate'}, {'name': 'E-commerce Page', 'difficulty': 'intermediate'}, {'name': 'Blog CMS', 'difficulty': 'intermediate'}]},
            'relevance_score': 0.9
        },
        'swot_analysis': {
            'title': 'Your SWOT Analysis',
            'content': f'Comprehensive analysis of your position as a {tier} developer at the {percentile}th percentile.',
            'metadata': {
                'strengths': [
                    'Strong foundation in modern JavaScript frameworks',
                    'Active learning mindset and growth potential',
                    'Understanding of responsive web design principles'
                ],
                'weaknesses': [
                    'Limited TypeScript experience - essential for most roles',
                    'Testing skills need development (Jest, RTL)',
                    'Backend/API integration experience could be stronger'
                ],
                'opportunities': [
                    'High demand for React developers in remote positions',
                    'Growing market for TypeScript specialists',
                    'Freelance opportunities in web development'
                ],
                'threats': [
                    'Increasing competition from bootcamp graduates',
                    'AI tools changing development workflows',
                    'Rapid framework evolution requires continuous learning'
                ]
            },
            'relevance_score': 0.95
        },
        'salary_comparison': {
            'title': 'Global Salary Comparison',
            'content': 'How your earning potential compares across experience levels.',
            'metadata': {
                'salary_data': [
                    {'name': 'Junior', 'salary': 45, 'description': '0-1 years'},
                    {'name': 'Mid-Level', 'salary': 75, 'description': '2-4 years'},
                    {'name': 'You', 'salary': max(30, int(benchmark.get('avg_rate', 35) * (percentile/50))), 'active': True, 'description': 'Current'},
                    {'name': 'Senior', 'salary': 120, 'description': '5-8 years'},
                    {'name': 'Lead', 'salary': 150, 'description': '8+ years'}
                ],
                'your_rate': max(30, int(benchmark.get('avg_rate', 35) * (percentile/50))),
                'market_average': benchmark.get('avg_rate', 35),
                'percentile': percentile,
                'growth_potential': f"{int((120 - max(30, benchmark.get('avg_rate', 35) * (percentile/50))) / max(30, benchmark.get('avg_rate', 35) * (percentile/50)) * 100)}%"
            },
            'relevance_score': 0.9
        },
        'skill_demand': {
            'title': 'Skill Demand in Your Niche',
            'content': 'Market demand distribution for frontend development skills.',
            'metadata': {
                'skill_demand': [
                    {'name': 'React', 'value': 400, 'user_has': True},
                    {'name': 'TypeScript', 'value': 350, 'user_has': False},
                    {'name': 'Node.js', 'value': 300, 'user_has': False},
                    {'name': 'Vue/Angular', 'value': 200, 'user_has': False},
                    {'name': 'CSS/Tailwind', 'value': 250, 'user_has': True}
                ],
                'total_jobs': 1500,
                'user_coverage': '43%',
                'top_growing': ['Next.js', 'TypeScript', 'Tailwind CSS']
            },
            'relevance_score': 0.88
        }
    }
    
    return fallbacks.get(insight_type, {
        'title': 'AI Insight',
        'content': 'Insight generation in progress.',
        'metadata': {},
        'relevance_score': 0.7
    })


def generate_swot_analysis_prompt(score_result, benchmark, llm_evaluation, skills):
    """Generate SWOT analysis prompt for Gemini"""
    tier = score_result.get('tier', 'Developing')
    percentile = benchmark.get('user_percentile', 50)
    strengths = llm_evaluation.get('strengths', [])
    weaknesses = llm_evaluation.get('areas_for_improvement', [])
    
    return f"""
Generate a comprehensive SWOT analysis for a {tier} frontend developer.
Current Skills: {', '.join(skills[:5])}
Percentile: {percentile}th
Known Strengths: {', '.join(strengths[:3])}
Known Weaknesses: {', '.join(weaknesses[:3])}

Return JSON with exactly this structure:
{{
  "title": "Your SWOT Analysis",
  "content": "Brief overview of the SWOT analysis findings.",
  "metadata": {{
    "strengths": [
      "Specific strength 1 based on their skills",
      "Specific strength 2",
      "Specific strength 3"
    ],
    "weaknesses": [
      "Specific weakness 1 to improve",
      "Specific weakness 2",
      "Specific weakness 3"
    ],
    "opportunities": [
      "Market opportunity 1 they can leverage",
      "Career opportunity 2",
      "Growth opportunity 3"
    ],
    "threats": [
      "Market threat 1 to be aware of",
      "Competition threat 2",
      "Technology threat 3"
    ]
  }},
  "relevance_score": 0.95
}}
Return ONLY valid JSON.
"""


def generate_salary_comparison_prompt(score_result, benchmark, llm_evaluation, skills):
    """Generate salary comparison data for charts"""
    tier = score_result.get('tier', 'Developing')
    percentile = benchmark.get('user_percentile', 50)
    avg_rate = benchmark.get('avg_rate', 35)
    
    return f"""
Generate salary comparison data for a {tier} frontend developer at {percentile}th percentile.
Average market rate: ${avg_rate}/hr

Return JSON with chart data:
{{
  "title": "Global Salary Comparison",
  "content": "How your earning potential compares to the market at different experience levels.",
  "metadata": {{
    "salary_data": [
      {{"name": "Junior", "salary": 45, "description": "0-1 years experience"}},
      {{"name": "Mid-Level", "salary": 75, "description": "2-4 years experience"}},
      {{"name": "You", "salary": {int(avg_rate * (percentile/50))}, "active": true, "description": "Your current position"}},
      {{"name": "Senior", "salary": 120, "description": "5-8 years experience"}},
      {{"name": "Lead", "salary": 150, "description": "8+ years experience"}}
    ],
    "your_rate": {int(avg_rate * (percentile/50))},
    "market_average": {avg_rate},
    "percentile": {percentile},
    "growth_potential": "{int((150 - avg_rate * (percentile/50)) / (avg_rate * (percentile/50)) * 100)}%"
  }},
  "relevance_score": 0.9
}}
Return ONLY valid JSON.
"""


def generate_skill_demand_prompt(score_result, benchmark, llm_evaluation, skills):
    """Generate skill demand data for pie chart"""
    user_skills = [s.lower() for s in skills[:5]]
    
    return f"""
Generate skill demand market share data for frontend development.
User's skills: {', '.join(skills[:5])}

Return JSON with pie chart data showing market demand for different skill categories:
{{
  "title": "Skill Demand in Your Niche",
  "content": "Market demand distribution for frontend development skills. Skills you have are highlighted.",
  "metadata": {{
    "skill_demand": [
      {{"name": "React", "value": 400, "user_has": {"true" if "react" in user_skills else "false"}}},
      {{"name": "TypeScript", "value": 350, "user_has": {"true" if "typescript" in user_skills else "false"}}},
      {{"name": "Node.js", "value": 300, "user_has": {"true" if "node" in user_skills or "nodejs" in user_skills else "false"}}},
      {{"name": "Vue/Angular", "value": 200, "user_has": {"true" if "vue" in user_skills or "angular" in user_skills else "false"}}},
      {{"name": "CSS/Tailwind", "value": 250, "user_has": {"true" if "css" in user_skills or "tailwind" in user_skills else "false"}}}
    ],
    "total_jobs": 1500,
    "user_coverage": "percentage of market user can target",
    "top_growing": ["Next.js", "TypeScript", "Tailwind CSS"]
  }},
  "relevance_score": 0.88
}}
Return ONLY valid JSON.
"""
