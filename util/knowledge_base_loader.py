from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass(frozen=True)
class KnowledgeBaseConfig:
    kb_root: Path
    strict: bool = True  # if False: missing files become {} instead of crashing


def _load_yaml_file(path: Path, *, strict: bool) -> Dict[str, Any]:
    if not path.exists():
        if strict:
            raise FileNotFoundError(f"Knowledge base file not found: {path}")
        return {}

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"KB YAML must be a mapping/object at top-level: {path}")

    return data


def load_all_kbs(*, kb_root: str | Path, strict: bool = True) -> Dict[str, Dict[str, Any]]:
    """
    Load all agent KBs from disk and return a dict ready to drop into ADK session state.

    Returned keys:
      - security_guidelines
      - code_quality_guidelines
      - engineering_practices_guidelines
      - carbon_emission_standards
    """
    root = Path(kb_root)

    files = {
        "security_guidelines": root / "security_guidelines.yaml",
        "code_quality_guidelines": root / "code_quality_guidelines.yaml",
        "engineering_practices_guidelines": root / "engineering_practices_guidelines.yaml",
        "carbon_emission_standards": root / "carbon_emission_standards.yaml",
    }

    kbs: Dict[str, Dict[str, Any]] = {}
    for key, path in files.items():
        kbs[key] = _load_yaml_file(path, strict=strict)

    return kbs


def ensure_kbs_in_state(callback_context, *, kb_root: str | Path, strict: bool = True) -> None:
    """
    Idempotently load KBs into callback_context.state exactly once per run/session.
    """
    if callback_context.state.get("_kbs_loaded"):
        return

    kbs = load_all_kbs(kb_root=kb_root, strict=strict)
    callback_context.state.update(kbs)
    callback_context.state["_kbs_loaded"] = True