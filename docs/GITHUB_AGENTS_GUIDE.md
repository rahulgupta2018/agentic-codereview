# GitHub Agents - Usage Guide

## Overview

The GitHub integration is now split into **two separate agents** for better separation of concerns:

### 1. GitHubFetcherAgent 🔍
**Location:** `agent_workspace/orchestrator_agent/sub_agents/github_fetcher_agent/`

**Responsibility:** Fetch PR data from GitHub API

**Output Key:** `github_pr_data`

**Tools:**
- `fetch_github_pr_files` - Fetch all files changed in PR with content
- `get_pr_summary` - Quick summary of fetched data

### 2. GitHubPublisherAgent 📤
**Location:** `agent_workspace/orchestrator_agent/sub_agents/github_publisher_agent/`

**Responsibility:** Post review results back to GitHub PR

**Output Key:** `github_review_url`

**Tools:**
- `post_github_review` - Post complete review as PR comment
- `post_review_comment_on_file` - Post inline comment on specific line
- `update_review_comment` - Update existing comment

---

## Why Two Separate Agents?

### ✅ Benefits of Separation

1. **Single Responsibility Principle**
   - Each agent has one clear job
   - Easier to understand and maintain

2. **Better Error Handling**
   - Fetch failures don't affect publishing logic
   - Publish failures don't affect analysis pipeline

3. **Pipeline Flexibility**
   - Can use fetcher without publisher (e.g., dry-run mode)
   - Can replace publisher with different output methods

4. **Testing & Debugging**
   - Test fetch logic independently
   - Test publish logic with mock data
   - Easier to isolate issues

5. **Clearer Orchestration**
   ```python
   GitHubPipeline = SequentialAgent(
       sub_agents=[
           github_fetcher_agent,    # Start: Fetch data
           planning_agent,          # Middle: Plan analysis
           execution_pipeline,      # Middle: Run analysis
           report_synthesizer,      # Middle: Create report
           github_publisher_agent   # End: Post to GitHub
       ]
   )
   ```

---

## Usage Examples

### Import Agents

```python
# Recommended: Import from specific agent modules
from agent_workspace.orchestrator_agent.sub_agents.github_fetcher_agent import (
    github_fetcher_agent,
    create_github_fetcher_agent
)

from agent_workspace.orchestrator_agent.sub_agents.github_publisher_agent import (
    github_publisher_agent,
    create_github_publisher_agent
)

# Also works: Import from sub_agents package
from agent_workspace.orchestrator_agent.sub_agents import (
    github_fetcher_agent,
    github_publisher_agent
)
```

### Use in GitHubPipeline

```python
from google.adk.agents import SequentialAgent
from agent_workspace.orchestrator_agent.sub_agents import (
    github_fetcher_agent,
    github_publisher_agent
)

# Create GitHubPipeline with separate agents
github_pipeline = SequentialAgent(
    name="GitHubPipeline",
    sub_agents=[
        github_fetcher_agent,    # 1. Fetch PR data
        planning_agent,          # 2. Plan analysis
        execution_pipeline,      # 3. Run analysis (parallel/sequential)
        report_synthesizer,      # 4. Create final report
        github_publisher_agent   # 5. Post to GitHub
    ],
    description="Deterministic pipeline for GitHub PR review"
)
```

### Fetch Only (No Publishing)

```python
# For dry-run or testing
dry_run_pipeline = SequentialAgent(
    name="DryRunPipeline",
    sub_agents=[
        github_fetcher_agent,   # Fetch data
        planning_agent,
        execution_pipeline,
        report_synthesizer      # Stop here - no publishing
    ]
)
```

### Custom Publishing Strategy

```python
# Use fetcher but replace publisher with custom logic
custom_pipeline = SequentialAgent(
    name="CustomPipeline",
    sub_agents=[
        github_fetcher_agent,     # Standard fetch
        planning_agent,
        execution_pipeline,
        report_synthesizer,
        slack_notifier_agent,     # Custom: Post to Slack instead
        email_sender_agent        # Custom: Send via email
    ]
)
```

### Testing Individual Agents

