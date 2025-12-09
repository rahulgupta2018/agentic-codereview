"""
Report Saver Agent
Automatically saves the final report from session state to disk as markdown
"""

import sys
import logging
from pathlib import Path
from google.adk.agents import Agent
from google.adk.tools.tool_context import ToolContext

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import model configuration and tools
from util.llm_model import get_sub_agent_model
from tools.save_analysis_artifact import save_final_report


async def save_final_report_from_state(tool_context: ToolContext) -> dict:
    """
    Automatically save the final report from session state to disk.
    
    Reads final_report from tool_context.state and saves as markdown.
    
    Args:
        tool_context: ADK tool context with session state
        
    Returns:
        Dictionary with save status and file path
    """
    try:
        logger.info("📝 [save_final_report_from_state] Reading final_report from session state...")
        
        # Read final_report from session state
        final_report = tool_context.state.get("final_report")
        
        if not final_report:
            logger.warning("⚠️  No final_report found in session state")
            return {
                "status": "error",
                "message": "No final_report found in session state",
                "saved": False
            }
        
        logger.info(f"  ✅ Found final_report ({len(final_report)} chars)")
        
        # Call save_final_report tool to save to disk
        result = await save_final_report(
            report_markdown=final_report,
            tool_context=tool_context
        )
        
        logger.info(f"✅ [save_final_report_from_state] {result.get('report', 'Report saved')}")
        
        return {
            "status": "success",
            "message": result.get('report', 'Report saved successfully'),
            "saved": True,
            "data": result.get('data', {})
        }
        
    except Exception as e:
        logger.error(f"❌ [save_final_report_from_state] Error: {e}")
        return {
            "status": "error",
            "message": f"Failed to save report: {str(e)}",
            "saved": False
        }


def create_report_saver_agent() -> Agent:
    """
    Create report saver agent that automatically saves final report.
    
    Returns:
        Agent: Report saver agent
    """
    logger.info("🔧 [report_saver_agent] Initializing Report Saver Agent")
    agent_model = get_sub_agent_model()
    logger.info(f"🔧 [report_saver_agent] Model configured: {agent_model}")
    
    logger.info("🔧 [report_saver_agent] Creating Agent with automated report saving")
    return Agent(
        name="report_saver_agent",
        model=agent_model,
        description="Automatically saves the final report from session state to disk",
        instruction="""You are a Report Saver Agent.

Your ONLY job: Save the final report to disk.

**Process:**
1. Call save_final_report_from_state() tool
   - This reads final_report from session state
   - Saves it as markdown to storage_bucket/artifacts/reports/<session_id>_report.md
   - Returns success/failure status

2. Return the status to confirm the save

**CRITICAL:**
- You MUST call save_final_report_from_state() tool immediately
- Do NOT skip this step
- Do NOT try to generate or modify the report
- Just read from state and save to disk
""",
        tools=[save_final_report_from_state],
    )


# Create agent instance
report_saver_agent = create_report_saver_agent()

logger.info("✅ [report_saver_agent] Report Saver Agent created successfully")
logger.info("🔧 [report_saver_agent] Tools available: ['save_final_report_from_state']")
