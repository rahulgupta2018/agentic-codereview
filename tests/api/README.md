# API Testing Guide

## Overview

This guide shows how to test the GitHub PR code review pipeline via REST API endpoints. **All testing is done through HTTP API calls**, not direct Python imports, to ensure we test the production workflow.

## Architecture

```
Client (Test Script)
    ↓ HTTP POST
┌─────────────────────────────────────┐
│  FastAPI Server (api_server.py)    │
│  Port: 8000                         │
└─────────────────────────────────────┘
    ↓ Background Task
┌─────────────────────────────────────┐
│  GitHubPipeline (SequentialAgent)  │
│  ├─ GitHubFetcher                   │
│  ├─ PlanningAgent                   │
│  ├─ DynamicRouterAgent              │
│  │   ├─ SecurityAgent        (1st)  │
│  │   ├─ CodeQualityAgent     (2nd)  │
│  │   ├─ EngineeringAgent     (3rd)  │
│  │   └─ CarbonAgent          (4th)  │
│  ├─ ReportSynthesizer               │
│  └─ GitHubPublisher                 │
└─────────────────────────────────────┘
    ↓ Artifacts Saved
┌─────────────────────────────────────┐
│  storage_bucket/artifacts/          │
│  ├─ sub_agent_outputs/              │
│  │   ├─ analysis_*_security.json    │
│  │   ├─ analysis_*_quality.json     │
│  │   ├─ analysis_*_engineering.json │
│  │   └─ analysis_*_carbon.json      │
│  └─ reports/                        │
│      └─ report_*.md                 │
└─────────────────────────────────────┘
```

## Quick Start

### 1. Install API Dependencies

```bash
pip install -r requirements-api.txt
```

This installs:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `httpx` - Async HTTP client for testing
- `pydantic` - Data validation

### 2. Start API Server

```bash
# Start server (development mode with auto-reload)
python api_server.py
```

Server will start at `http://localhost:8000`

Expected output:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
✅ Session service initialized
✅ Artifact service initialized
✅ Root agent: GitHubPipeline
✅ Agent registry: 4 agents
```

### 3. Verify Server Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-07T10:30:00",
  "service": "code-review-api",
  "root_agent": "GitHubPipeline",
  "agents_available": 4
}
```

### 4. Run Automated Test Suite

```bash
# Option 1: Automated (starts/stops server automatically)
python tests/api/run_api_tests.py

# Option 2: Manual (server already running)
python tests/api/test_github_webhook.py
```

## API Endpoints

### GET /health

Health check endpoint.

**Request:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-07T10:30:00.123456",
  "service": "code-review-api",
  "root_agent": "GitHubPipeline",
  "agents_available": 4
}
```

### POST /api/github/webhook

Submit GitHub PR for code review.

**Request:**
```bash
curl -X POST http://localhost:8000/api/github/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "action": "opened",
    "number": 123,
    "pull_request": {
      "title": "Add authentication feature",
      "body": "PR description...",
      "head": {"sha": "abc123"},
      "base": {"ref": "main"},
      "user": {"login": "developer"}
    },
    "repository": {
      "name": "test-repo",
      "owner": {"login": "test-org"},
      "full_name": "test-org/test-repo"
    }
  }'
