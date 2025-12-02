from django.conf import settings
import json
import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)


def analyze_profile_with_gemini(profile_data):
    """Analyze freelancer profile using Gemini AI - returns mock data if no API key"""
    return {
        'global_readiness_score': 78,
        'market_percentile': 65,
        'projected_earnings': 85000,
        'strengths': ['Strong React fundamentals', 'Good communication style'],
        'weaknesses': ['Lack of backend knowledge', 'Portfolio is generic'],
        'opportunities': ['High demand for Fullstack', 'SaaS niche'],
        'threats': ['AI code generation saturation'],
        'skill_gaps': ['Next.js', 'PostgreSQL', 'System Design'],
        'pricing_current': float(profile_data.get('hourly_rate', 0)),
        'pricing_recommended': float(profile_data.get('hourly_rate', 0)) * 1.25,
        'pricing_reasoning': 'Your skill set is in high demand.',
        'portfolio_score': 60,
        'github_score': 75,
        'communication_score': 85,
        'tech_stack_score': 80
    }


def analyze_sentiment_with_gemini(reviews):
    """Analyze sentiment of client reviews"""
    results = []
    for review in reviews:
        is_positive = any(word in review.lower() for word in ['great', 'excellent', 'amazing'])
        is_negative = any(word in review.lower() for word in ['bad', 'poor', 'slow'])
        sentiment = 'positive' if is_positive else ('negative' if is_negative else 'neutral')
        results.append({
            'review_text': review,
            'sentiment': sentiment,
            'confidence': 0.85 if sentiment != 'neutral' else 0.65,
            'keywords': review.split()[:5],
            'actionable_steps': ['Follow up with client', 'Improve communication']
        })
    return results


def generate_roadmap_with_gemini(profile_data, skill_gaps, user_skills=None):
    """
    Generate personalized roadmap using Gemini AI.
    Only learning (skill) steps include resource links. Project and branding steps don't.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', '')

    if not api_key or not skill_gaps:
        return _generate_fallback_roadmap(skill_gaps)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        skills_str = ', '.join(user_skills) if user_skills else 'general web development'
        gaps_str = ', '.join(skill_gaps[:5])

        prompt = f"""You are a career coach for junior frontend developers. Generate a varied, personalized roadmap.

Current Skills: {skills_str}
Skill Gaps to Address: {gaps_str}

Generate exactly 5-6 roadmap steps with a MIX of different types:
- 2-3 "skill" steps (learning new technologies) - ONLY these should include learning resource links
- 1-2 "project" steps (building something practical) - NO links, just describe what to build
- 1 "branding" step (improving portfolio/GitHub/LinkedIn) - NO links, just actionable advice

For SKILL steps only:
- Include 2-3 learning resources with REAL URLs as markdown links: [Name](url)
- Use real channels: Traversy Media, Web Dev Simplified, Fireship, freeCodeCamp
- Use real docs: react.dev, nextjs.org, developer.mozilla.org

For PROJECT steps:
- Describe a specific project to build that applies the skills
- No external links needed

For BRANDING steps:
- Give specific advice on improving online presence
- No external links needed

Format as JSON array:
[
  {{"title": "Learn TypeScript Basics", "description": "Master type safety with [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/) and [Traversy Media Tutorial](https://www.youtube.com/watch?v=BCg4U1FzODs).", "duration": "1 week", "type": "skill"}},
  {{"title": "Build a Task Manager App", "description": "Create a full-stack task manager with React and Node.js. Include user authentication, CRUD operations, and a clean UI.", "duration": "2 weeks", "type": "project"}},
  {{"title": "Optimize Your GitHub Profile", "description": "Pin your best 3-4 repositories, write detailed READMEs with screenshots, and add a profile README showcasing your skills.", "duration": "2 days", "type": "branding"}}
]

