"""
Scoring system optimized for Junior Frontend Developers
Rubric-based evaluation with transparent calculations
"""
from typing import Dict, List, Tuple

# Weights optimized for junior frontend developers
WEIGHTS = {
    'skill_strength': 0.35,      # Most important for juniors
    'github_activity': 0.25,     # Shows initiative and learning
    'portfolio_quality': 0.20,   # Demonstrates practical ability
    'experience_depth': 0.15,    # Less weight since they're junior
    'learning_momentum': 0.05    # Growth trajectory
}

# Skills valued for junior frontend developers
FRONTEND_SKILL_TIERS = {
    'essential': {
        'skills': ['html', 'css', 'javascript'],
        'weight': 1.0,
        'description': 'Core web fundamentals'
    },
    'framework': {
        'skills': ['react', 'vue', 'angular', 'svelte'],
        'weight': 1.2,
        'description': 'Modern framework knowledge'
    },
    'modern_css': {
        'skills': ['tailwind', 'sass', 'styled-components', 'bootstrap'],
        'weight': 0.8,
        'description': 'CSS tooling'
    },
    'typescript': {
        'skills': ['typescript'],
        'weight': 1.3,
        'description': 'Type safety - highly valued'
    },
    'tooling': {
        'skills': ['git', 'npm', 'webpack', 'vite'],
        'weight': 0.7,
        'description': 'Development tools'
    },
    'testing': {
        'skills': ['jest', 'cypress', 'react-testing-library', 'vitest'],
        'weight': 1.1,
        'description': 'Testing skills - differentiator'
    },
    'bonus': {
        'skills': ['next.js', 'graphql', 'rest-api', 'accessibility', 'responsive-design', 'figma'],
        'weight': 0.9,
        'description': 'Additional valuable skills'
    }
}

# Rubrics for junior frontend developers
RUBRICS = {
    'skill_strength': {
        'strong': {'min': 0.70, 'label': 'Strong Foundation', 'color': 'green'},
        'solid': {'min': 0.50, 'label': 'Solid Skills', 'color': 'blue'},
        'developing': {'min': 0.30, 'label': 'Developing', 'color': 'yellow'},
        'beginner': {'min': 0.0, 'label': 'Beginner', 'color': 'gray'}
    },
    'github_activity': {
        'active': {'min': 0.60, 'label': 'Active Contributor', 'color': 'green'},
        'regular': {'min': 0.40, 'label': 'Regular Activity', 'color': 'blue'},
        'occasional': {'min': 0.20, 'label': 'Occasional', 'color': 'yellow'},
        'minimal': {'min': 0.0, 'label': 'Minimal', 'color': 'gray'}
    },
    'portfolio_quality': {
        'impressive': {'min': 0.70, 'label': 'Impressive Portfolio', 'color': 'green'},
        'good': {'min': 0.45, 'label': 'Good Projects', 'color': 'blue'},
        'basic': {'min': 0.25, 'label': 'Basic Portfolio', 'color': 'yellow'},
        'minimal': {'min': 0.0, 'label': 'Needs Work', 'color': 'gray'}
    },
    'experience_depth': {
        'experienced': {'min': 0.60, 'label': '1.5-2+ Years', 'color': 'green'},
        'some': {'min': 0.35, 'label': '6-18 Months', 'color': 'blue'},
        'early': {'min': 0.15, 'label': '3-6 Months', 'color': 'yellow'},
        'new': {'min': 0.0, 'label': 'Just Starting', 'color': 'gray'}
    }
}


