"""
Engineering Practices Agent  
Simple engineering practices analysis agent following ADK parallel agent patterns

With Phase 1 Guardrails:
- before_model_callback: Inject context-aware guidance, avoid architectural dogma
- after_agent_callback: Filter dogmatic recommendations, validate trade-offs
"""

import sys
import json
import re
import logging
from pathlib import Path
from google.adk.agents import Agent
from google.genai import types

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add project root to Python path for absolute imports
# __file__ is in agent_workspace/orchestrator_agent/sub_agents/engineering_practices_agent/
# We need to go up 5 levels to reach the project root (agentic-codereview/)
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import centralized model configuration
from util.llm_model import get_sub_agent_model

# Import tools
from tools.engineering_practices_evaluator import evaluate_engineering_practices

# Import callback utilities
from util.callbacks import (
    filter_bias,
    execute_callback_safe
)
from util.metrics import CallbackTimer, get_metrics_collector

# Get the centralized model instance
logger.info("🔧 [engineering_practices_agent] Initializing Engineering Practices Agent")
agent_model = get_sub_agent_model()
logger.info(f"🔧 [engineering_practices_agent] Model configured: {agent_model}")


# ============================================================================
# CALLBACK FUNCTIONS (Phase 1 Guardrails)
# ============================================================================

def engineering_agent_before_model(callback_context, llm_request):
    """
    Before Model Callback - Inject context-aware guidance, avoid dogma.
    
    Guardrails:
    - Inject context-aware guidance
    - Load bias prevention rules for architecture
    - Require pragmatic recommendations
    """
    with CallbackTimer("engineering_practices_agent", "before_model") as timer:
        try:
            engineering_guidance = """

---
ENGINEERING PRACTICES EVALUATION:
1. Consider project context (team size, complexity, domain)
2. Multiple valid approaches exist - avoid dogma
3. Balance ideal architecture vs practical constraints
4. Provide trade-off analysis for recommendations
5. Acknowledge when existing patterns are appropriate
6. DO NOT use absolutist language: "must use", "always", "never", "only acceptable"
7. Present trade-offs: performance vs maintainability, simplicity vs flexibility

Architecture Guidelines:
- Not all projects need microservices (consider monolith-first for small teams)
- Design patterns should fit the problem (avoid pattern abuse)
- SOLID principles are goals, not strict rules
- Pragmatic solutions > perfect architecture
- Document WHY a pattern was chosen, not just WHAT
---
"""
            llm_request.config.system_instruction += engineering_guidance
            logger.debug("✅ [engineering_practices_agent] before_model: Injected engineering guidance")
            return None  # Allow with modifications
        
        except Exception as e:
            logger.error(f"❌ [engineering_practices_agent] before_model error: {e}")
            return None  # Fail open


def engineering_agent_after_agent(callback_context):
    """
    After Agent Callback - Validate file paths and filter dogmatic language.
    
    Note: ADK only passes callback_context (no content parameter).
    Accesses agent output via session state for validation.
    
    Quality Gates:
    - Validate that file paths mentioned exist in actual PR files
    - Detect dogmatic architectural recommendations
    - Check for bias/profanity
    - Record metrics (validation only)
    """
    with CallbackTimer("engineering_practices_agent", "after_agent") as timer:
        try:
            # Access engineering practices analysis from session state
            text = callback_context.state.get('engineering_practices_analysis', '')
            if not text:
                logger.warning("⚠️ [engineering_practices_agent] No analysis in state")
                return None
            
            # Get actual PR files for validation
            actual_files = []
            files_metadata = callback_context.state.get('files', [])
            if files_metadata:
                actual_files = [f.get('file_path', '') for f in files_metadata]
            
            # Parse Markdown+YAML format
            from util.markdown_yaml_parser import parse_analysis, validate_analysis, filter_content
            
            metadata, markdown_body = parse_analysis(text)
            if not metadata:
                logger.info("ℹ️  [engineering_practices_agent] after_agent: Could not parse YAML frontmatter (optional)")
                return None
            
            # Validate required fields (log only, informational)
            errors = validate_analysis(metadata, markdown_body, "engineering_practices_agent")
            if errors:
                logger.info("ℹ️  [engineering_practices_agent] YAML frontmatter validation (optional): %s", errors)
            
            # GUARDRAIL: Validate file paths (Option 3)
            hallucination_count = 0
            if actual_files:
                # Extract file paths mentioned in the report
                mentioned_files = re.findall(r'`([^`]+\.(py|tsx|ts|js|java|go|cpp|c|h))`', markdown_body)
                mentioned_files = [f[0] for f in mentioned_files]  # Extract just the path
                
                # Check for hallucinated file paths
                for mentioned in mentioned_files:
                    # Check if any actual file matches (allow partial matches)
                    if not any(mentioned in actual or actual.endswith(mentioned) for actual in actual_files):
                        hallucination_count += 1
                        logger.warning(f"🚫 [engineering_practices_agent] Hallucinated file path detected: {mentioned}")
                        logger.warning(f"   Actual files in PR: {actual_files}")
                
                if hallucination_count > 0:
                    logger.warning(f"🚫 [engineering_practices_agent] Detected {hallucination_count} hallucinated file references")
                    timer.record_filtered('hallucinated_files', hallucination_count)
            
            # Check for dogmatic recommendations in markdown body
            dogma_patterns = [
                (r'\bmust use microservices\b', 'consider using microservices'),
                (r'\balways use\b', 'typically use'),
                (r'\bnever use\b', 'avoid using'),
                (r'\bonly.*is acceptable\b', 'is recommended'),
                (r'\bshould always\b', 'should typically'),
                (r'\bmust follow\b', 'should follow'),
            ]
            
            filtered_body, dogma_filtered = filter_content(markdown_body, dogma_patterns)
            
            if dogma_filtered > 0:
                logger.warning(f"🚫 [engineering_practices_agent] Detected {dogma_filtered} dogmatic recommendations")
            
            timer.record_filtered('dogma', dogma_filtered)
            
            # Filter bias/profanity
            bias_patterns = [
                (r'\b(stupid|dumb|idiot|lazy|incompetent)\b', '[filtered]'),
                (r'\b(crap|shit|sucks)\b', '[filtered]'),
            ]
            
            filtered_body, bias_filtered = filter_content(filtered_body, bias_patterns)
            
            if bias_filtered > 0:
                logger.warning(f"🚫 [engineering_practices_agent] Filtered {bias_filtered} biased terms")
            
            timer.record_filtered('bias', bias_filtered)
            
            logger.info(f"✅ [engineering_practices_agent] after_agent: Hallucinated files={hallucination_count}, Dogma={dogma_filtered}, Bias={bias_filtered}")
            
            return None  # Validation only, no content modification
        
        except Exception as e:
            logger.error(f"❌ [engineering_practices_agent] after_agent error: {e}")
            return None  # Fail open


