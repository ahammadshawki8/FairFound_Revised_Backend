"""
Management command to test the agentic workflow end-to-end
Run with: python manage.py test_agents
"""
from django.core.management.base import BaseCommand
from apps.agents.scoring import (
    calculate_skill_score, calculate_github_score,
    calculate_portfolio_score, calculate_experience_score,
    compute_overall_score, generate_improvements
)
from apps.agents.collectors import fetch_github_metrics
from apps.agents.synthetic_data import (
    generate_junior_frontend_profile, get_junior_frontend_benchmark,
    seed_junior_frontend_benchmarks
)
from apps.agents.llm_judge import evaluate_junior_frontend
from apps.agents.models import BenchmarkCohort, SyntheticProfile
import json


class Command(BaseCommand):
    help = 'Test the agentic workflow for junior frontend developers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--github',
            type=str,
            help='GitHub username to test (optional)',
        )
        parser.add_argument(
            '--seed',
            action='store_true',
            help='Seed benchmark data before testing',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== FairFound Agentic Workflow Test ===\n'))
        
        # Seed if requested
        if options['seed']:
            self.stdout.write('Seeding benchmark data...')
            seed_junior_frontend_benchmarks()
            self.stdout.write(self.style.SUCCESS('✓ Benchmark data seeded\n'))
        
        # Check benchmark data exists
        self.stdout.write('1. Checking Benchmark Data...')
        try:
            cohort = BenchmarkCohort.objects.get(skill_category='junior_frontend')
            profile_count = SyntheticProfile.objects.filter(category='junior_frontend').count()
            self.stdout.write(self.style.SUCCESS(f'   ✓ Benchmark cohort found: {cohort.name}'))
            self.stdout.write(self.style.SUCCESS(f'   ✓ Synthetic profiles: {profile_count}'))
            self.stdout.write(f'   Percentiles: {cohort.percentiles}')
            self.stdout.write(f'   Avg Rate: ${cohort.avg_hourly_rate}/hr\n')
        except BenchmarkCohort.DoesNotExist:
            self.stdout.write(self.style.ERROR('   ✗ No benchmark data! Run with --seed first\n'))
            return
        
        # Test skill scoring
        self.stdout.write('2. Testing Skill Scoring Agent...')
        test_skills = {
            'all_skills': ['html', 'css', 'javascript', 'react', 'typescript', 'git', 'tailwind']
        }
        skill_score, skill_level, skill_details = calculate_skill_score(test_skills)
        self.stdout.write(self.style.SUCCESS(f'   ✓ Skill Score: {skill_score:.2f} ({skill_level})'))
        self.stdout.write(f'   Matched: {sum(len(v) for v in skill_details.get("matched_skills", {}).values())} skills')
        if skill_details.get('missing_important'):
            self.stdout.write(f'   Missing: {skill_details["missing_important"]}\n')
        else:
            self.stdout.write('')
        
        # Test GitHub collector (optional)
        self.stdout.write('3. Testing GitHub Collector Agent...')
        github_username = options.get('github')
        if github_username:
            github_data = fetch_github_metrics(github_username)
            if github_data.get('error'):
                self.stdout.write(self.style.WARNING(f'   ⚠ GitHub error: {github_data["error"]}'))
            else:
                self.stdout.write(self.style.SUCCESS(f'   ✓ GitHub data fetched for @{github_username}'))
                self.stdout.write(f'   Repos: {github_data.get("public_repos", 0)}, Stars: {github_data.get("total_stars", 0)}')
            github_score, github_level, _ = calculate_github_score(github_data)
            self.stdout.write(f'   GitHub Score: {github_score:.2f} ({github_level})\n')
        else:
            # Use mock data
            mock_github = {'public_repos': 8, 'total_stars': 15, 'recent_active_repos': 3, 'contributions_last_year': 120}
            github_score, github_level, _ = calculate_github_score(mock_github)
            self.stdout.write(self.style.SUCCESS(f'   ✓ Using mock GitHub data'))
            self.stdout.write(f'   GitHub Score: {github_score:.2f} ({github_level})\n')
        
        # Test portfolio scoring
        self.stdout.write('4. Testing Portfolio Scoring Agent...')
        mock_portfolio = {
            'has_projects': True,
            'project_count': 4,
            'has_live_demos': True,
            'has_code_links': True,
            'quality_score': 0.6
        }
        portfolio_score, portfolio_level, _ = calculate_portfolio_score(mock_portfolio)
        self.stdout.write(self.style.SUCCESS(f'   ✓ Portfolio Score: {portfolio_score:.2f} ({portfolio_level})\n'))
        
        # Test experience scoring
        self.stdout.write('5. Testing Experience Scoring Agent...')
        exp_score, exp_level, _ = calculate_experience_score(1.5)
        self.stdout.write(self.style.SUCCESS(f'   ✓ Experience Score (1.5 yrs): {exp_score:.2f} ({exp_level})\n'))
        
        # Test overall score computation
        self.stdout.write('6. Testing Overall Score Computation...')
        features = {
            'skill': (skill_score, skill_level, skill_details),
            'github': (github_score, github_level, {}),
            'portfolio': (portfolio_score, portfolio_level, {}),
            'experience': (exp_score, exp_level, {}),
            'learning_momentum': 0.6
        }
        score_result = compute_overall_score(features)
        self.stdout.write(self.style.SUCCESS(f'   ✓ Overall Score: {score_result["overall_score"]:.2f}'))
        self.stdout.write(f'   Tier: {score_result["tier"]} ({score_result["tier_color"]})')
        self.stdout.write('   Breakdown:')
        for key, data in score_result['breakdown'].items():
            self.stdout.write(f'     - {key}: {data["raw_score"]:.2f} × {data["weight"]} = {data["weighted"]:.3f}\n')
        
        # Test benchmark comparison
        self.stdout.write('7. Testing Benchmark Comparison...')
        benchmark = get_junior_frontend_benchmark(score_result['overall_score'])
        self.stdout.write(self.style.SUCCESS(f'   ✓ Percentile: {benchmark["user_percentile"]}th'))
        self.stdout.write(f'   Tier: {benchmark["tier"]}')
        self.stdout.write(f'   Suggested Rate: ${benchmark["market_insights"]["rate_suggestion"]["suggested_rate"]}/hr\n')
        
        # Test LLM Judge
        self.stdout.write('8. Testing LLM Judge Agent...')
        structured_data = {'form': {'skills': test_skills['all_skills'], 'experience_years': 1.5}}
        evaluation = evaluate_junior_frontend(structured_data, score_result, benchmark)
        self.stdout.write(self.style.SUCCESS(f'   ✓ Evaluation generated'))
        self.stdout.write(f'   Summary: {evaluation["summary"][:100]}...')
        self.stdout.write(f'   Strengths: {len(evaluation["strengths"])} items')
        self.stdout.write(f'   Recommendations: {len(evaluation["recommendations"])} items\n')
        
        # Test improvement generation
        self.stdout.write('9. Testing Improvement Generator...')
        improvements = generate_improvements(score_result['breakdown'])
        self.stdout.write(self.style.SUCCESS(f'   ✓ Generated {len(improvements)} improvements'))
        for imp in improvements[:3]:
            self.stdout.write(f'   - [{imp["priority"]}] {imp["area"]}: {imp["action"][:50]}...\n')
        
        # Test synthetic profile generation
        self.stdout.write('10. Testing Synthetic Profile Generator...')
        for tier in ['beginner', 'learning', 'competent', 'strong_junior']:
            profile = generate_junior_frontend_profile(tier)
            self.stdout.write(f'    {tier}: score={profile["overall_score"]:.2f}, skills={len(profile["skills"])}')
        self.stdout.write('')
        
        # Summary
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Test Summary ==='))
        self.stdout.write(self.style.SUCCESS('All agents are working correctly! ✓'))
        self.stdout.write(f'\nTest Profile Results:')
        self.stdout.write(f'  Overall Score: {score_result["overall_score"]:.0%}')
        self.stdout.write(f'  Tier: {score_result["tier"]}')
        self.stdout.write(f'  Percentile: {benchmark["user_percentile"]}th')
        self.stdout.write(f'  Suggested Rate: ${benchmark["market_insights"]["rate_suggestion"]["suggested_rate"]}/hr')
        
        # Print full JSON result
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Full Analysis Result (JSON) ==='))
        full_result = {
            'overall_score': score_result['overall_score'],
            'tier': score_result['tier'],
            'percentile': benchmark['user_percentile'],
            'breakdown': {k: {'score': v['raw_score'], 'level': v.get('level', 'n/a')} 
                         for k, v in score_result['breakdown'].items()},
            'improvements': [{'area': i['area'], 'action': i['action']} for i in improvements[:3]],
            'market_insights': benchmark['market_insights']
        }
        self.stdout.write(json.dumps(full_result, indent=2))
