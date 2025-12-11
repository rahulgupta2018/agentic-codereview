"""
Security Agent
Simple security analysis agent following ADK parallel agent patterns

With Phase 1 Guardrails:
- before_model_callback: Inject security analysis constraints
- after_tool_callback: Validate vulnerability findings and filter false positives
- after_agent_callback: Remove hallucinated CVEs, filter bias/profanity
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
# __file__ is in agent_workspace/orchestrator_agent/sub_agents/security_agent/
# We need to go up 5 levels to reach the project root (agentic-codereview/)
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import centralized model configuration
from util.llm_model import get_sub_agent_model

# Import tools
from tools.security_vulnerability_scanner import scan_security_vulnerabilities
from tools.save_analysis_artifact import save_analysis_result

# Import callback utilities
from util.callbacks import (
    validate_cve_exists,
    filter_bias,
    filter_false_positives,
    execute_callback_safe,
    parse_json_safe,
    format_json_safe
)
from util.metrics import CallbackTimer, get_metrics_collector

# Get the centralized model instance
logger.info("🔧 [security_agent] Initializing Security Analysis Agent")
agent_model = get_sub_agent_model()
logger.info(f"🔧 [security_agent] Model configured: {agent_model}")


# ============================================================================
# CALLBACK FUNCTIONS (Phase 1 Guardrails)
# ============================================================================

def security_agent_before_model(callback_context, llm_request):
    """
    Before Model Callback - Inject security analysis constraints.
    
    Guardrails:
    - Add security analysis constraints to system instruction
    - Inject OWASP/CWE reference guidance
    - Require evidence-based findings only
    """
    with CallbackTimer("security_agent", "before_model") as timer:
        try:
            safety_guidance = """

---
CRITICAL SECURITY ANALYSIS RULES:
1. Only report vulnerabilities with concrete evidence (line numbers, patterns)
2. Reference CWE/OWASP standards for each finding
3. Consider context - not all dynamic queries are SQL injection
4. Distinguish between actual vulnerabilities and potential risks
5. Provide mitigation steps, not just criticism
6. Check for common false positives:
   - Parameterized queries (NOT SQL injection)
   - subprocess with shell=False (NOT command injection)
   - DOMPurify sanitization (NOT XSS)
   - Environment variables (NOT hardcoded secrets)
