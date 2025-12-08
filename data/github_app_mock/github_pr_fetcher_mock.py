"""
Mock GitHub PR Fetcher for Testing

This module simulates GitHub API responses for testing the code review pipeline
without requiring actual GitHub API access or tokens.

Usage:
    Set environment variable: MOCK_GITHUB=true
    The github_pr_fetcher tool will automatically use mock data
"""

import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Load real test files
TEST_FILES_DIR = Path(__file__).parent.parent.parent / "tests" / "test_files"

# ============================================================================
# HELPER FUNCTION TO LOAD TEST FILES
# ============================================================================

def load_test_file(filename: str) -> str:
    """Load content from tests/test_files/ directory."""
    try:
        file_path = TEST_FILES_DIR / filename
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Failed to load test file {filename}: {e}")
        return f"# Error loading {filename}: {str(e)}"


# ============================================================================
# MOCK PR DATA - Using Real Test Files
# ============================================================================

MOCK_PR_DATA = {
    "test-org/test-repo": {
        42: {
            "number": 42,
            "title": "Add chat panel component and refactor orchestrator",
            "description": """This PR adds a React chat panel component and includes a backup of the orchestrator agent.

## Changes
- New ChatPanel.tsx component with WebSocket support
- Backup of orchestrator agent implementation
- Multiple potential issues for code review testing

## Files Changed
1. ChatPanel.tsx - React component with hooks and WebSocket
2. orecestrator_agent_bk.py - Python orchestrator agent backup

## Review Focus
- Security vulnerabilities
- Code quality and complexity
- Engineering best practices
- Performance and carbon impact""",
            "state": "open",
            "author": "developer123",
            "created_at": "2025-12-01T10:00:00Z",
            "updated_at": "2025-12-07T15:30:00Z",
            "head_branch": "feature/chat-and-refactor",
            "base_branch": "main",
            "head_sha": "abc123def456",
            "files": [
                {
                    "filename": "tests/test_files/ChatPanel.tsx",
                    "status": "added",
                    "additions": 378,
                    "deletions": 0,
                    "changes": 378,
                    "language": "typescript",
                    "content": load_test_file("ChatPanel.tsx"),
                    "patch": "@@ -0,0 +1,378 @@\n+" + load_test_file("ChatPanel.tsx")[:500] + "..."
                },
                {
                    "filename": "tests/test_files/orecestrator_agent_bk.py",
                    "status": "added",
                    "additions": 771,
                    "deletions": 0,
                    "changes": 771,
                    "language": "python",
                    "content": load_test_file("orecestrator_agent_bk.py"),
                    "patch": "@@ -0,0,+1,771 @@\n+" + load_test_file("orecestrator_agent_bk.py")[:500] + "..."
                }
            ],
            "stats": {
                "total_files": 2,
                "total_additions": 1149,
                "total_deletions": 0,
                "total_changes": 1149
            },
            "languages": ["typescript", "python"],
            "commits": 5,
            "comments": 3,
            "reviews": 1
        }
    }
}


# ============================================================================
# MOCK PR FETCHING FUNCTIONS  
# ============================================================================


