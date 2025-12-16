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
    execute_callback_safe
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
            
            # Extract CVE IDs from security artifact (now Markdown+YAML text)
            security_artifact_text = source_artifacts.get('security_analysis', '')
            source_cves = set(re.findall(r'CVE-\d{4}-\d{4,7}', security_artifact_text, re.IGNORECASE))
            
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
        instruction="""You are a Report Synthesizer Agent. Your job is to create a comprehensive code review report.

**STEP 1: Load Analysis Results**

First, call the load_analysis_results_from_artifacts() tool to get all agent analyses.

The tool returns:
- results: Dictionary containing analysis from each agent (Markdown+YAML format)
- agents_found: List of agents that produced results
- session_id: Current session identifier

**STEP 2: Create Your Report**

Generate a comprehensive markdown report with the following structure:

# Code Review Report

**Session:** [session_id]
**Agents:** [list agents_found]
**Date:** [current date]

## 📊 Executive Summary

[Brief overview of key findings - 3-5 sentences summarizing the most important issues]

## 🔍 Detailed Findings

### 🔒 Security Analysis
[Copy relevant findings from results["security_agent"] if available, or state "No security analysis available"]

### 📊 Code Quality Analysis
[Copy relevant findings from results["code_quality_agent"] if available, or state "No code quality analysis available"]

### ⚙️ Engineering Practices
[Copy relevant findings from results["engineering_practices_agent"] if available, or state "No engineering practices analysis available"]

### 🌱 Environmental Impact
[Copy relevant findings from results["carbon_emission_agent"] if available, or state "No carbon analysis available"]

## 💡 Recommendations

[Prioritized list of actionable recommendations based on all findings]

**STEP 3: Save Your Report**

After generating the report, call save_final_report() tool with:
- report_markdown: Your complete markdown report as a string

**CRITICAL RULES:**
- ALWAYS call load_analysis_results_from_artifacts() first
- ALWAYS call save_final_report() with your complete report
- Your response should be valid markdown
- DO NOT include raw YAML frontmatter in the final report
- DO NOT make up findings - only use data from the loaded artifacts
- If an agent's results are missing, state that clearly
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