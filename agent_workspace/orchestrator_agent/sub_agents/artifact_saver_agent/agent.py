"""
Artifact Saver Agent

Purpose: Automatically save all analysis results from session state to disk artifacts.

This agent solves the artifact persistence problem:
- Analysis agents write to session state via output_key
- LLMs don't reliably call save_analysis_result tool
- Solution: This agent reads session state and saves all artifacts

This runs AFTER AnalysisPipeline and BEFORE Report Synthesizer.
"""

import sys
import logging
from pathlib import Path
from google.adk.agents import Agent

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from util.llm_model import get_sub_agent_model
from tools.save_analysis_artifact import save_analysis_result

# Get model
logger.info("🔧 [artifact_saver_agent] Initializing Artifact Saver Agent")
agent_model = get_sub_agent_model()
logger.info(f"🔧 [artifact_saver_agent] Model configured: {agent_model}")

# Create a simpler tool that directly saves all artifacts without LLM decision-making
from google.adk.tools.tool_context import ToolContext
import asyncio

async def save_all_analysis_artifacts(tool_context: ToolContext) -> dict:
    """
    Save all 4 analysis results from session state to disk.
    
    This is a deterministic function that doesn't require LLM decision-making.
    It reads all analysis results from session state and saves them as artifacts.
    """
    logger.info("💾 [save_all_analysis_artifacts] Starting to save all analysis artifacts...")
    
    results = []
    analyses = [
        ("security_analysis", "security_agent"),
        ("code_quality_analysis", "code_quality_agent"),
        ("engineering_practices_analysis", "engineering_practices_agent"),
        ("carbon_emission_analysis", "carbon_emission_agent"),
    ]
    
    for state_key, agent_name in analyses:
        analysis_data = tool_context.state.get(state_key)
        if analysis_data:
            logger.info(f"  💾 Saving {state_key} ({len(str(analysis_data))} chars)...")
            result = await save_analysis_result(analysis_data, agent_name, tool_context)
            results.append(result)
            if result.get('status') == 'success':
                logger.info(f"    ✅ {state_key} saved successfully")
            else:
                logger.warning(f"    ❌ {state_key} save failed: {result.get('report')}")
        else:
            logger.warning(f"  ⚠️ {state_key} not found in session state - skipping")
    
    logger.info(f"✅ [save_all_analysis_artifacts] Saved {len(results)}/4 analysis artifacts")
    
    return {
        'status': 'success',
        'saved_count': len(results),
        'total_expected': 4,
        'details': results
    }

# Artifact Saver Agent - simple deterministic agent
logger.info("🔧 [artifact_saver_agent] Creating Agent with automated artifact saving")
artifact_saver_agent = Agent(
    name="artifact_saver_agent",
    model=agent_model,
    description="Automatically saves all analysis results from session state to disk",
    instruction="""You are an Artifact Saver Agent.

**YOUR TASK:**
Call save_all_analysis_artifacts() tool immediately.

The tool will automatically:
- Read all 4 analysis results from session state
- Save each one to disk as an artifact
- Report success

**IMPORTANT:**
Just call save_all_analysis_artifacts() and report the result.
""".strip(),
    tools=[save_all_analysis_artifacts],
)

logger.info("✅ [artifact_saver_agent] Artifact Saver Agent created successfully")
logger.info(f"🔧 [artifact_saver_agent] Tools available: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in [save_all_analysis_artifacts]]}")
