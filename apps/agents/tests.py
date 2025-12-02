"""
Tests for Junior Frontend Developer Analysis System
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal

from .models import IngestionJob, Evidence, ScoreSnapshot, BenchmarkCohort, SyntheticProfile
from .scoring import (
    calculate_skill_score, calculate_github_score, 
    calculate_experience_score, compute_overall_score,
    generate_improvements
)
from .synthetic_data import (
    generate_junior_frontend_profile, seed_junior_frontend_benchmarks,
    get_junior_frontend_benchmark
)
from .tasks import run_junior_frontend_pipeline

User = get_user_model()


class SkillScoringTests(TestCase):
    """Test skill scoring for junior frontend developers"""
    
    def test_strong_skills(self):
        """Test scoring for strong skill set"""
        skills = {
            'all_skills': ['html', 'css', 'javascript', 'react', 'typescript', 'tailwind', 'git', 'jest']
        }
        score, level, details = calculate_skill_score(skills)
        
        # Score should be moderate-to-good for this skill set
        self.assertGreaterEqual(score, 0.4)
        self.assertIn(level, ['strong', 'solid', 'developing'])
        self.assertIn('matched_skills', details)
    
    def test_beginner_skills(self):
        """Test scoring for beginner skill set"""
        skills = {'all_skills': ['html', 'css']}
        score, level, details = calculate_skill_score(skills)
        
        self.assertLess(score, 0.4)
        self.assertEqual(level, 'beginner')
    
    def test_empty_skills(self):
        """Test scoring with no skills"""
        score, level, details = calculate_skill_score({})
        
        self.assertEqual(score, 0.15)
        self.assertEqual(level, 'beginner')
    
    def test_typescript_bonus(self):
        """Test that TypeScript gives a scoring bonus"""
        without_ts = {'all_skills': ['html', 'css', 'javascript', 'react']}
        with_ts = {'all_skills': ['html', 'css', 'javascript', 'react', 'typescript']}
        
        score_without, _, _ = calculate_skill_score(without_ts)
        score_with, _, _ = calculate_skill_score(with_ts)
        
        self.assertGreater(score_with, score_without)


class GitHubScoringTests(TestCase):
    """Test GitHub activity scoring"""
    
    def test_active_github(self):
        """Test scoring for active GitHub user"""
        github_data = {
            'public_repos': 15,
            'total_stars': 25,
            'recent_active_repos': 5,
            'contributions_last_year': 150
        }
        score, level, details = calculate_github_score(github_data)
        
        self.assertGreaterEqual(score, 0.5)
        self.assertIn(level, ['active', 'regular'])
    
    def test_minimal_github(self):
        """Test scoring for minimal GitHub activity"""
        github_data = {
            'public_repos': 2,
            'total_stars': 0,
            'recent_active_repos': 0,
            'contributions_last_year': 10
        }
        score, level, details = calculate_github_score(github_data)
        
        self.assertLess(score, 0.3)
    
    def test_no_github(self):
        """Test scoring with no GitHub data"""
        score, level, details = calculate_github_score({})
        
        self.assertEqual(score, 0.1)
        self.assertEqual(level, 'minimal')


class ExperienceScoringTests(TestCase):
    """Test experience scoring for juniors"""
    
    def test_two_years(self):
        """Test scoring for 2 years experience"""
        score, level, details = calculate_experience_score(2)
        
        self.assertGreaterEqual(score, 0.8)
        self.assertEqual(level, 'experienced')
    
    def test_one_year(self):
        """Test scoring for 1 year experience"""
        score, level, details = calculate_experience_score(1)
        
        self.assertGreaterEqual(score, 0.5)
        self.assertIn(level, ['some', 'experienced'])
    
    def test_no_experience(self):
        """Test scoring for no experience"""
        score, level, details = calculate_experience_score(0)
        
        self.assertEqual(score, 0.1)
        self.assertEqual(level, 'new')


class OverallScoreTests(TestCase):
    """Test overall score computation"""
    
    def test_compute_overall(self):
        """Test overall score calculation"""
        features = {
            'skill': (0.7, 'solid', {}),
            'github': (0.5, 'regular', {}),
            'portfolio': (0.4, 'basic', {}),
            'experience': (0.6, 'some', {}),
            'learning_momentum': 0.5
        }
        
        result = compute_overall_score(features)
        
        self.assertIn('overall_score', result)
        self.assertIn('tier', result)
        self.assertIn('breakdown', result)
        self.assertGreater(result['overall_score'], 0)
        self.assertLess(result['overall_score'], 1)
    
    def test_tier_assignment(self):
        """Test tier assignment based on score"""
        # Strong junior
        features_strong = {
            'skill': (0.8, 'strong', {}),
            'github': (0.7, 'active', {}),
            'portfolio': (0.7, 'good', {}),
            'experience': (0.7, 'experienced', {}),
            'learning_momentum': 0.7
        }
        result = compute_overall_score(features_strong)
        self.assertEqual(result['tier'], 'Strong Junior')
        
        # Early stage
        features_early = {
            'skill': (0.2, 'beginner', {}),
            'github': (0.1, 'minimal', {}),
            'portfolio': (0.1, 'minimal', {}),
            'experience': (0.1, 'new', {}),
            'learning_momentum': 0.3
        }
        result = compute_overall_score(features_early)
        self.assertEqual(result['tier'], 'Early Stage')


class SyntheticDataTests(TestCase):
    """Test synthetic data generation"""
    
    def test_profile_generation(self):
        """Test generating a synthetic profile"""
        profile = generate_junior_frontend_profile()
        
        self.assertIn('name', profile)
        self.assertIn('skills', profile)
        self.assertIn('experience_years', profile)
        self.assertIn('overall_score', profile)
        self.assertEqual(profile['category'], 'junior_frontend')
        self.assertLessEqual(profile['experience_years'], 2.5)
    
    def test_benchmark_seeding(self):
        """Test seeding benchmark data"""
        count = seed_junior_frontend_benchmarks()
        
        self.assertEqual(count, 200)
        self.assertTrue(
            BenchmarkCohort.objects.filter(skill_category='junior_frontend').exists()
        )
        self.assertEqual(
            SyntheticProfile.objects.filter(category='junior_frontend').count(),
            200
        )
    
    def test_benchmark_comparison(self):
        """Test benchmark comparison"""
        seed_junior_frontend_benchmarks()
        
        benchmark = get_junior_frontend_benchmark(0.6)
        
        self.assertIn('user_percentile', benchmark)
        self.assertIn('tier', benchmark)
        self.assertIn('in_demand_skills', benchmark)
        self.assertIn('market_insights', benchmark)


class ImprovementTests(TestCase):
    """Test improvement generation"""
    
    def test_improvements_for_weak_skills(self):
        """Test improvements generated for weak skills"""
        breakdown = {
            'skill_strength': {'raw_score': 0.3},
            'github_activity': {'raw_score': 0.2},
            'portfolio_quality': {'raw_score': 0.3},
            'experience_depth': {'raw_score': 0.3}
        }
        
        improvements = generate_improvements(breakdown)
        
        self.assertGreater(len(improvements), 0)
        self.assertLessEqual(len(improvements), 5)
        self.assertIn('priority', improvements[0])
        self.assertIn('action', improvements[0])


class APITests(APITestCase):
    """Test API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        seed_junior_frontend_benchmarks()
    
    def test_onboarding_submit(self):
        """Test onboarding submission"""
        from unittest.mock import patch
        
        data = {
            'name': 'Test User',
            'email': 'test@example.com',
            'skills': ['html', 'css', 'javascript', 'react'],
            'experience_years': 1,
            'github_username': 'testuser'
        }
        
        # Mock Celery task to avoid Redis dependency
        with patch('apps.agents.views.run_junior_frontend_pipeline.delay') as mock_task:
            mock_task.return_value = None
            response = self.client.post('/api/agents/onboard/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('job_id', response.data)
    
    def test_job_list(self):
        """Test job listing"""
        IngestionJob.objects.create(
            user=self.user,
            input_data={'test': 'data'},
            status='done'
        )
        
        response = self.client.get('/api/agents/jobs/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_benchmark_endpoint(self):
        """Test benchmark data endpoint"""
        response = self.client.get('/api/agents/benchmarks/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('in_demand_skills', response.data)
    
    def test_quick_analyze(self):
        """Test quick analysis endpoint"""
        data = {
            'skills': ['html', 'css', 'javascript', 'react'],
            'experience_years': 1
        }
        
        response = self.client.post('/api/agents/quick-analyze/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('overall_score', response.data)
        self.assertIn('tier', response.data)
        self.assertIn('percentile', response.data)


class ModelTests(TestCase):
    """Test model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_ingestion_job_creation(self):
        """Test creating an ingestion job"""
        job = IngestionJob.objects.create(
            user=self.user,
            input_data={'skills': ['react']}
        )
        
        self.assertEqual(job.status, 'pending')
        self.assertIsNotNone(job.created_at)
    
    def test_evidence_creation(self):
        """Test creating evidence"""
        job = IngestionJob.objects.create(
            user=self.user,
            input_data={}
        )
        
        evidence = Evidence.objects.create(
            job=job,
            source='form',
            extracted_data={'skills': ['react']},
            confidence=1.0
        )
        
        self.assertEqual(evidence.source, 'form')
        self.assertEqual(evidence.confidence, 1.0)
    
    def test_score_snapshot_creation(self):
        """Test creating a score snapshot"""
        job = IngestionJob.objects.create(
            user=self.user,
            input_data={}
        )
        
        score = ScoreSnapshot.objects.create(
            job=job,
            overall_score=0.65,
            breakdown={'skill_strength': {'raw_score': 0.7}},
            confidence=0.85
        )
        
        self.assertEqual(score.overall_score, 0.65)
        self.assertFalse(score.flagged_for_human)
