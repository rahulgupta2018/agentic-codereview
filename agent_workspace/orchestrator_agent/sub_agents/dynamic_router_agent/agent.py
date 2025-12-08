"""
Dynamic Router Agent

Purpose:
    Creates a sub-workflow with all analysis agents pre-configured.
    All agents run SEQUENTIALLY (one-by-one) to prioritize accuracy over speed.
    
Architecture:
    This agent wraps all 4 analysis agents in a SequentialAgent structure.
    Agents execute sequentially - each completes before the next starts.
    This ensures thorough analysis and prevents resource contention.

Design Philosophy:
    - Accuracy over speed for GitHub PR reviews
    - Sequential execution prevents LLM context switching
    - Avoids API rate limiting issues
    - GitHub PRs are async - no user waiting for immediate response
    - More thorough, reliable results for production code

Note:
    ADK 1.19.0 doesn't support true dynamic agent creation at runtime.
    This is a static structure where all agents run sequentially.
"""

import sys
import logging
from pathlib import Path
from typing import Dict
from google.adk.agents import SequentialAgent, Agent

logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class DynamicRouterAgent(SequentialAgent):
    """
    Wrapper for sequential execution of analysis agents.
    
    All agents run sequentially (one-by-one) to prioritize accuracy over speed.
    Each agent completes fully before the next starts, ensuring thorough analysis.
    
    Execution Order:
        1. Security Agent - Completes fully
        2. Code Quality Agent - Completes fully  
        3. Engineering Practices Agent - Completes fully
        4. Carbon Emission Agent - Completes fully
    
    This approach prevents:
        - LLM context switching
        - API rate limiting
        - Resource contention
        - Incomplete analysis results
    """
    
    def __init__(self, agent_registry: Dict[str, Agent], **kwargs):
        """
        Initialize router with all analysis agents for sequential execution.
        
        Args:
            agent_registry: Dict of {"agent_name": agent_instance}
        """
        # Extract agents in priority order
        sub_agents = [
            agent_registry.get("security"),       # 1st priority
            agent_registry.get("code_quality"),   # 2nd priority
            agent_registry.get("engineering"),    # 3rd priority
            agent_registry.get("carbon"),         # 4th priority
        ]
        
        # Filter out None values
        sub_agents = [agent for agent in sub_agents if agent is not None]
        
        logger.info(f"🔧 [DynamicRouter] Creating SEQUENTIAL execution with {len(sub_agents)} agents")
        logger.info("   Execution mode: Sequential (accuracy over speed)")
        logger.info("   Order: security → quality → engineering → carbon")
        
        super().__init__(
            name="DynamicRouter",
            sub_agents=sub_agents,
            description="Sequential execution of all analysis agents (accuracy over speed)",
            **kwargs
        )


def create_dynamic_router(
    agent_registry: Dict[str, Agent]
) -> DynamicRouterAgent:
    """
    Factory function to create DynamicRouterAgent instances.
    
    Args:
        agent_registry: Dict of {"agent_name": agent_instance}
    
    Returns:
        DynamicRouterAgent instance
    """
    return DynamicRouterAgent(agent_registry=agent_registry)
