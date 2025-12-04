"""
FairFound Agentic AI System

This module provides a complete multi-agent AI system for evaluating
junior frontend developers with:

- Agent Registry: Central registration and discovery
- Agent Orchestrator: Pipeline execution with retry logic
- Event Bus: Event-driven communication
- Agent Memory: Learning from past interactions
- Monitoring: Performance tracking and anomaly detection
- Adaptive Learning: Weight adjustment from feedback
- Explainability: Human-readable decision explanations
- Multi-Agent Collaboration: Consensus building

Usage:
    from apps.agents import get_orchestrator, AgentContext
    
    orchestrator = get_orchestrator()
    result = orchestrator.execute_pipeline(
        job_id=123,
        user_id=456,
        input_data={'skills': ['react', 'typescript']}
    )
"""

default_app_config = 'apps.agents.apps.AgentsConfig'
