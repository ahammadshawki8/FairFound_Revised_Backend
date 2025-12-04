"""
Adaptive Learning Agent - Learns and adapts from feedback and outcomes
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
import logging
import json

from django.utils import timezone
from django.db.models import Avg, Count, Q

logger = logging.getLogger(__name__)


@dataclass
class LearningSignal:
    """A signal that the system should learn from"""
    signal_type: str  # 'human_feedback', 'outcome', 'market_data'
    source: str
    data: Dict[str, Any]
    weight: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class WeightUpdate:
    """A proposed weight update"""
    component: str
    current_weight: float
    proposed_weight: float
    change: float
    reason: str
    confidence: float


class AdaptiveLearningAgent:
    """
    Learns and adapts scoring weights based on feedback and outcomes.
    
    Features:
    - Learn from human review feedback
    - Adjust weights based on success metrics
    - Personalize recommendations per user
    - Track market trends for skill valuations
    """
    
    def __init__(self):
        self._learning_signals: List[LearningSignal] = []
        self._weight_history: List[Dict] = []
        
        # Default weights (from scoring.py)
        self.current_weights = {
            'skill_strength': 0.35,
            'github_activity': 0.25,
            'portfolio_quality': 0.20,
            'experience_depth': 0.15,
            'learning_momentum': 0.05
        }
        
        # Learning rate controls how fast weights change
        self.learning_rate = 0.05
        self.min_weight = 0.05
        self.max_weight = 0.50
    
    def add_learning_signal(self, signal: LearningSignal):
        """Add a learning signal to be processed"""
        self._learning_signals.append(signal)
        logger.debug(f"Added learning signal: {signal.signal_type} from {signal.source}")
    
    def learn_from_human_reviews(self, time_window: timedelta = None) -> List[WeightUpdate]:
        """
        Analyze human reviews and propose weight adjustments.
        
        Args:
            time_window: Only consider reviews within this window
        
        Returns:
            List of proposed weight updates
        """
        from .models import HumanReview, IngestionJob
        
        queryset = HumanReview.objects.filter(
            decision__in=['approved', 'rejected', 'modified']
        )
        
        if time_window:
            cutoff = timezone.now() - time_window
            queryset = queryset.filter(reviewed_at__gte=cutoff)
        
        reviews = list(queryset.select_related('job')[:200])
        
        if len(reviews) < 10:
            logger.info("Not enough reviews for learning")
            return []
        
        logger.info(f"Learning from {len(reviews)} human reviews")
        
        # Analyze patterns in rejected/modified reviews
        weight_adjustments = defaultdict(list)
        
        for review in reviews:
            if not review.job or not review.job.result:
                continue
            
            result = review.job.result
            breakdown = result.get('score_result', {}).get('breakdown', {})
            
            if review.decision == 'rejected':
                # The AI evaluation was wrong - analyze which components were off
                for component, data in breakdown.items():
                    if isinstance(data, dict):
                        raw_score = data.get('raw_score', 0)
                        
                        # If component had high score but overall was rejected,
                        # maybe it's overweighted
                        if raw_score > 0.7:
                            weight_adjustments[component].append(-0.02)
                        # If component had low score, maybe it's underweighted
                        elif raw_score < 0.3:
                            weight_adjustments[component].append(0.01)
            
            elif review.decision == 'modified':
                # Check what was modified
                original_score = result.get('score_result', {}).get('overall_score', 0)
                modified_score = review.modified_score
                
                if modified_score:
                    diff = modified_score - original_score
                    
                    # If human increased score, we were too harsh
                    # If human decreased score, we were too lenient
                    for component, data in breakdown.items():
                        if isinstance(data, dict):
                            raw_score = data.get('raw_score', 0)
                            
                            if diff > 0.1 and raw_score < 0.5:
                                # We undervalued this component
                                weight_adjustments[component].append(0.01)
                            elif diff < -0.1 and raw_score > 0.5:
                                # We overvalued this component
                                weight_adjustments[component].append(-0.01)
            
            elif review.decision == 'approved':
                # Reinforce current weights slightly
                for component in breakdown.keys():
                    weight_adjustments[component].append(0.002)
        
        # Calculate proposed updates
        updates = []
        for component, adjustments in weight_adjustments.items():
            if component not in self.current_weights:
                continue
            
            avg_adjustment = statistics.mean(adjustments)
            
            # Apply learning rate
            change = avg_adjustment * self.learning_rate * len(adjustments)
            
            # Limit change magnitude
            change = max(-0.05, min(0.05, change))
            
            if abs(change) > 0.001:
                current = self.current_weights[component]
                proposed = max(self.min_weight, min(self.max_weight, current + change))
                
                updates.append(WeightUpdate(
                    component=component,
                    current_weight=current,
                    proposed_weight=proposed,
                    change=proposed - current,
                    reason=f"Based on {len(adjustments)} reviews",
                    confidence=min(1.0, len(adjustments) / 50)
                ))
        
        return updates
    
    def learn_from_outcomes(self, user_id: int = None) -> Dict[str, Any]:
        """
        Learn from actual user outcomes (job placements, rate increases, etc.)
        
        This is a placeholder for future implementation when outcome tracking
        is available.
        """
        # TODO: Implement when outcome tracking is available
        return {
            'status': 'not_implemented',
            'message': 'Outcome tracking not yet available'
        }
    
    def update_skill_valuations(self, market_data: Dict[str, float] = None) -> Dict[str, float]:
        """
        Update skill valuations based on market demand.
        
        Args:
            market_data: Dictionary of skill -> demand_score
        
        Returns:
            Updated skill weights
        """
        from .scoring import FRONTEND_SKILL_TIERS
        
        if not market_data:
            # Use default market data (could be fetched from job boards)
            market_data = {
                'react': 1.3,
                'typescript': 1.4,
                'next.js': 1.2,
                'vue': 1.0,
                'angular': 0.9,
                'tailwind': 1.1,
                'jest': 1.1,
                'graphql': 1.0
            }
        
        # Adjust skill tier weights based on market demand
        updated_tiers = {}
        
        for tier_name, tier_config in FRONTEND_SKILL_TIERS.items():
            tier_skills = tier_config['skills']
            base_weight = tier_config['weight']
            
            # Calculate average market demand for skills in this tier
            demands = [market_data.get(skill, 1.0) for skill in tier_skills]
            avg_demand = statistics.mean(demands) if demands else 1.0
            
            # Adjust weight based on demand
            adjusted_weight = base_weight * avg_demand
            
            updated_tiers[tier_name] = {
                **tier_config,
                'weight': round(adjusted_weight, 2),
                'market_adjustment': round(avg_demand, 2)
            }
        
        logger.info(f"Updated skill valuations based on market data")
        
        return updated_tiers
    
    def personalize_for_user(self, user_id: int) -> Dict[str, Any]:
        """
        Generate personalized adjustments for a specific user.
        
        Args:
            user_id: The user to personalize for
        
        Returns:
            Personalization settings
        """
        from .models import IngestionJob
        from apps.roadmap.models import RoadmapStep, Task
        
        # Get user's history
        jobs = IngestionJob.objects.filter(user_id=user_id, status='done').order_by('-created_at')[:5]
        
        if not jobs.exists():
            return {'personalized': False, 'reason': 'No history available'}
        
        # Analyze progress over time
        scores = []
        for job in jobs:
            if job.result:
                score = job.result.get('score_result', {}).get('overall_score', 0)
                scores.append({
                    'score': score,
                    'date': job.created_at
                })
        
        # Calculate progress trajectory
        if len(scores) >= 2:
            score_change = scores[0]['score'] - scores[-1]['score']
            days_elapsed = (scores[0]['date'] - scores[-1]['date']).days
            
            if days_elapsed > 0:
                daily_progress = score_change / days_elapsed
            else:
                daily_progress = 0
        else:
            score_change = 0
            daily_progress = 0
        
        # Get roadmap completion rate
        total_steps = RoadmapStep.objects.filter(user_id=user_id).count()
        completed_steps = RoadmapStep.objects.filter(user_id=user_id, status='completed').count()
        completion_rate = completed_steps / max(total_steps, 1)
        
        # Determine focus areas
        latest_job = jobs.first()
        focus_areas = []
        
        if latest_job and latest_job.result:
            breakdown = latest_job.result.get('score_result', {}).get('breakdown', {})
            
            # Find weakest areas
            component_scores = []
            for component, data in breakdown.items():
                if isinstance(data, dict) and 'raw_score' in data:
                    component_scores.append((component, data['raw_score']))
            
            component_scores.sort(key=lambda x: x[1])
            focus_areas = [c[0] for c in component_scores[:2]]
        
        return {
            'personalized': True,
            'user_id': user_id,
            'progress': {
                'score_change': score_change,
                'daily_progress': daily_progress,
                'trajectory': 'improving' if daily_progress > 0 else 'stable' if daily_progress == 0 else 'declining'
            },
            'roadmap': {
                'total_steps': total_steps,
                'completed_steps': completed_steps,
                'completion_rate': completion_rate
            },
            'focus_areas': focus_areas,
            'recommendations': self._generate_personalized_recommendations(
                focus_areas, completion_rate, daily_progress
            )
        }
    
    def _generate_personalized_recommendations(self, focus_areas: List[str],
                                               completion_rate: float,
                                               daily_progress: float) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        # Based on focus areas
        area_recommendations = {
            'skill_strength': "Focus on learning TypeScript and testing frameworks",
            'github_activity': "Increase your GitHub activity - aim for daily commits",
            'portfolio_quality': "Add 2-3 polished projects with live demos",
            'experience_depth': "Take on freelance projects to build experience"
        }
        
        for area in focus_areas:
            if area in area_recommendations:
                recommendations.append(area_recommendations[area])
        
        # Based on roadmap progress
        if completion_rate < 0.3:
            recommendations.append("Focus on completing your roadmap tasks - consistency is key")
        elif completion_rate > 0.7:
            recommendations.append("Great progress! Consider adding more advanced topics to your roadmap")
        
        # Based on trajectory
        if daily_progress < 0:
            recommendations.append("Your scores have been declining - review recent changes and refocus")
        elif daily_progress > 0.01:
            recommendations.append("You're making great progress! Keep up the momentum")
        
        return recommendations[:4]
    
    def apply_weight_updates(self, updates: List[WeightUpdate],
                            min_confidence: float = 0.5) -> Dict[str, float]:
        """
        Apply weight updates to current weights.
        
        Args:
            updates: List of proposed updates
            min_confidence: Minimum confidence to apply update
        
        Returns:
            New weights
        """
        new_weights = self.current_weights.copy()
        applied = []
        
        for update in updates:
            if update.confidence >= min_confidence:
                new_weights[update.component] = update.proposed_weight
                applied.append(update.component)
        
        # Normalize weights to sum to 1.0
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: v / total for k, v in new_weights.items()}
        
        # Store in history
        self._weight_history.append({
            'timestamp': datetime.now().isoformat(),
            'old_weights': self.current_weights.copy(),
            'new_weights': new_weights,
            'updates_applied': applied
        })
        
        self.current_weights = new_weights
        
        logger.info(f"Applied {len(applied)} weight updates")
        
        return new_weights
    
    def get_weight_history(self, limit: int = 10) -> List[Dict]:
        """Get recent weight change history"""
        return self._weight_history[-limit:]
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of learning activity"""
        from .models import HumanReview
        
        # Count reviews by decision
        review_counts = HumanReview.objects.values('decision').annotate(
            count=Count('id')
        )
        
        decision_counts = {r['decision']: r['count'] for r in review_counts}
        
        return {
            'total_signals': len(self._learning_signals),
            'weight_updates': len(self._weight_history),
            'current_weights': self.current_weights,
            'review_counts': decision_counts,
            'learning_rate': self.learning_rate
        }


