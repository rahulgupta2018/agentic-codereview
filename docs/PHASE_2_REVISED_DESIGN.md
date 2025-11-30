# Phase 2: Deterministic Workflow Orchestration with Decision Frameworks

**Status:** Design Review  
**Version:** 3.0  
**Date:** November 28, 2025  
**Prerequisites:** Phase 1 MVP completed

---

## 📋 Executive Summary

**Framework:** Google ADK (Agent Development Kit) - Python SDK  
**GitHub Integration:** PyGithub library OR direct HTTP calls (no Microsoft Agent Framework)

Based on Google ADK best practices, Phase 2 **abandons custom orchestration logic** in favor of **deterministic ADK workflow patterns** using:

- **SequentialAgent** for ordered pipeline execution
- **Decision Frameworks** for request source routing (API vs Web UI)
- **PlanReActPlanner** for dynamic intent analysis and agent selection
- **ParallelAgent** for efficient multi-agent execution (where appropriate)
- **No custom orchestration code** - pure ADK patterns

### GitHub Integration Options (All work with Google ADK):

1. **PyGithub Library** ✅ Recommended
   - `pip install PyGithub`
   - Wrap as `FunctionTool` for agents
   - Handles auth, pagination, rate limiting

2. **Direct HTTP with httpx/requests** ✅ Simple
   - No extra dependencies
   - Full control over API calls
   - Good for MVP

3. **GitHub MCP Server** ✅ Advanced
   - Model Context Protocol integration
   - Auto-discovers GitHub tools
   - Good for complex workflows

### Key Design Principles

1. ✅ **Deterministic Workflows** - Predictable, ordered execution
2. ✅ **ADK Native Patterns** - Use SequentialAgent, ParallelAgent, Decision Frameworks
3. ✅ **No Custom Orchestration** - Eliminate custom if/elif logic
4. ✅ **Plan-ReAct for Intelligence** - LLM-driven agent selection
5. ✅ **GitHub Integration Ready** - Designed for webhook → queue → worker pattern

### Quick Start: GitHub Integration with Google ADK

```bash
# Install dependencies
pip install google-adk PyGithub httpx

# Set environment variables
export GITHUB_TOKEN="ghp_your_token_here"
export GOOGLE_API_KEY="your_gemini_key_here"
```

```python
# Minimal example: GitHub PR review agent with Google ADK
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from github import Github

# Setup GitHub client
gh = Github(os.getenv("GITHUB_TOKEN"))

def fetch_pr_files(repo: str, pr_number: int) -> dict:
    """Fetch PR files using PyGithub."""
    repo_obj = gh.get_repo(repo)
    pr = repo_obj.get_pull(pr_number)
    return {
        "files": [{"filename": f.filename, "patch": f.patch} 
                  for f in pr.get_files()]
    }

# Create agent with GitHub tool
agent = Agent(
    name="GitHubReviewer",
    model="gemini-2.5-flash",
    tools=[FunctionTool(
        name="fetch_pr_files",
        description="Fetch PR files from GitHub",
        function=fetch_pr_files
    )],
    instruction="Use fetch_pr_files to get PR data and review the code"
)
```

**That's it!** No Microsoft Agent Framework needed. Pure Google ADK + PyGithub.

---

## 📚 ADK Best Practices Review

### Workflow Patterns (Source: ADK Training)

```
Sequential (Assembly Line): One after another
  Step 1 → Step 2 → Step 3 → Step 4
  Use: Pipelines, dependencies, order matters

Parallel (Fan-out/Gather): Multiple tasks at once
  ┌─── Task A ───┐
  ├─── Task B ───┤ → Merge Results
  └─── Task C ───┘
  Use: Independent tasks, speed critical

Loop (Iterative Refinement): Repeat until good enough
  ┌──────────────────┐
  │  ┌──► Critic ───┐│
  │  └─── Refiner ◄─┘│
  └──────────────────┘
  Use: Quality improvement, retry logic
```

### Decision Framework Pattern

```python
# Routing based on request source
def route_by_source(context, result):
    source = result.get('source', '')
    if source == 'github_webhook':
        return 'github_pipeline'
    elif source == 'web_ui':
        return 'classifier_agent'
    else:
        return 'general_query_handler'

routing_agent = Agent(
    name="router",
    model="gemini-2.5-flash",
    instruction="Determine request source and route accordingly"
)

workflow = SequentialAgent(
    sub_agents=[routing_agent],
    dynamic_agents={
        'github_pipeline': github_workflow,
        'classifier_agent': web_workflow,
        'general_query_handler': general_handler
    },
    routing_function=route_by_source
)
```

### Plan-ReAct Pattern for Agent Selection

```python
# Planner determines which agents to employ
planning_agent = Agent(
    name="planner",
    model="gemini-2.5-flash",
    planner=PlanReActPlanner(),
    tools=[security_tool, quality_tool, practices_tool],
    instruction="""Analyze code review request and determine:
    - Which analysis types are needed
    - What order to execute them
    - Whether parallel or sequential execution"""
)
```

---

## 🏗️ Revised Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  GitHub Webhook (Entry Point)               │
│         POST /api/webhook/github (PR opened/updated)        │
└────────────────────┬────────────────────────────────────────┘
                     │ <100ms
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   Cloud Run #1 - API Service                │
│   • Validates HMAC signature                                │
│   • Enriches with repo metadata                             │
│   • Publishes to Cloud Pub/Sub                              │
└────────────────────┬────────────────────────────────────────┘
                     │ Asynchronous (no waiting)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      Cloud Pub/Sub Queue                    │
│   • Decouples webhook from processing                       │
│   • Handles multiple concurrent PRs                         │
│   • Rate limiting and retry logic                           │
└────────────────────┬────────────────────────────────────────┘
                     │ Push to worker (when available)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Cloud Run #2- Worker Service (ADK)             │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         RootOrchestrator (SequentialAgent)           │   │
│  │                                                      │   │
│  │  Step 1: SourceDetectorAgent                         │   │
│  │    ↓ Determines source (github_webhook vs web_ui)    │   │
│  │                                                      │   │
│  │  Step 2: Conditional Routing (Decision Framework)    │   │
│  │    ├─ If github_webhook → GitHubPipeline             │   │
│  │    └─ If web_ui → ClassifierAgent                    │   │
│  │                                                      │   │
│  │  Step 3: PlanningAgent (PlanReActPlanner)            │   │
│  │    ↓ Determines which agents + execution strategy    │   │
│  │                                                      │   │
│  │  Step 4: ExecutionPipeline                           │   │
│  │    ├─ Sequential: For dependent analyses             │   │
│  │    └─ Parallel: For independent analyses             │   │
│  │                                                      │   │
│  │  Step 5: ReportSynthesizer                           │   │
│  │    ↓ Consolidates results into markdown report       │   │
│  │                                                      │   │
│  │  Step 6: GitHubPublisher (if github_webhook)         │   │
│  │    ↓ Posts review comments to GitHub PR              │   │
│  │                                                      │   │
│  │  Step 7: MessageAcknowledger                         │   │
│  │    ↓ ACK Pub/Sub message (removes from queue)        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Components Breakdown

#### 1. SourceDetectorAgent (Decision Framework)

**Purpose:** Determine request source (GitHub webhook vs Web UI)

```python
source_detector = Agent(
    name="SourceDetector",
    model="gemini-2.5-flash",
    instruction="""Analyze the request context and determine the source.

Input Context:
- Request metadata: {request_metadata}
- User message: {user_message}
- Session state: {session_state}

Determine:
1. Is this from GitHub webhook? (Look for: pr_number, repo, head_sha)
2. Is this from Web UI? (Look for: interactive user message)
3. Other: General query or unknown source

Output JSON:
{
    "source": "github_webhook" | "web_ui" | "general_query",
    "confidence": 0.0-1.0,
    "reasoning": "Explanation",
    "github_context": {
        "repo": "owner/repo",
        "pr_number": 123,
        "head_sha": "abc123"
    } // Only if github_webhook
}""",
    output_key="source_detection"
)
```

#### 2. GitHubPipeline (SequentialAgent)

**Purpose:** Handle GitHub webhook requests with deterministic flow

```python
github_pipeline = SequentialAgent(
    name="GitHubPipeline",
    sub_agents=[
        github_agent,      # Fetch PR files and metadata
        classifier_agent,  # Classify changes (optional, could skip)
        # ... continues to planning
    ],
    description="Deterministic pipeline for GitHub PR review"
)
```

**github_agent** fetches PR data:

```python
# Three options for GitHub API integration with Google ADK:

# OPTION 1: Direct HTTP calls with requests/httpx (Simplest)
# ✅ Recommended for straightforward API calls
# No additional dependencies needed

import httpx

github_agent = Agent(
    name="GitHubAgent",
    model="gemini-2.5-flash",
    instruction="""Fetch PR files and metadata from GitHub.

GitHub Context: {source_detection.github_context}

I will help you make GitHub API calls. Based on the PR information, 
I'll construct the appropriate API requests and parse the responses.

You should ask me to:
1. Fetch PR files from: GET /repos/{owner}/{repo}/pulls/{pr_number}/files
2. Extract code changes (diff, additions, deletions)
3. Parse file paths, languages, and change statistics
4. Return structured data

Error Handling:
- If API fails, return error with details
- If no files changed, return empty list
""",
    output_key="github_pr_data"
)

# Then in your orchestrator or a custom tool:
async def fetch_github_pr_files(repo: str, pr_number: int, github_token: str):
    """Fetch PR files using direct HTTP calls."""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


# OPTION 2: PyGithub library (More features)
# ✅ Recommended if you need advanced GitHub features
# Install: pip install PyGithub

from github import Github
from google.adk.tools import FunctionTool

def create_github_tools(github_token: str):
    """Create GitHub tools using PyGithub."""
    gh = Github(github_token)
    
    def fetch_pr_files(repo_name: str, pr_number: int) -> dict:
        """Fetch PR files and metadata."""
        repo = gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        files = []
        for file in pr.get_files():
            files.append({
                "filename": file.filename,
                "status": file.status,
                "additions": file.additions,
                "deletions": file.deletions,
                "changes": file.changes,
                "patch": file.patch  # The actual diff
            })
        
        return {
            "pr_number": pr.number,
            "title": pr.title,
            "body": pr.body,
            "state": pr.state,
            "files": files
        }
    
    def post_review_comment(repo_name: str, pr_number: int, body: str) -> dict:
        """Post review comment to PR."""
        repo = gh.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        review = pr.create_review(body=body, event="COMMENT")
        
        return {
            "review_id": review.id,
            "url": review.html_url
        }
    
    return [
        FunctionTool(
            name="fetch_github_pr_files",
            description="Fetch PR files and metadata from GitHub",
            function=fetch_pr_files
        ),
        FunctionTool(
            name="post_github_review",
            description="Post review comment to GitHub PR",
            function=post_review_comment
        )
    ]

github_tools = create_github_tools(os.getenv("GITHUB_TOKEN"))

github_agent = Agent(
    name="GitHubAgent",
    model="gemini-2.5-flash",
    tools=github_tools,
    instruction="""Fetch PR files and metadata from GitHub.

GitHub Context: {source_detection.github_context}

Use the fetch_github_pr_files tool to get PR data.

Tasks:
1. Call fetch_github_pr_files with repo and pr_number
2. Extract code changes from the response
3. Store in session state as github_pr_data

Error Handling:
- If tool call fails, return error with details
- If no files changed, return empty analysis
""",
    output_key="github_pr_data"
)


# OPTION 3: GitHub MCP Server (Most flexible)
# ✅ Recommended for complex GitHub workflows with multiple operations
# Uses Model Context Protocol for standardized GitHub access

from google.adk.mcp import MCPClient

# Configure GitHub MCP server (runs as separate process)
# See: https://github.com/modelcontextprotocol/servers/tree/main/src/github

github_mcp = MCPClient(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-github"],
    env={"GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_TOKEN")}
)

github_agent = Agent(
    name="GitHubAgent",
    model="gemini-2.5-flash",
    tools=[github_mcp],  # MCP provides auto-discovered tools
    instruction="""Fetch PR files and metadata from GitHub using MCP tools.

GitHub Context: {source_detection.github_context}

Available MCP tools will include:
- get_pull_request: Get PR details
- list_pull_request_files: Get files changed in PR
- create_pull_request_review: Post review to PR

Tasks:
1. Use list_pull_request_files to get PR files
2. Extract code changes from the response
3. Store in session state as github_pr_data

Error Handling:
- If MCP tool fails, return error with details
- If no files changed, return empty analysis
""",
    output_key="github_pr_data"
)
```

