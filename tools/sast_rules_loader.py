from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml

logger = logging.getLogger(__name__)


DEFAULT_LANGUAGE_PRIORITY = [
    "typescript",
    "javascript",
    "python",
    "java",
    "go",
    "rust",
    "swift",
    "kotlin",
    "cpp",
    "csharp",
    "sql",
]


@dataclass(frozen=True)
class SASTLoadResult:
    rules: List[Dict[str, Any]]
    loaded_files: List[str]
    warnings: List[str]


def _safe_yaml_load(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return None
    except Exception as e:
        logger.warning("⚠️ Failed to load YAML %s: %s", path, e)
        return None


def _normalize_language(lang: str) -> str:
    l = (lang or "").strip().lower()
    # common aliases
    if l in ("ts",):
        return "typescript"
    if l in ("js",):
        return "javascript"
    if l in ("py",):
        return "python"
    if l in ("c++",):
        return "cpp"
    if l in ("c#",):
        return "csharp"
    return l


def _basic_schema_validate(doc: Dict[str, Any], source: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    MVP validation: ensure it has top-level 'rules' list and rule objects have essentials.
    Returns (rules, warnings). Does NOT raise (fail-open).
    """
    warnings: List[str] = []
    if not isinstance(doc, dict):
        return [], [f"{source}: YAML root is not a dict"]

    rules = doc.get("rules", [])
    if not isinstance(rules, list):
        return [], [f"{source}: 'rules' is not a list"]

    normalized: List[Dict[str, Any]] = []
    for i, r in enumerate(rules):
        if not isinstance(r, dict):
            warnings.append(f"{source}: rule[{i}] is not a dict")
            continue

        missing = []
        for k in ("id", "title", "description", "category", "severity", "confidence", "detection", "remediation"):
            if k not in r:
                missing.append(k)
        if missing:
            warnings.append(f"{source}: rule[{r.get('id','<no-id>')}] missing fields: {', '.join(missing)}")

        # detection sanity
        det = r.get("detection", {})
        if isinstance(det, dict):
            if not isinstance(det.get("file_globs", []), list):
                warnings.append(f"{source}: rule[{r.get('id')}] detection.file_globs is not a list")
            patterns = det.get("patterns", [])
            if not isinstance(patterns, list) or not patterns:
                warnings.append(f"{source}: rule[{r.get('id')}] detection.patterns is missing/empty")
        else:
            warnings.append(f"{source}: rule[{r.get('id')}] detection is not a dict")

        normalized.append(r)

    return normalized, warnings


def load_sast_rules(
    rules_dir: str | Path,
    detected_languages: Optional[Sequence[str]] = None,
    *,
    language_priority: Optional[Sequence[str]] = None,
    include_generic: bool = True,
    include_schema_file: bool = False,
) -> SASTLoadResult:
    """
    Load SAST rules from a directory.

    - Always loads generic.yaml first (if include_generic=True)
    - Loads language-specific YAMLs in priority order, but only for detected languages
    - Fail-open: missing files are skipped, parse errors produce warnings

    Args:
        rules_dir: directory containing YAML files (generic.yaml, python.yaml, etc.)
        detected_languages: e.g. ["python","typescript"]
        language_priority: ordering preference (defaults to DEFAULT_LANGUAGE_PRIORITY)
        include_generic: include generic.yaml
        include_schema_file: if True, attempts to load _schema.yaml (for future validation); not required for MVP

    Returns:
        SASTLoadResult(rules, loaded_files, warnings)
    """
    rules_path = Path(rules_dir)
    prio = [_normalize_language(x) for x in (language_priority or DEFAULT_LANGUAGE_PRIORITY)]
    detected = {_normalize_language(x) for x in (detected_languages or []) if x}

    loaded_files: List[str] = []
    warnings: List[str] = []
    all_rules: List[Dict[str, Any]] = []

    if include_schema_file:
        schema_doc = _safe_yaml_load(rules_path / "_schema.yaml")
        if schema_doc is None:
            warnings.append(f"{rules_path / '_schema.yaml'} not found (optional)")
        else:
            loaded_files.append(str(rules_path / "_schema.yaml"))

    # 1) generic.yaml first
    if include_generic:
        generic_file = rules_path / "generic.yaml"
        doc = _safe_yaml_load(generic_file)
        if doc is None:
            warnings.append(f"{generic_file} not found")
        else:
            rules, w = _basic_schema_validate(doc, str(generic_file))
            all_rules.extend(rules)
            warnings.extend(w)
            loaded_files.append(str(generic_file))

    # 2) language-specific files
    # Only load those that are both in detected AND in priority list (stable order)
    ordered_langs = [l for l in prio if l in detected] if detected else []
    for lang in ordered_langs:
        f = rules_path / f"{lang}.yaml"
        doc = _safe_yaml_load(f)
        if doc is None:
            warnings.append(f"{f} not found")
            continue
        rules, w = _basic_schema_validate(doc, str(f))
        all_rules.extend(rules)
        warnings.extend(w)
        loaded_files.append(str(f))

    # If nothing detected, you may want a fallback: load top-N priority languages.
    # MVP choice: keep it strict and only load generic if no detected languages.
    if not detected and include_generic:
        warnings.append("No detected languages provided; loaded only generic.yaml")

    return SASTLoadResult(rules=all_rules, loaded_files=loaded_files, warnings=warnings)