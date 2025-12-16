"""
Tool to load analysis results from persisted artifact files.

This tool allows the report synthesizer agent to read agent outputs
from disk using session-based directory structure.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


async def load_analysis_results_from_artifacts(
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Load all analysis results from session-based artifact directory.
    
    This tool loads analysis artifacts saved by analysis agents from
    storage_bucket/artifacts/<session_id>/ directory structure.
    
    Files are now in Markdown+YAML format (not JSON).
    
    Expected file structure:
        storage_bucket/artifacts/<session_id>/security_agent_analysis.md
        storage_bucket/artifacts/<session_id>/code_quality_agent_analysis.md
        storage_bucket/artifacts/<session_id>/engineering_practices_agent_analysis.md
        storage_bucket/artifacts/<session_id>/carbon_emission_agent_analysis.md
    
    Args:
        tool_context: ADK tool context (provides session_id)
        
    Returns:
        Dictionary containing:
        {
            "session_id": "e735b7b0-ea36-49ee-96c1-ef671f4d1594",
            "results": {
                "security_agent": "---\\nagent: security_agent\\n...\\n# Analysis...",
                "code_quality_agent": "---\\nagent: code_quality_agent...",
                ...
            },
            "agents_found": ["security_agent", "code_quality_agent", ...],
            "total_agents": 2
        }
    """
    # Get session ID from tool context
    session = tool_context.session
    session_id = session.id if session else "unknown"
    
    # Construct path to session artifacts directory
    project_root = Path(__file__).parent.parent
    session_artifacts_dir = project_root / "storage_bucket" / "artifacts" / session_id
    
    logger.info(f"Loading analysis artifacts for session: {session_id}")
    logger.info(f"Looking in: {session_artifacts_dir}")
    
    if not session_artifacts_dir.exists():
        logger.warning(f"Session artifacts directory does not exist: {session_artifacts_dir}")
        return {
            "session_id": session_id,
            "results": {},
            "agents_found": [],
            "total_agents": 0,
            "message": "No analysis results found. Analysis agents may not have run yet, or artifacts not saved."
        }
    
    try:
        # Find all *_analysis.md files in session directory
        analysis_files = list(session_artifacts_dir.glob("*_analysis.md"))
        
        if not analysis_files:
            logger.info(f"No analysis files found in {session_artifacts_dir}")
            return {
                "session_id": session_id,
                "results": {},
                "agents_found": [],
                "total_agents": 0,
                "message": "No analysis artifacts found in session directory."
            }
        
        logger.info(f"Found {len(analysis_files)} analysis artifact files")
        
        # Load results from each file
        results = {}
        agents_found = []
        
        for file_path in analysis_files:
            # Extract agent name from filename: <agent_name>_analysis.md
            agent_name = file_path.stem.replace('_analysis', '')
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # Read as text (Markdown+YAML format, not JSON)
                    agent_result = f.read()
                
                results[agent_name] = agent_result
                agents_found.append(agent_name)
                logger.info(f"  ✓ Loaded {agent_name} results ({file_path.stat().st_size} bytes)")
                
            except Exception as e:
                logger.error(f"  ✗ Error reading {file_path.name}: {e}")
        
        return {
            "session_id": session_id,
            "results": results,
            "agents_found": agents_found,
            "total_agents": len(agents_found),
            "message": f"Successfully loaded {len(agents_found)} analysis results from session artifacts"
        }
    
    except Exception as e:
        logger.error(f"Error loading analysis results: {e}")
        return {
            "session_id": session_id,
            "results": {},
            "agents_found": [],
            "total_agents": 0,
            "error": f"Failed to load analysis results: {str(e)}"
        }
