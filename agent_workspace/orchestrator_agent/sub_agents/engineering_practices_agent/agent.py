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
from tools.save_analysis_artifact import save_analysis_result

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
    After Agent Callback - Log dogmatic language detection (validation only).
    
    Note: ADK only passes callback_context (no content parameter).
    Accesses agent output via session state for validation.
    
    Quality Gates:
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
            
            # Parse Markdown+YAML format
            from util.markdown_yaml_parser import parse_analysis, validate_analysis, filter_content
            
            metadata, markdown_body = parse_analysis(text)
            if not metadata:
                logger.warning("⚠️ [engineering_practices_agent] after_agent: Could not parse Markdown+YAML")
                return None
            
            # Validate required fields
            errors = validate_analysis(metadata, markdown_body, 'engineering_practices_agent')
            if errors:
                logger.warning(f"⚠️ [engineering_practices_agent] Validation errors: {errors}")
            
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
            
            logger.info(f"✅ [engineering_practices_agent] after_agent: Detected {dogma_filtered} dogmatic + {bias_filtered} biased terms")
            
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
    You are the Engineering Practices Analysis Agent in a sequential code review pipeline.

Your job:
- Evaluate engineering best practices, design principles, maintainability, developer workflows.
- Focus on practical, context-aware recommendations (avoid dogma).

IMPORTANT REALITY CHECK:
- The PR code is stored in shared session state under the key "code".
- You (the LLM) do NOT read session state directly.
- The tool evaluate_engineering_practices reads the PR code from session state internally.

STEP 1: Run evaluation (mandatory)
- ALWAYS call evaluate_engineering_practices() exactly once at the start.
- Do not invent issues before tool results exist.

STEP 2: Use tool output as source of truth
- Use only the tool output and code evidence it provides.
- Do NOT invent file paths, line numbers, or snippets.
- If the tool output is uncertain or missing evidence, say so and recommend verification.

STEP 3: Output format (required)
Output Markdown with YAML frontmatter exactly:

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
---

# Engineering Practices Analysis

For each issue include:
- Title + confidence (0.0–1.0)
- Severity (critical/high/medium/low)
- Evidence:
  - File path
  - Line number(s) if available
  - Code snippet (only if provided)
- Why it matters (maintainability/reliability/team velocity)
- Practical recommendation and trade-offs (avoid absolutist language)

NO-ISSUE CASE:
- If no issues found, say exactly: "No significant issues found."
    """.strip(),
    tools=[evaluate_engineering_practices, save_analysis_result],
    output_key="engineering_practices_analysis",  # Auto-write to session state
    
    # Phase 1 Guardrails: Callbacks
    before_model_callback=engineering_agent_before_model,
    after_agent_callback=engineering_agent_after_agent,
)

logger.info("✅ [engineering_practices_agent] Engineering Practices Agent created successfully")
logger.info(f"🔧 [engineering_practices_agent] Tools available: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in [evaluate_engineering_practices, save_analysis_result]]}")
logger.info("🛡️ [engineering_practices_agent] Phase 1 Guardrails enabled: before_model, after_agent callbacks")