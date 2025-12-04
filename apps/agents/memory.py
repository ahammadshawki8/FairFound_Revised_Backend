"""
Agent Memory - Persistent memory and learning system for agents
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import json
import logging
import hashlib

from django.db import models
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single memory entry"""
    agent_id: str
    context_hash: str
    context: Dict[str, Any]
    decision: Dict[str, Any]
    outcome: Optional[str] = None
    feedback: Optional[Dict] = None
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'agent_id': self.agent_id,
            'context_hash': self.context_hash,
            'context': self.context,
            'decision': self.decision,
            'outcome': self.outcome,
            'feedback': self.feedback,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat()
        }


class AgentMemory:
    """
    Persistent memory system for agents to learn from past interactions.
    
    Features:
    - Store agent decisions and outcomes
    - Retrieve similar past cases
    - Track agent accuracy over time
    - Learn from human feedback
    - Adjust weights based on outcomes
    """
    
    def __init__(self):
        self._short_term: Dict[str, List[MemoryEntry]] = defaultdict(list)
        self._max_short_term = 100
    
    def _hash_context(self, context: Dict) -> str:
        """Create a hash of the context for similarity matching"""
        # Normalize and hash relevant context fields
        relevant_fields = ['skills', 'experience_years', 'tier', 'percentile']
        normalized = {k: context.get(k) for k in relevant_fields if k in context}
        context_str = json.dumps(normalized, sort_keys=True)
        return hashlib.md5(context_str.encode()).hexdigest()[:16]
    
    def store_interaction(self, agent_id: str, context: Dict, 
                         decision: Dict, confidence: float = 0.0) -> str:
        """
        Store an agent interaction in memory.
        
        Args:
            agent_id: The agent that made the decision
            context: The context/input data
            decision: The decision/output made
            confidence: Confidence in the decision
        
        Returns:
            Memory entry ID
        """
        from .models import AgentInteraction
        
        context_hash = self._hash_context(context)
        
        # Store in database
        try:
            interaction = AgentInteraction.objects.create(
                agent_id=agent_id,
                context_hash=context_hash,
                context=context,
                decision=decision,
                confidence=confidence
            )
            entry_id = str(interaction.id)
        except Exception as e:
            logger.warning(f"Failed to store in DB: {e}")
            entry_id = f"{agent_id}_{context_hash}_{datetime.now().timestamp()}"
        
        # Also store in short-term memory
        entry = MemoryEntry(
            agent_id=agent_id,
            context_hash=context_hash,
            context=context,
            decision=decision,
            confidence=confidence
        )
        
        self._short_term[agent_id].append(entry)
        if len(self._short_term[agent_id]) > self._max_short_term:
            self._short_term[agent_id] = self._short_term[agent_id][-self._max_short_term:]
        
        logger.debug(f"Stored interaction for {agent_id}: {entry_id}")
        
        return entry_id
    
    def record_outcome(self, entry_id: str, outcome: str, feedback: Dict = None):
        """
        Record the outcome of a previous decision.
        
        Args:
            entry_id: The memory entry ID
            outcome: The outcome (e.g., 'approved', 'rejected', 'successful')
            feedback: Additional feedback data
        """
        from .models import AgentInteraction
        
        try:
            interaction = AgentInteraction.objects.get(id=int(entry_id))
            interaction.outcome = outcome
            interaction.feedback = feedback or {}
            interaction.outcome_recorded_at = timezone.now()
            interaction.save()
            
            logger.info(f"Recorded outcome for {entry_id}: {outcome}")
        except (AgentInteraction.DoesNotExist, ValueError):
            logger.warning(f"Could not find interaction {entry_id}")
    
    def retrieve_similar_cases(self, context: Dict, agent_id: str = None,
                               limit: int = 5) -> List[Dict]:
        """
        Find similar past cases for reference.
        
        Args:
            context: Current context to match against
            agent_id: Filter by specific agent
            limit: Maximum number of results
        
        Returns:
            List of similar past interactions
        """
        from .models import AgentInteraction
        
        context_hash = self._hash_context(context)
        
        # Query database for similar contexts
        queryset = AgentInteraction.objects.all()
        
        if agent_id:
            queryset = queryset.filter(agent_id=agent_id)
        
        # First try exact hash match
        exact_matches = queryset.filter(context_hash=context_hash)[:limit]
        
        if exact_matches.exists():
            return [
                {
                    'context': m.context,
                    'decision': m.decision,
                    'outcome': m.outcome,
                    'confidence': m.confidence,
                    'similarity': 1.0
                }
                for m in exact_matches
            ]
        
        # Fall back to recent interactions with outcomes
        recent = queryset.filter(
            outcome__isnull=False
        ).order_by('-created_at')[:limit * 2]
        
        # Calculate similarity scores
        results = []
        for interaction in recent:
            similarity = self._calculate_similarity(context, interaction.context)
            if similarity > 0.3:  # Minimum similarity threshold
                results.append({
                    'context': interaction.context,
                    'decision': interaction.decision,
                    'outcome': interaction.outcome,
                    'confidence': interaction.confidence,
                    'similarity': similarity
                })
        
        # Sort by similarity and return top results
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:limit]
    
    def _calculate_similarity(self, context1: Dict, context2: Dict) -> float:
        """Calculate similarity between two contexts"""
        if not context1 or not context2:
            return 0.0
        
        score = 0.0
        comparisons = 0
        
        # Compare skills overlap
        skills1 = set(s.lower() for s in context1.get('skills', []))
        skills2 = set(s.lower() for s in context2.get('skills', []))
        if skills1 and skills2:
            overlap = len(skills1 & skills2) / max(len(skills1 | skills2), 1)
            score += overlap
            comparisons += 1
        
        # Compare experience years
        exp1 = context1.get('experience_years', 0)
        exp2 = context2.get('experience_years', 0)
        if exp1 is not None and exp2 is not None:
            exp_diff = abs(exp1 - exp2)
            exp_score = max(0, 1 - exp_diff / 5)  # 5 years = 0 similarity
            score += exp_score
            comparisons += 1
        
        # Compare tier
        if context1.get('tier') == context2.get('tier'):
            score += 1.0
            comparisons += 1
        elif context1.get('tier') and context2.get('tier'):
            comparisons += 1
        
        return score / max(comparisons, 1)
    
    def get_agent_accuracy(self, agent_id: str, 
                          time_window: timedelta = None) -> Dict[str, float]:
        """
        Calculate agent accuracy from human reviews.
        
        Args:
            agent_id: The agent to check
            time_window: Optional time window to consider
        
        Returns:
            Dictionary with accuracy metrics
        """
        from .models import AgentInteraction, HumanReview
        
        queryset = AgentInteraction.objects.filter(
            agent_id=agent_id,
            outcome__isnull=False
        )
        
        if time_window:
            cutoff = timezone.now() - time_window
            queryset = queryset.filter(created_at__gte=cutoff)
        
        total = queryset.count()
        if total == 0:
            return {
                'accuracy': 0.0,
                'total_reviewed': 0,
                'approved': 0,
                'rejected': 0,
                'modified': 0
            }
        
        approved = queryset.filter(outcome='approved').count()
        rejected = queryset.filter(outcome='rejected').count()
        modified = queryset.filter(outcome='modified').count()
        
        # Calculate accuracy (approved + modified count as partially correct)
        accuracy = (approved + modified * 0.5) / total
        
        return {
            'accuracy': accuracy,
            'total_reviewed': total,
            'approved': approved,
            'rejected': rejected,
            'modified': modified,
            'approval_rate': approved / total if total > 0 else 0,
            'rejection_rate': rejected / total if total > 0 else 0
        }
    
    def get_learning_insights(self, agent_id: str) -> Dict[str, Any]:
        """
        Get insights about what the agent should learn from feedback.
        
        Returns patterns in rejected/modified decisions.
        """
        from .models import AgentInteraction
        
        # Get rejected and modified interactions
        problematic = AgentInteraction.objects.filter(
            agent_id=agent_id,
            outcome__in=['rejected', 'modified']
        ).order_by('-created_at')[:50]
        
        if not problematic.exists():
            return {'patterns': [], 'recommendations': []}
        
        # Analyze patterns
        patterns = defaultdict(int)
        feedback_themes = defaultdict(list)
        
        for interaction in problematic:
            context = interaction.context or {}
            feedback = interaction.feedback or {}
            
            # Track context patterns
            tier = context.get('tier', 'unknown')
            patterns[f'tier_{tier}'] += 1
            
            exp = context.get('experience_years', 0)
            if exp < 1:
                patterns['low_experience'] += 1
            
            # Track feedback themes
            if feedback.get('disagreement_reasons'):
                for reason in feedback['disagreement_reasons']:
                    feedback_themes['disagreements'].append(reason)
        
        # Generate recommendations
        recommendations = []
        
        if patterns.get('low_experience', 0) > 5:
            recommendations.append(
                "Consider adjusting evaluation criteria for candidates with <1 year experience"
            )
        
        if patterns.get('tier_Early Stage', 0) > 5:
            recommendations.append(
                "Early Stage tier evaluations are frequently modified - review rubrics"
            )
        
        return {
            'patterns': dict(patterns),
            'feedback_themes': dict(feedback_themes),
            'recommendations': recommendations,
            'sample_size': problematic.count()
        }
    
    def clear_old_memories(self, days: int = 90):
        """Clear memories older than specified days"""
        from .models import AgentInteraction
        
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = AgentInteraction.objects.filter(
            created_at__lt=cutoff
        ).delete()
        
        logger.info(f"Cleared {deleted} old memory entries")
        return deleted


