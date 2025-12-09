# Callbacks, Guardrails & Quality Loop Implementation Design Document

**Version:** 2.0  
**Date:** December 9, 2025  
**Status:** Design Phase

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
11. [Next Steps](#11-next-steps)
12. [Appendix A: ADK Callback Reference](#appendix-a-adk-callback-reference)

---

## Executive Summary

This document outlines the comprehensive **two-tier quality assurance strategy** for the Agentic Code Review System, combining:

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

**Strategy:** Callbacks prevent bad data during execution, Quality Loop validates and refines the final output before delivery.

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
│              Saves 4 analysis JSONs to storage                            │
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
    # Parse security analysis JSON
    analysis = json.loads(content.parts[0].text)
    
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
    """Validate JSON output matches expected schema."""
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

## 11. Next Steps

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

### Decision Points
- [ ] Approve callback overhead budget (<100ms per agent?)
- [ ] Define false positive review process
- [ ] Establish guardrail metrics dashboard
- [ ] Decide on fail-open vs fail-closed for callback errors
- [ ] **NEW:** Approve Quality Loop implementation (Phase 3 after callbacks)?
- [ ] **NEW:** Set quality loop latency/cost budgets
- [ ] **NEW:** Define quality score calculation methodology

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
