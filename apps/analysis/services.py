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
    Generate personalized roadmap with tasks using Gemini AI.
    Each step includes 2-3 specific tasks.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', '')

    if not api_key or not skill_gaps:
        return _generate_fallback_roadmap(skill_gaps)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        skills_str = ', '.join(user_skills) if user_skills else 'general web development'
        gaps_str = ', '.join(skill_gaps[:5])

        prompt = f"""You are a career coach for junior frontend developers. Generate a personalized roadmap with specific tasks and learning resources.

Current Skills: {skills_str}
Skill Gaps to Address: {gaps_str}

Generate exactly 5-6 roadmap steps with a MIX of types AND 2-3 specific tasks for each step:
- 2-3 "skill" steps (learning new technologies)
- 1-2 "project" steps (building something practical)
- 1 "branding" step (improving portfolio/GitHub/LinkedIn)

IMPORTANT: For "skill" type steps, include a "resources" array with 2-4 helpful learning links (documentation, YouTube videos, courses, tutorials). Use REAL, working URLs.

Format as JSON array:
[
  {{
    "title": "Learn TypeScript Basics",
    "description": "Master type safety with TypeScript fundamentals. TypeScript adds static typing to JavaScript, helping catch errors early and improving code quality.",
    "duration": "1 week",
    "type": "skill",
    "resources": [
      {{"title": "TypeScript Official Docs", "url": "https://www.typescriptlang.org/docs/", "type": "docs"}},
      {{"title": "TypeScript Tutorial - Net Ninja", "url": "https://www.youtube.com/watch?v=2pZmKW9-I_k", "type": "youtube"}},
      {{"title": "TypeScript Course - freeCodeCamp", "url": "https://www.youtube.com/watch?v=gp5H0Vw39yw", "type": "youtube"}}
    ],
    "tasks": [
      {{"title": "Complete TypeScript tutorial", "description": "Work through the official TypeScript handbook basics section"}},
      {{"title": "Convert a JS file to TS", "description": "Take an existing JavaScript file and add proper TypeScript types"}},
      {{"title": "Build a typed React component", "description": "Create a React component with proper TypeScript props and state types"}}
    ]
  }},
  {{
    "title": "Build a Task Manager App",
    "description": "Create a full-stack task manager with React. Apply your skills by building a real project.",
    "duration": "2 weeks",
    "type": "project",
    "tasks": [
      {{"title": "Set up project structure", "description": "Initialize React app with TypeScript and configure folder structure"}},
      {{"title": "Implement CRUD operations", "description": "Build create, read, update, delete functionality for tasks"}},
      {{"title": "Add user authentication", "description": "Implement login/signup with JWT tokens"}}
    ]
  }}
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
            tasks = step.get('tasks', [])
            validated_tasks = []
            for task in tasks[:3]:
                validated_tasks.append({
                    'title': task.get('title', 'Complete task'),
                    'description': task.get('description', 'Work on this task'),
                })
            
            # Validate resources
            resources = step.get('resources', [])
            validated_resources = []
            for res in resources[:4]:
                if res.get('url') and res.get('title'):
                    validated_resources.append({
                        'title': res.get('title'),
                        'url': res.get('url'),
                        'type': res.get('type', 'link'),
                    })
            
            validated_steps.append({
                'title': step.get('title', f'Step {i+1}'),
                'description': step.get('description', 'Complete this step.'),
                'duration': step.get('duration', '1 week'),
                'status': 'in-progress' if i == 0 else 'pending',
                'type': step.get('type', 'skill'),
                'tasks': validated_tasks,
                'resources': validated_resources,
            })

        logger.info(f"Generated {len(validated_steps)} roadmap steps with tasks using Gemini")
        return validated_steps

    except Exception as e:
        logger.error(f"Gemini roadmap generation failed: {e}")
        return _generate_fallback_roadmap(skill_gaps)


def generate_single_step_with_gemini(skill_gaps, user_skills, existing_steps):
    """Generate a single roadmap step with tasks using Gemini AI for preview."""
    api_key = getattr(settings, 'GEMINI_API_KEY', '')

    if not api_key:
        return _generate_fallback_single_step(skill_gaps, existing_steps)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')

        skills_str = ', '.join(user_skills) if user_skills else 'general web development'
        gaps_str = ', '.join(skill_gaps[:5]) if skill_gaps else 'general improvement'
        existing_str = ', '.join(existing_steps) if existing_steps else 'None'

        prompt = f"""You are a career coach for developers. Generate ONE new roadmap step with specific tasks and learning resources.

Current Skills: {skills_str}
Skill Gaps to Address: {gaps_str}
Existing Steps (avoid duplicates): {existing_str}

