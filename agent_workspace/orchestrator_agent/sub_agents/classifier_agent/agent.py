"""
Intelligent input classifier agent that selects appropriate analysis sub-agents
based on the characteristics of the submitted code.

"""

import sys
import logging
from pathlib import Path
from google.adk.agents import Agent

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add project root to Python path for absolute imports
# __file__ is in agent_workspace/orchestrator_agent/sub_agents/carbon_emission_agent/
# We need to go up 5 levels to reach the project root (agentic-codereview/)
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import centralized model configuration
from util.llm_model import get_sub_agent_model
from util.llm_model import get_agent_model

# Initialize services at module level so they're available for adk web/api commands


# Get the centralized model instance
logger.info("🔧 [classifier_agent] Initializing Classifier Agent")
agent_model = get_agent_model()
logger.info(f"🔧 [classifier_agent] Model configured: {agent_model}")

logger.info("🔧 [classifier_agent] Creating Agent for request classification")
classifier_agent = Agent(
    name="classifier_agent",
    model=agent_model,
    description="Classifies user requests to determine appropriate code analysis sub-agents",
    instruction="""You are an intelligent request classifier and responder for a code review system.

    **STEP 1: Analyze the user's input**
    
    Classify into one of these categories:
    1. **general_query**: Questions about system capabilities (no code present)
    2. **code_review_full**: Comprehensive code analysis request
    3. **code_review_security**: Security-focused analysis
    4. **code_review_quality**: Code quality analysis
    5. **code_review_engineering**: Engineering practices review
    6. **code_review_carbon**: Environmental impact analysis
    7. **code_review_custom**: Multiple specific areas

    **STEP 2: For general queries (no code), provide direct response**
    
    If type is "general_query", include a helpful "response" field:
    
    {
        "type": "general_query",
        "has_code": false,
        "focus_areas": [],
        "confidence": "high",
        "reasoning": "User asking about capabilities",
        "response": "I'm an AI-powered code review system that can analyze your code for:
        
        🔒 **Security**: Vulnerabilities, authentication issues, input validation
        📊 **Code Quality**: Complexity, maintainability, code smells
        ⚙️ **Engineering Practices**: SOLID principles, design patterns, best practices
        🌱 **Environmental Impact**: Performance optimization, resource efficiency
        
        To get started, simply paste your code and I'll provide a comprehensive analysis!
        You can also request specific analyses like 'Check security' or 'Analyze code quality'."
    }
    
    **STEP 3: For code review requests, provide classification only**
    
    {
        "type": "code_review_full",
        "has_code": true,
        "focus_areas": ["all"],
        "confidence": "high",
        "reasoning": "User provided code for comprehensive review"
    }

    **Important**: 
    - Always check if code is present
    - If no code and user asks general questions, set type="general_query" and include a "response" field
    - Output ONLY the JSON classification (no additional text)
    - The JSON will be automatically available to the next agent via output_key="request_classification"
    """.strip(),
    input_schema=None,
    output_key="request_classification",
)

logger.info("✅ [classifier_agent] Classifier Agent created successfully")
logger.info("🔧 [classifier_agent] No tools - outputs classification JSON directly via output_key")