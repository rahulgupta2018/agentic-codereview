from __future__ import annotations

from typing import Any, Dict, List, Tuple
import re


SEVERITY_ORDER = ["low", "medium", "high", "critical"]


def clamp(x: float, lo: float = 0.05, hi: float = 0.98) -> float:
    return max(lo, min(hi, x))


def downgrade_severity(sev: str, steps: int = 1) -> str:
    sev = (sev or "low").lower()
    if sev not in SEVERITY_ORDER:
        sev = "low"
    idx = SEVERITY_ORDER.index(sev)
    idx = max(0, idx - steps)
    return SEVERITY_ORDER[idx]


def normalize_cwe(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value.strip()]
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [str(value).strip()]


def compute_confidence(finding: Dict[str, Any]) -> float:
    """
    Deterministic confidence scoring based on evidence presence.
    """
    base = finding.get("confidence", None)
    if isinstance(base, (int, float)):
        conf = float(base)
    else:
        # default confidence if not present (OWASP heuristic findings tend to be noisier)
        conf = 0.55

    # evidence boosts
    if finding.get("file_path"):
        conf += 0.10
    if finding.get("line"):
        conf += 0.10
    if finding.get("code_snippet") or finding.get("evidence"):
        conf += 0.10

    # penalties for weak evidence patterns
    evidence = (finding.get("evidence") or finding.get("code_snippet") or "").lower()
    if finding.get("line") == 1 and "no security logging detected" in evidence:
        conf -= 0.15

    # penalty if it looks like a generic pattern match without context
    if len(evidence.strip()) < 8 and not finding.get("code_snippet"):
        conf -= 0.10

    return clamp(conf)


def adjust_severity_by_confidence(severity: str, confidence: float) -> str:
    """
    If confidence is low, severity should not be extreme.
    """
    sev = (severity or "low").lower()
    if sev not in SEVERITY_ORDER:
        sev = "low"

    if confidence < 0.25:
        return downgrade_severity(sev, 2)
    if confidence < 0.45 and sev in ("critical", "high"):
        return downgrade_severity(sev, 1)
    return sev


def build_guideline_maps(security_guidelines: Dict[str, Any]) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Returns:
      - category_rules: {category_name: [rules...]}
      - cwe_to_owasp: {CWE-xxx: [owasp_id...]}
    """
    category_rules: Dict[str, List[str]] = {}
    for cat in (security_guidelines or {}).get("categories", []) or []:
        name = cat.get("name")
        rules = cat.get("rules", []) or []
        if name:
            category_rules[name] = [str(r) for r in rules]

    cwe_to_owasp: Dict[str, List[str]] = {}
    owasp = (security_guidelines or {}).get("owasp_top_10_2021", {}) or {}
    for owasp_id, block in owasp.items():
        for cwe in (block or {}).get("cwe", []) or []:
            cwe_to_owasp.setdefault(str(cwe), []).append(str(owasp_id))

    return category_rules, cwe_to_owasp


def infer_category_from_text(text: str) -> str | None:
    """
    Very small, explicit fallback mapping (keep it deterministic).
    """
    t = (text or "").lower()
    if any(k in t for k in ["sql injection", "command injection", "xss", "ssrf", "deserialization", "eval(", "exec("]):
        return "Injection & Unsafe Calls"
    if any(k in t for k in ["api key", "apikey", "secret", "token", "password", "private_key"]):
        return "Secrets Management"
    if any(k in t for k in ["cors", "csrf", "x-frame-options", "content-security-policy"]):
        return "Data Protection"
    if any(k in t for k in ["auth", "jwt", "session", "permission", "authorization"]):
        return "Authentication & Authorization"
    return None


def attach_guideline_refs(
    finding: Dict[str, Any],
    security_guidelines: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Adds finding["guideline_refs"] = [...]
    """
    if not security_guidelines:
        return finding

    category_rules, cwe_to_owasp = build_guideline_maps(security_guidelines)

    # Determine category
    category = finding.get("category")
    if not category:
        # try infer from title/type/subtype/message
        text = " ".join([
            str(finding.get("title", "")),
            str(finding.get("type", "")),
            str(finding.get("subtype", "")),
            str(finding.get("message", "")),
            str(finding.get("description", "")),
        ])
        category = infer_category_from_text(text)

    # Determine CWE list
    cwes = normalize_cwe(finding.get("cwe") or finding.get("cwe_id"))

    refs: List[Dict[str, Any]] = []

    # Category-based refs
    if category and category in category_rules:
        # pick top 1–2 rules to avoid noise
        for rule_text in category_rules[category][:2]:
            refs.append({
                "category": category,
                "rule": rule_text,
            })

    # CWE → OWASP refs
    for cwe in cwes[:2]:
        for owasp_id in cwe_to_owasp.get(cwe, [])[:1]:
            refs.append({
                "cwe": cwe,
                "owasp": owasp_id,
            })

    if refs:
        finding["guideline_refs"] = refs

    return finding