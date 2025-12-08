"""Planning Agent

Intelligent agent selection using PlanReActPlanner.
Determines which analysis agents should run based on request context.

This agent:
- Analyzes code review request intent
- Selects appropriate analysis agents (security, quality, practices, carbon)
- Determines execution strategy (parallel vs sequential)
- Uses proxy tools for agent selection (Plan-ReAct pattern)
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

from google.adk.agents import Agent
from google.adk.planners import PlanReActPlanner
from google.adk.tools import FunctionTool

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from util.llm_model import get_sub_agent_model


def create_planning_agent(pipeline_type: str = "web") -> Agent:
    """
    Create planning agent with PlanReActPlanner and proxy tools.
    
    Args:
        pipeline_type: "web" for Web Pipeline (uses request_classification)
                      "github" for GitHub Pipeline (uses github_pr_data)
    
    This agent uses the Plan-ReAct pattern:
    - Plan: Analyze request and decide which agents to run
    - ReAct: Use proxy tools to "select" agents
    - Output: Execution plan with selected agents and execution mode
    
    Returns:
        Agent: Planning agent with PlanReActPlanner
    """
    agent_model = get_sub_agent_model()
    
    # =========================================================================
    # PROXY TOOLS FOR AGENT SELECTION
    # =========================================================================
    # These tools don't actually execute agents - they're selection markers
    # The orchestrator reads the tool calls to determine which agents to run
    
    def select_security_analysis() -> Dict[str, Any]:
        """Proxy tool for selecting security analysis agent."""
        return {
            'status': 'success',
            'agent': 'security',
            'report': 'Security analysis agent selected'
        }
    
    def select_quality_analysis() -> Dict[str, Any]:
        """Proxy tool for selecting code quality analysis agent."""
        return {
            'status': 'success',
            'agent': 'code_quality',
            'report': 'Code quality analysis agent selected'
        }
    
    def select_practices_analysis() -> Dict[str, Any]:
        """Proxy tool for selecting engineering practices analysis agent."""
        return {
            'status': 'success',
            'agent': 'engineering',
            'report': 'Engineering practices analysis agent selected'
        }
    
    def select_carbon_analysis() -> Dict[str, Any]:
        """Proxy tool for selecting carbon footprint analysis agent."""
        return {
            'status': 'success',
            'agent': 'carbon',
            'report': 'Carbon footprint analysis agent selected'
        }
    
    # Create FunctionTools from proxy functions
    planning_tools = [
        FunctionTool(select_security_analysis),
        FunctionTool(select_quality_analysis),
        FunctionTool(select_practices_analysis),
        FunctionTool(select_carbon_analysis)
    ]
    
    # =========================================================================
    # CREATE PLANNING AGENT WITH PLAN-REACT PLANNER
    # =========================================================================
    
    # Build instruction based on pipeline type
    if pipeline_type == "github":
        instruction = """You are an intelligent code review planning agent for GitHub PR analysis.

**CONTEXT:**
You are in the GitHub Pipeline. The previous agent (GitHub Fetcher) has retrieved PR data.

**INPUT DATA:**
- github_pr_data: Summary of what was fetched
- github_pr_files: Actual file contents
- github_pr_metadata: PR metadata (title, author, etc.)
- github_pr_stats: Statistics (additions, deletions, languages)

**YOUR JOB:**
Select which analysis agents should run on this PR.

**DEFAULT BEHAVIOR:**
For GitHub PRs, ALWAYS run ALL agents (comprehensive analysis):
- Security analysis
- Code quality analysis  
- Engineering practices analysis
- Carbon footprint analysis

**EXECUTION:**

<ACTION>
Call ALL four proxy tools:
1. select_security_analysis()
2. select_quality_analysis()
3. select_practices_analysis()
4. select_carbon_analysis()
</ACTION>

<FINAL_ANSWER>
{
    "selected_agents": ["security", "code_quality", "engineering", "carbon"],
    "execution_mode": "sequential",
    "reasoning": "GitHub PR review requires comprehensive analysis of all aspects.",
    "estimated_duration": "2-4 minutes",
    "analysis_focus": {
        "security": "High priority - check for vulnerabilities",
        "code_quality": "High priority - assess maintainability",
        "engineering": "High priority - verify best practices",
        "carbon": "Medium priority - evaluate efficiency"
    }
}
</FINAL_ANSWER>

**Note:** GitHub PRs get full comprehensive analysis. This is NOT configurable - always select all agents."""
    else:
        # Web pipeline instruction
        instruction = """You are an intelligent code review planning agent using the Plan-ReAct pattern.

**STEP 1: Read classifier output from session state**

