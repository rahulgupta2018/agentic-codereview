"""
GitHub Review Publisher Tool Implementation for ADK Code Review System.

This tool posts code review comments back to GitHub pull requests.
"""

import time
import logging
from typing import Dict, Any, Optional

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


def post_github_review(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Post code review results to GitHub PR as a comment.
    
    Args:
        tool_context: ADK ToolContext containing session state and parameters
        
    Returns:
        dict: Review posting result with URL
    """
    execution_start = time.time()
    
    try:
        # Get review report from session state
        final_report = tool_context.state.get('final_report', '')
        github_context = tool_context.state.get('github_context', {})
        
        # Check parameters if not in state
        if not final_report and hasattr(tool_context, 'parameters'):
            params = getattr(tool_context, 'parameters', {})
            final_report = params.get('report', '')
            github_context = params.get('github_context', {})
        
        if not final_report:
            return {
                'status': 'error',
                'error_message': 'No review report available to post',
                'tool_name': 'post_github_review'
            }
        
        repo_name = github_context.get('repo', '')
        pr_number = github_context.get('pr_number', 0)
        
        if not repo_name or not pr_number:
            return {
                'status': 'error',
                'error_message': 'Missing required GitHub context: repo and pr_number',
                'tool_name': 'post_github_review'
            }
        
        # Import PyGithub (lazy import)
        try:
            from github import Github
            import os
        except ImportError:
            return {
                'status': 'error',
                'error_message': 'PyGithub not installed. Run: pip install PyGithub',
                'tool_name': 'post_github_review'
            }
        
        # Get GitHub token
        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            return {
                'status': 'error',
                'error_message': 'GITHUB_TOKEN environment variable not set',
                'tool_name': 'post_github_review'
            }
        
        # Initialize GitHub client
        gh = Github(github_token)
        
        # Fetch repository and PR
        logger.info(f"Posting review to PR #{pr_number} in {repo_name}")
        repo = gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        # Format report for GitHub (add header if not present)
        formatted_report = _format_report_for_github(final_report)
        
        # Post review comment
        # Using create_issue_comment for general PR comment
        # Alternative: pr.create_review(body=formatted_report, event="COMMENT")
        comment = pr.create_issue_comment(formatted_report)
        
        result = {
            'status': 'success',
            'tool_name': 'post_github_review',
            'repo_name': repo_name,
            'pr_number': pr_number,
            'comment_id': comment.id,
            'review_url': comment.html_url,
            'posted_at': comment.created_at.isoformat(),
            'timestamp': time.time()
        }
        
        execution_time = time.time() - execution_start
        result['execution_time_seconds'] = execution_time
        
        # Store result in session state
        tool_context.state['github_review_url'] = comment.html_url
        tool_context.state['github_comment_id'] = comment.id
        
        # Update analysis progress
        analysis_progress = tool_context.state.get('analysis_progress', {})
        analysis_progress['github_publish_completed'] = True
        analysis_progress['github_publish_timestamp'] = time.time()
        tool_context.state['analysis_progress'] = analysis_progress
        
        logger.info(f"✅ Posted review to PR #{pr_number}: {comment.html_url}")
        
        return result
        
    except Exception as e:
        execution_time = time.time() - execution_start
        error_result = {
            'status': 'error',
            'tool_name': 'post_github_review',
            'error_message': str(e),
            'error_type': type(e).__name__,
            'execution_time_seconds': execution_time
        }
        
        logger.error(f"❌ Error posting GitHub review: {e}")
        tool_context.state['github_publish_error'] = error_result
        return error_result


def post_review_comment_on_file(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Post a review comment on a specific file and line in the PR.
    
    Args:
        tool_context: ADK ToolContext containing session state and parameters
        
    Returns:
        dict: Comment posting result
    """
    execution_start = time.time()
    
    try:
        # Get parameters
        params = getattr(tool_context, 'parameters', {})
        github_context = tool_context.state.get('github_context', {})
        
        repo_name = github_context.get('repo', params.get('repo', ''))
        pr_number = github_context.get('pr_number', params.get('pr_number', 0))
        commit_id = github_context.get('head_sha', params.get('commit_id', ''))
        
        # Comment details
        file_path = params.get('file_path', '')
        line_number = params.get('line_number', 0)
        comment_body = params.get('comment', '')
        
        if not all([repo_name, pr_number, commit_id, file_path, line_number, comment_body]):
            return {
                'status': 'error',
                'error_message': 'Missing required parameters for file comment',
                'tool_name': 'post_review_comment_on_file'
            }
        
        # Import PyGithub
        try:
            from github import Github
            import os
        except ImportError:
            return {
                'status': 'error',
                'error_message': 'PyGithub not installed',
                'tool_name': 'post_review_comment_on_file'
            }
        
        # Get GitHub token
        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            return {
                'status': 'error',
                'error_message': 'GITHUB_TOKEN not set',
                'tool_name': 'post_review_comment_on_file'
            }
        
        # Initialize GitHub client
        gh = Github(github_token)
        
        # Fetch repository and PR
        logger.info(f"Posting comment on {file_path}:{line_number} in PR #{pr_number}")
        repo = gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        # Create review comment on specific line
        # Note: This requires the file to be part of the PR diff
        comment = pr.create_review_comment(
            body=comment_body,
            commit=repo.get_commit(commit_id),
            path=file_path,
            line=line_number
        )
        
        result = {
            'status': 'success',
            'tool_name': 'post_review_comment_on_file',
            'comment_id': comment.id,
            'comment_url': comment.html_url,
            'file_path': file_path,
            'line_number': line_number,
            'timestamp': time.time()
        }
        
        execution_time = time.time() - execution_start
        result['execution_time_seconds'] = execution_time
        
        logger.info(f"✅ Posted comment on {file_path}:{line_number}")
        
        return result
        
    except Exception as e:
        execution_time = time.time() - execution_start
        error_result = {
            'status': 'error',
            'tool_name': 'post_review_comment_on_file',
            'error_message': str(e),
            'error_type': type(e).__name__,
            'execution_time_seconds': execution_time
        }
        
        logger.error(f"❌ Error posting file comment: {e}")
        return error_result


def update_review_comment(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Update an existing review comment.
    
    Args:
        tool_context: ADK ToolContext containing session state and parameters
        
    Returns:
        dict: Update result
    """
    execution_start = time.time()
    
    try:
        params = getattr(tool_context, 'parameters', {})
        github_context = tool_context.state.get('github_context', {})
        
        repo_name = github_context.get('repo', params.get('repo', ''))
        comment_id = params.get('comment_id', tool_context.state.get('github_comment_id', 0))
        new_body = params.get('new_body', '')
        
        if not all([repo_name, comment_id, new_body]):
            return {
                'status': 'error',
                'error_message': 'Missing required parameters: repo, comment_id, new_body',
                'tool_name': 'update_review_comment'
            }
        
        # Import PyGithub
        try:
            from github import Github
            import os
        except ImportError:
            return {
                'status': 'error',
                'error_message': 'PyGithub not installed',
                'tool_name': 'update_review_comment'
            }
        
        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            return {
                'status': 'error',
                'error_message': 'GITHUB_TOKEN not set',
                'tool_name': 'update_review_comment'
            }
        
        gh = Github(github_token)
        repo = gh.get_repo(repo_name)
        
        # Get the comment
        comment = repo.get_issue_comment(comment_id)
        
        # Update comment
        comment.edit(new_body)
        
        result = {
            'status': 'success',
            'tool_name': 'update_review_comment',
            'comment_id': comment_id,
            'comment_url': comment.html_url,
            'updated_at': comment.updated_at.isoformat(),
            'timestamp': time.time()
        }
        
        execution_time = time.time() - execution_start
        result['execution_time_seconds'] = execution_time
        
        logger.info(f"✅ Updated comment {comment_id}")
        
        return result
        
    except Exception as e:
        execution_time = time.time() - execution_start
        return {
            'status': 'error',
            'tool_name': 'update_review_comment',
            'error_message': str(e),
            'error_type': type(e).__name__,
            'execution_time_seconds': execution_time
        }


def _format_report_for_github(report: str) -> str:
    """
    Format review report for GitHub display.
    
    Args:
        report: Raw markdown report
        
    Returns:
        str: Formatted report with GitHub-specific styling
    """
    # Add header if not present
    if not report.startswith('#'):
        header = """## 🤖 AI Code Review Report
        
*Generated by ADK Multi-Agent Code Review System*

---

"""
        report = header + report
    
    # Add footer
    footer = """

---

<details>
<summary>ℹ️ About this review</summary>

This automated code review was generated using Google ADK (Agent Development Kit) with multiple specialized analysis agents:

- 🔒 **Security Analysis** - Vulnerability detection
- 📊 **Code Quality** - Complexity & maintainability
- ⚙️ **Engineering Practices** - Best practices & patterns
- 🌱 **Carbon Footprint** - Computational efficiency

For questions or feedback, please contact your development team.
</details>
"""
    
    return report + footer
