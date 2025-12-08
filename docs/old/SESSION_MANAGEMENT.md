# Session Management - ADK Best Practices Implementation

## Overview

Session management following **ADK 1.17+ best practices** for custom session services. The new implementation provides:

✅ **Persistent Storage** - Sessions survive server restarts  
✅ **File-Based** - No external dependencies (Redis, MongoDB, etc.)  
✅ **Service Registry Integration** - Works with `adk web` CLI  
✅ **Auto-Registration** - Automatically available when module is imported  
✅ **Backward Compatible** - Old functions still work  

## What Changed

### Before (Simple Helpers)
```python
# Old approach - just provided initial state
from util.session import get_initial_session_state

initial_state = get_initial_session_state()
```

### After (Full Session Service)
```python
# New approach - complete session lifecycle management
from util.session import JSONFileSessionService

# Automatic registration with ADK
# Works with: adk web --session_service_uri=jsonfile://./sessions
```

## Features

### 1. **Persistent Sessions**
Sessions are stored as JSON files in a hierarchical structure:
```
sessions/
├── orchestrator_agent/
│   └── user123/
│       ├── session-abc-123.json
│       └── session-def-456.json
└── code_quality_agent/
    └── user456/
        └── session-xyz-789.json
```

### 2. **Automatic State Initialization**
Each new session automatically includes:
- User context
- Review history tracking
- Quality metrics
- User preferences
- Session metadata

### 3. **Event Persistence**
Every interaction (user messages, agent responses, tool calls) is automatically saved:
```python
# ADK calls append_event() automatically
# Your sessions persist across:
# - Page refreshes
# - Server restarts
# - Process crashes
```

### 4. **Service Registry Integration**
Use with `adk web` command:
```bash
# Use JSON file sessions (default location)
adk web agent_workspace/ --session_service_uri=jsonfile://./sessions

# Use custom location
adk web agent_workspace/ --session_service_uri=jsonfile:///path/to/sessions
```

## Usage

### Direct Usage (Programmatic)

```python
import asyncio
from util.session import JSONFileSessionService

async def main():
    # Initialize service
    service = JSONFileSessionService(uri="jsonfile://./sessions")
    
    # Create session
    session = await service.create_session(
        app_name="orchestrator_agent",
        user_id="developer_123",
        state={"user_name": "Rahul"}
    )
    
    # Retrieve session
    retrieved = await service.get_session(
        app_name="orchestrator_agent",
        user_id="developer_123",
        session_id=session.id
    )
    
    # List all sessions for user
    result = await service.list_sessions(
        app_name="orchestrator_agent",
        user_id="developer_123"
    )
    print(f"Found {result['total_count']} sessions")
    
    # Delete session
    await service.delete_session(
        app_name="orchestrator_agent",
        user_id="developer_123",
        session_id=session.id
    )

asyncio.run(main())
```

### With ADK Runner

```python
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService  # or use JSONFileSessionService
from agent_workspace.orchestrator_agent.agent import orchestrator_agent
from util.session import JSONFileSessionService

# Create persistent session service
session_service = JSONFileSessionService(uri="jsonfile://./sessions")

# Create runner with persistent sessions
runner = Runner(
    agent=orchestrator_agent,
    app_name="code_review_system",
    session_service=session_service
)

# Sessions now persist automatically!
```

### CLI Usage (adk web)

The service is automatically registered when you import the module:

```bash
# Start ADK web with persistent sessions
cd /Users/rahulgupta/Documents/Coding/agentic-codereview
adk web agent_workspace/ --session_service_uri=jsonfile://./sessions

# Sessions are saved to ./sessions/
# Access UI at http://localhost:8800
```

## Session State Structure

Each session contains:

```json
{
  "id": "abc-123-def-456",
  "app_name": "orchestrator_agent",
  "user_id": "developer_123",
  "state": {
    "user_name": "Code Reviewer",
    "review_history": [],
    "analysis_history": [],
    "session_metadata": {
      "total_reviews": 0,
      "successful_analyses": 0,
      "failed_analyses": 0,
      "created_at": "2025-11-18T12:00:00"
    },
    "quality_metrics": {
      "total_issues_found": 0,
      "critical_issues": 0,
      "high_issues": 0,
      "medium_issues": 0,
      "low_issues": 0
    },
    "user_preferences": {
      "analysis_depth": "standard",
      "focus_areas": ["quality", "security", "practices", "carbon"]
    }
  },
  "events": [
    {
      "id": "event-1",
      "type": "UserMessage",
      "timestamp": "2025-11-18T12:01:00",
      "data": "Review this code..."
    }
  ],
  "created_at": "2025-11-18T12:00:00",
  "last_update_time": 1700308800.0
}
```

