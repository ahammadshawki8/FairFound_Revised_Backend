"""
Multi-Agent Collaboration - Consensus and conflict resolution between agents
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import statistics
import logging

logger = logging.getLogger(__name__)


class ConsensusMethod(Enum):
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_AVERAGE = "weighted_average"
    HIGHEST_CONFIDENCE = "highest_confidence"
    DEBATE = "debate"


@dataclass
class AgentOpinion:
    """An agent's opinion/evaluation"""
    agent_id: str
    score: float
    confidence: float
    reasoning: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'agent_id': self.agent_id,
            'score': self.score,
            'confidence': self.confidence,
            'reasoning': self.reasoning,
            'strengths': self.strengths,
            'weaknesses': self.weaknesses,
            'recommendations': self.recommendations,
            'metadata': self.metadata
        }


@dataclass
class ConsensusResult:
    """Result of consensus building"""
    final_score: float
    final_confidence: float
    method_used: ConsensusMethod
    agreement_level: float  # 0-1, how much agents agreed
    participating_agents: List[str]
    individual_opinions: List[AgentOpinion]
    merged_strengths: List[str]
    merged_weaknesses: List[str]
    merged_recommendations: List[str]
    conflicts_resolved: List[Dict]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'final_score': self.final_score,
            'final_confidence': self.final_confidence,
            'method_used': self.method_used.value,
            'agreement_level': self.agreement_level,
            'participating_agents': self.participating_agents,
            'individual_opinions': [o.to_dict() for o in self.individual_opinions],
            'merged_strengths': self.merged_strengths,
            'merged_weaknesses': self.merged_weaknesses,
            'merged_recommendations': self.merged_recommendations,
            'conflicts_resolved': self.conflicts_resolved,
            'timestamp': self.timestamp.isoformat()
        }


