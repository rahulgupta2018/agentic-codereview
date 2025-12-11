"""
Report Synthesizer Agent
Combines parallel analysis results into comprehensive code review report
Following ADK parallel agent patterns like system monitor synthesizer
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
# __file__ is in agent_workspace/orchestrator_agent/sub_agents/report_synthesizer_agent/
# We need to go up 5 levels to reach the project root (agentic-codereview/)
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import centralized model configuration
from util.llm_model import get_agent_model

# Import artifact tools
from tools.artifact_loader_tool import load_analysis_results_from_artifacts
from tools.save_analysis_artifact import save_final_report

# Import callback utilities
from util.callbacks import (
    filter_bias,
    filter_hallucinations,
    execute_callback_safe,
    parse_json_safe,
    format_json_safe,
)
from util.metrics import CallbackTimer, get_metrics_collector

# ============================================================================
# PHASE 1 CALLBACKS
# ============================================================================

def report_synthesizer_before_agent(callback_context):
    """Validate all 4 artifacts are present before synthesizing report."""
    with CallbackTimer("report_synthesizer_agent", "before_agent") as timer:
        # Check session state for artifacts
        session_state = callback_context.state
        
        required_artifacts = [
            'security_analysis',
            'code_quality_analysis',
            'engineering_practices_analysis',
            'carbon_emission_analysis'
        ]
        
        missing_artifacts = []
        for artifact_key in required_artifacts:
            artifact_value = session_state.get(artifact_key, '')
            if not artifact_value:
                missing_artifacts.append(artifact_key)
        
        if missing_artifacts:
            logger.warning(f"⚠️ [report_synthesizer_agent] Missing artifacts: {missing_artifacts}")
        else:
            logger.info("✅ [report_synthesizer_agent] All 4 artifacts present in session state")
        
        timer.record_filtered('missing_artifacts', len(missing_artifacts))
        return None


def report_synthesizer_after_agent(callback_context):
    """Validate report completeness, log hallucinations (validation only)."""
    with CallbackTimer("report_synthesizer_agent", "after_agent") as timer:
        try:
            # Access final report from session state
            text = callback_context.state.get('final_report', '')
            if not text:
                logger.warning("⚠️ [report_synthesizer_agent] No final_report in state")
                return None
            
            # Check if report is markdown (not JSON)
            if text.strip().startswith('{'):
                logger.warning("⚠️ [report_synthesizer_agent] Report is JSON, not markdown - validation skipped")
                return None
            
            # Validate required sections are present
            required_sections = [
                r'#.*Executive Summary',
                r'#.*Security',
                r'#.*Code Quality',
                r'#.*Engineering Practices',
                r'#.*Environmental Impact',
                r'#.*Recommendations',
                r'#.*Next Steps',
            ]
            
            missing_sections = []
            for section_pattern in required_sections:
                if not re.search(section_pattern, text, re.IGNORECASE):
                    section_name = section_pattern.replace(r'#.*', '').replace('\\', '')
                    missing_sections.append(section_name)
            
            if missing_sections:
                logger.warning(f"⚠️ [report_synthesizer_agent] Report missing sections: {missing_sections}")
            
            # Load source artifacts for hallucination filtering
            source_artifacts = {
                'security_analysis': callback_context.state.get('security_analysis', ''),
                'code_quality_analysis': callback_context.state.get('code_quality_analysis', ''),
                'engineering_practices_analysis': callback_context.state.get('engineering_practices_analysis', ''),
                'carbon_emission_analysis': callback_context.state.get('carbon_emission_analysis', ''),
            }
            
            # Extract CVE IDs from report
            report_cves = set(re.findall(r'CVE-\d{4}-\d{4,7}', text, re.IGNORECASE))
            
            # Extract CVE IDs from security artifact
            security_analysis = parse_json_safe(source_artifacts.get('security_analysis', ''))
            source_cves = set()
            if security_analysis:
                for vuln in security_analysis.get('vulnerabilities', []):
                    if 'cve' in vuln:
                        source_cves.add(vuln['cve'])
            
            # Flag hallucinated CVEs
            hallucinations_filtered = 0
            hallucinated_cves = report_cves - source_cves
            if hallucinated_cves:
                logger.warning(f"⚠️ [report_synthesizer_agent] Report contains CVEs not in source: {hallucinated_cves}")
                hallucinations_filtered += len(hallucinated_cves)
            
            # Check for bias
            filtered_text = filter_bias(text)
            bias_filtered = 1 if filtered_text != text else 0
            
            if hallucinations_filtered > 0 or bias_filtered > 0 or missing_sections:
                logger.info(f"🛡️ [report_synthesizer_agent] Detected: hallucinations={hallucinations_filtered}, bias={bias_filtered}, missing_sections={len(missing_sections)}")
            
            # Record metrics
            timer.record_filtered('hallucinations', hallucinations_filtered)
            timer.record_filtered('bias', bias_filtered)
            timer.record_filtered('missing_sections', len(missing_sections))
            
            return None  # Validation only, no content modification
            
        except Exception as e:
            logger.error(f"❌ [report_synthesizer_agent] after_agent error: {e}")
            return None

# ============================================================================
# AGENT DEFINITION
# ============================================================================

def create_report_synthesizer_agent() -> Agent:
    """
    Create report synthesizer agent that combines analysis results.
    
    Returns:
        Agent: Report synthesizer agent
    """
    # Get the centralized model instance
    logger.info("🔧 [report_synthesizer_agent] Initializing Report Synthesizer Agent")
    agent_model = get_agent_model()
    logger.info(f"🔧 [report_synthesizer_agent] Model configured: {agent_model}")

    # Report Synthesizer Agent - combines all parallel analysis results
    logger.info("🔧 [report_synthesizer_agent] Creating Agent for report synthesis")
    return Agent(
        name="report_synthesizer_agent",
        model=agent_model,
        description="Synthesizes all code analysis results into a comprehensive review report",
        instruction="""You are a Report Synthesizer Agent in a simplified sequential pipeline.

