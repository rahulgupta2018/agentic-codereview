"""
Shared callback utilities for guardrails implementation.

This module provides reusable validation functions for agent callbacks:
- Hallucination detection and filtering
- Bias and profanity filtering
- False positive pattern matching
- CVE validation
- Metrics validation

Following the design in docs/CALLBACKS_GUARDRAILS_DESIGN.md (Phase 1)
"""

import json
import logging
import re
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

# Load configuration files
PROJECT_ROOT = Path(__file__).parent.parent
GUARDRAILS_DIR = PROJECT_ROOT / "config" / "guardrails"


class GuardrailConfig:
    """Centralized guardrail configuration loader."""
    
    def __init__(self):
        self._config_cache = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """Load all guardrail configuration files."""
        try:
            # Load main callback config
            callback_config_path = GUARDRAILS_DIR / "callback_config.yaml"
            if callback_config_path.exists():
                with open(callback_config_path) as f:
                    self._config_cache['callback_config'] = yaml.safe_load(f)
                logger.info(f"✅ Loaded callback_config.yaml")
            
            # Load false positive patterns
            fp_patterns_path = GUARDRAILS_DIR / "false_positive_patterns.yaml"
            if fp_patterns_path.exists():
                with open(fp_patterns_path) as f:
                    self._config_cache['false_positive_patterns'] = yaml.safe_load(f)
                logger.info(f"✅ Loaded false_positive_patterns.yaml")
            
            # Load bias prevention
            bias_path = GUARDRAILS_DIR / "bias_prevention.yaml"
            if bias_path.exists():
                with open(bias_path) as f:
                    self._config_cache['bias_prevention'] = yaml.safe_load(f)
                logger.info(f"✅ Loaded bias_prevention.yaml")
            
            # Load hallucination prevention
            hallucination_path = GUARDRAILS_DIR / "hallucination_prevention.yaml"
            if hallucination_path.exists():
                with open(hallucination_path) as f:
                    self._config_cache['hallucination_prevention'] = yaml.safe_load(f)
                logger.info(f"✅ Loaded hallucination_prevention.yaml")
            
            # Load profanity blocklist
            profanity_path = GUARDRAILS_DIR / "profanity_blocklist.txt"
            if profanity_path.exists():
                with open(profanity_path) as f:
                    self._config_cache['profanity_blocklist'] = [
                        line.strip() for line in f if line.strip() and not line.startswith('#')
                    ]
                logger.info(f"✅ Loaded profanity_blocklist.txt ({len(self._config_cache['profanity_blocklist'])} terms)")
            
        except Exception as e:
            logger.error(f"❌ Failed to load guardrail configs: {e}")
    
    def get(self, config_name: str) -> Optional[Any]:
        """Get configuration by name."""
        return self._config_cache.get(config_name)
    
    def reload(self):
        """Reload all configurations."""
        self._config_cache.clear()
        self._load_all_configs()


# Global config instance
_guardrail_config = GuardrailConfig()


def get_config(config_name: str) -> Optional[Any]:
    """Get guardrail configuration."""
    return _guardrail_config.get(config_name)


# ============================================================================
# HALLUCINATION DETECTION & FILTERING
# ============================================================================

def filter_hallucinations(analysis_data: Dict, source_artifacts: Dict) -> Tuple[Dict, int]:
    """
    Remove hallucinated findings not present in source artifacts.
    
    Args:
        analysis_data: Agent output (e.g., report synthesizer output)
        source_artifacts: Source analysis artifacts to validate against
    
    Returns:
        Tuple of (filtered_data, removed_count)
    """
    removed_count = 0
    
    try:
        # Load hallucination prevention config
        config = get_config('hallucination_prevention')
        if not config:
            logger.warning("⚠️ Hallucination prevention config not found, skipping")
            return analysis_data, 0
        
        # Extract all findings from source artifacts
        source_findings = set()
        for artifact_name, artifact_data in source_artifacts.items():
            if isinstance(artifact_data, dict):
                # Extract finding identifiers (CVEs, function names, file paths, etc.)
                source_findings.update(_extract_finding_identifiers(artifact_data))
        
        # Check findings in analysis_data
        filtered_data = analysis_data.copy()
        
        # Recursively check and filter
        filtered_data, removed = _filter_hallucinations_recursive(filtered_data, source_findings)
        removed_count += removed
        
        if removed_count > 0:
            logger.info(f"🛡️ [filter_hallucinations] Removed {removed_count} hallucinated findings")
        
        return filtered_data, removed_count
    
    except Exception as e:
        logger.error(f"❌ [filter_hallucinations] Error: {e}")
        return analysis_data, 0


def _extract_finding_identifiers(data: Any) -> set:
    """Extract finding identifiers from artifact data."""
    identifiers = set()
    
    if isinstance(data, dict):
        # Extract common identifier fields
        for key in ['cve', 'cve_id', 'function', 'function_name', 'file', 'file_path', 'type', 'issue_type']:
            if key in data:
                identifiers.add(str(data[key]))
        
        # Recurse into nested dicts
        for value in data.values():
            identifiers.update(_extract_finding_identifiers(value))
    
    elif isinstance(data, list):
        for item in data:
            identifiers.update(_extract_finding_identifiers(item))
    
    return identifiers


