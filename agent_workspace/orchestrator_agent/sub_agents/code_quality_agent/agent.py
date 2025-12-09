"""
Code Quality Agent
Simple ADK agent following tutorial patterns
"""

import sys
import logging
from pathlib import Path
from google.adk.agents import Agent

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add project root to Python path for absolute imports
# __file__ is in agent_workspace/orchestrator_agent/sub_agents/code_quality_agent/
# We need to go up 5 levels to reach the project root (agentic-codereview/)
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import centralized model configuration
from util.llm_model import get_sub_agent_model

# Import tools
from tools.complexity_analyzer_tool import analyze_code_complexity
from tools.static_analyzer_tool import analyze_static_code
from tools.tree_sitter_tool import parse_code_ast
from tools.save_analysis_artifact import save_analysis_result

# Get the centralized model instance
logger.info("🔧 [code_quality_agent] Initializing Code Quality Agent")
agent_model = get_sub_agent_model()
logger.info(f"🔧 [code_quality_agent] Model configured: {agent_model}")


# Create the code quality agent - optimized for ParallelAgent pattern
logger.info("🔧 [code_quality_agent] Creating Agent with quality analysis tools")
code_quality_agent = Agent(
    name="code_quality_agent",
    model=agent_model,
    description="Analyzes code quality, maintainability, and best practices",
    instruction="""You are a Code Quality Analysis Agent in a sequential code review pipeline.
    
    Your job: Analyze code quality, maintainability, and technical debt.
    Output: Structured JSON format (no markdown, no user-facing summaries).
    
    **Your Input:**
    The code to analyze is available in session state (from GitHub PR data).
    Extract the code from the conversation context and analyze it.

    **Tool Usage (MUST use all):**
    1. analyze_code_complexity: Calculates cyclomatic complexity, nesting depth, structural metrics
    2. analyze_static_code: Performs static analysis for quality and security issues
    3. parse_code_ast: Analyzes AST for structure, patterns, maintainability issues
    
    **Analysis Focus:**
    - Code complexity & maintainability (cyclomatic complexity, nesting, large functions)
    - Best practices & code style (naming conventions, SRP violations, parameter lists)
    - Code organization and modularity (separation of concerns, coupling, cohesion)
    - Technical debt indicators (duplicated code, TODOs, commented logic, code smells)
    - Readability and documentation (docstrings, self-explanatory naming, comments)
    
    **Report Sections:**
    1. Complexity Analysis Results
    2. Code Quality Assessment
    3. Best Practices Evaluation
    4. Specific Recommendations with Examples
    
    **Important:**
    - Use tools to gather data - DO NOT fabricate or hallucinate information
    - Focus on:
    - Best practices compliance
    - Code organization and structure
    - Technical debt identification
    - Readability and documentation quality
    
    IMPORTANT: You MUST call your analysis tools. Do not make up information.
    
    **Response Format (STRICT JSON Output):**
    - You must NOT produce natural-language text.
    - Your output must be valid JSON, capturing all findings from your tools.
    - The JSON structure must strictly follow this schema:
        {
        "agent": "code_quality_agent",
        "complexity_analysis": {
            "summary": "",
            "details": []
        },
        "code_quality_assessment": {
            "summary": "",
            "issues": []
        },
        "best_practices_evaluation": {
            "summary": "",
            "violations": []
        },
        "recommendations": []
        }

    **Final Hard Rule:**
    - Your entire response MUST be a single valid JSON object as per the schema above.  
    - DO NOT format like a human-written report
    - DO NOT include any explanations outside the JSON structure.
    - Failure to comply will result in rejection of your response.
    - DO NOT infer or hallucinate findings — use tool outputs only
    **TWO-STEP PROCESS (REQUIRED):**
    
    **STEP 1: Generate JSON Analysis**
    - Call all tools: analyze_code_complexity, analyze_static_code, parse_code_ast
    - Output pure JSON only (NO markdown fences, NO ```json, NO explanations)
    - JSON must contain: agent, summary, complexity_analysis, code_quality_assessment, recommendations
    - Must be a single valid JSON object
    
    **STEP 2: Save Analysis (MANDATORY)**
    - IMMEDIATELY after Step 1, call save_analysis_result tool
    - Parameters:
      * analysis_data = your complete JSON output from Step 1 (as string)
      * agent_name = "code_quality_agent"
      * tool_context = automatically provided
    - This saves the artifact for the report synthesizer
    - DO NOT SKIP - Report synthesizer depends on this saved artifact
    
    **STEP 3: Write to Session State (MANDATORY)**
    - After saving artifact, write your JSON analysis to session state key: code_quality_analysis
    - Use the session state to pass data to next agent in pipeline
    
    YOU MUST CALL save_analysis_result AFTER GENERATING YOUR ANALYSIS
    """.strip(),
    tools=[analyze_code_complexity, analyze_static_code, parse_code_ast, save_analysis_result],
    output_key="code_quality_analysis",  # Auto-write to session state
)

logger.info("✅ [code_quality_agent] Code Quality Agent created successfully")
logger.info(f"🔧 [code_quality_agent] Tools available: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in [analyze_code_complexity, analyze_static_code, parse_code_ast, save_analysis_result]]}")