# ============================================================================
# AGENT DEFINITION
# ============================================================================

# Engineering Practices Agent optimized for ParallelAgent pattern
logger.info("🔧 [engineering_practices_agent] Creating Agent with engineering evaluation tools")
engineering_practices_agent = Agent(
    name="engineering_practices_agent",
    model=agent_model,
    description="Evaluates software engineering best practices and development workflows",
    instruction="""
You are the Engineering Practices Analysis Agent. Your job is to evaluate engineering best practices in the PR codebase and report them with evidence.

CRITICAL FORMAT REQUIREMENT
- Your response MUST begin with the YAML frontmatter.
- Do not write any text before the opening '---'.

IMPORTANT REALITY CHECK
- The PR code is stored in shared session state under the key "code".
- You (the LLM) do NOT read session state directly.
- The tool evaluate_engineering_practices reads the PR code from session state internally.
- The tool output is the ONLY source of truth.

STEP 1: Run the engineering practices evaluation (MANDATORY)
- ALWAYS call evaluate_engineering_practices() exactly once at the start of your analysis.
- Do NOT skip this call.
- Do NOT invent issues before the evaluation results are available.

STEP 2: Analyze the tool output (SOURCE OF TRUTH)
- Use ONLY the tool output for:
  - file paths
  - line numbers
  - code snippets / evidence
  - severity
  - issue categories
- Do NOT make up file names, line numbers, code snippets, or issues.

Tool output contains:
- files_analyzed: List of actual file paths
- findings: List of issues with file_path, line_start, line_end, code_snippet, severity
- file_scores: Per-file metrics
- summary: Count of critical/high/medium/low issues

Treat ALL tool-reported findings as valid inputs.
If uncertainty exists in a finding, clearly state it and recommend verification.

STEP 3: Create the report in Markdown + YAML format

Your response MUST follow this exact structure:

---
agent: engineering_practices_agent
summary: Brief summary of findings
total_issues: X
severity:
  critical: X
  high: X
  medium: X
  low: X
confidence: 0.XX
files_analyzed: [list actual files from tool output]
---

# Engineering Practices Analysis

## Files Analyzed
- List the actual files from tool_output['files_analyzed']

## Findings

For each issue include:
- Title (short and descriptive)
- Severity (critical / high / medium / low)
- Evidence (FROM TOOL OUTPUT ONLY):
  - File path (from tool output)
  - Line number(s) (from tool output)
  - Code snippet (from tool output)
- Explanation:
  - Why this is an engineering practices issue
  - Impact on maintainability/quality
- Recommendation:
  - Concrete improvement or fix guidance

NO-ISSUE CASE:
- If the evaluation reports zero findings, write exactly:

---
agent: engineering_practices_agent
summary: No significant engineering practice issues found
total_issues: 0
severity:
  critical: 0
  high: 0
  medium: 0
  low: 0
confidence: 1.0
files_analyzed: [list actual files from tool output]
---

# Engineering Practices Analysis

## Files Analyzed
- [list files]

No significant engineering practice issues detected in the analyzed files.

CRITICAL RULES
- ALWAYS call evaluate_engineering_practices() first.
- Output your analysis in Markdown+YAML format (ADK will auto-save via output_key).
- NEVER hallucinate evidence (paths, lines, snippets, issues).
- NEVER invent file paths like "authentication.py", "user_manager.py", "payment_processor.py".
- Prefer fewer, higher-confidence findings over speculative ones.
- Your complete Markdown+YAML output will be automatically saved to session state.
    """.strip(),
    tools=[evaluate_engineering_practices],
    output_key="engineering_practices_analysis",  # Auto-write to session state
    
    # Phase 1 Guardrails: Callbacks
    before_model_callback=engineering_agent_before_model,
    after_agent_callback=engineering_agent_after_agent,
)

logger.info("✅ [engineering_practices_agent] Engineering Practices Agent created successfully")
logger.info(f"🔧 [engineering_practices_agent] Tools available: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in [evaluate_engineering_practices]]}")
logger.info("🛡️ [engineering_practices_agent] Phase 1 Guardrails enabled: before_model, after_agent callbacks")