def _filter_hallucinations_recursive(data: Any, valid_identifiers: set) -> Tuple[Any, int]:
    """Recursively filter hallucinated findings."""
    removed_count = 0
    
    if isinstance(data, dict):
        filtered = {}
        for key, value in data.items():
            if key in ['vulnerabilities', 'findings', 'issues', 'recommendations']:
                # This is a findings list - validate each item
                if isinstance(value, list):
                    filtered_list = []
                    for item in value:
                        if _is_valid_finding(item, valid_identifiers):
                            filtered_list.append(item)
                        else:
                            removed_count += 1
                            logger.debug(f"🚫 Filtered hallucinated finding: {item.get('type', 'unknown')}")
                    filtered[key] = filtered_list
                else:
                    filtered[key] = value
            else:
                # Recurse into nested structures
                filtered[key], removed = _filter_hallucinations_recursive(value, valid_identifiers)
                removed_count += removed
        return filtered, removed_count
    
    elif isinstance(data, list):
        filtered = []
        for item in data:
            filtered_item, removed = _filter_hallucinations_recursive(item, valid_identifiers)
            filtered.append(filtered_item)
            removed_count += removed
        return filtered, removed_count
    
    else:
        return data, 0


def _is_valid_finding(finding: Dict, valid_identifiers: set) -> bool:
    """Check if finding is valid (not hallucinated)."""
    # Extract identifiers from finding
    finding_ids = _extract_finding_identifiers(finding)
    
    # If any identifier matches source artifacts, it's valid
    if finding_ids & valid_identifiers:
        return True
    
    # If no identifiers extracted, be conservative and keep it
    if not finding_ids:
        return True
    
    return False


# ============================================================================
# BIAS & PROFANITY FILTERING
# ============================================================================

def filter_bias(text: str) -> Tuple[str, int]:
    """
    Remove biased/subjective language and profanity.
    
    Args:
        text: Text to filter
    
    Returns:
        Tuple of (filtered_text, replacements_count)
    """
    replacements_count = 0
    filtered = text
    
    try:
        # Load bias prevention config
        bias_config = get_config('bias_prevention')
        profanity_list = get_config('profanity_blocklist') or []
        
        if not bias_config:
            logger.warning("⚠️ Bias prevention config not found, skipping")
            return text, 0
        
        # Filter subjective language
        subjective_patterns = bias_config.get('subjective_language', {})
        for pattern_data in subjective_patterns.get('patterns', []):
            pattern = pattern_data.get('pattern', '')
            replacement = pattern_data.get('replacement', '[removed]')
            
            # Case-insensitive replacement
            new_text = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)
            if new_text != filtered:
                replacements_count += 1
                filtered = new_text
        
        # Filter profanity
        for profane_word in profanity_list:
            pattern = r'\b' + re.escape(profane_word) + r'\b'
            new_text = re.sub(pattern, '[removed]', filtered, flags=re.IGNORECASE)
            if new_text != filtered:
                replacements_count += 1
                filtered = new_text
        
        if replacements_count > 0:
            logger.info(f"🛡️ [filter_bias] Filtered {replacements_count} biased/profane terms")
        
        return filtered, replacements_count
    
    except Exception as e:
        logger.error(f"❌ [filter_bias] Error: {e}")
        return text, 0


# ============================================================================
# FALSE POSITIVE FILTERING
# ============================================================================

def filter_false_positives(findings: List[Dict], agent_type: str) -> Tuple[List[Dict], int]:
    """
    Filter false positive findings based on known patterns.
    
    Args:
        findings: List of findings to filter
        agent_type: Agent type (security_agent, code_quality_agent, etc.)
    
    Returns:
        Tuple of (filtered_findings, removed_count)
    """
    removed_count = 0
    
    try:
        # Load false positive patterns
        fp_config = get_config('false_positive_patterns')
        if not fp_config:
            logger.warning("⚠️ False positive patterns not found, skipping")
            return findings, 0
        
        # Get patterns for this agent type
        agent_patterns = fp_config.get(agent_type, {}).get('patterns', [])
        
        filtered_findings = []
        for finding in findings:
            if _is_false_positive(finding, agent_patterns):
                removed_count += 1
                logger.debug(f"🚫 Filtered false positive: {finding.get('type', 'unknown')}")
            else:
                filtered_findings.append(finding)
        
        if removed_count > 0:
            logger.info(f"🛡️ [filter_false_positives] Filtered {removed_count} false positives for {agent_type}")
        
        return filtered_findings, removed_count
    
    except Exception as e:
        logger.error(f"❌ [filter_false_positives] Error: {e}")
        return findings, 0


