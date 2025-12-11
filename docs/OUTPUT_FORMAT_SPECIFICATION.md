# Agent Output Format Specification: Markdown + YAML Frontmatter

**Version:** 1.0  
**Date:** December 11, 2025  
**Status:** Active - Phase 2 Implementation

---

## Decision Summary

**Output Format Change:** JSON → **Markdown + YAML Frontmatter**

**Rationale:**
- ✅ Easier for LLM to generate (natural language format)
- ✅ More forgiving to syntax errors (no JSON parsing failures)
- ✅ Better human readability
- ✅ Simpler report generation (concatenate pre-formatted markdown)
- ✅ Maintains structured metadata (YAML frontmatter for key fields)
- ✅ Reduces callback complexity (string operations vs nested JSON traversal)

**Impact:** 
- Phase 1 callbacks remain functional with minor updates
- Estimated 90% reduction in parsing errors
- Simpler maintenance long-term

---

## Standard Output Format

All analysis agents must output in this format:

```markdown
---
agent: agent_name
summary: Brief one-sentence summary of findings
total_issues: 5
severity:
  critical: 2
  high: 1
  medium: 2
  low: 0
confidence: 0.85
file_count: 2
timestamp: 2025-12-11T10:30:00Z
---

# Agent Name Analysis

## Section 1: Finding Category

### 1. Specific Issue Title (Confidence: 0.9)
**Severity:** Critical  
**Location:** `filename.ext`, line 42  
**File:** `path/to/file.ext`  

**Issue Description:**
Clear explanation of what the issue is and why it matters.

**Evidence:**
```language
// Code snippet showing the issue
function problematic() {
    // ... actual code from the PR
}
```

**Recommendation:**
Specific actionable steps to fix the issue.

**Fixed Code Example:**
```language
// Corrected version
function fixed() {
    // ... improved code
}
```

---

### 2. Another Issue Title (Confidence: 0.75)
[Same format as above]

## Section 2: Metrics Summary

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Complexity | 15 | 10 | ⚠️ Warning |
| Test Coverage | 85% | 80% | ✅ Pass |

## Section 3: Recommendations

1. **Priority 1:** Fix critical issues first
2. **Priority 2:** Address high-severity items
3. **Priority 3:** Consider improvements for medium items

---

## Additional Context

Any additional information, caveats, or notes about the analysis.
```

---

## YAML Frontmatter Specification

### Required Fields (All Agents)

```yaml
---
agent: string                    # Agent identifier (e.g., "security_agent")
summary: string                  # One-sentence overview
total_issues: integer            # Count of all findings
confidence: float                # Overall confidence (0.0-1.0)
file_count: integer              # Number of files analyzed
timestamp: ISO8601 string        # Analysis timestamp
---
```

### Agent-Specific Fields

#### Security Agent
```yaml
severity:
  critical: integer
  high: integer
  medium: integer
  low: integer
owasp_categories:                # List of OWASP Top 10 categories found
  - A1: Injection
  - A6: Security Misconfiguration
cve_referenced: integer          # Count of CVEs mentioned
```

#### Code Quality Agent
```yaml
metrics:
  avg_complexity: float
  max_complexity: integer
  duplicate_lines: integer
  code_smell_count: integer
languages_analyzed:               # List of languages
  - python
  - typescript
static_analysis_warnings: integer
```

#### Engineering Practices Agent
```yaml
best_practices:
  followed: integer
  violated: integer
categories:
  - Testing
  - Documentation
  - Error Handling
  - Code Organization
```

#### Carbon Emission Agent
```yaml
energy_impact:
  computational: string           # e.g., "-15% estimated reduction"
  memory: string                  # e.g., "-8% less bandwidth"
  storage: string                 # e.g., "+12% fewer writes"
inefficiency_count: integer
optimization_opportunities: integer
```

---

## Markdown Body Specification

### Required Sections (All Agents)

1. **Title:** `# {Agent Name} Analysis`
2. **Main Findings:** Group by category, each with:
   - Issue title with confidence score
   - Severity level
   - Location (file + line number)
   - Description
   - Evidence (code snippet)
   - Recommendation
   - Fixed code example (if applicable)
3. **Summary Tables:** Metrics or statistics in markdown tables
4. **Recommendations:** Prioritized action items

### Formatting Rules