## Backward Compatibility

Old functions still work:

```python
# These functions still work (for backward compatibility)
from util.session import (
    get_initial_session_state,  # Returns default initial state
    load_mock_session_data,      # Loads from data/mock_session_data.json
    get_fallback_session_data    # Returns fallback state
)

# But they're now deprecated in favor of JSONFileSessionService
```

## Migration Guide

### If you were using InMemorySessionService

**Before:**
```python
from google.adk.sessions import InMemorySessionService

session_service = InMemorySessionService()
```

**After:**
```python
from util.session import JSONFileSessionService

session_service = JSONFileSessionService(uri="jsonfile://./sessions")
# Everything else stays the same!
```

### If you were using get_initial_session_state()

**Before:**
```python
from util.session import get_initial_session_state

initial_state = get_initial_session_state()
session = await session_service.create_session(
    app_name="my_app",
    user_id="user123",
    state=initial_state
)
```

**After:**
```python
from util.session import JSONFileSessionService

# Initial state is handled automatically
service = JSONFileSessionService(uri="jsonfile://./sessions")
session = await service.create_session(
    app_name="my_app",
    user_id="user123"
    # state is auto-populated with smart defaults
)
```

## Benefits

### 1. Production-Ready
- Survives server restarts
- No data loss
- Suitable for production deployments

### 2. No External Dependencies
- No Redis, MongoDB, or PostgreSQL required
- Works out of the box
- Easy to deploy

### 3. ADK Native
- Follows ADK best practices
- Works seamlessly with `adk web`
- Compatible with all ADK features

### 4. Flexible Storage
- JSON files are human-readable
- Easy to debug
- Simple backup/restore

### 5. Hierarchical Organization
- Sessions organized by app_name and user_id
- Easy to find and manage
- Clean directory structure

## Monitoring & Debugging

### View Session Files

```bash
# List all sessions
ls -R sessions/

# View specific session
cat sessions/orchestrator_agent/user123/session-abc-123.json | python3 -m json.tool
```

### Check Session Count

```python
from pathlib import Path
import json

def count_sessions(app_name, user_id):
    sessions_dir = Path("sessions") / app_name / user_id
    if not sessions_dir.exists():
        return 0
    return len(list(sessions_dir.glob("*.json")))

print(f"Sessions: {count_sessions('orchestrator_agent', 'user123')}")
```

### Clean Old Sessions

```python
import asyncio
from util.session import JSONFileSessionService

async def cleanup_old_sessions():
    service = JSONFileSessionService(uri="jsonfile://./sessions")
    
    result = await service.list_sessions(
        app_name="orchestrator_agent",
        user_id="user123"
    )
    
    # Delete sessions older than 7 days
    import time
    cutoff = time.time() - (7 * 24 * 60 * 60)
    
    for session in result["sessions"]:
        if session.last_update_time < cutoff:
            await service.delete_session(
                app_name=session.app_name,
                user_id=session.user_id,
                session_id=session.id
            )
            print(f"Deleted old session: {session.id}")

asyncio.run(cleanup_old_sessions())
```

## Testing

Test the session service:

```bash
cd /Users/rahulgupta/Documents/Coding/agentic-codereview

# Test basic functionality
./venv/bin/python -c "
from util.session import JSONFileSessionService
import asyncio

async def test():
    service = JSONFileSessionService(uri='jsonfile://./test_sessions')
    session = await service.create_session(
        app_name='test_app',
        user_id='test_user'
    )
    print(f'✅ Session created: {session.id}')

asyncio.run(test())
"
```

## Next Steps

1. **Update your code** to use `JSONFileSessionService` instead of `InMemorySessionService`
2. **Test persistence** by restarting the server and checking if sessions persist
3. **Configure storage location** via environment variable if needed
4. **Monitor disk usage** as sessions accumulate
5. **Implement cleanup** for old sessions if needed

## Troubleshooting

### Sessions not persisting?
- Check that `append_event()` is being called (it should be automatic)
- Verify write permissions to the sessions directory
- Look for error messages in logs

### Performance issues?
- JSON file I/O is fast for <1000 sessions
- For more, consider Redis or database backend
- Implement session cleanup for old/inactive sessions

### Can't find sessions?
- Check the directory structure: `sessions/app_name/user_id/`
- Verify app_name and user_id match what you're searching for
- Use `list_sessions()` to debug

## Reference

- **Tutorial**: https://raphaelmansuy.github.io/adk_training/docs/til/til_custom_session_services_20251023
- **ADK Docs**: https://google.github.io/adk-docs/
- **Source**: `/Users/rahulgupta/Documents/Coding/agentic-codereview/util/session.py`

---

**Your session management is now production-ready!** 🎉
