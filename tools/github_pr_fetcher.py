"""
GitHub PR Fetcher Tool Implementation for ADK Code Review System.

This tool fetches pull request files and metadata from GitHub API.
Supports mock mode for testing without GitHub API access.
"""

import time
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)

# Add project root to Python path for mock imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def fetch_github_pr_files(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Fetch PR files and metadata from GitHub.
    
    Supports two modes:
    1. MOCK_GITHUB=true: Uses mock data from data/github_app_mock/
    2. Real mode: Uses GitHub API with GITHUB_TOKEN
    
    Args:
        tool_context: ADK ToolContext containing session state and parameters
        
    Returns:
        dict: PR files, metadata, and diff information
    """
    execution_start = time.time()
    
    try:
        # Get GitHub context from tool context state
        github_context = tool_context.state.get('github_context', {})
        
        # Check parameters if not in state
        if not github_context and hasattr(tool_context, 'parameters'):
            params = getattr(tool_context, 'parameters', {})
            github_context = {
                'repo': params.get('repo', ''),
                'pr_number': params.get('pr_number', 0),
                'head_sha': params.get('head_sha', '')
            }
        
        repo_name = github_context.get('repo', '')
        pr_number = github_context.get('pr_number', 0)
        head_sha = github_context.get('head_sha', '')
        
        if not repo_name or not pr_number:
            return {
                'status': 'error',
                'error_message': 'Missing required parameters: repo and pr_number',
                'tool_name': 'fetch_github_pr_files'
            }
        
        # =====================================================================
        # MOCK MODE - Use mock data for testing
        # =====================================================================
        use_mock = os.getenv('MOCK_GITHUB', 'false').lower() == 'true'
        
        if use_mock:
            logger.info(f"🧪 [MOCK MODE] Fetching PR #{pr_number} from {repo_name}")
            try:
                from data.github_app_mock.github_pr_fetcher_mock import fetch_mock_pr_files
                result = fetch_mock_pr_files(repo_name, pr_number, head_sha)
                
                # Store in session state for downstream agents
                if result.get('status') == 'success':
                    tool_context.state['github_pr_files'] = result['files']
                    tool_context.state['github_pr_metadata'] = result['pr_metadata']
                    tool_context.state['github_pr_stats'] = result['stats']
                    logger.info(f"✅ [MOCK] Stored {len(result['files'])} files in session state")
                
                return result
                
            except ImportError as e:
                return {
                    'status': 'error',
                    'error_message': f'Mock module not found: {str(e)}',
                    'tool_name': 'fetch_github_pr_files',
                    'hint': 'Check that data/github_app_mock/github_pr_fetcher_mock.py exists'
                }
        
        # =====================================================================
        # REAL MODE - Use GitHub API
        # =====================================================================
        
        # Import PyGithub (lazy import to avoid dependency issues)
        try:
            from github import Github
        except ImportError:
            return {
                'status': 'error',
                'error_message': 'PyGithub not installed. Run: pip install PyGithub',
                'tool_name': 'fetch_github_pr_files'
            }
        
        # Get GitHub token from environment
        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            return {
                'status': 'error',
                'error_message': 'GITHUB_TOKEN environment variable not set',
                'tool_name': 'fetch_github_pr_files'
            }
        
        # Initialize GitHub client
        gh = Github(github_token)
        
        # Fetch repository and PR
        logger.info(f"Fetching PR #{pr_number} from {repo_name}")
        repo = gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        # Extract PR metadata
        pr_metadata = {
            'pr_number': pr.number,
            'title': pr.title,
            'body': pr.body or '',
            'state': pr.state,
            'created_at': pr.created_at.isoformat(),
            'updated_at': pr.updated_at.isoformat(),
            'user': {
                'login': pr.user.login,
                'id': pr.user.id
            },
            'head': {
                'ref': pr.head.ref,
                'sha': pr.head.sha
            },
            'base': {
                'ref': pr.base.ref,
                'sha': pr.base.sha
            },
            'commits': pr.commits,
            'additions': pr.additions,
            'deletions': pr.deletions,
            'changed_files': pr.changed_files,
            'mergeable': pr.mergeable,
            'mergeable_state': pr.mergeable_state
        }
        
        # Fetch files changed in PR
        files_data = []
        for file in pr.get_files():
            file_info = {
                'filename': file.filename,
                'status': file.status,  # added, removed, modified, renamed
                'additions': file.additions,
                'deletions': file.deletions,
                'changes': file.changes,
                'patch': file.patch if hasattr(file, 'patch') and file.patch else '',
                'raw_url': file.raw_url,
                'blob_url': file.blob_url,
                'previous_filename': file.previous_filename if hasattr(file, 'previous_filename') else None
            }
            
            # Detect language from filename extension
            file_info['language'] = _detect_language(file.filename)
            
            # Extract code content if available
            if file.status != 'removed':
                try:
                    content_file = repo.get_contents(file.filename, ref=pr.head.sha)
                    if content_file.encoding == 'base64':
                        import base64
                        file_info['content'] = base64.b64decode(content_file.content).decode('utf-8')
                    else:
                        file_info['content'] = content_file.decoded_content.decode('utf-8')
                except Exception as e:
                    logger.warning(f"Could not fetch content for {file.filename}: {e}")
                    file_info['content'] = ''
            else:
                file_info['content'] = ''
            
            files_data.append(file_info)
        
        # Build result
        result = {
            'status': 'success',
            'tool_name': 'fetch_github_pr_files',
            'repo_name': repo_name,
            'pr_metadata': pr_metadata,
            'files': files_data,
            'total_files': len(files_data),
            'summary': {
                'total_additions': pr_metadata['additions'],
                'total_deletions': pr_metadata['deletions'],
                'total_changes': pr_metadata['additions'] + pr_metadata['deletions'],
                'files_by_status': _count_files_by_status(files_data),
                'languages': _count_languages(files_data)
            },
            'timestamp': time.time()
        }
        
        execution_time = time.time() - execution_start
        result['execution_time_seconds'] = execution_time
        
        # Store results in session state
        tool_context.state['github_pr_data'] = result
        
        # Update analysis progress
        analysis_progress = tool_context.state.get('analysis_progress', {})
        analysis_progress['github_fetch_completed'] = True
        analysis_progress['github_fetch_timestamp'] = time.time()
        tool_context.state['analysis_progress'] = analysis_progress
        
        logger.info(f"✅ Fetched {len(files_data)} files from PR #{pr_number}")
        
        return result
        
    except Exception as e:
        execution_time = time.time() - execution_start
        error_result = {
            'status': 'error',
            'tool_name': 'fetch_github_pr_files',
            'error_message': str(e),
            'error_type': type(e).__name__,
            'execution_time_seconds': execution_time
        }
        
        logger.error(f"❌ Error fetching GitHub PR: {e}")
        tool_context.state['github_fetch_error'] = error_result
        return error_result


def _detect_language(filename: str) -> str:
    """Detect programming language from filename extension."""
    extension_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.c': 'c',
        '.cpp': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.sh': 'bash',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.json': 'json',
        '.xml': 'xml',
        '.html': 'html',
        '.css': 'css',
        '.sql': 'sql',
        '.md': 'markdown',
        '.txt': 'text'
    }
    
    for ext, lang in extension_map.items():
        if filename.endswith(ext):
            return lang
    
    return 'unknown'


def _count_files_by_status(files_data: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count files by status (added, modified, removed, renamed)."""
    counts = {
        'added': 0,
        'modified': 0,
        'removed': 0,
        'renamed': 0
    }
    
    for file in files_data:
        status = file.get('status', 'modified')
        if status in counts:
            counts[status] += 1
    
    return counts


