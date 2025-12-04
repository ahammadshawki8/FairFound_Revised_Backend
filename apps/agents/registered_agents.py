"""
Registered Agents - All agents registered with the AgentRegistry
This file registers all agents so they can be discovered and orchestrated.
"""
from typing import Dict, List, Any

from .base import BaseAgent, ScoringAgent, CollectorAgent, EvaluationAgent, AgentContext, AgentResult
from .registry import AgentRegistry, register_agent
from .scoring import (
    calculate_skill_score, calculate_github_score,
    calculate_portfolio_score, calculate_experience_score,
    compute_overall_score, generate_improvements
)
from .collectors import fetch_github_metrics, fetch_portfolio_meta
from .synthetic_data import get_junior_frontend_benchmark
from .parsers import parse_cv_with_ai, parse_cv_complete


# ============================================
# DATA COLLECTION AGENTS
# ============================================

@register_agent(
    agent_id='cv_parser',
    capabilities=['data_collection', 'cv_parsing', 'document_processing'],
    description='Parses CV/Resume PDFs to extract skills, experience, and contact info'
)
class CVParserAgent(CollectorAgent):
    """
    CV/Resume Parser Agent
    
    Extracts structured information from PDF resumes using:
    1. AI-powered extraction (Gemini) for comprehensive parsing
    2. Rule-based extraction as fallback
    
    Extracted data includes:
    - Personal info (name, email, phone, location)
    - Skills by category (frontend, backend, database, etc.)
    - Work experience with duration
    - Education history
    - Projects and certifications
    - Total years of experience
    """
    
    @property
    def capabilities(self) -> List[str]:
        return ['data_collection', 'cv_parsing', 'document_processing']
    
    def _execute(self, context: AgentContext) -> AgentResult:
        cv_file_path = context.input_data.get('cv_file_path')
        
        if not cv_file_path:
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                data={'cv_data': None, 'skipped': True},
                confidence=0.5,
                metadata={'reason': 'No CV file provided'}
            )
        
        try:
            # Use AI-enhanced parsing
            cv_data = parse_cv_with_ai(cv_file_path)
            
            if cv_data.get('error'):
                return AgentResult(
                    agent_id=self.agent_id,
                    success=False,
                    error=cv_data['error'],
                    confidence=0.0
                )
            
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                data={'cv_data': cv_data},
                confidence=cv_data.get('confidence', 0.7),
                metadata={
                    'extraction_method': cv_data.get('method', 'unknown'),
                    'skills_found': len(cv_data.get('all_skills', [])),
                    'experience_years': cv_data.get('experience_years')
                }
            )
            
        except Exception as e:
            return AgentResult(
                agent_id=self.agent_id,
                success=False,
                error=f"CV parsing failed: {str(e)}",
                confidence=0.0
            )
    
    def get_fallback_result(self, context: AgentContext) -> AgentResult:
        """Return empty CV data as fallback"""
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            data={'cv_data': None, 'skipped': True},
            confidence=0.3,
            metadata={'used_fallback': True, 'reason': 'CV parsing failed'}
        )


@register_agent(
    agent_id='form_processor',
    capabilities=['data_collection', 'validation'],
    description='Processes and validates user form input'
)
class FormProcessorAgent(CollectorAgent):
    """Processes user-submitted form data"""
    
    @property
    def capabilities(self) -> List[str]:
        return ['data_collection', 'validation']
    
    def _execute(self, context: AgentContext) -> AgentResult:
        form_data = context.input_data.get('form_fields', {})
        
        # Validate and normalize
        processed = {
            'name': form_data.get('name', ''),
            'email': form_data.get('email', ''),
            'title': form_data.get('title', 'Junior Frontend Developer'),
            'skills': [s.strip() for s in form_data.get('skills', []) if s.strip()],
            'experience_years': float(form_data.get('experience_years', 0)),
            'hourly_rate': float(form_data.get('hourly_rate', 0)) if form_data.get('hourly_rate') else None,
            'bio': form_data.get('bio', ''),
            'location': form_data.get('location', ''),
            'project_count': int(form_data.get('project_count', 0)),
            'has_live_demos': bool(form_data.get('has_live_demos', False))
        }
        
        # Calculate data completeness
        filled_fields = sum(1 for v in processed.values() if v)
        completeness = filled_fields / len(processed)
        
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            data={'form_data': processed, 'completeness': completeness},
            confidence=completeness
        )