```

**Response (202 Accepted):**
```json
{
  "status": "queued",
  "session_id": "abc123-def456-...",
  "message": "Code review queued for PR #123",
  "pr_number": 123,
  "repository": "test-org/test-repo"
}
```

### GET /api/status/{session_id}

Check pipeline execution status.

**Request:**
```bash
curl http://localhost:8000/api/status/abc123-def456-...
```

**Response (In Progress):**
```json
{
  "session_id": "abc123-def456-...",
  "status": "in_progress",
  "created_at": "2025-12-07T10:30:00",
  "updated_at": "2025-12-07T10:30:15",
  "pr_number": 123,
  "repository": "test-org/test-repo",
  "artifacts_generated": 2,
  "report_ready": false
}
```

**Response (Completed):**
```json
{
  "session_id": "abc123-def456-...",
  "status": "completed",
  "created_at": "2025-12-07T10:30:00",
  "updated_at": "2025-12-07T10:32:30",
  "pr_number": 123,
  "repository": "test-org/test-repo",
  "artifacts_generated": 4,
  "report_ready": true
}
```

## Test Flow

The test suite validates the complete workflow:

1. **Health Check** (`test_health_check`)
   - Verifies API server is running
   - Checks orchestrator loaded correctly
   - Validates agent registry

2. **Submit Webhook** (`test_github_webhook`)
   - POST mock GitHub PR payload
   - Verifies webhook accepted (202)
   - Extracts session ID for tracking

3. **Poll Status** (`test_status_polling`)
   - Poll `/api/status/{session_id}` every 5 seconds
   - Track status: queued → in_progress → completed
   - Max wait: 300 seconds (5 minutes)

4. **Verify Results** (`test_full_workflow`)
   - Check artifacts created in storage_bucket
   - Verify all 4 analysis agents executed
   - Confirm report generated
   - Validate sequential execution order in logs

## Mock PR Payload

The test suite includes a realistic mock PR with security issues:

```python
{
    "action": "opened",
    "number": 123,
    "pull_request": {
        "title": "Add authentication feature",
        "body": "Adds JWT authentication...",
        "files": [
            {
                "filename": "src/auth/middleware.py",
                "patch": """
                    # Contains:
                    # 1. Hardcoded secret key (security issue)
                    # 2. SQL injection vulnerability
                    # 3. Missing error handling
                """
            }
        ]
    }
}
```

**Expected Agent Selection:**
- ✅ SecurityAgent (finds hardcoded secrets, SQL injection)
- ✅ CodeQualityAgent (analyzes complexity, code smells)
- ✅ EngineeringAgent (checks best practices)
- ✅ CarbonAgent (estimates carbon footprint)

## Verification Steps

After test completion, verify artifacts:

```bash
# Check artifacts directory
ls -la storage_bucket/artifacts/

# Check analysis outputs
ls -la storage_bucket/artifacts/orchestrator_agent/*/sub_agent_outputs/

# Check final report
ls -la storage_bucket/artifacts/orchestrator_agent/*/reports/

# View a report
cat storage_bucket/artifacts/orchestrator_agent/*/reports/report_*.md
```

## Sequential Execution Verification

Check logs to verify sequential execution (not parallel):

```
📝 [Session xxx] Phase 1: SecurityAgent starting...
📝 [Session xxx] SecurityAgent completed (artifacts saved)
📝 [Session xxx] Phase 2: CodeQualityAgent starting...
📝 [Session xxx] CodeQualityAgent completed (artifacts saved)
📝 [Session xxx] Phase 3: EngineeringAgent starting...
📝 [Session xxx] EngineeringAgent completed (artifacts saved)
📝 [Session xxx] Phase 4: CarbonAgent starting...
📝 [Session xxx] CarbonAgent completed (artifacts saved)
✅ [Session xxx] All agents completed sequentially
```

## Production Deployment

### Option 1: ngrok Tunnel (Testing)

```bash
# Terminal 1: Start API server
python api_server.py

# Terminal 2: Create tunnel
ngrok http 8000

# Configure GitHub webhook
# URL: https://xxx.ngrok.io/api/github/webhook
# Events: Pull requests (opened, synchronize, reopened)
```

### Option 2: Cloud Deployment

Deploy to cloud platform:
- Google Cloud Run
- AWS Lambda + API Gateway
- Azure Functions

See `docs/GITHUB_INTEGRATION.md` for deployment details.

## Troubleshooting

### Server Won't Start

```bash
# Check if port 8000 is already in use
lsof -i :8000

# Kill existing process
kill -9 <PID>

# Or use different port
uvicorn api_server:app --port 8001
```

### Tests Timeout

- Increase `max_wait` in `test_status_polling()` (default: 300s)
- Check API server logs for errors
- Verify agents are executing (check logs)
- Check LLM API connectivity (Gemini/OpenAI)

### No Artifacts Created

- Check `storage_bucket/artifacts/` permissions
- Verify artifact service initialized correctly
- Check agent logs for save errors
- Ensure agents completed successfully

## Next Steps

1. **Install dependencies**: `pip install -r requirements-api.txt`
2. **Start server**: `python api_server.py`
3. **Run tests**: `python tests/api/run_api_tests.py`
4. **Verify artifacts**: Check `storage_bucket/artifacts/`
5. **Review logs**: Confirm sequential execution
6. **Test with real PR**: Use ngrok tunnel + GitHub webhook

## Support

For issues or questions:
- Check logs in terminal where `api_server.py` is running
- Review `storage_bucket/sessions/` for session state
- Verify agent configuration in `agent_workspace/orchestrator_agent/agent.py`
