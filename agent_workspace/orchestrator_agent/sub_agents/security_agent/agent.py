"""
Security Agent
Simple security analysis agent following ADK parallel agent patterns
"""

import sys
import logging
from pathlib import Path
from google.adk.agents import Agent

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

# Get the centralized model instance
logger.info("🔧 [security_agent] Initializing Security Analysis Agent")
agent_model = get_sub_agent_model()
logger.info(f"🔧 [security_agent] Model configured: {agent_model}")

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
)

logger.info("✅ [security_agent] Security Analysis Agent created successfully")
logger.info(f"🔧 [security_agent] Tools available: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in [scan_security_vulnerabilities, save_analysis_result]]}")