@register_agent(
    agent_id='github_collector',
    capabilities=['data_collection', 'github'],
    description='Fetches GitHub profile metrics'
)
class GitHubCollectorAgent(CollectorAgent):
    """Collects GitHub profile data"""
    
    @property
    def capabilities(self) -> List[str]:
        return ['data_collection', 'github']
    
    def _execute(self, context: AgentContext) -> AgentResult:
        github_username = context.input_data.get('github_username')
        
        if not github_username:
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                data={'github_data': None, 'skipped': True},
                confidence=0.5,
                metadata={'reason': 'No GitHub username provided'}
            )
        
        github_data = fetch_github_metrics(github_username)
        
        if github_data.get('error'):
            return AgentResult(
                agent_id=self.agent_id,
                success=False,
                error=github_data['error'],
                confidence=0.0
            )
        
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            data={'github_data': github_data},
            confidence=github_data.get('confidence', 0.8)
        )


@register_agent(
    agent_id='portfolio_collector',
    capabilities=['data_collection', 'portfolio'],
    description='Scrapes portfolio website metadata'
)
class PortfolioCollectorAgent(CollectorAgent):
    """Collects portfolio website data"""
    
    @property
    def capabilities(self) -> List[str]:
        return ['data_collection', 'portfolio']
    
    def _execute(self, context: AgentContext) -> AgentResult:
        portfolio_url = context.input_data.get('portfolio_url')
        
        if not portfolio_url:
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                data={'portfolio_data': None, 'skipped': True},
                confidence=0.5,
                metadata={'reason': 'No portfolio URL provided'}
            )
        
        portfolio_data = fetch_portfolio_meta(portfolio_url)
        
        if portfolio_data.get('error'):
            return AgentResult(
                agent_id=self.agent_id,
                success=False,
                error=portfolio_data['error'],
                confidence=0.0
            )
        
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            data={'portfolio_data': portfolio_data},
            confidence=portfolio_data.get('confidence', 0.7)
        )


# ============================================
# SCORING AGENTS
# ============================================

@register_agent(
    agent_id='skill_scorer',
    capabilities=['scoring', 'skills'],
    dependencies=['form_processor', 'cv_parser'],
    priority=10,
    description='Scores technical skills from form and CV data'
)
class SkillScoringAgent(ScoringAgent):
    """
    Scores user's technical skills.
    Combines skills from form input and CV parsing for comprehensive assessment.
    """
    
    @property
    def dependencies(self) -> List[str]:
        return ['form_processor', 'cv_parser']
    
    def _execute(self, context: AgentContext) -> AgentResult:
        form_result = context.get_result('form_processor')
        cv_result = context.get_result('cv_parser')
        
        # Collect skills from all sources
        all_skills = set()
        
        # From form
        if form_result and form_result.success:
            form_data = form_result.data.get('form_data', {})
            form_skills = form_data.get('skills', [])
            all_skills.update(s.lower() for s in form_skills)
        
        # From CV
        if cv_result and cv_result.success and not cv_result.data.get('skipped'):
            cv_data = cv_result.data.get('cv_data', {})
            cv_skills = cv_data.get('all_skills', [])
            all_skills.update(s.lower() for s in cv_skills)
        
        if not all_skills and (not form_result or not form_result.success):
            return self.get_fallback_result(context)
        
        # Use combined skills for scoring
        skills_data = {'all_skills': list(all_skills)}
        score, level, details = calculate_skill_score(skills_data)
        
        # Track skill sources
        skill_sources = []
        if form_result and form_result.success:
            form_skills = form_result.data.get('form_data', {}).get('skills', [])
            if form_skills:
                skill_sources.append('form')
        if cv_result and cv_result.success and not cv_result.data.get('skipped'):
            cv_skills = cv_result.data.get('cv_data', {}).get('all_skills', [])
            if cv_skills:
                skill_sources.append('cv')
        
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            data={
                'score': score,
                'level': level,
                'details': details,
                'total_skills': len(all_skills),
                'skill_sources': skill_sources
            },
            confidence=0.95 if len(skill_sources) > 1 else 0.85 if all_skills else 0.5
        )
    
    def get_fallback_result(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            data={'score': 0.3, 'level': 'beginner', 'details': {}},
            confidence=0.3,
            metadata={'used_fallback': True}
        )