**Recommendation for Google ADK:**

1. **For MVP/Simple Integration**: Use **Option 1** (direct HTTP with httpx)
   - Simple, no extra dependencies
   - Full control over API calls
   - Easy to debug

2. **For Production/Rich Features**: Use **Option 2** (PyGithub)
   - Well-maintained library with 6k+ stars
   - Handles pagination, rate limiting, authentication
   - Type-safe with good IDE support

3. **For Advanced Workflows**: Use **Option 3** (GitHub MCP)
   - Standardized interface for LLM-GitHub interaction
   - Auto-discovers available GitHub operations
   - Best for complex multi-step GitHub workflows

**None of these require Microsoft Agent Framework** - all work with **Google ADK** natively!

#### 3. ClassifierAgent (for Web UI path)

**Purpose:** Classify user intent when code is submitted via Web UI

```python
classifier_agent = Agent(
    name="ClassifierAgent",
    model="gemini-2.5-flash",
    instruction="""Classify user's code review request.

User Message: {user_message}

Analyze:
1. What type of review? (security, quality, practices, performance, comprehensive)
2. Is code present in message?
3. Specific focus areas mentioned?

Output JSON:
{
    "type": "code_review_security" | "code_review_quality" | "code_review_comprehensive",
    "has_code": true/false,
    "focus_areas": ["security", "authentication"],
    "confidence": 0.0-1.0
}""",
    output_key="classification"
)
```

#### 4. PlanningAgent (PlanReActPlanner)

**Purpose:** Intelligently determine which agents to execute and in what manner

```python
planning_agent = Agent(
    name="PlanningAgent",
    model="gemini-2.5-flash",
    planner=PlanReActPlanner(),
    tools=[
        # Proxy tools for agent selection
        FunctionTool(
            name="select_security_analysis",
            description="""Select Security Agent to analyze:
            - Vulnerabilities (SQL injection, XSS, CSRF)
            - Authentication/authorization issues
            - Input validation problems
            - Cryptography weaknesses
            
            Use when: Security concerns, vulnerabilities, exploits mentioned""",
            function=lambda: {"agent": "security"}
        ),
        FunctionTool(
            name="select_quality_analysis",
            description="""Select Code Quality Agent to analyze:
            - Cyclomatic complexity
            - Code maintainability
            - Code smells and anti-patterns
            - Duplication detection
            
            Use when: Quality, complexity, maintainability mentioned""",
            function=lambda: {"agent": "code_quality"}
        ),
        FunctionTool(
            name="select_practices_analysis",
            description="""Select Engineering Practices Agent to analyze:
            - SOLID principles compliance
            - Design pattern usage
            - Testing strategy
            - Documentation quality
            
            Use when: Best practices, SOLID, patterns mentioned""",
            function=lambda: {"agent": "engineering"}
        ),
        FunctionTool(
            name="select_carbon_analysis",
            description="""Select Carbon Emission Agent to analyze:
            - Computational efficiency
            - Algorithm optimization
            - Resource usage
            
            Use when: Performance, efficiency, optimization mentioned""",
            function=lambda: {"agent": "carbon"}
        ),
    ],
    instruction="""You are a code review planning agent.

Context:
- Source: {source_detection.source}
- GitHub Data: {github_pr_data}  // If from GitHub
- Classification: {classification}  // If from Web UI
- User Message: {user_message}

Your Task:
Analyze the request and intelligently select which analysis agents to employ.

<PLANNING>
1. Understand the request intent
2. Identify which analysis types are needed
3. Determine execution strategy (parallel vs sequential)
4. Consider dependencies between analyses
</PLANNING>

<REASONING>
- If user asks "review this code" with no specifics → SELECT ALL agents (comprehensive)
- If user mentions specific area (e.g., "is this secure?") → SELECT ONLY relevant agents
- If multiple areas mentioned → SELECT MULTIPLE agents
- Consider whether analyses are independent (parallel) or dependent (sequential)
</REASONING>

<ACTION>
Call the appropriate select_*_analysis tools.
You can call multiple tools.
</ACTION>

<FINAL_ANSWER>
Output JSON:
{
    "selected_agents": ["security", "code_quality"],
    "execution_mode": "parallel" | "sequential",
    "reasoning": "Explanation of why these agents were selected",
    "estimated_duration": "2-5 minutes"
}
</FINAL_ANSWER>""",
    output_key="execution_plan"
)
```

#### 5. ExecutionPipeline (Dynamic: ParallelAgent or SequentialAgent)

**Purpose:** Execute selected agents based on planning decision

```python
def create_execution_pipeline(plan: dict) -> BaseAgent:
    """Create parallel or sequential pipeline based on plan."""
    
    agent_map = {
        "security": security_agent,
        "code_quality": code_quality_agent,
        "engineering": engineering_practices_agent,
        "carbon": carbon_emission_agent,
    }
    
    selected_agents = [agent_map[name] for name in plan["selected_agents"]]
    
    if plan["execution_mode"] == "parallel":
        return ParallelAgent(
            name="ParallelExecution",
            sub_agents=selected_agents,
            description="Execute independent analyses in parallel"
        )
    else:
        return SequentialAgent(
            name="SequentialExecution",
            sub_agents=selected_agents,
            description="Execute dependent analyses in sequence"
        )

# In main orchestrator
execution_pipeline = create_execution_pipeline(
    ctx.session.state["execution_plan"]
)

async for event in execution_pipeline.run_async(ctx):
    yield event
```

#### 6. ReportSynthesizer (LlmAgent)

**Purpose:** Consolidate results into final markdown report

```python
report_synthesizer = Agent(
    name="ReportSynthesizer",
    model="gemini-2.5-flash",
    instruction="""Synthesize comprehensive code review report.

Available Results:
- Security: {security_results}
- Quality: {code_quality_results}
- Practices: {engineering_results}
- Carbon: {carbon_results}

Execution Plan:
- Agents Run: {execution_plan.selected_agents}
- Reasoning: {execution_plan.reasoning}

Generate Markdown Report:

# Code Review Report

**Analysis ID:** {analysis_id}
**Date:** {timestamp}
**Source:** {source_detection.source}

## 🧠 Analysis Strategy

**Agents Selected:** {agents}
**Execution Mode:** {execution_mode}
**Reasoning:** {reasoning}

## 📊 Executive Summary

[Aggregate findings by severity]

## 🔍 Detailed Findings

[Only include sections for agents that ran]

### 🔒 Security Analysis
[If security_results exists]

### 📊 Code Quality
[If code_quality_results exists]

### ⚙️ Engineering Practices
[If engineering_results exists]

### 🌱 Carbon Footprint
[If carbon_results exists]

## 💡 Recommendations

[Prioritized action items]

---
*Powered by ADK Multi-Agent Code Review System*
""",
    output_key="final_report"
)
```

#### 7. GitHubPublisher (LlmAgent with GitHub Tools)

**Purpose:** Post review comments back to GitHub PR

```python
# Using the same GitHub integration approach as GitHubAgent

# OPTION 1: Direct HTTP (Simplest)
async def post_github_review(repo: str, pr_number: int, body: str, github_token: str):
    """Post review comment using direct HTTP."""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    payload = {
        "body": body,
        "event": "COMMENT"  # Options: COMMENT, APPROVE, REQUEST_CHANGES
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result["html_url"]


# OPTION 2: PyGithub (Recommended)
# Uses the tools created in GitHubAgent section

github_publisher = Agent(
    name="GitHubPublisher",
    model="gemini-2.5-flash",
    tools=github_tools,  # Same tools from GitHubAgent
    instruction="""Post code review results to GitHub PR.

Report: {final_report}
GitHub Context: {source_detection.github_context}

Tasks:
1. Format report for GitHub markdown (already formatted)
2. Use post_github_review tool to post comment
3. Pass repo, pr_number, and report body
4. Store returned review URL in session state

Error Handling:
- If tool call fails, log error but don't fail the workflow
- User can manually view report in artifact storage
""",
    output_key="github_review_url"
)


# OPTION 3: GitHub MCP (Advanced)
# Uses the same MCP client from GitHubAgent

github_publisher = Agent(
    name="GitHubPublisher",
    model="gemini-2.5-flash",
    tools=[github_mcp],  # Same MCP client from GitHubAgent
    instruction="""Post code review results to GitHub PR using MCP.

Report: {final_report}
GitHub Context: {source_detection.github_context}

Tasks:
1. Format report for GitHub markdown (already formatted)
2. Use create_pull_request_review MCP tool
3. Set event type to "COMMENT"
4. Store returned review URL in session state

Error Handling:
- If MCP tool fails, log error but don't fail the workflow
- User can manually view report in artifact storage
""",
    output_key="github_review_url"
)
```

