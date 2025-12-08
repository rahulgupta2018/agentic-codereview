# Documentation Index

## Observability & Tracing

ADK provides built-in observability for tracking agent executions, tool calls, and LLM usage.

### Quick Start
- **[OBSERVABILITY_QUICKSTART.md](OBSERVABILITY_QUICKSTART.md)** - Get started in 5 minutes
  - Visual UI access
  - Command-line analyzer
  - Common use cases

### Detailed Guides
- **[OBSERVABILITY_GUIDE.md](OBSERVABILITY_GUIDE.md)** - Complete reference
  - Trace data structure
  - API endpoints
  - Python examples
  - Advanced patterns

### Tools
- **`scripts/analyze_traces.py`** - Analyze traces from command line
  ```bash
  # Analyze most recent session
  python scripts/analyze_traces.py
  
  # Analyze specific session
  python scripts/analyze_traces.py <session_id>
  ```

## Model Configuration

- **`util/llm_model.py`** - Centralized model configuration
- **`util/README.md`** - Model switching guide
- **`util/README_GEMINI_CONFIG.md`** - Gemini-specific configuration

## Testing

- **`tests/unit/test_ollama_model_eval.py`** - Model evaluation harness
- **`tests/unit/MODEL_PARAMETERS_GUIDE.md`** - Parameter tuning guide
- **`tests/unit/TEMPERATURE_COMPARISON_RESULTS.md`** - Test results

## Access Points

| Resource | URL/Location |
|----------|--------------|
| ADK Dev UI | http://localhost:8800/dev-ui |
| Trace API | http://localhost:8800/debug/trace/session/{session_id} |
| Session API | http://localhost:8800/apps/orchestrator_agent/users/user/sessions |
| Server Logs | `agent_workspace/adk_web.log` |
| Trace Analyzer | `scripts/analyze_traces.py` |

## Quick Actions

```bash
# View server logs
tail -f agent_workspace/adk_web.log

# Analyze traces
python scripts/analyze_traces.py

# Test server
curl http://localhost:8800/apps/orchestrator_agent/users/user/sessions

# Check Python environment
python -c "import sys; print(sys.version)"
```

## Current Setup

- **Python**: 3.12.11
- **Model**: gemini-2.0-flash
- **Orchestrator Config**: temp=0.4, top_p=0.9, top_k=40
- **Sub-agent Config**: temp=0.2, top_p=0.85, top_k=30
- **Server**: http://localhost:8800 (port 8800)
