# Phase 2: Prompt Engineering & Model Quality

**Status:** 📋 PLANNED  
**Prerequisites:** Phase 1 Complete ✅  
**Estimated Duration:** 2-3 days

---

## Objectives

1. **Fix LLM Output Quality** - Eliminate invalid JSON generation
2. **Ground Analysis to Actual Code** - Stop hallucinated examples
3. **Complete Report Sections** - Ensure all required sections present
4. **Add Confidence Scores** - Include confidence in all analyses

---

## Issue 1: Invalid JSON from Carbon Agent

### Problem Statement
Carbon emission agent generates malformed JSON with unquoted percentage values:
```json
"computational_energy_use": -15% (estimated reduction in CPU cycles),
```

**Error:** `Expecting ',' delimiter: line 33 column 36 (char 1474)`

### Root Cause Analysis
- LLM generates prose-style values instead of valid JSON
- No strict format enforcement in prompt
- Output schema not clearly defined

### Proposed Solutions

#### Solution 1A: Enhanced Prompt with Schema Example ⭐ (Recommended)
**Effort:** Low  
**Impact:** High

**Implementation:**
```python
# In carbon_agent_before_model callback
schema_example = '''
REQUIRED OUTPUT FORMAT (Valid JSON only):
{
  "agent": "carbon_emission_agent",
  "summary": "string - brief summary",
  "computational_efficiency": [
    {
      "issue": "string - description",
      "example": "string - code reference",
      "line": number,
      "recommendation": "string - fix suggestion"
    }
  ],
  "energy_impact_assessment": {
    "computational_energy_use": "string - e.g., '-15% estimated reduction'",
    "memory_bandwidth_reduction": "string - e.g., '-8% less data transfer'",
    "storage_energy_efficiency": "string - e.g., '+12% fewer writes'"
  }
}

CRITICAL: All string values must be quoted. Do NOT use bare percentages or numbers.
CRITICAL: All field names must be exact matches to schema above.
'''
llm_request.config.system_instruction += schema_example
```

#### Solution 1B: JSON Repair Utility
**Effort:** Medium  
**Impact:** Medium (defensive)

**Implementation:**
```python
# In util/json_repair.py
import re

def repair_json(text: str) -> str:
    """Fix common JSON errors from LLM output."""
    # Fix bare percentages: -15% → "-15%"
    text = re.sub(r':\s*(-?\d+)%\s*\(', r': "\1% (', text)
    
    # Fix missing commas before closing braces
    text = re.sub(r'\)\s*\n\s*}', r')",\n  }', text)
    
    # Fix bare numbers with descriptions
    text = re.sub(r':\s*(\d+)\s*\(([^)]+)\)', r': "\1 (\2)"', text)
    
    return text

# In carbon_agent_after_agent callback
analysis = parse_json_safe(text)
if not analysis:
    # Try repair
    repaired = repair_json(text)
    analysis = parse_json_safe(repaired)
    if analysis:
        logger.info("✅ JSON repaired successfully")
```

#### Solution 1C: Structured Output Mode (Future)
**Effort:** High (requires model support)  
**Impact:** High (if available)

Check if `ollama_chat/granite4` supports structured output:
```python
# Check LiteLLM documentation for structured output
response = client.completion(
    model="ollama_chat/granite4:latest",
    messages=[...],
    response_format={"type": "json_object"},  # If supported
    schema=carbon_analysis_schema
)
```

---

## Issue 2: Generic Analysis Instead of Actual Code

### Problem Statement
Agents analyze hallucinated code (e.g., `getUserById`, `line 83`) instead of actual PR files (ChatPanel.tsx, orchestrator_agent_bk.py).

### Root Cause Analysis
- Prompt doesn't explicitly reference file names
- LLM relies on general knowledge instead of provided code
- No grounding mechanism in place

### Evidence
```
Data Adapter: ✅ "ChatPanel.tsx (typescript, 378 lines)"
Security Analysis: ❌ "SQL Injection in getUserById line 83" (doesn't exist!)
```

### Proposed Solutions

#### Solution 2A: Explicit File Context in Prompt ⭐ (Recommended)
**Effort:** Low  
**Impact:** High

