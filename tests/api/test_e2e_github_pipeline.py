#!/usr/bin/env python3
"""
End-to-End Test for GitHub Pipeline via ADK API Server (port 8000)

This script tests the complete GitHub pipeline flow using MOCK GitHub data:
1. Sets MOCK_GITHUB=true to use mock PR data
2. Creates session with github_context
3. Invokes pipeline via /run_sse endpoint
4. GitHub pipeline executes: Fetcher → Planning → DynamicRouter → Report → Publisher
5. Monitors execution and verifies artifacts

Usage:
    export MOCK_GITHUB=true
    python tests/api/test_e2e_github_pipeline.py
    
Note: Requires:
      - adk api_server running on port 8000
      - Mock data in data/github_app_mock/github_pr_fetcher_mock.py
      - MOCK_GITHUB=true environment variable
"""

import asyncio
import httpx
import json
import os
import time
from pathlib import Path
from datetime import datetime

# Enable mock GitHub mode
os.environ['MOCK_GITHUB'] = 'true'

# Configuration
API_BASE_URL = "http://localhost:8000"  # ADK API Server
APP_NAME = "orchestrator_agent"  
USER_ID = "rahulgupta"

# Mock PR data with intentional issues for testing
MOCK_PR_MESSAGE = """
Please perform a COMPLETE code review analysis of this GitHub Pull Request.

REQUIRED ANALYSES:
1. Security vulnerabilities (MD5 usage, plaintext secrets, etc.)
2. Code quality issues (complexity, nested logic, error handling)
3. Engineering best practices (testing, documentation, configuration)
4. Carbon emissions impact (memory usage, efficiency)

Then synthesize all findings into a comprehensive markdown report.

**PR #42**: Add OAuth2 authentication feature
**Repository**: test-org/test-repo
**Branch**: feature/oauth2 → main
**Author**: developer123

**Changes**: 2 files, +235 lines

**File 1: src/auth/oauth2.py** (new file, +150 lines)
```python
import hashlib
import secrets
from typing import Optional

class OAuth2Handler:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        # SECURITY ISSUE: storing secret in plain text
        self.client_secret = client_secret
        
    def generate_token(self, user_id: str) -> str:
        # COMPLEXITY ISSUE: deeply nested logic
        if user_id:
            if self.client_id:
                if self.client_secret:
                    # SECURITY ISSUE: using weak MD5 hash
                    token = hashlib.md5(f"{user_id}{self.client_id}".encode()).hexdigest()
                    return token
        return ""
        
    def validate_token(self, token: str) -> bool:
        # ENGINEERING ISSUE: missing error handling
        if token:
            return True
        return False
```

**File 2: src/auth/__init__.py** (modified, +2 lines)
```python
from .base import BaseAuth
from .jwt_handler import JWTHandler
from .oauth2 import OAuth2Handler
```

Please analyze this PR for:
1. Security vulnerabilities
2. Code quality issues
3. Engineering best practices
4. Carbon footprint impact
"""