class MarketTrendAnalyzer:
    """
    Analyzes market trends to inform skill valuations.
    """
    
    def __init__(self):
        self._trend_cache: Dict[str, Any] = {}
        self._cache_expiry: Optional[datetime] = None
    
    def get_skill_trends(self, skills: List[str] = None) -> Dict[str, Any]:
        """
        Get current market trends for skills.
        
        In production, this would fetch from job boards or market data APIs.
        """
        # Check cache
        if self._cache_expiry and datetime.now() < self._cache_expiry:
            return self._trend_cache
        
        # Default trend data (would be fetched from external sources)
        trends = {
            'react': {'demand': 'high', 'growth': 0.15, 'avg_salary': 95000},
            'typescript': {'demand': 'very_high', 'growth': 0.25, 'avg_salary': 100000},
            'next.js': {'demand': 'high', 'growth': 0.30, 'avg_salary': 105000},
            'vue': {'demand': 'medium', 'growth': 0.05, 'avg_salary': 90000},
            'angular': {'demand': 'medium', 'growth': -0.05, 'avg_salary': 92000},
            'tailwind': {'demand': 'high', 'growth': 0.35, 'avg_salary': 88000},
            'graphql': {'demand': 'medium', 'growth': 0.10, 'avg_salary': 98000},
            'jest': {'demand': 'high', 'growth': 0.08, 'avg_salary': 95000},
        }
        
        # Filter if specific skills requested
        if skills:
            trends = {k: v for k, v in trends.items() if k.lower() in [s.lower() for s in skills]}
        
        # Cache for 24 hours
        self._trend_cache = trends
        self._cache_expiry = datetime.now() + timedelta(hours=24)
        
        return trends
    
    def get_emerging_skills(self) -> List[Dict]:
        """Get list of emerging skills to watch"""
        return [
            {'skill': 'AI/ML Integration', 'growth': 0.50, 'relevance': 'high'},
            {'skill': 'Web3/Blockchain', 'growth': 0.20, 'relevance': 'medium'},
            {'skill': 'Edge Computing', 'growth': 0.15, 'relevance': 'medium'},
            {'skill': 'WebAssembly', 'growth': 0.25, 'relevance': 'low'},
        ]


# Global adaptive learning instance
_adaptive_agent: Optional[AdaptiveLearningAgent] = None


def get_adaptive_agent() -> AdaptiveLearningAgent:
    """Get the global adaptive learning agent"""
    global _adaptive_agent
    if _adaptive_agent is None:
        _adaptive_agent = AdaptiveLearningAgent()
    return _adaptive_agent