**Implementation:**
```python
# In security_agent_before_model callback (and others)
file_context = callback_context.state.get('file_path', 'unknown')
file_count = callback_context.state.get('file_count', 0)
languages = callback_context.state.get('languages', [])

grounding_instruction = f'''
CRITICAL ANALYSIS CONTEXT:
- You are analyzing ACTUAL CODE from a GitHub Pull Request
- Files in this PR: {file_count} files
- File path: {file_path}
- Languages: {', '.join(languages)}
- Total lines: {callback_context.state.get('total_lines', 0)}

INSTRUCTIONS:
1. Analyze ONLY the code provided in the 'code' field below
2. Reference actual file names (e.g., "ChatPanel.tsx line 42")
3. Quote actual code snippets from the provided files
4. Do NOT use generic examples or imagined code
5. If no issues found, explicitly state "No security issues detected in provided code"

CODE TO ANALYZE:
{callback_context.state.get('code', '')[:5000]}...  # First 5000 chars as context
'''

llm_request.config.system_instruction += grounding_instruction
```

#### Solution 2B: File Name Injection in Tool Calls
**Effort:** Medium  
**Impact:** High

Modify tool schemas to require file references:
```python
# In tools/security_vulnerability_scanner.py
def scan_security_vulnerabilities(code: str, language: str, file_path: str = "unknown"):
    """
    Args:
        file_path: REQUIRED - Name of the file being analyzed
    """
    # Tool output must include file_path in each finding
```

#### Solution 2C: Few-Shot Examples with Real Code
**Effort:** Medium  
**Impact:** Medium

```python
few_shot_example = '''
EXAMPLE ANALYSIS (from previous PR):

File: components/UserForm.tsx
Issue: "useState not properly initialized"
Line: 42
Code: `const [email, setEmail] = useState();`
Recommendation: "Initialize with empty string: useState('')"

Now analyze the provided code using the same format.
'''
```

---

## Issue 3: Missing Report Sections

### Problem Statement
Report synthesizer missing sections: 'Executive Summary', 'Engineering Practices', 'Environmental Impact'

### Root Cause Analysis
1. Carbon analysis JSON failed to parse → Environmental Impact incomplete
2. Report synthesis prompt doesn't specify required sections
3. No section template enforcement

### Proposed Solutions

#### Solution 3A: Section Template in Prompt ⭐ (Recommended)
**Effort:** Low  
**Impact:** High

**Implementation:**
```python
# In report_synthesizer_agent/agent.py instructions
section_template = '''
REQUIRED REPORT SECTIONS (in order):

## Executive Summary
- Brief overview of PR (2-3 sentences)
- Critical issues count
- Overall recommendation (Approve/Request Changes/Comment)

## Security Analysis
- From security_agent artifact
- List vulnerabilities by severity
- Include OWASP categories

## Code Quality Assessment  
- From code_quality_agent artifact
- Complexity metrics
- Static analysis findings

## Engineering Practices
- From engineering_practices_agent artifact
- Best practices compliance
- Areas for improvement

## Environmental Impact
- From carbon_emission_agent artifact
- Energy efficiency analysis
- Carbon footprint recommendations

## Recommendations
- Prioritized action items
- Timeline suggestions

CRITICAL: Generate ALL sections even if some data is incomplete. For missing data, state "Analysis incomplete" with reason.
'''
```

#### Solution 3B: Section Validation Before Report Generation
**Effort:** Medium  
**Impact:** Medium

```python
# In report_synthesizer_before_agent callback
def validate_artifacts_completeness(callback_context):
    """Ensure all required artifacts are present and parseable."""
    required = {
        'security_analysis': 'Security Analysis',
        'code_quality_analysis': 'Code Quality Assessment',
        'engineering_practices_analysis': 'Engineering Practices',
        'carbon_emission_analysis': 'Environmental Impact'
    }
    
    missing_data = []
    for key, section in required.items():
        data = callback_context.state.get(key, '')
        if not data:
            missing_data.append(section)
            continue
        
        # Try to parse as JSON
        try:
            json.loads(data)
        except:
            logger.warning(f"⚠️ {key} is not valid JSON - may affect {section}")
            missing_data.append(f"{section} (invalid format)")
    
    if missing_data:
        logger.warning(f"⚠️ Report may be incomplete due to: {', '.join(missing_data)}")
        # Add instruction to LLM to handle missing sections gracefully
```

