# ADK API Server Guide

## Overview

Google ADK provides a built-in `adk api_server` command that creates production-ready REST APIs for agents. This is the **recommended approach** instead of custom FastAPI implementations.

## ✅ Why Use ADK API Server?

| Feature | ADK API Server | Custom FastAPI |
|---------|----------------|----------------|
| **Official Support** | ✅ Built by Google | ❌ Maintained by us |
| **OpenAPI/Swagger** | ✅ Auto-generated | ⚠️ Manual setup |
| **Session Management** | ✅ SQLite, PostgreSQL, Agent Engine | ⚠️ Custom implementation |
| **A2A Protocol** | ✅ Built-in (--a2a flag) | ❌ Not available |
| **Hot Reload** | ✅ --reload_agents | ⚠️ Manual restart |
| **Cloud Observability** | ✅ --trace_to_cloud, --otel_to_cloud | ⚠️ Custom setup |
| **Standardized Endpoints** | ✅ ADK conventions | ⚠️ Custom design |

## 🚀 Quick Start

### Start Server
```bash
./scripts/start_adk_api_server.sh
```

### Stop Server
```bash
./scripts/stop_adk_api_server.sh
```

## 📋 Manual Commands

### Basic Start
```bash
cd /Users/rahulgupta/Documents/Coding/agentic-codereview/agent_workspace

adk api_server \
  --host 0.0.0.0 \
  --port 8000 \
  --session_service_uri sqlite:///./sessions.db \
  .
```

### Development Mode (with hot reload)
```bash
adk api_server \
  --host 0.0.0.0 \
  --port 8000 \
  --session_service_uri sqlite:///./sessions.db \
  --reload_agents \
  --verbose \
  .
```

### Production Mode (with cloud tracing)
```bash
adk api_server \
  --host 0.0.0.0 \
  --port 8000 \
  --session_service_uri postgresql://user:pass@host:port/dbname \
  --trace_to_cloud \
  --otel_to_cloud \
  .
```

## 🌐 API Endpoints

ADK API server exposes these endpoints:

### OpenAPI Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Session Management
```bash
# Create session
POST http://localhost:8000/apps/orchestrator_agent/users/{user_id}/sessions
Content-Type: application/json

{
  "state": {}
}

# Response
{
  "id": "session_uuid",
  "app_name": "orchestrator_agent",
  "user_id": "user",
  "state": {},
  "created_at": "2025-12-07T22:00:00Z"
}
```

### Chat/Interaction
```bash
# Send message to agent
POST http://localhost:8000/apps/orchestrator_agent/users/{user_id}/sessions/{session_id}/chat
Content-Type: application/json

{
  "message": "Review this code: ..."
}

# Response
{
  "response": "Code review results...",
  "session_id": "session_uuid",
  "event_id": "event_uuid"
}
```

### List Sessions
```bash
# Get all sessions for a user
GET http://localhost:8000/apps/orchestrator_agent/users/{user_id}/sessions

# Response
[
  {
    "id": "session_uuid",
    "app_name": "orchestrator_agent",
    "user_id": "user",
    "created_at": "2025-12-07T22:00:00Z"
  }
]
```

### Get Session Details
```bash
# Get specific session
GET http://localhost:8000/apps/orchestrator_agent/users/{user_id}/sessions/{session_id}

# Response
{
  "id": "session_uuid",
  "app_name": "orchestrator_agent",
  "user_id": "user",
  "state": {...},
  "events": [...]
}
```

## 🧪 Testing Examples

### Using curl
```bash
# Create session
SESSION_RESPONSE=$(curl -X POST \
  http://localhost:8000/apps/orchestrator_agent/users/testuser/sessions \
  -H "Content-Type: application/json" \
  -d '{"state": {}}')

SESSION_ID=$(echo $SESSION_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

# Send code review request
curl -X POST \
  "http://localhost:8000/apps/orchestrator_agent/users/testuser/sessions/$SESSION_ID/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Review this code: def login(user): query = f\"SELECT * FROM users WHERE name={user}\"; return exec(query)"
  }'
```

