# Security Agent - Design Documentation

**Version:** 1.0  
**Last Updated:** December 16, 2025  
**Agent Location:** `agent_workspace/orchestrator_agent/sub_agents/security_agent/`

---

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Security Scanning Components](#security-scanning-components)
4. [Execution Flow](#execution-flow)
5. [Guardrails & Validation](#guardrails--validation)
6. [SAST Rules Engine](#sast-rules-engine)
7. [OWASP Top 10 Analysis](#owasp-top-10-analysis)
8. [Output Format](#output-format)
9. [Configuration](#configuration)
10. [Error Handling](#error-handling)

---

## Overview

### Purpose
The Security Agent performs comprehensive security vulnerability analysis on code submissions, detecting potential security issues through:
- Static Application Security Testing (SAST) using regex-based rules
- OWASP Top 10 vulnerability heuristics
- Security configuration checks
- Risk assessment and compliance validation

### Key Capabilities
- ✅ Multi-language support (Python, TypeScript, JavaScript, Go, C++, etc.)
- ✅ Rule-based vulnerability detection (15+ SAST rules per language)
- ✅ OWASP Top 10 2021 coverage
- ✅ False positive filtering and confidence scoring
- ✅ CVE validation and hallucination prevention
- ✅ Automated reporting with actionable recommendations

### Integration Points
```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Pipeline                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  GitHub Fetcher → Data Adapter → [Security Agent] → Saver   │
│                                         ↓                     │
│                              output_key: security_analysis   │
│                              tool: scan_security_vulnerabilities │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture

### Component Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                      Security Agent                          │
│                (agent_workspace/.../security_agent/)         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            Agent Core (agent.py)                     │  │
│  │  - ADK Agent wrapper                                  │  │
│  │  - LLM orchestration (granite4:latest)               │  │
│  │  - output_key: security_analysis                     │  │
│  └───────────────┬──────────────────────────────────────┘  │
│                  │                                           │
│  ┌───────────────▼──────────────────────────────────────┐  │
│  │         Guardrail Callbacks                          │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │ before_model_callback                        │   │  │
│  │  │  - Inject security analysis constraints      │   │  │
│  │  │  - Load security knowledge bases             │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │ after_tool_callback                          │   │  │
│  │  │  - Normalize tool response                   │   │  │
│  │  │  - Filter false positives                    │   │  │
│  │  │  - Compute confidence scores                 │   │  │
│  │  │  - Validate findings                         │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │ after_agent_callback                         │   │  │
│  │  │  - Validate CVE IDs (API check)              │   │  │
│  │  │  - Filter bias/profanity                     │   │  │
│  │  │  - Parse/validate YAML frontmatter           │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────┘  │
│                  │                                           │
│  ┌───────────────▼──────────────────────────────────────┐  │
│  │   Security Vulnerability Scanner Tool                │  │
│  │   (tools/security_vulnerability_scanner.py)          │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ SAST Rules Engine                           │    │  │
│  │  │  - Load language-specific rules             │    │  │
│  │  │  - Regex pattern matching                   │    │  │
│  │  │  - Allowlist filtering                      │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ OWASP Top 10 Heuristics                     │    │  │
│  │  │  - Injection detection                      │    │  │
│  │  │  - Auth/AuthZ checks                        │    │  │
│  │  │  - Data exposure patterns                   │    │  │
│  │  │  - Security misconfigurations               │    │  │
│  │  │  - XSS/XXE/Deserialization                  │    │  │
│  │  │  - Logging/monitoring gaps                  │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  │  ┌─────────────────────────────────────────────┐    │  │
│  │  │ Risk & Compliance Assessment                │    │  │
│  │  │  - Aggregate severity scores                │    │  │
│  │  │  - Generate security grade                  │    │  │
│  │  │  - Produce recommendations                  │    │  │
│  │  └─────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### File Structure
```
agent_workspace/orchestrator_agent/sub_agents/security_agent/
├── agent.py                    # Main agent definition
└── __init__.py

tools/
├── security_vulnerability_scanner.py    # Core scanning logic
└── sast_rules_loader.py                # SAST rules loading utility

util/
├── callbacks.py                # Guardrail utilities
├── security_enrichment.py      # Confidence & enrichment
└── markdown_yaml_parser.py     # Output validation

config/
├── knowledge_base/
│   ├── security_guidelines.yaml        # Security review guidelines & OWASP mapping
│   └── security_controls/sast_rules/
│       ├── generic.yaml           # Cross-language rules
│       ├── python.yaml            # Python-specific rules
│       ├── typescript.yaml        # TypeScript rules
│       ├── javascript.yaml        # JavaScript rules
│       ├── go.yaml                # Go rules
│       ├── cpp.yaml               # C++ rules
│       ├── csharp.yaml            # C# rules
│       ├── swift.yaml             # Swift rules
│       ├── kotlin.yaml            # Kotlin rules
│       └── sql.yaml               # SQL rules
└── guardrails/
    ├── callback_config.yaml
    ├── false_positive_patterns.yaml
    ├── bias_prevention.yaml
    ├── hallucination_prevention.yaml
    └── profanity_blocklist.txt
```

---

## Security Scanning Components

### 1. SAST Rules Engine

**Purpose:** Regex-based static analysis for known vulnerability patterns

**Process:**
```
Input: Combined code blob from Data Adapter
  ↓
Load language-specific SAST rules
  ↓
For each rule:
  ├─ Apply regex patterns to code
  ├─ Check allowlist exclusions
  ├─ Extract code snippets
  └─ Create finding with metadata
  ↓
Output: List of SAST findings
```

**Rule Structure:**
```yaml
- id: "PY-INJECT-EXEC-001"
  enabled: true
  title: "Use of eval/exec"
  description: "Flags eval/exec which can lead to code injection"
  category: "Injection & Unsafe Calls"
  severity: "high"
  confidence: 0.7
  cwe: ["CWE-94"]
  owasp_top_10_2021: ["a03_injection"]
  detection:
    file_globs: ["**/*.py"]
    patterns:
      - name: "eval_call"
        regex: "\\beval\\s*\\("
    allowlist_patterns:
      - name: "safe_context"
        regex: "# safe-eval-context"
  remediation:
    recommendation: "Avoid eval/exec on untrusted input"
```

**Scanning Algorithm:**
```
function apply_sast_rules(code, rules):
    findings = []
    
    for rule in rules where rule.enabled:
        for pattern in rule.detection.patterns:
            matches = regex_find_all(pattern.regex, code)
            
            for match in matches:
                snippet = extract_snippet(match)
                line_number = calculate_line(match.position)
                
                # Check allowlist
                if any_allowlist_match(snippet, rule.allowlist_patterns):
                    continue  # Skip false positive
                
                finding = {
                    rule_id: rule.id,
                    title: rule.title,
                    severity: rule.severity,
                    confidence: rule.confidence,
                    line_number: line_number,
                    code_snippet: snippet,
                    category: rule.category,
                    cwe: rule.cwe,
                    owasp: rule.owasp_top_10_2021
                }
                
                findings.append(finding)
    
    return findings
```

### 2. OWASP Top 10 Analysis

**Coverage:**

| OWASP Category | Detection Method | Function |
|----------------|------------------|----------|
| A01: Broken Access Control | Route/endpoint pattern matching, command injection detection | `_scan_access_control()` |
| A02: Cryptographic Failures | Hardcoded secrets, weak hashing (MD5), TLS verification disabled | `_scan_data_exposure()` |
| A03: Injection | SQL/NoSQL injection patterns, XSS, command injection | `_scan_injection_vulnerabilities()` |
| A04: Insecure Design | (Limited heuristics - future enhancement) | N/A |
| A05: Security Misconfiguration | Debug mode enabled, CORS misconfiguration | `_scan_security_config()` |
| A06: Vulnerable Components | Version string analysis (basic) | `_scan_vulnerable_components()` |
| A07: Auth Failures | Hardcoded credentials, JWT verification disabled | `_scan_authentication_issues()` |
| A08: Data Integrity Failures | Unsafe deserialization (pickle, YAML) | `_scan_deserialization()` |
| A09: Logging Failures | Missing security event logging | `_scan_logging_issues()` |
| A10: SSRF | Unvalidated URL fetching | Included in injection checks |

**Example: Injection Detection Flow**
```
function scan_injection_vulnerabilities(code):
    vulnerabilities = []
    
    # SQL Injection patterns
    patterns = [
        (r"\.execute\(\s*f[\"'].*SELECT", "SQL injection via f-string", "critical"),
        (r"cursor\.execute\([^)]*\+[^)]*\)", "SQL injection via concatenation", "critical")
    ]
    
    for (pattern, description, severity) in patterns:
        matches = find_all_regex(pattern, code)
        
        for match in matches:
            vulnerability = {
                type: "injection_vulnerability",
                subtype: "sql_injection",
                title: "Potential SQL Injection",
                description: description,
                severity: severity,
                line: calculate_line_number(match),
                code_snippet: extract_snippet(match),
                cwe: ["CWE-89"],
                owasp: ["a03_injection"]
            }
            vulnerabilities.append(vulnerability)
    
    return vulnerabilities
```

### 3. Risk Assessment

**Risk Scoring Algorithm:**
```
function assess_security_risk(vulnerabilities):
    # Count by severity
    counts = {critical: 0, high: 0, medium: 0, low: 0}
    
    for vuln in vulnerabilities:
        severity = vuln.severity
        counts[severity] += 1
    
    # Weighted risk score
    risk_score = (
        counts.critical * 5 +
        counts.high * 3 +
        counts.medium * 2 +
        counts.low * 1
    )
    
    # Determine risk level
    if risk_score >= 15:
        risk_level = "critical"
    elif risk_score >= 8:
        risk_level = "high"
    elif risk_score >= 3:
        risk_level = "medium"
    else:
        risk_level = "low"
    
    # Generate security grade
    if risk_score == 0:
        grade = "A"
    elif risk_score <= 2:
        grade = "B"
    elif risk_score <= 5:
        grade = "C"
    elif risk_score <= 10:
        grade = "D"
    else:
        grade = "F"
    
    return {
        overall_risk_level: risk_level,
        risk_score: risk_score,
        security_grade: grade,
        by_severity: counts
    }
```

---

## Execution Flow

### End-to-End Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Security Analysis Lifecycle                     │
└─────────────────────────────────────────────────────────────────────┘

1. INITIALIZATION PHASE
   ┌──────────────────────────────────────────┐
   │ Orchestrator starts Analysis Pipeline    │
   │  - before_agent_callback triggers        │
   │  - Loads security knowledge bases:       │
   │    • security_guidelines.yaml            │
   │  - Prepares session state                │
   └──────────────┬───────────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────────┐
   │ Security Agent receives control          │
   │  State contains:                         │
   │   - code: combined code blob             │
   │   - language: detected language(s)       │
   │   - file_path: list of files             │
   │   - files: file metadata                 │
   │   - security_guidelines: loaded KB       │
   └──────────────┬───────────────────────────┘
                  │
                  ▼

2. PRE-MODEL CALLBACK
   ┌──────────────────────────────────────────┐
   │ before_model_callback                    │
   │  - Injects security analysis constraints │
   │  - Adds context about OWASP Top 10       │
   │  - Sets response format expectations     │
   └──────────────┬───────────────────────────┘
                  │
                  ▼

3. TOOL EXECUTION
   ┌──────────────────────────────────────────┐
   │ LLM decides to call tool:                │
   │ scan_security_vulnerabilities()          │
   └──────────────┬───────────────────────────┘
                  │
                  ▼
   ┌──────────────────────────────────────────────────────────┐
   │ security_vulnerability_scanner.py                         │
   │                                                            │
   │  A. Load SAST Rules                                       │
   │     ├─ Detect languages from state                       │
   │     ├─ Load generic.yaml (cross-language)                │
   │     └─ Load language-specific rules                      │
   │        (python.yaml, typescript.yaml, etc.)              │
   │                                                            │
   │  B. Run SAST Analysis                                    │
   │     ├─ Apply regex patterns from rules                   │
   │     ├─ Check allowlist exclusions                        │
   │     └─ Collect findings with metadata                    │
   │                                                            │
   │  C. Run OWASP Heuristics                                 │
   │     ├─ _scan_injection_vulnerabilities()                 │
   │     ├─ _scan_authentication_issues()                     │
   │     ├─ _scan_data_exposure()                             │
   │     ├─ _scan_xxe_vulnerabilities()                       │
   │     ├─ _scan_access_control()                            │
   │     ├─ _scan_security_config()                           │
   │     ├─ _scan_xss_vulnerabilities()                       │
   │     ├─ _scan_deserialization()                           │
   │     ├─ _scan_vulnerable_components()                     │
   │     └─ _scan_logging_issues()                            │
   │                                                            │
   │  D. Aggregate Results                                    │
   │     ├─ Combine SAST + OWASP findings                     │
   │     ├─ Count by severity                                 │
   │     └─ Generate summary                                  │
   │                                                            │
   │  E. Risk Assessment                                      │
   │     ├─ Calculate risk score                              │
   │     ├─ Determine risk level                              │
   │     ├─ Assign security grade                             │
   │     └─ Generate recommendations                          │
   │                                                            │
   │  F. Return Tool Response                                 │
   │     └─ JSON object with all findings                     │
   └──────────────┬───────────────────────────────────────────┘
                  │
                  ▼

4. POST-TOOL CALLBACK
   ┌──────────────────────────────────────────────────────────┐
   │ after_tool_callback                                       │
   │                                                            │
   │  A. Normalize Tool Response                              │
   │     └─ Ensure consistent field names/types               │
   │                                                            │
   │  B. Filter False Positives                               │
   │     ├─ Load false_positive_patterns.yaml                 │
   │     ├─ Check each finding against patterns               │
   │     └─ Remove matches (e.g., test files, comments)       │
   │                                                            │
   │  C. Compute Confidence Scores                            │
   │     ├─ Adjust based on code context                      │
   │     ├─ Lower confidence for heuristic findings           │
   │  D. Enrich Findings                                      │
   │     ├─ Attach security guidelines from KB               │
   │     ├─ Map CWE to OWASP categories                      │
   │     ├─ Add category-specific rules                      │
   │     └─ Include remediation references                    │
   │     ├─ Add remediation references                        │
   │     └─ Include CWE/OWASP mappings                        │
   │                                                            │
   │  E. Update Tool Response                                 │
   │     └─ Return enhanced findings to LLM                   │
   └──────────────┬───────────────────────────────────────────┘
                  │
                  ▼

5. LLM ANALYSIS
   ┌──────────────────────────────────────────┐
   │ LLM (granite4:latest) analyzes findings  │
   │  - Interprets tool results               │
   │  - Generates human-readable report       │
   │  - Adds context and recommendations      │
   │  - Produces markdown with YAML metadata  │
   └──────────────┬───────────────────────────┘
                  │
                  ▼

6. POST-AGENT CALLBACK
   ┌──────────────────────────────────────────────────────────┐
   │ after_agent_callback                                      │
   │                                                            │
   │  A. Parse Output                                         │
   │     ├─ Extract YAML frontmatter                          │
   │     └─ Extract markdown body                             │
   │                                                            │
   │  B. Validate CVEs (if mentioned)                         │
   │     ├─ Extract CVE IDs (CVE-YYYY-NNNNN)                  │
   │     ├─ Check existence via NVD API                       │
   │     └─ Remove hallucinated CVEs                          │
   │                                                            │
   │  C. Filter Bias & Profanity                              │
   │     ├─ Load bias_prevention.yaml                         │
   │     ├─ Load profanity_blocklist.txt                      │
   │     └─ Replace problematic terms with [filtered]         │
   │                                                            │
   │  D. Validate Metadata (Optional)                         │
   │     ├─ Check for required fields                         │
   │     └─ Log informational messages                        │
   │                                                            │
   │  E. Reconstruct Clean Output                             │
   │     └─ Combine filtered YAML + markdown                  │
   └──────────────┬───────────────────────────────────────────┘
                  │
                  ▼

7. OUTPUT CAPTURE
   ┌──────────────────────────────────────────┐
   │ ADK output_key mechanism                 │
   │  - Captures agent text output            │
   │  - Stores in session state:              │
   │    state["security_analysis"]            │
   └──────────────┬───────────────────────────┘
                  │
                  ▼

8. ARTIFACT SAVING
   ┌──────────────────────────────────────────┐
   │ Artifact Saver Agent                     │
   │  - Reads state["security_analysis"]      │
   │  - Saves to:                             │
   │    • ADK artifact service                │
   │    • Local disk (storage_bucket/)        │
   │    • Session database                    │
   └──────────────────────────────────────────┘
```

### Timing & Performance

```
Typical execution times (2 files, 1149 lines):
┌──────────────────────────────────────┬──────────┐
│ Phase                                │ Duration │
├──────────────────────────────────────┼──────────┤
│ Tool execution (SAST + OWASP)        │ 4-5s     │
│ LLM analysis generation              │ 10-15s   │
│ Callback processing                  │ <1s      │
│ Total                                │ 15-20s   │
└──────────────────────────────────────┴──────────┘
```

---

## Guardrails & Validation

### Three-Layer Guardrail System

```
┌───────────────────────────────────────────────────────────────┐
│                  Guardrail Architecture                       │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  Layer 1: BEFORE MODEL                                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • Inject security analysis constraints               │    │
│  │ • Set response format expectations                   │    │
│  │ • Add OWASP Top 10 context                          │    │
│  └─────────────────────────────────────────────────────┘    │
│                          ↓                                    │
│  Layer 2: AFTER TOOL                                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • Normalize tool response structure                  │    │
│  │ • Filter false positives (pattern matching)          │    │
│  │ • Compute confidence scores                          │    │
│  │ • Enrich findings with guidelines                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                          ↓                                    │
│  Layer 3: AFTER AGENT                                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ • Validate CVE IDs (API check)                       │    │
│  │ • Filter bias and profanity                          │    │
│  │ • Validate output structure                          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                                │
└───────────────────────────────────────────────────────────────┘
```

### False Positive Filtering

**Configuration:** `config/guardrails/false_positive_patterns.yaml`

**Filtering Logic:**
```
function filter_false_positives(findings, patterns_config):
    filtered = []
    removed_count = 0
    
    for finding in findings:
        should_keep = true
        
        # Check each false positive pattern
        for pattern in patterns_config.security_scan_filters:
            if matches_false_positive(finding, pattern):
                should_keep = false
                removed_count += 1
                break
        
        if should_keep:
            filtered.append(finding)
    
    log_info(f"Filtered {removed_count} false positives")
    return filtered

function matches_false_positive(finding, pattern):
    # Check file path patterns
    if pattern.file_path_regex:
        if regex_match(pattern.file_path_regex, finding.file_path):
            return true
    
    # Check code snippet patterns
    if pattern.code_pattern:
        if pattern.code_pattern in finding.code_snippet:
            return true
    
    # Check category exclusions
    if pattern.exclude_categories:
        if finding.category in pattern.exclude_categories:
            return true
    
    return false
```

### CVE Validation

**Purpose:** Prevent hallucinated CVE references

**Process:**
```
function validate_cve_ids(text, max_checks=10):
    # Extract CVE patterns
    cve_pattern = r'CVE-\d{4}-\d{4,7}'
    cve_ids = regex_find_all(cve_pattern, text)
    
    invalid_cves = []
    
    for cve_id in cve_ids[:max_checks]:
        # Check via NVD API
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
        
        try:
            response = http_get(url, timeout=5)
            
            if response.status_code == 404:
                invalid_cves.append(cve_id)
                log_warning(f"Invalid CVE detected: {cve_id}")
        except:
            log_error(f"CVE validation failed for {cve_id}")
    
    # Remove invalid CVEs from text
    cleaned_text = text
    for invalid_cve in invalid_cves:
        cleaned_text = replace(
            cleaned_text,
            invalid_cve,
            f"[INVALID CVE: {invalid_cve}]"
        )
    
    return cleaned_text, invalid_cves
```

---

## SAST Rules Engine

### Rule Loading Strategy

```
function load_sast_rules(languages_detected):
    rules = []
    
    # 1. Always load generic rules (cross-language)
    generic_rules = load_yaml("sast_rules/generic.yaml")
    rules.extend(generic_rules)
    
    # 2. Load language-specific rules
    for language in languages_detected:
        if language == "multi":
            continue  # Skip multi-language marker
        
        rule_file = f"sast_rules/{language}.yaml"
        if file_exists(rule_file):
            lang_rules = load_yaml(rule_file)
            rules.extend(lang_rules)
    
    # 3. Filter enabled rules
    enabled_rules = [r for r in rules if r.enabled]
    
    log_info(f"Loaded {len(enabled_rules)} enabled SAST rules")
    return enabled_rules
```

### Language Priority

When multiple languages detected:
1. Python (highest priority for backend security)
2. TypeScript/JavaScript (high priority for web)
3. Go (high priority for services)
4. C++/C (high priority for systems)
5. Java/Kotlin (medium priority)
6. Others (standard priority)

### Rule Categories

| Category | Description | Example Rules |
|----------|-------------|---------------|
| Injection & Unsafe Calls | SQL injection, command injection, code execution | eval/exec usage, shell=True, string interpolation in queries |
| Secrets Management | Hardcoded credentials, API keys, tokens | api_key=, password=, private_key= |
| Authentication & Authorization | Weak auth, broken session management | JWT verify=False, hardcoded passwords |
| Data Protection | Sensitive data exposure, weak crypto | TLS verify disabled, MD5 hashing |
| Error Handling & Logging | Insufficient logging, information disclosure | Secrets in logs, missing security logs |
| Input Validation & Sanitization | Missing validation, unsafe deserialization | Pickle.loads, YAML.load (unsafe) |

---

## OWASP Top 10 Analysis

### Detection Heuristics

#### A03: Injection Vulnerabilities

**SQL Injection Detection:**
```
Patterns:
  1. f-string in execute()
     Pattern: \.execute\(\s*f["'].*\b(SELECT|INSERT|UPDATE|DELETE)\b
     Example: cursor.execute(f"SELECT * FROM users WHERE id={user_id}")
     
  2. String concatenation in execute()
     Pattern: cursor\.execute\([^)]*\+[^)]*\)
     Example: cursor.execute("SELECT * FROM " + table_name)
     
  3. .format() in SQL
     Pattern: \.execute\(.*\.format\(
     Example: cursor.execute("SELECT {}".format(user_input))

Allowlist (safe patterns):
  - Parameterized queries: cursor.execute("SELECT * WHERE id=%s", (id,))
  - SQLAlchemy text with params: text("SELECT * WHERE id=:id")
```

**Command Injection Detection:**
```
Patterns:
  1. subprocess with shell=True
     Pattern: subprocess\.(run|Popen|call).*shell\s*=\s*True
     
  2. os.system() usage
     Pattern: \bos\.system\s*\(
     
  3. User input in commands
     Pattern: subprocess\.\w+\([^)]*user

Risk Level: CRITICAL
```

#### A07: Authentication Failures

**Detection Patterns:**
```
1. Hardcoded Passwords
   Pattern: password\s*==\s*["'][^"']+["']
   Risk: Credentials in source code
   
2. JWT Verification Disabled
   Pattern: jwt\.decode\([^,]*,\s*verify\s*=\s*False
   Risk: Forged tokens accepted
   
3. Weak Hashing
   Pattern: \bmd5\s*\([^)]*password
   Risk: Passwords easily cracked
```

#### A09: Security Logging Failures

**Improved Heuristic (Post-Fix):**
```
function scan_logging_issues(code):
    # Check for ACTUAL auth code patterns (not just keywords)
    auth_patterns = [
        r"\bdef\s+\w*(login|authenticate|verify_token)\s*\(",
        r"@\w*\.route\([^)]*\/(login|auth|token)",
        r"\bjwt\.(encode|decode)\s*\(",
        r"\.verify_password\s*\(",
        r"@(login_required|authenticated)"
    ]
    
    has_auth_code = any(pattern_found(p, code) for p in auth_patterns)
    
    # Check for security logging
    has_security_logging = pattern_found(
        r"\b(log|logger)\.\w+\([^)]*(security|auth|login|failed|denied)[^)]*\)",
        code
    )
    
    # Only flag if ACTUAL auth code exists without logging
    if has_auth_code and not has_security_logging:
        return [create_logging_warning()]
    
    return []
```

---

## Output Format

### YAML Frontmatter Structure

```yaml
---
agent: security_agent
summary: "Brief summary of security findings"
total_issues: 3
severity:
  critical: 0
  high: 1
  medium: 2
  low: 0
confidence: 0.85
---
```

### Markdown Body Structure

```markdown
# Security Analysis

## Executive Summary
Brief overview of security posture

## Critical Issues
(If any)
### 1. [Issue Title]
**Severity:** Critical
**Location:** file.py, line 45
**CWE:** CWE-89
**OWASP:** A03:2021 - Injection

**Description:**
[Detailed explanation]

**Evidence:**
```code snippet```

**Recommendation:**
[Fix guidance]

---

## High Severity Issues
[Similar structure]

## Medium Severity Issues
[Similar structure]

## Risk Assessment
- Overall Risk Level: Medium
- Risk Score: 5
- Security Grade: C

## Compliance Check
[Compliance analysis]

## Recommendations
1. [Priority recommendation]
2. [Secondary recommendation]
```

### Complete Tool Response Schema

```json
{
  "status": "success",
  "tool_name": "scan_security_vulnerabilities",
  "file_path": "path/to/file.py",
  "language": "python",
  "languages_detected": ["python", "typescript"],
  "analysis_type": "security_vulnerability_scan",
  
  "sast_rules": {
    "rules_loaded": 15,
    "files_loaded": ["generic.yaml", "python.yaml"],
    "warnings": [],
    "findings": [
      {
        "rule_id": "PY-INJECT-EXEC-001",
        "title": "Use of eval/exec",
        "description": "...",
        "category": "Injection & Unsafe Calls",
        "severity": "high",
        "confidence": 0.7,
        "line_number": 45,
        "code_snippet": "eval(user_input)",
        "cwe": ["CWE-94"],
        "owasp_top_10_2021": ["a03_injection"],
        "file_path": "utils/parser.py"
      }
    ]
  },
  
  "owasp_top_10_analysis": {
    "injection_vulnerabilities": [...],
    "broken_authentication": [...],
    "sensitive_data_exposure": [...],
    "xml_external_entities": [...],
    "broken_access_control": [...],
    "security_misconfiguration": [...],
    "cross_site_scripting": [...],
    "insecure_deserialization": [...],
    "vulnerable_components": [...],
    "insufficient_logging": [...]
  },
  
  "vulnerability_summary": {
    "total_vulnerabilities": 3,
    "critical_vulnerabilities": 0,
    "high_vulnerabilities": 1,
    "medium_vulnerabilities": 2,
    "low_vulnerabilities": 0
  },
  
  "risk_assessment": {
    "overall_risk_level": "medium",
    "risk_score": 5,
    "security_grade": "C",
    "risk_factors": {
      "by_severity": {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 0
      }
    }
  },
  
  "compliance_check": {
    "owasp_top_10_coverage": true,
    "critical_violations": 0,
    "high_violations": 1
  },
  
  "recommendations": [
    "Use parameterized queries instead of string interpolation",
    "Enable security event logging for authentication flows"
  ],
  
  "timestamp": 1702761234.567,
  "execution_time_seconds": 4.123
}
```

---
## Configuration

### Security Guidelines (Knowledge Base)

**File:** `config/knowledge_base/security_guidelines.yaml`

**Purpose:** Central repository of security best practices, OWASP Top 10 mappings, and category-specific rules. Loaded at pipeline initialization and used for:
- Enriching vulnerability findings with actionable guidance
- Mapping CWE IDs to OWASP categories
- Providing category-specific remediation rules
- Informing LLM analysis with security context

**Structure:**

```yaml
version: "1.0"
title: "Security Review Guidelines"
scope: "application_code_review"

# 7 Security Categories with Rules
categories:
  - name: "Input Validation & Sanitization"
    rules:
      - "Validate all external inputs"
      - "Prefer allow-lists over block-lists"
      
  - name: "Authentication & Authorization"
    rules:
      - "Use established password hashing libraries"
      - "Validate identity on all protected endpoints"
      
  - name: "Secrets Management"
    rules:
      - "Never hard-code secrets"
      - "Use environment variables or secret managers"
      
  - name: "Data Protection"
    rules:
      - "Encrypt sensitive data at rest and in transit"
      - "Don't leak internal details in errors"
      
  - name: "Injection & Unsafe Calls"
    rules:
      - "Use parameterized queries"
      - "Avoid eval/exec on untrusted data"
      
  - name: "Dependencies & Libraries"
    rules:
      - "Use trusted, maintained libraries"
      - "Keep security checks enabled"
      
  - name: "Error Handling & Logging"
    rules:
      - "Don't expose sensitive data in errors"
      - "Log security events with context"

# OWASP Top 10 2021 Mapping
owasp_top_10_2021:
  a01_broken_access_control:
    rules:
      - "Verify authorization for every protected resource"
      - "Deny by default; explicit allow-lists only"
    cwe: ["CWE-22", "CWE-284", "CWE-639"]
  
  a02_cryptographic_failures:
    rules:
      - "Use TLS 1.2+ for all network communication"
      - "Never implement custom encryption"
    cwe: ["CWE-327", "CWE-328"]
  
  a03_injection:
    rules:
      - "Use parameterized queries (prevents CWE-89)"
      - "Escape user data in shell commands (prevents CWE-78)"
      - "Use template engines with auto-escaping (prevents CWE-79)"
    cwe: ["CWE-79", "CWE-89", "CWE-78"]
  # ... more OWASP categories

# Additional Security Practices
security_testing:
  - "Run SAST on every commit"
  - "Dependency scanning for known CVEs"
  - "Secret scanning in commits and logs"

web_security:
  cors:
    - "Restrict CORS origins to known domains"
  csrf:
    - "Use CSRF tokens for state-changing operations"
  clickjacking:
    - "Set X-Frame-Options: DENY or SAMEORIGIN"

rate_limiting:
  - "Implement rate limiting on authentication endpoints"
  - "Limit API requests per user/IP"
```

**Usage Flow:**

```
Orchestrator before_agent_callback
  ↓
Load security_guidelines.yaml via knowledge_base_loader
  ↓
Store in session state["security_guidelines"]
  ↓
Security Agent after_tool_callback
  ↓
Enrich findings with guidelines:
  ├─ Map finding.cwe → OWASP category
  ├─ Attach category-specific rules
  └─ Add guideline references to finding
  ↓
Enhanced findings passed to LLM
  ↓
LLM generates report with enriched context
```

**Enrichment Function:**

```python
# util/security_enrichment.py
function attach_guideline_refs(finding, security_guidelines):
    # 1. Build CWE → OWASP mapping
    cwe_to_owasp = build_cwe_mapping(security_guidelines)
    
    # 2. Map finding's CWEs to OWASP categories
    finding_cwes = finding.get("cwe", [])
    for cwe in finding_cwes:
        if cwe in cwe_to_owasp:
            owasp_cats = cwe_to_owasp[cwe]
            finding["owasp_guidelines"] = owasp_cats
    
    # 3. Attach category-specific rules
    category = finding.get("category")
    if category in category_rules:
        finding["category_rules"] = category_rules[category]
    
    return finding
```

### SAST Rule Configuration

**File:** `config/knowledge_base/security_controls/sast_rules/generic.yaml`

**Key Improvements (Dec 2025):**

```yaml
# IMPROVED: GEN-LOG-SECRET-001
- id: "GEN-LOG-SECRET-001"
  title: "Potential secret in logs"
  description: "Detects logging of actual secret values (long alphanumeric strings)"
  
  # OLD (too broad):
  # regex: "\\b(log|logger\\.)\\w*\\(.*(token|secret|password).*\\)"
  
  # NEW (more precise):
  patterns:
    - name: "log_secret_value"
      regex: "(?i)\\b(log|logger\\.)\\w*\\([^)]*\\b(token|secret|password)\\s*[=:,]\\s*['\"]?[A-Za-z0-9_\\-\\+/=]{16,}['\"]?"
      description: "Logs actual secret value (not just variable name)"
  
  allowlist_patterns:
    - name: "metric_counters"
      regex: "(?i)\\b(token|secret|key)[s]?_(saved|count|length|size)"
      description: "Exclude metrics like tokens_saved, token_count"
    
    - name: "redaction_keywords"
      regex: "(?i)(redact|masked|sanitize)"
```

### False Positive Patterns

**File:** `config/guardrails/false_positive_patterns.yaml`

```yaml
security_scan_filters:
  - name: "test_files"
    description: "Exclude test files from security warnings"
    file_path_regex: "^(test_|tests/|.*_test\\.py)"
    
  - name: "example_code"
    description: "Exclude documented examples"
    code_pattern: "# Example:"
    
  - name: "safe_sql_params"
    description: "Parameterized queries are safe"
    code_pattern: "execute.*%s.*,\\s*\\("
```

---

## Error Handling

### Error Categories & Recovery

```
┌──────────────────────────────────────────────────────────┐
│                  Error Handling Strategy                  │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  1. SAST Rules Loading Errors                            │
│     ├─ Missing rule file → Log warning, continue         │
│     ├─ Invalid YAML → Skip rule, load others             │
│     └─ No rules loaded → Return empty findings           │
│                                                            │
│  2. Pattern Matching Errors                              │
│     ├─ Invalid regex → Skip pattern, log error           │
│     ├─ Timeout → Limit processing time per pattern       │
│     └─ Memory limit → Process in chunks                  │
│                                                            │
│  3. Tool Execution Errors                                │
│     ├─ No code provided → Return error response          │
│     ├─ Language detection fails → Use generic rules      │
│     └─ Parsing error → Return partial results            │
│                                                            │
│  4. Guardrail Callback Errors                            │
│     ├─ CVE API timeout → Skip validation, log warning    │
│     ├─ False positive filter fails → Use raw results     │
│     └─ Confidence computation error → Use default 0.5    │
│                                                            │
│  5. Output Formatting Errors                             │
│     ├─ YAML parse failure → Use markdown only            │
│     ├─ Missing metadata → Provide defaults               │
│     └─ Validation errors → Log as INFO, not WARNING      │
│                                                            │
└──────────────────────────────────────────────────────────┘
```

### Graceful Degradation

```
Priority Levels (from most to least critical):
  1. Core scanning functionality (SAST + OWASP)
  2. Risk assessment and scoring
  3. Output formatting and metadata
  4. Guardrail callbacks (nice-to-have)
  5. CVE validation (informational only)

Degradation Strategy:
  - Always return SOME result (even if empty findings)
  - Partial results better than complete failure
  - Log errors but don't block pipeline
  - Provide default values for missing data
```

---

## Future Enhancements

### Planned Improvements

1. **Per-File Analysis**
   - Currently scans combined code blob
   - Future: Individual file attribution for better context

2. **Dataflow Analysis**
   - Track variable flow from source to sink
   - Detect taint propagation for injections

3. **AI-Powered Detection**
   - Use LLM for semantic vulnerability detection
   - Complement regex-based SAST rules

4. **Custom Rule Support**
   - Allow users to define project-specific rules
   - Organization-level security policies

5. **Integration with SCA**
   - Software Composition Analysis for dependencies
   - Automated CVE scanning for libraries

6. **Remediation Automation**
   - Generate fix suggestions
   - Auto-PR for simple security issues

---

## References

### Internal Documentation
- `docs/CALLBACKS_GUARDRAILS_DESIGN.md` - Guardrails architecture
- `docs/SIMPLIFIED_SEQUENTIAL_PIPELINE_DESIGN.md` - Pipeline flow
- `docs/OUTPUT_FORMAT_SPECIFICATION.md` - Output standards

### External Standards
- OWASP Top 10 2021: https://owasp.org/Top10/
- CWE Common Weakness Enumeration: https://cwe.mitre.org/
- NIST NVD API: https://nvd.nist.gov/developers

### Tool Dependencies
- Google ADK (Agent Development Kit)
- YAML parsing: PyYAML
- Regex engine: Python re module
- HTTP client: requests (for CVE validation)

---

**Document Version:** 1.0  
**Last Updated:** December 16, 2025  
**Maintained By:** Security Agent Team