---

## Issue 4: Missing Confidence Scores

### Problem Statement
All 4 analysis agents generate output without confidence scores, triggering warnings.

### Proposed Solutions

#### Solution 4A: Add Confidence Field to Output Schemas ⭐ (Recommended)
**Effort:** Low  
**Impact:** Medium

**Implementation:**
```python
# Update agent instructions to include confidence
confidence_instruction = '''
CONFIDENCE SCORES:
Add a "confidence" field (0.0-1.0) to each finding:
- 1.0: Certain (code clearly shows the issue)
- 0.8: High confidence (strong evidence)
- 0.6: Medium confidence (likely issue, needs verification)
- 0.4: Low confidence (potential issue, may be false positive)
- 0.2: Very uncertain (flagged for review)

Example:
{
  "type": "SQL Injection",
  "confidence": 0.9,
  "location": "getUserById",
  ...
}
'''
```

#### Solution 4B: Automated Confidence Calculation
**Effort:** High  
**Impact:** Low (less accurate)

Calculate confidence based on heuristics:
- Pattern match strength
- Tool agreement (multiple tools find same issue)
- Code complexity in affected area

---

## Implementation Priority

### Week 1: Critical Fixes
1. **Issue 1 (Solution 1A + 1B):** Fix JSON output + repair utility
2. **Issue 2 (Solution 2A):** Add file context grounding
3. **Issue 3 (Solution 3A):** Add section templates

### Week 2: Quality Improvements
4. **Issue 2 (Solution 2B):** File name injection in tools
5. **Issue 4 (Solution 4A):** Add confidence scores
6. **Issue 3 (Solution 3B):** Artifact validation

### Week 3: Advanced Features
7. **Issue 2 (Solution 2C):** Few-shot examples
8. **Issue 1 (Solution 1C):** Explore structured output mode
9. **Testing & Iteration:** Test with various PR sizes/types

---

## Success Criteria

### Phase 2 Complete When:
- ✅ Carbon agent generates valid JSON (0 parsing errors)
- ✅ All agents reference actual file names from PR
- ✅ Final report includes all 6 required sections
- ✅ All findings include confidence scores (0.0-1.0)
- ✅ Test with 5 different PR examples (small/medium/large)
- ✅ End-to-end pipeline runs without warnings

---

## Testing Plan

### Test Suite
1. **Small PR (1 file, <200 lines)** - Basic functionality
2. **Medium PR (2-3 files, 500-1000 lines)** - Current test case
3. **Large PR (5+ files, 2000+ lines)** - Scalability
4. **Multi-language PR** - TypeScript + Python + Java
5. **Security-focused PR** - Known vulnerabilities injected

### Validation Checklist
- [ ] JSON parses without errors (all agents)
- [ ] File names match actual PR files
- [ ] Line numbers reference actual code locations
- [ ] Code snippets quoted from provided files
- [ ] All 6 report sections present
- [ ] Confidence scores in range [0.0, 1.0]
- [ ] No hallucinated code examples
- [ ] Pipeline completes in <5 minutes

---

## Dependencies

### External
- LiteLLM library (already installed)
- ollama_chat/granite4 model (already configured)

### Internal
- Phase 1 callbacks (✅ Complete)
- GitHub data adapter (✅ Working)
- Artifact saving system (✅ Working)

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM still generates invalid JSON | Medium | High | Implement JSON repair utility (Solution 1B) |
| LLM ignores file context | Medium | High | Make context more prominent, use few-shot examples |
| Prompt too long (token limit) | Low | Medium | Chunk large files, summarize context |
| Model doesn't support structured output | High | Low | Fall back to schema examples + repair |

---

## Next Phase Preview

**Phase 3:** Advanced Guardrails & Testing
- Hallucination detection refinement
- Bias detection improvement
- Profanity filtering
- Comprehensive test suite
- Performance optimization

---

**Document Version:** 1.0  
**Last Updated:** December 10, 2025  
**Owner:** Rahul Gupta
