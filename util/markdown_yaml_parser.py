"""
Markdown + YAML Parser Utilities for Agent Output

Drop-in module for parsing, validating, normalizing, filtering, and reconstructing
agent outputs that follow a Markdown body with YAML frontmatter.

Expected format:

---
agent: security_agent
summary: ...
total_issues: 3
severity:
  critical: 0
  high: 1
  medium: 2
  low: 0
confidence: 0.85
---

# Title
...markdown...

Design goals:
- Robust frontmatter parsing (avoid false positives on '---' elsewhere)
- Graceful fallback on parse errors
- Optional type coercion (LLMs sometimes output numbers as strings)
- Reconstruction with stable delimiters/newlines
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Tuple

import yaml

logger = logging.getLogger(__name__)

# Robust YAML frontmatter matcher:
# - Allows leading whitespace/BOM-like whitespace
# - Requires opening '---' at the top and closing '---' on its own line
_FRONTMATTER_RE = re.compile(
    r"^\s*---\s*\r?\n"      # opening delimiter
    r"(?P<yaml>.*?)"        # YAML content (non-greedy)
    r"\r?\n---\s*\r?\n"     # closing delimiter
    r"(?P<body>.*)$",       # rest is markdown body
    re.DOTALL,
)


def parse_analysis(text: str) -> Tuple[Dict[str, Any], str]:
    """
    Parse Markdown+YAML analysis output.

    Args:
        text: Raw agent output with YAML frontmatter and markdown body.

    Returns:
        (metadata_dict, markdown_body_str)

    Notes:
        - If no proper frontmatter exists, returns metadata with parse_warning.
        - If YAML fails to parse, returns metadata with parse_error and best-effort body.
    """
    if text is None:
        logger.warning("⚠️ parse_analysis called with None text")
        return {"agent": "unknown", "parse_warning": "none_text"}, ""

    raw = text.strip("\ufeff")  # strip BOM if present
    m = _FRONTMATTER_RE.match(raw)

    if not m:
        logger.warning("⚠️ No YAML frontmatter found (missing proper --- blocks at top)")
        return {"agent": "unknown", "parse_warning": "no_frontmatter"}, raw.strip()

    yaml_block = m.group("yaml")
    body = (m.group("body") or "").strip()

    try:
        metadata = yaml.safe_load(yaml_block) or {}
        if not isinstance(metadata, dict):
            logger.warning("YAML frontmatter is not a dict: %s", type(metadata))
            metadata = {"agent": "unknown", "parse_warning": "yaml_not_dict"}
        return metadata, body
    except yaml.YAMLError as e:
        logger.warning("⚠️ YAML parse error: %s", e)
        metadata = {
            "agent": "unknown",
            "parse_error": str(e),
            "raw_frontmatter": yaml_block,
        }
        return metadata, body if body else raw.strip()


def parse_json_safe(text: str) -> Dict[str, Any]:
    """
    Backward compatibility: Try JSON first, fallback to Markdown+YAML.

    Returns:
        Dict parsed from JSON or YAML metadata.
        NOTE: This returns ONLY metadata for YAML (legacy behavior).
    """
    if text is None:
        logger.error("❌ parse_json_safe called with None text")
        return {}

    t = text.strip()

    if t.startswith("{"):
        try:
            parsed = json.loads(t)
            if isinstance(parsed, dict):
                return parsed
            logger.warning("⚠️ JSON parsed but not a dict (got %s)", type(parsed))
            return {"parse_warning": "json_not_dict"}
        except json.JSONDecodeError as e:
            logger.warning("⚠️ JSON parse failed: %s", e)

    metadata, _ = parse_analysis(t)
    if "parse_error" not in metadata and metadata:
        return metadata

    logger.error("❌ Failed to parse as JSON or Markdown+YAML")
    return {}


def _coerce_int(value: Any) -> Tuple[Any, bool]:
    if isinstance(value, int):
        return value, True
    if isinstance(value, str):
        s = value.strip()
        if re.fullmatch(r"\d+", s):
            return int(s), True
        if re.fullmatch(r"\d+\.0+", s):
            return int(float(s)), True
    return value, False


def _coerce_float(value: Any) -> Tuple[Any, bool]:
    if isinstance(value, (int, float)):
        return float(value), True
    if isinstance(value, str):
        s = value.strip()
        try:
            return float(s), True
        except ValueError:
            return value, False
    return value, False


def normalize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize common LLM output quirks (numbers as strings).
    Returns the same dict instance for convenience.
    """
    if not isinstance(metadata, dict):
        return {"agent": "unknown", "parse_warning": "metadata_not_dict"}

    if "confidence" in metadata:
        v, ok = _coerce_float(metadata["confidence"])
        if ok:
            metadata["confidence"] = v

    if "total_issues" in metadata:
        v, ok = _coerce_int(metadata["total_issues"])
        if ok:
            metadata["total_issues"] = v

    return metadata


