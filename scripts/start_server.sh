#!/bin/bash
# Start ADK web server with custom session and artifact services

# Navigate to project root, then to agent_workspace
cd "$(dirname "$0")/.." && cd agent_workspace

# Kill any existing adk web process
pkill -f "adk web" 2>/dev/null
sleep 2

# Start ADK web server
# Note: ADK uses in-memory sessions by default
# Our FileArtifactService is initialized by the orchestrator agent
echo "🚀 Starting ADK web server..."
echo "   Artifact storage: ../storage_bucket/artifacts"
echo "   Port: 8800"
echo "   (Sessions: ADK in-memory, artifacts saved by FileArtifactService)"
echo ""

adk web \
  --host 0.0.0.0 \
  --port 8800 \
  . > adk_web.log 2>&1 &

sleep 4

echo "✅ Server started"
echo ""
echo "📋 Recent log:"
tail -20 adk_web.log
