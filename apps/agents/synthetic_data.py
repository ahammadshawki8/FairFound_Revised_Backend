"""
Synthetic data generation focused on Junior Frontend Developers
Based on Stack Overflow Developer Survey 2024 and Freelance Platform datasets
"""
import random
from typing import Dict, List
from decimal import Decimal
from .models import SyntheticProfile, BenchmarkCohort


# Junior Frontend Developer skill tiers (based on SO Survey 2024 trends)
JUNIOR_FRONTEND_SKILLS = {
    'core': ['html', 'css', 'javascript'],
    'frameworks': ['react', 'vue', 'angular', 'svelte'],
    'styling': ['tailwind', 'bootstrap', 'sass', 'styled-components'],
    'tools': ['git', 'npm', 'webpack', 'vite'],
    'testing': ['jest', 'cypress', 'react-testing-library'],
    'typescript': ['typescript'],
    'state': ['redux', 'zustand', 'react-query'],
    'other': ['figma', 'responsive-design', 'accessibility', 'rest-api']
}

# Realistic skill combinations for junior devs (0-2 years)
SKILL_PROFILES = {
    'beginner': {
        'skills': ['html', 'css', 'javascript', 'git'],
        'exp_range': (0, 1),
        'rate_range': (15, 25),
        'repos_range': (1, 5),
        'stars_range': (0, 5),
        'score_base': 0.25
    },
    'learning': {
        'skills': ['html', 'css', 'javascript', 'react', 'git', 'npm'],
        'exp_range': (0.5, 1.5),
        'rate_range': (20, 35),
        'repos_range': (3, 10),
        'stars_range': (0, 15),
        'score_base': 0.40
    },
    'competent': {
        'skills': ['html', 'css', 'javascript', 'react', 'tailwind', 'git', 'npm', 'responsive-design'],
        'exp_range': (1, 2),
        'rate_range': (30, 50),
        'repos_range': (5, 15),
        'stars_range': (5, 30),
        'score_base': 0.55
    },
    'strong_junior': {
        'skills': ['html', 'css', 'javascript', 'typescript', 'react', 'tailwind', 'git', 'jest', 'rest-api'],
        'exp_range': (1.5, 2.5),
        'rate_range': (40, 65),
        'repos_range': (8, 20),
        'stars_range': (10, 50),
        'score_base': 0.70
    }
}

# Names for synthetic profiles
FIRST_NAMES = ['Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Quinn', 'Avery', 
               'Skyler', 'Dakota', 'Jamie', 'Reese', 'Finley', 'Sage', 'Rowan']
LAST_NAMES = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 
              'Davis', 'Rodriguez', 'Martinez', 'Chen', 'Kim', 'Patel', 'Singh', 'Lee']

# Market data based on freelance platform datasets
MARKET_DATA = {
    'avg_hourly_rate': 35.0,
    'median_hourly_rate': 30.0,
    'rate_percentiles': {10: 18, 25: 25, 50: 35, 75: 50, 90: 65},
    'avg_experience': 1.2,
    'top_skills_demand': ['react', 'javascript', 'typescript', 'tailwind', 'next.js'],
    'job_success_rate_avg': 0.85,
    'projects_completed_avg': 8
}


def generate_junior_frontend_profile(tier: str = None) -> Dict:
    """Generate a realistic junior frontend developer profile"""
    if tier is None:
        # Distribution: 20% beginner, 35% learning, 30% competent, 15% strong
        tier = random.choices(
            ['beginner', 'learning', 'competent', 'strong_junior'],
            weights=[20, 35, 30, 15]
        )[0]
    
    profile_config = SKILL_PROFILES[tier]
    
    # Generate base skills with some variation
    skills = profile_config['skills'].copy()
    
    # Randomly add 0-2 extra skills based on tier
    extra_count = random.randint(0, 2) if tier != 'beginner' else 0
    all_possible = []
    for cat_skills in JUNIOR_FRONTEND_SKILLS.values():
        all_possible.extend(cat_skills)
    extra_skills = [s for s in all_possible if s not in skills]
    if extra_skills and extra_count > 0:
        skills.extend(random.sample(extra_skills, min(extra_count, len(extra_skills))))
    
    exp_years = round(random.uniform(*profile_config['exp_range']), 1)
    hourly_rate = random.randint(*profile_config['rate_range'])
    github_repos = random.randint(*profile_config['repos_range'])
    github_stars = random.randint(*profile_config['stars_range'])
    
    # Portfolio score based on tier with variance
    portfolio_base = {'beginner': 0.2, 'learning': 0.4, 'competent': 0.6, 'strong_junior': 0.75}
    portfolio_score = min(1.0, max(0.1, portfolio_base[tier] + random.uniform(-0.1, 0.15)))
    
    # Calculate overall score with variance
    base_score = profile_config['score_base']
    variance = random.uniform(-0.08, 0.12)
    overall_score = max(0.15, min(0.85, base_score + variance))
    
    return {
        'name': f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
        'title': random.choice([
            'Junior Frontend Developer',
            'Frontend Developer',
            'React Developer',
            'Web Developer',
            'UI Developer'
        ]),
        'skills': skills,
        'experience_years': exp_years,
        'hourly_rate': hourly_rate,
        'github_repos': github_repos,
        'github_stars': github_stars,
        'portfolio_score': round(portfolio_score, 2),
        'overall_score': round(overall_score, 2),
        'tier': tier,
        'category': 'junior_frontend'
    }


