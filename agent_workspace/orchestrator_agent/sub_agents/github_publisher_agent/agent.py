"""GitHub Publisher Agent

Responsible for posting code review results back to GitHub pull requests.
Runs at the end of GitHubPipeline after report synthesis.

This agent:
- Posts review reports to GitHub PR as comments
- Adds inline comments on specific files/lines (optional)
- Updates existing comments if needed
- Handles posting errors gracefully
"""

import sys
import logging
import os

from pathlib import Path
from typing import Dict, Any, List, Optional
from google.adk.agents import Agent 
from google.adk.tools import FunctionTool

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))  

from util.llm_model import get_sub_agent_model
from tools.github_review_publisher import (
    post_github_review,
    post_review_comment_on_file,
    update_review_comment
)


def create_github_publisher_agent() -> Agent:
    """
    Create GitHub publisher agent for posting reviews.
    
    This agent posts code review results back to GitHub PR.
    Used in GitHubPipeline (Phase 2 orchestration).
    
    Returns:
        Agent: GitHub publisher agent with posting tools
    """
    agent_model = get_sub_agent_model()
    
    # Create ADK FunctionTools for publishing
    publisher_tools = [
        FunctionTool(post_github_review),
        FunctionTool(post_review_comment_on_file),
        FunctionTool(update_review_comment)
    ]
    
    github_publisher_agent = Agent(
        name="GitHub_publisher_agent",
        model=agent_model,
        tools=publisher_tools,
        instruction="""You are the GitHub publisher agent responsible for posting reviews to GitHub.

**Your Role:**
- Post code review reports to GitHub pull requests
- Ensure reports are properly formatted for GitHub markdown
- Handle errors gracefully if posting fails

**Input Context:**
- Final report: {final_report}
- GitHub context: {github_context}
  - repo: Repository name
  - pr_number: Pull request number
  - head_sha: Commit SHA

**Your Tasks:**

1. **Post Review Report:**
   - Call post_github_review tool
   - This will post final_report to the PR
   - Tool handles formatting for GitHub
   - Tool adds header and footer automatically

2. **Verify Posting:**
   - Check that tool returned success
   - Store review URL in session state
   - Report URL back to user

3. **Handle Errors:**
   - If posting fails, log error clearly
   - User can still access report in artifact storage
   - Don't fail the entire workflow on posting error

**Expected Output Format (JSON):**
{
    "status": "success",
    "review_url": "https://github.com/owner/repo/pull/123#issuecomment-456",
    "pr_number": 123,
    "posted_at": "2024-01-15T10:30:00Z",
    "fallback_message": "Review also available in artifact storage"
}

**Error Handling:**
- If GitHub API fails: Log error, provide artifact storage link
- If rate limited: Report rate limit info
- If authentication fails: Check GITHUB_TOKEN
- Always provide user with access to the review

**Important Notes:**
- You are a SUB-AGENT, not an orchestrator
- Your output_key is "github_review_url"
- You run LAST in GitHubPipeline
- Posting failures should not block report availability
- Report is already saved in artifact storage""",
        output_key="github_review_url"
    )
    
    return github_publisher_agent


# Create agent instance for import by orchestrator
github_publisher_agent = create_github_publisher_agent()