**Summary of Google ADK GitHub Integration:**

| Approach | Pros | Cons | Best For |
|----------|------|------|----------|
| **Direct HTTP (httpx)** | Simple, no deps, full control | More code, manual error handling | MVP, simple workflows |
| **PyGithub Library** | Feature-rich, well-maintained | Extra dependency | Production, most use cases |
| **GitHub MCP** | Standardized, auto-discovery | Requires Node.js runtime | Complex GitHub workflows |

**All three work perfectly with Google ADK!** No Microsoft Agent Framework needed.

#### 8. MessageAcknowledger (Pub/Sub Cleanup)

**Purpose:** Acknowledge Pub/Sub message to remove from queue and prevent reprocessing

```python
# This happens at the FastAPI endpoint level, not as an ADK agent

@app.post("/process")
async def process_code_review(request: Request):
    """Process code review from Pub/Sub push subscription."""
    
    envelope = await request.json()
    message_data = base64.b64decode(envelope["message"]["data"])
    payload = json.loads(message_data)
    
    try:
        # Run ADK orchestrator (Steps 1-6)
        async for event in orchestrator.run(...):
            pass
        
        # Step 7: Success - Return 200 OK to acknowledge message
        # Pub/Sub will remove message from queue
        logging.info(f"✅ Completed PR #{payload['pr_number']} - ACKing message")
        return {"status": "success"}  # ← This ACKs the message
        
    except Exception as e:
        # Error - Return 500 to NACK message
        # Pub/Sub will retry (up to max_delivery_attempts)
        logging.error(f"❌ Error processing PR #{payload['pr_number']}: {e}")
        raise HTTPException(status_code=500, detail=str(e))  # ← This NACKs
```

**How Pub/Sub Acknowledgment Works:**

1. **Success (HTTP 200-299):** Message is **acknowledged** and removed from queue
2. **Failure (HTTP 500-599):** Message is **not acknowledged** and will be retried
3. **Timeout (no response):** Message is **not acknowledged** and will be retried

**Configuration (Pub/Sub Subscription):**
```bash
gcloud pubsub subscriptions create code-review-worker-sub \
  --topic=code-review-queue \
  --push-endpoint=https://worker.example.com/process \
  --ack-deadline=600 \        # 10 minutes (code review can take time)
  --max-delivery-attempts=3 \  # Retry up to 3 times on failure
  --dead-letter-topic=code-review-dlq  # Failed messages go here
```

**Error Scenarios:**

| Scenario | HTTP Code | Pub/Sub Action | Explanation |
|----------|-----------|----------------|-------------|
| Success | 200 | ACK (remove from queue) | Review completed successfully |
| GitHub API failure (non-critical) | 200 | ACK (remove from queue) | Review done, GitHub post failed but logged |
| ADK orchestrator crash | 500 | NACK (retry) | Transient error, worth retrying |
| Invalid payload | 200 | ACK (remove from queue) | Permanent error, no point retrying |
| Timeout (>10min) | No response | NACK (retry) | Worker didn't respond in time |

**Why This Matters:**

✅ **Prevents Duplicate Reviews:**
- Without ACK, same PR would be reviewed multiple times
- Wastes LLM tokens and GitHub API calls

✅ **Enables Retries:**
- Transient errors (network issues) automatically retry
- Permanent errors (bad data) don't retry forever

✅ **Dead Letter Queue:**
- After 3 failed attempts, message goes to DLQ
- Engineers can investigate and manually reprocess

---

## 🔄 Complete Orchestrator Implementation

### RootOrchestrator (SequentialAgent with Dynamic Routing)

```python
# agent_workspace/orchestrator_agent/agent.py

from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.adk.planners import PlanReActPlanner
from google.adk.tools import FunctionTool, OpenAPIToolset
from typing import Dict, Any

class RootOrchestrator:
    """
    Phase 2: ADK-native orchestrator using deterministic workflows.
    
    Pattern: SequentialAgent with conditional routing via Decision Framework
    """
    
    def __init__(self):
        # Step 1: Source Detection
        self.source_detector = self._create_source_detector()
        
        # Step 2a: GitHub Pipeline (if webhook)
        self.github_agent = self._create_github_agent()
        
        # Step 2b: Classifier (if web UI)
        self.classifier = self._create_classifier()
        
        # Step 3: Planning Agent (Plan-ReAct)
        self.planning_agent = self._create_planning_agent()
        
        # Step 4: Sub-agents (same as Phase 1)
        self.security_agent = ...  # Reuse Phase 1
        self.code_quality_agent = ...
        self.engineering_agent = ...
        self.carbon_agent = ...
        
        # Step 5: Report Synthesizer
        self.report_synthesizer = self._create_report_synthesizer()
        
        # Step 6: GitHub Publisher
        self.github_publisher = self._create_github_publisher()
        
        # Orchestrator: SequentialAgent with routing
        self.root_agent = self._create_root_workflow()
    
    def _create_source_detector(self) -> Agent:
        """Create source detection agent."""
        return Agent(
            name="SourceDetector",
            model="gemini-2.5-flash",
            instruction="""[Source detection instruction from above]""",
            output_key="source_detection"
        )
    
    def _create_github_agent(self) -> Agent:
        """Create GitHub data fetching agent."""
        github_spec = self._load_github_openapi_spec()
        github_toolset = OpenAPIToolset(spec_dict=github_spec)
        
        return Agent(
            name="GitHubAgent",
            model="gemini-2.5-flash",
            tools=[github_toolset],
            instruction="""[GitHub agent instruction from above]""",
            output_key="github_pr_data"
        )
    
    def _create_classifier(self) -> Agent:
        """Create web UI classifier agent."""
        return Agent(
            name="ClassifierAgent",
            model="gemini-2.5-flash",
            instruction="""[Classifier instruction from above]""",
            output_key="classification"
        )
    
    def _create_planning_agent(self) -> Agent:
        """Create planning agent with Plan-ReAct."""
        return Agent(
            name="PlanningAgent",
            model="gemini-2.5-flash",
            planner=PlanReActPlanner(),
            tools=[
                FunctionTool(
                    name="select_security_analysis",
                    description="Select Security Agent...",
                    function=lambda: {"agent": "security"}
                ),
                # ... other proxy tools
            ],
            instruction="""[Planning instruction from above]""",
            output_key="execution_plan"
        )
    
    def _create_report_synthesizer(self) -> Agent:
        """Create report synthesizer."""
        return Agent(
            name="ReportSynthesizer",
            model="gemini-2.5-flash",
            instruction="""[Report synthesizer instruction from above]""",
            output_key="final_report"
        )
    
    def _create_github_publisher(self) -> Agent:
        """Create GitHub publisher."""
        github_spec = self._load_github_openapi_spec()
        github_toolset = OpenAPIToolset(spec_dict=github_spec)
        
        return Agent(
            name="GitHubPublisher",
            model="gemini-2.5-flash",
            tools=[github_toolset],
            instruction="""[GitHub publisher instruction from above]""",
            output_key="github_review_url"
        )
    
    def _create_root_workflow(self) -> SequentialAgent:
        """Create main orchestration workflow."""
        
        # Define routing function for source-based branching
        def route_by_source(context, result):
            source = result.get('source', 'web_ui')
            if source == 'github_webhook':
                return 'github_pipeline'
            elif source == 'web_ui':
                return 'web_pipeline'
            else:
                return 'general_query'
        
        # GitHub-specific pipeline
        github_pipeline = SequentialAgent(
            name="GitHubPipeline",
            sub_agents=[
                self.github_agent,      # Fetch PR data
                self.planning_agent,    # Plan analysis
                # Execution happens dynamically
                self.report_synthesizer,
                self.github_publisher
            ]
        )
        
        # Web UI pipeline
        web_pipeline = SequentialAgent(
            name="WebPipeline",
            sub_agents=[
                self.classifier,
                self.planning_agent,
                # Execution happens dynamically
                self.report_synthesizer
            ]
        )
        
        # Root orchestrator with conditional routing
        return SequentialAgent(
            name="RootOrchestrator",
            sub_agents=[self.source_detector],
            dynamic_agents={
                'github_pipeline': github_pipeline,
                'web_pipeline': web_pipeline,
            },
            routing_function=route_by_source
        )
    
    async def run(self, user_message: str, request_metadata: dict):
        """Run the orchestration workflow."""
        from google.adk.runners import Runner
        
        runner = Runner(agent=self.root_agent)
        
        async for event in runner.run_async(
            user_id="system",
            session_id=f"session_{request_metadata.get('pr_number', 'web')}",
            new_message=user_message,
            app_state={
                "request_metadata": request_metadata
            }
        ):
            # Handle events
            if event.author == "ExecutionPipeline":
                # Dynamic execution based on plan
                plan = event.context.session.state.get("execution_plan", {})
                pipeline = self._create_execution_pipeline(plan)
                
                async for exec_event in pipeline.run_async(event.context):
                    yield exec_event
            else:
                yield event
    
    def _create_execution_pipeline(self, plan: Dict[str, Any]) -> BaseAgent:
        """Create execution pipeline based on plan."""
        agent_map = {
            "security": self.security_agent,
            "code_quality": self.code_quality_agent,
            "engineering": self.engineering_agent,
            "carbon": self.carbon_agent,
        }
        
        selected = [agent_map[name] for name in plan.get("selected_agents", [])]
        
        if plan.get("execution_mode") == "parallel":
            return ParallelAgent(
                name="ParallelExecution",
                sub_agents=selected
            )
        else:
            return SequentialAgent(
                name="SequentialExecution",
                sub_agents=selected
            )
```

### FastAPI Worker Endpoint (Pub/Sub Integration)

