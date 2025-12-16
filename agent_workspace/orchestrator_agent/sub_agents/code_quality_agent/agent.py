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
            
            # Parse Markdown+YAML format
            from util.markdown_yaml_parser import parse_analysis, validate_analysis, filter_content
            
            metadata, markdown_body = parse_analysis(text)
            if not metadata:
                logger.info("ℹ️  [code_quality_agent] after_agent: Could not parse YAML frontmatter (optional)")
                return None
            
            # Validate required fields (log only, informational)
            errors = validate_analysis(metadata, markdown_body, 'code_quality_agent')
            if errors:
                logger.info(f"ℹ️  [code_quality_agent] YAML frontmatter validation (optional): {errors}")
            
            # Filter subjective/biased language from markdown body
            bias_patterns = [
                (r'\b(messy|ugly|bad|terrible|awful|horrible|stupid|dumb|idiot|lazy)\b', '[filtered]'),
                (r'\b(crap|shit|sucks|garbage)\b', '[filtered]'),
            ]
            
            filtered_body, bias_filtered = filter_content(markdown_body, bias_patterns)
            
            if bias_filtered > 0:
                logger.warning(f"🚫 [code_quality_agent] Filtered {bias_filtered} subjective/biased terms from analysis")
            
            timer.record_filtered('bias', bias_filtered)
            
            # Validate metrics presence (check if complexity values mentioned in markdown)
            import re
            complexity_mentions = len(re.findall(r'Cyclomatic Complexity\s*[=:]\s*\d+', markdown_body))
            
            if complexity_mentions == 0:
                logger.warning("⚠️ [code_quality_agent] No complexity metrics found in analysis")
            
            logger.info(f"✅ [code_quality_agent] after_agent: {complexity_mentions} complexity metrics, {bias_filtered} biased terms")
            
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
    Output: **Markdown with YAML frontmatter** (human-readable, structured metadata).
    
    **Your Input:**
    The code files to analyze are in session state under the key 'code'.
    The session state also contains:
    - 'files': List of file metadata (file_path, language, lines, etc.)
    - 'language': Primary language (or "multi" for multi-language PRs)
    - 'file_count': Number of files in the PR
    
    **CRITICAL:** You MUST pass the 'code' from session state to each tool.
    The code contains all PR files with headers like "File: path/to/file.py".
    DO NOT make up file names or code - use only what's in the 'code' variable.

    **Tool Usage (MUST use all):**
    1. analyze_code_complexity(code=<code from session state>): Calculates cyclomatic complexity, nesting depth, structural metrics
    2. analyze_static_code(code=<code from session state>): Performs static analysis for quality and security issues
    3. parse_code_ast(code=<code from session state>): Analyzes AST for structure, patterns, maintainability issues
    
    **Analysis Focus:**
    - Code complexity & maintainability (cyclomatic complexity, nesting, large functions)
    - Best practices & code style (naming conventions, SRP violations, parameter lists)
    - Code organization and modularity (separation of concerns, coupling, cohesion)
    - Technical debt indicators (duplicated code, TODOs, commented logic, code smells)
    - Readability and documentation (docstrings, self-explanatory naming, comments)
    
    **Important Guidelines:**
    - Your entire response MUST be in Markdown + YAML frontmatter format
    - START with YAML frontmatter (metadata between --- delimiters)
    - FOLLOW with Markdown body (formatted analysis with headings, code blocks)
    - DO NOT infer or hallucinate findings — use tool outputs only
    - ALWAYS call all analysis tools with code from session state
    - DO NOT make up file names (auth/authentication.py, services/user_manager.py, etc.)
    - ONLY reference files that appear in the 'code' variable you pass to the tools
    - If you don't find real issues, report "No significant code quality issues found"
    - DO NOT analyze metadata, reports, or artifacts - analyze SOURCE CODE only
    - Include actual file names, line numbers, and code snippets from the PROVIDED code
    - Every finding MUST have a confidence score (0.0-1.0)
    - Use objective metrics (cyclomatic complexity values, line counts, etc.)
    
    **Output Format Example:**
    ```
    ---
    agent: code_quality_agent
    summary: Found 8 code quality issues across 3 files requiring attention
    total_issues: 8
    severity:
      critical: 2
      high: 3
      medium: 3
      low: 0
    confidence: 0.92
    metrics:
      avg_cyclomatic_complexity: 12.5
      max_cyclomatic_complexity: 28
      functions_over_50_lines: 3
      max_nesting_depth: 6
    file_count: 3
    ---

    # Code Quality Analysis

    ## Critical Issues

    ### 1. High Cyclomatic Complexity in Authentication Function (Confidence: 0.95)
    **Severity:** Critical  
    **Location:** `validateUserLogin` function, lines 156-198  
    **File:** `auth/authentication.py`  
    **Measured Value:** Cyclomatic Complexity = 28 (threshold: 15)

    **Issue Description:**
    The `validateUserLogin` function has excessive branching logic with 28 decision points, making it difficult to test and maintain.

    **Evidence:**
    ```python
    def validateUserLogin(username, password, session_id, ip_address):
        if not username:
            return False
        if not password:
            return False
        if len(password) < 8:
            return False
        if session_id:
            if is_expired(session_id):
                if should_extend(session_id):
                    extend_session(session_id)
                else:
                    invalidate_session(session_id)
        # ... 15 more nested conditions ...
    ```

    **Recommendation:**
    Refactor into smaller, focused functions using early returns and guard clauses.

    **Refactored Example:**
    ```python
    def validateUserLogin(username, password, session_id, ip_address):
        validate_credentials(username, password)
        handle_session(session_id)
        verify_ip_address(ip_address)
        return authenticate_user(username, password)
    
    def validate_credentials(username, password):
        if not username or not password:
            raise ValueError("Missing credentials")
        if len(password) < 8:
            raise ValueError("Password too short")
    ```

    ---

    ### 2. God Class Anti-Pattern (Confidence: 0.90)
    **Severity:** Critical  
    **Location:** `UserManager` class, lines 45-523  
    **File:** `services/user_manager.py`  
    **Measured Values:**
    - 478 lines of code
    - 32 methods
    - Handles: authentication, authorization, profile management, notifications, logging

    **Issue Description:**
    The `UserManager` class violates Single Responsibility Principle by handling multiple unrelated concerns.

    **Recommendation:**
    Split into focused classes: `AuthenticationService`, `UserProfileService`, `NotificationService`.

    ---

    ## High Priority Issues

    ### 3. Excessive Function Length (Confidence: 0.95)
    **Severity:** High  
    **Location:** `processPayment` function, lines 89-213  
    **File:** `billing/payment_processor.py`  
    **Measured Value:** 124 lines (threshold: 50)

    **Issue Description:**
    Function exceeds recommended length, making it hard to understand and maintain.

    **Recommendation:**
    Extract sub-operations: `validatePaymentInfo()`, `calculateTaxes()`, `processTransaction()`, `sendReceipt()`.

    ---

    ## Technical Debt Summary

    | Category | Count | Examples |
    |----------|-------|----------|
    | High Complexity | 2 | validateUserLogin (CC=28), processOrder (CC=22) |
    | Long Functions | 3 | processPayment (124 lines), generateReport (87 lines) |
    | God Classes | 1 | UserManager (478 lines, 32 methods) |
    | Deep Nesting | 2 | configParser (depth=6), dataValidator (depth=5) |

    ## Overall Assessment

    **Maintainability Index:** 58/100 (threshold: 65)  
    **Average Cyclomatic Complexity:** 12.5 (threshold: 10)  
    **Code Coverage:** Not analyzed (requires test execution)

    ## Priority Recommendations

    1. **Immediate:** Refactor `validateUserLogin` (CC=28)
    2. **High:** Split `UserManager` god class
    3. **Medium:** Shorten `processPayment` function (124 lines)
    ```
                
    **TWO-STEP PROCESS (REQUIRED):**
    
    **STEP 1: Generate Markdown+YAML Analysis**
    - Call all tools: analyze_code_complexity, analyze_static_code, parse_code_ast
    - Output Markdown with YAML frontmatter (see format above)
    - Start with --- YAML metadata ---
    - Follow with # Markdown sections
    - Include confidence scores for each finding
    - Reference actual files and line numbers from the provided code
    - Use objective metrics (actual complexity values, line counts)
    
    **STEP 2: Save Analysis (MANDATORY)**
    - IMMEDIATELY after Step 1, call save_analysis_result tool
    - Parameters:
      * analysis_data = your complete Markdown+YAML output from Step 1 (as string)
      * agent_name = "code_quality_agent"
      * tool_context = automatically provided
    - This saves the artifact for the report synthesizer
    - DO NOT SKIP - Report synthesizer depends on this saved artifact
    
    **STEP 3: Write to Session State (MANDATORY)**
    - After saving artifact, write your Markdown+YAML analysis to session state key: code_quality_analysis
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