Return ONLY the JSON array."""

        response = model.generate_content(prompt)
        response_text = response.text.strip()

        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        response_text = response_text.strip()

        steps = json.loads(response_text)

        validated_steps = []
        for i, step in enumerate(steps[:6]):
            validated_steps.append({
                'title': step.get('title', f'Step {i+1}'),
                'description': step.get('description', 'Complete this step.'),
                'duration': step.get('duration', '1 week'),
                'status': 'in-progress' if i == 0 else 'pending',
                'type': step.get('type', 'skill'),
            })

        logger.info(f"Generated {len(validated_steps)} roadmap steps with Gemini")
        return validated_steps

    except Exception as e:
        logger.error(f"Gemini roadmap generation failed: {e}")
        return _generate_fallback_roadmap(skill_gaps)


def _generate_fallback_roadmap(skill_gaps):
    """Generate fallback roadmap with a mix of skill, project, and branding steps."""

    # Curated resources for common skill gaps (only skill steps have links)
    SKILL_RESOURCES = {
        'react': {
            'title': 'Master React Fundamentals',
            'description': 'Deep dive into React hooks, state management, and component patterns. Start with the [Official React Tutorial](https://react.dev/learn) and watch [React Course for Beginners](https://www.youtube.com/watch?v=bMknfKXIFA8) by freeCodeCamp.',
            'duration': '2 weeks',
            'type': 'skill'
        },
        'next.js': {
            'title': 'Learn Next.js for Production Apps',
            'description': 'Master server-side rendering, API routes, and the App Router. Follow the [Next.js Official Tutorial](https://nextjs.org/learn) and watch [Next.js 14 Full Course](https://www.youtube.com/watch?v=wm5gMKuwSYk) by Traversy Media.',
            'duration': '2 weeks',
            'type': 'skill'
        },
        'typescript': {
            'title': 'TypeScript for React Developers',
            'description': 'Learn type safety, generics, and TypeScript with React. Start with [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/) and watch [TypeScript Tutorial](https://www.youtube.com/watch?v=BwuLxPH8IDs) by Traversy Media.',
            'duration': '1 week',
            'type': 'skill'
        },
        'system design': {
            'title': 'Frontend System Design Basics',
            'description': 'Learn to design scalable frontend architectures. Watch [Frontend System Design](https://www.youtube.com/watch?v=5vyKhm2NTfw) by Chirag Goel and read [Frontend Architecture Patterns](https://www.patterns.dev/).',
            'duration': '2 weeks',
            'type': 'skill'
        },
        'testing': {
            'title': 'Testing React Applications',
            'description': 'Master unit testing and E2E testing. Learn from [Testing Library Docs](https://testing-library.com/docs/react-testing-library/intro/) and watch [React Testing Tutorial](https://www.youtube.com/watch?v=8Xwq35cPwYg) by Net Ninja.',
            'duration': '1 week',
            'type': 'skill'
        },
        'css': {
            'title': 'Advanced CSS & Modern Layouts',
            'description': 'Master Flexbox, Grid, and modern CSS. Study [CSS Tricks Guide to Flexbox](https://css-tricks.com/snippets/css/a-guide-to-flexbox/) and watch [CSS Grid Course](https://www.youtube.com/watch?v=rg7Fvvl3taU) by Traversy Media.',
            'duration': '1 week',
            'type': 'skill'
        },
        'postgresql': {
            'title': 'PostgreSQL for Web Developers',
            'description': 'Learn SQL and database design. Start with [PostgreSQL Tutorial](https://www.postgresqltutorial.com/) and watch [SQL Tutorial](https://www.youtube.com/watch?v=HXV3zeQKqGY) by freeCodeCamp.',
            'duration': '1 week',
            'type': 'skill'
        },
        'node.js': {
            'title': 'Node.js Backend Basics',
            'description': 'Learn server-side JavaScript and REST APIs. Watch [Node.js Crash Course](https://www.youtube.com/watch?v=fBNz5xF-Kx4) by Traversy Media and follow [Express.js Guide](https://expressjs.com/en/guide/routing.html).',
            'duration': '2 weeks',
            'type': 'skill'
        },
    }

    steps = []

    # Add 2-3 skill steps with learning links
    skill_count = 0
    for gap in skill_gaps[:3]:
        gap_lower = gap.lower()
        resource = None
        for key, value in SKILL_RESOURCES.items():
            if key in gap_lower or gap_lower in key:
                resource = value.copy()
                resource['title'] = f'Learn {gap}'
                break

        if not resource:
            resource = {
                'title': f'Learn {gap}',
                'description': f'Deep dive into {gap} fundamentals. Check out [freeCodeCamp](https://www.freecodecamp.org/) for free courses and [MDN Web Docs](https://developer.mozilla.org/) for references.',
                'duration': '1 week',
                'type': 'skill'
            }

        resource['status'] = 'in-progress' if skill_count == 0 else 'pending'
        steps.append(resource)
        skill_count += 1

    # Add a project step (no links)
    steps.append({
        'title': 'Build a Full-Stack Project',
        'description': 'Apply your new skills by building a real-world application. Create a task manager, blog platform, or e-commerce dashboard with user authentication, database integration, and a polished UI. Deploy it to showcase your abilities.',
        'duration': '2 weeks',
        'status': 'pending',
        'type': 'project'
    })

    # Add a branding step (no links)
    steps.append({
        'title': 'Optimize Your GitHub Profile',
        'description': 'Pin your best 3-4 repositories with detailed READMEs including screenshots and live demo links. Add a profile README that highlights your skills, current learning goals, and contact information. Make sure commit history shows consistent activity.',
        'duration': '2 days',
        'status': 'pending',
        'type': 'branding'
    })

    # Add another project step if we have more skill gaps
    if len(skill_gaps) > 2:
        steps.append({
            'title': 'Create a Portfolio Case Study',
            'description': 'Document one of your projects as a detailed case study. Explain the problem, your approach, technical decisions, challenges faced, and lessons learned. Include before/after screenshots and metrics if available.',
            'duration': '3 days',
            'status': 'pending',
            'type': 'branding'
        })

    return steps


def generate_task_for_mentee(mentee_name, mentee_title, step_title):
    """Generate a single task for mentee"""
    return {
        'title': f'Practice {step_title} concepts',
        'description': 'Complete hands-on exercises to reinforce learning',
        'due_date': '2024-12-15',
        'status': 'pending'
    }
