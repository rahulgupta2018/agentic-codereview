#!/bin/bash
#================================================================================
# Stop ADK API Server
#
# Gracefully stops the ADK API server started by start_adk_api_server.sh
#================================================================================

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
PID_FILE="$LOG_DIR/adk_api_server.pid"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  ADK API Server Stopper${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    echo -e "${YELLOW}⚠️  No PID file found at: $PID_FILE${NC}"
    echo -e "${YELLOW}Attempting to find and kill process...${NC}"
    
    # Try to find by process name
    PIDS=$(pgrep -f "adk api_server")
    if [ ! -z "$PIDS" ]; then
        echo -e "${YELLOW}Found processes: $PIDS${NC}"
        for PID in $PIDS; do
            echo -e "${YELLOW}Killing process $PID...${NC}"
            kill $PID 2>/dev/null
        done
        sleep 2
        
        # Check if still running
        REMAINING=$(pgrep -f "adk api_server")
        if [ ! -z "$REMAINING" ]; then
            echo -e "${RED}Processes still running, forcing kill...${NC}"
            pkill -9 -f "adk api_server"
        fi
        echo -e "${GREEN}✅ Processes terminated${NC}"
    else
        echo -e "${YELLOW}No running ADK API server process found${NC}"
    fi
    
    # Also check port 8000
    PORT_PID=$(lsof -ti:8000)
    if [ ! -z "$PORT_PID" ]; then
        echo -e "${YELLOW}Found process on port 8000 (PID: $PORT_PID), killing...${NC}"
        kill -9 $PORT_PID
        echo -e "${GREEN}✅ Port 8000 cleared${NC}"
    fi
    
    exit 0
fi

# Read PID from file
PID=$(cat "$PID_FILE")
echo -e "${BLUE}📋 PID from file: $PID${NC}"

# Check if process is running
if ! ps -p $PID > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Process $PID is not running${NC}"
    rm -f "$PID_FILE"
    echo -e "${GREEN}✅ Cleaned up PID file${NC}"
    exit 0
fi

# Graceful shutdown
echo -e "${YELLOW}🛑 Sending SIGTERM to process $PID...${NC}"
kill $PID

# Wait for process to exit
echo -e "${YELLOW}⏳ Waiting for process to exit...${NC}"
WAIT_COUNT=0
MAX_WAIT=10

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if ! ps -p $PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Process exited gracefully${NC}"
        rm -f "$PID_FILE"
        echo -e "${GREEN}✅ Cleaned up PID file${NC}"
        exit 0
    fi
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    echo -n "."
done

# Force kill if still running
echo -e ""
echo -e "${RED}⚠️  Process didn't exit gracefully, forcing kill...${NC}"
kill -9 $PID 2>/dev/null

if ! ps -p $PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Process force-killed${NC}"
    rm -f "$PID_FILE"
    echo -e "${GREEN}✅ Cleaned up PID file${NC}"
else
    echo -e "${RED}❌ Failed to kill process${NC}"
    exit 1
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