@register_agent(
    agent_id='github_scorer',
    capabilities=['scoring', 'github'],
    dependencies=['github_collector'],
    priority=8,
    description='Scores GitHub activity'
)
class GitHubScoringAgent(ScoringAgent):
    """Scores GitHub activity"""
    
    @property
    def dependencies(self) -> List[str]:
        return ['github_collector']
    
    def _execute(self, context: AgentContext) -> AgentResult:
        github_result = context.get_result('github_collector')
        
        if not github_result or not github_result.success:
            return self.get_fallback_result(context)
        
        github_data = github_result.data.get('github_data')
        
        if not github_data or github_result.data.get('skipped'):
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                data={'score': 0.2, 'level': 'minimal', 'details': {'skipped': True}},
                confidence=0.5
            )
        
        score, level, details = calculate_github_score(github_data)
        
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            data={'score': score, 'level': level, 'details': details},
            confidence=0.85
        )
    
    def get_fallback_result(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            data={'score': 0.2, 'level': 'minimal', 'details': {}},
            confidence=0.3,
            metadata={'used_fallback': True}
        )


@register_agent(
    agent_id='portfolio_scorer',
    capabilities=['scoring', 'portfolio'],
    dependencies=['portfolio_collector', 'form_processor'],
    priority=7,
    description='Scores portfolio quality'
)
class PortfolioScoringAgent(ScoringAgent):
    """Scores portfolio quality"""
    
    @property
    def dependencies(self) -> List[str]:
        return ['portfolio_collector', 'form_processor']
    
    def _execute(self, context: AgentContext) -> AgentResult:
        portfolio_result = context.get_result('portfolio_collector')
        form_result = context.get_result('form_processor')
        
        # Build portfolio data from multiple sources
        portfolio_data = {}
        
        if portfolio_result and portfolio_result.success:
            scraped = portfolio_result.data.get('portfolio_data', {})
            if scraped and not portfolio_result.data.get('skipped'):
                portfolio_data = scraped
        
        # Supplement with form data
        if form_result and form_result.success:
            form_data = form_result.data.get('form_data', {})
            portfolio_data['project_count'] = portfolio_data.get('estimated_projects', 0) or form_data.get('project_count', 0)
            portfolio_data['has_live_demos'] = form_data.get('has_live_demos', False)
            portfolio_data['has_projects'] = portfolio_data.get('project_count', 0) > 0
        
        if not portfolio_data:
            portfolio_data = {
                'has_projects': False,
                'project_count': 0,
                'has_live_demos': False,
                'quality_score': 0.2
            }
        
        score, level, details = calculate_portfolio_score(portfolio_data)
        
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            data={'score': score, 'level': level, 'details': details},
            confidence=0.7 if portfolio_data.get('has_projects') else 0.5
        )


