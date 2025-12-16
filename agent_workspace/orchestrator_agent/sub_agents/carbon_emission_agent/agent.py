"""
Carbon Emission Agent
Green software analysis agent following ADK parallel agent patterns
"""

import sys
import logging
import json
import re
from pathlib import Path
from google.adk.agents import Agent
from google.genai import types

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

# Import callback utilities
from util.callbacks import (
    filter_bias,
    execute_callback_safe
)
from util.metrics import CallbackTimer, get_metrics_collector

# Get the centralized model instance
logger.info("🔧 [carbon_emission_agent] Initializing Carbon Emission Agent")
agent_model = get_sub_agent_model()
logger.info(f"🔧 [carbon_emission_agent] Model configured: {agent_model}")

# ============================================================================
# PHASE 1 CALLBACKS
# ============================================================================

def carbon_agent_before_model(callback_context, llm_request):
    """Inject greenwashing prevention and evidence requirements."""
    with CallbackTimer("carbon_emission_agent", "before_model") as timer:
        carbon_guidance = """
CARBON EMISSION ANALYSIS REQUIREMENTS:
1. Require measurable, evidence-based estimates (kWh, CPU cycles, memory usage)
2. Avoid greenwashing language - be realistic about environmental impact
3. Do NOT use exaggerated terms: "dramatically reduce", "eliminate carbon", "zero impact", "perfectly green"
4. Require cost-benefit analysis for optimization recommendations
5. Acknowledge when optimizations have marginal benefit
6. Energy estimates must include units (kWh, Wh, J, CPU seconds)
7. Compare against baseline or alternative approaches when possible

PROHIBITED LANGUAGE:
- "Dramatically reduce carbon emissions" → "Reduce carbon emissions by approximately X%"
- "Eliminate environmental impact" → "Reduce environmental impact"
- "Zero-carbon solution" → "Lower-carbon solution"
- "Perfectly efficient" → "More efficient"
- "Massive energy savings" → "Energy savings estimated at X kWh"
"""
        # Inject guidance into system instructions
        llm_request.config.system_instruction += carbon_guidance
        logger.debug("✅ [carbon_emission_agent] before_model: Injected greenwashing prevention guidance")
        
        timer.record_filtered('guidance_injected', 1)
        return None  # Allow with modifications


def carbon_agent_after_agent(callback_context):
    """Validate energy estimates, log greenwashing detection (validation only)."""
    with CallbackTimer("carbon_emission_agent", "after_agent") as timer:
        try:
            # Access carbon emission analysis from session state
            text = callback_context.state.get('carbon_emission_analysis', '')
            if not text:
                logger.warning("⚠️ [carbon_emission_agent] No analysis in state")
                return None
            
            # Parse Markdown+YAML format (no JSON parsing needed)
            from util.markdown_yaml_parser import parse_analysis, validate_analysis, filter_content
            
            metadata, markdown_body = parse_analysis(text)
            if not metadata:
                logger.warning("⚠️ [carbon_emission_agent] after_agent: Could not parse Markdown+YAML")
                return None
            
            # Validate required fields
            errors = validate_analysis(metadata, markdown_body, 'carbon_emission_agent')
            if errors:
                logger.warning(f"⚠️ [carbon_emission_agent] Validation errors: {errors}")
            
            # Filter greenwashing terms from markdown body
            greenwashing_patterns = [
                (r'\bdramatically reduce\b', 'reduce'),
                (r'\beliminate\s+(?:carbon|emissions|environmental impact)\b', 'reduce'),
                (r'\bzero[- ](?:carbon|impact|emissions)\b', 'lower-carbon'),
                (r'\bperfectly\s+(?:green|efficient|clean)\b', 'more efficient'),
                (r'\bmassive\s+(?:energy savings|carbon reduction)\b', 'energy savings'),
                (r'\bcompletely\s+(?:eliminate|remove)\b', 'reduce'),
            ]
            
            filtered_body, greenwashing_filtered = filter_content(markdown_body, greenwashing_patterns)
            
            if greenwashing_filtered > 0:
                logger.warning(f"🚫 [carbon_emission_agent] Detected {greenwashing_filtered} greenwashing terms")
            
            timer.record_filtered('greenwashing', greenwashing_filtered)
            
            # Filter bias/profanity
            bias_patterns = [
                (r'\b(stupid|dumb|idiot|lazy|incompetent)\b', '[filtered]'),
                (r'\b(crap|shit|sucks)\b', '[filtered]'),
            ]
            
            filtered_body, bias_filtered = filter_content(filtered_body, bias_patterns)
            
            if bias_filtered > 0:
                logger.warning(f"🚫 [carbon_emission_agent] Filtered {bias_filtered} biased terms")
        
            timer.record_filtered('bias', bias_filtered)
            
            logger.info(f"🛡️ [carbon_emission_agent] Detected: greenwashing={greenwashing_filtered}, bias={bias_filtered}")
            
            return None  # Validation only, no content modification
            
        except Exception as e:
            logger.error(f"❌ [carbon_emission_agent] after_agent error: {e}")
            return None