def calculate_skill_score(skills_data: Dict) -> Tuple[float, str, Dict]:
    """
    Calculate skill score for junior frontend developer.
    Returns (score, level, details)
    """
    print("\n      [RUBRIC] Skill Scoring Rubric Applied:")
    print("      - Essential (HTML, CSS, JS): weight 1.0")
    print("      - Framework (React, Vue, Angular): weight 1.2")
    print("      - TypeScript: weight 1.3 (highly valued)")
    print("      - Testing (Jest, Cypress): weight 1.1")
    
    if not skills_data:
        print("      ⚠️ No skills data provided")
        return 0.15, 'beginner', {'message': 'No skills detected'}
    
    user_skills = []
    if isinstance(skills_data, dict):
        # Handle both formats
        if 'all_skills' in skills_data:
            user_skills = [s.lower() for s in skills_data.get('all_skills', [])]
        else:
            for cat_skills in skills_data.values():
                if isinstance(cat_skills, list):
                    user_skills.extend([s.lower() for s in cat_skills])
    elif isinstance(skills_data, list):
        user_skills = [s.lower() for s in skills_data]
    
    if not user_skills:
        print("      ⚠️ No skills extracted")
        return 0.15, 'beginner', {'message': 'No skills detected'}
    
    print(f"      User skills: {user_skills}")
    
    # Calculate weighted skill score
    total_weight = 0
    earned_weight = 0
    matched_skills = {}
    missing_important = []
    
    for tier_name, tier_config in FRONTEND_SKILL_TIERS.items():
        tier_skills = tier_config['skills']
        tier_weight = tier_config['weight']
        
        matched = [s for s in tier_skills if s in user_skills]
        matched_skills[tier_name] = matched
        
        if tier_skills:
            tier_score = len(matched) / len(tier_skills)
            total_weight += tier_weight
            earned_weight += tier_score * tier_weight
            
            # Track missing essential/framework skills
            if tier_name in ['essential', 'framework', 'typescript'] and len(matched) < len(tier_skills):
                missing = [s for s in tier_skills if s not in user_skills]
                missing_important.extend(missing[:2])
    
    # Normalize score
    score = earned_weight / total_weight if total_weight > 0 else 0.15
    score = max(0.1, min(0.95, score))
    
    print(f"      Calculation: {earned_weight:.3f} / {total_weight:.3f} = {score:.3f}")
    
    # Determine level
    level = 'beginner'
    for lvl, config in RUBRICS['skill_strength'].items():
        if score >= config['min']:
            level = lvl
            break
    
    print(f"      [RUBRIC] Level determination:")
    print(f"      - Strong (≥0.70): {'✓' if score >= 0.70 else '✗'}")
    print(f"      - Solid (≥0.50): {'✓' if score >= 0.50 else '✗'}")
    print(f"      - Developing (≥0.30): {'✓' if score >= 0.30 else '✗'}")
    print(f"      - Beginner (<0.30): {'✓' if score < 0.30 else '✗'}")
    print(f"      → Assigned level: {level}")
    
    details = {
        'matched_skills': matched_skills,
        'total_skills': len(user_skills),
        'missing_important': missing_important[:5],
        'recommendation': get_skill_recommendation(score, missing_important)
    }
    
    return round(score, 3), level, details


def calculate_github_score(github_data: Dict) -> Tuple[float, str, Dict]:
    """Calculate GitHub activity score for junior developer"""
    if not github_data or github_data.get('error'):
        return 0.1, 'minimal', {'message': 'No GitHub data available'}
    
    repos = github_data.get('public_repos', 0)
    stars = github_data.get('total_stars', 0)
    recent_repos = github_data.get('recent_active_repos', 0)
    contributions = github_data.get('contributions_last_year', 0)
    
    # Junior-appropriate thresholds
    repo_score = min(1.0, repos / 10)  # 10 repos = max
    star_score = min(1.0, stars / 20)   # 20 stars = max for junior
    recent_score = min(1.0, recent_repos / 5)  # 5 recent active = max
    contrib_score = min(1.0, contributions / 200)  # 200 contributions = max
    
    # Weighted combination
    score = (repo_score * 0.25) + (star_score * 0.20) + (recent_score * 0.30) + (contrib_score * 0.25)
    score = max(0.05, min(0.95, score))
    
    # Determine level
    level = 'minimal'
    for lvl, config in RUBRICS['github_activity'].items():
        if score >= config['min']:
            level = lvl
            break
    
    details = {
        'repos': repos,
        'stars': stars,
        'recent_active': recent_repos,
        'contributions': contributions,
        'recommendation': get_github_recommendation(score, repos, recent_repos)
    }
    
    return round(score, 3), level, details