```python
# worker.py - Cloud Run Worker Service entry point

from fastapi import FastAPI, Request, HTTPException
from google.cloud import logging as cloud_logging
import base64
import json
import logging

app = FastAPI()
orchestrator = RootOrchestrator()

# Setup Cloud Logging
cloud_logging.Client().setup_logging()
logger = logging.getLogger(__name__)

@app.post("/process")
async def process_code_review(request: Request):
    """
    Process code review from Pub/Sub push subscription.
    
    Pub/Sub Acknowledgment:
    - Return 200-299: Message is ACKed (removed from queue)
    - Return 500-599: Message is NACKed (will be retried)
    - No response: Message is NACKed after ack_deadline (600s)
    """
    
    # 1. Parse Pub/Sub message
    try:
        envelope = await request.json()
        message_data = base64.b64decode(envelope["message"]["data"])
        payload = json.loads(message_data)
        
        pr_number = payload.get("pr_number")
        repo = payload.get("repo")
        
        logger.info(f"📥 Received Pub/Sub message for {repo}#{pr_number}")
        
    except Exception as e:
        logger.error(f"❌ Invalid Pub/Sub message format: {e}")
        # Return 200 to ACK - bad message, no point retrying
        return {"status": "rejected", "reason": "Invalid message format"}
    
    # 2. Run ADK orchestrator (Steps 1-6)
    try:
        logger.info(f"🚀 Starting code review for {repo}#{pr_number}")
        
        async for event in orchestrator.run(
            user_message="",  # GitHub webhook, no user message
            request_metadata={
                "source": "github_webhook",
                "repo": repo,
                "pr_number": pr_number,
                "head_sha": payload.get("head_sha"),
                "action": payload.get("action")
            }
        ):
            # Log events for monitoring
            if event.turn_complete:
                logger.info(f"✓ Agent {event.author} completed")
        
        logger.info(f"✅ Code review completed for {repo}#{pr_number}")
        
        # Step 7: Return 200 to ACK message (success)
        return {
            "status": "success",
            "pr_number": pr_number,
            "repo": repo
        }
        
    except GitHubAPIError as e:
        # GitHub API failures - Could be transient (rate limit, network)
        logger.error(f"⚠️ GitHub API error for {repo}#{pr_number}: {e}")
        
        if e.status_code == 403:  # Rate limit
            # Retry - might succeed after rate limit resets
            raise HTTPException(status_code=500, detail="GitHub rate limit")
        elif e.status_code == 404:  # PR not found
            # Don't retry - permanent error
            logger.warning(f"PR {repo}#{pr_number} not found, ACKing message")
            return {"status": "skipped", "reason": "PR not found"}
        else:
            # Unknown error - retry
            raise HTTPException(status_code=500, detail=str(e))
    
    except GeminiAPIError as e:
        # Gemini API failures - Usually transient
        logger.error(f"⚠️ Gemini API error for {repo}#{pr_number}: {e}")
        # Retry - might succeed on next attempt
        raise HTTPException(status_code=500, detail="LLM API error")
    
    except Exception as e:
        # Unexpected error
        logger.error(f"❌ Unexpected error for {repo}#{pr_number}: {e}", exc_info=True)
        # Retry - might be transient
        raise HTTPException(status_code=500, detail="Internal error")

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy"}

# Run with: uvicorn worker:app --host 0.0.0.0 --port 8080
```

**Key Points:**

1. **Success Path (200 OK):**
   - Code review completed successfully
   - GitHub review posted
   - Message is **ACKed** and removed from queue
   - Won't be processed again

2. **Transient Errors (500):**
   - API rate limits, network timeouts, temporary LLM issues
   - Message is **NACKed** and will be retried
   - Up to `max_delivery_attempts` (3 times)

3. **Permanent Errors (200 OK):**
   - Invalid message format, PR not found, bad data
   - Message is **ACKed** to remove from queue
   - No point retrying - would fail again

4. **Dead Letter Queue:**
   - After 3 failed retries, message goes to DLQ
   - Engineers can investigate and manually reprocess

---

## 🧪 Testing Strategy

### Unit Tests

```python
@pytest.mark.asyncio
async def test_source_detector_identifies_github_webhook():
    """Test source detector correctly identifies GitHub webhook."""
    detector = create_source_detector()
    
    ctx = create_mock_context(
        user_message="",
        request_metadata={
            "pr_number": 123,
            "repo": "owner/repo",
            "head_sha": "abc123"
        }
    )
    
    async for event in detector.run_async(ctx):
        pass
    
    result = ctx.session.state["source_detection"]
    assert result["source"] == "github_webhook"
    assert result["github_context"]["pr_number"] == 123


@pytest.mark.asyncio
async def test_planning_agent_selects_security_for_security_query():
    """Test planning agent selects security agent for security focus."""
    planner = create_planning_agent()
    
    ctx = create_mock_context(
        user_message="Check if this code has SQL injection vulnerabilities",
        classification={"type": "code_review_security"}
    )
    
    async for event in planner.run_async(ctx):
        pass
    
    plan = ctx.session.state["execution_plan"]
    assert "security" in plan["selected_agents"]
    assert len(plan["selected_agents"]) == 1  # Only security needed
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_e2e_github_webhook_flow():
    """Test end-to-end flow from GitHub webhook to PR comment."""
    orchestrator = RootOrchestrator()
    
    events = []
    async for event in orchestrator.run(
        user_message="",
        request_metadata={
            "source": "github_webhook",
            "pr_number": 123,
            "repo": "test/repo",
            "head_sha": "abc123"
        }
    ):
        events.append(event)
    
    # Verify workflow
    assert any(e.author == "SourceDetector" for e in events)
    assert any(e.author == "GitHubAgent" for e in events)
    assert any(e.author == "PlanningAgent" for e in events)
    assert any(e.author == "ReportSynthesizer" for e in events)
    assert any(e.author == "GitHubPublisher" for e in events)
    
    # Verify GitHub review posted
    final_state = events[-1].context.session.state
    assert "github_review_url" in final_state
```

---

## 🚀 Deployment Architecture

### Cloud Run Services

```yaml
# api-service (Webhook Handler)
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: code-review-api
spec:
  template:
    spec:
      containers:
      - image: gcr.io/project/code-review-api:latest
        env:
        - name: PUBSUB_TOPIC
          value: projects/PROJECT_ID/topics/code-review-queue
        resources:
          limits:
            memory: 512Mi
            cpu: 1

# worker-service (ADK Orchestrator)
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: code-review-worker
spec:
  template:
    spec:
      containers:
      - image: gcr.io/project/code-review-worker:latest
        env:
        - name: GOOGLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: gemini-api-key
              key: key
        - name: GITHUB_TOKEN
          valueFrom:
            secretKeyRef:
              name: github-token
              key: token
        resources:
          limits:
            memory: 2Gi
            cpu: 2
```

### Cloud Pub/Sub Configuration

```bash
# Create topic
gcloud pubsub topics create code-review-queue

# Create subscription with push to worker
gcloud pubsub subscriptions create code-review-worker-sub \
  --topic=code-review-queue \
  --push-endpoint=https://code-review-worker-HASH-uc.a.run.app/process \
  --ack-deadline=600 \
  --max-delivery-attempts=3
```

---

## 🔧 GitHub Integration: Personal vs Organization vs Enterprise

### Architecture Decision: GitHub Apps vs Personal Access Tokens

| Approach | Best For | Pros | Cons |
|----------|----------|------|------|
| **Personal Access Token (PAT)** | Personal repos, single user | Simple setup, no OAuth | Tied to user account, limited to 60 req/hr |
| **GitHub App (Recommended)** | Organizations, multiple repos | Fine-grained permissions, 5000 req/hr, org-level install | Complex setup, requires OAuth flow |
| **GitHub App + Installation Tokens** | Enterprise, multi-tenant SaaS | Per-repo authentication, auto-revocation, audit logs | Most complex, requires database |

**Recommendation:**
- **MVP (Personal Use):** Personal Access Token ✅ Simple
- **Production (Organization):** GitHub App ✅ Recommended
- **Enterprise (Multi-tenant SaaS):** GitHub App + Installation Tokens ✅ Scalable

---

## 🏢 Multi-Tenant Architecture Design

### Database Schema for Multi-Tenant Support

```sql
-- Organizations/Tenants table
CREATE TABLE organizations (
    org_id UUID PRIMARY KEY,
    github_org_name VARCHAR(255) UNIQUE NOT NULL,  -- e.g., "microsoft", "google"
    github_org_id BIGINT UNIQUE NOT NULL,           -- GitHub's org ID
    subscription_tier VARCHAR(50),                  -- free, pro, enterprise
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- GitHub App installations (per org/user)
CREATE TABLE github_installations (
    installation_id BIGINT PRIMARY KEY,             -- GitHub's installation ID
    org_id UUID REFERENCES organizations(org_id),
    installation_type VARCHAR(20),                  -- 'organization' or 'user'
    github_account_name VARCHAR(255),               -- org/user name
    github_account_id BIGINT,                       -- org/user ID
    installed_at TIMESTAMP,
    suspended_at TIMESTAMP NULL,
    INDEX idx_org_installation (org_id, installation_id)
);

-- Repository configurations (per repo)
CREATE TABLE repositories (
    repo_id UUID PRIMARY KEY,
    installation_id BIGINT REFERENCES github_installations(installation_id),
    github_repo_id BIGINT UNIQUE NOT NULL,          -- GitHub's repo ID
    full_name VARCHAR(255) UNIQUE NOT NULL,         -- "owner/repo"
    webhook_secret_name VARCHAR(255),               -- GCP Secret Manager reference
    is_active BOOLEAN DEFAULT TRUE,
    config JSONB,                                   -- Per-repo settings
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_installation_repo (installation_id, github_repo_id),
    INDEX idx_full_name (full_name)
);

-- Code review sessions (multi-tenant)
CREATE TABLE review_sessions (
    session_id UUID PRIMARY KEY,
    repo_id UUID REFERENCES repositories(repo_id),
    pr_number INTEGER NOT NULL,
    github_pr_id BIGINT NOT NULL,
    head_sha VARCHAR(40),
    author_login VARCHAR(255),
    status VARCHAR(50),                             -- pending, in_progress, completed, failed
    analysis_id VARCHAR(100),
    artifact_path VARCHAR(500),                     -- GCS path to artifacts
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP NULL,
    INDEX idx_repo_pr (repo_id, pr_number),
    INDEX idx_status (status, created_at)
);

-- Audit logs (compliance)
CREATE TABLE audit_logs (
    log_id UUID PRIMARY KEY,
    org_id UUID REFERENCES organizations(org_id),
    repo_id UUID REFERENCES repositories(repo_id) NULL,
    actor VARCHAR(255),                             -- User who triggered action
    action VARCHAR(100),                            -- webhook_received, review_posted, etc.
    details JSONB,
    timestamp TIMESTAMP DEFAULT NOW(),
    INDEX idx_org_timestamp (org_id, timestamp),
    INDEX idx_repo_timestamp (repo_id, timestamp)
);
```

### Enhanced Webhook Payload Processing

