"""
GitHub Data Adapter Agent

Purpose: Transform GitHub PR file data into format that analysis tools expect.

This agent solves the data format mismatch problem:
- GitHub Fetcher provides: {filename, content, language, status, ...}
- Analysis Tools expect: tool_context.state["code"], ["language"], ["file_path"]

The adapter extracts files from github_pr_files and prepares them for analysis.
"""

import sys
import logging
from pathlib import Path
from google.adk.agents import Agent

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add project root to Python path for absolute imports
# __file__ is in agent_workspace/orchestrator_agent/sub_agents/github_data_adapter_agent/
# We need to go up 5 levels to reach the project root (agentic-codereview/)
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import centralized model configuration
from util.llm_model import get_sub_agent_model

# Import the adapter tool
from tools.github_data_adapter import prepare_files_for_analysis

# Get the centralized model instance
logger.info("🔧 [github_data_adapter_agent] Initializing GitHub Data Adapter Agent")
agent_model = get_sub_agent_model()
logger.info(f"🔧 [github_data_adapter_agent] Model configured: {agent_model}")

# GitHub Data Adapter Agent
logger.info("🔧 [github_data_adapter_agent] Creating Agent with data transformation tool")
github_data_adapter_agent = Agent(
    name="github_data_adapter_agent",
    model=agent_model,
    description="Transforms GitHub PR file data for analysis tools",
    instruction="""You are a GitHub Data Adapter Agent in a sequential code review pipeline.

**YOUR SINGLE RESPONSIBILITY:**
Transform GitHub PR file data from the fetcher's format into the format that analysis tools expect.

**CONTEXT:**
You run immediately after the GitHub Fetcher Agent and before all analysis agents (Security, Quality, Engineering, Carbon).

The GitHub Fetcher stores PR files in session state as:
```
session.state["github_pr_files"] = [
    {
        "filename": "ChatPanel.tsx",
        "content": "import React...",  ← Full file content
        "language": "typescript",
        "status": "added",
        "additions": 378,
        ...
    },
    ...
]
```

But analysis tools expect data in this format:
```
session.state["code"] = "..."          ← Raw code string
session.state["language"] = "..."      ← Language identifier  
session.state["file_path"] = "..."     ← File path
```

**YOUR TASK:**
1. Call the `prepare_files_for_analysis()` tool
2. The tool will:
   - Read github_pr_files from session state
   - Extract and combine all file contents
   - Set code/language/file_path in session state
   - Return success confirmation

**IMPORTANT:**
- You MUST call prepare_files_for_analysis() immediately
- No analysis or decision-making needed
- Just execute the transformation tool
- After the tool succeeds, your job is done

**EXPECTED OUTPUT:**
After calling the tool, you should see a success response like:
```
{
    "status": "success",
    "files_prepared": 2,
    "total_lines": 1149,
    "primary_language": "multi",
    "message": "✅ Prepared 2 files (1149 lines) for analysis"
}
```

Then respond with a brief confirmation for the next agents.
""".strip(),
    tools=[prepare_files_for_analysis],
)

logger.info("✅ [github_data_adapter_agent] GitHub Data Adapter Agent created successfully")
logger.info(f"🔧 [github_data_adapter_agent] Tools available: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in [prepare_files_for_analysis]]}")