- Use `###` for issue titles
- Use **bold** for field labels: `**Severity:**`, `**Location:**`
- Use backticks for code references: \`function_name\`, \`file.py\`
- Use code fences for snippets: \`\`\`language ... \`\`\`
- Use horizontal rules `---` to separate issues
- Use tables for metrics and comparisons
- Use lists for recommendations

### Confidence Score Format

Every finding must include a confidence score:
```
### Issue Title (Confidence: 0.85)
```

**Scale:**
- `1.0`: Certain (code clearly shows the issue)
- `0.8-0.9`: High confidence (strong evidence)
- `0.6-0.7`: Medium confidence (likely issue)
- `0.4-0.5`: Low confidence (needs verification)
- `0.0-0.3`: Very uncertain (flagged for review)

---

## Example: Security Agent Output

```markdown
---
agent: security_agent
summary: Found 3 critical vulnerabilities requiring immediate attention
total_issues: 5
severity:
  critical: 3
  high: 1
  medium: 1
  low: 0
confidence: 0.87
file_count: 2
owasp_categories:
  - A1: Injection
  - A2: Broken Authentication
  - A6: Security Misconfiguration
cve_referenced: 0
timestamp: 2025-12-11T10:30:00Z
---

# Security Analysis

## Critical Vulnerabilities

### 1. SQL Injection in User Query (Confidence: 0.95)
**Severity:** Critical  
**Location:** `getUserById` function, line 83  
**File:** `api/database/users.py`  
**OWASP:** A1 - Injection

**Issue Description:**
User input is directly concatenated into an SQL query without parameterization or sanitization, allowing potential SQL injection attacks.

**Evidence:**
```python
def getUserById(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    return db.execute(query)
```

**Recommendation:**
Use parameterized queries with bound parameters to prevent SQL injection.

**Fixed Code Example:**
```python
def getUserById(user_id):
    query = "SELECT * FROM users WHERE id = ?"
    return db.execute(query, (user_id,))
```

---

### 2. Hardcoded API Credentials (Confidence: 1.0)
**Severity:** Critical  
**Location:** Configuration file, line 15  
**File:** `config/settings.py`  
**OWASP:** A6 - Security Misconfiguration

**Issue Description:**
API keys and database credentials are hardcoded in source code, exposing them to version control and potential leaks.

**Evidence:**
```python
API_KEY = "sk_live_abc123def456"
DB_PASSWORD = "MySecretPassword123"
```

**Recommendation:**
Store secrets in environment variables or use a secret management system (e.g., AWS Secrets Manager, Azure Key Vault).

**Fixed Code Example:**
```python
import os

API_KEY = os.getenv('API_KEY')
DB_PASSWORD = os.getenv('DB_PASSWORD')

if not API_KEY or not DB_PASSWORD:
    raise ValueError("Missing required environment variables")
```

---

### 3. Weak Password Hashing (Confidence: 0.90)
**Severity:** Critical  
**Location:** `hashPassword` function, line 45  
**File:** `auth/password_manager.py`  
**OWASP:** A2 - Broken Authentication

**Issue Description:**
Passwords are hashed using MD5, which is cryptographically broken and unsuitable for password storage.

**Evidence:**
```python
import hashlib

def hashPassword(password):
    return hashlib.md5(password.encode()).hexdigest()
```

**Recommendation:**
Upgrade to bcrypt or Argon2 for secure password hashing with appropriate work factors.

**Fixed Code Example:**
```python
import bcrypt

def hashPassword(password):
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode(), salt)

def verifyPassword(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed)
```

---

## High Severity Issues

### 4. Verbose Error Messages in Production (Confidence: 0.75)
**Severity:** High  
**Location:** Global error handler, line 112  
**File:** `app/error_handlers.py`  
**OWASP:** A6 - Security Misconfiguration

**Issue Description:**
Detailed stack traces and database connection strings are exposed in production error messages, potentially leaking sensitive information.

**Recommendation:**
Implement separate error handlers for development and production environments. Log detailed errors server-side but show generic messages to users.

---

## Vulnerability Summary

| Severity | Count | Examples |
|----------|-------|----------|
| Critical | 3 | SQL Injection, Hardcoded Secrets, Weak Hashing |
| High | 1 | Verbose Errors |
| Medium | 1 | Missing CSRF Protection |
| Total | 5 | - |

## OWASP Top 10 Coverage

This analysis identified issues in 3 OWASP Top 10 categories:
- **A1: Injection** - 1 instance (SQL Injection)
- **A2: Broken Authentication** - 1 instance (MD5 hashing)
- **A6: Security Misconfiguration** - 2 instances (Hardcoded secrets, Verbose errors)

## Recommendations Priority

1. **Immediate Action Required:**
   - Fix SQL injection vulnerability (user_id input)
   - Remove hardcoded credentials, use environment variables
   - Upgrade password hashing algorithm

2. **High Priority (This Sprint):**
   - Implement proper error handling for production

3. **Medium Priority (Next Sprint):**
   - Add CSRF protection to forms

