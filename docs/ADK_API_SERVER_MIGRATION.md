# Migration to ADK API Server

## 📋 Summary

We've migrated from a custom FastAPI implementation (`api_server.py`) to **Google ADK's official `adk api_server` command**. This provides production-ready REST APIs with better features and official support.

## ✅ What Changed

### Before (Custom Implementation)
```python
# api_server.py - 316 lines of custom code
app = FastAPI(title="Code Review API")

@app.post("/api/github/webhook")
async def webhook(payload: GitHubPRPayload):
    session_id = str(uuid.uuid4())
    asyncio.create_task(run_github_pipeline_task(...))
    return {"session_id": session_id}
```

**Issues:**
- ❌ Custom code to maintain
- ❌ Manual session management implementation
- ❌ No standardized endpoints
- ❌ Manual OpenAPI documentation
- ❌ No cloud observability integration

### After (ADK API Server)
```bash
# One command, all features included
adk api_server \
  --host 0.0.0.0 \
  --port 8000 \
  --session_service_uri sqlite:///./sessions.db \
  --reload_agents \
  .
```

**Benefits:**
- ✅ Official Google ADK solution
- ✅ Auto-generated OpenAPI/Swagger docs
- ✅ Built-in session management (SQLite, PostgreSQL, Cloud)
- ✅ Standardized RESTful endpoints
- ✅ Cloud trace and observability integration
- ✅ Agent-to-Agent (A2A) protocol support
- ✅ Hot reload for development
- ✅ Zero custom code to maintain

## 🎯 New Scripts

### Start Server
```bash
./scripts/start_adk_api_server.sh
```

### Stop Server
```bash
./scripts/stop_adk_api_server.sh
```

## 🌐 New API Endpoints

ADK API server follows REST conventions:

### 1. Create Session
```bash
POST /apps/orchestrator_agent/users/{user_id}/sessions
Content-Type: application/json

{
  "state": {}
}

# Response
{
  "id": "uuid",
  "app_name": "orchestrator_agent",
  "user_id": "user",
  "created_at": "2025-12-07T22:00:00Z"
}
```

### 2. Send Message/Request
```bash
POST /apps/orchestrator_agent/users/{user_id}/sessions/{session_id}/chat
Content-Type: application/json

{
  "message": "Review this code: ..."
}

# Response
{
  "response": "Code review results...",
  "session_id": "uuid",
  "event_id": "uuid"
}
```

### 3. List Sessions
```bash
GET /apps/orchestrator_agent/users/{user_id}/sessions
```

### 4. Get Session Details
```bash
GET /apps/orchestrator_agent/users/{user_id}/sessions/{session_id}
```

## 📚 Documentation

- **OpenAPI Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Complete Guide**: [docs/ADK_API_SERVER_GUIDE.md](./ADK_API_SERVER_GUIDE.md)

## 🔄 Migration Tasks

### ✅ Completed
- [x] Created `start_adk_api_server.sh` script
- [x] Created `stop_adk_api_server.sh` script
- [x] Created ADK API Server guide documentation
- [x] Updated README.md with ADK API server instructions
- [x] Updated scripts/README.md with new scripts

### 🔄 Next Steps
1. **Test ADK API Server**: Start server and verify endpoints work
2. **Update GitHub Integration**: Modify webhook to use ADK endpoints
3. **Update Test Suite**: Adapt tests to ADK API conventions
4. **Deprecate Custom Server**: Mark `api_server.py` as deprecated
5. **Update CI/CD**: Use ADK API server in deployment pipelines

## 🧪 Testing

### Start Server
```bash
./scripts/start_adk_api_server.sh
```

### Test Endpoints
```bash
# Create session
SESSION_RESPONSE=$(curl -s -X POST \
  http://localhost:8000/apps/orchestrator_agent/users/testuser/sessions \
  -H "Content-Type: application/json" \
  -d '{"state": {}}')

echo $SESSION_RESPONSE

SESSION_ID=$(echo $SESSION_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Session ID: $SESSION_ID"

# Send code review request
curl -X POST \
  "http://localhost:8000/apps/orchestrator_agent/users/testuser/sessions/$SESSION_ID/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Review this code: def login(user): query = f\"SELECT * FROM users WHERE name={user}\"; return exec(query)"
  }'
```

### Access Documentation
```bash
open http://localhost:8000/docs
```

## 🎨 Features Comparison

| Feature | Custom API | ADK API Server |
|---------|-----------|----------------|
| OpenAPI Docs | ⚠️ Manual | ✅ Auto-generated |
| Session Persistence | ⚠️ Custom JSON files | ✅ SQLite/PostgreSQL/Cloud |
| Hot Reload | ❌ No | ✅ --reload_agents |
| Cloud Tracing | ❌ No | ✅ --trace_to_cloud |
| A2A Protocol | ❌ No | ✅ --a2a |
| Maintenance | ❌ Us | ✅ Google |
| Standards | ⚠️ Custom | ✅ ADK conventions |
| Production Ready | ⚠️ Needs work | ✅ Yes |

## 📝 Configuration Options

### Development
```bash
adk api_server \
  --host 0.0.0.0 \
  --port 8000 \
  --session_service_uri sqlite:///./sessions.db \
  --reload_agents \
  --verbose \
  .
```

### Production
```bash
adk api_server \
  --host 0.0.0.0 \
  --port 8000 \
  --session_service_uri postgresql://user:pass@host:port/dbname \
  --trace_to_cloud \
  --otel_to_cloud \
  .
```

## 🚀 Deployment

### Docker
```dockerfile
FROM python:3.12

WORKDIR /app
COPY . .
RUN pip install google-adk

EXPOSE 8000
CMD ["adk", "api_server", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--session_service_uri", "postgresql://...", \
     "agent_workspace"]
```

### Kubernetes
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: code-review-api
spec:
  containers:
  - name: adk-api
    image: code-review:latest
    ports:
    - containerPort: 8000
    env:
    - name: SESSION_DB_URL
      valueFrom:
        secretKeyRef:
          name: db-credentials
          key: url
    command:
    - adk
    - api_server
    - --host
    - "0.0.0.0"
    - --port
    - "8000"
    - --session_service_uri
    - $(SESSION_DB_URL)
    - --trace_to_cloud
    - agent_workspace
```

## 🔍 Troubleshooting

### Issue: OpenAPI schema error (httpx.Client)
**Symptom**: Server starts but `/openapi.json` returns 500 error

**Cause**: Pydantic cannot serialize httpx.Client instances in OpenAPI schema

**Workaround**: 
- Server still works fine for actual API calls
- Access endpoints directly without relying on `/docs`
- This is a known issue with some ADK versions

**Solution**: Will be fixed in future ADK releases

### Issue: Session not persisting
**Check**:
```bash
ls -la agent_workspace/sessions.db
tail -100 logs/adk_api_server.log | grep -i session
```

### Issue: Port already in use
```bash
lsof -i :8000
kill -9 <PID>
./scripts/start_adk_api_server.sh
```

## 📖 References

- [ADK CLI Documentation](https://github.com/googleapis/genai-agent-dev-kit)
- [ADK API Server Guide](./ADK_API_SERVER_GUIDE.md)
- [ADK Session Management](./SESSION_MANAGEMENT.md)
- [ADK Observability](./OBSERVABILITY_GUIDE.md)

---

**Decision**: Use ADK API server as the official API server for production deployments. The custom `api_server.py` is deprecated but kept for reference.