```python
from google.adk.tools.tool_context import ToolContext

# Test fetcher independently
async def test_github_fetcher():
    context = ToolContext(
        state={
            'github_context': {
                'repo': 'owner/repo',
                'pr_number': 123,
                'head_sha': 'abc123'
            }
        }
    )
    
    async for event in github_fetcher_agent.run_async(context):
        print(f"Event: {event}")
    
    # Check results
    pr_data = context.state.get('github_pr_data')
    assert pr_data['status'] == 'success'
    print(f"✅ Fetched {pr_data['total_files']} files")

# Test publisher independently
async def test_github_publisher():
    context = ToolContext(
        state={
            'github_context': {
                'repo': 'owner/repo',
                'pr_number': 123
            },
            'final_report': '# Test Report\n\nThis is a test.'
        }
    )
    
    async for event in github_publisher_agent.run_async(context):
        print(f"Event: {event}")
    
    # Check results
    review_url = context.state.get('github_review_url')
    print(f"✅ Posted review: {review_url}")
```

---

## Agent Details

### GitHubFetcherAgent

**Input (from session state):**
```python
{
    'github_context': {
        'repo': 'owner/repo',
        'pr_number': 123,
        'head_sha': 'abc123'
    }
}
```

**Output (to session state):**
```python
{
    'github_pr_data': {
        'status': 'success',
        'repo_name': 'owner/repo',
        'pr_metadata': {
            'pr_number': 123,
            'title': 'Add feature',
            'state': 'open',
            'additions': 150,
            'deletions': 30,
            # ... more metadata
        },
        'files': [
            {
                'filename': 'src/main.py',
                'status': 'modified',
                'additions': 50,
                'deletions': 10,
                'patch': '...',
                'content': '...',
                'language': 'python'
            }
        ],
        'summary': {
            'total_files': 5,
            'total_additions': 150,
            'total_deletions': 30,
            'languages': {'python': 3, 'javascript': 2}
        }
    }
}
```

### GitHubPublisherAgent

**Input (from session state):**
```python
{
    'github_context': {
        'repo': 'owner/repo',
        'pr_number': 123
    },
    'final_report': '# Code Review Report\n\n...'
}
```

**Output (to session state):**
```python
{
    'github_review_url': 'https://github.com/owner/repo/pull/123#issuecomment-456',
    'github_comment_id': 456
}
```

---

## Configuration

### Environment Variables

```bash
# Required for both agents
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"

# Optional: Rate limiting
export GITHUB_API_RATE_LIMIT="5000"  # requests per hour
```

### Dependencies

```bash
pip install PyGithub
```

---

## Usage in Production Code

```python
from agent_workspace.orchestrator_agent.sub_agents import (
    github_fetcher_agent,
    github_publisher_agent
)

pipeline = SequentialAgent(
    sub_agents=[
        github_fetcher_agent,    # Fetch
        # ... analysis ...
        github_publisher_agent   # Publish
    ]
)
```

---

## Error Handling

### Fetcher Errors

```python
# Session state after fetch error
{
    'github_pr_data': {
        'status': 'error',
        'error_message': 'GitHub API rate limit exceeded',
        'error_type': 'RateLimitExceededException'
    },
    'github_fetch_error': { ... }
}
```

**Handling:**
- Check `status == 'error'` before proceeding
- Can retry with exponential backoff
- Can fall back to manual code submission

### Publisher Errors

```python
# Session state after publish error
{
    'github_review_url': None,
    'github_publish_error': {
        'status': 'error',
        'error_message': 'Authentication failed',
        'error_type': 'UnauthorizedException'
    }
}
```

**Handling:**
- Report is still in artifact storage
- User can manually post review
- Can retry with updated token
- Workflow continues (doesn't fail)

---

## Best Practices

### ✅ Do

- Use separate agents in new orchestration code
- Test fetcher and publisher independently
- Handle errors at each stage
- Log all GitHub API calls
- Check rate limits before calling

### ❌ Don't

- Don't combine fetch and publish in single agent (violates SRP)
- Don't fail workflow if publish fails (report still accessible)
- Don't retry GitHub API calls without exponential backoff
- Don't expose GitHub tokens in logs or session state

---

## See Also

- **Tools:** `tools/github_pr_fetcher.py`, `tools/github_review_publisher.py`
- **Design:** `docs/PHASE_2_REVISED_DESIGN.md` (lines 1287-1475)
- **Tests:** `tests/unit/test_github_agents/`
