"""
Agent Registry - Central registration and discovery system for all agents
"""
from typing import Dict, List, Type, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

from .base import BaseAgent, AgentStatus

logger = logging.getLogger(__name__)


class AgentHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class AgentInfo:
    """Information about a registered agent"""
    agent_id: str
    agent_class: Type[BaseAgent]
    capabilities: List[str]
    dependencies: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    description: str = ""
    enabled: bool = True
    priority: int = 0  # Higher = more important
    registered_at: datetime = field(default_factory=datetime.now)
    
    # Runtime stats
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    avg_execution_time: float = 0.0
    last_execution: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions
    
    @property
    def health(self) -> AgentHealth:
        if self.total_executions == 0:
            return AgentHealth.UNKNOWN
        if self.success_rate >= 0.95:
            return AgentHealth.HEALTHY
        if self.success_rate >= 0.80:
            return AgentHealth.DEGRADED
        return AgentHealth.UNHEALTHY
    
    def update_stats(self, success: bool, execution_time: float):
        """Update execution statistics"""
        self.total_executions += 1
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
        
        # Running average of execution time
        self.avg_execution_time = (
            (self.avg_execution_time * (self.total_executions - 1) + execution_time)
            / self.total_executions
        )
        self.last_execution = datetime.now()


class AgentRegistry:
    """
    Central registry for all agents in the FairFound system.
    
    Features:
    - Agent registration with capabilities
    - Capability-based discovery
    - Health monitoring
    - Dependency tracking
    """
    
    _instance = None
    _agents: Dict[str, AgentInfo] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._agents = {}
        return cls._instance
    
    @classmethod
    def register(cls, agent_id: str = None, capabilities: List[str] = None,
                 dependencies: List[str] = None, version: str = "1.0.0",
                 description: str = "", priority: int = 0):
        """
        Decorator to register an agent class.
        
        Usage:
            @AgentRegistry.register(
                agent_id='skill_scorer',
                capabilities=['scoring', 'skills'],
                dependencies=['form_processor']
            )
            class SkillScoringAgent(BaseAgent):
                pass
        """
        def decorator(agent_class: Type[BaseAgent]):
            nonlocal agent_id, capabilities
            
            # Use class name if no ID provided
            if agent_id is None:
                agent_id_final = agent_class.__name__
            else:
                agent_id_final = agent_id
            
            # Get capabilities from class if not provided
            if capabilities is None:
                try:
                    instance = agent_class(agent_id_final)
                    capabilities = instance.capabilities
                except:
                    capabilities = []
            
            # Get dependencies from class if not provided
            deps = dependencies or []
            try:
                instance = agent_class(agent_id_final)
                deps = deps or instance.dependencies
            except:
                pass
            
            # Register the agent
            cls._agents[agent_id_final] = AgentInfo(
                agent_id=agent_id_final,
                agent_class=agent_class,
                capabilities=capabilities,
                dependencies=deps,
                version=version,
                description=description or agent_class.__doc__ or "",
                priority=priority
            )
            
            logger.info(f"Registered agent: {agent_id_final} with capabilities {capabilities}")
            
            return agent_class
        
        return decorator
    
    @classmethod
    def register_agent(cls, agent_class: Type[BaseAgent], agent_id: str = None,
                       capabilities: List[str] = None, **kwargs):
        """Programmatic agent registration (non-decorator)"""
        agent_id = agent_id or agent_class.__name__
        
        if capabilities is None:
            try:
                instance = agent_class(agent_id)
                capabilities = instance.capabilities
            except:
                capabilities = []
        
        cls._agents[agent_id] = AgentInfo(
            agent_id=agent_id,
            agent_class=agent_class,
            capabilities=capabilities,
            **kwargs
        )
        
        return agent_id
    
    @classmethod
    def unregister(cls, agent_id: str) -> bool:
        """Remove an agent from the registry"""
        if agent_id in cls._agents:
            del cls._agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
            return True
        return False
    
    @classmethod
    def get(cls, agent_id: str) -> Optional[AgentInfo]:
        """Get agent info by ID"""
        return cls._agents.get(agent_id)
    
    @classmethod
    def get_agent(cls, agent_id: str) -> Optional[BaseAgent]:
        """Get an instance of the agent"""
        info = cls._agents.get(agent_id)
        if info and info.enabled:
            return info.agent_class(agent_id)
        return None
    
    @classmethod
    def discover(cls, capability: str) -> List[str]:
        """Find all agents with a specific capability"""
        return [
            agent_id for agent_id, info in cls._agents.items()
            if capability in info.capabilities and info.enabled
        ]
    
    @classmethod
    def discover_by_capabilities(cls, capabilities: List[str], 
                                  match_all: bool = False) -> List[str]:
        """Find agents matching multiple capabilities"""
        results = []
        for agent_id, info in cls._agents.items():
            if not info.enabled:
                continue
            
            if match_all:
                if all(cap in info.capabilities for cap in capabilities):
                    results.append(agent_id)
            else:
                if any(cap in info.capabilities for cap in capabilities):
                    results.append(agent_id)
        
        return results
    
    @classmethod
    def get_all(cls) -> Dict[str, AgentInfo]:
        """Get all registered agents"""
        return cls._agents.copy()
    
    @classmethod
    def get_enabled(cls) -> Dict[str, AgentInfo]:
        """Get all enabled agents"""
        return {k: v for k, v in cls._agents.items() if v.enabled}
    
    @classmethod
    def enable(cls, agent_id: str) -> bool:
        """Enable an agent"""
        if agent_id in cls._agents:
            cls._agents[agent_id].enabled = True
            return True
        return False
    
    @classmethod
    def disable(cls, agent_id: str) -> bool:
        """Disable an agent"""
        if agent_id in cls._agents:
            cls._agents[agent_id].enabled = False
            return True
        return False
    
    @classmethod
    def get_dependencies(cls, agent_id: str) -> List[str]:
        """Get dependencies for an agent"""
        info = cls._agents.get(agent_id)
        return info.dependencies if info else []
    
    @classmethod
    def get_dependents(cls, agent_id: str) -> List[str]:
        """Get agents that depend on this agent"""
        return [
            aid for aid, info in cls._agents.items()
            if agent_id in info.dependencies
        ]
    
    @classmethod
    def get_execution_order(cls, agent_ids: List[str] = None) -> List[str]:
        """
        Get topologically sorted execution order based on dependencies.
        Returns agents in order they should be executed.
        """
        if agent_ids is None:
            agent_ids = list(cls._agents.keys())
        
        # Build dependency graph
        graph = {aid: cls._agents[aid].dependencies for aid in agent_ids if aid in cls._agents}
        
        # Topological sort using Kahn's algorithm
        in_degree = {aid: 0 for aid in agent_ids}
        for aid in agent_ids:
            for dep in graph.get(aid, []):
                if dep in in_degree:
                    in_degree[aid] += 1
        
        # Start with nodes that have no dependencies
        queue = [aid for aid in agent_ids if in_degree[aid] == 0]
        result = []
        
        while queue:
            # Sort by priority (higher first)
            queue.sort(key=lambda x: cls._agents.get(x, AgentInfo(x, None, [])).priority, reverse=True)
            current = queue.pop(0)
            result.append(current)
            
            # Reduce in-degree for dependents
            for aid in agent_ids:
                if current in graph.get(aid, []):
                    in_degree[aid] -= 1
                    if in_degree[aid] == 0:
                        queue.append(aid)
        
        return result
    
    @classmethod
    def update_stats(cls, agent_id: str, success: bool, execution_time: float):
        """Update execution statistics for an agent"""
        if agent_id in cls._agents:
            cls._agents[agent_id].update_stats(success, execution_time)
    
    @classmethod
    def get_health_report(cls) -> Dict[str, Any]:
        """Get health report for all agents"""
        report = {
            'total_agents': len(cls._agents),
            'enabled_agents': len([a for a in cls._agents.values() if a.enabled]),
            'health_summary': {
                'healthy': 0,
                'degraded': 0,
                'unhealthy': 0,
                'unknown': 0
            },
            'agents': {}
        }
        
        for agent_id, info in cls._agents.items():
            health = info.health
            report['health_summary'][health.value] += 1
            report['agents'][agent_id] = {
                'health': health.value,
                'enabled': info.enabled,
                'success_rate': info.success_rate,
                'total_executions': info.total_executions,
                'avg_execution_time': info.avg_execution_time,
                'capabilities': info.capabilities
            }
        
        return report
    
    @classmethod
    def clear(cls):
        """Clear all registered agents (useful for testing)"""
        cls._agents = {}


# Convenience function for registration
def register_agent(agent_id: str = None, capabilities: List[str] = None, **kwargs):
    """Shorthand for AgentRegistry.register"""
    return AgentRegistry.register(agent_id, capabilities, **kwargs)