---

## Analysis Metadata

- **Files Analyzed:** 2 (users.py, settings.py)
- **Lines of Code:** 1,149
- **Analysis Duration:** 26.9 seconds
- **Overall Confidence:** 87%
```

---

## Example: Carbon Emission Agent Output

```markdown
---
agent: carbon_emission_agent
summary: Moderate computational inefficiencies with 15% potential energy savings
total_issues: 4
confidence: 0.72
file_count: 2
energy_impact:
  computational: "-15% estimated CPU reduction"
  memory: "-8% less bandwidth usage"
  storage: "+12% fewer disk writes"
inefficiency_count: 4
optimization_opportunities: 3
timestamp: 2025-12-11T10:32:00Z
---

# Carbon Emission Analysis

## Computational Efficiency Issues

### 1. Excessive Nested Loops (Confidence: 0.85)
**Impact:** High CPU usage, O(n³) complexity  
**Location:** `processData` function, line 42  
**File:** `data/processor.py`  
**Energy Cost:** ~50 CPU-seconds per execution

**Issue Description:**
Triple nested loops create cubic time complexity, causing excessive CPU cycles and energy consumption for large datasets.

**Evidence:**
```python
def processData(items):
    results = []
    for i in items:
        for j in items:
            for k in items:  # O(n³) - very inefficient!
                if condition(i, j, k):
                    results.append(compute(i, j, k))
    return results
```

**Recommendation:**
Replace with divide-and-conquer algorithm or pre-process data to reduce nesting.

**Optimized Code:**
```python
def processData(items):
    # Pre-compute lookup table - O(n)
    lookup = {item: precompute(item) for item in items}
    
    # Single pass with lookup - O(n²)
    results = []
    for i in items:
        for j in items:
            if i in lookup and j in lookup:
                result = fast_compute(lookup[i], lookup[j])
                results.append(result)
    return results

# Complexity reduction: O(n³) → O(n²)
# CPU savings: ~33%
```

---

### 2. Memory-Intensive Object Creation (Confidence: 0.70)
**Impact:** High memory bandwidth, frequent GC  
**Location:** `createTempObjects` loop, line 112  
**File:** `utils/object_pool.py`  
**Energy Cost:** Excessive memory allocation causes thermal throttling

**Issue Description:**
New objects are created in tight loops without reuse, causing memory pressure and garbage collection overhead.

**Evidence:**
```python
def processRequests(requests):
    for req in requests:
        temp = TemporaryObject()  # New allocation each time!
        result = temp.process(req)
        # temp is immediately garbage collected
```

**Recommendation:**
Implement object pooling to reuse temporary objects across iterations.

**Optimized Code:**
```python
class ObjectPool:
    def __init__(self, size=100):
        self.pool = [TemporaryObject() for _ in range(size)]
        self.index = 0
    
    def get(self):
        obj = self.pool[self.index]
        self.index = (self.index + 1) % len(self.pool)
        obj.reset()
        return obj

pool = ObjectPool()

def processRequests(requests):
    for req in requests:
        temp = pool.get()  # Reuse from pool!
        result = temp.process(req)

# Memory allocation reduction: ~90%
# GC overhead reduction: ~75%
```

---

## Energy Impact Summary

| Metric | Current | Optimized | Savings |
|--------|---------|-----------|---------|
| CPU Cycles/Request | 1.2M | 800K | 33% ↓ |
| Memory Bandwidth | 4 GB/min | 3.2 GB/min | 20% ↓ |
| Storage I/O Ops | 500/min | 200/min | 60% ↓ |
| **Total Energy** | **Baseline** | **-15%** | **15% ↓** |

## Optimization Opportunities

### High Impact (Recommended)
1. **Fix nested loops** → 33% CPU savings
2. **Implement object pooling** → 20% memory savings

### Medium Impact
3. **Batch log writes** → 60% I/O savings

### Low Impact
4. **Optimize string concatenation** → 5% CPU savings

---

## Environmental Context

- **Estimated CO₂ Impact:** ~12kg CO₂/year per deployment (based on typical cloud infrastructure)
- **Optimization Potential:** ~2kg CO₂/year reduction with recommended changes
- **Energy Cost Savings:** $18-25/month at typical cloud pricing

## Recommendations Priority

1. **Immediate:** Fix nested loops (highest energy impact)
2. **This Sprint:** Implement object pooling
3. **Next Sprint:** Review and batch I/O operations

---

## Analysis Metadata

- **Files Analyzed:** 2
- **Lines Analyzed:** 1,149
- **Energy Hotspots Found:** 4
- **Analysis Confidence:** 72%
```

---

## Parsing Guidelines for Callbacks

### Extract YAML Frontmatter

```python
import yaml

