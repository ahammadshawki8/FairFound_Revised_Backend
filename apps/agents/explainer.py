"""
Explainer Agent - Generates human-readable explanations for AI decisions
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class Explanation:
    """A structured explanation of an AI decision"""
    summary: str
    detailed_breakdown: List[Dict[str, Any]]
    key_factors: List[str]
    counterfactuals: List[Dict[str, Any]]
    confidence_explanation: str
    visualization_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'summary': self.summary,
            'detailed_breakdown': self.detailed_breakdown,
            'key_factors': self.key_factors,
            'counterfactuals': self.counterfactuals,
            'confidence_explanation': self.confidence_explanation,
            'visualization_data': self.visualization_data
        }


class ExplainerAgent:
    """
    Generates human-readable explanations for AI decisions.
    
    Features:
    - Natural language score explanations
    - Counterfactual analysis ("what if" scenarios)
    - Decision tree visualization data
    - Factor importance ranking
    """
    
    def __init__(self):
        self.weight_labels = {
            'skill_strength': 'Technical Skills',
            'github_activity': 'GitHub Activity',
            'portfolio_quality': 'Portfolio Quality',
            'experience_depth': 'Experience Level',
            'learning_momentum': 'Learning Progress'
        }
        
        self.tier_descriptions = {
            'Strong Junior': 'You have a strong foundation and are ready for junior developer roles.',
            'Competent': 'You have solid skills and are close to being job-ready.',
            'Developing': 'You are building good habits and making progress.',
            'Early Stage': 'You are just starting your journey - focus on fundamentals.'
        }
    
    def explain_score(self, score_result: Dict, benchmark: Dict = None) -> Explanation:
        """
        Generate a comprehensive explanation of a score.
        
        Args:
            score_result: The scoring result with breakdown
            benchmark: Optional benchmark data for context
        
        Returns:
            Explanation object with all details
        """
        overall_score = score_result.get('overall_score', 0)
        tier = score_result.get('tier', 'Unknown')
        breakdown = score_result.get('breakdown', {})
        
        # Generate summary
        summary = self._generate_summary(overall_score, tier, benchmark)
        
        # Generate detailed breakdown
        detailed_breakdown = self._generate_detailed_breakdown(breakdown)
        
        # Identify key factors
        key_factors = self._identify_key_factors(breakdown)
        
        # Generate counterfactuals
        counterfactuals = self._generate_counterfactuals(breakdown, overall_score)
        
        # Explain confidence
        confidence_explanation = self._explain_confidence(score_result)
        
        # Generate visualization data
        visualization_data = self._generate_visualization_data(breakdown, benchmark)
        
        return Explanation(
            summary=summary,
            detailed_breakdown=detailed_breakdown,
            key_factors=key_factors,
            counterfactuals=counterfactuals,
            confidence_explanation=confidence_explanation,
            visualization_data=visualization_data
        )
    
    def _generate_summary(self, overall_score: float, tier: str, 
                         benchmark: Dict = None) -> str:
        """Generate a natural language summary"""
        score_percent = int(overall_score * 100)
        
        # Base description
        tier_desc = self.tier_descriptions.get(tier, 'Your skills are being evaluated.')
        
        # Add percentile context if available
        percentile_text = ""
        if benchmark and 'user_percentile' in benchmark:
            percentile = benchmark['user_percentile']
            if percentile >= 75:
                percentile_text = f" You're in the top {100 - percentile}% of junior frontend developers!"
            elif percentile >= 50:
                percentile_text = f" You're above average, ranking at the {percentile}th percentile."
            else:
                percentile_text = f" You're at the {percentile}th percentile - there's room to grow."
        
        return f"Your overall score is {score_percent}% ({tier} tier). {tier_desc}{percentile_text}"
    
    def _generate_detailed_breakdown(self, breakdown: Dict) -> List[Dict]:
        """Generate detailed explanation for each component"""
        details = []
        
        for component, data in breakdown.items():
            if not isinstance(data, dict):
                continue
            
            raw_score = data.get('raw_score', 0)
            weight = data.get('weight', 0)
            weighted = data.get('weighted', 0)
            level = data.get('level', 'unknown')
            
            label = self.weight_labels.get(component, component.replace('_', ' ').title())
            
            # Generate component-specific explanation
            explanation = self._explain_component(component, raw_score, level, data.get('details', {}))
            
            details.append({
                'component': component,
                'label': label,
                'score': raw_score,
                'score_percent': int(raw_score * 100),
                'weight': weight,
                'weight_percent': int(weight * 100),
                'contribution': weighted,
                'contribution_percent': int(weighted * 100),
                'level': level,
                'explanation': explanation,
                'impact': 'high' if weight >= 0.25 else 'medium' if weight >= 0.15 else 'low'
            })
        
        # Sort by contribution (highest first)
        details.sort(key=lambda x: x['contribution'], reverse=True)
        
        return details
    
    def _explain_component(self, component: str, score: float, 
                          level: str, details: Dict) -> str:
        """Generate explanation for a specific component"""
        explanations = {
            'skill_strength': {
                'strong': "Excellent technical skills! You have a strong foundation in modern frontend technologies.",
                'solid': "Good skill set. Consider adding TypeScript or testing to stand out.",
                'developing': "Building your skills. Focus on mastering React and JavaScript fundamentals.",
                'beginner': "Just starting out. Learn HTML, CSS, and JavaScript basics first."
            },
            'github_activity': {
                'active': "Great GitHub presence! Your consistent activity shows dedication.",
                'regular': "Good activity level. Try to commit more frequently.",
                'occasional': "Some GitHub activity. Aim for daily commits to build momentum.",
                'minimal': "Limited GitHub activity. Start pushing code regularly to showcase your work."
            },
            'portfolio_quality': {
                'impressive': "Impressive portfolio! Your projects demonstrate real-world skills.",
                'good': "Good portfolio. Add live demos and detailed case studies.",
                'basic': "Basic portfolio. Build 2-3 more polished projects.",
                'minimal': "Portfolio needs work. Create projects with live demos and documentation."
            },
            'experience_depth': {
                'experienced': "Good experience level for a junior developer.",
                'some': "Building experience. Keep working on projects.",
                'early': "Early in your journey. Focus on learning and building.",
                'new': "Just starting. Everyone begins somewhere - keep going!"
            }
        }
        
        component_explanations = explanations.get(component, {})
        return component_explanations.get(level, f"Your {component.replace('_', ' ')} is at the {level} level.")
    
    def _identify_key_factors(self, breakdown: Dict) -> List[str]:
        """Identify the key factors affecting the score"""
        factors = []
        
        # Find highest and lowest scoring components
        scores = []
        for component, data in breakdown.items():
            if isinstance(data, dict) and 'raw_score' in data:
                scores.append((component, data['raw_score'], data.get('weight', 0)))
        
        if not scores:
            return ["Unable to identify key factors"]
        
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Highest contributor
        highest = scores[0]
        label = self.weight_labels.get(highest[0], highest[0])
        factors.append(f"Your strongest area is {label} ({int(highest[1] * 100)}%)")
        
        # Lowest contributor
        lowest = scores[-1]
        label = self.weight_labels.get(lowest[0], lowest[0])
        factors.append(f"Your biggest opportunity for improvement is {label} ({int(lowest[1] * 100)}%)")
        
        # High-weight components
        high_weight = [s for s in scores if s[2] >= 0.25]
        for comp, score, weight in high_weight:
            if score < 0.5:
                label = self.weight_labels.get(comp, comp)
                factors.append(f"{label} has high weight ({int(weight * 100)}%) but low score - focus here for maximum impact")
        
        return factors[:5]
    
    def _generate_counterfactuals(self, breakdown: Dict, 
                                  current_score: float) -> List[Dict]:
        """
        Generate "what if" scenarios showing how score could improve.
        """
        counterfactuals = []
        
        for component, data in breakdown.items():
            if not isinstance(data, dict):
                continue
            
            raw_score = data.get('raw_score', 0)
            weight = data.get('weight', 0)
            
            # Skip if already high
            if raw_score >= 0.8:
                continue
            
            # Calculate impact of improving this component
            improvement_scenarios = [
                (0.1, "small improvement"),
                (0.2, "moderate improvement"),
                (0.3, "significant improvement")
            ]
            
            for improvement, description in improvement_scenarios:
                new_component_score = min(1.0, raw_score + improvement)
                score_increase = improvement * weight
                new_total = current_score + score_increase
                
                if new_total > current_score + 0.02:  # Only show meaningful improvements
                    label = self.weight_labels.get(component, component)
                    
                    counterfactuals.append({
                        'component': component,
                        'label': label,
                        'scenario': f"If you made a {description} in {label}",
                        'current_component_score': int(raw_score * 100),
                        'new_component_score': int(new_component_score * 100),
                        'current_total': int(current_score * 100),
                        'new_total': int(new_total * 100),
                        'improvement': int(score_increase * 100),
                        'action': self._get_improvement_action(component, improvement)
                    })
                    break  # Only show one scenario per component
        
        # Sort by potential improvement
        counterfactuals.sort(key=lambda x: x['improvement'], reverse=True)
        
        return counterfactuals[:5]
    
    def _get_improvement_action(self, component: str, improvement: float) -> str:
        """Get specific action to achieve improvement"""
        actions = {
            'skill_strength': {
                0.1: "Learn one new technology (e.g., TypeScript)",
                0.2: "Master a testing framework and TypeScript",
                0.3: "Add TypeScript, testing, and a CSS framework"
            },
            'github_activity': {
                0.1: "Commit code 3-4 times per week",
                0.2: "Create 2-3 new public repositories",
                0.3: "Maintain daily commits and contribute to open source"
            },
            'portfolio_quality': {
                0.1: "Add live demos to existing projects",
                0.2: "Build one polished project with documentation",
                0.3: "Create 3 portfolio projects with case studies"
            },
            'experience_depth': {
                0.1: "Complete a few freelance projects",
                0.2: "Work on a substantial side project",
                0.3: "Gain 6+ months of practical experience"
            }
        }
        
        component_actions = actions.get(component, {})
        
        if improvement <= 0.1:
            return component_actions.get(0.1, "Make small improvements")
        elif improvement <= 0.2:
            return component_actions.get(0.2, "Make moderate improvements")
        else:
            return component_actions.get(0.3, "Make significant improvements")
    
    def _explain_confidence(self, score_result: Dict) -> str:
        """Explain the confidence level of the evaluation"""
        # Check for evaluation metadata
        eval_metadata = score_result.get('evaluation_metadata', {})
        confidence = eval_metadata.get('final_confidence', 0.85)
        iterations = eval_metadata.get('iterations', 1)
        
        if confidence >= 0.9:
            return f"High confidence evaluation ({int(confidence * 100)}%). The data provided was comprehensive and consistent."
        elif confidence >= 0.8:
            return f"Good confidence ({int(confidence * 100)}%). The evaluation is reliable based on the available data."
        elif confidence >= 0.7:
            return f"Moderate confidence ({int(confidence * 100)}%). Some data may be incomplete. Consider adding more information."
        else:
            return f"Lower confidence ({int(confidence * 100)}%). The evaluation may improve with more complete data (GitHub, portfolio, etc.)."
    
    def _generate_visualization_data(self, breakdown: Dict, 
                                     benchmark: Dict = None) -> Dict:
        """Generate data for visualizations"""
        # Radar chart data
        radar_data = []
        for component, data in breakdown.items():
            if isinstance(data, dict) and 'raw_score' in data:
                radar_data.append({
                    'axis': self.weight_labels.get(component, component),
                    'value': data['raw_score']
                })
        
        # Bar chart data (contribution)
        bar_data = []
        for component, data in breakdown.items():
            if isinstance(data, dict):
                bar_data.append({
                    'name': self.weight_labels.get(component, component),
                    'score': data.get('raw_score', 0),
                    'weight': data.get('weight', 0),
                    'contribution': data.get('weighted', 0)
                })
        
        # Benchmark comparison if available
        benchmark_comparison = None
        if benchmark:
            benchmark_comparison = {
                'user_percentile': benchmark.get('user_percentile', 50),
                'avg_score': benchmark.get('avg_score', 0.5),
                'distribution': benchmark.get('distribution', [])
            }
        
        return {
            'radar': radar_data,
            'bar': bar_data,
            'benchmark': benchmark_comparison
        }
    
    def explain_recommendation(self, recommendation: Dict) -> str:
        """Generate explanation for a specific recommendation"""
        area = recommendation.get('area', 'General')
        action = recommendation.get('action', '')
        impact = recommendation.get('impact', 'medium')
        time_estimate = recommendation.get('time_estimate', 'varies')
        
        impact_text = {
            'high': 'This will significantly improve your profile.',
            'medium': 'This will noticeably improve your profile.',
            'low': 'This is a nice-to-have improvement.'
        }.get(impact, '')
        
        return f"**{area}**: {action}\n\n{impact_text} Estimated time: {time_estimate}."
    
    def generate_decision_tree(self, score_result: Dict) -> Dict:
        """
        Generate a decision tree representation of how the score was calculated.
        """
        overall_score = score_result.get('overall_score', 0)
        tier = score_result.get('tier', 'Unknown')
        breakdown = score_result.get('breakdown', {})
        
        tree = {
            'name': f'Overall Score: {int(overall_score * 100)}%',
            'tier': tier,
            'children': []
        }
        
        for component, data in breakdown.items():
            if not isinstance(data, dict):
                continue
            
            child = {
                'name': self.weight_labels.get(component, component),
                'score': data.get('raw_score', 0),
                'weight': data.get('weight', 0),
                'contribution': data.get('weighted', 0),
                'level': data.get('level', 'unknown'),
                'children': []
            }
            
            # Add sub-factors if available
            details = data.get('details', {})
            if isinstance(details, dict):
                for key, value in details.items():
                    if key not in ['message', 'recommendation']:
                        child['children'].append({
                            'name': key.replace('_', ' ').title(),
                            'value': value
                        })
            
            tree['children'].append(child)
        
        return tree


# Global explainer instance
_explainer: Optional[ExplainerAgent] = None


def get_explainer() -> ExplainerAgent:
    """Get the global explainer instance"""
    global _explainer
    if _explainer is None:
        _explainer = ExplainerAgent()
    return _explainer
