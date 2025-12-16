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


# Add project root to Python path for absolute imports
# __file__ is in agent_workspace/orchestrator_agent/sub_agents/security_agent/
# We need to go up 5 levels to reach the project root (agentic-codereview/)
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import centralized model configuration
from util.llm_model import get_sub_agent_model
from util.markdown_yaml_parser import parse_analysis, validate_analysis, filter_content

# Import callback utilities
from util.callbacks import (
    validate_cve_exists,
    filter_bias,
    filter_false_positives,
    execute_callback_safe
)
from util.metrics import CallbackTimer, get_metrics_collector
from util.markdown_yaml_parser import parse_analysis, reconstruct_analysis, validate_analysis
from util.security_enrichment import compute_confidence, adjust_severity_by_confidence, attach_guideline_refs

# Import tools
from tools.security_vulnerability_scanner import scan_security_vulnerabilities
from tools.save_analysis_artifact import save_analysis_result

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
    After Tool Callback - Normalize findings, filter false positives, enrich with
    confidence + guideline references, and recompute summary.

    Expected tool_response (merged scanner):
      - owasp_top_10_analysis: {category: [finding...], ...}
      - sast_rules: {findings: [finding...], ...}
      - (optional) vulnerabilities (legacy)

    Produces:
      - tool_response["vulnerabilities"]: final, enriched list
      - tool_response["vulnerability_summary"]: recomputed from final severities
    """
    with CallbackTimer("security_agent", "after_tool") as timer:
        try:
            tool_name = tool if isinstance(tool, str) else getattr(tool, "name", str(tool))
            if tool_name != "scan_security_vulnerabilities":
                return None

            if not isinstance(tool_response, dict):
                logger.warning("⚠️ [security_agent] after_tool: tool_response not a dict")
                return None

            # ------------------------------------------------------------------
            # 1) Normalize: flatten OWASP + SAST + legacy findings
            # ------------------------------------------------------------------
            vulnerabilities = []

            # A) SAST rule findings
            sast_block = tool_response.get("sast_rules") or {}
            sast_findings = (
                sast_block.get("findings", [])
                if isinstance(sast_block, dict)
                else []
            )

            for f in sast_findings:
                if not isinstance(f, dict):
                    continue
                vulnerabilities.append({
                    "source": "sast",
                    "type": f.get("type") or "sast_rule_match",
                    "rule_id": f.get("rule_id"),
                    "title": f.get("title"),
                    "description": f.get("description") or f.get("message"),
                    "category": f.get("category"),
                    "severity": (f.get("severity") or "low").lower(),
                    "confidence": f.get("confidence"),
                    "file_path": f.get("file_path") or tool_response.get("file_path"),
                    "line": f.get("line"),
                    "code_snippet": f.get("code_snippet") or f.get("evidence"),
                    "cwe": f.get("cwe") or ([] if not f.get("cwe_id") else [f.get("cwe_id")]),
                    "owasp_top_10_2021": f.get("owasp_top_10_2021") or [],
                })

            # B) OWASP category findings
            owasp_block = tool_response.get("owasp_top_10_analysis") or {}
            if isinstance(owasp_block, dict):
                for owasp_category, findings in owasp_block.items():
                    if not isinstance(findings, list):
                        continue
                    for f in findings:
                        if not isinstance(f, dict):
                            continue
                        vulnerabilities.append({
                            "source": "owasp",
                            "type": f.get("type") or owasp_category,
                            "subtype": f.get("subtype"),
                            "title": f.get("title") or f.get("message") or owasp_category,
                            "description": f.get("description") or f.get("message"),
                            "category": f.get("category"),
                            "severity": (f.get("severity") or "low").lower(),
                            "confidence": f.get("confidence"),
                            "file_path": f.get("file_path") or tool_response.get("file_path"),
                            "line": f.get("line"),
                            "code_snippet": f.get("code_snippet") or f.get("evidence"),
                            "cwe": f.get("cwe") or ([] if not f.get("cwe_id") else [f.get("cwe_id")]),
                            "owasp_top_10_2021": f.get("owasp_top_10_2021") or [],
                        })

            # C) Legacy vulnerabilities (if any)
            legacy_vulns = tool_response.get("vulnerabilities")
            if isinstance(legacy_vulns, list):
                for f in legacy_vulns:
                    if isinstance(f, dict):
                        vulnerabilities.append(f)

            # De-duplicate
            deduped = []
            seen = set()
            for v in vulnerabilities:
                key = (
                    v.get("rule_id") or "",
                    v.get("type") or "",
                    v.get("file_path") or "",
                    v.get("line") or 0,
                    (v.get("code_snippet") or "")[:80],
                )
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(v)

            vulnerabilities = deduped

            if not vulnerabilities:
                tool_response["vulnerabilities"] = []
                tool_response["vulnerability_summary"] = {
                    "total_vulnerabilities": 0,
                    "critical_vulnerabilities": 0,
                    "high_vulnerabilities": 0,
                    "medium_vulnerabilities": 0,
                    "low_vulnerabilities": 0,
                }
                return tool_response

            # ------------------------------------------------------------------
            # 2) Filter false positives
            # ------------------------------------------------------------------
            filtered_vulns, removed_count = filter_false_positives(
                vulnerabilities, "security_agent"
            )
            timer.record_filtered("false_positives", removed_count)

            # ------------------------------------------------------------------
            # 3) Validate minimal evidence
            # ------------------------------------------------------------------
            validated_vulns = []
            for vuln in filtered_vulns:
                has_description = bool(vuln.get("description") or vuln.get("title"))
                has_evidence = bool(vuln.get("line") or vuln.get("code_snippet"))
                if has_description and has_evidence:
                    validated_vulns.append(vuln)
                else:
                    timer.record_filtered("missing_evidence", 1)

            # ------------------------------------------------------------------
            # 4) Enrich: confidence, severity adjustment, guideline refs
            # ------------------------------------------------------------------
            from util.security_enrichment import (
                compute_confidence,
                adjust_severity_by_confidence,
                attach_guideline_refs,
            )

            security_guidelines = tool_context.state.get("security_guidelines") or {}

            enriched = []
            for vuln in validated_vulns:
                conf = compute_confidence(vuln)
                vuln["confidence"] = conf
                vuln["severity"] = adjust_severity_by_confidence(
                    vuln.get("severity", "low"), conf
                )
                vuln = attach_guideline_refs(vuln, security_guidelines)
                enriched.append(vuln)

            tool_response["vulnerabilities"] = enriched

            # ------------------------------------------------------------------
            # 5) Recompute vulnerability summary AFTER enrichment
            # ------------------------------------------------------------------
            summary = {
                "total_vulnerabilities": len(enriched),
                "critical_vulnerabilities": 0,
                "high_vulnerabilities": 0,
                "medium_vulnerabilities": 0,
                "low_vulnerabilities": 0,
            }

            for vuln in enriched:
                sev = (vuln.get("severity") or "low").lower()
                key = f"{sev}_vulnerabilities"
                if key in summary:
                    summary[key] += 1

            tool_response["vulnerability_summary"] = summary

            logger.info(
                "✅ [security_agent] after_tool: normalized=%d filtered=%d validated=%d final=%d",
                len(vulnerabilities),
                len(filtered_vulns),
                len(validated_vulns),
                len(enriched),
            )

            return tool_response

        except Exception as e:
            logger.error(
                "❌ [security_agent] after_tool error: %s", e, exc_info=True
            )
            return None  # Fail open


def security_agent_after_agent(callback_context):
    """
    After Agent Callback - Validate and sanitize the final security analysis.

    Accesses agent output via session state:
      - Parses Markdown+YAML
      - Validates required metadata/body structure
      - Applies centralized bias/profanity filtering
      - Detects invalid CVEs (and optionally removes them from the text)
      - Writes corrected output back into state when changes were made
    """
    with CallbackTimer("security_agent", "after_agent") as timer:
        try:
            analysis = callback_context.state.get("security_analysis", "")
            if not analysis:
                logger.warning("⚠️ [security_agent] No security_analysis in state")
                # Helpful context: tool output lives elsewhere now
                if callback_context.state.get("security_scan_result"):
                    logger.info("ℹ️ [security_agent] security_scan_result exists (tool output). Agent output_key 'security_analysis' is missing.")
                return None

            # At this point, security_analysis SHOULD always be a string (agent output).
            if not isinstance(analysis, str):
                logger.warning(
                    "⚠️ [security_agent] Expected security_analysis to be a string, got %s. Skipping validation.",
                    type(analysis).__name__,
                )
                return None

            text = analysis

            metadata, markdown_body = parse_analysis(text)
            if not metadata:
                logger.warning("⚠️ [security_agent] after_agent: Could not parse Markdown+YAML")
                return None

            # Validate required fields (log only)
            errors = validate_analysis(metadata, markdown_body, "security_agent")
            if errors:
                logger.warning("⚠️ [security_agent] Validation errors: %s", errors)

            # 1) Bias/profanity filtering (centralized, config-driven)
            filtered_body, bias_filtered = filter_bias(markdown_body)
            timer.record_filtered("bias", bias_filtered)

            if bias_filtered > 0:
                logger.warning(
                    "🚫 [security_agent] filter_bias removed %d biased/profane replacements",
                    bias_filtered,
                )

            # 2) CVE validation
            import re
            cve_pattern = r"CVE-\d{4}-\d{4,7}"
            cves_found = re.findall(cve_pattern, filtered_body)

            invalid_cves = []
            for cve_id in cves_found:
                if not validate_cve_exists(cve_id):
                    logger.warning("🚫 [security_agent] Found potentially hallucinated/invalid CVE: %s", cve_id)
                    invalid_cves.append(cve_id)

            cve_filtered = len(invalid_cves)
            timer.record_filtered("invalid_cves", cve_filtered)

            # OPTIONAL: remove invalid CVEs from the text (prevention instead of just detection)
            if invalid_cves:
                for cve_id in invalid_cves:
                    filtered_body = re.sub(rf"\b{re.escape(cve_id)}\b", "[invalid-cve-removed]", filtered_body)

            # 3) Write back only if we changed something
            changed = (bias_filtered > 0) or (cve_filtered > 0)
            if changed:
                fixed = reconstruct_analysis(metadata, filtered_body)
                callback_context.state["security_analysis"] = fixed

            logger.info(
                "✅ [security_agent] after_agent: Checked %d CVEs (%d invalid), %d bias/profanity replacements%s",
                len(cves_found),
                cve_filtered,
                bias_filtered,
                " (updated state)" if changed else "",
            )

            return None  # Fail-open; pipeline continues

        except Exception as e:
            logger.error("❌ [security_agent] after_agent error: %s", e, exc_info=True)
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
    instruction="""
    You are the Security Analysis Agent. Your job is to identify security vulnerabilities in the PR codebase and report them with evidence.