def _count_languages(files_data: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count files by programming language."""
    counts = {}
    
    for file in files_data:
        language = file.get('language', 'unknown')
        counts[language] = counts.get(language, 0) + 1
    
    return counts


def get_pr_summary(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get a summary of PR data from session state.
    
    Supports two modes:
    1. MOCK_GITHUB=true: Uses mock data
    2. Real mode: Uses data from previous fetch_github_pr_files call
    
    Args:
        tool_context: ADK ToolContext containing session state
        
    Returns:
        dict: PR summary information
    """
    try:
        # Check for mock mode
        use_mock = os.getenv('MOCK_GITHUB', 'false').lower() == 'true'
        
        if use_mock:
            logger.info("🧪 [MOCK MODE] Getting PR summary from mock data")
            
            # Get repo and PR number from session state
            github_context = tool_context.state.get('github_context', {})
            repo_name = github_context.get('repo', '')
            pr_number = github_context.get('pr_number', 0)
            
            if not repo_name or not pr_number:
                return {
                    'status': 'error',
                    'error_message': 'Missing repo or pr_number in session state',
                    'tool_name': 'get_pr_summary'
                }
            
            try:
                from data.github_app_mock.github_pr_fetcher_mock import get_mock_pr_summary
                return get_mock_pr_summary(repo_name, pr_number)
            except ImportError as e:
                return {
                    'status': 'error',
                    'error_message': f'Mock module not found: {str(e)}',
                    'tool_name': 'get_pr_summary'
                }
        
        # Real mode - get from session state
        github_pr_data = tool_context.state.get('github_pr_data', {})
        
        if not github_pr_data or github_pr_data.get('status') != 'success':
            return {
                'status': 'error',
                'error_message': 'No PR data available in session state',
                'tool_name': 'get_pr_summary'
            }
        
        pr_metadata = github_pr_data.get('pr_metadata', {})
        summary = github_pr_data.get('summary', {})
        
        return {
            'status': 'success',
            'tool_name': 'get_pr_summary',
            'pr_number': pr_metadata.get('pr_number'),
            'title': pr_metadata.get('title'),
            'state': pr_metadata.get('state'),
            'total_files': github_pr_data.get('total_files', 0),
            'total_additions': summary.get('total_additions', 0),
            'total_deletions': summary.get('total_deletions', 0),
            'files_by_status': summary.get('files_by_status', {}),
            'languages': summary.get('languages', {})
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'tool_name': 'get_pr_summary',
            'error_message': str(e),
            'error_type': type(e).__name__
        }
