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
import logging
from google.adk.tools.tool_context import ToolContext
from google.genai import types

logger = logging.getLogger(__name__)


async def save_analysis_result(
    analysis_data: str,
    agent_name: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Save analysis result as an artifact.
    
    Saves to THREE locations:
    1. Session state (for next agent in pipeline): tool_context.state[f"{agent_name}_analysis"]
    2. ADK artifact storage (using tool_context.save_artifact)
    3. Disk: storage_bucket/artifacts/<session_id>/<agent_name>_analysis.md
    
    Args:
        analysis_data: Markdown+YAML formatted text string with analysis results (or dict if LLM returns structured output)
        agent_name: Name of the agent that produced the analysis
        tool_context: ADK tool context (provides access to artifact service and session_id)
    
    Returns:
        Dictionary with status and artifact information
    """
    try:
        # Handle dict output from LLM (ADK auto-parsed the text)
        if isinstance(analysis_data, dict):
            # ADK sometimes auto-parses text output into dict
            # We need the original text for Markdown+YAML format
            logger.error(f"💾 [save_analysis_result] Received dict instead of string - this breaks Markdown+YAML format!")
            logger.error(f"💾 Dict keys: {list(analysis_data.keys())}")
            return {
                'status': 'error',
                'report': f'Failed to save analysis: Received dict instead of Markdown+YAML string. This indicates the agent is not outputting in the correct format.',
                'data': {'error': 'Dict output not supported - need Markdown+YAML text string'}
            }
        
        logger.info(f"💾 [save_analysis_result] Called by {agent_name} with {len(analysis_data)} chars of data")
        
        # Strip if LLM incorrectly wraps output
        # Case 1: LLM adds markdown before YAML: "---\n**YAML Output**\n```yaml\n---"
        # Case 2: LLM wraps entire output: "```yaml\n---\nagent:..."
        analysis_data = analysis_data.strip()
        
        # Check if starts with --- but has code fence wrapper
        if analysis_data.startswith('---\n'):
            lines = analysis_data.split('\n')
            # If second line has markdown heading or code fence, strip it
            if len(lines) > 1 and (lines[1].startswith('**') or lines[1].startswith('```')):
                # Find the actual YAML start (next --- after code fence)
                for i, line in enumerate(lines[2:], start=2):
                    if line.strip() == '---':
                        # Found actual YAML start, extract from here
                        analysis_data = '\n'.join(lines[i:])
                        # Remove closing code fence if present
                        if analysis_data.endswith('\n```'):
                            analysis_data = analysis_data[:-4].strip()
                        logger.info(f"  🔧 Stripped markdown wrapper from YAML frontmatter")
                        break
        
        # Check if wrapped in code fence without leading ---
        elif analysis_data.startswith('```yaml\n---') or analysis_data.startswith('```markdown\n---'):
            lines = analysis_data.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]  # Remove opening fence
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]  # Remove closing fence
            analysis_data = '\n'.join(lines).strip()
            logger.info(f"  🔧 Stripped code fence wrapper from output")
        
        # Fix markdown-formatted YAML: **key:** → key:
        # LLM sometimes outputs: "---\n**agent:** security_agent\n**summary:** ..."
        if analysis_data.startswith('---\n'):
            lines = analysis_data.split('\n')
            fixed_lines = []
            in_frontmatter = False
            needs_fix = False
            
            for i, line in enumerate(lines):
                if line.strip() == '---':
                    fixed_lines.append(line)
                    if i == 0:
                        in_frontmatter = True
                    else:
                        in_frontmatter = False
                elif in_frontmatter and line.strip().startswith('**') and ':**' in line:
                    # Fix: **key:** value → key: value
                    needs_fix = True
                    fixed_line = line.replace('**', '').strip()
                    fixed_lines.append(fixed_line)
                else:
                    fixed_lines.append(line)
            
            if needs_fix:
                analysis_data = '\n'.join(fixed_lines)
                logger.info(f"  🔧 Fixed markdown-formatted YAML keys (** markers removed)")
        
        # Get session ID from tool context
        session = tool_context.session
        session_id = session.id if session else "unknown"
        
        # Create session-based filename (standardized format)
        artifact_filename = f"{agent_name}_analysis.md"
        
        # STEP 1: Write to session state (for next agent in pipeline)
        # Map agent_name to the correct session state key
        state_key = f"{agent_name}_analysis"
        if agent_name == "security_agent":
            state_key = "security_analysis"
        elif agent_name == "code_quality_agent":
            state_key = "code_quality_analysis"
        elif agent_name == "engineering_practices_agent":
            state_key = "engineering_practices_analysis"
        elif agent_name == "carbon_emission_agent":
            state_key = "carbon_emission_analysis"
        
        tool_context.state[state_key] = analysis_data
        logger.info(f"  ✅ Wrote to session state: {state_key}")
        
        # STEP 2: Save to ADK artifact storage
        artifact_part = types.Part.from_text(text=analysis_data)
        version = await tool_context.save_artifact(
            filename=artifact_filename,
            artifact=artifact_part
        )
        logger.info(f"  ✅ Saved to ADK artifacts: {artifact_filename} (v{version})")
        
        # STEP 3: ALSO save to disk in session-based directory structure
        # storage_bucket/artifacts/<session_id>/<agent_name>_analysis.md
        project_root = Path(__file__).parent.parent
        session_artifacts_dir = project_root / "storage_bucket" / "artifacts" / session_id
        session_artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        artifact_path = session_artifacts_dir / artifact_filename
        
        # Save Markdown+YAML format as-is (no parsing needed)
        # All agents now output in Markdown+YAML format, not JSON
        artifact_path.write_text(analysis_data, encoding='utf-8')
        logger.info(f"  💾 Saved Markdown+YAML analysis to disk ({len(analysis_data)} chars)")
        
        logger.info(f"  ✅ Saved to disk: {artifact_path.relative_to(project_root)}")
        logger.info(f"✅ [save_analysis_result] {agent_name} analysis saved successfully to 3 locations")
        
        return {
            'status': 'success',
            'report': f'✅ Analysis saved: session state ({state_key}) + ADK artifact (v{version}) + disk ({artifact_path.relative_to(project_root)})',
            'data': {
                'filename': artifact_filename,
                'version': version,
                'agent': agent_name,
                'session_id': session_id,
                'state_key': state_key,
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
