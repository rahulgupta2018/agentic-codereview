"""
Quick Start Script for API Server Testing

This script:
1. Checks if API dependencies are installed
2. Starts the API server in the background
3. Waits for server to be ready
4. Runs the test suite
5. Stops the server

Usage:
    python tests/api/run_api_tests.sh
"""

import subprocess
import time
import sys
import signal
import os

API_SERVER_PROCESS = None

def check_dependencies():
    """Check if API dependencies are installed."""
    print("🔍 Checking API dependencies...")
    try:
        import fastapi
        import uvicorn
        import httpx
        print("✅ All API dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("\n📦 Install API dependencies:")
        print("  pip install -r requirements-api.txt")
        return False

def start_api_server():
    """Start API server in background."""
    global API_SERVER_PROCESS
    
    print("\n🚀 Starting API server...")
    API_SERVER_PROCESS = subprocess.Popen(
        [sys.executable, "api_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to be ready
    print("⏳ Waiting for server to start...")
    for i in range(30):
        try:
            import httpx
            response = httpx.get("http://localhost:8000/health", timeout=1.0)
            if response.status_code == 200:
                print("✅ API server ready!")
                return True
        except:
            pass
        time.sleep(1)
        print(f"   Attempt {i+1}/30...")
    
    print("❌ API server failed to start")
    return False

def run_tests():
    """Run API test suite."""
    print("\n🧪 Running API tests...")
    result = subprocess.run(
        [sys.executable, "tests/api/test_github_webhook.py"],
        capture_output=False
    )
    return result.returncode == 0

def stop_api_server():
    """Stop API server."""
    global API_SERVER_PROCESS
    if API_SERVER_PROCESS:
        print("\n🛑 Stopping API server...")
        API_SERVER_PROCESS.send_signal(signal.SIGINT)
        API_SERVER_PROCESS.wait(timeout=5)
        print("✅ API server stopped")

def main():
    """Main execution."""
    try:
        # Check dependencies
        if not check_dependencies():
            sys.exit(1)
        
        # Start server
        if not start_api_server():
            sys.exit(1)
        
        # Run tests
        success = run_tests()
        
        # Stop server
        stop_api_server()
        
        # Exit with test result
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        stop_api_server()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        stop_api_server()
        sys.exit(1)

if __name__ == "__main__":
    main()
