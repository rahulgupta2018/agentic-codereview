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
    execute_callback_safe,
    parse_json_safe,
    format_json_safe
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
            
            # Parse JSON
            analysis = parse_json_safe(text)
            if not analysis:
                logger.warning("⚠️ [engineering_practices_agent] after_agent: Could not parse JSON")
                return None
            
            # Check for dogmatic recommendations
            dogma_patterns = [
                (r'\bmust use microservices\b', 'consider using microservices'),
                (r'\balways use\b', 'typically use'),
                (r'\bnever use\b', 'avoid using'),
                (r'\bonly.*is acceptable\b', 'is recommended'),
                (r'\bshould always\b', 'should typically'),
                (r'\bmust follow\b', 'should follow'),
            ]
            
            dogma_filtered = 0
            
            # Filter recommendations
            for recommendation in analysis.get('recommendations', []):
                if 'description' in recommendation:
                    desc = recommendation['description']
                    original_desc = desc
                    
                    for pattern, replacement in dogma_patterns:
                        desc = re.sub(pattern, replacement, desc, flags=re.IGNORECASE)
                    
                    if desc != original_desc:
                        recommendation['description'] = desc
                        dogma_filtered += 1
                        logger.debug(f"🔄 Softened dogmatic recommendation")
            
            # Filter in design_principles_assessment
            if 'design_principles_assessment' in analysis:
                for item in analysis['design_principles_assessment']:
                    if isinstance(item, dict) and 'recommendation' in item:
                        rec = item['recommendation']
                        original = rec
                        
                        for pattern, replacement in dogma_patterns:
                            rec = re.sub(pattern, replacement, rec, flags=re.IGNORECASE)
                        
                        if rec != original:
                            item['recommendation'] = rec
                            dogma_filtered += 1
            
            timer.record_filtered('dogma', dogma_filtered)
            
            # Filter bias/profanity
            bias_filtered = 0
            for rec in analysis.get('recommendations', []):
                if 'description' in rec:
                    original = rec['description']
                    filtered, count = filter_bias(original)
                    if count > 0:
                        rec['description'] = filtered
                        bias_filtered += count
            
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
    instruction="""You are an Engineering Practices Analysis Agent in a sequential code review pipeline.
    
    Your job: Evaluate engineering best practices, design principles, and development workflows.
    Output: Structured JSON format (no markdown, no user-facing summaries).
    
    **Your Input:**
    The code to analyze is available in session state (from GitHub PR data).
    Extract the code from the conversation context and analyze it.
    
    **Tool Usage:**
    - evaluate_engineering_practices: Assesses adherence to engineering best practices

    **Analysis Focus:**
    - SOLID principles and design patterns adherence
    - Code organization and project structure
    - Documentation and code comments quality
    - Testing strategy and coverage indicators
    - Dependency management practices
    - Error handling and logging practices
    
    **Report Sections:**
    1. Design Principles Assessment
    2. Code Organization Evaluation
    3. Documentation Quality Analysis
    4. Best Practices Compliance
    5. Specific Engineering Recommendations with Examples
    
    **Important:**
    - Use tool to gather data - DO NOT fabricate or hallucinate information
    - Provide actionable recommendations based on established engineering standards
    
    **Important Guidelines:**
    - Ensure your analysis is objective and based on established engineering standards.
    - Provide actionable recommendations that can be realistically implemented by the development team.
    - Use examples from the codebase to illustrate points where applicable.
    - Return only structured JSON as defined below — no freeform text, no markdown.
    - Your output JSON must include the following keys:
        - design_principles_assessment
        - code_organization_evaluation
        - documentation_quality_analysis
        - best_practices_compliance
        - specific_engineering_recommendations
    
    **Output JSON Structure Example:**
    {
        "agent": "EngineeringPracticesAgent",
        "summary": "One-line summary of findings",
        "design_principles": [
            {
            "principle": "Single Responsibility Principle",
            "status": "violated",
            "example": "Class `OrderProcessor` handles both validation and persistence",
            "line": 12,
            "recommendation": "Separate validation into a dedicated class"
            }
        ],
        "code_organization": [
            {
            "issue": "Mixed UI and business logic in same module",
            "example": "Component `CheckoutView` includes price calculation logic",
            "line": 89,
            "recommendation": "Extract logic into service layer"
            }
        ],
        "documentation": [
            {
            "element": "function",
            "issue": "Missing docstring",
            "location": "calculatePremium",
            "line": 24,
            "recommendation": "Add a descriptive docstring with input/output explanation"
            }
        ],
        "testing": [
            {
            "observation": "No unit tests found for core modules",
            "impact": "Low confidence in change safety",
            "recommendation": "Add tests for `PricingService`, `ValidationUtils`"
            }
        ],
        "dependencies": [
            {
            "issue": "Tightly coupled to 3rd-party logging lib",
            "example": "Direct calls to `LoggerLib.log()` throughout",
            "recommendation": "Abstract via interface for easier swapping/mocking"
            }
        ],
        "error_handling": [
            {
            "pattern": "Broad exception catch",
            "example": "catch(Exception e)",
            "line": 152,
            "recommendation": "Catch specific exceptions and log detailed context"
            }
        ]
    }                   
    
    **TWO-STEP PROCESS (REQUIRED):**
    
    **STEP 1: Generate JSON Analysis**
    - Call evaluate_engineering_practices tool
    - Output pure JSON only (NO markdown fences, NO ```json, NO explanations)
    - JSON must contain: agent, summary, design_principles, code_organization, documentation_quality, recommendations
    - Must be a single valid JSON object
    
    **STEP 2: Save Analysis (MANDATORY)**
    - IMMEDIATELY after Step 1, call save_analysis_result tool
    - Parameters:
      * analysis_data = your complete JSON output from Step 1 (as string)
      * agent_name = "engineering_practices_agent"
      * tool_context = automatically provided
    - This saves the artifact for the report synthesizer
    - DO NOT SKIP - Report synthesizer depends on this saved artifact
    
    **STEP 3: Write to Session State (MANDATORY)**
    - After saving artifact, write your JSON analysis to session state key: engineering_practices_analysis
    - Use the session state to pass data to next agent in pipeline
    
    YOU MUST CALL BOTH TOOLS IN ORDER: evaluate_engineering_practices → save_analysis_result
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