class ConsensusAgent:
    """
    Mediates when multiple agents need to reach consensus.
    
    Features:
    - Multiple consensus methods
    - Conflict detection and resolution
    - Weighted voting based on agent accuracy
    - Explanation of disagreements
    """
    
    def __init__(self, default_method: ConsensusMethod = ConsensusMethod.WEIGHTED_AVERAGE):
        self.default_method = default_method
        self._agent_weights: Dict[str, float] = {}
    
    def set_agent_weight(self, agent_id: str, weight: float):
        """Set the weight for an agent (based on historical accuracy)"""
        self._agent_weights[agent_id] = max(0.1, min(2.0, weight))
    
    def build_consensus(self, opinions: List[AgentOpinion],
                       method: ConsensusMethod = None) -> ConsensusResult:
        """
        Build consensus from multiple agent opinions.
        
        Args:
            opinions: List of agent opinions
            method: Consensus method to use
        
        Returns:
            ConsensusResult with merged evaluation
        """
        if not opinions:
            raise ValueError("No opinions provided")
        
        method = method or self.default_method
        
        logger.info(f"Building consensus from {len(opinions)} agents using {method.value}")
        
        # Calculate agreement level
        scores = [o.score for o in opinions]
        agreement_level = self._calculate_agreement(scores)
        
        logger.info(f"Agreement level: {agreement_level:.2f}")
        
        # If high disagreement, try to resolve conflicts
        conflicts_resolved = []
        if agreement_level < 0.7:
            conflicts_resolved = self._identify_conflicts(opinions)
            logger.warning(f"Low agreement detected, {len(conflicts_resolved)} conflicts identified")
        
        # Calculate final score based on method
        if method == ConsensusMethod.MAJORITY_VOTE:
            final_score, final_confidence = self._majority_vote(opinions)
        elif method == ConsensusMethod.WEIGHTED_AVERAGE:
            final_score, final_confidence = self._weighted_average(opinions)
        elif method == ConsensusMethod.HIGHEST_CONFIDENCE:
            final_score, final_confidence = self._highest_confidence(opinions)
        elif method == ConsensusMethod.DEBATE:
            final_score, final_confidence = self._debate_method(opinions)
        else:
            final_score, final_confidence = self._weighted_average(opinions)
        
        # Merge qualitative assessments
        merged_strengths = self._merge_lists([o.strengths for o in opinions])
        merged_weaknesses = self._merge_lists([o.weaknesses for o in opinions])
        merged_recommendations = self._merge_lists([o.recommendations for o in opinions])
        
        return ConsensusResult(
            final_score=final_score,
            final_confidence=final_confidence,
            method_used=method,
            agreement_level=agreement_level,
            participating_agents=[o.agent_id for o in opinions],
            individual_opinions=opinions,
            merged_strengths=merged_strengths[:5],
            merged_weaknesses=merged_weaknesses[:5],
            merged_recommendations=merged_recommendations[:5],
            conflicts_resolved=conflicts_resolved
        )
    
    def _calculate_agreement(self, scores: List[float]) -> float:
        """Calculate how much agents agree (0-1)"""
        if len(scores) < 2:
            return 1.0
        
        # Use coefficient of variation (lower = more agreement)
        mean = statistics.mean(scores)
        if mean == 0:
            return 1.0
        
        std_dev = statistics.stdev(scores)
        cv = std_dev / mean
        
        # Convert to agreement score (0-1)
        agreement = max(0, 1 - cv)
        return agreement
    
    def _identify_conflicts(self, opinions: List[AgentOpinion]) -> List[Dict]:
        """Identify specific conflicts between agents"""
        conflicts = []
        
        # Check score conflicts
        scores = [(o.agent_id, o.score) for o in opinions]
        scores.sort(key=lambda x: x[1])
        
        if len(scores) >= 2:
            lowest = scores[0]
            highest = scores[-1]
            
            if highest[1] - lowest[1] > 0.2:
                conflicts.append({
                    'type': 'score_disagreement',
                    'agents': [lowest[0], highest[0]],
                    'values': [lowest[1], highest[1]],
                    'difference': highest[1] - lowest[1],
                    'resolution': 'weighted_average'
                })
        
        # Check for contradictory strengths/weaknesses
        all_strengths = set()
        all_weaknesses = set()
        
        for o in opinions:
            all_strengths.update(s.lower() for s in o.strengths)
            all_weaknesses.update(w.lower() for w in o.weaknesses)
        
        contradictions = all_strengths & all_weaknesses
        if contradictions:
            conflicts.append({
                'type': 'strength_weakness_contradiction',
                'items': list(contradictions),
                'resolution': 'majority_classification'
            })
        
        return conflicts
    
    def _majority_vote(self, opinions: List[AgentOpinion]) -> Tuple[float, float]:
        """Use majority vote for consensus"""
        # Bucket scores into tiers
        tiers = {'low': 0, 'medium': 0, 'high': 0}
        
        for o in opinions:
            if o.score < 0.4:
                tiers['low'] += 1
            elif o.score < 0.7:
                tiers['medium'] += 1
            else:
                tiers['high'] += 1
        
        # Get majority tier
        majority_tier = max(tiers, key=tiers.get)
        
        # Calculate score based on tier
        tier_scores = {'low': 0.3, 'medium': 0.55, 'high': 0.8}
        final_score = tier_scores[majority_tier]
        
        # Confidence based on majority strength
        majority_count = tiers[majority_tier]
        confidence = majority_count / len(opinions)
        
        return final_score, confidence
    
    def _weighted_average(self, opinions: List[AgentOpinion]) -> Tuple[float, float]:
        """Use weighted average based on confidence and agent weights"""
        total_weight = 0
        weighted_sum = 0
        confidence_sum = 0
        
        for o in opinions:
            # Get agent weight (default 1.0)
            agent_weight = self._agent_weights.get(o.agent_id, 1.0)
            
            # Combined weight = agent_weight * confidence
            weight = agent_weight * o.confidence
            
            weighted_sum += o.score * weight
            confidence_sum += o.confidence * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.5, 0.5
        
        final_score = weighted_sum / total_weight
        final_confidence = confidence_sum / total_weight
        
        return final_score, final_confidence
    
    def _highest_confidence(self, opinions: List[AgentOpinion]) -> Tuple[float, float]:
        """Use the opinion with highest confidence"""
        best = max(opinions, key=lambda o: o.confidence)
        return best.score, best.confidence
    
    def _debate_method(self, opinions: List[AgentOpinion]) -> Tuple[float, float]:
        """
        Simulate a debate between agents.
        Each agent can critique others and refine their position.
        """
        # Start with weighted average
        initial_score, _ = self._weighted_average(opinions)
        
        # Identify outliers
        scores = [o.score for o in opinions]
        mean = statistics.mean(scores)
        std = statistics.stdev(scores) if len(scores) > 1 else 0
        
        # Agents far from mean get lower weight in final calculation
        adjusted_opinions = []
        for o in opinions:
            distance = abs(o.score - mean)
            if std > 0:
                z_score = distance / std
                # Reduce confidence for outliers
                adjusted_confidence = o.confidence * max(0.5, 1 - z_score * 0.2)
            else:
                adjusted_confidence = o.confidence
            
            adjusted_opinions.append(AgentOpinion(
                agent_id=o.agent_id,
                score=o.score,
                confidence=adjusted_confidence,
                reasoning=o.reasoning,
                strengths=o.strengths,
                weaknesses=o.weaknesses,
                recommendations=o.recommendations
            ))
        
        # Recalculate with adjusted confidences
        return self._weighted_average(adjusted_opinions)
    
    def _merge_lists(self, lists: List[List[str]], max_items: int = 10) -> List[str]:
        """Merge multiple lists, prioritizing items that appear more often"""
        item_counts: Dict[str, int] = {}
        
        for lst in lists:
            for item in lst:
                normalized = item.strip().lower()
                if normalized:
                    item_counts[normalized] = item_counts.get(normalized, 0) + 1
        
        # Sort by frequency
        sorted_items = sorted(item_counts.items(), key=lambda x: -x[1])
        
        # Return original casing for most common items
        result = []
        seen = set()
        
        for normalized, _ in sorted_items[:max_items]:
            for lst in lists:
                for item in lst:
                    if item.strip().lower() == normalized and normalized not in seen:
                        result.append(item)
                        seen.add(normalized)
                        break
                if normalized in seen:
                    break
        
        return result