Your job: Load analysis artifacts from all 4 analysis agents and synthesize a comprehensive markdown report.

**SEQUENTIAL PIPELINE CONTEXT:**
In the simplified pipeline, ALL 4 analysis agents ALWAYS run in this order:
1. Security Agent → security_analysis.json
2. Code Quality Agent → quality_analysis.json  
3. Engineering Practices Agent → engineering_analysis.json
4. Carbon Emission Agent → carbon_analysis.json

**STEP 1: Load All Analysis Artifacts**

Call load_analysis_results_from_artifacts() tool which returns:
- analysis_id: Timestamp-based ID for this analysis session
- results: Dictionary with all 4 agent outputs
  - "security_agent": {...security analysis JSON...}
  - "code_quality_agent": {...quality analysis JSON...}
  - "engineering_practices_agent": {...practices analysis JSON...}
  - "carbon_emission_agent": {...carbon analysis JSON...}
- agents_found: List of agents that saved artifacts
- total_agents: Count of agents (should be 4 in normal operation)
- message or error: Status information

**STEP 2: Generate Comprehensive Markdown Report**

If total_agents > 0 (artifacts found):

Create comprehensive report using ALL available analysis results:

# Code Review Report

**Agents Executed:** {use agents_found from tool response}  
**Date:** {current date/time}

## 📊 Executive Summary

Aggregate findings by severity across all analyses:
- **Critical** 🔴: [Count from all agents]
- **High** 🟠: [Count from all agents]
- **Medium** 🟡: [Count from all agents]
- **Low** 🟢: [Count from all agents]

**Key Concerns:** [Top 2-3 most important findings across all analyses]

## 🔍 Detailed Findings

### 🔒 Security Analysis
[Parse results["security_agent"] from tool response]
- List vulnerabilities with severity, location, and line numbers
- Highlight OWASP Top 10 risks
- Provide remediation guidance with examples

### 📊 Code Quality Analysis
[Parse results["code_quality_agent"] from tool response]
- Complexity metrics (cyclomatic, cognitive)
- Code smells and maintainability issues
- Refactoring opportunities with examples

### ⚙️ Engineering Practices
[Parse results["engineering_practices_agent"] from tool response]
- SOLID principles assessment
- Design pattern recommendations
- Testing and documentation quality
- Best practices compliance

### 🌱 Environmental Impact
[Parse results["carbon_emission_agent"] from tool response]
- Computational efficiency assessment
- Resource usage analysis
- Performance optimization opportunities
- Green software recommendations

## 💡 Prioritized Recommendations

Combine and prioritize all findings:

### Critical 🔴 (Fix Immediately)
[Security vulnerabilities, major bugs]

### High 🟠 (Fix Soon)
[Performance issues, maintainability problems]

### Medium 🟡 (This Sprint)
[Code quality improvements, refactoring opportunities]

### Low 🟢 (Backlog)
[Style improvements, documentation enhancements]

For each recommendation:
- Specific issue with file/line references
- Impact explanation
- Actionable fix guidance with code examples

## 🚀 Next Steps

1. **Immediate Actions** (Critical/High priority)
2. **Short-Term Improvements** (Medium priority)
3. **Long-Term Enhancements** (Low priority)

---
*Powered by Simplified Sequential Pipeline*

**STEP 3: Save the Final Report (MANDATORY)**

ALWAYS call save_final_report() tool after generating your report:
- Parameters:
  * report_markdown = your complete markdown report (as string)
  * tool_context = provided automatically by ADK
- This saves the final report to disk and ADK artifacts
- DO NOT skip this step - the report MUST be saved