def calculate_portfolio_score(portfolio_data: Dict) -> Tuple[float, str, Dict]:
    """Calculate portfolio quality score"""
    if not portfolio_data or portfolio_data.get('error'):
        return 0.1, 'minimal', {'message': 'No portfolio data'}
    
    # Extract metrics
    has_projects = portfolio_data.get('has_projects', False)
    project_count = portfolio_data.get('project_count', 0)
    has_descriptions = portfolio_data.get('has_descriptions', False)
    has_live_demos = portfolio_data.get('has_live_demos', False)
    has_code_links = portfolio_data.get('has_code_links', False)
    quality_score = portfolio_data.get('quality_score', 0.3)
    
    # Calculate score
    score = quality_score
    
    # Bonuses
    if has_projects and project_count >= 3:
        score += 0.1
    if has_descriptions:
        score += 0.1
    if has_live_demos:
        score += 0.15
    if has_code_links:
        score += 0.1
    
    score = max(0.1, min(0.95, score))
    
    # Determine level
    level = 'minimal'
    for lvl, config in RUBRICS['portfolio_quality'].items():
        if score >= config['min']:
            level = lvl
            break
    
    details = {
        'project_count': project_count,
        'has_live_demos': has_live_demos,
        'has_code_links': has_code_links,
        'recommendation': get_portfolio_recommendation(score, has_live_demos, project_count)
    }
    
    return round(score, 3), level, details


def calculate_experience_score(experience_years: float) -> Tuple[float, str, Dict]:
    """Calculate experience score for junior developer (0-2 years focus)"""
    if not experience_years or experience_years < 0:
        experience_years = 0
    
    # Junior scale: 0-2 years
    if experience_years >= 2:
        score = 0.85
    elif experience_years >= 1.5:
        score = 0.70
    elif experience_years >= 1:
        score = 0.55
    elif experience_years >= 0.5:
        score = 0.35
    elif experience_years > 0:
        score = 0.20
    else:
        score = 0.10
    
    # Determine level
    level = 'new'
    for lvl, config in RUBRICS['experience_depth'].items():
        if score >= config['min']:
            level = lvl
            break
    
    details = {
        'years': experience_years,
        'recommendation': get_experience_recommendation(experience_years)
    }
    
    return round(score, 3), level, details


def compute_overall_score(features: Dict) -> Dict:
    """
    Compute overall score with transparent digit-by-digit calculation.
    """
    # Extract scores and levels
    skill_score, skill_level, skill_details = features.get('skill', (0.3, 'beginner', {}))
    github_score, github_level, github_details = features.get('github', (0.2, 'minimal', {}))
    portfolio_score, portfolio_level, portfolio_details = features.get('portfolio', (0.2, 'minimal', {}))
    exp_score, exp_level, exp_details = features.get('experience', (0.2, 'new', {}))
    momentum_score = features.get('learning_momentum', 0.5)
    
    # Weighted calculation (transparent)
    components = {
        'skill_strength': {
            'raw_score': skill_score,
            'weight': WEIGHTS['skill_strength'],
            'weighted': round(skill_score * WEIGHTS['skill_strength'], 4),
            'level': skill_level,
            'details': skill_details
        },
        'github_activity': {
            'raw_score': github_score,
            'weight': WEIGHTS['github_activity'],
            'weighted': round(github_score * WEIGHTS['github_activity'], 4),
            'level': github_level,
            'details': github_details
        },
        'portfolio_quality': {
            'raw_score': portfolio_score,
            'weight': WEIGHTS['portfolio_quality'],
            'weighted': round(portfolio_score * WEIGHTS['portfolio_quality'], 4),
            'level': portfolio_level,
            'details': portfolio_details
        },
        'experience_depth': {
            'raw_score': exp_score,
            'weight': WEIGHTS['experience_depth'],
            'weighted': round(exp_score * WEIGHTS['experience_depth'], 4),
            'level': exp_level,
            'details': exp_details
        },
        'learning_momentum': {
            'raw_score': momentum_score,
            'weight': WEIGHTS['learning_momentum'],
            'weighted': round(momentum_score * WEIGHTS['learning_momentum'], 4),
            'level': 'n/a',
            'details': {}
        }
    }
    
    # Sum weighted scores
    overall = sum(c['weighted'] for c in components.values())
    overall = round(max(0.1, min(0.95, overall)), 3)
    
    # Determine overall tier
    if overall >= 0.70:
        tier = 'Strong Junior'
        tier_color = 'green'
    elif overall >= 0.50:
        tier = 'Competent'
        tier_color = 'blue'
    elif overall >= 0.35:
        tier = 'Developing'
        tier_color = 'yellow'
    else:
        tier = 'Early Stage'
        tier_color = 'gray'
    
    return {
        'overall_score': overall,
        'tier': tier,
        'tier_color': tier_color,
        'breakdown': components,
        'weights_used': WEIGHTS,
        'calculation_method': 'weighted_sum'
    }