def fetch_mock_pr_files(repo: str, pr_number: int, head_sha: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch mock PR data simulating GitHub API response.
    
    Args:
        repo: Repository in format "owner/repo"
        pr_number: Pull request number
        head_sha: Optional commit SHA (for verification)
        
    Returns:
        dict: Mock PR data with files, metadata, and analysis-ready content
    """
    start_time = time.time()
    
    logger.info(f"[MOCK] Fetching PR #{pr_number} from {repo}")
    
    # Check if we have mock data for this repo/PR
    if repo not in MOCK_PR_DATA:
        return {
            "status": "error",
            "error_message": f"No mock data available for repository: {repo}",
            "tool_name": "fetch_github_pr_files",
            "suggestions": [
                f"Available repos: {', '.join(MOCK_PR_DATA.keys())}",
                "Add mock data in github_pr_fetcher_mock.py"
            ]
        }
    
    repo_prs = MOCK_PR_DATA[repo]
    if pr_number not in repo_prs:
        return {
            "status": "error",
            "error_message": f"No mock data available for PR #{pr_number}",
            "tool_name": "fetch_github_pr_files",
            "suggestions": [
                f"Available PRs: {', '.join(map(str, repo_prs.keys()))}",
                f"Add mock PR #{pr_number} in github_pr_fetcher_mock.py"
            ]
        }
    
    pr_data = repo_prs[pr_number]
    
    # Simulate API delay (realistic timing)
    time.sleep(0.5)
    
    # Build response matching GitHub API structure
    response = {
        "status": "success",
        "tool_name": "fetch_github_pr_files",
        "execution_time": time.time() - start_time,
        "pr_metadata": {
            "number": pr_data["number"],
            "title": pr_data["title"],
            "description": pr_data["description"],
            "state": pr_data["state"],
            "author": pr_data["author"],
            "created_at": pr_data["created_at"],
            "updated_at": pr_data["updated_at"],
            "head_branch": pr_data["head_branch"],
            "base_branch": pr_data["base_branch"],
            "head_sha": pr_data["head_sha"],
            "commits": pr_data["commits"],
            "comments": pr_data["comments"],
            "reviews": pr_data["reviews"]
        },
        "files": pr_data["files"],
        "stats": pr_data["stats"],
        "languages": pr_data["languages"],
        "ready_for_analysis": True
    }
    
    logger.info(f"[MOCK] Successfully fetched PR #{pr_number}: {pr_data['stats']['total_files']} files, {pr_data['stats']['total_additions']} additions")
    
    return response


def get_mock_pr_summary(repo: str, pr_number: int) -> Dict[str, Any]:
    """
    Get mock PR summary without full file content.
    
    Args:
        repo: Repository in format "owner/repo"
        pr_number: Pull request number
        
    Returns:
        dict: Summary of PR metadata and file stats
    """
    logger.info(f"[MOCK] Getting PR summary for #{pr_number} from {repo}")
    
    if repo not in MOCK_PR_DATA or pr_number not in MOCK_PR_DATA[repo]:
        return {
            "status": "error",
            "error_message": f"No mock data for {repo} PR #{pr_number}",
            "tool_name": "get_pr_summary"
        }
    
    pr_data = MOCK_PR_DATA[repo][pr_number]
    
    # Return summary without full file content
    return {
        "status": "success",
        "tool_name": "get_pr_summary",
        "pr_number": pr_data["number"],
        "title": pr_data["title"],
        "author": pr_data["author"],
        "state": pr_data["state"],
        "head_branch": pr_data["head_branch"],
        "base_branch": pr_data["base_branch"],
        "stats": pr_data["stats"],
        "languages": pr_data["languages"],
        "file_list": [f["filename"] for f in pr_data["files"]]
    }


# ============================================================================
# ADDITIONAL MOCK PR SCENARIOS (for future testing)
# ============================================================================

def add_mock_pr(repo: str, pr_number: int, pr_data: Dict[str, Any]):
    """
    Add additional mock PR data for testing.
    
    Args:
        repo: Repository in format "owner/repo"
        pr_number: Pull request number
        pr_data: PR data dictionary matching MOCK_PR_DATA structure
    """
    if repo not in MOCK_PR_DATA:
        MOCK_PR_DATA[repo] = {}
    
    MOCK_PR_DATA[repo][pr_number] = pr_data
    logger.info(f"[MOCK] Added mock PR #{pr_number} for {repo}")


def list_mock_repos() -> List[str]:
    """List all repositories with mock data."""
    return list(MOCK_PR_DATA.keys())


def list_mock_prs(repo: str) -> List[int]:
    """List all PRs with mock data for a repository."""
    return list(MOCK_PR_DATA.get(repo, {}).keys())