```python
# api_server.py - Multi-tenant webhook handler

from fastapi import FastAPI, Request, HTTPException, Header
from typing import Optional
import hmac
import hashlib

app = FastAPI()

class RepositoryService:
    """Service to fetch repository-specific configuration."""
    
    async def get_repo_config(self, github_repo_id: int) -> dict:
        """
        Fetch repository configuration from database.
        
        Returns:
        {
            "repo_id": "uuid",
            "installation_id": 12345,
            "webhook_secret": "secret_from_secret_manager",
            "org_id": "uuid",
            "config": {"max_files": 100, "auto_approve": false}
        }
        """
        # Query database
        query = """
            SELECT 
                r.repo_id,
                r.installation_id,
                r.webhook_secret_name,
                r.config,
                gi.org_id,
                o.subscription_tier
            FROM repositories r
            JOIN github_installations gi ON r.installation_id = gi.installation_id
            JOIN organizations o ON gi.org_id = o.org_id
            WHERE r.github_repo_id = $1 AND r.is_active = TRUE
        """
        result = await db.fetchrow(query, github_repo_id)
        
        if not result:
            raise ValueError(f"Repository {github_repo_id} not configured")
        
        # Fetch webhook secret from Secret Manager
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        secret_name = f"projects/{PROJECT_ID}/secrets/{result['webhook_secret_name']}/versions/latest"
        response = client.access_secret_version(request={"name": secret_name})
        webhook_secret = response.payload.data.decode('UTF-8')
        
        return {
            "repo_id": result["repo_id"],
            "installation_id": result["installation_id"],
            "webhook_secret": webhook_secret,
            "org_id": result["org_id"],
            "subscription_tier": result["subscription_tier"],
            "config": result["config"]
        }

repo_service = RepositoryService()


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
    x_github_delivery: Optional[str] = Header(None)
):
    """
    Multi-tenant GitHub webhook handler.
    
    Flow:
    1. Extract repository from payload
    2. Fetch repo-specific webhook secret from database
    3. Validate HMAC signature with repo-specific secret
    4. Fetch GitHub App installation token for this repo
    5. Enrich payload with tenant context
    6. Publish to Pub/Sub with tenant isolation
    """
    
    # 1. Read raw body (needed for HMAC validation)
    body = await request.body()
    
    # 2. Parse payload to get repository
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # 3. Extract repository information
    if "repository" not in payload:
        raise HTTPException(status_code=400, detail="Missing repository in payload")
    
    github_repo_id = payload["repository"]["id"]
    repo_full_name = payload["repository"]["full_name"]
    
    logger.info(f"📥 Webhook received for {repo_full_name} (ID: {github_repo_id})")
    
    # 4. Fetch repository-specific configuration (includes webhook secret)
    try:
        repo_config = await repo_service.get_repo_config(github_repo_id)
    except ValueError as e:
        logger.warning(f"⚠️ Repository {repo_full_name} not configured: {e}")
        # Return 200 to avoid GitHub retrying for unconfigured repos
        return {"status": "ignored", "reason": "Repository not configured in system"}
    
    # 5. Validate HMAC signature with repo-specific secret
    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")
    
    expected_signature = "sha256=" + hmac.new(
        repo_config["webhook_secret"].encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(x_hub_signature_256, expected_signature):
        logger.error(f"❌ Invalid signature for {repo_full_name}")
        # Audit log for security
        await audit_log(
            org_id=repo_config["org_id"],
            repo_id=repo_config["repo_id"],
            action="webhook_signature_failed",
            details={"repo": repo_full_name, "event": x_github_event}
        )
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # 6. Filter: Only process PR events
    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"Event '{x_github_event}' not processed"}
    
    action = payload.get("action")
    if action not in ["opened", "synchronize", "reopened"]:
        return {"status": "ignored", "reason": f"PR action '{action}' not processed"}
    
    # 7. Fetch GitHub App installation token (short-lived, repo-specific)
    installation_token = await get_installation_token(
        installation_id=repo_config["installation_id"]
    )
    
    # 8. Extract PR data with tenant context
    pr = payload["pull_request"]
    enriched_payload = {
        # Tenant context (CRITICAL for multi-tenant isolation)
        "org_id": repo_config["org_id"],
        "repo_id": repo_config["repo_id"],
        "installation_id": repo_config["installation_id"],
        "subscription_tier": repo_config["subscription_tier"],
        
        # GitHub context
        "repo": repo_full_name,
        "github_repo_id": github_repo_id,
        "pr_number": pr["number"],
        "github_pr_id": pr["id"],
        "head_sha": pr["head"]["sha"],
        "action": action,
        "title": pr["title"],
        "author": pr["user"]["login"],
        
        # Authentication (short-lived installation token)
        "github_token": installation_token,  # Valid for 1 hour
        
        # Webhook metadata
        "webhook_delivery_id": x_github_delivery,
        "webhook_event": x_github_event,
        
        # Repo-specific config
        "repo_config": repo_config["config"],
        
        # Timestamps
        "webhook_received_at": datetime.utcnow().isoformat()
    }
    
    # 9. Create review session record
    session_id = str(uuid.uuid4())
    await db.execute("""
        INSERT INTO review_sessions (
            session_id, repo_id, pr_number, github_pr_id, 
            head_sha, author_login, status
        )
        VALUES ($1, $2, $3, $4, $5, $6, 'pending')
    """, session_id, repo_config["repo_id"], pr["number"], 
         pr["id"], pr["head"]["sha"], pr["user"]["login"])
    
    enriched_payload["session_id"] = session_id
    
    # 10. Publish to Pub/Sub with tenant routing
    from google.cloud import pubsub_v1
    
    publisher = pubsub_v1.PublisherClient()
    
    # Use org-specific topic for tenant isolation (optional)
    # OR use single topic with tenant attribute for filtering
    topic_path = f"projects/{PROJECT_ID}/topics/code-review-queue"
    
    message_data = json.dumps(enriched_payload).encode()
    
    # Add tenant attributes for Pub/Sub filtering/routing
    future = publisher.publish(
        topic_path,
        message_data,
        org_id=repo_config["org_id"],              # For filtering
        repo_id=repo_config["repo_id"],            # For filtering
        subscription_tier=repo_config["subscription_tier"]  # For priority routing
    )
    message_id = future.result()
    
    # 11. Audit log
    await audit_log(
        org_id=repo_config["org_id"],
        repo_id=repo_config["repo_id"],
        actor=pr["user"]["login"],
        action="webhook_accepted",
        details={
            "pr_number": pr["number"],
            "message_id": message_id,
            "session_id": session_id
        }
    )
    
    logger.info(f"✅ Published PR #{pr['number']} for {repo_full_name} to queue: {message_id}")
    
    # 12. Return fast ACK to GitHub
    return {
        "status": "accepted",
        "session_id": session_id,
        "message_id": message_id,
        "pr_number": pr["number"]
    }


async def get_installation_token(installation_id: int) -> str:
    """
    Get GitHub App installation token for specific installation.
    
    This token is:
    - Short-lived (1 hour)
    - Repository-specific (based on installation)
    - Auto-revoked when app uninstalled
    - Higher rate limits (5000 req/hr)
    
    Returns: Installation access token
    """
    import jwt
    import time
    import httpx
    
    # 1. Generate JWT for GitHub App authentication
    # (GitHub App private key stored in Secret Manager)
    from google.cloud import secretmanager
    client = secretmanager.SecretManagerServiceClient()
    private_key_name = f"projects/{PROJECT_ID}/secrets/github-app-private-key/versions/latest"
    response = client.access_secret_version(request={"name": private_key_name})
    private_key = response.payload.data.decode('UTF-8')
    
    # GitHub App ID (from environment)
    app_id = os.getenv("GITHUB_APP_ID")
    
    # Create JWT (valid for 10 minutes)
    now = int(time.time())
    payload = {
        "iat": now - 60,        # Issued at (with 60s clock skew)
        "exp": now + 600,       # Expires in 10 minutes
        "iss": app_id           # GitHub App ID
    }
    
    jwt_token = jwt.encode(payload, private_key, algorithm="RS256")
    
    # 2. Exchange JWT for installation access token
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Token is valid for 1 hour
        # Cache it with expiration
        installation_token = data["token"]
        expires_at = data["expires_at"]  # ISO 8601 timestamp
        
        # Optional: Cache in Redis/Memcached to avoid repeated JWT exchanges
        # await cache.set(f"github_token:{installation_id}", installation_token, ttl=3000)
        
        return installation_token


async def audit_log(org_id: str, repo_id: str, actor: str, action: str, details: dict):
    """Write audit log for compliance."""
    await db.execute("""
        INSERT INTO audit_logs (log_id, org_id, repo_id, actor, action, details)
        VALUES ($1, $2, $3, $4, $5, $6)
    """, str(uuid.uuid4()), org_id, repo_id, actor, action, json.dumps(details))
```

---

## 🔑 GitHub App Setup (Recommended for Organizations)

### Step 1: Create GitHub App

**Purpose:** Organization-level installation with fine-grained permissions

1. **Go to:** https://github.com/organizations/YOUR_ORG/settings/apps/new
   - Or personal: https://github.com/settings/apps/new

2. **GitHub App Configuration:**
   
   **Basic Information:**
   ```
   GitHub App name: Agentic Code Review Bot
   Homepage URL: https://your-company.com/code-review
   Webhook URL: https://code-review-api-HASH-uc.a.run.app/webhook/github
   Webhook secret: (generate with: openssl rand -hex 32)
   ```
   
   **Permissions (Repository):**
   ```
   ✅ Pull requests: Read & write
   ✅ Contents: Read-only
   ✅ Metadata: Read-only (automatically selected)
   ```
   
   **Subscribe to events:**
   ```
   ✅ Pull request
       - opened
       - reopened  
       - synchronize
   ```
   
   **Where can this GitHub App be installed?**
   ```
   ○ Only on this account (private)
   ● Any account (public - if building SaaS)
   ```

3. **Click:** "Create GitHub App"

4. **Generate Private Key:**
   - Scroll to "Private keys" section
   - Click "Generate a private key"
   - Download `your-app-name.2025-11-30.private-key.pem`
   - Store securely:
     ```bash
     # Store in Google Secret Manager
     gcloud secrets create github-app-private-key \
       --data-file=your-app-name.2025-11-30.private-key.pem
     
     # Delete local copy
     rm your-app-name.2025-11-30.private-key.pem
     ```

5. **Note App ID:**
   - Found at top of page: `App ID: 123456`
   - Store in environment:
     ```bash
     export GITHUB_APP_ID=123456
     
     # Cloud Run
     gcloud secrets create github-app-id --data-file=- <<< "123456"
     ```

### Step 2: Install GitHub App on Organization/Repositories

**Purpose:** Grant app access to specific repositories

1. **Go to:** https://github.com/organizations/YOUR_ORG/settings/installations

2. **Click:** "Install App" → Select your app

