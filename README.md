



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
ollama serve

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
Access at: http://localhost:8000

Start ADK API server:
```bash
cd /Users/rahulgupta/Documents/Coding/agentic-codereview/agent_workspace
adk api --host 0.0.0.0 --port 8000 .
```

Run in background:
```bash
pkill -f "adk api" && sleep 2 && cd /Users/rahulgupta/Documents/Coding/agentic-codereview/agent_workspace && /Users/rahulgupta/Documents/Coding/agentic-codereview/venv/bin/adk api --host 0.0.0.0 --port 8000 . > adk_api.log 2>&1 &


pkill -f "adk web" && sleep 2 && /Users/rahulgupta/Documents/Coding/agentic-codereview/venv/bin/adk web --host 0.0.0.0 --port 8800 . > adk_web.log 2>&1 &
```

Check API health:
```bash
curl http://localhost:8000/health
```

Test code review via API:
```bash
curl -X POST http://localhost:8000/apps/orchestrator_agent/users/user/sessions \
  -H "Content-Type: application/json" \
  -d '{"state": {}}'
# Returns session_id, use it for chat:
curl -X POST http://localhost:8000/apps/orchestrator_agent/users/user/sessions/{session_id}/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Review this code: def login(user): query = f\"SELECT * FROM users WHERE name={user}\"; return exec(query)"}'
```

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




