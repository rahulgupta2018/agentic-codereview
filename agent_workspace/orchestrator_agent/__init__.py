"""
Orchestrator Agent Module

Exports the ADK-based deterministic workflow orchestrator using:
- SequentialAgent for deterministic workflow execution
- Dynamic routing based on source detection (GitHub vs Web UI)
- PlanReActPlanner for intelligent agent selection
- No custom if/elif orchestration logic
"""

from .agent import root_agent, orchestrator_agent, orchestrator

__all__ = ['root_agent', 'orchestrator_agent', 'orchestrator']