3. **Choose repositories:**
   ```
   ○ All repositories (risky, not recommended)
   ● Only select repositories:
       ☑ repo-1
       ☑ repo-2
       ☑ repo-3
   ```

4. **Click:** "Install"

5. **Note Installation ID:**
   - After install, URL will be: `https://github.com/organizations/YOUR_ORG/settings/installations/12345678`
   - Installation ID: `12345678`
   - Store in database (repositories table)

### Step 3: Register Installation in Database

```bash
# Insert organization
psql -h DB_HOST -U postgres -d codereview -c "
INSERT INTO organizations (org_id, github_org_name, github_org_id, subscription_tier)
VALUES (
    'uuid-here',
    'your-org-name',
    123456,  -- GitHub org ID (from API or org settings)
    'enterprise'
);"

# Insert GitHub App installation
psql -h DB_HOST -U postgres -d codereview -c "
INSERT INTO github_installations (
    installation_id, org_id, installation_type, 
    github_account_name, github_account_id, installed_at
)
VALUES (
    12345678,                -- Installation ID from Step 2
    'uuid-here',            -- org_id from above
    'organization',
    'your-org-name',
    123456,                 -- GitHub org ID
    NOW()
);"

# Register repositories (repeat for each repo)
psql -h DB_HOST -U postgres -d codereview -c "
INSERT INTO repositories (
    repo_id, installation_id, github_repo_id, 
    full_name, webhook_secret_name, is_active, config
)
VALUES (
    gen_random_uuid(),
    12345678,                           -- Installation ID
    987654321,                          -- GitHub repo ID
    'your-org-name/repo-1',
    'webhook-secret-org-repo1',         -- Secret Manager reference
    TRUE,
    '{\"max_files\": 100, \"auto_approve\": false}'::jsonb
);"

# Store webhook secret in Secret Manager (per repo)
openssl rand -hex 32 | gcloud secrets create webhook-secret-org-repo1 --data-file=-
```

### Step 4: Configure Webhooks (Per Repository)

**Note:** When using GitHub Apps, webhooks are auto-configured at installation!

If manual configuration needed:
1. Go to: https://github.com/YOUR_ORG/REPO/settings/hooks
2. Verify webhook exists with correct URL
3. Check "Recent Deliveries" for successful pings

---

## 🔒 Security & Compliance for Enterprise

### Data Isolation

```python
# worker.py - Ensure tenant isolation

@app.post("/process")
async def process_code_review(request: Request):
    """Process code review with tenant isolation."""
    
    envelope = await request.json()
    message_data = base64.b64decode(envelope["message"]["data"])
    payload = json.loads(message_data)
    
    # Extract tenant context
    org_id = payload["org_id"]
    repo_id = payload["repo_id"]
    session_id = payload["session_id"]
    
    # Create tenant-scoped storage path
    artifact_base_path = f"gs://{BUCKET_NAME}/{org_id}/{repo_id}/{session_id}"
    
    # Configure artifact service with tenant isolation
    artifact_service = FileArtifactService(base_path=artifact_base_path)
    
    # Run orchestrator with tenant context
    async for event in orchestrator.run(
        user_message="",
        request_metadata={
            "org_id": org_id,          # CRITICAL: Tenant isolation
            "repo_id": repo_id,
            "session_id": session_id,
            "github_token": payload["github_token"],  # Repo-specific token
            **payload
        },
        artifact_service=artifact_service  # Tenant-scoped storage
    ):
        pass
    
    # Update session status
    await db.execute("""
        UPDATE review_sessions
        SET status = 'completed', completed_at = NOW()
        WHERE session_id = $1 AND repo_id = $2
    """, session_id, repo_id)  # Double-check tenant boundary
    
    return {"status": "success", "session_id": session_id}
```

### Access Control

```python
# Verify user can access review results

@app.get("/api/reviews/{session_id}")
async def get_review(
    session_id: str,
    current_user: User = Depends(get_current_user)  # JWT auth
):
    """Get review results with access control."""
    
    # Fetch review session
    session = await db.fetchrow("""
        SELECT rs.*, r.installation_id, gi.org_id
        FROM review_sessions rs
        JOIN repositories r ON rs.repo_id = r.repo_id
        JOIN github_installations gi ON r.installation_id = gi.installation_id
        WHERE rs.session_id = $1
    """, session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Verify user has access to this org
    user_orgs = await get_user_organizations(current_user.github_id)
    if session["org_id"] not in user_orgs:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Fetch artifacts from tenant-scoped storage
    artifact_path = f"gs://{BUCKET_NAME}/{session['org_id']}/{session['repo_id']}/{session_id}/reports/final_report.md"
    
    return {
        "session_id": session_id,
        "status": session["status"],
        "report_url": artifact_path
    }
```

### Rate Limiting (Per Organization)

```python
# Pub/Sub subscription with org-specific filtering

# Create separate subscriptions for different tiers
gcloud pubsub subscriptions create code-review-worker-free \
  --topic=code-review-queue \
  --push-endpoint=https://worker.example.com/process \
  --ack-deadline=600 \
  --filter='attributes.subscription_tier="free"' \
  --max-delivery-rate=10  # 10 reviews/minute for free tier

gcloud pubsub subscriptions create code-review-worker-enterprise \
  --topic=code-review-queue \
  --push-endpoint=https://worker-premium.example.com/process \
  --ack-deadline=600 \
  --filter='attributes.subscription_tier="enterprise"' \
  --max-delivery-rate=1000  # 1000 reviews/minute for enterprise
```

---

## 📋 Personal vs Organization Setup Comparison

| Aspect | Personal Account | Organization Account | Enterprise Multi-Tenant |
|--------|------------------|----------------------|-------------------------|
| **Authentication** | Personal Access Token | GitHub App (org-level) | GitHub App + Installation Tokens |
| **Webhook Secret** | Single global secret | Per-organization secret | Per-repository secret |
| **Rate Limits** | 60 req/hr (or 5000 if authed) | 5000 req/hr per installation | 5000 req/hr per installation |
| **Permissions** | User's personal permissions | Fine-grained app permissions | Fine-grained app permissions |
| **Token Lifetime** | 90 days (manual refresh) | 1 hour (auto-refresh) | 1 hour (auto-refresh) |
| **Revocation** | Manual token deletion | Auto-revoked on app uninstall | Auto-revoked on app uninstall |
| **Audit Logs** | None | Basic GitHub logs | Full audit trail in database |
| **Data Isolation** | Single user | Per-org storage | Per-org + per-repo storage |
| **Cost** | Free | Free | Database + storage costs |
| **Setup Complexity** | ⭐ Simple | ⭐⭐ Moderate | ⭐⭐⭐ Complex |
| **Best For** | Learning, personal projects | Teams, private repos | SaaS product, multi-tenant |

---

## 🚀 Migration Path: Personal → Organization → Enterprise

### Phase 1: Personal (MVP) ✅ Current Design
- Use Personal Access Token
- Single webhook secret
- No database needed
- Perfect for testing and learning

### Phase 2: Organization (Production)
- Create GitHub App
- Install on organization
- Add database for installation tracking
- Per-org webhook secrets
- **Backward compatible** with Phase 1 (keep PAT as fallback)

### Phase 3: Enterprise (Multi-Tenant SaaS)
- Full database schema (see above)
- Per-repository webhook secrets
- Tenant-scoped storage (GCS with org/repo prefixes)
- Rate limiting per subscription tier
- Audit logging and compliance
- User authentication (OAuth, JWT)
- Web dashboard for managing installations

**Good news:** The ADK orchestrator code doesn't change! Only webhook handler and storage paths need updates.

---

### Step 2: Configure Repository Webhook

**Purpose:** GitHub sends webhook events when PRs are opened/updated

#### 2.1 Deploy Your API Service First

Before configuring the webhook, deploy your API service to get the URL:

```bash
# Deploy API service to Cloud Run
gcloud run deploy code-review-api \
  --image gcr.io/PROJECT_ID/code-review-api:latest \
  --region us-central1 \
  --allow-unauthenticated

# Get the service URL
gcloud run services describe code-review-api \
  --region us-central1 \
  --format='value(status.url)'
# Output: https://code-review-api-HASH-uc.a.run.app
```

#### 2.2 Generate Webhook Secret

```bash
# Generate a secure random secret (32 bytes, hex encoded)
openssl rand -hex 32

# Example output: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2

# Store it securely
export GITHUB_WEBHOOK_SECRET="a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2"

# Add to Cloud Run secret
gcloud secrets create github-webhook-secret \
  --data-file=- <<< "$GITHUB_WEBHOOK_SECRET"
```

#### 2.3 Configure Webhook in GitHub Repository

1. **Go to your repository:** https://github.com/rahulgupta2018/YOUR_REPO

2. **Navigate to:** Settings → Webhooks → "Add webhook"

3. **Webhook Configuration:**
   
   **Payload URL:**
   ```
   https://code-review-api-HASH-uc.a.run.app/webhook/github
   ```
   
   **Content type:**
   ```
   application/json
   ```
   
   **Secret:**
   ```
   a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
   ```
   (Use the secret generated in Step 2.2)
   
   **Which events would you like to trigger this webhook?**
   ```
   ☐ Just the push event
   ☑ Let me select individual events:
       ☑ Pull requests
           - opened
           - reopened
           - synchronize (new commits pushed)
           - edited
       ☐ Pushes (uncheck)
       ☐ Issues (uncheck)
   ```
   
   **Active:**
   ```
   ☑ Active (checkbox checked)
   ```

4. **Click:** "Add webhook"

5. **Verify:** GitHub will send a test ping event
   - Check "Recent Deliveries" tab
   - Should see ✅ green checkmark for successful delivery
   - Response should be `200 OK`

#### 2.4 Webhook Payload Example

When a PR is opened, GitHub sends this payload:

```json
{
  "action": "opened",
  "number": 123,
  "pull_request": {
    "id": 1234567890,
    "number": 123,
    "state": "open",
    "title": "Add new feature",
    "user": {
      "login": "rahulgupta2018"
    },
    "body": "This PR adds a new feature...",
    "head": {
      "sha": "abc123def456",
      "ref": "feature-branch",
      "repo": {
        "full_name": "rahulgupta2018/repo-name"
      }
    },
    "base": {
      "ref": "main"
    }
  },
  "repository": {
    "name": "repo-name",
    "full_name": "rahulgupta2018/repo-name",
    "owner": {
      "login": "rahulgupta2018"
    }
  }
}
```

Your API service will validate HMAC signature and extract:
- `repo`: `rahulgupta2018/repo-name`
- `pr_number`: `123`
- `head_sha`: `abc123def456`
- `action`: `opened`

