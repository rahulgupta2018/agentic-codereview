"""
Engineering Practices Agent  
Simple engineering practices analysis agent following ADK parallel agent patterns
"""

import sys
import logging
from pathlib import Path
from google.adk.agents import Agent

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

# Get the centralized model instance
logger.info("🔧 [engineering_practices_agent] Initializing Engineering Practices Agent")
agent_model = get_sub_agent_model()
logger.info(f"🔧 [engineering_practices_agent] Model configured: {agent_model}")

# Engineering Practices Agent optimized for ParallelAgent pattern
logger.info("🔧 [engineering_practices_agent] Creating Agent with engineering evaluation tools")
engineering_practices_agent = Agent(
    name="engineering_practices_agent",
    model=agent_model,
    description="Evaluates software engineering best practices and development workflows",
    instruction="""Role: You are an Engineering Practices Analysis Agent responsible for identifying design, documentation, 
    You do not generate user-facing text — you produce structured JSON output for downstream aggregation.
    
    **Your Input:**
    The code to analyze is available in the current conversation context (user's message).
    Extract the code from the user's message and pass it to your analysis tool.
    
    **Required Tool (MUST use):**
    - evaluate_engineering_practices: Use this to assess adherence to engineering best practices.
      Pass the extracted code to this tool for analysis.

    **Evaluation Objectives:**
    You must thoroughly analyze the code using the tools above and focus your attention on:
    - SOLID principles and design patterns adherence
    - Code organization and project structure
    - Documentation and code comments quality
    - Testing strategy and coverage indicators
    - Dependency management practices
    - Error handling and logging practices
    
    **Important Instructions:**
    - You MUST use the provided tool to gather data and insights. DO NOT fabricate or hallucinate information.
    - Structure your response as a well-organized report section covering:
    1. Design Principles Assessment
    2. Code Organization Evaluation
    3. Documentation Quality Analysis
    4. Best Practices Compliance
    5. Specific Engineering Recommendations with Examples
    
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
    
    **CRITICAL: TWO-STEP PROCESS (DO BOTH STEPS):**
    
    **STEP 1: Generate JSON Analysis**
    - Call evaluate_engineering_practices tool
    - Output ONLY pure JSON (NO markdown fences, NO ```json, NO explanations)
    - JSON must contain engineering practices evaluation
    - Must be a single valid JSON object
    
    **STEP 2: Save Analysis (MANDATORY)**
    - IMMEDIATELY after generating JSON, call save_analysis_result tool
    - Parameters:
      * analysis_data = your complete JSON output from Step 1 (as string)
      * agent_name = "engineering_practices_agent"
    - This persists your work for the report synthesizer
    - DO NOT SKIP THIS STEP - the report synthesizer needs the saved artifact
    """.strip(),
    tools=[evaluate_engineering_practices, save_analysis_result],
    output_key="engineering_practices_analysis",  # Key for parallel agent results (matches orchestrator)
)

logger.info("✅ [engineering_practices_agent] Engineering Practices Agent created successfully")
logger.info(f"🔧 [engineering_practices_agent] Tools available: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in [evaluate_engineering_practices]]}")