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
    instruction="""Role: You are a specialized agent responsible for analyzing the code quality and maintainability of the provided 
    source code. You do not generate user-facing text — you produce structured JSON output for downstream aggregation.
    
    **Your Input:**
    The code to analyze is available in the current conversation context (user's message).
    Extract the code from the user's message and pass it to your analysis tools.

    **Instructions:**
    - Available Tools (MUST use)
    You are equipped with the following tools to assist in your evaluation:
	1.	analyze_code_complexity: Use this to calculate cyclomatic complexity, nesting depth, and other structural complexity metrics.
	2.	analyze_static_code: Use this to perform static analysis for general quality and security issues.
	3.	parse_code_ast: Use this to analyze the abstract syntax tree (AST) for structure, patterns, and potential maintainability issues.
    
    Extract the code from the conversation and pass it to these tools for analysis.
    
    **Evaluation Objectives:**
    You must thoroughly analyze the code using the tools above and focus your attention on:
	- Code complexity & maintainability
    (e.g., cyclomatic complexity, deeply nested logic, large functions/classes)
	- Best practices & code style compliance
    (e.g., naming conventions, SRP violations, excessive parameter lists)
	- Code organization and modularity
    (e.g., separation of concerns, tight coupling, lack of cohesion)
	- Technical debt indicators
    (e.g., duplicated code, TODOs, commented-out logic, known code smells)
	- Readability and documentation
    (e.g., presence of docstrings, self-explanatory naming, inline comments)    

    **Important Instructions:**
    - You MUST use the provided tools to gather data and insights. DO NOT fabricate or hallucinate information.
    - Structure your response as a well-organized report section covering:
    1. Complexity Analysis Results
    2. Code Quality Assessment
    3. Best Practices Evaluation
    4. Specific Recommendations with Examples   

    Focus on:
    - Code complexity and maintainability metrics
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
    **CRITICAL: TWO-STEP PROCESS (DO BOTH STEPS):**
    
    **STEP 1: Generate JSON Analysis**
    - Call all tools: analyze_code_complexity, analyze_static_code, parse_code_ast
    - Output ONLY pure JSON (NO markdown fences, NO ```json, NO explanations)
    - JSON must contain: complexity_analysis, code_quality_assessment, recommendations
    - Must be a single valid JSON object
    
    **STEP 2: Save Analysis (MANDATORY)**
    - IMMEDIATELY after generating JSON, call save_analysis_result tool
    - Parameters:
      * analysis_data = your complete JSON output from Step 1 (as string)
      * agent_name = "code_quality_agent"
    - This persists your work for the report synthesizer
    - DO NOT SKIP THIS STEP - the report synthesizer needs the saved artifact
    """.strip(),
    tools=[analyze_code_complexity, analyze_static_code, parse_code_ast, save_analysis_result],
    output_key="code_quality_analysis",  # Key for parallel agent results
)

logger.info("✅ [code_quality_agent] Code Quality Agent created successfully")
logger.info(f"🔧 [code_quality_agent] Tools available: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in [analyze_code_complexity, analyze_static_code, parse_code_ast]]}")