@register_agent(
    agent_id='experience_scorer',
    capabilities=['scoring', 'experience'],
    dependencies=['form_processor', 'cv_parser'],
    priority=6,
    description='Scores experience level from form and CV data'
)
class ExperienceScoringAgent(ScoringAgent):
    """
    Scores experience depth.
    Uses experience years from form input or CV parsing (whichever is higher).
    """
    
    @property
    def dependencies(self) -> List[str]:
        return ['form_processor', 'cv_parser']
    
    def _execute(self, context: AgentContext) -> AgentResult:
        form_result = context.get_result('form_processor')
        cv_result = context.get_result('cv_parser')
        
        # Get experience from form
        form_experience = 0
        if form_result and form_result.success:
            form_data = form_result.data.get('form_data', {})
            form_experience = form_data.get('experience_years', 0) or 0
        
        # Get experience from CV
        cv_experience = 0
        if cv_result and cv_result.success and not cv_result.data.get('skipped'):
            cv_data = cv_result.data.get('cv_data', {})
            cv_experience = cv_data.get('experience_years') or 0
        
        # Use the higher value (CV might have more accurate data)
        experience_years = max(form_experience, cv_experience)
        experience_source = 'cv' if cv_experience > form_experience else 'form'
        
        score, level, details = calculate_experience_score(experience_years)
        details['experience_source'] = experience_source
        details['form_years'] = form_experience
        details['cv_years'] = cv_experience
        
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            data={'score': score, 'level': level, 'details': details},
            confidence=0.95 if cv_experience > 0 else 0.85
        )


@register_agent(
    agent_id='score_aggregator',
    capabilities=['scoring', 'aggregation'],
    dependencies=['skill_scorer', 'github_scorer', 'portfolio_scorer', 'experience_scorer'],
    priority=5,
    description='Aggregates all scores into overall score'
)
class ScoreAggregatorAgent(ScoringAgent):
    """Aggregates component scores into overall score"""
    
    @property
    def dependencies(self) -> List[str]:
        return ['skill_scorer', 'github_scorer', 'portfolio_scorer', 'experience_scorer']
    
    def _execute(self, context: AgentContext) -> AgentResult:
        # Gather all scores
        skill_result = context.get_result('skill_scorer')
        github_result = context.get_result('github_scorer')
        portfolio_result = context.get_result('portfolio_scorer')
        experience_result = context.get_result('experience_scorer')
        
        # Build features dict
        features = {
            'skill': self._extract_score_tuple(skill_result, 'skill'),
            'github': self._extract_score_tuple(github_result, 'github'),
            'portfolio': self._extract_score_tuple(portfolio_result, 'portfolio'),
            'experience': self._extract_score_tuple(experience_result, 'experience'),
            'learning_momentum': 0.5
        }
        
        # Calculate learning momentum from GitHub activity
        if github_result and github_result.success:
            github_score = github_result.data.get('score', 0.2)
            if github_score > 0.3:
                features['learning_momentum'] = min(0.9, 0.3 + (github_score * 0.5))
        
        # Compute overall score
        score_result = compute_overall_score(features)
        
        # Calculate aggregate confidence
        confidences = [
            skill_result.confidence if skill_result else 0.5,
            github_result.confidence if github_result else 0.5,
            portfolio_result.confidence if portfolio_result else 0.5,
            experience_result.confidence if experience_result else 0.5
        ]
        avg_confidence = sum(confidences) / len(confidences)
        
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            data={'score_result': score_result},
            confidence=avg_confidence
        )
    
    def _extract_score_tuple(self, result: AgentResult, name: str):
        """Extract (score, level, details) tuple from result"""
        if not result or not result.success:
            return (0.3, 'unknown', {})
        
        data = result.data
        return (
            data.get('score', 0.3),
            data.get('level', 'unknown'),
            data.get('details', {})
        )


@register_agent(
    agent_id='benchmark_agent',
    capabilities=['benchmarking', 'comparison'],
    dependencies=['score_aggregator'],
    priority=4,
    description='Compares score against benchmark cohort'
)
class BenchmarkAgent(BaseAgent):
    """Compares user against benchmark cohort"""
    
    @property
    def capabilities(self) -> List[str]:
        return ['benchmarking', 'comparison']
    
    @property
    def dependencies(self) -> List[str]:
        return ['score_aggregator']
    
    def _execute(self, context: AgentContext) -> AgentResult:
        aggregator_result = context.get_result('score_aggregator')
        
        # Get user skills from context for personalized skill gaps
        user_skills = []
        form_result = context.get_result('form_processor')
        if form_result and form_result.success:
            user_skills = form_result.data.get('skills', [])
        
        if not aggregator_result or not aggregator_result.success:
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                data={'benchmark': get_junior_frontend_benchmark(0.5, user_skills)},
                confidence=0.5
            )
        
        score_result = aggregator_result.data.get('score_result', {})
        overall_score = score_result.get('overall_score', 0.5)
        
        benchmark = get_junior_frontend_benchmark(overall_score, user_skills)
        
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            data={'benchmark': benchmark},
            confidence=0.85
        )


