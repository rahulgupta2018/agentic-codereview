#!/usr/bin/env python3
"""
Post-process GitHub pipeline results to persist artifacts.

This script:
1. Reads session state from ADK API
2. Extracts analysis results (security, quality, engineering, carbon)
3. Saves them as JSON files in session-based directory structure
4. Generates comprehensive markdown report

Usage:
    python scripts/persist_github_pipeline_artifacts.py <session_id>
"""

import sys
import json
import requests
from pathlib import Path
from typing import Dict, Any

API_BASE_URL = "http://localhost:8000"
USER_ID = "rahulgupta"
APP_NAME = "orchestrator_agent"

def fetch_session_state(session_id: str) -> Dict[str, Any]:
    """Fetch session state from ADK API."""
    url = f"{API_BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def clean_json_output(raw_output: str) -> str:
    """
    Clean markdown fences and extract pure JSON from agent output.
    
    Handles formats like:
    - ```json\n{...}\n```
    - {…}
    -  Plain text (returns as-is for error handling)
    """
    output = raw_output.strip()
    
    # Remove markdown code fences
    if output.startswith('```json'):
        output = output[7:]  # Remove ```json
    elif output.startswith('```'):
        output = output[3:]  # Remove ```
        
    if output.endswith('```'):
        output = output[:-3]  # Remove trailing ```
    
    output = output.strip()
    
    # Validate it's JSON
    try:
        json.loads(output)
        return output
    except json.JSONDecodeError:
        # Not valid JSON, return original
        return raw_output

def persist_artifacts(session_id: str):
    """Persist analysis artifacts from session state to disk."""
    print(f"📦 Persisting artifacts for session: {session_id}")
    
    # Fetch session
    try:
        session = fetch_session_state(session_id)
    except Exception as e:
        print(f"❌ Failed to fetch session: {e}")
        return False
    
    state = session.get('state', {})
    
    # Create session artifacts directory
    project_root = Path(__file__).parent.parent
    session_dir = project_root / "storage_bucket" / "artifacts" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Session directory: {session_dir}")
    
    # Analysis keys to persist
    analysis_keys = [
        ('security_analysis', 'security_agent_analysis.json'),
        ('code_quality_analysis', 'code_quality_agent_analysis.json'),
        ('engineering_practices_analysis', 'engineering_practices_agent_analysis.json'),
        ('carbon_emission_analysis', 'carbon_emission_agent_analysis.json'),
    ]
    
    saved_count = 0
    
    for state_key, filename in analysis_keys:
        if state_key not in state:
            print(f"  ⚠️  Skipping {state_key} (not in session state)")
            continue
        
        raw_output = state[state_key]
        
        # Clean and parse JSON
        try:
            cleaned_json = clean_json_output(raw_output)
            parsed = json.loads(cleaned_json)
            
            # Save to disk
            artifact_path = session_dir / filename
            with open(artifact_path, 'w', encoding='utf-8') as f:
                json.dump(parsed, f, indent=2)
            
            file_size = artifact_path.stat().st_size
            print(f"  ✅ Saved {filename} ({file_size} bytes)")
            saved_count += 1
            
        except json.JSONDecodeError as e:
            print(f"  ❌ Failed to parse {state_key} as JSON: {e}")
            print(f"     First 200 chars: {raw_output[:200]}")
        except Exception as e:
            print(f"  ❌ Error saving {state_key}: {e}")
    
    print(f"\n✅ Saved {saved_count}/{len(analysis_keys)} analysis artifacts")
    
    # TODO: Generate comprehensive report by loading JSONs and synthesizing
    # For now, just report on what was saved
    
    return saved_count > 0

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/persist_github_pipeline_artifacts.py <session_id>")
        sys.exit(1)
    
    session_id = sys.argv[1]
    success = persist_artifacts(session_id)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
