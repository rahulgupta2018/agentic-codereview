"""
Code Quality Agent
Simple ADK agent following tutorial patterns

With Phase 1 Guardrails:
- before_model_callback: Enforce objective, metric-based analysis
- after_tool_callback: Validate complexity metrics and ranges
- after_agent_callback: Remove subjective language, validate evidence
"""

import sys
import json
import logging
from pathlib import Path
from google.adk.agents import Agent
from google.genai import types

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

# Import callback utilities
from util.callbacks import (
    filter_bias,
    validate_metrics,
    execute_callback_safe,
    parse_json_safe,
    format_json_safe,
    get_config
)
from util.metrics import CallbackTimer, get_metrics_collector

# Get the centralized model instance
logger.info("🔧 [code_quality_agent] Initializing Code Quality Agent")
agent_model = get_sub_agent_model()
logger.info(f"🔧 [code_quality_agent] Model configured: {agent_model}")


# ============================================================================
# CALLBACK FUNCTIONS (Phase 1 Guardrails)
# ============================================================================

def quality_agent_before_model(callback_context, llm_request):
    """
    Before Model Callback - Enforce objective, metric-based analysis.
    
    Guardrails:
    - Enforce objective, metric-based analysis
    - Load acceptable threshold ranges from config
    - Require evidence for all quality claims
    """
    with CallbackTimer("code_quality_agent", "before_model") as timer:
        try:
            quality_guidance = """

---
CODE QUALITY ANALYSIS REQUIREMENTS:
1. Base ALL findings on measurable metrics (cyclomatic complexity, coupling, etc.)
2. Do NOT use subjective language ("messy", "ugly", "bad", "terrible", "awful")
3. Consider project context (size, team, domain)
4. Provide actionable refactoring suggestions with examples
5. Acknowledge when code meets acceptable standards
6. Use objective metrics: cyclomatic_complexity, nesting_depth, function_length, parameter_count
7. State the actual measured value, not just "high" or "low"

Acceptable Thresholds (from config):
- Cyclomatic Complexity: 1-15 (acceptable), 16-30 (warning), 31+ (critical)
- Function Length: <50 lines (good), 50-100 (acceptable), 100+ (warning)
- Nesting Depth: <=3 (good), 4-5 (acceptable), 6+ (warning)
- Parameters: <=4 (good), 5-7 (acceptable), 8+ (warning)
---
"""
            llm_request.config.system_instruction += quality_guidance
            logger.debug("✅ [code_quality_agent] before_model: Injected quality guidance")
            return None  # Allow with modifications
        
        except Exception as e:
            logger.error(f"❌ [code_quality_agent] before_model error: {e}")
            return None  # Fail open


def quality_agent_after_tool(tool, args, tool_context, tool_response):
    """
    After Tool Callback - Validate complexity metrics and ranges.
    
    Args:
        tool: Tool object or name
        args: Tool arguments (dict)
        tool_context: Tool execution context
        tool_response: Tool response (dict)
    
    Returns:
        Modified tool_response or None
    """
    with CallbackTimer("code_quality_agent", "after_tool") as timer:
        try:
            tool_name = tool if isinstance(tool, str) else getattr(tool, 'name', str(tool))
            if tool_name not in ['analyze_code_complexity', 'analyze_static_code']:
                return None
            
            if not isinstance(tool_response, dict):
                logger.warning("⚠️ [code_quality_agent] after_tool: tool_response not a dict")
                return None
            
            # Sanity check complexity values
            if 'cyclomatic_complexity' in tool_response:
                cc = tool_response['cyclomatic_complexity']
                if isinstance(cc, (int, float)):
                    if cc < 1 or cc > 1000:
                        logger.error(f"🚫 [code_quality_agent] Impossible complexity value: {cc}")
                        tool_response['cyclomatic_complexity'] = 'N/A'
                        timer.record_filtered('invalid_metrics', 1)
            
            # Check for null/undefined metrics
            required_metrics = ['cyclomatic_complexity', 'maintainability_index', 'cognitive_complexity']
            for key in required_metrics:
                if key in tool_response and tool_response[key] is None:
                    logger.debug(f"⚠️ [code_quality_agent] Null metric: {key}")
                    tool_response[key] = 'N/A'
            
            # Validate maintainability index (0-100 scale)
            if 'maintainability_index' in tool_response:
                mi = tool_response['maintainability_index']
                if isinstance(mi, (int, float)):
                    if mi < 0 or mi > 100:
                        logger.warning(f"⚠️ [code_quality_agent] Invalid maintainability index: {mi}")
                        tool_response['maintainability_index'] = max(0, min(100, mi))
            
            return tool_response
        
        except Exception as e:
            logger.error(f"❌ [code_quality_agent] after_tool error: {e}")
            return None  # Fail open


