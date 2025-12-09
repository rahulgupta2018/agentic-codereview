



# Agentic Code Review System

Multi-agent AI system for comprehensive code review using Google ADK.

## 🌟 Features

- **Multi-Provider Support**: Works with Gemini, Ollama, OpenAI, and any ADK-compatible LLM
- **Intelligent Orchestration**: Classifier-based agent selection
- **4 Specialized Agents**: Code Quality, Security, Engineering Practices, Carbon Footprint
- **Smart Optimizations**: Code optimization (~20-30% token reduction), result caching (1hr TTL)
- **Rate Limit Protection**: Sequential execution with adaptive delays
- **State Management**: Artifact storage, session tracking, analysis history

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
cd /Users/rahulgupta/Documents/Coding/agentic-codereview
python3 -m venv venv

/opt/homebrew/bin/python3.12 -m venv venv && source venv/bin/activate && pip install --upgrade pip

# Activate environment
source venv/bin/activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure LLM Provider

**Option A: Google Gemini (Remote)**
```bash
# Edit .env
GOOGLE_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
```

**Option B: Ollama (Local)**
```bash
# Install and start Ollama
brew install ollama
ollama serve #Start ollama

# Test if ollama is working
ollama run llama3.2 "Say hello in one sentence"
curl -X POST http://localhost:11434/api/generate -d '{"model": "granite4:latest", "prompt": "Say hello in one sentence", "stream": false}'

# Pull models
ollama pull granite4:latest
ollama pull gemma3:latest

# Edit .env
OLLAMA_API_BASE=http://localhost:11434
OLLAMA_MODEL=ollama_chat/granite4:latest
OLLAMA_SUBAGENT_MODEL=ollama_chat/gemma3:latest

# Update util/llm_model.py (uncomment Ollama section)
```

**Option C: OpenAI**
```bash
# Edit .env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4-turbo

# Update util/llm_model.py to use LiteLlm with OpenAI
```

See [UNIVERSAL_LLM_WRAPPER.md](docs/UNIVERSAL_LLM_WRAPPER.md) for detailed provider setup.

## 🖥️ Usage

### ADK Interaction

## ADK Web UI (Interactive Testing)
Access at: http://localhost:8800/dev-ui

Start ADK web server:
```bash
cd /Users/rahulgupta/Documents/Coding/agentic-codereview/agent_workspace
adk web --host 0.0.0.0 --port 8800 .
```

Run in background:
```bash
pkill -f "adk web" && sleep 2 && cd /Users/rahulgupta/Documents/Coding/agentic-codereview/agent_workspace && /Users/rahulgupta/Documents/Coding/agentic-codereview/venv/bin/adk web --host 0.0.0.0 --port 8800 . > adk_web.log 2>&1 &
```

Check status:
```bash
ps aux | grep "adk web" | grep -v grep
```

Stop server:
```bash
pkill -f "adk web"
```

## ADK API Server (Production Integration)
**Official Google ADK REST API** at: http://localhost:8000

### Quick Start
```bash
# Start server (with SQLite sessions, auto-reload)
./scripts/start_adk_api_server.sh

# Stop server
./scripts/stop_adk_api_server.sh
```

### Manual Start
```bash
cd /Users/rahulgupta/Documents/Coding/agentic-codereview/agent_workspace

# Development mode
adk api_server \
  --host 0.0.0.0 \
  --port 8000 \
  --session_service_uri sqlite:///./sessions.db \
  --reload_agents \
  .

# Production mode (with PostgreSQL)
adk api_server \
  --host 0.0.0.0 \
  --port 8000 \
  --session_service_uri postgresql://user:pass@host:port/dbname \
  --trace_to_cloud \
  .
```

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Test API
```bash
# Create session
SESSION_RESPONSE=$(curl -s -X POST \
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

**See full guide**: [docs/ADK_API_SERVER_GUIDE.md](./docs/ADK_API_SERVER_GUIDE.md)

## CLI/Script Mode (Direct Execution)
```bash
cd /Users/rahulgupta/Documents/Coding/agentic-codereview
python main.py
```

## Key Features
- **Artifact Storage**: All code inputs, reports, and sub-agent outputs saved to `./artifacts/`
- **Session Persistence**: Session state maintained in `./sessions/`
- **Service Registry**: Global access to artifact and session services
- **Works with**: ADK Web UI, ADK API Server, and direct Python execution




ADK - adk -- help

Commands:
  api_server   Starts a FastAPI server for agents.
  conformance  Conformance testing tools for ADK.
  create       Creates a new app in the current folder with prepopulated agent template.
  deploy       Deploys agent to hosted environments.
  eval         Evaluates an agent given the eval sets.
  eval_set     Manage Eval Sets.
  run          Runs an interactive CLI for a certain agent.
  web          Starts a FastAPI server with Web UI for agents.

  adk api_server --help

  Test the flow 
  ./scripts/stop_adk_api_server.sh && sleep 2 && ./scripts/start_adk_api_server.sh