Check the request_classification from the previous agent (classifier):
- Access: {request_classification}
- Key fields: type, has_code, focus_areas, confidence

**STEP 2: Handle general queries (no code analysis needed)**

If request_classification.type == "general_query" OR has_code == false:

<FINAL_ANSWER>
{
  "selected_agents": [],
  "execution_mode": "none",
  "reasoning": "General query detected by classifier - no code to analyze. Classifier will provide informational response.",
  "request_type": "general_query",
  "skip_analysis": true
}
</FINAL_ANSWER>

**STEP 3: For code review requests, plan agent selection**

If has_code == true, follow the Plan-ReAct pattern:

<PLANNING>
Break down the code review request into clear steps:
1. Understand Intent: Check request_classification.type (comprehensive, security-focused, etc.)
2. Identify Required Analyses based on classifier output:
   - Security: For auth, input validation, vulnerabilities
   - Quality: For complexity, maintainability, code smells
   - Practices: For SOLID, design patterns, best practices
   - Carbon: For performance, efficiency, optimization
3. Determine Execution Strategy: Parallel (default) or Sequential (rare)
</PLANNING>

<REASONING>
Explain your logic for agent selection:

**Decision Matrix:**
- Comprehensive Review → All agents (security, quality, practices, carbon) → Parallel
- Security Focus → Security only → Parallel (single agent)
- Quality Focus → Quality + Practices → Parallel (independent)
- Performance Focus → Carbon + Quality → Parallel (independent)
- Multiple Areas → Specified agents → Parallel (usually independent)
- Best Practices → Practices + Quality → Parallel (independent)

**Key Considerations:**
- User's explicit requests take priority
- Comprehensive reviews include all agents
- Performance-critical code needs carbon analysis
- Most analyses are independent → use parallel execution
- Sequential only if true dependency exists (very rare)
</REASONING>

<ACTION>
Call the appropriate select_*_analysis tools:
- select_security_analysis() for security analysis
- select_quality_analysis() for code quality analysis
- select_practices_analysis() for engineering practices analysis
- select_carbon_analysis() for carbon footprint analysis

You can call multiple tools in the same turn for comprehensive reviews.
</ACTION>

<OBSERVATION>
Note the results of your tool calls:
- Which tools were successfully called?
- What agents were selected?
- Are the selections appropriate for the request?
</OBSERVATION>

<REPLANNING>
If you encounter issues or realize the initial plan needs adjustment:
1. Explain what went wrong or what you missed
2. Describe the new plan
3. Execute the adjusted plan

Note: Only use this section if replanning is actually needed.
</REPLANNING>

<FINAL_ANSWER>
Provide your execution plan in JSON format:

{
    "selected_agents": ["security", "code_quality", "engineering"],
    "execution_mode": "parallel",
    "reasoning": "User requested comprehensive review. All analyses are independent so parallel execution provides fastest results.",
    "estimated_duration": "3-5 minutes",
    "analysis_focus": {
        "security": "High priority - code handles user input",
        "code_quality": "Medium priority - check complexity",
        "engineering": "Medium priority - verify best practices"
    }
}

**JSON Schema:**
- selected_agents: Array of agent names that were selected via tool calls
- execution_mode: "parallel" (default) or "sequential" (rare)
- reasoning: Clear explanation of selection rationale
- estimated_duration: Time estimate (e.g., "3-5 minutes")
- analysis_focus: Object with priority and reason for each selected agent
</FINAL_ANSWER>

**Error Handling:**
- No code detected → Provide advisory response with recommendations
- Unclear intent → Default to comprehensive review (all agents)
- Invalid request → Return error JSON with clear explanation

**Important Guidelines:**
1. Always use the structured tags: <PLANNING>, <REASONING>, <ACTION>, <OBSERVATION>, <FINAL_ANSWER>
2. Use <REPLANNING> only if your initial plan needs adjustment
3. Tool calls are proxy selections - orchestrator executes the actual agents
4. Be systematic but decisive - don't overthink simple requests
5. selected_agents in JSON must match your tool calls
"""
    
    planning_agent = Agent(
        name=f"planning_agent_{pipeline_type}",
        model=agent_model,
        planner=PlanReActPlanner(),
        tools=planning_tools,
        instruction=instruction,
        output_key="execution_plan"
    )
    
    logger.info(f"✅ Created PlanningAgent ({pipeline_type}) with PlanReActPlanner and 4 proxy tools")
    
    return planning_agent


# Create agent instances for import by orchestrator
planning_agent = create_planning_agent("web")  # Default for backward compatibility
planning_agent_github = create_planning_agent("github")