### Using Python
```python
import httpx
import asyncio

async def test_code_review():
    async with httpx.AsyncClient() as client:
        # Create session
        session_resp = await client.post(
            "http://localhost:8000/apps/orchestrator_agent/users/testuser/sessions",
            json={"state": {}}
        )
        session_id = session_resp.json()["id"]
        
        # Send code review request
        review_resp = await client.post(
            f"http://localhost:8000/apps/orchestrator_agent/users/testuser/sessions/{session_id}/chat",
            json={"message": "Review this code: ..."}
        )
        print(review_resp.json())

asyncio.run(test_code_review())
```

## ⚙️ Configuration Options

### Session Service URIs

| Type | URI Format | Use Case |
|------|------------|----------|
| **SQLite** | `sqlite:///path/to/db.db` | Local development |
| **PostgreSQL** | `postgresql://user:pass@host:port/db` | Production |
| **Agent Engine** | `agentengine://<resource_id>` | Google Cloud |

### Command Line Flags

```bash
adk api_server --help
```

Important flags:
- `--host TEXT` - Binding host (default: 127.0.0.1)
- `--port INTEGER` - Server port
- `--session_service_uri TEXT` - Session storage backend
- `--artifact_service_uri TEXT` - Artifact storage (e.g., gs://bucket)
- `--reload_agents` - Auto-reload agents on code changes
- `--verbose` or `-v` - Enable DEBUG logging
- `--trace_to_cloud` - Send traces to Google Cloud
- `--otel_to_cloud` - Send OpenTelemetry data to Cloud Observability
- `--a2a` - Enable Agent-to-Agent protocol
- `--url_prefix TEXT` - URL prefix for reverse proxy (e.g., '/api/v1')

## 🔍 Debugging

### View Logs
```bash
tail -f logs/adk_api_server.log
```

### Check Server Status
```bash
# Check if process is running
ps aux | grep "adk api_server"

# Check port
lsof -i :8000

# Test health
curl http://localhost:8000/docs
```

### Common Issues

**Issue**: Server won't start
```bash
# Check if port is in use
lsof -i :8000

# Kill existing process
pkill -f "adk api_server"

# Try again
./scripts/start_adk_api_server.sh
```

**Issue**: Pydantic schema error (httpx.Client)
- This is a known issue with some ADK versions
- Workaround: Server still works, just OpenAPI schema generation fails
- Alternative: Access endpoints directly without /docs

**Issue**: Session not persisting
```bash
# Check session DB exists
ls -la agent_workspace/sessions.db

# Check logs for database errors
tail -100 logs/adk_api_server.log | grep -i error
```

## 📊 Comparison: ADK API Server vs Custom FastAPI

### Our Previous Approach (api_server.py)
```python
# Custom FastAPI server
app = FastAPI()

@app.post("/api/github/webhook")
async def webhook(payload: GitHubPRPayload):
    # Custom implementation
    session_id = str(uuid.uuid4())
    asyncio.create_task(run_pipeline(payload))
    return {"session_id": session_id}
```

### ADK API Server Approach
```bash
# One command, all features included
adk api_server \
  --session_service_uri sqlite:///./sessions.db \
  .
```

**Benefits of switching:**
- ✅ No custom code to maintain
- ✅ Automatic OpenAPI docs
- ✅ Standardized session management
- ✅ Built-in A2A protocol support
- ✅ Cloud observability integration
- ✅ Hot reload for development

## 🎯 Next Steps

1. **Test the ADK API server**:
   ```bash
   ./scripts/start_adk_api_server.sh
   open http://localhost:8000/docs
   ```

2. **Migrate webhook integration**:
   - Use ADK API endpoints instead of custom `/api/github/webhook`
   - Adapt GitHub webhook to POST to ADK session/chat endpoints

3. **Update tests**:
   - Modify test suite to use ADK API conventions
   - Test session creation → chat → results flow

4. **Production deployment**:
   - Switch to PostgreSQL session service
   - Enable cloud tracing
   - Set up reverse proxy with `--url_prefix`

## 📚 References

- [ADK CLI Documentation](https://github.com/googleapis/genai-agent-dev-kit)
- [ADK API Server Help](run `adk api_server --help`)
- [ADK Session Management](./docs/SESSION_MANAGEMENT.md)
- [ADK Observability](./docs/OBSERVABILITY_GUIDE.md)

---

**Note**: The custom `api_server.py` is now **deprecated** in favor of ADK's built-in API server. Update all integrations to use the standardized ADK endpoints.
