#!/usr/bin/env python3
"""
Simple Direct Test for GitHub Data Adapter Pipeline

Tests the adapter directly by checking session state after execution.
"""

import httpx
import json
import time

API_BASE_URL = "http://localhost:8000"
APP_NAME = "orchestrator_agent"
USER_ID = "rahul gupta"

def test_adapter_pipeline():
    """Test that the data adapter properly transforms GitHub PR data."""
    
    print("\n" + "="*80)
    print("🧪 GitHub Data Adapter Pipeline Test")
    print("="*80)
    
    with httpx.Client(timeout=600.0) as client:
        # Step 1: Create session
        print("\n📝 Step 1: Creating session...")
        session_resp = client.post(
            f"{API_BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions",
            json={"state": {"github_context": {
                "repo": "test-org/test-repo",
                "pr_number": 42
            }}}
        )
        session_data = session_resp.json()
        session_id = session_data["id"]
        print(f"✅ Session created: {session_id}")
        
        # Step 2: Send simple message
        print("\n📤 Step 2: Sending message to trigger pipeline...")
        message = "Please review the code in this PR"
        
        start_time = time.time()
        invoke_resp = client.post(
            f"{API_BASE_URL}/run_sse",
            json={
                "appName": APP_NAME,
                "userId": USER_ID,
                "sessionId": session_id,
                "newMessage": {
                    "role": "user",
                    "parts": [{"text": message}]
                }
            }
        )
        duration = time.time() - start_time
        
        print(f"⏱️  Pipeline completed in {duration:.1f}s")
        print(f"📊 Status: {invoke_resp.status_code}")
        
        # Step 3: Check session state
        print("\n🔍 Step 3: Checking session state...")
        session_resp = client.get(
            f"{API_BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}"
        )
        state = session_resp.json()["state"]
        
        print(f"\n📋 Session State Keys ({len(state)} keys):")
        for key in sorted(state.keys()):
            print(f"   ✓ {key}")
        
        # Check for data adapter outputs
        print("\n🔬 Checking GitHub Data Adapter outputs:")
        adapter_keys = ['code', 'language', 'file_path', 'files_prepared', 'file_count', 'total_lines']
        for key in adapter_keys:
            if key in state:
                value = state[key]
                if key == 'code':
                    print(f"   ✅ {key}: {len(value)} chars")
                elif key == 'file_count':
                    print(f"   ✅ {key}: {value} files")
                elif key == 'total_lines':
                    print(f"   ✅ {key}: {value} lines")
                else:
                    print(f"   ✅ {key}: {value}")
            else:
                print(f"   ❌ {key}: MISSING")
        
        # Check for analysis outputs
        print("\n🔬 Checking Analysis Agent outputs:")
        analysis_keys = [
            'security_analysis',
            'code_quality_analysis',
            'engineering_practices_analysis',
            'carbon_emission_analysis'
        ]
        for key in analysis_keys:
            if key in state:
                data = state[key]
                if isinstance(data, str):
                    print(f"   ✅ {key}: {len(data)} chars")
                elif isinstance(data, dict):
                    print(f"   ✅ {key}: {len(str(data))} chars (dict)")
                else:
                    print(f"   ✅ {key}: {type(data)}")
            else:
                print(f"   ❌ {key}: MISSING")
        
        # Check final report
        print("\n📄 Final Report:")
        if 'final_report' in state:
            report = state['final_report']
            print(f"   ✅ Generated: {len(report)} chars")
            print(f"\n   Preview (first 500 chars):")
            print(f"   {report[:500]}...")
        else:
            print(f"   ❌ NOT GENERATED")
        
        print("\n" + "="*80)
        print("✅ Test Complete")
        print("="*80 + "\n")

if __name__ == "__main__":
    test_adapter_pipeline()
