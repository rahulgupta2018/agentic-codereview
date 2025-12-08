"""GitHub Fetcher Agent

Responsible for fetching pull request data from GitHub API.
Runs early in GitHubPipeline to retrieve PR files and metadata.

This agent:
- Fetches PR files and metadata from GitHub
- Extracts code changes and diffs
- Prepares data for downstream analysis agents
"""

import sys
import logging
import os

from pathlib import Path
from typing import Dict, Any, List, Optional
from google.adk.agents import Agent 
from google.adk.tools import FunctionTool

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))  

from util.llm_model import get_sub_agent_model
from tools.github_pr_fetcher import fetch_github_pr_files, get_pr_summary


def create_github_fetcher_agent() -> Agent:
    """
    Create GitHub fetcher agent for retrieving PR data.
    
    This agent fetches PR files and metadata from GitHub API.
    Used in GitHubPipeline (Phase 2 orchestration).
    
    Returns:
        Agent: GitHub fetcher agent with fetch tools
    """
    # Get model from centralized configuration
    agent_model = get_sub_agent_model()
    
    # Create ADK FunctionTools from GitHub functions
    github_fetch_tools = [
        FunctionTool(fetch_github_pr_files),
        FunctionTool(get_pr_summary)
    ]
    
    # Create Agent (NOT LlmAgent)
    # NOTE: No output_key so SequentialAgent continues to next agent
    github_fetcher_agent = Agent(
        name="Github_fetcher_agent",
        model=agent_model,
        tools=github_fetch_tools,
        instruction="""You are Step 1 of a multi-agent pipeline: the DATA FETCHER.

TASK:
1. Call fetch_github_pr_files tool (reads github_context from session state)
2. Call get_pr_summary tool to verify fetch succeeded
3. Output EXACTLY: "Data fetched. Proceeding to planning stage."

DO NOT:
- Analyze code (security/quality/engineering/carbon) - next agents will do this
- Provide recommendations
- Generate reports

Just fetch data and confirm. Then the pipeline will continue automatically."""
        # Removed output_key to allow SequentialAgent to continue to next agent
    )
    
    return github_fetcher_agent


# Create agent instance for import by orchestrator
github_fetcher_agent = create_github_fetcher_agent()