CRITICAL FORMAT REQUIREMENT
- Your response MUST begin with the YAML frontmatter.
- Do not write any text before the opening '---'.

IMPORTANT REALITY CHECK
- The PR code is stored in shared session state under the key "code".
- You (the LLM) do NOT read session state directly.
- The tool scan_security_vulnerabilities reads the PR code from session state internally.
- The tool output is the ONLY source of truth.

STEP 1: Run the security scan (MANDATORY)
- ALWAYS call scan_security_vulnerabilities() exactly once at the start of your analysis.
- Do NOT skip this call.
- Do NOT invent issues before the scan results are available.

STEP 2: Analyze the tool output (SOURCE OF TRUTH)
- Use ONLY the tool output for:
  - file paths
  - line numbers
  - code snippets / evidence
  - severity
  - CWE / OWASP tags
  - CVE references (ONLY if present in tool output)
- Do NOT make up file names, line numbers, code snippets, or CVEs.

Tool output may contain findings in:
- OWASP Top 10 categories (e.g. injection_vulnerabilities, broken_authentication, etc.)
- SAST rule-based findings (language-specific or generic)

Treat ALL tool-reported findings as valid inputs.
If uncertainty exists in a finding, clearly state it and recommend verification.

STEP 3: Apply security guidelines (IF AVAILABLE)
- If security guidelines are available in session state under "security_guidelines":
  - Categorize findings using those guideline categories
  - Reference the relevant guideline rule(s) in your explanation