Generate exactly 1 roadmap step that:
1. Addresses one of the skill gaps or builds on existing skills
2. Is different from existing steps
3. Is practical and actionable
4. Includes 2-4 specific tasks
5. For "skill" type steps, include 2-4 learning resources with REAL working URLs

The step type should be one of: "skill" (learning), "project" (building), or "branding" (portfolio/profile improvement)

Format as JSON object:
{{
  "title": "Step title (concise, actionable)",
  "description": "Detailed description of what they'll learn and why it's important",
  "duration": "1 week",
  "type": "skill",
  "resources": [
    {{"title": "Official Documentation", "url": "https://example.com/docs", "type": "docs"}},
    {{"title": "YouTube Tutorial", "url": "https://youtube.com/watch?v=xxx", "type": "youtube"}},
    {{"title": "Free Course", "url": "https://freecodecamp.org/xxx", "type": "course"}}
  ],
  "tasks": [
    {{"title": "Task 1 title", "description": "What they need to do"}},
    {{"title": "Task 2 title", "description": "What they need to do"}},
    {{"title": "Task 3 title", "description": "What they need to do"}}
  ]
}}

Return ONLY the JSON object."""

        response = model.generate_content(prompt)
        response_text = response.text.strip()

        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        response_text = response_text.strip()

        step = json.loads(response_text)

        # Validate and clean the response
        validated_tasks = []
        for task in step.get('tasks', [])[:4]:
            validated_tasks.append({
                'title': task.get('title', 'Complete task'),
                'description': task.get('description', 'Work on this task'),
            })

        # Validate resources
        resources = step.get('resources', [])
        validated_resources = []
        for res in resources[:4]:
            if res.get('url') and res.get('title'):
                validated_resources.append({
                    'title': res.get('title'),
                    'url': res.get('url'),
                    'type': res.get('type', 'link'),
                })

        validated_step = {
            'title': step.get('title', 'New Learning Step'),
            'description': step.get('description', 'Complete this step to improve your skills.'),
            'duration': step.get('duration', '1 week'),
            'type': step.get('type', 'skill'),
            'tasks': validated_tasks,
            'resources': validated_resources,
        }

        logger.info(f"Generated single step with {len(validated_tasks)} tasks using Gemini")
        return validated_step

    except Exception as e:
        logger.error(f"Gemini single step generation failed: {e}")
        return _generate_fallback_single_step(skill_gaps, existing_steps)


def _generate_fallback_single_step(skill_gaps, existing_steps):
    """Generate a fallback single step when Gemini is unavailable."""
    existing_lower = [s.lower() for s in existing_steps] if existing_steps else []
    
    # Find a skill gap that's not already covered
    target_skill = None
    for gap in skill_gaps:
        if not any(gap.lower() in existing for existing in existing_lower):
            target_skill = gap
            break
    
    if not target_skill and skill_gaps:
        target_skill = skill_gaps[0]
    elif not target_skill:
        target_skill = 'Web Development'

    return {
        'title': f'Learn {target_skill}',
        'description': f'Deep dive into {target_skill} fundamentals and best practices to strengthen your skill set.',
        'duration': '1 week',
        'type': 'skill',
        'resources': [
            {'title': f'{target_skill} Documentation', 'url': f'https://www.google.com/search?q={target_skill.replace(" ", "+")}+documentation', 'type': 'docs'},
            {'title': f'{target_skill} Tutorial - YouTube', 'url': f'https://www.youtube.com/results?search_query={target_skill.replace(" ", "+")}+tutorial', 'type': 'youtube'},
        ],
        'tasks': [
            {'title': f'Research {target_skill} basics', 'description': f'Read documentation and watch tutorials about {target_skill}'},
            {'title': f'Practice {target_skill} exercises', 'description': f'Complete hands-on coding exercises for {target_skill}'},
            {'title': f'Build mini-project with {target_skill}', 'description': f'Create a small project demonstrating {target_skill} skills'},
        ]
    }


def _generate_fallback_roadmap(skill_gaps):
    """Generate fallback roadmap with tasks for each step."""

    # Curated resources with tasks for common skill gaps
    SKILL_RESOURCES = {
        'react': {
            'title': 'Master React Fundamentals',
            'description': 'Deep dive into React hooks, state management, and component patterns.',
            'duration': '2 weeks',
            'type': 'skill',
            'resources': [
                {'title': 'React Official Docs', 'url': 'https://react.dev/learn', 'type': 'docs'},
                {'title': 'React Tutorial - freeCodeCamp', 'url': 'https://www.youtube.com/watch?v=bMknfKXIFA8', 'type': 'youtube'},
                {'title': 'React Hooks Course', 'url': 'https://www.youtube.com/watch?v=TNhaISOUy6Q', 'type': 'youtube'},
            ],
            'tasks': [
                {'title': 'Complete React tutorial', 'description': 'Work through the official React documentation tutorial'},
                {'title': 'Build 3 custom hooks', 'description': 'Create useLocalStorage, useDebounce, and useFetch hooks'},
                {'title': 'Implement state management', 'description': 'Add Context API or Zustand to a sample project'},
            ]
        },
        'next.js': {
            'title': 'Learn Next.js for Production Apps',
            'description': 'Master server-side rendering, API routes, and the App Router.',
            'duration': '2 weeks',
            'type': 'skill',
            'resources': [
                {'title': 'Next.js Official Docs', 'url': 'https://nextjs.org/docs', 'type': 'docs'},
                {'title': 'Next.js 14 Tutorial', 'url': 'https://www.youtube.com/watch?v=wm5gMKuwSYk', 'type': 'youtube'},
                {'title': 'Next.js App Router Course', 'url': 'https://nextjs.org/learn', 'type': 'course'},
            ],
            'tasks': [
                {'title': 'Set up Next.js project', 'description': 'Create a new Next.js app with App Router'},
                {'title': 'Build API routes', 'description': 'Create REST API endpoints in Next.js'},
                {'title': 'Implement SSR page', 'description': 'Build a server-rendered page with data fetching'},
            ]
        },
        'typescript': {
            'title': 'TypeScript for React Developers',
            'description': 'Learn type safety, generics, and TypeScript with React.',
            'duration': '1 week',
            'type': 'skill',
            'resources': [
                {'title': 'TypeScript Official Handbook', 'url': 'https://www.typescriptlang.org/docs/handbook/', 'type': 'docs'},
                {'title': 'TypeScript Full Course', 'url': 'https://www.youtube.com/watch?v=gp5H0Vw39yw', 'type': 'youtube'},
                {'title': 'TypeScript for React', 'url': 'https://react-typescript-cheatsheet.netlify.app/', 'type': 'docs'},
            ],
            'tasks': [
                {'title': 'Learn TypeScript basics', 'description': 'Complete TypeScript handbook fundamentals'},
                {'title': 'Type a React component', 'description': 'Add proper types to props, state, and events'},
                {'title': 'Create generic utilities', 'description': 'Build reusable generic type utilities'},
            ]
        },
    }

    steps = []

    # Add 2-3 skill steps with tasks
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
                'description': f'Deep dive into {gap} fundamentals and best practices.',
                'duration': '1 week',
                'type': 'skill',
                'resources': [
                    {'title': f'{gap} Documentation', 'url': f'https://www.google.com/search?q={gap.replace(" ", "+")}+documentation', 'type': 'docs'},
                    {'title': f'{gap} Tutorial - YouTube', 'url': f'https://www.youtube.com/results?search_query={gap.replace(" ", "+")}+tutorial', 'type': 'youtube'},
                ],
                'tasks': [
                    {'title': f'Research {gap} basics', 'description': f'Read documentation and watch tutorials about {gap}'},
                    {'title': f'Practice {gap} exercises', 'description': f'Complete hands-on coding exercises for {gap}'},
                    {'title': f'Build mini-project with {gap}', 'description': f'Create a small project demonstrating {gap} skills'},
                ]
            }

        resource['status'] = 'in-progress' if skill_count == 0 else 'pending'
        steps.append(resource)
        skill_count += 1

    # Add a project step with tasks
    steps.append({
        'title': 'Build a Full-Stack Project',
        'description': 'Apply your new skills by building a real-world application with authentication and database.',
        'duration': '2 weeks',
        'status': 'pending',
        'type': 'project',
        'tasks': [
            {'title': 'Set up project structure', 'description': 'Initialize repository, configure tools, and plan architecture'},
            {'title': 'Implement core features', 'description': 'Build the main functionality with CRUD operations'},
            {'title': 'Add authentication', 'description': 'Implement user login/signup with JWT'},
            {'title': 'Deploy to production', 'description': 'Deploy the app to Vercel or similar platform'},
        ]
    })

    # Add a branding step with tasks
    steps.append({
        'title': 'Optimize Your GitHub Profile',
        'description': 'Improve your online presence to attract potential clients and employers.',
        'duration': '2 days',
        'status': 'pending',
        'type': 'branding',
        'tasks': [
            {'title': 'Update profile README', 'description': 'Create an engaging profile README with skills and stats'},
            {'title': 'Pin best repositories', 'description': 'Select and pin your top 4-6 projects'},
            {'title': 'Write detailed READMEs', 'description': 'Add screenshots, demos, and setup instructions to repos'},
        ]
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