def _is_false_positive(finding: Dict, patterns: List[Dict]) -> bool:
    """Check if finding matches false positive patterns."""
    finding_type = finding.get('type', '').lower()
    finding_desc = finding.get('description', '').lower()
    finding_code = finding.get('code_snippet', '').lower()
    
    for pattern in patterns:
        pattern_type = pattern.get('type', '').lower()
        pattern_indicators = pattern.get('indicators', [])
        pattern_code = pattern.get('code_pattern', '').lower()
        
        # Check if types match
        if pattern_type and pattern_type in finding_type:
            # Check for indicators in description
            if pattern_indicators:
                if any(indicator.lower() in finding_desc for indicator in pattern_indicators):
                    return True
            
            # Check for code pattern
            if pattern_code and pattern_code in finding_code:
                return True
    
    return False


# ============================================================================
# CVE VALIDATION
# ============================================================================

def validate_cve_exists(cve_id: str) -> bool:
    """
    Validate that a CVE ID exists using NVD API.
    
    Args:
        cve_id: CVE identifier (e.g., CVE-2023-12345)
    
    Returns:
        True if CVE exists, False otherwise
    """
    try:
        # Basic format validation
        if not re.match(r'^CVE-\d{4}-\d{4,}$', cve_id):
            logger.warning(f"⚠️ Invalid CVE format: {cve_id}")
            return False
        
        # Check against NVD API
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
        
        # Add timeout to prevent blocking
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            # Check if CVE exists in results
            if data.get('totalResults', 0) > 0:
                logger.debug(f"✅ CVE validated: {cve_id}")
                return True
            else:
                logger.warning(f"⚠️ CVE not found: {cve_id}")
                return False
        else:
            logger.warning(f"⚠️ NVD API error for {cve_id}: {response.status_code}")
            # On API error, be conservative and allow CVE (don't block on network issues)
            return True
    
    except requests.exceptions.Timeout:
        logger.warning(f"⚠️ NVD API timeout for {cve_id}, allowing CVE")
        return True
    except Exception as e:
        logger.error(f"❌ [validate_cve_exists] Error validating {cve_id}: {e}")
        return True  # Fail open


# ============================================================================
# METRICS VALIDATION
# ============================================================================

def validate_metrics(analysis_data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate that findings include required metrics/evidence.
    
    Args:
        analysis_data: Analysis output to validate
    
    Returns:
        Tuple of (is_valid, missing_fields)
    """
    missing_fields = []
    
    try:
        # Required fields for findings
        required_fields = ['type', 'location', 'description', 'recommendation']
        evidence_fields = ['line', 'code_snippet', 'metric', 'file_path']
        
        # Check findings recursively
        findings = []
        _extract_findings(analysis_data, findings)
        
        for finding in findings:
            # Check required fields
            for field in required_fields:
                if field not in finding or not finding[field]:
                    missing_fields.append(f"Missing {field} in finding: {finding.get('type', 'unknown')}")
            
            # Check that at least one evidence field exists
            has_evidence = any(field in finding and finding[field] for field in evidence_fields)
            if not has_evidence:
                missing_fields.append(f"No evidence (line/snippet/metric) in finding: {finding.get('type', 'unknown')}")
        
        is_valid = len(missing_fields) == 0
        
        if not is_valid:
            logger.warning(f"⚠️ [validate_metrics] Found {len(missing_fields)} validation issues")
        
        return is_valid, missing_fields
    
    except Exception as e:
        logger.error(f"❌ [validate_metrics] Error: {e}")
        return False, [str(e)]


def _extract_findings(data: Any, findings: List[Dict]):
    """Extract all findings from nested data structure."""
    if isinstance(data, dict):
        # Check if this is a finding
        if 'type' in data and ('description' in data or 'location' in data):
            findings.append(data)
        
        # Recurse
        for value in data.values():
            _extract_findings(value, findings)
    
    elif isinstance(data, list):
        for item in data:
            _extract_findings(item, findings)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def parse_json_safe(text: str) -> Optional[Dict]:
    """Safely parse JSON from text, handling markdown code fences."""
    try:
        # Strip markdown code fences
        text = text.strip()
        if text.startswith('```json'):
            lines = text.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            text = '\n'.join(lines).strip()
        elif text.startswith('```'):
            lines = text.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            text = '\n'.join(lines).strip()
        
        return json.loads(text)
    except Exception as e:
        logger.error(f"❌ Failed to parse JSON: {e}")
        return None


def format_json_safe(data: Any) -> str:
    """Safely format data as JSON string."""
    try:
        return json.dumps(data, indent=2)
    except Exception as e:
        logger.error(f"❌ Failed to format JSON: {e}")
        return str(data)


# ============================================================================
# CALLBACK EXECUTION WRAPPER
# ============================================================================

def execute_callback_safe(callback_func, *args, **kwargs):
    """
    Execute callback with error handling (fail-open strategy).
    
    Args:
        callback_func: Callback function to execute
        *args, **kwargs: Arguments to pass to callback
    
    Returns:
        Callback result or None on error
    """
    try:
        return callback_func(*args, **kwargs)
    except Exception as e:
        logger.error(f"❌ Callback failed: {callback_func.__name__}: {e}")
        # Fail open - return None to continue execution
        return None


logger.info("✅ [callbacks.py] Callback utilities loaded")