def validate_analysis(
    metadata: Dict[str, Any],
    markdown_body: str,
    agent_name: str | None = None,
    *,
    coerce_types: bool = True,
) -> List[str]:
    """
    Validate analysis output has required fields and proper structure.

    Args:
        metadata: Parsed YAML frontmatter dict
        markdown_body: Markdown content
        agent_name: Expected agent name (optional)
        coerce_types: If True, attempts to coerce numeric strings

    Returns:
        List[str] validation errors (empty if valid)
    """
    errors: List[str] = []

    if coerce_types:
        metadata = normalize_metadata(metadata)

    if isinstance(metadata, dict) and "parse_error" in metadata:
        errors.append(f"YAML parsing failed: {metadata['parse_error']}")
        return errors

    if not isinstance(metadata, dict):
        errors.append(f"Metadata must be a dict, got {type(metadata).__name__}")
        return errors

    required_fields = ["agent", "summary", "total_issues", "confidence"]
    for field in required_fields:
        if field not in metadata:
            errors.append(f"Missing required metadata field: {field}")

    if agent_name and metadata.get("agent") != agent_name:
        errors.append(
            f"Agent mismatch: expected '{agent_name}', got '{metadata.get('agent')}'"
        )

    if "confidence" in metadata:
        conf = metadata["confidence"]
        if not isinstance(conf, (int, float)):
            errors.append(f"Confidence must be numeric, got {type(conf).__name__}")
        else:
            conf_f = float(conf)
            if not (0.0 <= conf_f <= 1.0):
                errors.append(f"Confidence {conf_f} outside valid range [0.0, 1.0]")

    if "total_issues" in metadata:
        issues = metadata["total_issues"]
        if not isinstance(issues, int):
            errors.append(f"total_issues must be integer, got {type(issues).__name__}")
        elif issues < 0:
            errors.append(f"total_issues cannot be negative: {issues}")

    body = (markdown_body or "").strip()
    if not body:
        errors.append("Empty markdown body")
    else:
        # Accept any heading level
        if not re.search(r"^\s*#{1,6}\s+\S", body, flags=re.MULTILINE):
            errors.append("Missing a markdown heading")

    return errors


def reconstruct_analysis(metadata: Dict[str, Any], markdown_body: str) -> str:
    """
    Reconstruct Markdown+YAML output after modifications.

    - Removes internal parse fields
    - Ensures correct delimiter formatting
    - Ensures trailing newline
    """
    if not isinstance(metadata, dict):
        metadata = {"agent": "unknown", "parse_warning": "metadata_not_dict"}

    clean_metadata = {
        k: v
        for k, v in metadata.items()
        if k not in ("parse_error", "parse_warning", "raw_frontmatter")
    }

    yaml_str = yaml.safe_dump(
        clean_metadata,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    ).rstrip() + "\n"

    body = (markdown_body or "").strip()

    return f"---\n{yaml_str}---\n\n{body}\n"


def filter_content(markdown_body: str, patterns: List[Tuple[str, str]]) -> Tuple[str, int]:
    """
    Filter markdown content using regex patterns.

    Args:
        markdown_body: Markdown text to filter
        patterns: List of (pattern, replacement) tuples

    Returns:
        (filtered_text, num_replacements)
    """
    filtered = markdown_body or ""
    total_replacements = 0

    for pattern, replacement in patterns:
        filtered, count = re.subn(pattern, replacement, filtered, flags=re.IGNORECASE)
        total_replacements += count

    return filtered, total_replacements


def extract_confidence_scores(markdown_body: str) -> List[float]:
    """
    Extract confidence scores from markdown headings.

    Looks for: "(Confidence: 0.85)" and accepts 0..1 inclusive.
    """
    body = markdown_body or ""
    pattern = r"\(Confidence:\s*(0(?:\.\d+)?|1(?:\.0+)?)\)"
    matches = re.findall(pattern, body)

    scores: List[float] = []
    for match in matches:
        try:
            score = float(match)
            if 0.0 <= score <= 1.0:
                scores.append(score)
        except ValueError:
            continue

    return scores


def update_metadata_confidence(metadata: Dict[str, Any], markdown_body: str) -> Dict[str, Any]:
    """
    Update overall confidence in metadata based on individual finding scores.
    Sets:
      - confidence (avg, rounded to 2 decimals)
      - confidence_scores_count
    """
    if not isinstance(metadata, dict):
        metadata = {"agent": "unknown", "parse_warning": "metadata_not_dict"}

    scores = extract_confidence_scores(markdown_body)

    if scores:
        avg_confidence = sum(scores) / len(scores)
        metadata["confidence"] = round(avg_confidence, 2)
        metadata["confidence_scores_count"] = len(scores)
        logger.info(
            "📊 Recalculated confidence: %.2f from %d scores",
            avg_confidence,
            len(scores),
        )
    else:
        logger.warning("⚠️ No confidence scores found in markdown body")

    return metadata