def create_junior_frontend_cohort(count: int = 200) -> List[SyntheticProfile]:
    """Create a cohort of junior frontend developer profiles"""
    profiles = []
    
    for _ in range(count):
        data = generate_junior_frontend_profile()
        profile = SyntheticProfile(
            name=data['name'],
            title=data['title'],
            skills=data['skills'],
            experience_years=int(data['experience_years']),
            hourly_rate=Decimal(str(data['hourly_rate'])),
            github_repos=data['github_repos'],
            github_stars=data['github_stars'],
            portfolio_score=data['portfolio_score'],
            overall_score=data['overall_score'],
            category='junior_frontend',
            source='synthetic_kaggle_inspired'
        )
        profiles.append(profile)
    
    return profiles


def calculate_percentiles(values: List[float]) -> Dict:
    """Calculate percentiles from a list of values"""
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    
    percentiles = {}
    for p in [10, 25, 50, 75, 90, 95]:
        idx = int(n * p / 100)
        percentiles[p] = round(sorted_vals[min(idx, n - 1)], 3)
    
    return percentiles


def seed_junior_frontend_benchmarks():
    """Seed database with junior frontend developer benchmark data"""
    print("\n" + "=" * 60)
    print("  SYNTHETIC DATA GENERATION")
    print("=" * 60)
    print("\n[SYNTHETIC] Clearing existing benchmark data...")
    
    # Clear existing synthetic data for this category
    SyntheticProfile.objects.filter(category='junior_frontend').delete()
    BenchmarkCohort.objects.filter(skill_category='junior_frontend').delete()
    
    print("[SYNTHETIC] Generating 200 junior frontend developer profiles...")
    print("[SYNTHETIC] Distribution: 20% beginner, 35% learning, 30% competent, 15% strong")
    
    # Generate cohort
    profiles = create_junior_frontend_cohort(200)
    SyntheticProfile.objects.bulk_create(profiles)
    print(f"[SYNTHETIC] ✅ Created {len(profiles)} synthetic profiles")
    
    # Calculate statistics
    scores = [p.overall_score for p in profiles]
    rates = [float(p.hourly_rate) for p in profiles]
    exp_years = [p.experience_years for p in profiles]
    
    # Aggregate skills
    skill_counts = {}
    for p in profiles:
        for skill in p.skills:
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
    
    top_skills = sorted(skill_counts.items(), key=lambda x: -x[1])[:15]
    common_skills = [s[0] for s in top_skills]
    
    # Create benchmark cohort
    percentile_data = calculate_percentiles(scores)
    avg_rate = round(sum(rates) / len(rates), 2)
    avg_exp = round(sum(exp_years) / len(exp_years), 1)
    
    print("\n[SYNTHETIC] Benchmark Statistics:")
    print(f"   Percentiles: {percentile_data}")
    print(f"   Average hourly rate: ${avg_rate}")
    print(f"   Average experience: {avg_exp} years")
    print(f"   Top skills: {common_skills[:5]}")
    
    BenchmarkCohort.objects.create(
        name='junior_frontend_2024',
        skill_category='junior_frontend',
        percentiles=percentile_data,
        avg_hourly_rate=Decimal(str(avg_rate)),
        avg_experience_years=avg_exp,
        common_skills=common_skills,
        sample_size=len(profiles),
        is_synthetic=True
    )
    
    print(f"\n[SYNTHETIC] ✅ Benchmark cohort created successfully")
    print("=" * 60 + "\n")
    
    return len(profiles)