---

### Step 3: Validate HMAC Signature in API Service

**Purpose:** Ensure webhook requests actually come from GitHub (security)

```python
# api_server.py - Webhook receiver

import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

@app.post("/webhook/github")
async def github_webhook(request: Request):
    """
    Receive and validate GitHub webhook events.
    
    Security: Validates HMAC signature to ensure request is from GitHub.
    """
    
    # 1. Get signature from header
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing signature")
    
    # 2. Read raw body
    body = await request.body()
    
    # 3. Calculate expected signature
    expected_signature = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    # 4. Compare signatures (constant-time comparison)
    if not hmac.compare_digest(signature_header, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # 5. Parse payload
    payload = await request.json()
    
    # 6. Filter: Only process "opened" and "synchronize" events
    action = payload.get("action")
    if action not in ["opened", "synchronize", "reopened"]:
        return {"status": "ignored", "reason": f"Action '{action}' not processed"}
    
    # 7. Extract PR data
    pr = payload["pull_request"]
    pr_data = {
        "repo": payload["repository"]["full_name"],
        "pr_number": pr["number"],
        "head_sha": pr["head"]["sha"],
        "action": action,
        "title": pr["title"],
        "author": pr["user"]["login"]
    }
    
    # 8. Publish to Pub/Sub queue
    from google.cloud import pubsub_v1
    
    publisher = pubsub_v1.PublisherClient()
    topic_path = f"projects/{PROJECT_ID}/topics/code-review-queue"
    
    message_data = json.dumps(pr_data).encode()
    future = publisher.publish(topic_path, message_data)
    message_id = future.result()
    
    logger.info(f"✅ Published PR #{pr_data['pr_number']} to queue: {message_id}")
    
    # 9. Return fast ACK to GitHub (< 100ms)
    return {
        "status": "accepted",
        "message_id": message_id,
        "pr_number": pr_data["pr_number"]
    }
```

**Testing Webhook Locally:**

```bash
# Use ngrok to expose local server
ngrok http 8000

# Use ngrok URL in GitHub webhook configuration
# https://abc123.ngrok.io/webhook/github

# Start your API server
uvicorn api_server:app --host 0.0.0.0 --port 8000

# Open a PR in your repo and watch the logs!
```

---

### Step 4: Test GitHub Integration End-to-End

#### 4.1 Create Test Repository

```bash
# Create a test repository
gh repo create test-code-review --public --clone

cd test-code-review

# Add some code to review
cat > bad_code.py << 'EOF'
import os

def login(username, password):
    # SQL Injection vulnerability!
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    db.execute(query)
    
    # Hardcoded credentials
    if username == "admin" and password == "admin123":
        return True
    
    return False
EOF

git add bad_code.py
git commit -m "Add login function"
git push origin main
```

#### 4.2 Create Pull Request

```bash
# Create feature branch
git checkout -b fix-security
echo "# Fixed security issues" >> README.md
git add README.md
git commit -m "Fix security vulnerabilities"
git push origin fix-security

# Create PR via GitHub CLI
gh pr create \
  --title "Fix security vulnerabilities in login function" \
  --body "This PR fixes SQL injection and hardcoded credentials" \
  --base main \
  --head fix-security
```

#### 4.3 Monitor Webhook Delivery

1. **GitHub UI:**
   - Go to: Repository → Settings → Webhooks
   - Click on your webhook
   - Click "Recent Deliveries" tab
   - Should see delivery with ✅ green checkmark
   - Click to see request/response details

2. **Cloud Logs:**
   ```bash
   # API Service logs (webhook receiver)
   gcloud logging read "resource.type=cloud_run_revision \
     AND resource.labels.service_name=code-review-api" \
     --limit 50 --format json
   
   # Worker Service logs (ADK orchestrator)
   gcloud logging read "resource.type=cloud_run_revision \
     AND resource.labels.service_name=code-review-worker" \
     --limit 50 --format json
   ```

3. **Pub/Sub Monitoring:**
   ```bash
   # Check queue depth
   gcloud pubsub topics describe code-review-queue
   
   # List subscriptions
   gcloud pubsub subscriptions list
   
   # Check dead letter queue
   gcloud pubsub topics describe code-review-dlq
   ```

#### 4.4 Verify Review Posted

1. **Check PR on GitHub:**
   - Go to your PR: https://github.com/rahulgupta2018/test-code-review/pulls
   - Should see bot comment with code review
   - Review should highlight security issues

2. **Expected Review Comment:**
   ```markdown
   # Code Review Report
   
   **Analysis ID:** abc-123-def-456
   **Date:** 2025-11-29 10:30:00 UTC
   **Source:** github_webhook
   
   ## 🧠 Analysis Strategy
   
   **Agents Selected:** security, code_quality
   **Execution Mode:** parallel
   **Reasoning:** Detected security-related code changes
   
   ## 📊 Executive Summary
   
   🔴 **2 Critical Issues Found**
   
   ## 🔍 Detailed Findings
   
   ### 🔒 Security Analysis
   
   **CRITICAL: SQL Injection Vulnerability (Line 5)**
   - User input directly concatenated into SQL query
   - Recommendation: Use parameterized queries
   
   **CRITICAL: Hardcoded Credentials (Line 9)**
   - Admin password hardcoded in source code
   - Recommendation: Use environment variables
   
   ## 💡 Recommendations
   
   1. Replace string concatenation with parameterized queries
   2. Move credentials to environment variables
   3. Add input validation for username/password
   
   ---
   *Powered by ADK Multi-Agent Code Review System*
   ```

---

### Step 5: Repository-Specific Configuration

#### 5.1 Configure Branch Protection Rules

**Purpose:** Require code review approval before merging

1. **Go to:** Repository → Settings → Branches
2. **Add rule for:** `main` branch
3. **Settings:**
   ```
   ☑ Require a pull request before merging
   ☑ Require approvals: 1
   ☐ Require review from Code Owners (optional)
   ☑ Require status checks to pass before merging
       - Add: code-review-bot
   ☑ Require conversation resolution before merging
   ☐ Require linear history (optional)
   ```

#### 5.2 Add CODEOWNERS File (Optional)

Create `.github/CODEOWNERS` in your repository:

```bash
# .github/CODEOWNERS

# Global owners
* @rahulgupta2018

# Specific paths
/src/security/ @rahulgupta2018 @security-team
/src/api/ @rahulgupta2018 @backend-team
*.py @rahulgupta2018

# Documentation
/docs/ @rahulgupta2018
*.md @rahulgupta2018
```

#### 5.3 Configure Notifications

**Purpose:** Get notified when code reviews are posted

1. **GitHub Notifications:**
   - Go to: https://github.com/settings/notifications
   - Enable: "Pull request reviews"
   - Choose: Email or Web notification

2. **Email Notifications:**
   ```bash
   # Configure in repository settings
   # Settings → Notifications → Email notifications
   ```

3. **Slack Integration (Optional):**
   ```bash
   # Add GitHub app to Slack workspace
   /github subscribe rahulgupta2018/repo-name reviews
   ```

---

## 🧪 Testing Checklist

### Before Going to Production

- [ ] **Personal Access Token created** with correct scopes
- [ ] **Webhook configured** with valid secret
- [ ] **HMAC validation working** (test with invalid secret)
- [ ] **Pub/Sub queue created** and configured
- [ ] **Dead letter queue created** for failed messages
- [ ] **Cloud Run services deployed** (API + Worker)
- [ ] **Secrets stored** in Google Secret Manager
- [ ] **Test PR created** and reviewed successfully
- [ ] **Review posted** to GitHub with correct formatting
- [ ] **Concurrent PRs tested** (open 3-5 PRs simultaneously)
- [ ] **Error handling tested** (invalid repo, rate limits)
- [ ] **Monitoring setup** (Cloud Logging, alerting)
- [ ] **Cost monitoring** enabled (GCP billing alerts)

### Test Scenarios

```bash
# Scenario 1: Valid PR (should post review)
gh pr create --title "Test PR" --body "Test"

# Scenario 2: Invalid webhook signature (should reject)
curl -X POST https://your-api.com/webhook/github \
  -H "X-Hub-Signature-256: sha256=invalid" \
  -d '{"action":"opened"}'

# Scenario 3: Concurrent PRs (should handle all)
for i in {1..5}; do
  gh pr create --title "Concurrent PR $i" --body "Test" &
done
wait

# Scenario 4: Large PR with 50+ files (should handle)
# Create PR with many file changes and verify processing

# Scenario 5: Trigger rate limit (should retry)
# Open many PRs quickly and verify retries work
```

---

## ❓ Cloud Pub/Sub: Do We Need It?

### When to Use Cloud Pub/Sub

✅ **YES** - Use Pub/Sub when:

1. **Multiple Concurrent PRs**: GitHub sends multiple webhooks simultaneously
2. **Rate Limiting**: Need to throttle requests to Gemini API (15 RPM free tier)
3. **Retry Logic**: Webhook processing might fail (API errors, timeouts)
4. **Decoupling**: Separate webhook receiver (fast ACK) from processing (slow)
5. **Scaling**: Worker service auto-scales based on queue depth

### When to Skip Pub/Sub

❌ **NO** - Skip Pub/Sub when:

1. **Low Volume**: < 10 PRs/day, synchronous processing acceptable
2. **Development/Testing**: Local testing with direct API calls
3. **Single Tenant**: One repository, predictable load
4. **Cost Sensitivity**: Pub/Sub adds cost ($0.40/million messages)

### Recommended Approach

**Phase 1 (MVP):** Skip Pub/Sub
- Direct API call from webhook → worker
- Synchronous processing acceptable for testing
- Simpler deployment and debugging

**Phase 2 (Production):** Add Pub/Sub
- Handle concurrent PRs reliably
- Implement rate limiting and retry logic
- Better observability and monitoring

---

## 📊 Performance Expectations

| Metric | Phase 1 (Hardcoded) | Phase 2 (Revised) | Change |
|--------|---------------------|-------------------|--------|
| Source Detection | N/A | 300ms | +300ms |
| GitHub Data Fetch | N/A | 800ms | +800ms |
| Classification | 450ms | 450ms | ±0 |
| Planning (Plan-ReAct) | 10ms (hardcoded) | 700ms | +690ms |
| Agent Execution | 3200ms | 3200ms | ±0 |
| Report Synthesis | 500ms | 500ms | ±0 |
| GitHub Publish | N/A | 400ms | +400ms |
| **Total (GitHub)** | **~3.7s** | **~6.3s** | **+2.6s** |
| **Total (Web UI)** | **~3.7s** | **~4.8s** | **+1.1s** |

