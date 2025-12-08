"""
Test GitHub Pipeline via API
Tests the complete workflow by calling POST /api/github/webhook with mock PR data.
"""

import asyncio
import httpx
import json
import time
from datetime import datetime

# API base URL (adjust if running on different host/port)
API_BASE_URL = "http://localhost:8000"

# ============================================================================
# MOCK GITHUB PR PAYLOAD
# ============================================================================

MOCK_PR_PAYLOAD = {
    "action": "opened",
    "number": 123,
    "pull_request": {
        "title": "Add authentication feature",
        "body": """
This PR adds JWT-based authentication to the API.

Changes:
- Added authentication middleware
- Implemented JWT token generation and validation
- Added user login and registration endpoints
- Updated API documentation
        """,
        "head": {
            "sha": "abc123def456",
            "ref": "feature/authentication"
        },
        "base": {
            "ref": "main"
        },
        "user": {
            "login": "developer123"
        },
        "html_url": "https://github.com/test-org/test-repo/pull/123",
        "diff_url": "https://github.com/test-org/test-repo/pull/123.diff",
        "files": [
            {
                "filename": "src/auth/middleware.py",
                "status": "added",
                "additions": 150,
                "deletions": 0,
                "patch": """
@@ -0,0 +1,150 @@
+import jwt
+from datetime import datetime, timedelta
+
+def generate_token(user_id: str) -> str:
+    # TODO: Move secret key to environment variable
+    secret_key = "hardcoded_secret_key_123"
+    payload = {
+        "user_id": user_id,
+        "exp": datetime.utcnow() + timedelta(hours=24)
+    }
+    return jwt.encode(payload, secret_key, algorithm="HS256")
+
+def validate_token(token: str) -> dict:
+    secret_key = "hardcoded_secret_key_123"
+    try:
+        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
+        return payload
+    except jwt.ExpiredSignatureError:
+        raise Exception("Token expired")
+    except jwt.InvalidTokenError:
+        raise Exception("Invalid token")
+
+def authenticate_request(request):
+    # SQL injection vulnerability here
+    user_id = request.headers.get("user_id")
+    query = f"SELECT * FROM users WHERE id = {user_id}"
+    # Execute query...
+                """
            }
        ]
    },
    "repository": {
        "name": "test-repo",
        "owner": {
            "login": "test-org"
        },
        "full_name": "test-org/test-repo"
    }
}

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

async def test_health_check():
    """Test 1: Health check endpoint."""
    print("\n" + "=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/health")
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        assert response.status_code == 200, "Health check failed"
        assert response.json()["status"] == "healthy", "Service not healthy"
        
        print("✅ Health check passed!")
        return response.json()

async def test_github_webhook():
    """Test 2: Send GitHub webhook and verify queuing."""
    print("\n" + "=" * 60)
    print("TEST 2: GitHub Webhook - Queue Pipeline")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{API_BASE_URL}/api/github/webhook",
            json=MOCK_PR_PAYLOAD
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        assert response.status_code == 200, "Webhook submission failed"
        result = response.json()
        assert result["status"] == "queued", "Pipeline not queued"
        assert "session_id" in result, "No session ID returned"
        
        print("✅ Webhook processed and pipeline queued!")
        return result["session_id"]

async def test_status_polling(session_id: str, max_wait: int = 180):
    """Test 3: Poll status endpoint until pipeline completes."""
    print("\n" + "=" * 60)
    print(f"TEST 3: Poll Status for Session {session_id}")
    print("=" * 60)
    
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > max_wait:
                print(f"❌ Timeout after {max_wait}s")
                break
            
            response = await client.get(f"{API_BASE_URL}/api/status/{session_id}")
            
            if response.status_code != 200:
                print(f"❌ Status check failed: {response.status_code}")
                break
            
            status_data = response.json()
            status = status_data["status"]
            
            print(f"⏱️  [{elapsed:.1f}s] Status: {status}")
            
            if status == "completed":
                print("\n✅ Pipeline completed successfully!")
                print(f"📊 Final Status: {json.dumps(status_data, indent=2)}")
                return status_data
            
            elif status == "failed":
                print(f"\n❌ Pipeline failed!")
                print(f"📊 Final Status: {json.dumps(status_data, indent=2)}")
                return status_data
            
            # Wait before next poll
            await asyncio.sleep(5)
    
    print("❌ Status polling incomplete")
    return None

async def test_full_workflow():
    """Test 4: Complete end-to-end workflow."""
    print("\n" + "=" * 80)
    print("🚀 FULL WORKFLOW TEST: GitHub PR Code Review Pipeline")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Health check
        health_data = await test_health_check()
        print(f"\n✅ API Server: {health_data['status']}")
        print(f"✅ Root Agent: {health_data['root_agent']}")
        print(f"✅ Agents Available: {health_data['agents_available']}")
        
        # Step 2: Submit webhook
        session_id = await test_github_webhook()
        print(f"\n✅ Session Created: {session_id}")
        
        # Step 3: Poll for completion
        final_status = await test_status_polling(session_id, max_wait=300)
        
        if final_status and final_status["status"] == "completed":
            print("\n" + "=" * 80)
            print("🎉 SUCCESS: Full workflow completed!")
            print("=" * 80)
            print(f"\n📊 Summary:")
            print(f"  Session ID: {session_id}")
            print(f"  PR Number: {final_status.get('pr_number')}")
            print(f"  Repository: {final_status.get('repository')}")
            print(f"  Artifacts Generated: {final_status.get('artifacts_generated', 0)}")
            print(f"  Report Ready: {final_status.get('report_ready', False)}")
            print(f"  Duration: {final_status.get('updated_at')} - {final_status.get('created_at')}")
            
            print(f"\n📁 Check artifacts at: ./storage_bucket/artifacts/")
            print(f"💾 Check session at: ./storage_bucket/sessions/{session_id}.json")
            
            return True
        else:
            print("\n" + "=" * 80)
            print("❌ FAILURE: Workflow did not complete successfully")
            print("=" * 80)
            return False
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("🧪 API TEST SUITE: GitHub Pipeline via REST API")
    print("=" * 80)
    print("\nThis test suite validates the complete GitHub PR review workflow:")
    print("1. API health check")
    print("2. Submit GitHub webhook payload")
    print("3. Poll for pipeline completion")
    print("4. Verify artifacts and reports generated")
    print("\nPipeline Execution (Sequential):")
    print("  GitHubFetcher → PlanningAgent → DynamicRouter → ReportSynthesizer → GitHubPublisher")
    print("\nDynamicRouter Sequential Execution:")
    print("  1. SecurityAgent (completes fully)")
    print("  2. CodeQualityAgent (completes fully)")
    print("  3. EngineeringAgent (completes fully)")
    print("  4. CarbonAgent (completes fully)")
    print("\n" + "=" * 80)
    
    # Check if API is running
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE_URL}/health")
            if response.status_code != 200:
                print("\n❌ ERROR: API server not healthy")
                print("Please start the API server first:")
                print("  python api_server.py")
                return
    except Exception as e:
        print(f"\n❌ ERROR: Cannot connect to API server at {API_BASE_URL}")
        print(f"Error: {e}")
        print("\nPlease start the API server first:")
        print("  python api_server.py")
        return
    
    # Run full workflow test
    success = await test_full_workflow()
    
    if success:
        print("\n✅ ALL TESTS PASSED!")
        exit(0)
    else:
        print("\n❌ TESTS FAILED")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