def get_junior_frontend_benchmark(user_score: float) -> Dict:
    """Get benchmark comparison for a junior frontend developer"""
    print(f"\n      [BENCHMARK] Comparing user score {user_score:.3f} against synthetic dataset...")
    try:
        cohort = BenchmarkCohort.objects.get(skill_category='junior_frontend')
        print(f"      [BENCHMARK] Found cohort: {cohort.name} (n={cohort.sample_size})")
        
        percentiles = cohort.percentiles
        user_percentile = 0
        
        # Find user's percentile (convert keys to int for comparison)
        for p in sorted([int(k) for k in percentiles.keys()]):
            p_str = str(p)
            if user_score >= float(percentiles[p_str]):
                user_percentile = p
        
        # Determine tier
        if user_percentile >= 90:
            tier = 'Top Performer'
            tier_description = 'You are among the top junior frontend developers'
        elif user_percentile >= 75:
            tier = 'Strong'
            tier_description = 'Above average skills and experience'
        elif user_percentile >= 50:
            tier = 'Competitive'
            tier_description = 'Solid foundation with room to grow'
        elif user_percentile >= 25:
            tier = 'Developing'
            tier_description = 'Building skills, focus on key areas'
        else:
            tier = 'Early Stage'
            tier_description = 'Just starting out, lots of opportunity ahead'
        
        # Convert percentiles to int keys for consistency
        clean_percentiles = {int(k): float(v) for k, v in percentiles.items()}
        
        print(f"      [BENCHMARK] User percentile: {user_percentile}th")
        print(f"      [BENCHMARK] Tier assigned: {tier}")
        
        return {
            'user_percentile': user_percentile,
            'tier': tier,
            'tier_description': tier_description,
            'benchmark_percentiles': clean_percentiles,
            'avg_rate': float(cohort.avg_hourly_rate),
            'avg_experience': cohort.avg_experience_years,
            'in_demand_skills': cohort.common_skills[:10],
            'sample_size': cohort.sample_size,
            'market_insights': {
                'rate_suggestion': get_rate_suggestion(user_score, float(cohort.avg_hourly_rate)),
                'skill_gaps': get_skill_gaps(cohort.common_skills[:10])
            }
        }
    except BenchmarkCohort.DoesNotExist:
        # Return default data if no benchmark exists
        return get_default_benchmark(user_score)


def get_rate_suggestion(score: float, avg_rate: float) -> Dict:
    """Suggest hourly rate based on score"""
    if score >= 0.7:
        multiplier = 1.3
        range_desc = 'premium'
    elif score >= 0.55:
        multiplier = 1.1
        range_desc = 'above average'
    elif score >= 0.4:
        multiplier = 1.0
        range_desc = 'market rate'
    else:
        multiplier = 0.8
        range_desc = 'entry level'
    
    suggested = round(avg_rate * multiplier, 0)
    return {
        'suggested_rate': suggested,
        'range': range_desc,
        'min': round(suggested * 0.85),
        'max': round(suggested * 1.15)
    }


def get_skill_gaps(in_demand_skills: List[str]) -> List[str]:
    """Return skills that are in high demand for junior frontend devs"""
    high_value = ['typescript', 'react', 'next.js', 'tailwind', 'jest']
    return [s for s in high_value if s in in_demand_skills][:5]


def get_default_benchmark(user_score: float) -> Dict:
    """Return default benchmark when no data exists"""
    return {
        'user_percentile': int(user_score * 100),
        'tier': 'Unranked',
        'tier_description': 'Benchmark data being generated',
        'benchmark_percentiles': {10: 0.25, 25: 0.35, 50: 0.50, 75: 0.65, 90: 0.78},
        'avg_rate': 35.0,
        'avg_experience': 1.2,
        'in_demand_skills': ['react', 'javascript', 'typescript', 'tailwind', 'git'],
        'sample_size': 0,
        'market_insights': {
            'rate_suggestion': {'suggested_rate': 35, 'range': 'market rate', 'min': 30, 'max': 40},
            'skill_gaps': ['typescript', 'react', 'tailwind']
        }
    }
