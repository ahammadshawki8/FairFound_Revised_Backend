"""
Agent Orchestrator - Central coordinator for agent pipeline execution
"""
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import time
import traceback

from .base import BaseAgent, AgentContext, AgentResult, AgentStatus
from .registry import AgentRegistry
from .events import EventBus, AgentEvent

logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some agents failed


@dataclass
class PipelineResult:
    """Result of a complete pipeline execution"""
    job_id: int
    status: PipelineStatus
    results: Dict[str, AgentResult] = field(default_factory=dict)
    total_time: float = 0.0
    agents_executed: int = 0
    agents_succeeded: int = 0
    agents_failed: int = 0
    errors: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            'job_id': self.job_id,
            'status': self.status.value,
            'results': {k: v.to_dict() for k, v in self.results.items()},
            'total_time': self.total_time,
            'agents_executed': self.agents_executed,
            'agents_succeeded': self.agents_succeeded,
            'agents_failed': self.agents_failed,
            'errors': self.errors,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class RetryPolicy:
    """Retry policy for failed agents"""
    
    def __init__(self, max_retries: int = 2, delay: float = 1.0, 
                 exponential_backoff: bool = True):
        self.max_retries = max_retries
        self.delay = delay
        self.exponential_backoff = exponential_backoff
    
    def get_delay(self, attempt: int) -> float:
        if self.exponential_backoff:
            return self.delay * (2 ** attempt)
        return self.delay