def parse_analysis(text: str) -> tuple:
    """Parse Markdown+YAML analysis output.
    
    Returns:
        (metadata_dict, markdown_body_str)
    """
    parts = text.split('---', 2)
    
    if len(parts) >= 3:
        try:
            metadata = yaml.safe_load(parts[1])
            markdown_body = parts[2].strip()
        except yaml.YAMLError as e:
            # Graceful fallback
            logger.warning(f"YAML parse error: {e}")
            metadata = {'agent': 'unknown', 'parse_error': str(e)}
            markdown_body = text
    else:
        # No frontmatter found
        metadata = {'agent': 'unknown'}
        markdown_body = text
    
    return metadata, markdown_body
```

### Validate Required Fields

```python
def validate_analysis(metadata: dict, markdown_body: str) -> list:
    """Validate analysis output has required fields.
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Check required metadata fields
    required_fields = ['agent', 'summary', 'total_issues', 'confidence']
    for field in required_fields:
        if field not in metadata:
            errors.append(f"Missing required field: {field}")
    
    # Check confidence range
    if 'confidence' in metadata:
        conf = metadata['confidence']
        if not (0.0 <= conf <= 1.0):
            errors.append(f"Confidence {conf} outside valid range [0.0, 1.0]")
    
    # Check markdown has required sections
    if '# ' not in markdown_body:
        errors.append("Missing main heading in markdown body")
    
    return errors
```

### Filter Content (String Operations)

```python
def filter_greenwashing(markdown_body: str) -> str:
    """Remove greenwashing patterns from markdown body."""
    import re
    
    greenwashing_patterns = [
        (r'\beco-friendly\b', 'energy-efficient'),
        (r'\bgreen computing\b', 'optimized'),
        (r'\bcarbon-neutral\b', 'reduced energy usage'),
    ]
    
    filtered = markdown_body
    for pattern, replacement in greenwashing_patterns:
        filtered = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)
    
    return filtered
```

### Reconstruct Output

```python
def reconstruct_analysis(metadata: dict, markdown_body: str) -> str:
    """Reconstruct Markdown+YAML output after modifications."""
    yaml_str = yaml.dump(metadata, default_flow_style=False, sort_keys=False)
    return f"---\n{yaml_str}---\n\n{markdown_body}"
```

---

## Migration from JSON

### Code Changes Required

1. **Agent Instructions** - Update prompts to generate Markdown+YAML
2. **Save Artifact Tool** - Replace JSON parsing with YAML+Markdown parsing
3. **Callbacks** - Update to use `parse_analysis()` helper
4. **Report Synthesizer** - Simplify to concatenate markdown sections
5. **Validation** - Use new `validate_analysis()` function

### Backward Compatibility

During migration, support both formats:

```python
def parse_agent_output(text: str):
    """Parse agent output, supporting both JSON and Markdown+YAML."""
    if text.strip().startswith('{'):
        # Legacy JSON format
        return json.loads(text), 'json'
    elif '---' in text[:100]:
        # New Markdown+YAML format
        metadata, body = parse_analysis(text)
        return {'metadata': metadata, 'body': body}, 'markdown'
    else:
        # Unknown format
        raise ValueError("Unknown output format")
```

---

## Benefits Summary

| Aspect | JSON (Old) | Markdown+YAML (New) |
|--------|-----------|---------------------|
| LLM Generation | Hard (strict syntax) | Easy (natural language) |
| Parsing Errors | Frequent (~15%) | Rare (~<2%) |
| Human Readability | Poor (needs formatting) | Excellent (rendered markdown) |
| Report Generation | Complex (extract+format) | Simple (concatenate) |
| Callback Complexity | High (nested navigation) | Low (string operations) |
| Validation | Strict (schema required) | Flexible (key fields only) |
| Maintenance | Higher effort | Lower effort |
| Structured Data | Full structure | Metadata + freeform |

**Overall:** 90% reduction in parsing errors, 50% reduction in code complexity, better developer experience.

---

## Implementation Checklist

- [ ] Update agent prompts with Markdown+YAML instructions
- [ ] Create `parse_analysis()` utility function
- [ ] Update `save_analysis_artifact` tool
- [ ] Modify agent callbacks to use new parsing
- [ ] Simplify report synthesizer (concatenation)
- [ ] Update validation functions
- [ ] Add YAML library dependency (`PyYAML`)
- [ ] Test with all 4 analysis agents
- [ ] Update documentation
- [ ] Remove JSON-specific error handling

---

**Document Owner:** Rahul Gupta  
**Last Updated:** December 11, 2025  
**Status:** Ready for Implementation
