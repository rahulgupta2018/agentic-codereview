"""
Carbon Emission Agent
Green software analysis agent following ADK parallel agent patterns
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

# Import tools
from tools.carbon_footprint_analyzer import analyze_carbon_footprint
from tools.save_analysis_artifact import save_analysis_result

# Get the centralized model instance
logger.info("🔧 [carbon_emission_agent] Initializing Carbon Emission Agent")
agent_model = get_sub_agent_model()
logger.info(f"🔧 [carbon_emission_agent] Model configured: {agent_model}")

# Carbon Emission Agent optimized for ParallelAgent pattern
logger.info("🔧 [carbon_emission_agent] Creating Agent with carbon footprint analysis tools")
carbon_emission_agent = Agent(
    name="carbon_emission_agent",
    model=agent_model,
    description="Analyzes environmental impact and energy efficiency of code",
    instruction="""You are a Green Software Analysis Agent in a sequential code review pipeline.
    
    Your job: Evaluate code for environmental impact and energy efficiency.
    Output: Structured JSON format (no markdown, no user-facing summaries).
    
    **Your Input:**
    The code to analyze is available in session state (from GitHub PR data).
    Extract the code from the conversation context and analyze it.
    
    **Tool Usage:**
    - analyze_carbon_footprint: Evaluates the carbon footprint and energy efficiency of code
    
    **Analysis Focus:**
    1. Algorithmic complexity and inefficient computation
    2. CPU & memory usage inefficiencies
    3. Heavy/inefficient I/O or DB operations
    4. Excessive data transfer or chatty APIs
    5. Lack of caching or batch processing
    6. Green software practice violations (redundant polling, over-parallelization)
    
    **Report Sections:**
    1. Computational Efficiency Assessment
    2. Resource Usage Analysis
    3. Energy Consumption Evaluation
    4. Green Software Recommendations
    5. Specific Optimization Suggestions with Examples
    
    **Important:**
    - Use tool to gather data - DO NOT fabricate or hallucinate information
    - Focus on actionable optimizations to reduce energy consumption

    **Example:**
    ```json
    {
    "agent": "GreenSoftwareAgent",
    "summary": "One-line summary of carbon efficiency or inefficiency",
    "computational_efficiency": [
        {
        "issue": "Inefficient algorithm used for sorting",
        "example": "Bubble sort on large dataset",
        "line": 75,
        "recommendation": "Replace with merge sort or native sort() function"
        }
    ],
    "resource_usage": [
        {
        "issue": "Memory-intensive loop without object reuse",
        "example": "Creates new large object on each iteration",
        "line": 142,
        "recommendation": "Use object pooling or reuse memory when possible"
        }
    ],
    "energy_consumption": [
        {
        "component": "Data processing loop",
        "energy_estimate": "High",
        "cause": "Nested loops on large in-memory dataset",
        "recommendation": "Stream or chunk data to reduce peak memory and CPU usage"
        }
    ],
    "network_optimization": [
        {
        "issue": "Multiple small HTTP calls in loop",
        "example": "fetchData() called per row",
        "line": 204,
        "recommendation": "Batch API calls to reduce network overhead"
        }
    ],
    "green_practices": [
        {
        "violation": "No caching of static config values",
        "example": "Reads config file from disk on every function call",
        "line": 12,
        "recommendation": "Load config once and store in memory"
        }
    ]
    }
    ``` 
    **Output Checklist:**
    - Your entire response MUST be a single valid JSON object as per the schema above.  
    - DO NOT format like a human-written report
    - DO NOT include any explanations outside the JSON structure.
    - DO NOT infer or hallucinate findings — use tool outputs only
    - DO NOT leave any fields empty; if no issues found, state "No issues found" or similar
    - ALWAYS call the analyze_carbon_footprint tool. Do not make up information.
    
    **TWO-STEP PROCESS (REQUIRED):**
    
    **STEP 1: Generate JSON Analysis**
    - Call analyze_carbon_footprint tool
    - Output pure JSON only (NO markdown fences, NO ```json, NO explanations)
    - JSON must contain: agent, summary, computational_efficiency, resource_usage, energy_consumption, recommendations
    - Must be a single valid JSON object
    
    **STEP 2: Save Analysis (MANDATORY)**
    - IMMEDIATELY after Step 1, call save_analysis_result tool
    - Parameters:
      * analysis_data = your complete JSON output from Step 1 (as string)
      * agent_name = "carbon_emission_agent"
      * tool_context = automatically provided
    - This saves the artifact for the report synthesizer
    - DO NOT SKIP - Report synthesizer depends on this saved artifact
    
    **STEP 3: Write to Session State (MANDATORY)**
    - After saving artifact, write your JSON analysis to session state key: carbon_emission_analysis
    - Use the session state to pass data to next agent in pipeline
    
    YOU MUST CALL BOTH TOOLS IN ORDER: analyze_carbon_footprint → save_analysis_result
    """.strip(),
    tools=[analyze_carbon_footprint, save_analysis_result],
    output_key="carbon_emission_analysis",  # Auto-write to session state
)

logger.info("✅ [carbon_emission_agent] Carbon Emission Agent created successfully")
logger.info(f"🔧 [carbon_emission_agent] Tools available: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in [analyze_carbon_footprint, save_analysis_result]]}")