class AgentOrchestrator:
    """
    Central coordinator for agent pipeline execution.
    
    Features:
    - Dependency-aware execution ordering
    - Retry logic for failed agents
    - Event emission for monitoring
    - Fallback handling
    - Parallel execution support (future)
    """
    
    def __init__(self, retry_policy: RetryPolicy = None):
        self.retry_policy = retry_policy or RetryPolicy()
        self.event_bus = EventBus()
        self._hooks: Dict[str, List[Callable]] = {
            'before_pipeline': [],
            'after_pipeline': [],
            'before_agent': [],
            'after_agent': [],
            'on_error': []
        }
    
    def register_hook(self, hook_type: str, callback: Callable):
        """Register a hook callback"""
        if hook_type in self._hooks:
            self._hooks[hook_type].append(callback)
    
    def _run_hooks(self, hook_type: str, **kwargs):
        """Run all hooks of a given type"""
        for callback in self._hooks.get(hook_type, []):
            try:
                callback(**kwargs)
            except Exception as e:
                logger.warning(f"Hook {hook_type} failed: {e}")
    
    def execute_pipeline(self, job_id: int, user_id: int, 
                        input_data: Dict[str, Any],
                        agent_ids: List[str] = None) -> PipelineResult:
        """
        Execute the agent pipeline for a job.
        
        Args:
            job_id: The job ID being processed
            user_id: The user ID
            input_data: Input data for the pipeline
            agent_ids: Specific agents to run (None = all enabled)
        
        Returns:
            PipelineResult with all agent results
        """
        start_time = time.time()
        started_at = datetime.now()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"  PIPELINE EXECUTION - Job {job_id}")
        logger.info(f"{'='*60}")
        
        # Initialize context
        context = AgentContext(
            job_id=job_id,
            user_id=user_id,
            input_data=input_data
        )
        
        # Get execution order
        if agent_ids is None:
            agent_ids = list(AgentRegistry.get_enabled().keys())
        
        execution_order = AgentRegistry.get_execution_order(agent_ids)
        
        logger.info(f"Execution order: {execution_order}")
        
        # Run before_pipeline hooks
        self._run_hooks('before_pipeline', job_id=job_id, context=context)
        
        # Emit pipeline started event
        self.event_bus.publish(AgentEvent(
            event_type='pipeline_started',
            agent_id='orchestrator',
            job_id=job_id,
            data={'agent_count': len(execution_order)}
        ))
        
        # Execute agents in order
        results: Dict[str, AgentResult] = {}
        errors: List[str] = []
        agents_succeeded = 0
        agents_failed = 0
        
        for agent_id in execution_order:
            logger.info(f"\n[AGENT] Executing: {agent_id}")
            
            # Run before_agent hooks
            self._run_hooks('before_agent', agent_id=agent_id, context=context)
            
            # Execute with retry
            result = self._execute_with_retry(agent_id, context)
            
            # Store result
            results[agent_id] = result
            context.add_result(result)
            
            # Update registry stats
            AgentRegistry.update_stats(agent_id, result.success, result.execution_time)
            
            # Run after_agent hooks
            self._run_hooks('after_agent', agent_id=agent_id, result=result)
            
            # Emit agent completed event
            self.event_bus.publish(AgentEvent(
                event_type='agent_completed' if result.success else 'agent_failed',
                agent_id=agent_id,
                job_id=job_id,
                data=result.to_dict()
            ))
            
            if result.success:
                agents_succeeded += 1
                logger.info(f"  ✅ {agent_id} completed (confidence: {result.confidence:.2f})")
            else:
                agents_failed += 1
                errors.append(f"{agent_id}: {result.error}")
                logger.error(f"  ❌ {agent_id} failed: {result.error}")
                
                # Run on_error hooks
                self._run_hooks('on_error', agent_id=agent_id, error=result.error)
        
        # Determine final status
        if agents_failed == 0:
            status = PipelineStatus.COMPLETED
        elif agents_succeeded == 0:
            status = PipelineStatus.FAILED
        else:
            status = PipelineStatus.PARTIAL
        
        total_time = time.time() - start_time
        completed_at = datetime.now()
        
        pipeline_result = PipelineResult(
            job_id=job_id,
            status=status,
            results=results,
            total_time=total_time,
            agents_executed=len(execution_order),
            agents_succeeded=agents_succeeded,
            agents_failed=agents_failed,
            errors=errors,
            started_at=started_at,
            completed_at=completed_at
        )
        
        # Run after_pipeline hooks
        self._run_hooks('after_pipeline', result=pipeline_result)
        
        # Emit pipeline completed event
        self.event_bus.publish(AgentEvent(
            event_type='pipeline_completed',
            agent_id='orchestrator',
            job_id=job_id,
            data={
                'status': status.value,
                'total_time': total_time,
                'succeeded': agents_succeeded,
                'failed': agents_failed
            }
        ))
        
        logger.info(f"\n{'='*60}")
        logger.info(f"  PIPELINE COMPLETE - {status.value}")
        logger.info(f"  Time: {total_time:.2f}s | Success: {agents_succeeded}/{len(execution_order)}")
        logger.info(f"{'='*60}\n")
        
        return pipeline_result
    
    def _execute_with_retry(self, agent_id: str, context: AgentContext) -> AgentResult:
        """Execute an agent with retry logic"""
        agent = AgentRegistry.get_agent(agent_id)
        
        if agent is None:
            return AgentResult(
                agent_id=agent_id,
                success=False,
                error=f"Agent {agent_id} not found or disabled",
                confidence=0.0
            )
        
        last_error = None
        
        for attempt in range(self.retry_policy.max_retries + 1):
            try:
                result = agent.execute(context)
                
                if result.success:
                    return result
                
                last_error = result.error
                
                # Don't retry if it's a validation error
                if "validation" in str(result.error).lower():
                    break
                
            except Exception as e:
                last_error = str(e)
                logger.warning(f"  Attempt {attempt + 1} failed: {e}")
            
            # Wait before retry
            if attempt < self.retry_policy.max_retries:
                delay = self.retry_policy.get_delay(attempt)
                logger.info(f"  Retrying in {delay:.1f}s...")
                time.sleep(delay)
        
        # All retries failed, try fallback
        logger.warning(f"  All retries failed, attempting fallback...")
        
        try:
            fallback_result = agent.get_fallback_result(context)
            if fallback_result.success:
                fallback_result.metadata['used_fallback'] = True
                return fallback_result
        except Exception as e:
            logger.error(f"  Fallback also failed: {e}")
        
        return AgentResult(
            agent_id=agent_id,
            success=False,
            error=last_error or "Unknown error after retries",
            confidence=0.0,
            metadata={'retries_attempted': self.retry_policy.max_retries}
        )
    
    def execute_single_agent(self, agent_id: str, context: AgentContext) -> AgentResult:
        """Execute a single agent (useful for testing or manual runs)"""
        return self._execute_with_retry(agent_id, context)
    
    def get_pipeline_status(self, job_id: int) -> Optional[Dict]:
        """Get status of a running or completed pipeline"""
        # This would typically query a database or cache
        # For now, return None (not implemented)
        return None


class PipelineBuilder:
    """
    Builder pattern for constructing custom pipelines.
    
    Usage:
        pipeline = (PipelineBuilder()
            .add_agent('form_processor')
            .add_agent('github_collector')
            .add_agent('skill_scorer', depends_on=['form_processor'])
            .build())
    """
    
    def __init__(self):
        self._agents: List[Dict] = []
        self._retry_policy = RetryPolicy()
    
    def add_agent(self, agent_id: str, depends_on: List[str] = None) -> 'PipelineBuilder':
        """Add an agent to the pipeline"""
        self._agents.append({
            'agent_id': agent_id,
            'depends_on': depends_on or []
        })
        return self
    
    def with_retry_policy(self, max_retries: int = 2, delay: float = 1.0) -> 'PipelineBuilder':
        """Set retry policy"""
        self._retry_policy = RetryPolicy(max_retries, delay)
        return self
    
    def build(self) -> AgentOrchestrator:
        """Build the orchestrator with configured pipeline"""
        orchestrator = AgentOrchestrator(self._retry_policy)
        # Store pipeline configuration
        orchestrator._pipeline_config = self._agents
        return orchestrator


# Global orchestrator instance
_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """Get or create the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
