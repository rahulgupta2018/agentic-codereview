"""
Tool for saving analysis results as artifacts.

This tool demonstrates proper ADK artifact usage:
- Async function with ToolContext parameter
- Uses tool_context.save_artifact() to persist results
- Also saves to session-based directory structure on disk
- Returns structured response with version information
"""

from typing import Dict, Any
from pathlib import Path
import json
from google.adk.tools.tool_context import ToolContext
from google.genai import types


async def save_analysis_result(
    analysis_data: str,
    agent_name: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Save analysis result as an artifact.
    
    Saves to TWO locations:
    1. ADK artifact storage (using tool_context.save_artifact)
    2. Disk: storage_bucket/artifacts/<session_id>/<agent_name>_analysis.json
    
    Args:
        analysis_data: JSON string with analysis results
        agent_name: Name of the agent that produced the analysis
        tool_context: ADK tool context (provides access to artifact service and session_id)
    
    Returns:
        Dictionary with status and artifact information
    """
    try:
        # Get session ID from tool context
        session = tool_context.session
        session_id = session.id if session else "unknown"
        
        # Create session-based filename (standardized format)
        artifact_filename = f"{agent_name}_analysis.json"
        
        # Save to ADK artifact storage
        artifact_part = types.Part.from_text(text=analysis_data)
        version = await tool_context.save_artifact(
            filename=artifact_filename,
            artifact=artifact_part
        )
        
        # ALSO save to disk in session-based directory structure
        # storage_bucket/artifacts/<session_id>/<agent_name>_analysis.json
        project_root = Path(__file__).parent.parent
        session_artifacts_dir = project_root / "storage_bucket" / "artifacts" / session_id
        session_artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        artifact_path = session_artifacts_dir / artifact_filename
        
        # Parse and pretty-print JSON for readability
        try:
            parsed_json = json.loads(analysis_data)
            artifact_path.write_text(json.dumps(parsed_json, indent=2), encoding='utf-8')
        except json.JSONDecodeError:
            # If not valid JSON, save as-is
            artifact_path.write_text(analysis_data, encoding='utf-8')
        
        return {
            'status': 'success',
            'report': f'Analysis saved: ADK artifact (v{version}) + disk ({artifact_path.relative_to(project_root)})',
            'data': {
                'filename': artifact_filename,
                'version': version,
                'agent': agent_name,
                'session_id': session_id,
                'disk_path': str(artifact_path.relative_to(project_root))
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'report': f'Failed to save analysis: {str(e)}',
            'data': {'error': str(e)}
        }


async def save_code_input(
    code: str,
    language: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Save user-submitted code as an artifact.
    
    Args:
        code: Source code to save
        language: Programming language
        tool_context: ADK tool context
    
    Returns:
        Dictionary with status and artifact information
    """
    try:
        # Generate filename
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"input_{timestamp}.{language}"
        
        # Create artifact Part
        artifact_part = types.Part.from_text(text=code)
        
        # Save artifact
        version = await tool_context.save_artifact(
            filename=filename,
            artifact=artifact_part
        )
        
        return {
            'status': 'success',
            'report': f'Code saved as {filename}',
            'data': {
                'filename': filename,
                'version': version,
                'language': language
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'report': f'Failed to save code: {str(e)}',
            'data': {'error': str(e)}
        }


async def save_final_report(
    report_markdown: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Save final synthesized report as an artifact.
    
    Saves to TWO locations:
    1. ADK artifact storage (using tool_context.save_artifact)
    2. Disk: storage_bucket/artifacts/reports/<session_id>_report.md
    
    Args:
        report_markdown: Complete markdown report
        tool_context: ADK tool context
    
    Returns:
        Dictionary with status and artifact information
    """
    try:
        # Get session ID from tool context
        session = tool_context.session
        session_id = session.id if session else "unknown"
        
        # Create session-based filename
        artifact_filename = f"{session_id}_report.md"
        
        # Save to ADK artifact storage
        artifact_part = types.Part.from_text(text=report_markdown)
        version = await tool_context.save_artifact(
            filename=artifact_filename,
            artifact=artifact_part
        )
        
        # ALSO save to disk in reports directory
        # storage_bucket/artifacts/reports/<session_id>_report.md
        project_root = Path(__file__).parent.parent
        reports_dir = project_root / "storage_bucket" / "artifacts" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = reports_dir / artifact_filename
        report_path.write_text(report_markdown, encoding='utf-8')
        
        return {
            'status': 'success',
            'report': f'Final report saved: ADK artifact (v{version}) + disk ({report_path.relative_to(project_root)})',
            'data': {
                'filename': artifact_filename,
                'version': version,
                'session_id': session_id,
                'disk_path': str(report_path.relative_to(project_root))
            }
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'report': f'Failed to save report: {str(e)}',
            'data': {'error': str(e)}
        }