# ============================================================================
# AGENT DEFINITION
# ============================================================================

logger.info("🔧 [carbon_emission_agent] Creating Agent with carbon footprint analysis tools")
carbon_emission_agent = Agent(
    name="carbon_emission_agent",
    model=agent_model,
    description="Analyzes environmental impact and energy efficiency of code",
    instruction="""You are a Green Software Analysis Agent in a sequential code review pipeline.
    
    Your job: Evaluate code for environmental impact and energy efficiency.
    Output: **Markdown with YAML frontmatter** (human-readable, structured metadata).
    
    **Your Input:**
    The code files to analyze are in session state under the key 'code'.
    The session state also contains:
    - 'files': List of file metadata (file_path, language, lines, etc.)
    - 'language': Primary language (or "multi" for multi-language PRs)
    - 'file_count': Number of files in the PR
    
    **CRITICAL:** You MUST pass the 'code' from session state to the analyze_carbon_footprint tool.
    The code contains all PR files with headers like "File: path/to/file.py".
    DO NOT make up file names or code - use only what's in the 'code' variable.
    
    **Tool Usage:**
    - analyze_carbon_footprint(code=<code from session state>): Evaluates the carbon footprint and energy efficiency of code
    
    **Analysis Focus:**
    1. Algorithmic complexity and inefficient computation
    2. CPU & memory usage inefficiencies
    3. Heavy/inefficient I/O or DB operations
    4. Excessive data transfer or chatty APIs
    5. Lack of caching or batch processing
    6. Green software practice violations (redundant polling, over-parallelization)
    
    **Important Guidelines:**
    - Your entire response MUST be in Markdown + YAML frontmatter format
    - START with YAML frontmatter (metadata between --- delimiters)
    - FOLLOW with Markdown body (formatted analysis with headings, code blocks)
    - DO NOT infer or hallucinate findings — use tool outputs only
    - ALWAYS call analyze_carbon_footprint with code from session state
    - DO NOT make up file names (auth/authentication.py, services/user_manager.py, etc.)
    - ONLY reference files that appear in the 'code' variable you pass to the tool
    - If you don't find real issues, report "No significant energy efficiency issues found"
    - DO NOT analyze metadata, reports, or artifacts - analyze SOURCE CODE only
    - Include actual file names, line numbers, and code snippets from the PROVIDED code
    - Every finding MUST have a confidence score (0.0-1.0)
    - Use quantitative estimates where possible (percentage reductions, energy savings)
    
    **Output Format Example:**
    ```
    ---
    agent: carbon_emission_agent
    summary: Found 5 energy efficiency issues with potential 20%" reduction in computational costs
    total_issues: 5
    severity:
      critical: 1
      high: 2
      medium: 2
      low: 0
    confidence: 0.85
    estimated_improvements:
      cpu_reduction: "15%"
      memory_reduction: "25%"
      io_reduction: "30%"
    categories:
      algorithmic: 1
      resource_usage: 2
      network: 1
      caching: 1
    file_count: 3
    ---

    # Carbon Footprint & Energy Efficiency Analysis

    ## Critical Energy Inefficiencies

    ### 1. Nested Loop with O(n³) Complexity (Confidence: 0.95)
    **Severity:** Critical  
    **Location:** `matchRecords` function, lines 67-89  
    **File:** `data/matcher.py`  
    **Energy Impact:** High (excessive CPU cycles)

    **Issue Description:**
    Triple-nested loop creates cubic time complexity, consuming unnecessary CPU resources and energy.

    **Evidence:**
    ```python
    def matchRecords(users, orders, products):
        matches = []
        for user in users:              # O(n)
            for order in orders:        # O(m)
                for product in products: # O(p)
                    if order.user_id == user.id and order.product_id == product.id:
                        matches.append((user, order, product))
    ```

    **Energy Estimate:** For 1000 users, 5000 orders, 500 products = 2.5 billion iterations

    **Recommendation:**
    Use hash maps to reduce to O(n+m+p) by creating lookup dictionaries for users and products,
    then iterating only through orders to find matches. This eliminates nested loops.

    **Expected Improvement:** ~99.9%" reduction in iterations, estimated 15%" CPU energy savings

    ---

    ## High Priority Optimizations

    ### 2. Memory Allocation in Tight Loop (Confidence: 0.90)
    **Severity:** High  
    **Location:** `processDataBatch`, lines 142-156  
    **File:** `processing/batch_processor.py`  
    **Energy Impact:** Medium-High (memory churn, GC pressure)

    **Issue Description:**
    Creates new large objects on each iteration without reuse, causing memory pressure and frequent garbage collection.

    **Evidence:**
    ```python
    def processDataBatch(records):
        results = []
        for record in records:
            processor = DataProcessor()  # New object per iteration
            buffer = ByteArray(1024)     # New 1KB allocation
            result = processor.process(record, buffer)
            results.append(result)
    ```

    **Recommendation:**
    Use object pooling and buffer reuse:
    ```python
    def processDataBatch(records):
        processor = DataProcessor()      # Reuse
        buffer = ByteArray(1024)         # Reuse
        results = []
        for record in records:
            result = processor.process(record, buffer)
            results.append(result)
            buffer.clear()  # Reset for reuse
    ```

    **Expected Improvement:** 25% memory reduction, fewer GC cycles

    ---

    ### 3. Chatty API Calls in Loop (Confidence: 0.88)
    **Severity:** High  
    **Location:** `fetchUserData`, lines 204-218  
    **File:** `api/user_service.py`  
    **Energy Impact:** High (network overhead, server load)

    **Issue Description:**
    Makes individual HTTP request for each user instead of batching, increasing network energy consumption.

    **Evidence:**
    Individual API calls in a loop create unnecessary network overhead.

    **Recommendation:**
    Batch API calls to reduce network traffic and improve performance.

    **Expected Improvement:** 30%" reduction in network traffic, 50%" faster execution

    ## Green Software Practice Violations

    ### 4. No Caching of Static Configuration (Confidence: 0.92)
    **Severity:** Medium  
    **Location:** Throughout `config/` module  
    **Energy Impact:** Low-Medium (repeated I/O)

    **Issue:** Configuration file read from disk on every function call.

    **Recommendation:**
    Load config once at startup:
    ```python
    # Global singleton
    _CONFIG_CACHE = None

    def get_config():
        global _CONFIG_CACHE
        if _CONFIG_CACHE is None:
            _CONFIG_CACHE = load_config_from_disk()
        return _CONFIG_CACHE
    ```

    ## Energy Efficiency Summary

    | Category | Count | Est. Energy Savings |
    |----------|-------|---------------------|
    | Algorithmic | 1 | 15% CPU reduction |
    | Memory | 2 | 25% memory reduction |
    | Network | 1 | 30% I/O reduction |
    | Caching | 1 | 10%" disk I/O reduction |

    **Total Estimated Improvement:** 20%" reduction in computational energy consumption

    ## Priority Actions

    1. **Immediate:** Refactor triple-nested loop (15% CPU savings)
    2. **High:** Implement object pooling in batch processor (25% memory savings)
    3. **Medium:** Batch API calls (30% network savings)
    ```
                
    **TWO-STEP PROCESS (REQUIRED):**
    
    **STEP 1: Generate Markdown+YAML Analysis**
    - Call analyze_carbon_footprint tool
    - Output Markdown with YAML frontmatter (see format above)
    - Start with --- YAML metadata ---
    - Follow with # Markdown sections
    - Include confidence scores for each finding
    - Reference actual files and line numbers
    - Provide energy estimates and percentage improvements
    
    **STEP 2: Save Analysis (MANDATORY)**
    - IMMEDIATELY after Step 1, call save_analysis_result tool
    - Parameters:
      * analysis_data = your complete Markdown+YAML output from Step 1 (as string)
      * agent_name = "carbon_emission_agent"
      * tool_context = automatically provided
    - This saves the artifact for the report synthesizer
    - DO NOT SKIP - Report synthesizer depends on this saved artifact
    
    **STEP 3: Write to Session State (MANDATORY)**
    - After saving artifact, write your Markdown+YAML analysis to session state key: carbon_emission_analysis
    - Use the session state to pass data to next agent in pipeline
    
    YOU MUST CALL BOTH TOOLS IN ORDER: analyze_carbon_footprint → save_analysis_result
    """.strip(),
    tools=[analyze_carbon_footprint, save_analysis_result],
    output_key="carbon_emission_analysis",  # Auto-write to session state
    
    # Phase 1 Guardrails: Callbacks
    before_model_callback=carbon_agent_before_model,
    after_agent_callback=carbon_agent_after_agent,
)

logger.info("✅ [carbon_emission_agent] Carbon Emission Agent created successfully")
logger.info(f"🔧 [carbon_emission_agent] Tools available: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in [analyze_carbon_footprint, save_analysis_result]]}")
logger.info("🛡️ [carbon_emission_agent] Phase 1 Guardrails enabled: before_model, after_agent callbacks")