@register_agent(
    agent_id='llm_judge',
    capabilities=['evaluation', 'llm', 'judgment'],
    dependencies=['score_aggregator', 'benchmark_agent'],
    priority=3,
    description='LLM-as-a-Judge evaluation with confidence loop'
)
class LLMJudgeAgent(EvaluationAgent):
    """LLM-based evaluation with iterative confidence loop"""
    
    @property
    def capabilities(self) -> List[str]:
        return ['evaluation', 'llm', 'judgment']
    
    @property
    def dependencies(self) -> List[str]:
        return ['score_aggregator', 'benchmark_agent']
    
    def _execute(self, context: AgentContext) -> AgentResult:
        from .llm_judge import evaluate_junior_frontend
        
        aggregator_result = context.get_result('score_aggregator')
        benchmark_result = context.get_result('benchmark_agent')
        form_result = context.get_result('form_processor')
        github_result = context.get_result('github_collector')
        
        # Build structured data
        structured_data = {
            'form': form_result.data.get('form_data', {}) if form_result else {},
            'github': github_result.data.get('github_data', {}) if github_result else {}
        }
        
        score_result = aggregator_result.data.get('score_result', {}) if aggregator_result else {}
        benchmark = benchmark_result.data.get('benchmark', {}) if benchmark_result else {}
        
        # Run LLM evaluation
        evaluation = evaluate_junior_frontend(structured_data, score_result, benchmark)
        
        confidence = evaluation.get('confidence', 0.7)
        
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            data={'evaluation': evaluation},
            confidence=confidence,
            metadata={
                'evaluation_type': evaluation.get('evaluation_type', 'unknown'),
                'iterations': evaluation.get('evaluation_metadata', {}).get('iterations', 1)
            }
        )


@register_agent(
    agent_id='improvement_generator',
    capabilities=['recommendations', 'improvements'],
    dependencies=['score_aggregator'],
    priority=2,
    description='Generates improvement recommendations'
)
class ImprovementGeneratorAgent(BaseAgent):
    """Generates prioritized improvement recommendations"""
    
    @property
    def capabilities(self) -> List[str]:
        return ['recommendations', 'improvements']
    
    @property
    def dependencies(self) -> List[str]:
        return ['score_aggregator']
    
    def _execute(self, context: AgentContext) -> AgentResult:
        aggregator_result = context.get_result('score_aggregator')
        
        if not aggregator_result or not aggregator_result.success:
            return AgentResult(
                agent_id=self.agent_id,
                success=True,
                data={'improvements': []},
                confidence=0.5
            )
        
        score_result = aggregator_result.data.get('score_result', {})
        breakdown = score_result.get('breakdown', {})
        
        improvements = generate_improvements(breakdown)
        
        return AgentResult(
            agent_id=self.agent_id,
            success=True,
            data={'improvements': improvements},
            confidence=0.85
        )


def register_all_agents():
    """
    Ensure all agents are registered.
    Call this at application startup.
    """
    # The decorators handle registration, but we can verify here
    expected_agents = [
        'cv_parser', 'form_processor', 'github_collector', 'portfolio_collector',
        'skill_scorer', 'github_scorer', 'portfolio_scorer', 'experience_scorer',
        'score_aggregator', 'benchmark_agent', 'llm_judge', 'improvement_generator'
    ]
    
    registered = list(AgentRegistry.get_all().keys())
    
    for agent_id in expected_agents:
        if agent_id not in registered:
            print(f"Warning: Agent {agent_id} not registered")
    
    return registered