---
"""
            llm_request.config.system_instruction += safety_guidance
            logger.debug("✅ [security_agent] before_model: Injected safety guidance")
            return None  # Allow with modifications
        
        except Exception as e:
            logger.error(f"❌ [security_agent] before_model error: {e}")
            return None  # Fail open


def security_agent_after_tool(tool, args, tool_context, tool_response):
    """
    After Tool Callback - Validate vulnerability findings and filter false positives.
    
    Args:
        tool: Tool object or name
        args: Tool arguments (dict)
        tool_context: Tool execution context
        tool_response: Tool response (dict)
    
    Returns:
        Modified tool_response or None
    """
    with CallbackTimer("security_agent", "after_tool") as timer:
        try:
            tool_name = tool if isinstance(tool, str) else getattr(tool, 'name', str(tool))
            if tool_name != 'scan_security_vulnerabilities':
                return None
            
            if not isinstance(tool_response, dict):
                logger.warning("⚠️ [security_agent] after_tool: tool_response not a dict")
                return None
            
            vulnerabilities = tool_response.get('vulnerabilities', [])
            if not vulnerabilities:
                return None
            
            # Filter false positives
            filtered_vulns, removed_count = filter_false_positives(vulnerabilities, 'security_agent')
            timer.record_filtered('false_positives', removed_count)
            
            # Validate evidence fields
            validated_vulns = []
            for vuln in filtered_vulns:
                # Check required evidence fields
                has_location = vuln.get('location') or vuln.get('file_path')
                has_description = vuln.get('description')
                has_evidence = vuln.get('line') or vuln.get('code_snippet') or vuln.get('cve')
                
                if has_location and has_description and has_evidence:
                    validated_vulns.append(vuln)
                else:
                    logger.debug(f"🚫 [security_agent] Filtered vuln without evidence: {vuln.get('type', 'unknown')}")
                    timer.record_filtered('missing_evidence', 1)
            
            tool_response['vulnerabilities'] = validated_vulns
            
            logger.info(f"✅ [security_agent] after_tool: Validated {len(validated_vulns)}/{len(vulnerabilities)} vulnerabilities")
            
            return tool_response
        
        except Exception as e:
            logger.error(f"❌ [security_agent] after_tool error: {e}")
            return None  # Fail open


def security_agent_after_agent(callback_context):
    """
    After Agent Callback - Validate CVEs, log bias detection (validation only).
    
    Note: ADK only passes callback_context (no content parameter).
    Accesses agent output via session state for validation.
    
    Quality Gates:
    - Validate CVE IDs against NVD database
    - Check for bias/profanity in descriptions
    - Record metrics (validation only, no content modification)
    """
    with CallbackTimer("security_agent", "after_agent") as timer:
        try:
            # Access security analysis from session state
            text = callback_context.state.get('security_analysis', '')
            if not text:
                logger.warning("⚠️ [security_agent] No security_analysis in state")
                return None
            
            # Parse JSON
            analysis = parse_json_safe(text)
            if not analysis:
                logger.warning("⚠️ [security_agent] after_agent: Could not parse JSON")
                return None
            
            # Validate and filter CVEs
            cve_filtered = 0
            for vuln in analysis.get('vulnerabilities', []):
                if 'cve' in vuln or 'cve_id' in vuln:
                    cve_field = 'cve' if 'cve' in vuln else 'cve_id'
                    cve_id = vuln[cve_field]
                    
                    if not validate_cve_exists(cve_id):
                        logger.warning(f"🚫 [security_agent] Removed hallucinated CVE: {cve_id}")
                        del vuln[cve_field]
                        cve_filtered += 1
            
            timer.record_filtered('invalid_cves', cve_filtered)
            
            # Filter bias/profanity from descriptions
            bias_filtered = 0
            for vuln in analysis.get('vulnerabilities', []):
                if 'description' in vuln:
                    original = vuln['description']
                    filtered, count = filter_bias(original)
                    if count > 0:
                        vuln['description'] = filtered
                        bias_filtered += count
            
            timer.record_filtered('bias', bias_filtered)
            
            logger.info(f"✅ [security_agent] after_agent: Detected {cve_filtered} invalid CVEs, {bias_filtered} biased terms")
            
            return None  # Validation only, no content modification
        
        except Exception as e:
            logger.error(f"❌ [security_agent] after_agent error: {e}")
            return None  # Fail open


# ============================================================================
# AGENT DEFINITION
# ============================================================================

# Security Agent optimized for ParallelAgent pattern
logger.info("🔧 [security_agent] Creating Agent with security scanning tools")
security_agent = Agent(
    name="security_agent",
    model=agent_model,
    description="Analyzes security vulnerabilities and compliance issues",
    instruction="""You are a Security Analysis Agent in a sequential code review pipeline.
    
    Your job: Scan code for security vulnerabilities using OWASP Top 10 as guidance.
    Output: Structured JSON format (no markdown, no user-facing summaries).
    
    **Your Input:**
    The code to analyze is available in session state (from GitHub PR data).
    Extract the code from the conversation context and analyze it.

    **Tool Usage:** 
    - scan_security_vulnerabilities: Detects security flaws, misconfigurations, and unsafe practices.
    
    **Analysis Categories:**
    1. Vulnerability Assessment Results
    2. OWASP Top 10 Risk Analysis
    3. Security Best Practices Evaluation
    4. Specific Security Recommendations with Examples
    5. Security Misconfiguration Issues
    6. Input Validation Problems
    7. Cryptographic Weaknesses
    8. Authentication/Authorization Issues
    9. Sensitive Data Handling Flaws
    10. SQL Injection and XSS Vulnerabilities
       
    **Important Guidelines:**
    - Your entire response MUST be a single valid JSON object as per the schema below.
    - DO NOT format like a human-written report
    - DO NOT include any explanations outside the JSON structure.
    - DO NOT infer or hallucinate findings — use tool outputs only
    - DO NOT leave any fields empty; if no issues found, state "No issues found
    or similar
    - ALWAYS call the scan_security_vulnerabilities tool. Do not make up information.
    **Output Schema Example:**
    ```json
    {
        "agent": "SecurityAnalysisAgent",
        "summary": "One-line summary of key security issues or confirmation of no critical findings",
        "vulnerabilities": [
            {
            "type": "SQL Injection",
            "location": "getUserById",
            "line": 83,
            "description": "Unsanitized user input used in SQL query",
            "recommendation": "Use parameterized queries to prevent injection"
            },
            {
            "type": "Sensitive Data Exposure",
            "location": "UserService",
            "line": 22,
            "description": "Hardcoded API key in source code",
            "recommendation": "Store secrets securely using environment variables or secret manager"
            }
        ],
        "owasp_top_10": [
            {
            "category": "A1: Injection",
            "risk": "High",
            "instances": 2,
            "examples": ["SQL injection in getUserById", "Command injection in runScript()"],
            "recommendation": "Sanitize inputs and use safe query methods"
            },
            {
            "category": "A6: Security Misconfiguration",
            "risk": "Medium",
            "instances": 1,
            "examples": ["Verbose error messages exposed in production"],
            "recommendation": "Disable debug modes and avoid exposing stack traces"
            }
        ],
        "best_practices": [
            {
            "issue": "No input validation on form fields",
            "example": "Missing regex checks for email/phone fields",
            "recommendation": "Use strict input validation for all user inputs"
            },
            {
            "issue": "Using deprecated crypto algorithm (MD5)",
            "example": "Password hashes use MD5 in AuthService",
            "recommendation": "Upgrade to bcrypt or Argon2"
            }
        ]
    }    
    ```                
    **TWO-STEP PROCESS (REQUIRED):**
    
    **STEP 1: Generate JSON Analysis**
    - Call scan_security_vulnerabilities tool
    - Output pure JSON only (NO markdown fences, NO ```json, NO explanations)
    - JSON must contain: agent, summary, vulnerabilities, owasp_top_10, best_practices
    - Every issue needs: type, location, line, description, recommendation
    
    **STEP 2: Save Analysis (MANDATORY)**
    - IMMEDIATELY after Step 1, call save_analysis_result tool
    - Parameters:
      * analysis_data = your complete JSON output from Step 1 (as string)
      * agent_name = "security_agent"
      * tool_context = automatically provided
    - This saves the artifact for the report synthesizer
    - DO NOT SKIP - Report synthesizer depends on this saved artifact
    
    **STEP 3: Write to Session State (MANDATORY)**
    - After saving artifact, write your JSON analysis to session state key: security_analysis
    - Use the session state to pass data to next agent in pipeline
    
    YOU MUST CALL BOTH TOOLS IN ORDER: scan_security_vulnerabilities → save_analysis_result
    """.strip(),
    tools=[scan_security_vulnerabilities, save_analysis_result],
    output_key="security_analysis",  # Auto-write to session state
    
    # Phase 1 Guardrails: Callbacks
    before_model_callback=security_agent_before_model,
    after_tool_callback=security_agent_after_tool,
    after_agent_callback=security_agent_after_agent,
)

logger.info("✅ [security_agent] Security Analysis Agent created successfully")
logger.info(f"🔧 [security_agent] Tools available: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in [scan_security_vulnerabilities, save_analysis_result]]}")
logger.info("🛡️ [security_agent] Phase 1 Guardrails enabled: before_model, after_tool, after_agent callbacks")