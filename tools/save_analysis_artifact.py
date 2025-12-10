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
    3. Disk: storage_bucket/artifacts/<session_id>/<agent_name>_analysis.json
    
    Args:
        analysis_data: JSON string with analysis results
        agent_name: Name of the agent that produced the analysis
        tool_context: ADK tool context (provides access to artifact service and session_id)
    
    Returns:
        Dictionary with status and artifact information
    """
    try:
        logger.info(f"💾 [save_analysis_result] Called by {agent_name} with {len(analysis_data)} chars of data")
        
        # Strip markdown code fences if present (LLMs often wrap JSON in ```json...```)
        analysis_data = analysis_data.strip()
        if analysis_data.startswith('```json'):
            # Remove opening ```json and closing ```
            lines = analysis_data.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]  # Remove first line
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]  # Remove last line
            analysis_data = '\n'.join(lines).strip()
            logger.info(f"  🔧 Stripped markdown code fences from analysis data")
        elif analysis_data.startswith('```'):
            # Generic code fence
            lines = analysis_data.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            analysis_data = '\n'.join(lines).strip()
            logger.info(f"  🔧 Stripped markdown code fences from analysis data")
        
        # Sanitize markdown backticks inside JSON strings (model mixing markdown with JSON)
        # Replace backticks with single quotes to maintain valid JSON
        import re
        original_data = analysis_data
        # Replace backticks that appear inside JSON string values
        # Pattern: finds backticks within quoted strings (not at start/end of file)
        analysis_data = re.sub(r'`([^`]+)`', r"'\1'", analysis_data)
        if analysis_data != original_data:
            logger.info(f"  🔧 Sanitized markdown backticks inside JSON strings")
        
        # Get session ID from tool context
        session = tool_context.session
        session_id = session.id if session else "unknown"
        
        # Create session-based filename (standardized format)
        artifact_filename = f"{agent_name}_analysis.json"
        
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
        # storage_bucket/artifacts/<session_id>/<agent_name>_analysis.json
        project_root = Path(__file__).parent.parent
        session_artifacts_dir = project_root / "storage_bucket" / "artifacts" / session_id
        session_artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        artifact_path = session_artifacts_dir / artifact_filename
        
        # Parse and pretty-print JSON for readability
        try:
            parsed_json = json.loads(analysis_data)
            artifact_path.write_text(json.dumps(parsed_json, indent=2), encoding='utf-8')
            
            # Parse and log confidence scores
            findings_with_confidence = []
            confidence_scores = []
            
            # Helper function to recursively extract confidence scores from nested structures
            def extract_confidence_scores_recursive(data, path=""):
                """Recursively search for confidence_score keys in nested dictionaries and lists."""
                if isinstance(data, dict):
                    # Check if this dict has a confidence_score
                    if 'confidence_score' in data:
                        score = data.get('confidence_score', 0.0)
                        confidence_scores.append(score)
                        findings_with_confidence.append({
                            'type': data.get('type') or data.get('issue') or data.get('principle') or data.get('recommendation', '')[:50] or path or 'finding',
                            'confidence': score,
                            'reasoning': data.get('confidence_reasoning', 'N/A')
                        })
                    
                    # Recursively search nested dictionaries
                    for key, value in data.items():
                        new_path = f"{path}.{key}" if path else key
                        extract_confidence_scores_recursive(value, new_path)
                        
                elif isinstance(data, list):
                    # Recursively search list items
                    for i, item in enumerate(data):
                        new_path = f"{path}[{i}]" if path else f"[{i}]"
                        extract_confidence_scores_recursive(item, new_path)
            
            # Extract confidence scores from entire JSON structure
            extract_confidence_scores_recursive(parsed_json)
            
            # Log confidence score statistics
            if confidence_scores:
                avg_confidence = sum(confidence_scores) / len(confidence_scores)
                high_confidence_count = len([s for s in confidence_scores if s >= 0.90])
                medium_confidence_count = len([s for s in confidence_scores if 0.70 <= s < 0.90])
                low_confidence_count = len([s for s in confidence_scores if s < 0.70])
                
                logger.info(
                    f"💯 [save_analysis_artifact] Confidence scores logged for {agent_name}",
                    extra={
                        'agent': agent_name,
                        'total_findings': len(findings_with_confidence),
                        'avg_confidence': round(avg_confidence, 3),
                        'high_confidence_count': high_confidence_count,
                        'medium_confidence_count': medium_confidence_count,
                        'low_confidence_count': low_confidence_count
                    }
                )
                
                # Log low confidence findings for review
                low_confidence_findings = [f for f in findings_with_confidence if f['confidence'] < 0.60]
                if low_confidence_findings:
                    logger.warning(
                        f"⚠️ [save_analysis_artifact] {len(low_confidence_findings)} low-confidence findings (<0.60) for {agent_name}",
                        extra={
                            'agent': agent_name,
                            'low_confidence_findings': low_confidence_findings
                        }
                    )
            else:
                logger.warning(f"⚠️ [save_analysis_artifact] No confidence scores found in {agent_name} output")
                
        except json.JSONDecodeError:
            # If not valid JSON, save as-is
            artifact_path.write_text(analysis_data, encoding='utf-8')
            logger.warning(f"⚠️ [save_analysis_artifact] Invalid JSON from {agent_name}, saved as-is")
        
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