async def test_github_pipeline():
    """Test the complete GitHub pipeline through ADK API server."""
    
    print("="*80)
    print("🧪 End-to-End GitHub Pipeline Test")
    print("="*80)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"User ID: {USER_ID}")
    print()
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            # Step 1: Create session with GitHub context
            print("📝 Step 1: Creating session with GitHub PR context...")
            github_context = {
                "repo": "test-org/test-repo",  # Format: owner/repo
                "pr_number": 42,
                "head_sha": "abc123def456",  # Mock SHA
                "title": "Add OAuth2 authentication feature",
                "description": "This PR adds OAuth2 authentication support",
                "branch": "feature/oauth2",
                "base_branch": "main",
                "author": "developer123",
                "files_changed": [
                    {
                        "filename": "src/auth/oauth2.py",
                        "status": "added",
                        "additions": 150,
                        "deletions": 0,
                        "patch": "...code with security issues..."
                    }
                ]
            }
            
            session_resp = await client.post(
                f"{API_BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions",
                json={"state": {"github_context": github_context}}
            )
            session_resp.raise_for_status()
            session_data = session_resp.json()
            session_id = session_data["id"]
            print(f"✅ Session created: {session_id}")
            print(f"   Session data: {json.dumps(session_data, indent=2)}")
            print()
            
            # Step 2: Send PR review request via /run_sse endpoint
            print("🚀 Step 2: Invoking GitHub Pipeline via /run_sse...")
            print(f"   Message length: {len(MOCK_PR_MESSAGE)} chars")
            print(f"   Expected flow:")
            print(f"     1. GitHub Fetcher → parse PR data")
            print(f"     2. Planning Agent → select analyses")
            print(f"     3. Dynamic Router → run sequentially:")
            print(f"        • Security Agent")
            print(f"        • Code Quality Agent")
            print(f"        • Engineering Practices Agent")
            print(f"        • Carbon Emission Agent")
            print(f"     4. Report Synthesizer → generate markdown")
            print(f"     5. GitHub Publisher → post review")
            print()
            
            # Invoke agent via ADK API server /run_sse endpoint
            invoke_start_time = time.time()
            invoke_resp = await client.post(
                f"{API_BASE_URL}/run_sse",
                json={
                    "appName": APP_NAME,
                    "userId": USER_ID,
                    "sessionId": session_id,
                    "newMessage": {
                        "role": "user",
                        "parts": [
                            {"text": MOCK_PR_MESSAGE}
                        ]
                    }
                }
            )
            invoke_duration = time.time() - invoke_start_time
            
            print(f"⏱️  Invocation completed in {invoke_duration:.2f}s")
            print(f"   Status code: {invoke_resp.status_code}")
            print()
            
            if invoke_resp.status_code == 200:
                # SSE response - read the stream
                response_text = invoke_resp.text
                print("✅ GitHub Pipeline executed!")
                print(f"   Response length: {len(response_text)} chars")
                print(f"   Response preview:")
                print(f"   {response_text[:500]}...")
                print()
            else:
                print(f"❌ Invocation failed: {invoke_resp.status_code}")
                print(f"   Response: {invoke_resp.text[:500]}")
                return False
            
            # Step 3: Get updated session to see events
            print("📊 Step 3: Fetching session events...")
            session_resp = await client.get(
                f"{API_BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}"
            )
            session_resp.raise_for_status()
            updated_session = session_resp.json()
            
            print(f"   Session state keys: {list(updated_session.get('state', {}).keys())}")
            print(f"   Events count: {len(updated_session.get('events', []))}")
            
            if updated_session.get('events'):
                print("   Events:")
                for idx, event in enumerate(updated_session['events'][:5], 1):
                    event_type = event.get('type', 'unknown')
                    event_data = event.get('data', {})
                    print(f"      {idx}. {event_type}: {str(event_data)[:80]}...")
            print()
            
            # Step 4: Check for artifacts
            print("📁 Step 4: Checking for artifacts...")
            artifact_base = Path("storage_bucket/artifacts")
            
            if artifact_base.exists():
                # Find session-specific artifacts
                session_artifacts = list(artifact_base.glob(f"**/*{session_id[:8]}*"))
                print(f"   Artifact directory exists: {artifact_base.resolve()}")
                print(f"   Session artifacts found: {len(session_artifacts)}")
                
                if session_artifacts:
                    for artifact in session_artifacts[:10]:
                        print(f"      - {artifact.relative_to(artifact_base)}")
                else:
                    print("   ⚠️  No session-specific artifacts found yet")
                    print("   (Artifacts may be created asynchronously)")
            else:
                print(f"   ⚠️  Artifact directory not found: {artifact_base.resolve()}")
            print()
            
            # Step 5: Summary
            print("="*80)
            print("✅ Test Completed Successfully!")
            print("="*80)
            print("\n📊 Summary:")
            print(f"   Session ID: {session_id}")
            print(f"   Invocation duration: {invoke_duration:.2f}s")
            print(f"   Events captured: {len(updated_session.get('events', []))}")
            print(f"   Session state: {len(updated_session.get('state', {}))} keys")
            
            print("\n🔍 Next Steps:")
            print("   1. Check logs: tail -f agent_workspace/adk_web.log")
            print("   2. Verify sequential execution in logs (timestamps show each agent completing)")
            print("   3. Check artifacts: ls -R storage_bucket/artifacts/")
            print(f"   4. ADK Web UI: http://localhost:8800")
            print(f"   5. Session API: http://localhost:8000/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}")
            
            return True
            
        except httpx.HTTPStatusError as e:
            print(f"\n❌ HTTP Error: {e}")
            print(f"   Response: {e.response.text}")
            return False
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = asyncio.run(test_github_pipeline())
    exit(0 if success else 1)