**Analysis:**
- GitHub path is slower due to API calls (fetch PR + post review)
- Planning adds ~700ms but provides intelligence and explainability
- Trade-off: Slower execution for better accuracy and transparency
- Acceptable for async GitHub workflow (user expects delay anyway)

---

## ✅ Summary

### Complete Workflow (8 Steps)

**GitHub PR Path:**
```
PR Opened → Webhook → API Service → Pub/Sub Queue → Worker Service
  ↓
Step 1: SourceDetector → Identifies github_webhook source
  ↓
Step 2: GitHubAgent → Fetches PR files via OpenAPI
  ↓
Step 3: PlanningAgent → Uses Plan-ReAct to select sub-agents
  ↓
Step 4: ExecutionPipeline → Runs selected agents (parallel/sequential)
  ↓
Step 5: ReportSynthesizer → Consolidates results
  ↓
Step 6: GitHubPublisher → Posts review to PR via OpenAPI
  ↓
Step 7: MessageAcknowledger → ACKs Pub/Sub message (cleanup)
```

**Web UI Path:**
```
User Query → API Service → Worker Service (optional Pub/Sub)
  ↓
Step 1: SourceDetector → Identifies web_ui source
  ↓
Step 2: ClassifierAgent → Determines intent (security/quality/comprehensive)
  ↓
Step 3: PlanningAgent → Uses Plan-ReAct to select sub-agents
  ↓
Step 4: ExecutionPipeline → Runs selected agents (parallel/sequential)
  ↓
Step 5: ReportSynthesizer → Consolidates results
  ↓
Step 6: Return JSON/markdown report to user
```

### What Changed from Original Phase 2

❌ **Removed:**
- Custom if/elif orchestration logic
- Phase 1 hardcoded agent selection
- Manual checkpointing

✅ **Added:**
- SequentialAgent for deterministic workflow
- Decision Framework for source routing
- Plan-ReAct for intelligent agent selection
- GitHub integration pipeline
- OpenAPI tools for GitHub API
- Pub/Sub message acknowledgment for cleanup

### ADK Patterns Used

1. ✅ **SequentialAgent**: Ordered pipeline execution
2. ✅ **ParallelAgent**: Concurrent independent analyses
3. ✅ **Decision Framework**: Source-based routing
4. ✅ **PlanReActPlanner**: Intelligent agent selection
5. ✅ **OpenAPIToolset**: GitHub API integration

### Why Pub/Sub with Acknowledgment is Critical

For production GitHub integration, Pub/Sub is **essential** (not optional):

| Problem | Without Pub/Sub | With Pub/Sub + ACK |
|---------|----------------|-------------------|
| **Concurrent PRs** | Sequential processing, long queue | Parallel workers, auto-scaling |
| **GitHub Rate Limits** | Webhook timeout, review lost | Message retried automatically |
| **ADK Crashes** | Review lost, no retry | Message retried up to 3 times |
| **Webhook Timeouts** | GitHub retries webhook → duplicate reviews | ACK prevents duplicates |
| **Failed Reviews** | Silent failure, user never notified | Dead letter queue, alerting |
| **Cost** | Wasted LLM tokens on duplicates | Pay only for unique reviews |

**Step 7 (MessageAcknowledger) prevents:**
- ❌ Duplicate reviews (same PR reviewed 2-3 times)
- ❌ Lost reviews (crashes with no retry)
- ❌ Silent failures (no visibility into errors)
- ❌ Rate limit cascades (GitHub blocks webhook)

### Key Benefits

- **Deterministic**: Predictable, ordered execution via SequentialAgent
- **Flexible**: Add new agents without code changes (via planner)
- **Explainable**: [PLANNING] → [REASONING] → [ACTION] visible to users
- **Scalable**: Pub/Sub + Cloud Run handles 50+ concurrent PRs
- **Reliable**: ACK/NACK with retries + dead letter queue
- **Cost-efficient**: No duplicate processing, pay per unique review
- **Maintainable**: Pure ADK patterns, no custom orchestration logic

---

## 🚀 Implementation Recommendation

### Current vs Proposed Architecture

**Current State (main.py):**
- ✅ Interactive CLI tool for local development
- ✅ Direct orchestrator invocation with Runner
- ✅ Session persistence to disk (JSON files)
- ✅ Artifact storage to disk (./artifacts)
- ⚠️ **Can be extended for Web UI** (synchronous response model)

**Proposed Architecture:**

| Component | Purpose | File | Use Case |
|-----------|---------|------|----------|
| **main.py** | Web UI backend (synchronous) | `/main.py` | ✅ Existing - User submits code, waits for result |
| **api_server.py** | GitHub webhook receiver | `/api_server.py` | ❌ To Create - Fast webhook ACK (< 100ms) |
| **worker.py** | GitHub async processor | `/worker.py` | ❌ To Create - Heavy ADK processing (30-60s) |

**Architecture by Request Source:**

```
┌─────────────────────────────────────────────────────────────┐
│  WEB UI PATH (main.py)                                      │
│                                                             │
│  User Browser → FastAPI /analyze endpoint                   │
│      ↓                                                      │
│  main.py: runner.run_async(user_input)                     │
│      ↓                                                      │
│  Orchestrator (Steps 1-5)                                   │
│      ↓                                                      │
│  Return JSON/markdown report immediately                    │
│      ↓                                                      │
│  User sees result in browser                                │
│                                                             │
│  Characteristics:                                           │
│  • Synchronous: User waits 30-60s for result               │
│  • Direct response: No queue, no Pub/Sub                   │
│  • Interactive: User can ask follow-up questions            │
│  • Session-based: Maintains conversation history           │
│  • SourceDetector output: "web_ui"                         │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  GITHUB API PATH (api_server.py + worker.py)               │
│                                                             │
│  GitHub Webhook → api_server.py /webhook/github            │
│      ↓                                                      │
│  Validate HMAC signature                                    │
│      ↓                                                      │
│  Publish to Pub/Sub queue                                   │
│      ↓                                                      │
│  Return 200 OK (< 100ms) ✅ GitHub happy                   │
│                                                             │
│  [Meanwhile, async in background...]                        │
│                                                             │
│  Pub/Sub → worker.py /process                               │
│      ↓                                                      │
│  Parse PR data from message                                 │
│      ↓                                                      │
│  Orchestrator (Steps 1-6)                                   │
│      ↓                                                      │
│  Post review to GitHub PR                                   │
│      ↓                                                      │
│  ACK Pub/Sub message (Step 7) ✅ Queue cleaned             │
│                                                             │
│  Characteristics:                                           │
│  • Asynchronous: GitHub doesn't wait                       │
│  • Queue-based: Handles 50+ concurrent PRs                 │
│  • Fire-and-forget: Review posted later                    │
│  • Stateless: One-shot per PR (no session)                 │
│  • SourceDetector output: "github_webhook"                 │
└─────────────────────────────────────────────────────────────┘
```

**Key Differences:**

| Aspect | main.py (Web UI) | api_server.py + worker.py (GitHub API) |
|--------|------------------|----------------------------------------|
| **Request Source** | Web UI (user browser) | GitHub webhook (API call) |
| **Response Model** | Synchronous (user waits) | Asynchronous (via Pub/Sub) |
| **User Waits?** | Yes (30-60s) | No (< 100ms ACK) |
| **Result Delivery** | HTTP response body | GitHub PR comment |
| **Session State** | Persistent (multi-turn) | Stateless (one-shot) |
| **Pub/Sub Queue** | Not needed | Required for scaling |
| **Concurrency** | 1-10 concurrent users | 50+ concurrent PRs |
| **SourceDetector** | Outputs "web_ui" | Outputs "github_webhook" |
| **Orchestrator Steps** | Steps 1-5 (no GitHub publish) | Steps 1-7 (full workflow) |

### Implementation Phases

**Phase 2A: Web UI Integration (main.py)**
1. ✅ Implement Steps 1-5 (SourceDetector → ReportSynthesizer)
2. ✅ Current `main.py` already has Runner + Session + Artifacts
3. Add FastAPI endpoints to `main.py`:
   ```python
   @app.post("/analyze")
   async def analyze_code(code: str, focus: str):
       result = await runner.run_async(...)
       return {"report": result}
   ```
4. Test with Web UI (user submits code, gets report)
5. **Decision Point:** If only building Web UI, stop here! No need for `worker.py`

**Phase 2B: GitHub API Integration (api_server.py + worker.py)**
1. Create `api_server.py` (FastAPI webhook receiver)
   - Endpoint: `/webhook/github`
   - Validates HMAC signature
   - Publishes to Pub/Sub
   - Returns 200 OK (< 100ms)
2. Create `worker.py` (ADK orchestrator with Pub/Sub)
   - Endpoint: `/process`
   - Receives Pub/Sub messages
   - Runs full orchestrator (Steps 1-7)
   - Posts review to GitHub
   - ACKs message
3. Add Steps 6-7 (GitHubPublisher → MessageAcknowledger)
4. Deploy both services to Cloud Run
5. Configure Pub/Sub with ACK/NACK logic
6. Set up dead letter queue
7. Configure GitHub webhook
8. **Use case:** Automated PR reviews at scale (50+ concurrent PRs)

**Architecture Status:** ✅ Design Complete - Ready for Implementation

**Key Achievement:** Replaced custom orchestration with pure ADK patterns while adding complete Pub/Sub lifecycle management (including message acknowledgment and cleanup). All 8 workflow steps are deterministic, scalable, and production-ready.

---

### 🎯 Clear Recommendation

**You are correct!** The architecture is:

```
┌──────────────────────────────────────────────────────────────┐
│  main.py = Web UI Backend (Synchronous)                     │
│  • User submits code via browser                            │
│  • Waits 30-60s for analysis result                         │
│  • Gets markdown report back immediately                    │
│  • Can ask follow-up questions (session-based)              │
│  • SourceDetector: "web_ui" → ClassifierAgent path          │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  api_server.py + worker.py = GitHub API Integration (Async) │
│  • GitHub sends webhook on PR open                          │
│  • api_server.py: Validates + queues (< 100ms ACK)         │
│  • worker.py: Processes PR + posts review (30-60s later)    │
│  • No user waiting, review appears on GitHub automatically  │
│  • SourceDetector: "github_webhook" → GitHubAgent path      │
└──────────────────────────────────────────────────────────────┘
```

**Start with Phase 2A:** Extend `main.py` for Web UI (add FastAPI endpoints)  
**Add Phase 2B later:** Create `api_server.py` + `worker.py` for GitHub automation

**You don't need both unless you want both Web UI AND GitHub integration!**
