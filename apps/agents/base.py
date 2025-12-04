"""
Base Agent Class - Foundation for all agents in the system
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import time
import uuid

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class AgentResult:
    """Standardized result from agent execution"""
    agent_id: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    confidence: float = 1.0
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'agent_id': self.agent_id,
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'confidence': self.confidence,
            'execution_time': self.execution_time,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class AgentContext:
    """Context passed between agents"""
    job_id: int
    user_id: int
    input_data: Dict[str, Any] = field(default_factory=dict)
    previous_results: Dict[str, AgentResult] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_result(self, agent_id: str) -> Optional[AgentResult]:
        return self.previous_results.get(agent_id)
    
    def add_result(self, result: AgentResult):
        self.previous_results[result.agent_id] = result


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the FairFound system.
    
    All agents must implement:
    - execute(): Main execution logic
    - get_capabilities(): List of agent capabilities
    """
    
    def __init__(self, agent_id: str = None):
        self.agent_id = agent_id or self.__class__.__name__
        self.status = AgentStatus.IDLE
        self.last_execution: Optional[datetime] = None
        self.execution_count = 0
        self._logger = logging.getLogger(f"agent.{self.agent_id}")
    
    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """Return list of capabilities this agent provides"""
        pass
    
    @property
    def dependencies(self) -> List[str]:
        """Return list of agent IDs this agent depends on"""
        return []
    
    @abstractmethod
    def _execute(self, context: AgentContext) -> AgentResult:
        """Internal execution logic - must be implemented by subclasses"""
        pass
    
    def execute(self, context: AgentContext) -> AgentResult:
        """
        Execute the agent with timing, logging, and error handling.
        Wraps _execute() with common functionality.
        """
        self.status = AgentStatus.RUNNING
        self._logger.info(f"Starting execution for job {context.job_id}")
        
        start_time = time.time()
        
        try:
            # Check dependencies
            missing_deps = self._check_dependencies(context)
            if missing_deps:
                raise ValueError(f"Missing dependencies: {missing_deps}")
            
            # Execute agent logic
            result = self._execute(context)
            result.execution_time = time.time() - start_time
            
            self.status = AgentStatus.SUCCESS
            self.last_execution = datetime.now()
            self.execution_count += 1
            
            self._logger.info(
                f"Completed in {result.execution_time:.3f}s "
                f"(confidence: {result.confidence:.2f})"
            )
            
            return result
            
        except Exception as e:
            self.status = AgentStatus.FAILED
            execution_time = time.time() - start_time
            
            self._logger.error(f"Failed after {execution_time:.3f}s: {str(e)}")
            
            return AgentResult(
                agent_id=self.agent_id,
                success=False,
                error=str(e),
                execution_time=execution_time,
                confidence=0.0
            )
    
    def _check_dependencies(self, context: AgentContext) -> List[str]:
        """Check if all dependencies have been executed"""
        missing = []
        for dep_id in self.dependencies:
            if dep_id not in context.previous_results:
                missing.append(dep_id)
            elif not context.previous_results[dep_id].success:
                missing.append(f"{dep_id} (failed)")
        return missing
    
    def validate_input(self, context: AgentContext) -> bool:
        """Validate input data - can be overridden by subclasses"""
        return True
    
    def get_fallback_result(self, context: AgentContext) -> AgentResult:
        """Return fallback result when execution fails"""
        return AgentResult(
            agent_id=self.agent_id,
            success=False,
            error="No fallback implemented",
            confidence=0.0
        )
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.agent_id}, status={self.status.value})>"


class ScoringAgent(BaseAgent):
    """Base class for scoring agents with common scoring functionality"""
    
    @property
    def capabilities(self) -> List[str]:
        return ['scoring']
    
    def normalize_score(self, score: float, min_val: float = 0.0, 
                       max_val: float = 1.0) -> float:
        """Normalize score to 0-1 range"""
        return max(min_val, min(max_val, score))
    
    def get_level_from_score(self, score: float, rubric: Dict) -> str:
        """Determine level from score using rubric"""
        for level, config in rubric.items():
            if score >= config['min']:
                return level
        return list(rubric.keys())[-1]


class CollectorAgent(BaseAgent):
    """Base class for data collection agents"""
    
    @property
    def capabilities(self) -> List[str]:
        return ['data_collection']
    
    def validate_url(self, url: str) -> bool:
        """Basic URL validation"""
        if not url:
            return False
        return url.startswith(('http://', 'https://'))
    
    def sanitize_data(self, data: Dict) -> Dict:
        """Remove sensitive or unnecessary data"""
        sensitive_keys = ['password', 'token', 'secret', 'key']
        return {
            k: v for k, v in data.items() 
            if not any(s in k.lower() for s in sensitive_keys)
        }


class EvaluationAgent(BaseAgent):
    """Base class for evaluation/judgment agents"""
    
    @property
    def capabilities(self) -> List[str]:
        return ['evaluation', 'judgment']
    
    def calculate_confidence(self, factors: Dict[str, float]) -> float:
        """Calculate overall confidence from multiple factors"""
        if not factors:
            return 0.5
        return sum(factors.values()) / len(factors)