class DebateAgent:
    """
    Enables structured debate between agents to refine evaluations.
    """
    
    def __init__(self, max_rounds: int = 3):
        self.max_rounds = max_rounds
    
    def conduct_debate(self, initial_evaluation: Dict,
                      critic_fn: callable,
                      refiner_fn: callable) -> Dict:
        """
        Conduct a multi-round debate to refine an evaluation.
        
        Args:
            initial_evaluation: Starting evaluation
            critic_fn: Function that critiques an evaluation
            refiner_fn: Function that refines based on critique
        
        Returns:
            Refined evaluation
        """
        current_eval = initial_evaluation.copy()
        debate_history = []
        
        for round_num in range(self.max_rounds):
            logger.info(f"Debate round {round_num + 1}/{self.max_rounds}")
            
            # Critic phase
            critique = critic_fn(current_eval)
            
            if not critique.get('issues'):
                logger.info("No issues found, ending debate")
                break
            
            debate_history.append({
                'round': round_num + 1,
                'critique': critique
            })
            
            # Refiner phase
            refined = refiner_fn(current_eval, critique)
            
            # Check if refinement improved confidence
            if refined.get('confidence', 0) <= current_eval.get('confidence', 0):
                logger.info("No improvement, ending debate")
                break
            
            current_eval = refined
            debate_history.append({
                'round': round_num + 1,
                'refinement': refined
            })
        
        current_eval['debate_history'] = debate_history
        current_eval['debate_rounds'] = len(debate_history) // 2
        
        return current_eval


class ConflictResolver:
    """
    Resolves specific conflicts between agent opinions.
    """
    
    def resolve_score_conflict(self, opinions: List[AgentOpinion],
                               context: Dict = None) -> float:
        """
        Resolve conflicting scores using context-aware logic.
        """
        if not opinions:
            return 0.5
        
        # If we have context about data quality, weight accordingly
        if context:
            data_completeness = context.get('data_completeness', 1.0)
            
            # With incomplete data, trust more conservative estimates
            if data_completeness < 0.7:
                # Weight lower scores more heavily
                scores = sorted([o.score for o in opinions])
                return statistics.mean(scores[:len(scores)//2 + 1])
        
        # Default: weighted average by confidence
        total_weight = sum(o.confidence for o in opinions)
        if total_weight == 0:
            return statistics.mean([o.score for o in opinions])
        
        return sum(o.score * o.confidence for o in opinions) / total_weight
    
    def resolve_qualitative_conflict(self, items: List[Tuple[str, str]]) -> str:
        """
        Resolve conflict about whether something is a strength or weakness.
        
        Args:
            items: List of (item, classification) tuples
        
        Returns:
            Final classification ('strength', 'weakness', or 'neutral')
        """
        strength_count = sum(1 for _, c in items if c == 'strength')
        weakness_count = sum(1 for _, c in items if c == 'weakness')
        
        if strength_count > weakness_count:
            return 'strength'
        elif weakness_count > strength_count:
            return 'weakness'
        else:
            return 'neutral'
