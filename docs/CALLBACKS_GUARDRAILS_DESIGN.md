# Callbacks, Guardrails & Quality Loop Implementation Design Document

**Version:** 3.1  
**Date:** December 11, 2025  
**Status:** Phase 1 Complete - Markdown+YAML Output Format

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Agent-Specific Callback Strategies](#2-agent-specific-callback-strategies)
3. [Shared Callback Infrastructure](#3-shared-callback-infrastructure)
4. [Configuration File Structure](#4-configuration-file-structure)
5. [Implementation Plan](#5-implementation-plan)
6. [Testing Strategy](#6-testing-strategy)
7. [Configuration Management](#7-configuration-management)
8. [Success Criteria](#8-success-criteria)
9. [Risk Mitigation](#9-risk-mitigation)
10. [Quality Loop Evaluation System (LLM-as-a-Judge)](#10-quality-loop-evaluation-system-llm-as-a-judge)
11. [Confidence Scoring & Evaluation Architecture](#11-confidence-scoring--evaluation-architecture)
12. [Next Steps](#12-next-steps)
13. [Appendix A: ADK Callback Reference](#appendix-a-adk-callback-reference)

---

## Executive Summary

This document outlines the comprehensive **three-tier quality assurance strategy** for the Agentic Code Review System, combining:

### Tier 1: Inline Guardrails (Callbacks)
Real-time prevention during agent execution:
- ✅ **Hallucination Prevention** - Agents provide factually accurate, evidence-based analysis
- ✅ **Quality Control** - All outputs meet defined quality standards
- ✅ **Security** - No profanity, bias, or inappropriate content in responses
- ✅ **Self-Preservation** - Agents don't make self-destructive recommendations
- ✅ **False Positive Prevention** - Findings are validated and actionable

### Tier 2: Iterative Refinement (Quality Loop)
Post-generation validation using LLM-as-a-Judge pattern:
- ✅ **Holistic Evaluation** - Comprehensive report assessment against multiple criteria
- ✅ **Iterative Refinement** - Automatic improvement through Critic → Refiner loop
- ✅ **Cross-Validation** - Verify report findings match source artifacts
- ✅ **Early Exit** - Stop when quality threshold met (saves time/cost)
- ✅ **Safety Net** - Max 5 iterations prevents runaway costs

### Tier 3: Context Engineering & Evaluation (NEW)
Knowledge-based prevention and independent validation:
- ✅ **Context Engineering** - Inject domain-specific guidelines into agent prompts
- ✅ **Confidence Scoring** - Each finding includes 0.0-1.0 confidence score
- ✅ **Evaluator Agent** - Independent LLM-as-a-Judge scores findings post-analysis
- ✅ **False Positive Detection** - Automated flagging of likely false positives
- ✅ **Guideline Alignment** - Verify findings match knowledge base standards

**Strategy:** Context engineering prevents false positives at source, callbacks ensure quality during execution, evaluator validates findings post-analysis, and quality loop refines the final report before delivery. Target: <5% false positive rate.

---

## 1. Architecture Overview

### 1.1 Complete System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                                      │
│          "Review PR #123 from repo/project"                               │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                                     │
│                  (Coordinates entire flow)                                │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                    GITHUB DATA ADAPTER                                    │
│              Fetches code, PR details, diff                               │
│              Callbacks: Input validation                                  │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│              PARALLEL ANALYSIS AGENTS (Tier 1 Quality)                    │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐        │
│  │ SECURITY   │  │  QUALITY   │  │ ENGINEERING│  │  CARBON    │        │
│  │   AGENT    │  │   AGENT    │  │   AGENT    │  │   AGENT    │        │
│  └────────────┘  └────────────┘  └────────────┘  └────────────┘        │
│                                                                           │
│  Each agent has INLINE CALLBACKS:                                        │
│    ✅ before_model_callback  → Inject guidance, constraints              │
│    ✅ after_tool_callback    → Validate tool output, filter FPs          │
│    ✅ after_agent_callback   → Remove hallucinations, bias               │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                    ARTIFACT SAVER AGENT                                   │
│         Saves 4 analysis artifacts (Markdown+YAML) to storage             │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                    REPORT SYNTHESIZER AGENT                               │
│            Aggregates findings into markdown report                       │
│            Callbacks: Artifact validation, hallucination check            │
│            Output: DRAFT REPORT (may have issues)                         │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│         🔁 QUALITY LOOP (Tier 2 Quality - LLM-as-a-Judge) 🔁              │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────┐          │
│  │  Iteration 1-5 (exits early when quality met)              │          │
│  │                                                             │          │
│  │  ┌──────────────┐              ┌──────────────┐            │          │
│  │  │   CRITIC     │─────────────▶│   REFINER    │            │          │
│  │  │   AGENT      │              │    AGENT     │            │          │
│  │  │              │              │              │            │          │
│  │  │ Evaluates:   │              │ Improves:    │            │          │
│  │  │ ✓ Evidence   │              │ ✓ Add line#s │            │          │
│  │  │ ✓ No halluc. │              │ ✓ Remove FPs │            │          │
│  │  │ ✓ Objective  │              │ ✓ Fix bias   │            │          │
│  │  │ ✓ No FPs     │              │ ✓ Add evid.  │            │          │
│  │  │ ✓ Complete   │              │ OR           │            │          │
│  │  │              │              │ ✓ exit_loop()│            │          │
│  │  └──────────────┘              └──────────────┘            │          │
│  │        ↓                              ↓                    │          │
│  │  Critique: Issues              Improved Report            │          │
│  │  OR "APPROVED"                 (overwrites draft)         │          │
│  └────────────────────────────────────────────────────────────┘          │
│                                                                           │
│  Exit Conditions:                                                         │
│    ✅ Critic approves (all criteria met)                                  │
│    ✅ Max 5 iterations reached (safety net)                               │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                    REPORT SAVER AGENT                                     │
│            Saves VALIDATED final report to storage                        │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                    FINAL VALIDATED REPORT                                 │
│   ✅ Evidence-based (all findings have line numbers/metrics)              │
│   ✅ No hallucinations (verified against source artifacts)                │
│   ✅ Objective language (no bias/profanity)                               │
│   ✅ No false positives (validated against patterns)                      │
│   ✅ Complete & actionable (all sections present)                         │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Callback Layers (Tier 1: Inline Guardrails)

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR LEVEL                        │
│  - Global monitoring                                         │
│  - Cross-agent validation                                    │
│  - Performance tracking                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    AGENT-SPECIFIC LEVEL                      │
│  Security Agent | Quality Agent | Engineering | Carbon       │
│  - Domain-specific guardrails                                │
│  - Tool validation                                           │
│  - Output quality gates                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    TOOL EXECUTION LEVEL                      │
│  - Input validation                                          │
│  - Rate limiting                                             │
│  - Result verification                                       │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Guardrail Types by Concern

| Concern | Guardrail Type | Implementation Layer |
|---------|---------------|---------------------|
| Hallucination | Evidence Validation | `after_model_callback` |
| Profanity/Bias | Content Filtering | `before_model_callback`, `after_model_callback` |
| Quality Control | Output Validation | `after_agent_callback` |
| False Positives | Finding Verification | `after_tool_callback` |
| Self-Destruction | Recommendation Filter | `after_agent_callback` |
| Security Attacks | Input Sanitization | `before_agent_callback` |

### 1.4 Two-Tier Quality Strategy Comparison

| Aspect | Tier 1: Callbacks (Inline) | Tier 2: Quality Loop (Post-Processing) |
|--------|---------------------------|----------------------------------------|
| **Timing** | During agent execution | After report synthesis |
| **Scope** | Per-agent, per-operation | Holistic report validation |
| **Mechanism** | Hook functions (before/after) | Critic-Refiner LoopAgent |
| **Latency** | <100ms per callback | 15-60s total (1-5 iterations) |
| **Cost** | Negligible (no LLM calls) | ~$0.01-0.02 per review |
| **Prevention** | ✅ Stops bad data at source | ✅ Catches issues that slipped through |
| **Context** | Limited (single operation) | Full report + all artifacts |
| **Iteration** | ❌ Single-pass only | ✅ Iterative refinement (up to 5x) |
| **Validation** | Agent-specific rules | Cross-agent consistency |
| **Best For** | Real-time prevention | Comprehensive validation |
| **Example** | Filter false positive SQL injection in Security Agent | Verify all findings have evidence across entire report |

**Why Both?**
- **Callbacks**: Fast, preventive, domain-specific → Block obvious issues early
- **Quality Loop**: Thorough, iterative, holistic → Ensure final output meets all standards

**Analogy:**
- Callbacks = Spell-check while typing (real-time)
- Quality Loop = Professional editor review (after draft complete)

---

## 2. Agent-Specific Callback Strategies

### 2.1 Security Agent

#### Primary Concerns
1. **False Positives** - Flagging benign code as vulnerabilities
2. **Hallucinated Vulnerabilities** - Reporting non-existent security issues
3. **Missing Context** - Misunderstanding secure patterns

#### Callback Implementation

**before_model_callback:**
```python
def security_agent_before_model(callback_context, llm_request):
    """
    Guardrails:
    - Add security analysis constraints to system instruction
    - Inject OWASP/CWE reference guidance
    - Require evidence-based findings only
    """
    # Add to system instruction
    safety_guidance = """
    CRITICAL SECURITY ANALYSIS RULES:
    1. Only report vulnerabilities with concrete evidence (line numbers, patterns)
    2. Reference CWE/OWASP standards for each finding
    3. Consider context - not all dynamic queries are SQL injection
    4. Distinguish between actual vulnerabilities and potential risks
    5. Provide mitigation steps, not just criticism
    """
    llm_request.config.system_instruction += safety_guidance
    return None  # Allow with modifications
```

**after_tool_callback:**
```python
def security_agent_after_tool(callback_context, tool_name, tool_response):
    """
    Validation:
    - Verify vulnerability findings have required fields
    - Cross-check against known false positive patterns
    - Validate severity ratings
    """
    if tool_name == 'scan_security_vulnerabilities':
        validated_vulns = []
        for vuln in tool_response.get('vulnerabilities', []):
            # Check required evidence fields
            if not all([
                vuln.get('line_number'),
                vuln.get('code_snippet'),
                vuln.get('cwe_id') or vuln.get('owasp_id')
            ]):
                logger.warning(f"Filtered vulnerability without evidence: {vuln.get('type')}")
                continue
            
            # Check against false positive patterns
            if not is_false_positive(vuln, callback_context):
                validated_vulns.append(vuln)
        
        tool_response['vulnerabilities'] = validated_vulns
        return tool_response
    
    return None
```

**after_agent_callback:**
```python
def security_agent_after_agent(callback_context, content):
    """
    Quality Gates:
    - Ensure all findings are evidence-based
    - Validate JSON structure
    - Check for hallucinated CVEs
    - Remove profanity/bias from descriptions
    """
    # Parse security analysis (Markdown+YAML)
    text = content.parts[0].text
    parts = text.split('---', 2)
    metadata = yaml.safe_load(parts[1]) if len(parts) >= 3 else {}
    markdown_body = parts[2] if len(parts) >= 3 else text
    
    # Validate each vulnerability
    for vuln in analysis.get('vulnerabilities', []):
        # Check for hallucinated CVEs
        if 'cve_id' in vuln:
            if not validate_cve_exists(vuln['cve_id']):
                logger.warning(f"Removed hallucinated CVE: {vuln['cve_id']}")
                del vuln['cve_id']
        
        # Content moderation on descriptions
        vuln['description'] = filter_profanity_and_bias(vuln['description'])
    
    # Update content with filtered analysis
    filtered_text = json.dumps(analysis, indent=2)
    return types.Content(parts=[types.Part(text=filtered_text)], role="model")
```

#### Configuration Usage
- Load from: `config/guardrails/security_analysis.yaml`
- Load patterns for false positive detection
- Reference severity thresholds

---

### 2.2 Code Quality Agent

#### Primary Concerns
1. **Subjective Criticism** - "This code is messy" without metrics
2. **Language Bias** - Favoring certain languages/frameworks
3. **Unrealistic Standards** - Expecting enterprise patterns in small projects

#### Callback Implementation

**before_model_callback:**
```python
def quality_agent_before_model(callback_context, llm_request):
    """
    Guardrails:
    - Enforce objective, metric-based analysis
    - Load acceptable threshold ranges from config
    - Require evidence for all quality claims
    """
    quality_guidance = """
    CODE QUALITY ANALYSIS REQUIREMENTS:
    1. Base ALL findings on measurable metrics (cyclomatic complexity, coupling, etc.)
    2. Do NOT use subjective language ("messy", "ugly", "bad")
    3. Consider project context (size, team, domain)
    4. Provide actionable refactoring suggestions with examples
    5. Acknowledge when code meets acceptable standards
    """
    
    # Load thresholds from config
    thresholds = load_yaml_config('config/guardrails/quality_gates.yaml')
    context_info = f"\nAcceptable Thresholds: {json.dumps(thresholds['code_quality_gates']['code_quality']['thresholds'])}"
    
    llm_request.config.system_instruction += quality_guidance + context_info
    return None
```

**after_tool_callback:**
```python
def quality_agent_after_tool(callback_context, tool_name, tool_response):
    """
    Validation:
    - Verify complexity calculations are within reasonable bounds
    - Check for tool errors or anomalies
    - Validate metric ranges
    """
    if tool_name in ['analyze_code_complexity', 'analyze_static_code']:
        # Sanity check complexity values
        if 'cyclomatic_complexity' in tool_response:
            cc = tool_response['cyclomatic_complexity']
            if cc < 1 or cc > 1000:
                logger.error(f"Impossible complexity value: {cc}")
                return {'status': 'error', 'message': 'Invalid complexity calculation'}
        
        # Check for null/undefined metrics
        for key, value in tool_response.items():
            if value is None and key in ['cyclomatic_complexity', 'maintainability_index']:
                tool_response[key] = 'N/A'
    
    return None
```

**after_agent_callback:**
```python
def quality_agent_after_agent(callback_context, content):
    """
    Quality Gates:
    - Remove subjective language
    - Validate all metrics are evidence-based
    - Apply bias prevention rules
    """
    analysis = json.loads(content.parts[0].text)
    
    # Load bias prevention config
    bias_config = load_yaml_config('config/guardrails/bias_prevention.yaml')
    
    # Filter findings for bias
    for issue in analysis.get('quality_issues', []):
        # Check for subjective language
        subjective_words = ['messy', 'ugly', 'bad', 'terrible', 'awful']
        for word in subjective_words:
            if word in issue.get('description', '').lower():
                logger.warning(f"Removed subjective language from: {issue['description']}")
                issue['description'] = remove_subjective_language(issue['description'])
        
        # Ensure metric-based evidence
        if 'metric' not in issue and 'complexity' not in issue:
            logger.warning(f"Filtered non-metric-based issue: {issue.get('type')}")
            analysis['quality_issues'].remove(issue)
    
    filtered_text = json.dumps(analysis, indent=2)
    return types.Content(parts=[types.Part(text=filtered_text)], role="model")
```

---

### 2.3 Engineering Practices Agent

#### Primary Concerns
1. **Architectural Dogma** - "Must use microservices" without context
2. **Pattern Enforcement** - Forcing design patterns inappropriately
3. **Scale Assumptions** - Enterprise patterns for small projects

#### Callback Implementation

**before_model_callback:**
```python
def engineering_agent_before_model(callback_context, llm_request):
    """
    Guardrails:
    - Inject context-aware guidance
    - Load bias prevention rules for architecture
    - Require pragmatic recommendations
    """
    engineering_guidance = """
    ENGINEERING PRACTICES EVALUATION:
    1. Consider project context (team size, complexity, domain)
    2. Multiple valid approaches exist - avoid dogma
    3. Balance ideal architecture vs practical constraints
    4. Provide trade-off analysis for recommendations
    5. Acknowledge when existing patterns are appropriate
    """
    
    # Load context-aware guidance from config
    bias_config = load_yaml_config('config/guardrails/bias_prevention.yaml')
    architecture_rules = bias_config['bias_prevention']['domain_specific']['architecture']
    
    context_guidance = "\nArchitecture Guidelines:\n" + "\n".join(f"- {rule}" for rule in architecture_rules)
    
    llm_request.config.system_instruction += engineering_guidance + context_guidance
    return None
```

**after_agent_callback:**
```python
def engineering_agent_after_agent(callback_context, content):
    """
    Quality Gates:
    - Ensure recommendations are pragmatic
    - Filter architectural dogma
    - Validate trade-offs are presented
    """
    analysis = json.loads(content.parts[0].text)
    
    # Check for dogmatic recommendations
    dogma_patterns = [
        r'must use microservices',
        r'always use.*pattern',
        r'never use',
        r'only.*is acceptable'
    ]
    
    for recommendation in analysis.get('recommendations', []):
        desc = recommendation.get('description', '')
        for pattern in dogma_patterns:
            if re.search(pattern, desc, re.IGNORECASE):
                # Soften dogmatic language
                recommendation['description'] = soften_recommendation(desc)
                logger.info(f"Softened dogmatic recommendation: {desc[:50]}...")
    
    filtered_text = json.dumps(analysis, indent=2)
    return types.Content(parts=[types.Part(text=filtered_text)], role="model")
```

---

### 2.4 Carbon Emission Agent

#### Primary Concerns
1. **Greenwashing** - Exaggerating environmental benefits
2. **Unrealistic Estimates** - Claiming precise carbon savings without evidence
3. **False Trade-offs** - Ignoring performance/cost for minor carbon gains

#### Callback Implementation

**before_model_callback:**
```python
def carbon_agent_before_model(callback_context, llm_request):
    """
    Guardrails:
    - Require evidence-based carbon estimates
    - Load sustainability bias prevention rules
    - Enforce cost-benefit analysis requirement
    """
    carbon_guidance = """
    CARBON EMISSION ANALYSIS REQUIREMENTS:
    1. Provide measurable or estimated metrics (kWh, CPU cycles)
    2. Present cost-benefit analysis for sustainability recommendations
    3. Avoid greenwashing - be honest about trade-offs
    4. Focus on high-impact improvements, not micro-optimizations
    5. Consider total lifecycle impact (not just runtime)
    """
    
    # Load sustainability guidelines
    bias_config = load_yaml_config('config/guardrails/bias_prevention.yaml')
    sustainability_rules = bias_config['bias_prevention']['domain_specific']['sustainability']
    
    context = "\nSustainability Guidelines:\n" + "\n".join(f"- {rule}" for rule in sustainability_rules)
    
    llm_request.config.system_instruction += carbon_guidance + context
    return None
```

**after_agent_callback:**
```python
def carbon_agent_after_agent(callback_context, content):
    """
    Quality Gates:
    - Validate carbon estimates have basis
    - Check for greenwashing language
    - Ensure trade-offs are presented
    """
    analysis = json.loads(content.parts[0].text)
    
    # Validate computational efficiency claims
    for efficiency_item in analysis.get('computational_efficiency', []):
        # Check for unrealistic claims
        if 'estimated_energy' in efficiency_item:
            energy = efficiency_item['estimated_energy']
            # Require unit and range
            if not re.search(r'\d+\.?\d*\s*(kWh|Wh|J)', energy):
                logger.warning(f"Removed imprecise energy estimate: {energy}")
                efficiency_item['estimated_energy'] = 'Not quantifiable with current data'
    
    # Check for greenwashing language
    greenwash_terms = ['dramatically reduce', 'eliminate carbon', 'zero impact', 'perfectly green']
    for recommendation in analysis.get('recommendations', []):
        desc = recommendation.get('description', '')
        for term in greenwash_terms:
            if term in desc.lower():
                logger.warning(f"Removed greenwashing language: {term}")
                recommendation['description'] = remove_greenwashing(desc)
    
    filtered_text = json.dumps(analysis, indent=2)
    return types.Content(parts=[types.Part(text=filtered_text)], role="model")
```

---

### 2.5 Report Synthesizer Agent

#### Primary Concerns
1. **Hallucinated Findings** - Creating findings not from analysis artifacts
2. **Inconsistent Summaries** - Executive summary doesn't match details
3. **Loss of Context** - Missing critical information during synthesis

#### Callback Implementation

**before_agent_callback:**
```python
def report_synthesizer_before_agent(callback_context):
    """
    Validation:
    - Verify all analysis artifacts are loaded
    - Check artifact integrity
    """
    required_artifacts = [
        'security_analysis',
        'code_quality_analysis',
        'engineering_practices_analysis',
        'carbon_emission_analysis'
    ]
    
    missing = []
    for artifact in required_artifacts:
        if artifact not in callback_context.state:
            missing.append(artifact)
    
    if missing:
        logger.error(f"Missing artifacts for report synthesis: {missing}")
        # Return early response
        return types.Content(
            parts=[types.Part(text=f"Cannot generate report: Missing {', '.join(missing)}")],
            role="model"
        )
    
    return None  # Proceed
```

**after_agent_callback:**
```python
def report_synthesizer_after_agent(callback_context, content):
    """
    Quality Gates:
    - Validate report structure
    - Cross-check findings against source artifacts
    - Ensure executive summary accuracy
    """
    report_text = content.parts[0].text
    
    # Extract findings from report
    report_findings = extract_findings_from_report(report_text)
    
    # Load source artifacts
    source_findings = {
        'security': callback_context.state.get('security_analysis'),
        'quality': callback_context.state.get('code_quality_analysis'),
        'engineering': callback_context.state.get('engineering_practices_analysis'),
        'carbon': callback_context.state.get('carbon_emission_analysis')
    }
    
    # Validate no hallucinated findings
    for finding in report_findings:
        if not finding_exists_in_source(finding, source_findings):
            logger.error(f"HALLUCINATED FINDING DETECTED: {finding}")
            # Remove from report
            report_text = remove_finding_from_report(report_text, finding)
    
    return types.Content(parts=[types.Part(text=report_text)], role="model")
```

---

## 3. Shared Callback Infrastructure

### 3.1 Common Callback Functions

Create shared utility callbacks in `util/callbacks.py`:

```python
# util/callbacks.py

import re
import json
import logging
from typing import Optional, Dict, Any
from google.adk.agents import CallbackContext
from google.genai import types
import yaml

logger = logging.getLogger(__name__)

# ============================================================================
# CONTENT MODERATION
# ============================================================================

PROFANITY_BLOCKLIST = [
    'damn', 'crap', 'stupid', 'idiot', 'dumb'  # Extend as needed
]

def filter_profanity(text: str) -> str:
    """Remove profanity from text."""
    for word in PROFANITY_BLOCKLIST:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        text = pattern.sub('[FILTERED]', text)
    return text

def filter_bias(text: str, bias_config: Dict) -> str:
    """Remove biased language based on config."""
    # Load language bias patterns from config
    biased_phrases = bias_config.get('biased_phrases', [])
    
    for phrase in biased_phrases:
        if phrase.lower() in text.lower():
            # Replace with neutral alternative
            neutral = bias_config.get('neutral_alternatives', {}).get(phrase, '[REPHRASED]')
            text = text.replace(phrase, neutral)
    
    return text

# ============================================================================
# EVIDENCE VALIDATION
# ============================================================================

def validate_finding_has_evidence(finding: Dict) -> bool:
    """Check if finding has required evidence fields."""
    required_fields = ['description', 'location']  # Adjust per domain
    
    for field in required_fields:
        if field not in finding or not finding[field]:
            logger.warning(f"Finding missing required field: {field}")
            return False
    
    # Check for specific evidence markers
    if 'line_number' not in finding and 'function_name' not in finding:
        logger.warning("Finding lacks location specificity")
        return False
    
    return True

def validate_metric_claim(claim: Dict) -> bool:
    """Validate that metric-based claims have actual metrics."""
    metric_fields = ['value', 'unit', 'threshold']
    
    has_metric = any(field in claim for field in metric_fields)
    if not has_metric:
        logger.warning(f"Claim lacks metric evidence: {claim}")
        return False
    
    return True

# ============================================================================
# FALSE POSITIVE DETECTION
# ============================================================================

def is_false_positive(finding: Dict, context: CallbackContext) -> bool:
    """Check against known false positive patterns."""
    # Load false positive patterns from config
    fp_config = load_yaml_config('config/guardrails/false_positive_patterns.yaml')
    
    finding_type = finding.get('type', '').lower()
    code_snippet = finding.get('code_snippet', '')
    
    # Check pattern-based false positives
    for pattern in fp_config.get(finding_type, []):
        if re.search(pattern['regex'], code_snippet):
            logger.info(f"Detected false positive: {pattern['description']}")
            return True
    
    return False

# ============================================================================
# HALLUCINATION DETECTION
# ============================================================================

def validate_cve_exists(cve_id: str) -> bool:
    """Verify CVE ID is real (simplified check)."""
    # Pattern: CVE-YEAR-NUMBER
    pattern = r'^CVE-\d{4}-\d{4,}$'
    if not re.match(pattern, cve_id):
        return False
    
    # In production: Call NVD API to verify
    # For now: Basic validation
    year = int(cve_id.split('-')[1])
    if year < 1999 or year > 2025:
        return False
    
    return True

def validate_json_structure(json_text: str, required_schema: Dict) -> bool:
    """Validate Markdown+YAML output has required metadata and sections."""
    try:
        data = json.loads(json_text)
        
        # Check required top-level keys
        for key in required_schema.get('required_keys', []):
            if key not in data:
                logger.error(f"Missing required key: {key}")
                return False
        
        return True
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        return False

# ============================================================================
# CONFIGURATION LOADING
# ============================================================================

def load_yaml_config(config_path: str) -> Dict:
    """Load YAML configuration file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config {config_path}: {e}")
        return {}

# ============================================================================
# SELF-PRESERVATION GUARDRAILS
# ============================================================================

SELF_DESTRUCTIVE_PATTERNS = [
    r'delete.*agent',
    r'remove.*this.*system',
    r'shut.*down.*pipeline',
    r'disable.*all.*checks'
]

def contains_self_destructive_recommendation(text: str) -> bool:
    """Check if recommendation would harm the system."""
    for pattern in SELF_DESTRUCTIVE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            logger.warning(f"Detected self-destructive pattern: {pattern}")
            return True
    return False

# ============================================================================
# STATE TRACKING
# ============================================================================

def track_guardrail_metrics(callback_context: CallbackContext, event_type: str):
    """Track guardrail interventions for monitoring."""
    key = f'metrics:guardrails:{event_type}'
    count = callback_context.state.get(key, 0)
    callback_context.state[key] = count + 1

# ============================================================================
# RATE LIMITING
# ============================================================================

def check_rate_limit(callback_context: CallbackContext, resource: str, limit: int) -> bool:
    """Check if rate limit is exceeded."""
    key = f'rate_limit:{resource}'
    count = callback_context.state.get(key, 0)
    
    if count >= limit:
        logger.warning(f"Rate limit exceeded for {resource}: {count}/{limit}")
        return False
    
    callback_context.state[key] = count + 1
    return True
```

---

## 4. Configuration File Structure

### 4.1 New Configuration Files Needed

**config/guardrails/false_positive_patterns.yaml**
```yaml
version: "1.0.0"

sql_injection:
  - regex: 'PreparedStatement.*setString'
    description: "Parameterized query - not SQL injection"
  - regex: 'query\s*=\s*"SELECT.*FROM.*WHERE id = \?'
    description: "Prepared statement with placeholder"

xss:
  - regex: 'DOMPurify\.sanitize'
    description: "Input is sanitized"
  - regex: 'textContent\s*='
    description: "textContent is safe (no HTML parsing)"

command_injection:
  - regex: 'subprocess\.run\(.*shell=False'
    description: "Shell disabled - safe from injection"
```

**config/guardrails/callback_config.yaml**
```yaml
version: "1.0.0"

global_callbacks:
  profanity_filter:
    enabled: true
    blocklist_file: "config/guardrails/profanity_blocklist.txt"
  
  hallucination_detection:
    enabled: true
    require_evidence: true
    validate_external_references: true
  
  rate_limiting:
    enabled: true
    llm_calls_per_session: 100
    tool_calls_per_agent: 50

agent_specific_callbacks:
  security_agent:
    before_model:
      - inject_security_guidance
      - load_cwe_reference
    after_tool:
      - validate_vulnerability_evidence
      - filter_false_positives
    after_agent:
      - validate_cve_ids
      - check_severity_ratings
  
  code_quality_agent:
    before_model:
      - inject_objectivity_guidance
      - load_quality_thresholds
    after_tool:
      - validate_metric_ranges
    after_agent:
      - remove_subjective_language
      - validate_metric_based_findings
  
  engineering_practices_agent:
    before_model:
      - inject_pragmatic_guidance
      - load_context_rules
    after_agent:
      - soften_dogmatic_recommendations
      - validate_trade_off_analysis
  
  carbon_emission_agent:
    before_model:
      - inject_sustainability_guidance
    after_agent:
      - validate_energy_estimates
      - remove_greenwashing_language
  
  report_synthesizer_agent:
    before_agent:
      - validate_artifact_presence
    after_agent:
      - cross_check_findings
      - validate_summary_consistency
```

---

## 5. Implementation Plan

### Phase 1: Infrastructure Setup (Week 1)
1. ✅ Create `util/callbacks.py` with shared utilities
2. ✅ Create new guardrail configuration files
3. ✅ Add callback registration system in agent base class
4. ✅ Set up metrics tracking for guardrail interventions

### Phase 2: Security Agent (Week 2)
1. ✅ Implement before_model_callback for security guidance
2. ✅ Implement after_tool_callback for vulnerability validation
3. ✅ Implement after_agent_callback for CVE validation
4. ✅ Test with known false positive cases
5. ✅ Integrate with existing security_analysis.yaml config

### Phase 3: Code Quality Agent (Week 2)
1. ✅ Implement before_model_callback for objectivity enforcement
2. ✅ Implement after_tool_callback for metric validation
3. ✅ Implement after_agent_callback for bias removal
4. ✅ Test with subjective vs objective findings
5. ✅ Integrate with quality_gates.yaml and bias_prevention.yaml

### Phase 4: Engineering & Carbon Agents (Week 3)
1. ✅ Implement callbacks for engineering practices agent
2. ✅ Implement callbacks for carbon emission agent
3. ✅ Test architectural dogma detection
4. ✅ Test greenwashing detection
5. ✅ Integrate with bias_prevention.yaml

### Phase 5: Report Synthesizer (Week 3)
1. ✅ Implement before_agent_callback for artifact validation
2. ✅ Implement after_agent_callback for hallucination detection
3. ✅ Test report accuracy against source artifacts
4. ✅ Integrate with hallucination_prevention.yaml

### Phase 6: Testing & Validation (Week 4)
1. ✅ End-to-end testing with real PRs
2. ✅ Measure guardrail intervention rates
3. ✅ Tune thresholds and patterns
4. ✅ Performance impact assessment
5. ✅ Documentation and Bruno test collection updates

---

## 6. Testing Strategy

### 6.1 Test Cases by Concern

**Hallucination Prevention:**
- Test Case: Agent invents CVE ID → Callback removes it
- Test Case: Agent creates finding not in artifacts → Callback filters it
- Test Case: Agent claims metric without evidence → Callback requires evidence

**Profanity/Bias:**
- Test Case: "This code is garbage" → "This code has high complexity"
- Test Case: "Must use microservices" → "Consider microservices based on context"
- Test Case: Subjective criticism → Objective metric-based feedback

**False Positives:**
- Test Case: Parameterized SQL → Not flagged as SQL injection
- Test Case: DOMPurify usage → Not flagged as XSS
- Test Case: shell=False subprocess → Not flagged as command injection

**Self-Preservation:**
- Test Case: "Delete all analysis agents" → Blocked
- Test Case: "Disable security checks" → Blocked
- Test Case: "Remove this system" → Blocked

### 6.2 Metrics to Track

```python
# Guardrail Metrics
metrics = {
    'profanity_filtered': 0,
    'biased_language_removed': 0,
    'hallucinated_findings_blocked': 0,
    'false_positives_prevented': 0,
    'self_destructive_recommendations_blocked': 0,
    'cve_ids_validated': 0,
    'metric_claims_validated': 0,
    'dogmatic_language_softened': 0,
    'greenwashing_removed': 0
}
```

---

## 7. Configuration Management

### 7.1 Loading Strategy

```python
class GuardrailConfigManager:
    """Centralized configuration management for guardrails."""
    
    def __init__(self, config_dir: str = "config/guardrails"):
        self.config_dir = Path(config_dir)
        self._configs = {}
    
    def load_config(self, config_name: str) -> Dict:
        """Load and cache configuration."""
        if config_name not in self._configs:
            config_path = self.config_dir / f"{config_name}.yaml"
            with open(config_path) as f:
                self._configs[config_name] = yaml.safe_load(f)
        return self._configs[config_name]
    
    def get_agent_callbacks(self, agent_name: str) -> Dict:
        """Get callback configuration for specific agent."""
        callback_config = self.load_config('callback_config')
        return callback_config['agent_specific_callbacks'].get(agent_name, {})
    
    def get_false_positive_patterns(self, finding_type: str) -> List:
        """Get false positive patterns for finding type."""
        fp_config = self.load_config('false_positive_patterns')
        return fp_config.get(finding_type, [])
```

---

## 8. Success Criteria

### 8.1 Quantitative Metrics
- ✅ 0 hallucinated findings in production (detected by cross-validation)
- ✅ <5% false positive rate in security findings
- ✅ 100% of findings have evidence (line numbers/metrics)
- ✅ 0 profanity/bias instances in final reports
- ✅ <100ms average callback overhead per agent

### 8.2 Qualitative Goals
- ✅ All findings are actionable and specific
- ✅ Recommendations are pragmatic and context-aware
- ✅ No architectural dogma in engineering feedback
- ✅ Carbon recommendations include cost-benefit analysis
- ✅ Report summaries accurately reflect source data

---

## 9. Risk Mitigation

### 9.1 Performance Impact
- **Risk**: Callbacks add latency to agent execution
- **Mitigation**: Keep callbacks lightweight (<50ms each), parallelize where possible
- **Monitoring**: Track callback execution time per agent

### 9.2 Over-Filtering
- **Risk**: Guardrails remove valid content
- **Mitigation**: Log all filtered content, review logs weekly
- **Fallback**: Manual override mechanism for false positives

### 9.3 Configuration Drift
- **Risk**: Config files get out of sync with code
- **Mitigation**: Version config files, validate on startup
- **Testing**: Integration tests verify config loading

---

## 10. Quality Loop Evaluation System (LLM-as-a-Judge)

### 10.1 Overview

The **Quality Loop Evaluation System** implements an iterative refinement pattern using ADK's `LoopAgent` to ensure all code review reports meet production quality standards. This system acts as an **LLM-as-a-Judge**, automatically critiquing and refining agent outputs before they reach users.

**Key Concept:** While callbacks provide **inline guardrails** during agent execution, the Quality Loop provides **post-execution validation** with iterative refinement capability.

### 10.2 Architecture Integration

```
┌──────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                             │
│  - Coordinates 4 analysis agents                                  │
│  - Collects analysis outputs                                      │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│                    REPORT SYNTHESIZER                             │
│  - Aggregates findings from 4 agents                              │
│  - Generates initial draft report                                 │
│  - Callbacks: hallucination detection, artifact validation        │
└──────────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│            🔁 QUALITY LOOP EVALUATION SYSTEM 🔁                   │
│                                                                    │
│  ┌────────────────────┐         ┌───────────────────────┐        │
│  │   CRITIC AGENT     │────────▶│   REFINER AGENT       │        │
│  │  Evaluates report  │         │  Improves OR signals  │        │
│  │  quality against   │         │  completion via       │        │
│  │  criteria          │         │  exit_loop()          │        │
│  └────────────────────┘         └───────────────────────┘        │
│           ↓                               ↓                       │
│      Iteration 1-5                   Overwrites report            │
│  (Max 5, exits early                                              │
│   when quality met)                                               │
│                                                                    │
│  Exit Conditions:                                                 │
│  ✅ All findings have evidence                                     │
│  ✅ No hallucinated claims                                         │
│  ✅ Objective language used                                        │
│  ✅ No false positives detected                                    │
│  ✅ All sections complete                                          │
└──────────────────────────────────────────────────────────────────┘
                            ↓
                   Final Validated Report
```

### 10.3 Holistic View: Callbacks + Quality Loop

**Two-Tier Quality Assurance Strategy:**

```
TIER 1: INLINE GUARDRAILS (Callbacks)          TIER 2: ITERATIVE REFINEMENT (Loop)
═══════════════════════════════════════        ════════════════════════════════════

During Agent Execution:                         After Report Generation:
┌─────────────────────────────┐                ┌──────────────────────────────┐
│ before_model_callback       │                │ Critic Agent                 │
│ - Inject guidance           │                │ - Holistic evaluation        │
│ - Add constraints           │                │ - Multi-criteria assessment  │
└─────────────────────────────┘                │ - Pattern detection          │
           ↓                                    └──────────────────────────────┘
┌─────────────────────────────┐                           ↓
│ after_tool_callback         │                ┌──────────────────────────────┐
│ - Validate tool output      │                │ Refiner Agent                │
│ - Filter false positives    │                │ - Remove unsupported claims  │
└─────────────────────────────┘                │ - Add missing evidence       │
           ↓                                    │ - Objectify language         │
┌─────────────────────────────┐                │ - Validate against patterns  │
│ after_agent_callback        │                └──────────────────────────────┘
│ - Remove hallucinations     │                           ↓
│ - Filter profanity/bias     │                    Repeat 1-5 times
│ - Validate output           │                    until quality met
└─────────────────────────────┘

BENEFITS:                                       BENEFITS:
✅ Real-time prevention                         ✅ Comprehensive validation
✅ Fast (per-operation)                         ✅ Iterative improvement
✅ Agent-specific                               ✅ Context-aware refinement
✅ Prevents bad data propagation                ✅ Cross-finding validation

LIMITATIONS:                                    LIMITATIONS:
❌ Can't see full report context                ❌ Adds latency (15-60s)
❌ No cross-agent validation                    ❌ Additional LLM costs
❌ Limited iterative refinement                 ❌ Requires termination logic
```

**Complementary, Not Redundant:**
- **Callbacks** = Prevention (stop bad data from entering report)
- **Quality Loop** = Validation (ensure final report meets standards)

### 10.4 Quality Loop Implementation

#### 10.4.1 Critic Agent

**Purpose:** Evaluate report quality against comprehensive criteria

```python
critic_agent = Agent(
    name="ReportQualityCritic",
    model="gemini-2.0-flash",
    description="Evaluates code review report quality using LLM-as-a-Judge pattern",
    instruction="""
You are an expert code review quality auditor. Evaluate the report below against 
these CRITICAL QUALITY CRITERIA:

**Report to Evaluate:**
{final_report}

**Source Artifacts for Cross-Validation:**
- Security Analysis: {security_analysis}
- Code Quality Analysis: {quality_analysis}
- Engineering Practices: {engineering_analysis}
- Carbon Emissions: {carbon_analysis}

---

**EVALUATION CRITERIA:**

1. **Evidence Requirement** (CRITICAL)
   - ALL findings MUST have: line numbers, code snippets, or metrics
   - Security vulnerabilities MUST have: file path, line number, code context
   - Quality issues MUST have: metric values (complexity score, maintainability index)
   - REJECT any claim without concrete evidence

2. **Hallucination Detection**
   - Verify all CVE IDs exist (no invented CVEs)
   - Verify all file paths match source artifacts
   - Verify all metrics match source analysis
   - Verify no findings appear in report that don't exist in source artifacts

3. **Objectivity & Bias**
   - NO subjective language: "terrible", "awful", "perfect", "obviously"
   - NO emotional criticism: "garbage code", "lazy implementation"
   - ONLY objective, measurable language: "complexity score 47 exceeds threshold 15"
   - Check against bias_prevention.yaml patterns

4. **False Positive Prevention**
   - Check security findings against false_positive_patterns.yaml
   - Verify parameterized queries not flagged as SQL injection
   - Verify HTML encoding not flagged as XSS vulnerability
   - Verify prepared statements recognized as secure

5. **Completeness**
   - All 4 sections present: Security, Quality, Engineering, Carbon
   - Each section has: summary, findings, recommendations
   - No empty sections (or explain why empty)
   - Recommendations are actionable

6. **Cross-Validation**
   - Report findings match source artifact findings (no additions/omissions)
   - Severity levels consistent with source analysis
   - Metrics accurately transferred from source artifacts

---

**YOUR TASK:**

IF all criteria are met (report is production-ready):
  Output EXACTLY: "APPROVED - Report meets all quality criteria."

ELSE (report needs improvement):
  Provide 2-4 SPECIFIC, ACTIONABLE improvements with examples:
  - "Finding at line 42: Missing evidence. Add code snippet showing vulnerability."
  - "CVE-2023-XXXX: This CVE does not exist. Verify or remove."
  - "Language violation: Replace 'terrible code' with 'complexity score 52 (high)'."
  - "False positive: Parameterized query at line 78 incorrectly flagged as SQL injection."

Output ONLY the approval phrase OR the specific feedback list.
""",
    output_key="quality_critique"
)
```

#### 10.4.2 Refiner Agent

**Purpose:** Apply improvements or signal completion

```python
def exit_quality_loop(tool_context: ToolContext):
    """
    Signal that report quality is acceptable.
    Called by refiner when critic approves.
    """
    print(f"  [Quality Loop Exit] Report approved after {tool_context.state.get('loop_iteration', 0)} iterations")
    tool_context.actions.end_of_agent = True
    return {"text": "Quality loop exited. Report approved."}

refiner_agent = Agent(
    name="ReportQualityRefiner",
    model="gemini-2.0-flash",
    tools=[exit_quality_loop],
    description="Improves report based on critic feedback or signals approval",
    instruction="""
You are an expert editor for code review reports. Read the critique and take action.

**Current Report:**
{final_report}

**Quality Critique:**
{quality_critique}

**Source Artifacts (for reference):**
- Security: {security_analysis}
- Quality: {quality_analysis}
- Engineering: {engineering_analysis}
- Carbon: {carbon_analysis}

---

**YOUR TASK:**

IF critique says "APPROVED - Report meets all quality criteria.":
  Call the 'exit_quality_loop' function immediately.
  Do NOT output any text. ONLY call the function.

ELSE (critique contains improvement suggestions):
  Apply ALL suggested improvements to create a corrected report:
  
  1. **Add Missing Evidence:**
     - Add line numbers where missing
     - Add code snippets for vulnerabilities
     - Add metric values for quality issues
  
  2. **Remove Hallucinations:**
     - Remove non-existent CVEs
     - Remove findings not in source artifacts
     - Correct mismatched file paths/metrics
  
  3. **Objectify Language:**
     - Replace subjective terms with objective metrics
     - Remove emotional language
     - Use bias_prevention.yaml approved phrasing
  
  4. **Filter False Positives:**
     - Remove findings matching false_positive_patterns.yaml
     - Verify security findings are genuine vulnerabilities
  
  5. **Complete Missing Sections:**
     - Add missing summaries/recommendations
     - Ensure all 4 sections present
  
  Output ONLY the improved report (markdown format).
  Do NOT call any functions when improving the report.
  Do NOT add meta-commentary - just the corrected report.

CRITICAL: You must EITHER call exit_quality_loop OR output improved report.
Never do both in the same response.
""",
    output_key="final_report"  # Overwrites report each iteration
)
```

#### 10.4.3 Loop Configuration

```python
from google.adk.agents import LoopAgent, SequentialAgent

# Quality refinement loop
quality_loop = LoopAgent(
    name="QualityRefinementLoop",
    sub_agents=[
        critic_agent,   # Step 1: Evaluate
        refiner_agent   # Step 2: Improve OR exit
    ],
    max_iterations=5  # Safety limit
)

# Complete orchestrator with quality loop
orchestrator_with_quality = SequentialAgent(
    name="CodeReviewOrchestratorWithQuality",
    sub_agents=[
        github_data_adapter_agent,      # Phase 1: Fetch code
        parallel_analysis_agents,        # Phase 2: Analyze (4 agents)
        artifact_saver_agent,           # Phase 3: Save artifacts
        report_synthesizer_agent,       # Phase 4: Generate draft report
        quality_loop,                   # Phase 5: Validate & refine ✨
        report_saver_agent              # Phase 6: Save final report
    ],
    description="End-to-end code review with quality assurance"
)
```

### 10.5 Integration with Callbacks

**Layered Quality Assurance Strategy:**

| Stage | Quality Mechanism | Purpose | When It Runs |
|-------|------------------|---------|--------------|
| **1. Individual Agents** | Callbacks (before_model, after_tool, after_agent) | Prevent bad data from entering analysis | During each agent execution |
| **2. Report Synthesizer** | Callbacks (before_agent, after_agent) | Validate artifact aggregation | During report generation |
| **3. Quality Loop** | Critic-Refiner Pattern | Holistic validation & refinement | After initial report complete |
| **4. Final Output** | Report Saver | Persistence verification | After quality approval |

**Example Flow:**

```
Security Agent analyzes code
  → after_tool_callback: Filters false positive SQL injection finding
  → after_agent_callback: Validates CVE-2023-12345 exists
  → Output: {vulnerabilities: [{cve: "CVE-2023-12345", evidence: "..."}]}

[... other agents run with callbacks ...]

Report Synthesizer aggregates
  → before_agent_callback: Validates all 4 artifacts present
  → Generates draft report
  → after_agent_callback: Removes hallucinated finding not in artifacts
  → Output: Draft report (markdown)

Quality Loop iterates:
  Iteration 1:
    → Critic: "Missing line numbers for 2 vulnerabilities, subjective language in quality section"
    → Refiner: Adds line numbers, replaces "terrible complexity" with "complexity score 52"
  
  Iteration 2:
    → Critic: "APPROVED - Report meets all quality criteria."
    → Refiner: Calls exit_quality_loop() ✅

Report Saver persists final validated report
```

### 10.6 Configuration Files

#### config/guardrails/quality_loop_config.yaml

```yaml
quality_loop:
  enabled: true
  max_iterations: 5
  early_exit: true
  
  # Timeout per iteration (prevent slow LLM responses from blocking)
  iteration_timeout_seconds: 45
  
  # Model configuration
  critic_model: "gemini-2.0-flash"
  refiner_model: "gemini-2.0-flash"
  
  # Evaluation criteria weights (for scoring)
  criteria:
    evidence_requirement:
      weight: 0.30
      threshold: 1.0  # Must be perfect
    hallucination_detection:
      weight: 0.25
      threshold: 1.0  # Must be perfect
    objectivity:
      weight: 0.20
      threshold: 0.90
    false_positive_prevention:
      weight: 0.15
      threshold: 0.95
    completeness:
      weight: 0.10
      threshold: 0.90
  
  # Termination conditions
  termination:
    # Exit early if score above threshold
    quality_score_threshold: 0.95
    
    # Exit if no improvements made in iteration
    no_change_exit: true
    
    # Always exit after max_iterations
    enforce_max_iterations: true

# Reference existing configs
referenced_configs:
  - hallucination_prevention.yaml
  - quality_gates.yaml
  - bias_prevention.yaml
  - false_positive_patterns.yaml
```

### 10.7 Metrics & Observability

**Quality Loop Metrics to Track:**

```python
# In util/metrics.py

QUALITY_LOOP_ITERATIONS = Counter(
    "quality_loop_iterations_total",
    "Total quality loop iterations executed",
    ["exit_reason"]  # approved, max_iterations, timeout, error
)

QUALITY_LOOP_DURATION = Histogram(
    "quality_loop_duration_seconds",
    "Time spent in quality loop refinement",
    buckets=[5, 10, 20, 30, 45, 60]
)

QUALITY_IMPROVEMENTS = Counter(
    "quality_improvements_total",
    "Improvements made by refiner agent",
    ["improvement_type"]  # evidence_added, hallucination_removed, language_fixed, false_positive_filtered
)

QUALITY_APPROVAL_RATE = Gauge(
    "quality_approval_rate",
    "Percentage of reports approved on first iteration"
)

QUALITY_SCORE = Histogram(
    "quality_score",
    "Quality score before/after loop",
    ["stage"],  # initial, final
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]
)
```

**Logging:**

```python
# In quality loop execution

logger.info(
    "quality_loop_started",
    session_id=session_id,
    report_length=len(final_report),
    source_artifacts_count=4
)

logger.info(
    "quality_loop_iteration",
    session_id=session_id,
    iteration=iteration_num,
    critique_length=len(critique),
    improvements_count=len(parse_improvements(critique))
)

logger.info(
    "quality_loop_completed",
    session_id=session_id,
    total_iterations=iteration_num,
    exit_reason="approved",  # or max_iterations, timeout, error
    duration_seconds=duration,
    improvements_applied=improvements_count
)
```

### 10.8 Testing Strategy

#### Unit Tests

```python
# tests/unit/test_quality_loop.py

def test_critic_approves_high_quality_report():
    """Critic should approve report with all evidence and objectivity"""
    report = generate_perfect_report()
    critique = critic_agent.run(report)
    assert "APPROVED" in critique

def test_critic_detects_missing_evidence():
    """Critic should flag findings without line numbers"""
    report = generate_report_missing_evidence()
    critique = critic_agent.run(report)
    assert "Missing evidence" in critique
    assert "APPROVED" not in critique

def test_refiner_adds_evidence():
    """Refiner should add missing evidence based on source artifacts"""
    initial_report = generate_report_missing_evidence()
    critique = "Finding at line 42: Missing evidence. Add code snippet."
    refined = refiner_agent.run(initial_report, critique, artifacts)
    assert "line 42" in refined
    assert "code snippet" in refined

def test_refiner_exits_on_approval():
    """Refiner should call exit_quality_loop when approved"""
    report = generate_perfect_report()
    critique = "APPROVED - Report meets all quality criteria."
    with patch('tool_context.actions.end_of_agent') as mock_exit:
        refiner_agent.run(report, critique, artifacts)
        assert mock_exit.called

def test_loop_terminates_after_max_iterations():
    """Loop should stop after 5 iterations even without approval"""
    loop = create_quality_loop(max_iterations=5)
    result = loop.run(poor_quality_report)
    assert loop.iteration_count == 5
```

#### Integration Tests

```python
# tests/integration/test_quality_loop_integration.py

def test_quality_loop_improves_report_iteratively():
    """Full loop should improve report quality over iterations"""
    initial_report = generate_mediocre_report()
    loop = create_quality_loop()
    
    final_report = loop.run(initial_report, artifacts)
    
    # Verify improvements
    assert has_all_evidence(final_report)
    assert no_hallucinations(final_report)
    assert is_objective_language(final_report)
    assert loop.iteration_count <= 5

def test_quality_loop_exits_early_on_quality():
    """Loop should exit before max_iterations if quality is good"""
    good_report = generate_good_but_not_perfect_report()
    loop = create_quality_loop(max_iterations=5)
    
    final_report = loop.run(good_report, artifacts)
    
    assert loop.iteration_count < 5  # Exited early
    assert loop.exit_reason == "approved"

def test_callbacks_and_loop_integration():
    """Callbacks and quality loop should work together without conflict"""
    orchestrator = create_orchestrator_with_callbacks_and_loop()
    
    result = orchestrator.run(github_context)
    
    # Verify callbacks executed
    assert callback_metrics["after_agent_callback_count"] > 0
    
    # Verify quality loop executed
    assert quality_loop_metrics["iterations"] > 0
    
    # Verify final report quality
    assert validate_report_quality(result["final_report"]) > 0.95
```

### 10.9 Performance Considerations

**Latency Impact:**

| Iteration Count | Time Added (est.) | When It Happens |
|----------------|-------------------|-----------------|
| 1 iteration | 15-20 seconds | High quality draft (80% of cases) |
| 2-3 iterations | 30-45 seconds | Medium quality draft (15% of cases) |
| 4-5 iterations | 60-75 seconds | Poor quality draft (5% of cases) |

**Cost Impact:**

- **Critic Agent**: ~2,000 tokens per call (input: report + artifacts, output: critique)
- **Refiner Agent**: ~3,000 tokens per call (input: report + critique + artifacts, output: refined report)
- **Total per iteration**: ~5,000 tokens
- **Max cost (5 iterations)**: ~25,000 tokens (~$0.02 at $0.80/1M tokens)

**Optimization Strategies:**

1. **Callback Prevention** - Good callbacks reduce loop iterations
2. **Smart Exit** - Early exit on quality threshold (don't wait for perfection)
3. **Cached Artifacts** - Don't re-send artifacts each iteration (reference only)
4. **Parallel Validation** - Run independent checks concurrently in critic
5. **Incremental Improvement** - Focus refiner on specific issues (not full rewrite)

### 10.10 Decision Points

**Before implementing Quality Loop:**

- [ ] **Latency Tolerance**: Is 15-60s additional latency acceptable?
- [ ] **Cost Tolerance**: Is $0.01-0.02 per review acceptable?
- [ ] **Callback First**: Should we implement callbacks first to see if loop is needed?
- [ ] **Iteration Limit**: Is 5 iterations the right balance? (More = better quality, higher cost)
- [ ] **Model Selection**: Use Gemini Flash (fast/cheap) or Gemini Pro (slower/better)?

**Recommended Approach:**

1. ✅ **Phase 1**: Implement callbacks (inline guardrails)
2. ✅ **Phase 2**: Measure report quality metrics
3. ✅ **Phase 3**: If quality issues persist (>10% reports), implement Quality Loop
4. ✅ **Phase 4**: Tune loop configuration based on production metrics

### 10.11 Success Criteria

**Quality Loop is successful if:**

- ✅ **Quality Improvement**: Final reports score >95% on quality criteria (vs <80% without loop)
- ✅ **Early Exit Rate**: >70% of reports exit within 2 iterations
- ✅ **No False Approvals**: 0% of approved reports contain hallucinations or missing evidence
- ✅ **Performance**: Average latency <30 seconds per review
- ✅ **Cost Efficiency**: Average cost <$0.015 per review
- ✅ **User Satisfaction**: >90% of users rate reports as "actionable and accurate"

---

## 11. Confidence Scoring & Evaluation Architecture

### 11.1 Overview

Building on the two-tier quality strategy (Callbacks + Quality Loop), we introduce a **three-layer quality assurance system** to prevent false positives and ensure report reliability:

**Layer 1: Context Engineering** - Inject agent-specific knowledge base guidelines  
**Layer 2: Confidence Scoring** - Each finding includes confidence score (0.0-1.0)  
**Layer 3: Evaluator Agent** - Post-analysis scoring against guidelines  

This comprehensive approach addresses false positives through:
- **Prevention** (Context Engineering) - Agents understand domain standards from start
- **Transparency** (Confidence Scoring) - Visibility into finding reliability
- **Validation** (Evaluator Agent) - Independent scoring of findings quality

### 11.2 Context Engineering with Knowledge Base

#### 11.2.1 Agent-Specific Knowledge Base Injection

**Problem:** Agents operate without understanding of domain-specific best practices, leading to false positives and misinterpretation of patterns.

**Solution:** Load relevant knowledge base guidelines into agent system prompts before analysis.

**Architecture:**

```python
# util/context_engineering.py

import yaml
from pathlib import Path
from typing import Dict, List

class KnowledgeBaseLoader:
    """Load and inject domain-specific guidelines into agent prompts."""
    
    def __init__(self, kb_dir: str = "config/knowledge_base"):
        self.kb_dir = Path(kb_dir)
        self._cache = {}
    
    def load_guidelines(self, agent_type: str) -> Dict:
        """Load guidelines for specific agent type."""
        if agent_type in self._cache:
            return self._cache[agent_type]
        
        # Map agent types to knowledge base files
        kb_mapping = {
            "security_agent": ["security_guidelines.yaml"],
            "code_quality_agent": ["code_quality_guidelines.yaml"],
            "engineering_practices_agent": ["engineering_practices_guidlines.yaml"],
            "carbon_emission_agent": ["carbon_emission_guidlines.yaml"]
        }
        
        guidelines = {}
        for kb_file in kb_mapping.get(agent_type, []):
            kb_path = self.kb_dir / kb_file
            with open(kb_path) as f:
                data = yaml.safe_load(f)
                guidelines.update(data)
        
        self._cache[agent_type] = guidelines
        return guidelines
    
    def format_guidelines_for_prompt(self, guidelines: Dict) -> str:
        """Format guidelines as readable text for system prompt."""
        sections = []
        
        # Skip metadata keys
        skip_keys = {'version', 'title'}
        
        for key, value in guidelines.items():
            if key in skip_keys:
                continue
            
            # Format section header
            section_title = key.replace('_', ' ').title()
            sections.append(f"\n**{section_title}:**")
            
            # Format guidelines
            if isinstance(value, list):
                for item in value:
                    sections.append(f"  - {item}")
            elif isinstance(value, dict):
                sections.append(self._format_nested_dict(value, indent=2))
        
        return "\n".join(sections)
    
    def _format_nested_dict(self, data: Dict, indent: int = 0) -> str:
        """Recursively format nested dictionary."""
        lines = []
        prefix = "  " * indent
        
        for key, value in data.items():
            formatted_key = key.replace('_', ' ').title()
            if isinstance(value, list):
                lines.append(f"{prefix}- {formatted_key}:")
                for item in value:
                    lines.append(f"{prefix}  * {item}")
            elif isinstance(value, dict):
                lines.append(f"{prefix}- {formatted_key}:")
                lines.append(self._format_nested_dict(value, indent + 1))
            else:
                lines.append(f"{prefix}- {formatted_key}: {value}")
        
        return "\n".join(lines)

# Usage in agent initialization
kb_loader = KnowledgeBaseLoader()

def inject_knowledge_base_context(agent_type: str, base_instruction: str) -> str:
    """Inject knowledge base guidelines into agent instruction."""
    guidelines = kb_loader.load_guidelines(agent_type)
    formatted_kb = kb_loader.format_guidelines_for_prompt(guidelines)
    
    enhanced_instruction = f"""{base_instruction}

---

## DOMAIN KNOWLEDGE BASE

You MUST follow these industry-standard guidelines when analyzing code:

{formatted_kb}

---

**CRITICAL:** Use these guidelines to:
1. **Identify issues** - Check code against these standards
2. **Avoid false positives** - Recognize secure/compliant patterns
3. **Provide context** - Reference specific guidelines in findings
4. **Assign confidence** - Higher confidence when guideline is clearly violated

"""
    
    return enhanced_instruction
```

#### 11.2.2 Integration with Existing Agents

**Security Agent Example:**

```python
# Before (agent_workspace/orchestrator_agent/sub_agents/security_agent/agent.py)
security_agent = Agent(
    name="security_agent",
    instruction="You are a Security Analysis Agent...",
    # ... rest of agent config
)

# After (with context engineering)
from util.context_engineering import inject_knowledge_base_context

base_instruction = """You are a Security Analysis Agent in a sequential code review pipeline.
Your job: Scan code for security vulnerabilities using OWASP Top 10 as guidance.
"""

enhanced_instruction = inject_knowledge_base_context("security_agent", base_instruction)

security_agent = Agent(
    name="security_agent",
    instruction=enhanced_instruction,
    # ... rest of agent config
)
```

**Result:** Agent now understands:
- OWASP Top 10 2021 categories with CWE mappings
- Secure coding patterns (parameterized queries, DOMPurify, shell=False)
- Security testing requirements (SAST, dependency scanning, secret scanning)
- Web security best practices (CORS, CSRF, clickjacking prevention)
- Rate limiting standards

### 11.3 Confidence Scoring System

#### 11.3.1 Confidence Score Definition

Each finding MUST include a `confidence_score` field (0.0-1.0) indicating reliability:

| Score Range | Interpretation | Usage |
|-------------|----------------|-------|
| 0.90 - 1.00 | **High Confidence** | Clear guideline violation, strong evidence |
| 0.70 - 0.89 | **Medium Confidence** | Likely issue, but context-dependent |
| 0.50 - 0.69 | **Low Confidence** | Potential issue, needs human review |
| 0.00 - 0.49 | **Very Low** | Uncertain, may be false positive |

**Confidence Factors:**
- ✅ **Evidence strength** - Line numbers, metrics, code snippets
- ✅ **Guideline alignment** - Direct match with knowledge base rule
- ✅ **Pattern clarity** - Unambiguous anti-pattern vs. context-dependent
- ✅ **Tool validation** - Static analyzer confirms finding
- ✅ **Historical accuracy** - Similar findings validated in past

#### 11.3.2 Updated Output Schema

**Before (no confidence):**
```json
{
  "vulnerabilities": [
    {
      "type": "SQL Injection",
      "location": "getUserById",
      "line": 83,
      "description": "Unsanitized user input used in SQL query",
      "recommendation": "Use parameterized queries"
    }
  ]
}
```

**After (with confidence):**
```json
{
  "vulnerabilities": [
    {
      "type": "SQL Injection",
      "location": "getUserById",
      "line": 83,
      "description": "Unsanitized user input used in SQL query",
      "recommendation": "Use parameterized queries",
      "confidence_score": 0.85,
      "confidence_reasoning": "Direct string concatenation detected, no evidence of parameterization, matches OWASP A03 (Injection) guideline"
    }
  ]
}
```

#### 11.3.3 Agent Instruction Update

Add to all analysis agents:

```python
instruction="""
# ... existing instruction ...

**CONFIDENCE SCORING (REQUIRED):**

For EVERY finding, you MUST include:
- `confidence_score` (float 0.0-1.0)
- `confidence_reasoning` (string explaining score)

**Confidence Calculation Guidelines:**

HIGH (0.90-1.00):
- Clear violation of knowledge base guideline
- Strong evidence (line number + code snippet + metric)
- Static analyzer tool confirms issue
- Pattern matches known vulnerability/anti-pattern

MEDIUM (0.70-0.89):
- Likely issue based on guidelines
- Moderate evidence (line number + description)
- Context may affect severity
- Pattern is concerning but not definitive

LOW (0.50-0.69):
- Potential issue requiring review
- Weak evidence (general observation)
- Highly context-dependent
- Pattern could be intentional design choice

VERY LOW (0.00-0.49):
- Uncertain or likely false positive
- Insufficient evidence
- May be secure pattern misidentified
- Needs human expert validation

**Example:**
```json
{
  "type": "High Cyclomatic Complexity",
  "location": "processPayment",
  "line": 142,
  "description": "Function has cyclomatic complexity of 23",
  "recommendation": "Refactor into smaller functions",
  "confidence_score": 0.95,
  "confidence_reasoning": "Exceeds threshold of 15 from code_quality_guidelines.yaml, metric objectively measured by complexity_analyzer_tool"
}
```
"""
```

### 11.4 Evaluator Agent Architecture

#### 11.4.1 Purpose

**Evaluator Agent** runs AFTER all 4 analysis agents complete and artifacts are saved. It:

1. **Loads all analysis artifacts** from disk
2. **Loads knowledge base guidelines** for all domains
3. **Scores each finding** against guidelines using LLM-as-a-Judge
4. **Flags potential false positives** with low evaluation scores
5. **Outputs evaluation report** with per-finding scores

#### 11.4.2 Evaluator Agent Implementation

```python
# agent_workspace/orchestrator_agent/sub_agents/evaluator_agent/agent.py

import sys
import logging
from pathlib import Path
from google.adk.agents import Agent

logger = logging.getLogger(__name__)
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from util.llm_model import get_sub_agent_model
from util.context_engineering import KnowledgeBaseLoader

# Load knowledge base
kb_loader = KnowledgeBaseLoader()

# Combine all guidelines into evaluator context
all_guidelines = {
    "security": kb_loader.load_guidelines("security_agent"),
    "code_quality": kb_loader.load_guidelines("code_quality_agent"),
    "engineering": kb_loader.load_guidelines("engineering_practices_agent"),
    "carbon": kb_loader.load_guidelines("carbon_emission_agent")
}

formatted_guidelines = kb_loader.format_guidelines_for_prompt({
    **all_guidelines["security"],
    **all_guidelines["code_quality"],
    **all_guidelines["engineering"],
    **all_guidelines["carbon"]
})

evaluator_agent = Agent(
    name="evaluator_agent",
    model=get_sub_agent_model(),
    description="Evaluates analysis findings against knowledge base guidelines to detect false positives",
    instruction=f"""You are an Evaluator Agent using LLM-as-a-Judge pattern.

**YOUR ROLE:** Score each finding from analysis agents against industry guidelines.

**INPUT (from session state):**
- security_analysis (artifact)
- code_quality_analysis (artifact)
- engineering_practices_analysis (artifact)
- carbon_emission_analysis (artifact)

**KNOWLEDGE BASE GUIDELINES:**

{formatted_guidelines}

---

**EVALUATION CRITERIA:**

For EACH finding, score 0.0-1.0 on:

1. **Guideline Alignment** (40% weight)
   - Does finding match a specific guideline?
   - Is the guideline clearly violated?
   - 1.0 = Perfect match, 0.0 = No guideline support

2. **Evidence Quality** (30% weight)
   - Does finding have line numbers, code snippets, metrics?
   - Is evidence concrete and verifiable?
   - 1.0 = Strong evidence, 0.0 = No evidence

3. **False Positive Likelihood** (20% weight)
   - Could this be a secure pattern misidentified?
   - Does it match false_positive_patterns.yaml?
   - 1.0 = Definitely valid, 0.0 = Likely false positive

4. **Confidence Alignment** (10% weight)
   - Does agent's confidence_score match your assessment?
   - Is confidence_reasoning sound?
   - 1.0 = Perfect alignment, 0.0 = Misaligned

**WEIGHTED EVALUATION SCORE:**
evaluation_score = (guideline * 0.4) + (evidence * 0.3) + ((1 - false_positive) * 0.2) + (confidence_align * 0.1)

---

**OUTPUT SCHEMA:**

```json
{{
  "evaluator": "EvaluatorAgent",
  "evaluation_summary": "Evaluated X findings across 4 domains. Y findings flagged for review.",
  "findings_evaluated": {{
    "security": [
      {{
        "finding_id": "security_001",
        "finding_type": "SQL Injection",
        "agent_confidence": 0.85,
        "evaluation_score": 0.92,
        "guideline_alignment": 0.95,
        "evidence_quality": 0.90,
        "false_positive_likelihood": 0.10,
        "confidence_alignment": 0.85,
        "verdict": "VALID",
        "reasoning": "Clear OWASP A03 violation, strong evidence with line number and code snippet, low FP risk"
      }},
      {{
        "finding_id": "security_002",
        "finding_type": "Command Injection",
        "agent_confidence": 0.78,
        "evaluation_score": 0.35,
        "guideline_alignment": 0.40,
        "evidence_quality": 0.60,
        "false_positive_likelihood": 0.85,
        "confidence_alignment": 0.20,
        "verdict": "LIKELY_FALSE_POSITIVE",
        "reasoning": "Code uses subprocess.run with shell=False - safe pattern per guidelines. Agent missed secure context."
      }}
    ],
    "code_quality": [ /* ... */ ],
    "engineering": [ /* ... */ ],
    "carbon": [ /* ... */ ]
  }},
  "flagged_for_review": [
    {{
      "finding_id": "security_002",
      "domain": "security",
      "reason": "Low evaluation score (0.35), high false positive likelihood (0.85)"
    }}
  ],
  "statistics": {{
    "total_findings": 47,
    "valid_findings": 42,
    "likely_false_positives": 5,
    "average_evaluation_score": 0.87
  }}
}}
```

**CRITICAL:**
- Evaluate EVERY finding from all 4 agents
- Be strict on evidence quality (no line numbers = lower score)
- Flag findings with evaluation_score < 0.60 for review
- Cross-reference false_positive_patterns.yaml
- Output pure JSON (no markdown, no explanations outside JSON)
""",
    output_key="evaluation_results"
)

logger.info("✅ [evaluator_agent] Evaluator Agent created with knowledge base context")
```

#### 11.4.3 Integration into Orchestrator

**Updated Pipeline Flow:**

```python
# agent_workspace/orchestrator_agent/agent.py

orchestrator = SequentialAgent(
    name="CodeReviewOrchestrator",
    sub_agents=[
        github_data_adapter_agent,      # Step 1: Transform PR data
        parallel_analysis_agents,        # Step 2: 4 analysis agents
        artifact_saver_agent,           # Step 3: Save analysis artifacts
        evaluator_agent,                # Step 4: Evaluate findings ✨ NEW
        report_synthesizer_agent,       # Step 5: Generate report
        quality_loop,                   # Step 6: Refine report (optional)
        report_saver_agent              # Step 7: Save final report
    ]
)
```

**Why After Artifact Saver?**
- Evaluator needs all 4 analysis artifacts loaded
- Evaluation results available for Report Synthesizer to filter/annotate findings
- Report Synthesizer can use evaluation_score to prioritize findings

### 11.5 False Positive Prevention Strategy

**Three-Layer Defense:**

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: CONTEXT ENGINEERING (Prevention)                   │
│ - Knowledge base guidelines injected into agent prompts     │
│ - Agents understand secure patterns BEFORE analysis         │
│ - Reduces false positives at source                         │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 2: CONFIDENCE SCORING (Transparency)                  │
│ - Each finding includes confidence_score (0.0-1.0)          │
│ - Low confidence findings flagged automatically             │
│ - Human reviewers prioritize high-confidence issues         │
└─────────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│ LAYER 3: EVALUATOR AGENT (Validation)                       │
│ - Independent LLM-as-a-Judge scores findings                │
│ - Cross-references knowledge base guidelines                │
│ - Flags evaluation_score < 0.60 as potential FP             │
│ - Provides reasoning for each evaluation                    │
└─────────────────────────────────────────────────────────────┘
                         ↓
              Report Synthesizer
       (Uses evaluation scores to filter/rank)
```

**Effectiveness:**

| Without System | With 3-Layer System |
|----------------|---------------------|
| ~15-25% false positive rate | <5% false positive rate |
| No confidence visibility | Full transparency per finding |
| Manual review required | Automated pre-filtering |
| Inconsistent quality | Guideline-backed validation |

### 11.6 Configuration Files

#### config/evaluation/evaluator_config.yaml

```yaml
version: "1.0.0"

evaluator:
  enabled: true
  
  # Evaluation criteria weights
  criteria_weights:
    guideline_alignment: 0.40
    evidence_quality: 0.30
    false_positive_prevention: 0.20
    confidence_alignment: 0.10
  
  # Thresholds
  thresholds:
    # Findings below this score flagged for review
    flag_for_review: 0.60
    
    # Findings below this score automatically filtered
    auto_filter: 0.40
    
    # Minimum evidence quality to be valid
    min_evidence_quality: 0.50
  
  # Knowledge base references
  knowledge_bases:
    - config/knowledge_base/security_guidelines.yaml
    - config/knowledge_base/code_quality_guidelines.yaml
    - config/knowledge_base/engineering_practices_guidlines.yaml
    - config/knowledge_base/carbon_emission_guidlines.yaml
    - config/guardrails/false_positive_patterns.yaml
  
  # Output configuration
  output:
    include_reasoning: true
    include_statistics: true
    save_evaluation_artifact: true
```

### 11.7 Artifact Logging Enhancement

**Updated Artifact Saver to Log Confidence Scores:**

```python
# Update tools/save_analysis_artifact.py

async def save_analysis_result(
    analysis_data: str,
    agent_name: str,
    tool_context: ToolContext
) -> dict:
    """Save analysis result with confidence score logging."""
    
    # ... existing code ...
    
    # Parse JSON to extract confidence scores
    try:
        data = json.loads(analysis_data)
        
        # Log confidence scores
        findings_with_confidence = []
        for finding_key in ['vulnerabilities', 'issues', 'findings', 'recommendations']:
            for finding in data.get(finding_key, []):
                if 'confidence_score' in finding:
                    findings_with_confidence.append({
                        'type': finding.get('type', 'unknown'),
                        'confidence': finding['confidence_score'],
                        'location': finding.get('location', 'unknown')
                    })
        
        logger.info(
            f"💯 [save_analysis_artifact] Confidence scores logged",
            extra={
                'agent': agent_name,
                'total_findings': len(findings_with_confidence),
                'avg_confidence': sum(f['confidence'] for f in findings_with_confidence) / len(findings_with_confidence) if findings_with_confidence else 0,
                'high_confidence_count': len([f for f in findings_with_confidence if f['confidence'] >= 0.90]),
                'low_confidence_count': len([f for f in findings_with_confidence if f['confidence'] < 0.60])
            }
        )
    except Exception as e:
        logger.warning(f"Could not parse confidence scores: {e}")
    
    # ... rest of save logic ...
```

### 11.8 Report Synthesizer Integration

**Use Evaluation Results to Improve Report Quality:**

```python
# Update report_synthesizer_agent instruction

instruction="""
# ... existing instruction ...

**EVALUATION-AWARE REPORTING:**

Session state contains `evaluation_results` from Evaluator Agent.
Use this to improve report quality:

1. **Filter Low-Confidence Findings:**
   - Exclude findings with evaluation_score < 0.40 (auto-filter threshold)
   - Add warning for findings 0.40-0.60: "⚠️ Requires review"

2. **Prioritize High-Confidence Findings:**
   - Sort findings by evaluation_score (highest first)
   - Highlight findings with score > 0.90 as "High Confidence"

3. **Include Confidence Context:**
   - Show agent_confidence and evaluation_score for transparency
   - If scores differ significantly, explain discrepancy

4. **False Positive Warnings:**
   - For flagged findings, include evaluator's reasoning
   - Give users option to report false positives

**Example Output:**

```markdown
### 🔴 Critical Security Issues (High Confidence)

1. **SQL Injection in getUserById** [Confidence: 95% ✅]
   - Location: `auth/service.py:83`
   - Evaluation Score: 0.92 (Valid finding)
   - ...

### ⚠️ Potential Issues (Requires Review)

2. **Command Injection in runScript** [Confidence: 78% ⚠️]
   - Location: `utils/runner.py:42`
   - Evaluation Score: 0.35 (Likely false positive)
   - Evaluator Note: "Uses subprocess with shell=False - secure pattern"
   - ...
```
"""
```

### 11.9 Metrics & Observability

**New Metrics to Track:**

```python
# util/metrics.py

CONFIDENCE_SCORE_DISTRIBUTION = Histogram(
    "finding_confidence_score",
    "Distribution of confidence scores across findings",
    ["agent", "finding_type"],
    buckets=[0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

EVALUATION_SCORE_DISTRIBUTION = Histogram(
    "evaluation_score",
    "Distribution of evaluator scores across findings",
    ["agent", "verdict"],  # verdict: VALID, LIKELY_FALSE_POSITIVE
    buckets=[0.0, 0.4, 0.6, 0.8, 0.9, 1.0]
)

FALSE_POSITIVE_RATE = Gauge(
    "false_positive_rate",
    "Percentage of findings flagged as likely false positives",
    ["agent"]
)

CONFIDENCE_EVALUATION_ALIGNMENT = Histogram(
    "confidence_evaluation_alignment",
    "Difference between agent confidence and evaluator score",
    buckets=[-1.0, -0.5, -0.2, 0.0, 0.2, 0.5, 1.0]
)

KNOWLEDGE_BASE_COVERAGE = Gauge(
    "knowledge_base_guideline_coverage",
    "Percentage of findings with guideline alignment > 0.8",
    ["agent"]
)
```

### 11.10 Testing Strategy

**Test Scenarios:**

1. **Context Engineering Tests:**
   - Verify knowledge base loads correctly
   - Verify guidelines formatted properly in prompts
   - Verify agent recognizes secure patterns (e.g., parameterized queries)

2. **Confidence Scoring Tests:**
   - Verify all findings include confidence_score
   - Verify confidence aligns with evidence quality
   - Verify low-confidence findings flagged appropriately

3. **Evaluator Agent Tests:**
   - Verify evaluator loads all 4 artifacts
   - Verify evaluation_score calculation correct
   - Verify false positive detection (parameterized SQL, shell=False, etc.)
   - Verify flagged findings list accurate

4. **End-to-End Tests:**
   - Run full pipeline with known false positives
   - Verify false positives filtered by evaluator
   - Verify report synthesizer uses evaluation scores
   - Verify confidence metrics logged correctly

### 11.11 Success Criteria

**System is successful if:**

- ✅ **False Positive Rate:** <5% (down from 15-25% baseline)
- ✅ **Confidence Accuracy:** Agent confidence aligns with evaluator score (±0.15)
- ✅ **Guideline Coverage:** >90% of findings reference specific guideline
- ✅ **Evidence Quality:** >95% of findings include line numbers/metrics
- ✅ **Auto-Filter Accuracy:** <2% of auto-filtered findings are actually valid
- ✅ **User Trust:** >85% of users rate reports as "reliable and accurate"

### 11.12 Implementation Phases

**Phase 1: Context Engineering (Week 1)**
- Create `util/context_engineering.py`
- Update all 4 analysis agents to inject knowledge base
- Test agent recognition of secure patterns
- Measure baseline false positive rate

**Phase 2: Confidence Scoring (Week 1-2)**
- Update agent instructions to require confidence scores
- Update output schemas to include confidence fields
- Update artifact saver to log confidence metrics
- Validate confidence score distribution

**Phase 3: Evaluator Agent (Week 2)**
- Create `evaluator_agent/agent.py`
- Implement evaluation scoring logic
- Integrate into orchestrator after artifact saver
- Test false positive detection accuracy

**Phase 4: Report Integration (Week 3)**
- Update report synthesizer to use evaluation results
- Implement confidence-based filtering/ranking
- Add evaluation transparency to reports
- User testing and feedback collection

**Phase 5: Tuning (Week 3-4)**
- Adjust evaluation thresholds based on data
- Refine knowledge base guidelines
- Optimize confidence score accuracy
- A/B test with/without evaluation system

---

## 12. Next Steps

### Immediate Actions
1. ✅ Review and approve this design document
2. ✅ Create `util/callbacks.py` with shared utilities
3. ✅ Set up new config files in `config/guardrails/`
4. ✅ Implement callback infrastructure in agent base classes
5. ✅ Start with Security Agent callbacks (highest risk)

### Quality Loop Implementation (Phase 3)
6. ✅ Create `config/guardrails/quality_loop_config.yaml`
7. ✅ Implement Critic Agent with comprehensive evaluation criteria
8. ✅ Implement Refiner Agent with improvement logic
9. ✅ Create `exit_quality_loop()` tool for early termination
10. ✅ Integrate LoopAgent into orchestrator after Report Synthesizer
11. ✅ Add quality loop metrics to observability system
12. ✅ Create unit tests for critic/refiner agents
13. ✅ Create integration tests for full loop
14. ✅ Run A/B test: reports with/without quality loop
15. ✅ Tune max_iterations based on production data

### Context Engineering & Evaluation (Phase 4)
16. ✅ Create `util/context_engineering.py` for knowledge base injection
17. ✅ Update all agent instructions to include confidence scoring
18. ✅ Create evaluator_agent with LLM-as-a-Judge pattern
19. ✅ Integrate evaluator into orchestrator pipeline
20. ✅ Update report synthesizer to use evaluation scores

### Decision Points - CLOSED ✅

**ALL DECISIONS FINALIZED - READY FOR IMPLEMENTATION**

#### 1. Callback Overhead Budget ✅ APPROVED
- ✅ **Decision:** APPROVED - <100ms per agent callback overhead
- **Rationale:** 
  - Callbacks are lightweight (regex, dict lookups)
  - Most will run <10-30ms, 100ms provides headroom
  - Total overhead: ~500ms across 5 agents (acceptable for PR reviews)
- **Implementation:** Monitor callback execution time, optimize if >50ms average
- **Impact:** Enables complex validation without sacrificing performance

#### 2. False Positive Review Process ✅ APPROVED (Lightweight)
- ✅ **Decision:** APPROVED - Weekly async review (not meeting-based)
- **Process:**
  - **Weekly async review** (Fridays)
  - **Sample 20-30 filtered findings** (reduced from 50)
  - **Track FP filter rate metric** (automated)
  - **Update patterns monthly** (or when FP rate >10%)
  - **Owner:** One engineer assigned as KB maintainer (rotates quarterly)
- **Rationale:** Lightweight process ensures knowledge base accuracy with minimal overhead
- **Impact:** Continuous improvement with low maintenance burden

#### 3. Guardrail Metrics Dashboard ✅ APPROVED
- ✅ **Decision:** USE EXISTING observability stack (Prometheus + Grafana if available)
- **Approach:**
  - Leverage existing `util/metrics.py` structure
  - If no stack exists: Start with logs + simple Grafana dashboard
  - No custom dashboard initially (YAGNI principle)
- **Metrics to Track:**
  - Callback execution time (histogram)
  - Confidence score distribution (histogram)
  - False positive filter rate (gauge)
  - Evaluation score distribution (histogram)
- **Impact:** Fast setup, leverages existing infrastructure

#### 4. Callback Error Handling Strategy ✅ APPROVED (Fail-Open)
- ✅ **Decision:** FAIL-OPEN with error logging + alerting
- **Implementation:**
  ```python
  try:
      callback_result = run_callback(...)
  except Exception as e:
      logger.error(f"Callback failed: {e}")
      metrics.callback_errors.inc()
      return None  # Continue execution
  ```
- **Alert Threshold:** Alert if error rate >5%
- **Rationale:** PR reviews shouldn't break due to malformed regex patterns
- **Impact:** System resilient, quality monitoring via alerts

#### 5. Quality Loop Approval ✅ APPROVED
- ✅ **Decision:** YES - Implement Quality Loop (Phase 3 after callbacks)
- **Rationale:**
  - Callbacks = prevention during execution
  - Quality Loop = safety net for final report quality
  - 15-60s latency acceptable for PR reviews (not real-time chat)
  - $0.01-0.02 per review negligible vs. developer time saved
  - Catches cross-agent inconsistencies, missing evidence
- **Implementation Order:** Callbacks first (Phase 1-2), then Quality Loop (Phase 3)
- **Impact:** Comprehensive quality assurance with defense-in-depth

#### 6. Evaluator Agent Thresholds ✅ APPROVED (with tuning plan)
- ✅ **Decision:** START with proposed thresholds, TUNE after 2 weeks
- **Initial Thresholds:**
  - Flag for review: evaluation_score < 0.60
  - Auto-filter: evaluation_score < 0.40
  - Min evidence quality: 0.50
- **Tuning Plan:** After 2 weeks, analyze:
  - Auto-filtered findings accuracy
  - Review queue size (adjust if overwhelming)
  - Adjust thresholds based on production data
- **Impact:** Conservative start, data-driven optimization

#### 7. Confidence Score Requirement ✅ APPROVED (Mandatory)
- ✅ **Decision:** MANDATORY with graceful degradation
- **Enforcement:**
  - Agent instruction REQUIRES confidence_score + reasoning
  - If missing: Log error + assign default 0.50
  - DO NOT fail entire agent (graceful degradation)
- **Validation:** Artifact saver checks for confidence_score, logs warning if missing
- **Rationale:** Transparency critical for user trust, but system shouldn't break
- **Impact:** Full transparency with system resilience

#### 8. Knowledge Base Update Frequency ✅ APPROVED (Hybrid)
- ✅ **Decision:** HYBRID approach (monthly + quarterly + ad-hoc)
- **Process:**
  - **Monthly review:** Check FP rate, review flagged findings
  - **Quarterly update:** Align with industry standards (OWASP updates, new CWEs)
  - **Ad-hoc (immediate):** When FP rate spikes >10%
  - **Owner:** One engineer + rotate quarterly
  - **Process:** PR-based updates to `config/knowledge_base/*.yaml`
- **Rationale:** Balances responsiveness with structured updates
- **Impact:** System stays current with industry standards and project needs

---

### Decision Summary Table

| # | Decision Point | Status | Decision | Rationale |
|---|----------------|--------|----------|-----------|
| 1 | Callback Overhead | ✅ CLOSED | <100ms per agent | Provides headroom for complex validation |
| 2 | FP Review Process | ✅ CLOSED | Weekly async, 20-30 samples | Lightweight continuous improvement |
| 3 | Metrics Dashboard | ✅ CLOSED | Use existing (Prometheus+Grafana) | Leverage existing infrastructure |
| 4 | Error Handling | ✅ CLOSED | Fail-open + alerting | Resilient system with monitoring |
| 5 | Quality Loop | ✅ CLOSED | Implement Phase 3 | Comprehensive quality assurance |
| 6 | Evaluator Thresholds | ✅ CLOSED | 0.60/0.40/0.50, tune after 2 weeks | Data-driven optimization |
| 7 | Confidence Mandatory | ✅ CLOSED | Required, default 0.50 fallback | Transparency with resilience |
| 8 | KB Update Frequency | ✅ CLOSED | Monthly + quarterly + ad-hoc | Responsive to needs + standards |

**DESIGN DOCUMENT STATUS:** ✅ **APPROVED - READY FOR IMPLEMENTATION**

---

## Appendix A: ADK Callback Reference

### Callback Types
- `before_agent_callback` - Before agent starts
- `after_agent_callback` - After agent completes
- `before_model_callback` - Before LLM call
- `after_model_callback` - After LLM response
- `before_tool_callback` - Before tool execution
- `after_tool_callback` - After tool completes

### Return Behavior
- `return None` → Proceed normally
- `return Object` → Override/skip operation

### Context Available
- `callback_context.state` - Session state
- `callback_context.invocation_id` - Request ID
- `callback_context.user_id` - User identifier

---

## Appendix B: Real-World Examples - Two-Tier Quality in Action

### Example 1: SQL Injection False Positive

**Without Quality Assurance:**
```
Security Agent finds: "SQL injection vulnerability at line 42"
Report shows: "CRITICAL: SQL injection detected in user input handling"
Reality: It's a parameterized query (false positive)
```

**With Tier 1 (Callbacks Only):**
```
Security Agent finds: "SQL injection vulnerability at line 42"
→ after_tool_callback: Checks false_positive_patterns.yaml
→ Pattern match: "Parameterized query detected"
→ Callback filters out finding
Report shows: No SQL injection (correctly filtered)
```

**With Both Tiers:**
```
Security Agent finds: "SQL injection vulnerability at line 42"
→ after_tool_callback: Misses it (pattern not exact match)
→ Finding makes it to draft report

Quality Loop - Iteration 1:
→ Critic: "Line 42: Verify finding. Check if parameterized query."
→ Refiner: Cross-checks code context in artifacts
→ Refiner: Removes false positive finding
→ Critic (Iteration 2): "APPROVED - Report accurate"

Final Report: No SQL injection (caught by quality loop)
```

**Benefit:** Two chances to catch the false positive!

---

### Example 2: Missing Evidence

**Without Quality Assurance:**
```
Quality Agent: "High complexity detected"
Report shows: "This code has terrible complexity and needs refactoring."
Evidence: None (no metrics, no line numbers)
```

**With Tier 1 (Callbacks Only):**
```
Quality Agent: "High complexity detected"
→ after_agent_callback: Checks for metrics in output
→ Finds metric: cyclomatic_complexity=47
→ Callback rewrites: "Cyclomatic complexity score 47 exceeds threshold 15"
Report shows: Objective statement with metric ✅
```

**With Both Tiers (Belt and Suspenders):**
```
Quality Agent: "High complexity detected (complexity=47)"
→ after_agent_callback: Validates metric present ✅
→ Draft report has metric

Quality Loop - Iteration 1:
→ Critic: "Finding has metric but missing line numbers. Add file:line reference."
→ Refiner: Adds "src/utils.py:142-180"
→ Critic (Iteration 2): "APPROVED - Complete evidence"

Final Report: "Cyclomatic complexity 47 in src/utils.py:142-180 exceeds threshold 15" ✅✅
```

**Benefit:** Callbacks ensure metric present, loop ensures line numbers added!

---

### Example 3: Hallucinated CVE

**Without Quality Assurance:**
```
Security Agent: "CVE-2024-99999 detected in dependency"
Report shows: "CRITICAL: CVE-2024-99999 (invented by LLM)"
```

**With Tier 1 (Callbacks Only):**
```
Security Agent: "CVE-2024-99999 detected"
→ after_agent_callback: Calls validate_cve_exists()
→ API check: CVE does not exist
→ Callback removes finding
Report shows: No CVE (hallucination blocked) ✅
```

**With Both Tiers (Defense in Depth):**
```
Security Agent: "CVE-2024-99999 detected"
→ after_agent_callback: CVE validation API times out (network issue)
→ Finding makes it to draft report ⚠️

Quality Loop - Iteration 1:
→ Critic: Cross-validates all CVEs against source artifacts
→ Critic: "CVE-2024-99999 not in security_agent_analysis.json - hallucination!"
→ Refiner: Removes CVE from report
→ Critic (Iteration 2): "APPROVED - No hallucinations"

Final Report: No CVE (caught by redundant validation) ✅
```

**Benefit:** If callback fails (network/timeout), loop catches it!

---

### Example 4: Subjective Language

**Without Quality Assurance:**
```
Engineering Agent: "This architecture is a complete disaster"
Report shows: Emotional criticism, not actionable
```

**With Tier 1 (Callbacks Only):**
```
Engineering Agent: "This architecture is a complete disaster"
→ after_agent_callback: Runs filter_bias()
→ Matches pattern: "disaster" in bias_prevention.yaml
→ Callback rewrites: "Architecture violates single responsibility principle"
Report shows: Objective, actionable feedback ✅
```

**With Both Tiers (Holistic Check):**
```
Engineering Agent: Analysis with mostly objective language
→ after_agent_callback: Filters a few subjective terms ✅
→ Draft report 95% objective

Quality Loop - Iteration 1:
→ Critic: "Overall objective, but paragraph 3 says 'obviously wrong' - subjective"
→ Refiner: Replaces with "deviates from industry best practice (OWASP guideline X)"
→ Critic (Iteration 2): "APPROVED - Fully objective"

Final Report: 100% objective language ✅✅
```

**Benefit:** Callbacks catch individual terms, loop reviews full context!

---

### Example 5: Cross-Agent Inconsistency

**Without Quality Assurance:**
```
Security Agent: "No critical vulnerabilities"
Quality Agent: "SQL injection at line 78"
Report shows: Contradictory findings (confusing to user)
```

**With Tier 1 (Callbacks Only):**
```
Security Agent: "No critical vulnerabilities"
Quality Agent: "SQL injection at line 78"
→ Callbacks can't see cross-agent issues (different execution contexts)
Report shows: Contradiction remains ⚠️
```

**With Both Tiers (Quality Loop Catches It):**
```
Security Agent: "No critical vulnerabilities"
Quality Agent: "SQL injection at line 78"
→ Both pass individual callbacks
→ Draft report has contradiction

Quality Loop - Iteration 1:
→ Critic: "Inconsistency detected. Security says 'no vulns', Quality says 'SQL injection'."
→ Critic: "Cross-validate findings against source artifacts."
→ Refiner: Checks both JSONs, finds SQL injection only in Quality artifact
→ Refiner: Removes from Quality section OR moves to Security section
→ Critic (Iteration 2): "APPROVED - Consistent findings across sections"

Final Report: Consistent, no contradictions ✅
```

**Benefit:** Only the Quality Loop has full report context to catch this!

---

**Key Insight:** The two tiers are **complementary, not redundant**:
- **Callbacks** = Fast, domain-specific, real-time prevention
- **Quality Loop** = Slow, holistic, comprehensive validation

Together they provide **defense in depth** against quality issues.

---

## Appendix C: Decision Tree - Callbacks vs Quality Loop

```
                    Quality Issue Detected
                            ↓
              ┌─────────────┴─────────────┐
              │                           │
         Issue Type?                 Issue Type?
              ↓                           ↓
    ┌─────────────────┐         ┌──────────────────┐
    │ SINGLE OPERATION│         │ MULTI-AGENT      │
    │ DOMAIN-SPECIFIC │         │ CROSS-CUTTING    │
    │ REAL-TIME       │         │ HOLISTIC         │
    └─────────────────┘         └──────────────────┘
              ↓                           ↓
    ┌─────────────────┐         ┌──────────────────┐
    │   USE CALLBACK  │         │ USE QUALITY LOOP │
    └─────────────────┘         └──────────────────┘
              ↓                           ↓
    Examples:                    Examples:
    • Filter FP in tool         • Cross-agent consistency
    • Validate CVE exists       • Evidence completeness
    • Remove profanity          • Full report objectivity
    • Add metric to output      • Contradiction detection
    • Check rate limits         • Missing sections
              ↓                           ↓
    Characteristics:             Characteristics:
    ✅ <100ms                     ⚠️ 15-60s
    ✅ No cost                    ⚠️ ~$0.01/review
    ✅ Prevents propagation       ✅ Catches what slipped through
    ❌ No full context            ✅ Full report context
    ❌ No iteration               ✅ Iterative refinement
```

**Rule of Thumb:**
- If you can validate **during execution** → Use callback
- If you need **full report context** → Use quality loop
- If unsure → **Use both!** (defense in depth)

---

## Appendix D: Quick Reference - Complete Roadmap

### Phase 1: Callback Infrastructure (Weeks 1-2)
**Goal:** Implement inline guardrails for all agents

| Component | Files | Purpose |
|-----------|-------|---------|
| Shared utilities | `util/callbacks.py` | Reusable validation functions |
| Config files | `config/guardrails/callback_config.yaml`<br>`config/guardrails/false_positive_patterns.yaml`<br>`config/guardrails/profanity_blocklist.txt` | Centralized guardrail configuration |
| Security Agent | `agent_workspace/orchestrator_agent/sub_agents/security_agent/agent.py` | 3 callbacks (before_model, after_tool, after_agent) |
| Quality Agent | `agent_workspace/orchestrator_agent/sub_agents/code_quality_agent/agent.py` | 3 callbacks |
| Engineering Agent | `agent_workspace/orchestrator_agent/sub_agents/engineering_practices_agent/agent.py` | 2 callbacks |
| Carbon Agent | `agent_workspace/orchestrator_agent/sub_agents/carbon_emission_agent/agent.py` | 2 callbacks |
| Report Synthesizer | `agent_workspace/orchestrator_agent/sub_agents/report_synthesizer_agent/agent.py` | 2 callbacks |
| Metrics | `util/metrics.py` | Guardrail execution tracking |
| Tests | `tests/unit/test_callbacks.py`<br>`tests/integration/test_guardrails.py` | Validation |

**Success Criteria:**
- ✅ All agents have callbacks implemented
- ✅ <100ms overhead per agent
- ✅ >80% reduction in hallucinated findings

---

### Phase 2: Quality Loop System (Weeks 3-4)
**Goal:** Implement iterative report refinement

| Component | Files | Purpose |
|-----------|-------|---------|
| Loop config | `config/guardrails/quality_loop_config.yaml` | Iteration limits, criteria weights |
| Critic Agent | `agent_workspace/orchestrator_agent/sub_agents/quality_critic_agent/agent.py` | Evaluate report quality |
| Refiner Agent | `agent_workspace/orchestrator_agent/sub_agents/quality_refiner_agent/agent.py` | Apply improvements or exit |
| Exit tool | `tools/exit_quality_loop.py` | Early termination mechanism |
| Orchestrator update | `agent_workspace/orchestrator_agent/agent.py` | Integrate LoopAgent after Report Synthesizer |
| Metrics | `util/metrics.py` | Loop iterations, improvements, duration |
| Tests | `tests/unit/test_quality_loop.py`<br>`tests/integration/test_end_to_end_with_loop.py` | Validation |

**Success Criteria:**
- ✅ >95% of reports meet quality criteria
- ✅ Average <30s latency overhead
- ✅ >70% early exit rate (within 2 iterations)
- ✅ 0 false approvals (hallucinations in approved reports)

---

### Phase 3: Monitoring & Tuning (Week 5+)
**Goal:** Optimize performance based on production data

| Activity | Metrics | Actions |
|----------|---------|---------|
| Callback performance | Execution time per callback | Optimize slow callbacks |
| False positive rates | Findings filtered by type | Tune patterns, add exceptions |
| Quality loop efficiency | Iterations per review, exit reasons | Adjust max_iterations, criteria weights |
| Cost analysis | Token usage, LLM costs | Balance quality vs cost |
| A/B testing | Reports with/without quality loop | Validate business value |
| User feedback | Report quality ratings | Incorporate into criteria |

---

### Key Integrations

**Existing Config Files Leveraged:**
- ✅ `config/guardrails/hallucination_prevention.yaml` - Evidence requirements
- ✅ `config/guardrails/quality_gates.yaml` - Metric thresholds
- ✅ `config/guardrails/security_analysis.yaml` - Vulnerability patterns
- ✅ `config/guardrails/bias_prevention.yaml` - Objective language rules

**New Config Files Required:**
- 🆕 `config/guardrails/callback_config.yaml` - Per-agent callback settings
- 🆕 `config/guardrails/false_positive_patterns.yaml` - Known FP patterns
- 🆕 `config/guardrails/quality_loop_config.yaml` - Loop behavior, criteria
- 🆕 `config/guardrails/profanity_blocklist.txt` - Content moderation list

**Code Structure:**
```
agent_workspace/orchestrator_agent/
├── agent.py                           # Updated with LoopAgent integration
├── sub_agents/
│   ├── security_agent/
│   │   └── agent.py                   # + callbacks
│   ├── code_quality_agent/
│   │   └── agent.py                   # + callbacks
│   ├── engineering_practices_agent/
│   │   └── agent.py                   # + callbacks
│   ├── carbon_emission_agent/
│   │   └── agent.py                   # + callbacks
│   ├── report_synthesizer_agent/
│   │   └── agent.py                   # + callbacks
│   ├── quality_critic_agent/          # NEW
│   │   └── agent.py
│   └── quality_refiner_agent/         # NEW
│       └── agent.py

util/
├── callbacks.py                       # NEW - Shared utilities
├── metrics.py                         # NEW - Guardrail metrics tracking
├── llm_model.py                       # EXISTING - LLM configuration
├── artifact_service.py                # EXISTING - Artifact storage
├── session.py                         # EXISTING - Session management
├── system_prompts.py                  # EXISTING - Prompt templates
├── llm_wrapper.py                     # EXISTING - LLM wrapper utilities
├── rate_limiter.py                    # EXISTING - Rate limiting
├── result_cache.py                    # EXISTING - Result caching
└── service_registry.py                # EXISTING - Service registry

tools/
├── exit_quality_loop.py               # NEW
├── carbon_footprint_analyzer.py       # EXISTING
├── complexity_analyzer_tool.py        # EXISTING
├── engineering_practices_evaluator.py # EXISTING
├── security_vulnerability_scanner.py  # EXISTING
├── static_analyzer_tool.py            # EXISTING
└── tree_sitter_tool.py                # EXISTING

config/guardrails/
├── callback_config.yaml               # NEW
├── false_positive_patterns.yaml       # NEW
├── quality_loop_config.yaml           # NEW
├── profanity_blocklist.txt            # NEW
├── hallucination_prevention.yaml      # EXISTING
├── quality_gates.yaml                 # EXISTING
├── security_analysis.yaml             # EXISTING
└── bias_prevention.yaml               # EXISTING

```

---

**Document Status:** Design Complete - Ready for Implementation  
**Version:** 2.0  
**Next Review:** After Phase 1 Completion (Callbacks)  
**Owner:** Development Team  
**Stakeholders:** Security, Quality, Engineering Teams  

**Estimated Timeline:**
- Phase 1 (Callbacks): 2 weeks
- Phase 2 (Quality Loop): 2 weeks
- Phase 3 (Tuning): Ongoing
- **Total to Production:** 4-6 weeks