class WeightLearner:
    """
    Learns and adjusts scoring weights based on feedback and outcomes.
    """
    
    def __init__(self):
        self.memory = AgentMemory()
    
    def calculate_weight_adjustments(self, agent_id: str) -> Dict[str, float]:
        """
        Calculate suggested weight adjustments based on feedback patterns.
        
        Returns:
            Dictionary of weight adjustments (positive = increase, negative = decrease)
        """
        from .models import AgentInteraction
        
        # Get interactions with feedback
        interactions = AgentInteraction.objects.filter(
            agent_id=agent_id,
            feedback__isnull=False,
            outcome__in=['approved', 'rejected', 'modified']
        ).order_by('-created_at')[:100]
        
        if interactions.count() < 10:
            return {}  # Not enough data
        
        adjustments = defaultdict(float)
        
        for interaction in interactions:
            feedback = interaction.feedback or {}
            decision = interaction.decision or {}
            outcome = interaction.outcome
            
            # If rejected, the decision was wrong
            if outcome == 'rejected':
                # Analyze which components were likely wrong
                breakdown = decision.get('breakdown', {})
                for component, data in breakdown.items():
                    if isinstance(data, dict) and data.get('raw_score', 0) > 0.7:
                        # High score but rejected = maybe overweighted
                        adjustments[component] -= 0.02
            
            # If modified, check what was changed
            elif outcome == 'modified':
                modified_score = feedback.get('modified_score')
                original_score = decision.get('overall_score', 0)
                
                if modified_score and original_score:
                    diff = modified_score - original_score
                    # If human increased score, we were too harsh
                    # If human decreased score, we were too lenient
                    adjustments['overall_bias'] = diff * 0.1
            
            # If approved, reinforce current weights slightly
            elif outcome == 'approved':
                for component in decision.get('breakdown', {}).keys():
                    adjustments[component] += 0.005
        
        # Normalize adjustments
        max_adjustment = 0.1
        for key in adjustments:
            adjustments[key] = max(-max_adjustment, min(max_adjustment, adjustments[key]))
        
        return dict(adjustments)
    
    def apply_weight_adjustments(self, current_weights: Dict[str, float],
                                 adjustments: Dict[str, float]) -> Dict[str, float]:
        """
        Apply weight adjustments while maintaining constraints.
        
        Args:
            current_weights: Current scoring weights
            adjustments: Suggested adjustments
        
        Returns:
            New weights (normalized to sum to 1.0)
        """
        new_weights = current_weights.copy()
        
        for key, adjustment in adjustments.items():
            if key in new_weights:
                new_weights[key] = max(0.05, min(0.5, new_weights[key] + adjustment))
        
        # Normalize to sum to 1.0
        total = sum(new_weights.values())
        if total > 0:
            new_weights = {k: v / total for k, v in new_weights.items()}
        
        return new_weights


# Global memory instance
_memory: Optional[AgentMemory] = None


def get_memory() -> AgentMemory:
    """Get the global memory instance"""
    global _memory
    if _memory is None:
        _memory = AgentMemory()
    return _memory