**Critical Rules:**
- DO NOT include raw JSON in the report
- DO NOT hallucinate data - only use results from tool
- DO reference specific line numbers, function names, file paths
- DO use markdown formatting (headings, lists, code blocks, emoji)
- DO prioritize findings by actual severity from agent outputs
- If an agent ran but found no issues, state "No issues found" for that section
- If total_agents == 0, provide helpful introduction message (see above)
    
    ### � Code Quality Analysis  
    [Include ONLY if "code_quality_agent" is in agents_selected AND "code_quality_analysis" exists in session state]
    - Parse code_quality_analysis JSON
    - Complexity metrics
    - Code smells and maintainability issues
    
    ### ⚙️ Engineering Practices
    [Include ONLY if "engineering_practices_agent" is in agents_selected AND "engineering_practices_analysis" exists in session state]
    - Parse engineering_practices_analysis JSON
    - SOLID principles violations
    - Design pattern recommendations
    
    ### 🌱 Environmental Impact
    [Include ONLY if "carbon_emission_agent" is in agents_selected AND "carbon_emission_analysis" exists in session state]
    - Parse carbon_emission_analysis JSON
    - Performance inefficiencies
    - Carbon footprint estimates

    ## 💡 Prioritized Recommendations
    
    Combine findings from all agents and prioritize by severity:
    1. **Critical** 🔴 - Security vulnerabilities, major bugs (fix immediately)
    2. **High** 🟠 - Performance issues, maintainability problems (fix soon)
    3. **Medium** 🟡 - Code quality improvements, refactoring opportunities
    4. **Low** 🟢 - Style improvements, documentation enhancements
    
    For each recommendation:
    - State the issue clearly with specific references (line numbers, function names)
    - Explain the impact and why it matters
    - Provide actionable fix guidance with examples if possible
    
    ## 🚀 Next Steps
    
    Provide clear, prioritized action items:
    1. **Immediate Actions** (critical/high priority - fix now)
    2. **Short-Term Improvements** (medium priority - this sprint/week)
    3. **Long-Term Enhancements** (low priority - backlog items)

    **Output Format:**
    - Use markdown formatting for headings, subheadings, bullet points, and code blocks.
    - Highlight critical issues and prioritize recommendations.
    - Ensure clarity and professionalism in language.
    **Important Guidelines:**
    - DO NOT include any raw JSON in the final report.
    - DO NOT fabricate or infer information — use only the provided agent outputs.
    - DO NOT omit any sections; if no findings, state "No issues found" or similar.
    - ALWAYS reference specific findings from the input JSON to support your analysis.
    **Example Report Structure:**
    # Code Review Report
    ## Executive Summary
    [Overall assessment and key findings]
    ## Code Quality Analysis
    [Results from code quality agent]
    ## Security Analysis
    [Results from security agent]
    ## Engineering Practices
    [Results from engineering practices agent]
    ## Environmental Impact
    [Results from carbon emission agent]
    ## Recommendations
    [Prioritized action items]
    ## Next Steps
    [Clear implementation guidance]  

    **Report Guidelines:**
    - Use ✅🟢🟠🔴 to highlight risk/priority levels (optional but recommended)
	- Avoid jargon or tool-specific terms — write for cross-functional stakeholders
	- Be brief but actionable — every recommendation must help improve the code
	- You may collapse empty sections with “No critical findings” if applicable   

    **Output Requirements:**
    - Your entire response MUST be a single valid markdown document as per the structure above.  
    - ALWAYS produce markdown formatting for readability.
    - NEVER include any raw JSON or tool output in the final report.
    - DO NOT infer or hallucinate findings — use agent outputs only
    - DO NOT leave any sections empty; if no issues found, state "No issues found" or similar
    - Sections are in the specified order
	- Executive Summary is concise, 3-5 lines max
	- Each agent's results are clearly attributed and summarized
	- Recommendations are prioritized by severity + impact
	- Next Steps are implementation-focused


**Sequential Pipeline Rules:**
- In normal operation, ALL 4 agents run and save artifacts
- ALWAYS call load_analysis_results_from_artifacts() FIRST
- Use ONLY the data returned by the tool (analysis_id, results dict, agents_found list)
- Include sections for all agents found in agents_found list (should be 4)
- DO NOT include raw JSON in the report
- Parse JSON from results[agent_name] for each agent

**Two-Step Process:**
1. Call load_analysis_results_from_artifacts() to get all analyses
2. Call save_final_report() with your complete markdown report
   - Parameters: report_content (markdown string), analysis_id (from step 1)
   - This saves the final report as an artifact
    """.strip(),
        output_key="final_report",
        tools=[load_analysis_results_from_artifacts, save_final_report],
        
        # Phase 1 Guardrails: Callbacks
        before_agent_callback=report_synthesizer_before_agent,
        after_agent_callback=report_synthesizer_after_agent,
    )


# Create agent instance for import by orchestrator
report_synthesizer_agent = create_report_synthesizer_agent()

logger.info("✅ [report_synthesizer_agent] Report Synthesizer Agent created successfully")
logger.info("🔧 [report_synthesizer_agent] Output key configured: final_report")
logger.info("🔧 [report_synthesizer_agent] Tools available: ['load_analysis_results_from_artifacts', 'save_final_report']")
logger.info("🛡️ [report_synthesizer_agent] Phase 1 Guardrails enabled: before_agent, after_agent callbacks")