# Scripts Directory

Utility scripts for managing the Code Review System.

## ADK API Server Scripts (Recommended)

### Start ADK API Server
```bash
./scripts/start_adk_api_server.sh
```

**What it does:**
- Activates Python virtual environment
- Kills any existing process on port 8000
- Starts **official Google ADK API server** in background
- Uses SQLite for session persistence (`agent_workspace/sessions.db`)
- Enables auto-reload for agent code changes
- Saves PID to `logs/adk_api_server.pid`
- Waits for server to be healthy
- Shows OpenAPI documentation URLs

**Output:**
```
✅ ADK API Server is running!

Server Information:
   PID:  12345
   Host: 0.0.0.0
   Port: 8000

API Endpoints:
   OpenAPI Docs:    http://localhost:8000/docs
   OpenAPI JSON:    http://localhost:8000/openapi.json
   Agent Endpoints: http://localhost:8000/apps/orchestrator_agent/...
```

### Stop ADK API Server
```bash
./scripts/stop_adk_api_server.sh
```

**What it does:**
- Reads PID from `logs/adk_api_server.pid`
- Gracefully stops the ADK API server process
- Falls back to force kill if needed
- Cleans up PID file
- Also checks for processes on port 8000

---

## Custom API Server Scripts (Deprecated)

> **Note**: These scripts use a custom FastAPI implementation. **Use ADK API server instead** for better features and official support.

### Start Custom API Server
```bash
./scripts/start_api_server.sh
```

**What it does:**
- Activates Python virtual environment
- Checks/installs API dependencies (`requirements-api.txt`)
- Kills any existing process on port 8000
- Starts custom FastAPI server in background
- Saves PID to `logs/api_server.pid`
- Waits for server to be healthy
- Shows endpoints and recent logs

**Output:**
```
✅ API server is ready!
   PID: 12345
   URL: http://localhost:8000
   Logs: logs/api_server.log

Endpoints:
  GET  http://localhost:8000/health
  POST http://localhost:8000/api/github/webhook
  GET  http://localhost:8000/api/status/{session_id}
```

### Stop Custom API Server
```bash
./scripts/stop_api_server.sh
```

**What it does:**
- Reads PID from `logs/api_server.pid`
- Gracefully stops the server process
- Falls back to force kill if needed
- Cleans up PID file
- Also checks for processes on port 8000

### View Logs
```bash
# Follow logs in real-time
tail -f logs/api_server.log

# View last 50 lines
tail -50 logs/api_server.log

# View all logs
cat logs/api_server.log
```

## Usage Examples

### Basic Workflow
```bash
# 1. Start API server
./scripts/start_api_server.sh

# 2. In another terminal, run tests
python tests/api/test_github_webhook.py

# 3. When done, stop server
./scripts/stop_api_server.sh
```

### Development Workflow
```bash
# Terminal 1: Start server and follow logs
./scripts/start_api_server.sh && tail -f logs/api_server.log

# Terminal 2: Run tests
python tests/api/test_github_webhook.py

# Terminal 3: Make code changes, restart server
./scripts/stop_api_server.sh
./scripts/start_api_server.sh
```

### Quick Test
```bash
# Start server and test in one command
./scripts/start_api_server.sh && sleep 2 && curl http://localhost:8000/health
```

## Other Scripts

### Start ADK Web Server
```bash
./scripts/start_server.sh
```
Starts the ADK web UI at http://localhost:8800 (deferred - not actively used)

## Troubleshooting

### Port Already in Use
```bash
# Find what's using port 8000
lsof -i :8000

# Kill process
kill <PID>

# Or let start script handle it
./scripts/start_api_server.sh
```

### Server Won't Start
```bash
# Check logs
tail -50 logs/api_server.log

# Verify Python environment
source venv/bin/activate
python --version

# Check dependencies
pip list | grep fastapi
```

### Server Started But Not Responding
```bash
# Check if process is running
ps aux | grep api_server

# Check if port is listening
lsof -i :8000

# Test health endpoint
curl http://localhost:8000/health
```

### Clean Start
```bash
# Stop everything
./scripts/stop_api_server.sh

# Clean logs
rm -f logs/api_server.log logs/api_server.pid

# Fresh start
./scripts/start_api_server.sh
```

## File Locations

| File | Purpose |
|------|---------|
| `logs/api_server.log` | Server output and error logs |
| `logs/api_server.pid` | Process ID of running server |
| `scripts/start_api_server.sh` | Start server script |
| `scripts/stop_api_server.sh` | Stop server script |
| `api_server.py` | FastAPI application code |
| `requirements-api.txt` | API dependencies |

## Environment Variables

The API server uses environment variables from `.env`:

```bash
# GitHub Configuration (optional for testing with mock data)
GITHUB_TOKEN=your_github_token_here
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

# LLM Configuration
GEMINI_API_KEY=your_gemini_api_key_here
# or
OPENAI_API_KEY=your_openai_api_key_here
```

## Next Steps

1. **Start Server**: `./scripts/start_api_server.sh`
2. **Test Health**: `curl http://localhost:8000/health`
3. **Run Tests**: `python tests/api/test_github_webhook.py`
4. **View Logs**: `tail -f logs/api_server.log`
5. **Stop Server**: `./scripts/stop_api_server.sh`

For more details, see:
- `tests/api/README.md` - API testing guide
- `docs/API_TESTING_SUMMARY.md` - Quick start summary