def quality_agent_after_agent(callback_context):
    """
    After Agent Callback - Validate quality metrics, log bias (validation only).
    
    Note: ADK only passes callback_context (no content parameter).
    Accesses agent output via session state for validation.
    
    Quality Gates:
    - Check for subjective language in descriptions
    - Validate metrics are evidence-based
    - Record bias detection metrics
    """
    with CallbackTimer("code_quality_agent", "after_agent") as timer:
        try:
            # Access code quality analysis from session state
            text = callback_context.state.get('code_quality_analysis', '')
            if not text:
                logger.warning("⚠️ [code_quality_agent] No code_quality_analysis in state")
                return None
            
            # Parse JSON
            analysis = parse_json_safe(text)
            if not analysis:
                logger.warning("⚠️ [code_quality_agent] after_agent: Could not parse JSON")
                return None
            
            # Filter subjective language from all text fields
            bias_filtered = 0
            
            # Filter in complexity_analysis
            if 'complexity_analysis' in analysis:
                for detail in analysis['complexity_analysis'].get('details', []):
                    if 'description' in detail:
                        original = detail['description']
                        filtered, count = filter_bias(original)
                        if count > 0:
                            detail['description'] = filtered
                            bias_filtered += count
            
            # Filter in code_quality_assessment
            if 'code_quality_assessment' in analysis:
                for issue in analysis['code_quality_assessment'].get('issues', []):
                    if 'description' in issue:
                        original = issue['description']
                        filtered, count = filter_bias(original)
                        if count > 0:
                            issue['description'] = filtered
                            bias_filtered += count
            
            # Filter in best_practices_evaluation
            if 'best_practices_evaluation' in analysis:
                for violation in analysis['best_practices_evaluation'].get('violations', []):
                    if 'description' in violation:
                        original = violation['description']
                        filtered, count = filter_bias(original)
                        if count > 0:
                            violation['description'] = filtered
                            bias_filtered += count
            
            # Filter in recommendations
            for rec in analysis.get('recommendations', []):
                if 'description' in rec:
                    original = rec['description']
                    filtered, count = filter_bias(original)
                    if count > 0:
                        rec['description'] = filtered
                        bias_filtered += count
            
            timer.record_filtered('bias', bias_filtered)
            
            # Validate metrics presence
            is_valid, missing = validate_metrics(analysis)
            if not is_valid:
                logger.warning(f"⚠️ [code_quality_agent] Missing metrics: {len(missing)} issues")
            
            logger.info(f"✅ [code_quality_agent] after_agent: Detected {bias_filtered} biased terms")
            
            return None  # Validation only, no content modification
        
        except Exception as e:
            logger.error(f"❌ [code_quality_agent] after_agent error: {e}")
            return None  # Fail open


# ============================================================================
# AGENT DEFINITION
# ============================================================================


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
    tools=[analyze_code_complexity, analyze_static_code, save_analysis_result],
    output_key="code_quality_analysis",  # Auto-write to session state
    
    # Phase 1 Guardrails: Callbacks
    before_model_callback=quality_agent_before_model,
    after_tool_callback=quality_agent_after_tool,
    after_agent_callback=quality_agent_after_agent,
)

logger.info("✅ [code_quality_agent] Code Quality Agent created successfully")
logger.info(f"🔧 [code_quality_agent] Tools available: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in [analyze_code_complexity, analyze_static_code, parse_code_ast, save_analysis_result]]}")
logger.info("🛡️ [code_quality_agent] Phase 1 Guardrails enabled: before_model, after_tool, after_agent callbacks")




