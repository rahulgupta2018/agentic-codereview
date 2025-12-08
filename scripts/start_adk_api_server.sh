#!/bin/bash
#================================================================================
# Start ADK API Server (Google ADK Built-in)
#
# This script starts the official Google ADK API server with:
# - SQLite session persistence
# - Auto-reload for development
# - OpenAPI/Swagger documentation at http://localhost:8000/docs
#================================================================================

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
AGENT_WORKSPACE="$PROJECT_ROOT/agent_workspace"
VENV_PATH="$PROJECT_ROOT/venv"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/adk_api_server.log"
PID_FILE="$LOG_DIR/adk_api_server.pid"
SESSION_DIR="$PROJECT_ROOT/data/sessions"
SESSION_DB="$SESSION_DIR/sessions.db"

# Configuration
HOST="0.0.0.0"
PORT=8000

# Use environment variable if set, otherwise use default SQLite
if [ -z "$SESSION_DB_URI" ]; then
    SESSION_DB_URI="sqlite:///$SESSION_DB"
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  ADK API Server Starter${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}❌ Virtual environment not found at: $VENV_PATH${NC}"
    echo -e "${YELLOW}Please create one with: python -m venv venv${NC}"
    exit 1
fi

echo -e "${BLUE}📦 Activating virtual environment...${NC}"
source "$VENV_PATH/bin/activate"

# Create required directories if they don't exist
mkdir -p "$LOG_DIR"
mkdir -p "$SESSION_DIR"

# Kill any existing process on port 8000
echo -e "${YELLOW}🔍 Checking for existing process on port $PORT...${NC}"
EXISTING_PID=$(lsof -ti:$PORT)
if [ ! -z "$EXISTING_PID" ]; then
    echo -e "${YELLOW}⚠️  Killing existing process (PID: $EXISTING_PID)${NC}"
    kill -9 $EXISTING_PID 2>/dev/null
    sleep 2
fi
# Start ADK API server
echo -e "${GREEN}🚀 Starting ADK API server...${NC}"
echo -e "${BLUE}   Agent workspace: $AGENT_WORKSPACE${NC}"
echo -e "${BLUE}   Session DB URI: $SESSION_DB_URI${NC}"
echo -e "${BLUE}   Log file: $LOG_FILE${NC}"

cd "$AGENT_WORKSPACE"

# Start server in background with nohup
nohup "$VENV_PATH/bin/adk" api_server \
    --host "$HOST" \
    --port "$PORT" \
    --session_service_uri "$SESSION_DB_URI" \
    --reload_agents \
    . > "$LOG_FILE" 2>&1 &

# Give it a moment to start and get the actual Python process PID
sleep 2

# Find the actual adk api_server process PID (not the shell wrapper)
SERVER_PID=$(pgrep -f "adk api_server.*$PORT" | head -1)

if [ -z "$SERVER_PID" ]; then
    echo -e "${RED}❌ Failed to find server process${NC}"
    echo -e "${YELLOW}Last 50 lines of logs:${NC}"
    tail -50 "$LOG_FILE"
    exit 1
fi

echo $SERVER_PID > "$PID_FILE"

echo -e "${GREEN}✅ Server started with PID: $SERVER_PID${NC}"
echo -e "${BLUE}   PID saved to: $PID_FILE${NC}"

# Wait for server to be ready
echo -e "${YELLOW}⏳ Waiting for server to be ready...${NC}"
MAX_WAIT=30
WAIT_COUNT=0

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    # Check if process is still running
    if ! pgrep -f "adk api_server.*$PORT" > /dev/null 2>&1; then
        echo -e "${RED}❌ Server process died during startup${NC}"
        echo -e "${YELLOW}Last 50 lines of logs:${NC}"
        tail -50 "$LOG_FILE"
        exit 1
    fi
    
    # Try to connect to the server's docs endpoint (root may not exist)
    if curl -s -f http://localhost:$PORT/docs > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Server is ready!${NC}"
        break
    fi
    
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    if [ $((WAIT_COUNT % 5)) -eq 0 ]; then
        echo -n "."
    fi
done

echo ""  # New line after dots

if [ $WAIT_COUNT -eq $MAX_WAIT ]; then
    echo -e "${YELLOW}⚠️  Server didn't respond to health check within ${MAX_WAIT}s${NC}"
    echo -e "${YELLOW}Checking if server is actually running...${NC}"
    
    # Final check if server is running
    if pgrep -f "adk api_server.*$PORT" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Process is running! Server may still be starting up.${NC}"
        echo -e "${YELLOW}Check logs: tail -f $LOG_FILE${NC}"
    else
        echo -e "${RED}❌ Process not found${NC}"
        exit 1
    fi
fi

echo -e ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ ADK API Server is running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e ""
echo -e "${BLUE}📌 Server Information:${NC}"
echo -e "   PID:  $SERVER_PID"
echo -e "   Host: $HOST"
echo -e "   Port: $PORT"
echo -e ""
echo -e "${BLUE}🌐 API Endpoints:${NC}"
echo -e "   OpenAPI Docs:    ${GREEN}http://localhost:$PORT/docs${NC}"
echo -e "   OpenAPI JSON:    ${GREEN}http://localhost:$PORT/openapi.json${NC}"
echo -e "   Agent Endpoints: ${GREEN}http://localhost:$PORT/apps/orchestrator_agent/...${NC}"
echo -e ""
echo -e "${BLUE}📝 Management Commands:${NC}"
echo -e "   Stop server:     ${YELLOW}$SCRIPT_DIR/stop_adk_api_server.sh${NC}"
echo -e "   View logs:       ${YELLOW}tail -f $LOG_FILE${NC}"
echo -e "   Check status:    ${YELLOW}ps -p $SERVER_PID${NC}"
echo -e ""
echo -e "${BLUE}🧪 Test API:${NC}"
echo -e "   ${YELLOW}curl http://localhost:$PORT/docs${NC}"
echo -e ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📋 Recent logs:${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
tail -15 "$LOG_FILE"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
