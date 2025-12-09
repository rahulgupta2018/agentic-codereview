"""
GitHub Data Adapter Tool for ADK Code Review System.

This tool transforms GitHub PR file data from the fetcher's format into
the format that analysis tools expect.

Problem:
- GitHub Fetcher outputs: {filename, content, language, status, ...}
- Analysis Tools expect: tool_context.state["code"], ["language"], ["file_path"]

Solution:
- Extract files from github_pr_files
- Combine multi-file PRs into single analysis context (Strategy A)
- Set session state variables that analysis tools can read
"""

import time
import logging
from typing import Dict, Any, List
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


def prepare_files_for_analysis(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Adapt GitHub PR files data for analysis tools.
    
    Reads github_pr_files from session state and transforms into
    format that analysis tools expect (code, language, file_path).
    
    Strategy A (Phase 1): Concatenate all files with headers
    - Simple to implement
    - Agents see full PR context
    - Works with current tools unchanged
    
    Args:
        tool_context: ADK ToolContext containing session state
        
    Returns:
        dict: Status and summary of files prepared
    """
    execution_start = time.time()
    
    try:
        # Get github_pr_files from session state (set by GitHub Fetcher)
        github_pr_files = tool_context.state.get('github_pr_files', [])
        
        if not github_pr_files:
            logger.warning("⚠️ No github_pr_files found in session state")
            return {
                'status': 'error',
                'error_message': 'No GitHub PR files found in session state',
                'tool_name': 'prepare_files_for_analysis',
                'hint': 'Ensure GitHub Fetcher runs first and populates github_pr_files'
            }
        
        logger.info(f"📦 Preparing {len(github_pr_files)} files for analysis")
        
        # Strategy A: Concatenate all files into single analysis context
        combined_code = ""
        file_summaries = []
        total_lines = 0
        languages = set()
        
        for idx, file_data in enumerate(github_pr_files, 1):
            filename = file_data.get('filename', f'file_{idx}')
            content = file_data.get('content', '')
            language = file_data.get('language', 'unknown')
            status = file_data.get('status', 'modified')
            additions = file_data.get('additions', 0)
            deletions = file_data.get('deletions', 0)
            
            # Track metadata
            languages.add(language)
            lines_count = len(content.split('\n')) if content else 0
            total_lines += lines_count
            
            file_summaries.append({
                'file_path': filename,
                'language': language,
                'status': status,
                'lines': lines_count,
                'additions': additions,
                'deletions': deletions
            })
            
            # Add file header and content
            combined_code += f"\n\n{'='*80}\n"
            combined_code += f"File: {filename}\n"
            combined_code += f"Language: {language}\n"
            combined_code += f"Status: {status}\n"
            combined_code += f"Lines: {lines_count}\n"
            combined_code += f"{'='*80}\n\n"
            combined_code += content
            combined_code += "\n\n"
            
            logger.info(f"  ✅ {idx}. {filename} ({language}, {lines_count} lines)")
        
        # Determine primary language (most common)
        if len(languages) == 1:
            primary_language = list(languages)[0]
        elif len(languages) > 1:
            primary_language = "multi"
            logger.info(f"  🌐 Multi-language PR: {', '.join(sorted(languages))}")
        else:
            primary_language = "unknown"
        
        # Store prepared data in session state (for analysis tools to read)
        tool_context.state['code'] = combined_code
        tool_context.state['language'] = primary_language
        tool_context.state['file_path'] = f"PR_combined_{len(github_pr_files)}_files"
        tool_context.state['files'] = file_summaries
        tool_context.state['files_prepared'] = True
        tool_context.state['file_count'] = len(github_pr_files)
        tool_context.state['total_lines'] = total_lines
        tool_context.state['languages'] = list(languages)
        
        execution_time = time.time() - execution_start
        
        result = {
            'status': 'success',
            'tool_name': 'prepare_files_for_analysis',
            'files_prepared': len(github_pr_files),
            'total_lines': total_lines,
            'primary_language': primary_language,
            'all_languages': list(languages),
            'file_summaries': file_summaries,
            'execution_time': round(execution_time, 3),
            'message': f"✅ Prepared {len(github_pr_files)} files ({total_lines} lines) for analysis"
        }
        
        logger.info(
            f"✅ GitHub Data Adapter: Prepared {len(github_pr_files)} files "
            f"({total_lines} lines, {primary_language}) in {execution_time:.2f}s"
        )
        
        return result
        
    except Exception as e:
        execution_time = time.time() - execution_start
        error_msg = f"Error preparing files for analysis: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        
        return {
            'status': 'error',
            'tool_name': 'prepare_files_for_analysis',
            'error_message': error_msg,
            'execution_time': round(execution_time, 3)
        }
