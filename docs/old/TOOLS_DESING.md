# Tools Directory

This directory contains all tool implementations for the ADK Code Review System.

## Overview

Tools are functions wrapped as ADK `FunctionTool` instances and used by agents to interact with external systems or perform specialized analysis.

## Tool Categories

### 1. GitHub Integration Tools

Tools for interacting with GitHub API (fetching PR data, posting reviews).

#### `github_pr_fetcher.py`

**Functions:**
- `fetch_github_pr_files(tool_context)` - Fetch PR files and metadata from GitHub
- `get_pr_summary(tool_context)` - Get summary of PR data from session state

**Dependencies:**
- `PyGithub` library
- `GITHUB_TOKEN` environment variable

**Usage:**
```python
from google.adk.tools import FunctionTool
from tools.github_pr_fetcher import fetch_github_pr_files

github_tool = FunctionTool(
    name="fetch_github_pr_files",
    description="Fetch PR files from GitHub",
    function=fetch_github_pr_files
)

github_agent = Agent(
    name="GitHubAgent",
    model="gemini-2.5-flash",
    tools=[github_tool],
    instruction="Fetch PR data from GitHub",
    output_key="github_pr_data"
)
```

**Output Format:**
```json
{
    "status": "success",
    "repo_name": "owner/repo",
    "pr_metadata": {
        "pr_number": 123,
        "title": "Add feature",
        "state": "open",
        "additions": 150,
        "deletions": 30
    },
    "files": [
        {
            "filename": "src/main.py",
            "status": "modified",
            "additions": 50,
            "deletions": 10,
            "patch": "...",
            "content": "...",
            "language": "python"
        }
    ],
    "summary": {
        "total_files": 5,
        "languages": {"python": 3, "javascript": 2}
    }
}
```

#### `github_review_publisher.py`

**Functions:**
- `post_github_review(tool_context)` - Post review comment to PR
- `post_review_comment_on_file(tool_context)` - Post inline comment on specific file/line
- `update_review_comment(tool_context)` - Update existing comment

**Dependencies:**
- `PyGithub` library
- `GITHUB_TOKEN` environment variable

**Usage:**
```python
from tools.github_review_publisher import post_github_review

publisher_tool = FunctionTool(
    name="post_github_review",
    description="Post review to GitHub PR",
    function=post_github_review
)

publisher_agent = Agent(
    name="GitHubPublisher",
    model="gemini-2.5-flash",
    tools=[publisher_tool],
    instruction="Post review report to GitHub",
    output_key="github_review_url"
)
```

**Output Format:**
```json
{
    "status": "success",
    "review_url": "https://github.com/owner/repo/pull/123#issuecomment-456",
    "comment_id": 456,
    "posted_at": "2024-01-15T10:30:00Z"
}
```

### 2. Security Analysis Tools

#### `security_vulnerability_scanner.py`

Scans code for security vulnerabilities (SQL injection, XSS, CSRF, etc.).

**Function:** `scan_security_vulnerabilities(tool_context)`

### 3. Code Quality Tools

#### `complexity_analyzer_tool.py`

Analyzes code complexity (cyclomatic complexity, cognitive complexity).

**Function:** `analyze_complexity(tool_context)`

#### `static_analyzer_tool.py`

Runs static analysis on code (linting, type checking).

**Function:** `run_static_analysis(tool_context)`

### 4. Engineering Practices Tools

#### `engineering_practices_evaluator.py`

Evaluates code against best practices (SOLID, design patterns, testing).

**Function:** `evaluate_engineering_practices(tool_context)`

### 5. Carbon Footprint Tools

#### `carbon_footprint_analyzer.py`

Analyzes computational efficiency and environmental impact.

**Function:** `analyze_carbon_footprint(tool_context)`

## Tool Implementation Pattern

All tools follow this consistent pattern:

```python
"""
Tool description.
"""

import time
import logging
from typing import Dict, Any
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


def tool_function(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Tool function documentation.
    
    Args:
        tool_context: ADK ToolContext containing session state and parameters
        
    Returns:
        dict: Tool result with status, data, and metadata
    """
    execution_start = time.time()
    
    try:
        # Get inputs from session state
        input_data = tool_context.state.get('input_key', '')
        
        # Check parameters if not in state
        if not input_data and hasattr(tool_context, 'parameters'):
            params = getattr(tool_context, 'parameters', {})
            input_data = params.get('input_key', '')
        
        if not input_data:
            return {
                'status': 'error',
                'error_message': 'Missing required input',
                'tool_name': 'tool_function'
            }
        
        # Perform tool operation
        result = perform_operation(input_data)
        
        # Build result
        output = {
            'status': 'success',
            'tool_name': 'tool_function',
            'result': result,
            'timestamp': time.time()
        }
        
        execution_time = time.time() - execution_start
        output['execution_time_seconds'] = execution_time
        
        # Store in session state
        tool_context.state['output_key'] = output
        
        # Update progress
        analysis_progress = tool_context.state.get('analysis_progress', {})
        analysis_progress['tool_completed'] = True
        tool_context.state['analysis_progress'] = analysis_progress
        
        logger.info(f"✅ Tool completed successfully")
        
        return output
        
    except Exception as e:
        execution_time = time.time() - execution_start
        error_result = {
            'status': 'error',
            'tool_name': 'tool_function',
            'error_message': str(e),
            'error_type': type(e).__name__,
            'execution_time_seconds': execution_time
        }
        
        logger.error(f"❌ Tool error: {e}")
        tool_context.state['tool_error'] = error_result
        return error_result
```

## Tool Context Access

Tools receive `tool_context: ToolContext` which provides:

1. **Session State:** `tool_context.state`
   - Read/write session state variables
   - Access data from previous agents

2. **Parameters:** `tool_context.parameters` (if provided)
   - Direct function parameters
   - Used for explicit tool calls

3. **Configuration:** `tool_context.config`
   - Tool-specific configuration
   - Runtime settings

## Error Handling

All tools should:

1. Return structured error results (don't raise exceptions)
2. Log errors with appropriate severity
3. Store errors in session state for visibility
4. Provide actionable error messages
5. Track execution time even on failure

## Testing Tools

To test a tool independently:

```python
from google.adk.tools.tool_context import ToolContext
from tools.github_pr_fetcher import fetch_github_pr_files

# Create test context
test_context = ToolContext(
    state={
        'github_context': {
            'repo': 'owner/repo',
            'pr_number': 123,
            'head_sha': 'abc123'
        }
    }
)

# Run tool
result = fetch_github_pr_files(test_context)

print(f"Status: {result['status']}")
if result['status'] == 'success':
    print(f"Fetched {result['total_files']} files")
else:
    print(f"Error: {result['error_message']}")
```

## Environment Variables

Required environment variables:

```bash
# GitHub Integration
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"

# Optional: API Rate Limiting
export GITHUB_API_RATE_LIMIT="5000"  # requests per hour
```

## Adding New Tools

1. Create new file in `tools/` directory
2. Follow the tool implementation pattern
3. Add to `tools/__init__.py` exports
4. Document in this README
5. Write tests in `tests/unit/test_tools/`
6. Update agent configurations to use the tool

## Dependencies

Install required packages:

```bash
pip install PyGithub  # For GitHub integration
pip install bandit    # For security scanning
pip install radon     # For complexity analysis
pip install pylint    # For static analysis
```

See `requirements.txt` for complete dependency list.