- Do NOT claim guideline coverage if guidelines are missing.

STEP 4: Create the report in Markdown + YAML format

Your response MUST follow this exact structure:

---
agent: security_agent
summary: Brief summary of findings
total_issues: X
severity:
  critical: X
  high: X
  medium: X
  low: X
confidence: 0.XX
---

# Security Analysis

For each issue include:
- Title (short and descriptive)
- Severity (critical / high / medium / low)
- Evidence (FROM TOOL OUTPUT ONLY):
  - File path (if provided)
  - Line number(s) (if provided)
  - Code snippet (from tool output)
- Explanation:
  - Why this is a security risk
  - Potential impact
- Recommendation:
  - Concrete mitigation or fix guidance
- References:
  - CWE / OWASP category (if provided)
  - CVE IDs ONLY if provided by the tool output

NO-ISSUE CASE:
- If the scan reports zero findings, write exactly:
  "No significant security issues found."

STEP 5: Save your analysis (MANDATORY)
After completing the report, you MUST call:

save_analysis_result(
  analysis_data="<your complete Markdown+YAML analysis>",
  agent_name="security_agent"
)

CRITICAL RULES
- ALWAYS call scan_security_vulnerabilities() first.
- ALWAYS call save_analysis_result() last.
- NEVER hallucinate evidence (paths, lines, snippets, CVEs).
- Prefer fewer, higher-confidence findings over speculative ones.
    """.strip(),
    output_key="security_analysis",
    tools=[scan_security_vulnerabilities, save_analysis_result],
    
    # Phase 1 Guardrails: Callbacks
    before_model_callback=security_agent_before_model,
    after_tool_callback=security_agent_after_tool,
    after_agent_callback=security_agent_after_agent,
)

logger.info("✅ [security_agent] Security Analysis Agent created successfully")
logger.info(f"🔧 [security_agent] Tools available: {[tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in [scan_security_vulnerabilities, save_analysis_result]]}")
logger.info("🛡️ [security_agent] Phase 1 Guardrails enabled: before_model, after_tool, after_agent callbacks")