def generate_improvements(breakdown: Dict) -> List[Dict]:
    """Generate prioritized improvement suggestions"""
    improvements = []
    
    # Check each component
    skill_data = breakdown.get('skill_strength', {})
    if skill_data.get('raw_score', 1) < 0.5:
        improvements.append({
            'priority': 1,
            'area': 'Skills',
            'action': 'Learn TypeScript and a testing framework (Jest)',
            'impact': 'high',
            'time_estimate': '2-4 weeks'
        })
    
    github_data = breakdown.get('github_activity', {})
    if github_data.get('raw_score', 1) < 0.4:
        improvements.append({
            'priority': 2,
            'area': 'GitHub',
            'action': 'Commit code daily and build 2-3 public projects',
            'impact': 'high',
            'time_estimate': '1-2 months'
        })
    
    portfolio_data = breakdown.get('portfolio_quality', {})
    if portfolio_data.get('raw_score', 1) < 0.45:
        improvements.append({
            'priority': 3,
            'area': 'Portfolio',
            'action': 'Create 3 polished projects with live demos and documentation',
            'impact': 'medium',
            'time_estimate': '3-6 weeks'
        })
    
    exp_data = breakdown.get('experience_depth', {})
    if exp_data.get('raw_score', 1) < 0.4:
        improvements.append({
            'priority': 4,
            'area': 'Experience',
            'action': 'Take on freelance projects or contribute to open source',
            'impact': 'medium',
            'time_estimate': 'ongoing'
        })
    
    if not improvements:
        improvements.append({
            'priority': 1,
            'area': 'Growth',
            'action': 'You are doing great! Consider learning Next.js or advanced React patterns',
            'impact': 'medium',
            'time_estimate': '2-4 weeks'
        })
    
    return sorted(improvements, key=lambda x: x['priority'])[:5]


# Helper functions for recommendations
def get_skill_recommendation(score: float, missing: List[str]) -> str:
    if score >= 0.7:
        return "Strong skill set! Consider adding testing or TypeScript to stand out."
    elif score >= 0.5:
        return f"Good foundation. Focus on learning: {', '.join(missing[:3]) if missing else 'TypeScript, testing'}"
    else:
        return "Build your core skills: HTML, CSS, JavaScript, then learn React."


def get_github_recommendation(score: float, repos: int, recent: int) -> str:
    if score >= 0.6:
        return "Great GitHub presence! Keep contributing consistently."
    elif repos < 5:
        return "Create more public repositories showcasing your projects."
    elif recent < 3:
        return "Increase your recent activity - aim for weekly commits."
    else:
        return "Good start! Focus on quality projects with good READMEs."


def get_portfolio_recommendation(score: float, has_demos: bool, count: int) -> str:
    if score >= 0.7:
        return "Impressive portfolio! Consider adding case studies."
    elif not has_demos:
        return "Add live demos to your projects - this is crucial for juniors."
    elif count < 3:
        return "Build 2-3 more polished projects to showcase your skills."
    else:
        return "Improve project descriptions and add screenshots/videos."


def get_experience_recommendation(years: float) -> str:
    if years >= 1.5:
        return "Good experience level. Document your achievements with metrics."
    elif years >= 0.5:
        return "Keep building experience through projects and freelance work."
    else:
        return "Focus on learning and building projects to gain experience."
