# Multi-Agent State Management Design

**Version:** 1.0  
**Date:** November 18, 2025  
**Status:** Design Proposal

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Design Principles](#design-principles)
3. [Storage Strategy](#storage-strategy)
4. [Data Flow](#data-flow)
5. [Implementation Plan](#implementation-plan)
6. [File Structure](#file-structure)
7. [Code Examples](#code-examples)
8. [Scalability Considerations](#scalability-considerations)

---

## Architecture Overview

### Agent Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INPUT                              │
│              (Chat UI / API / Webhook)                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 ORCHESTRATOR AGENT                           │
│  • Request routing                                           │
│  • Parallel execution management                             │
│  • Result coordination                                       │
└─────┬─────────────────────────────────────────────┬─────────┘
      │                                             │
      │ Delegates to Sub-Agents (Parallel)         │
      ▼                                             ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Code Quality    │  │ Security        │  │ Engineering     │
│ Agent           │  │ Agent           │  │ Practices Agent │
│                 │  │                 │  │                 │
│ output_key:     │  │ output_key:     │  │ output_key:     │
│ code_quality_   │  │ security_       │  │ engineering_    │
│ results         │  │ results         │  │ results         │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                 ┌────────────┴──────────────┐
                 │                           │
                 ▼                           ▼
         ┌──────────────┐          ┌────────────────┐
         │ Carbon       │          │ All sub-agent  │
         │ Emission     │          │ outputs stored │
         │ Agent        │          │ in session     │
         │              │          │ state          │
         │ output_key:  │          └────────┬───────┘
         │ carbon_      │                   │
         │ results      │                   │
         └──────┬───────┘                   │
                │                           │
                └───────────┬───────────────┘
                            │
                            ▼
                ┌────────────────────────┐
                │ Report Synthesizer     │
                │ Agent                  │
                │                        │
                │ • Reads all outputs    │
                │ • Generates markdown   │
                │ • Saves as artifact    │
                └────────────┬───────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │ Orchestrator Agent     │
                │ • Returns report URL   │
                │ • Updates session      │
                └────────────┬───────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │  USER RESPONSE │
                    └────────────────┘
```

### Use Cases

| Scenario | Input Size | Processing Time | Key Requirements |
|----------|-----------|-----------------|------------------|
| **MVP - Chat UI** | Small code snippets (< 1000 lines) | 5-15 seconds | Fast response, good UX |
| **API - Single File** | Medium files (1000-5000 lines) | 15-30 seconds | Resumability, progress tracking |
| **API - Multiple Files** | Large codebases (5000+ lines) | 30-120 seconds | Streaming results, checkpoint recovery |
| **Webhook Integration** | Varies | Async processing | Status callbacks, artifact storage |

---

## Design Principles

### 1. **Separation of Concerns**
- **Session State**: Lightweight metadata, preferences, conversation context
- **Artifacts**: Large files (code, reports, analysis outputs)
- **Memory**: Long-term learning, historical patterns (future)
- **Ephemeral**: Temporary data during single execution

### 2. **Resilience**
- Sub-agent outputs stored immediately (not just in-memory)
- Can resume from last successful checkpoint
- Graceful degradation if one agent fails

### 3. **Scalability**
- Session files stay small (< 1MB)
- Artifacts referenced by URL/key, not embedded
- Can handle large codebases without memory issues

### 4. **Debuggability**
- All intermediate outputs are traceable
- Timestamps and agent metadata preserved
- Can replay/audit any analysis

### 5. **Performance**
- Parallel sub-agent execution
- Stream results as available (don't wait for all)
- Minimal disk I/O during active processing

---

## Storage Strategy

### Recommended Approach: **Hybrid Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    STORAGE LAYERS                            │
└─────────────────────────────────────────────────────────────┘

1. SESSION STATE (JSONFileSessionService)
   Location: ./sessions/{app_name}/{user_id}/{session_id}.json
   Purpose: Lightweight conversation metadata
   Size Limit: < 100KB per session
   
   Contents:
   {
     "current_analysis_id": "analysis_20251118_143022",
     "user_preferences": {...},
     "analysis_history": [
       {
         "analysis_id": "analysis_20251118_143022",
         "timestamp": "2025-11-18T14:30:22Z",
         "status": "completed",
         "code_summary": {
           "files": 3,
           "total_lines": 450,
           "language": "python"
         },
         "artifacts": {
           "input_code": "artifact://code_input_123.py",
           "final_report": "artifact://report_analysis_123.md",
           "sub_agent_outputs": "artifact://sub_outputs_123.json"
         },
         "metrics": {
           "duration_seconds": 12.5,
           "issues_found": 8,
           "severity_breakdown": {"critical": 0, "high": 2, "medium": 4, "low": 2}
         }
       }
     ],
     "quality_metrics": {...},
     "agent_usage_stats": {...}
   }

2. ARTIFACT SERVICE (Custom FileArtifactService)
   Location: ./artifacts/{app_name}/{user_id}/
   Purpose: Store large files and outputs
   
   Structure:
   ./artifacts/
     ├── Code_Review_System/
     │   └── rahul_gupta_123/
     │       ├── inputs/
     │       │   ├── code_input_20251118_143022.py
     │       │   └── code_input_20251118_150033.zip
     │       ├── reports/
     │       │   ├── report_20251118_143022.md
     │       │   └── report_20251118_143022.html
     │       └── sub_agent_outputs/
     │           ├── analysis_20251118_143022_code_quality.json
     │           ├── analysis_20251118_143022_security.json
     │           ├── analysis_20251118_143022_engineering.json
     │           └── analysis_20251118_143022_carbon.json

3. EPHEMERAL CONTEXT (Agent State during execution)
   Location: In-memory (agent's context object)
   Purpose: Temporary workspace during single analysis
   Lifetime: Duration of one run_async() call
   
   Structure:
   {
     "analysis_id": "analysis_20251118_143022",
     "code_quality_results": {...},      # Sub-agent output
     "security_results": {...},          # Sub-agent output
     "engineering_results": {...},       # Sub-agent output
     "carbon_results": {...},            # Sub-agent output
     "checkpoints": [
       {"step": "code_quality", "status": "completed", "timestamp": "..."},
       {"step": "security", "status": "completed", "timestamp": "..."}
     ]
   }
   
   Note: This is passed between agents via ADK's built-in state propagation
         and checkpointed to artifacts after each sub-agent completes.

4. MEMORY SERVICE (Future - Optional)
   Purpose: Long-term learning across sessions
   Use Cases:
   - Remember user's common issues
   - Learn coding patterns
   - Suggest proactive improvements
```

---

## Data Flow

### Single Analysis Flow (MVP)

```
PHASE 1: REQUEST INITIATION
────────────────────────────
User → Orchestrator
  ├─ Create analysis_id: "analysis_20251118_143022"
  ├─ Save input code to artifact: artifact://code_input_123.py
  ├─ Update session.state.current_analysis_id
  └─ Initialize ephemeral context with analysis_id

PHASE 2: PARALLEL SUB-AGENT EXECUTION
──────────────────────────────────────
Orchestrator → [Code Quality, Security, Engineering, Carbon] (parallel)

Sub-Agent Execution (each agent independently):
  1. Receive ephemeral context (contains analysis_id, code reference)
  2. Load code from artifact if needed
  3. Perform analysis
  4. Store output in ephemeral context under output_key
  5. CHECKPOINT: Save output to artifact:
     artifact://sub_agent_outputs/analysis_{id}_{agent_name}.json
  6. Return control to orchestrator

Ephemeral Context after Phase 2:
{
  "analysis_id": "analysis_20251118_143022",
  "code_quality_results": {
    "issues": [...],
    "metrics": {...},
    "artifact_ref": "artifact://...code_quality.json"
  },
  "security_results": {...},
  "engineering_results": {...},
  "carbon_results": {...},
  "checkpoints": [...]
}

PHASE 3: REPORT SYNTHESIS
──────────────────────────
Orchestrator → Report Synthesizer Agent
  1. Receive ephemeral context with all sub-agent outputs
  2. Generate comprehensive markdown report
  3. Save report to artifact: artifact://reports/report_{analysis_id}.md
  4. Return report reference to orchestrator

PHASE 4: FINALIZATION
─────────────────────
Orchestrator:
  1. Update session.state.analysis_history[] with:
     - analysis_id
     - timestamp
     - status: "completed"
     - artifacts: {input, report, sub_outputs}
     - metrics: {duration, issues_found, severity}
  2. Return report URL/content to user
  3. Clear current_analysis_id

Session persisted by JSONFileSessionService.append_event()
```

### Error Recovery Flow

```
SCENARIO: Agent fails during execution
───────────────────────────────────────

1. Orchestrator detects failure (e.g., security agent timeout)
2. Check which agents completed via checkpoints in ephemeral context
3. Update session.state.analysis_history with status: "partial"
4. Save completed sub-agent outputs to artifacts
5. Return partial report with:
   "⚠️ Analysis partially completed. Security analysis unavailable."

SCENARIO: Server crash mid-execution
─────────────────────────────────────

1. User returns, creates new session or continues existing
2. Orchestrator checks session.state.current_analysis_id
3. If exists, offer to resume:
   "Your previous analysis was interrupted. Resume from checkpoint?"
4. Load sub-agent outputs from artifacts based on analysis_id
5. Determine which agents need to re-run
6. Continue from checkpoint

SCENARIO: Large file processing timeout
────────────────────────────────────────

1. Orchestrator detects timeout (> 2 minutes)
2. Stream partial results as they complete:
   "✅ Code quality analysis complete (3 issues found)"
   "✅ Security analysis complete (0 critical issues)"
   "⏳ Engineering practices analysis in progress..."
3. Save completed outputs incrementally
4. User can choose to wait or get partial report
```

---

## Implementation Plan

### Phase 1: Core Architecture (Current Sprint)

✅ **Already Implemented:**
- JSONFileSessionService with persistence
- Session state structure with analysis_history
- Basic agent coordination via orchestrator

🎯 **To Implement:**

#### 1.1 Create FileArtifactService

```python
# util/artifact_service.py

from google.adk.artifacts import BaseArtifactService
from google.genai import types
from pathlib import Path
import json
from datetime import datetime

class FileArtifactService(BaseArtifactService):
    """File-based artifact storage for code, reports, and analysis outputs."""
    
    def __init__(self, base_dir: str = "./artifacts"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        artifact: types.Part,
        session_id: str = None,
        custom_metadata: dict = None
    ) -> int:
        """Save artifact to disk, return version number."""
        artifact_dir = self.base_dir / app_name / user_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine subdirectory based on file type
        if filename.startswith("code_input_"):
            subdir = artifact_dir / "inputs"
        elif filename.startswith("report_"):
            subdir = artifact_dir / "reports"
        elif filename.startswith("analysis_"):
            subdir = artifact_dir / "sub_agent_outputs"
        else:
            subdir = artifact_dir
        
        subdir.mkdir(exist_ok=True)
        file_path = subdir / filename
        
        # Save artifact
        if hasattr(artifact, 'text'):
            file_path.write_text(artifact.text)
        elif hasattr(artifact, 'data'):
            file_path.write_bytes(artifact.data)
        
        # Save metadata
        metadata = {
            "filename": filename,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "custom": custom_metadata or {}
        }
        metadata_path = file_path.with_suffix(file_path.suffix + ".meta.json")
        metadata_path.write_text(json.dumps(metadata, indent=2))
        
        return 1  # Version number (simplified)
    
    async def load_artifact(
        self,
        *,
        app_name: str,
        user_id: str,
        filename: str,
        session_id: str = None,
        version: int = None
    ) -> types.Part:
        """Load artifact from disk."""
        # Search in subdirectories
        artifact_dir = self.base_dir / app_name / user_id
        
        for subdir in ["inputs", "reports", "sub_agent_outputs", "."]:
            file_path = artifact_dir / subdir / filename
            if file_path.exists():
                content = file_path.read_text()
                return types.Part(text=content)
        
        return None
    
    async def list_artifact_keys(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str = None
    ) -> list[str]:
        """List all artifact filenames."""
        artifact_dir = self.base_dir / app_name / user_id
        if not artifact_dir.exists():
            return []
        
        files = []
        for subdir in ["inputs", "reports", "sub_agent_outputs"]:
            subdir_path = artifact_dir / subdir
            if subdir_path.exists():
                files.extend([
                    str(f.relative_to(artifact_dir))
                    for f in subdir_path.rglob("*")
                    if f.is_file() and not f.name.endswith(".meta.json")
                ])
        return files
```

#### 1.2 Update Orchestrator Agent Logic

```python
# agent_workspace/orchestrator_agent/agent.py

# Add output_keys to sub-agents
code_quality_agent = LlmAgent(
    ...,
    output_key="code_quality_results"  # IMPORTANT!
)

security_agent = LlmAgent(
    ...,
    output_key="security_results"
)

# Similar for engineering_practices_agent, carbon_emission_agent

# Orchestrator coordinates and checkpoints
orchestrator_agent = LlmAgent(
    ...,
    instruction="""
    When user submits code for review:
    
    1. Generate unique analysis_id: f"analysis_{datetime.now():%Y%m%d_%H%M%S}"
    
    2. Save input code to artifact:
       - Use artifact_service.save_artifact()
       - Filename: f"code_input_{analysis_id}.py"
    
    3. Delegate to sub-agents in parallel:
       - Pass analysis_id in context
       - Each sub-agent stores output under their output_key
    
    4. After each sub-agent completes, CHECKPOINT:
       - Save sub-agent output to artifact
       - Filename: f"analysis_{analysis_id}_{agent_name}.json"
    
    5. Invoke Report Synthesizer with all sub-agent outputs
    
    6. Report Synthesizer generates markdown and saves:
       - Filename: f"report_{analysis_id}.md"
    
    7. Update session state with analysis record:
       session.state["analysis_history"].append({
         "analysis_id": analysis_id,
         "timestamp": ...,
         "artifacts": {
           "input_code": f"artifact://code_input_{analysis_id}.py",
           "final_report": f"artifact://report_{analysis_id}.md"
         }
       })
    
    8. Return report to user (inline text + artifact reference)
    """,
    sub_agents=[...],
)
```

#### 1.3 Update Report Synthesizer

```python
# agent_workspace/orchestrator_agent/sub_agents/report_synthesizer_agent/agent.py

report_synthesizer_agent = LlmAgent(
    ...,
    instruction="""
    You synthesize analysis results from multiple sub-agents into a final report.
    
    Input: Receive all sub-agent outputs via their output_keys:
    - code_quality_results
    - security_results
    - engineering_results
    - carbon_results
    
    Process:
    1. Aggregate all findings
    2. Prioritize by severity (critical → high → medium → low)
    3. Remove duplicates
    4. Generate comprehensive markdown report
    
    Output Format (Markdown):
    ```markdown
    # Code Review Report
    
    **Analysis ID:** {analysis_id}
    **Date:** {timestamp}
    **Code Summary:** {files_count} files, {total_lines} lines
    
    ## 📊 Executive Summary
    - **Total Issues:** {count}
    - **Critical:** {critical_count}
    - **High:** {high_count}
    - **Medium:** {medium_count}
    - **Low:** {low_count}
    
    ## 🔍 Detailed Findings
    
    ### 🔒 Security Analysis
    {security_findings}
    
    ### 📈 Code Quality Analysis
    {quality_findings}
    
    ### ⚙️ Engineering Practices
    {engineering_findings}
    
    ### 🌱 Environmental Impact
    {carbon_findings}
    
    ## 💡 Recommendations
    {prioritized_recommendations}
    
    ## 📋 Action Items
    {actionable_steps}
    ```
    
    After generating report:
    - Save markdown to artifact via artifact_service
    - Return both inline text and artifact reference
    """,
)
```

#### 1.4 Update main.py with Artifact Service

```python
# main.py

from util.artifact_service import FileArtifactService

# Create services
session_service = JSONFileSessionService(uri="jsonfile://./sessions")
artifact_service = FileArtifactService(base_dir="./artifacts")

# Create runner with both services
runner = Runner(
    agent=orchestrator_agent,
    app_name=APP_NAME,
    session_service=session_service,
    artifact_service=artifact_service,  # ADD THIS
)
```

### Phase 2: Enhanced Features (Future)

#### 2.1 Progress Streaming
- Stream sub-agent completion events
- Show "✅ Code quality analysis complete (3 issues found)"
- Real-time progress bar

#### 2.2 Resumability
- Check `session.state.current_analysis_id` on startup
- Offer to resume interrupted analysis
- Load checkpoints from artifacts

#### 2.3 Memory Service
- Learn from historical analyses
- Suggest proactive improvements
- Track common user mistakes

#### 2.4 Webhook Integration
- Accept webhook requests with multiple files
- Process asynchronously
- POST results to callback URL

---

## File Structure

```
agentic-codereview/
├── sessions/                          # Session persistence
│   └── Code_Review_System/
│       └── rahul_gupta_123/
│           ├── abc123-session.json    # 50KB - Lightweight metadata
│           └── def456-session.json
│
├── artifacts/                         # Large files & outputs
│   └── Code_Review_System/
│       └── rahul_gupta_123/
│           ├── inputs/
│           │   ├── code_input_20251118_143022.py           # User code
│           │   ├── code_input_20251118_143022.py.meta.json # Metadata
│           │   └── code_input_20251118_150033.zip
│           ├── reports/
│           │   ├── report_20251118_143022.md               # Final report
│           │   ├── report_20251118_143022.md.meta.json
│           │   └── report_20251118_143022.html
│           └── sub_agent_outputs/
│               ├── analysis_20251118_143022_code_quality.json
│               ├── analysis_20251118_143022_security.json
│               ├── analysis_20251118_143022_engineering.json
│               └── analysis_20251118_143022_carbon.json
│
├── data/
│   └── mock_session_data.json         # Default session state
│
└── util/
    ├── session.py                      # JSONFileSessionService
    └── artifact_service.py             # FileArtifactService (NEW)
```

### Storage Estimates

| Scenario | Session Size | Artifact Size | Total |
|----------|-------------|---------------|-------|
| MVP - Small snippet | 50KB | 10KB input + 50KB report + 100KB sub-outputs = 160KB | 210KB |
| Medium file | 60KB | 100KB input + 100KB report + 200KB sub-outputs = 400KB | 460KB |
| Multiple files | 80KB | 1MB input + 200KB report + 500KB sub-outputs = 1.7MB | 1.78MB |

**Key Benefit:** Session stays small (< 100KB), artifacts scale independently

---

## Code Examples

### Example 1: Orchestrator Saving Input Code

```python
# In orchestrator agent's processing logic

from datetime import datetime
from google.genai import types

# Generate analysis ID
analysis_id = f"analysis_{datetime.now():%Y%m%d_%H%M%S}"

# Save user's input code to artifact
input_filename = f"code_input_{analysis_id}.py"
await artifact_service.save_artifact(
    app_name=app_name,
    user_id=user_id,
    filename=input_filename,
    artifact=types.Part(text=user_code),
    session_id=session_id,
    custom_metadata={
        "analysis_id": analysis_id,
        "language": "python",
        "lines": len(user_code.split('\n'))
    }
)

# Pass analysis_id to sub-agents via context
context = {
    "analysis_id": analysis_id,
    "code_artifact": f"artifact://{input_filename}",
    "code": user_code  # Also pass inline for performance
}
```

### Example 2: Sub-Agent Checkpointing Output

```python
# In code_quality_agent after analysis completes

# Agent's analysis result
code_quality_results = {
    "issues": [...],
    "metrics": {"complexity": 12, "maintainability": 85},
    "recommendations": [...]
}

# Checkpoint to artifact
output_filename = f"analysis_{analysis_id}_code_quality.json"
await artifact_service.save_artifact(
    app_name=app_name,
    user_id=user_id,
    filename=output_filename,
    artifact=types.Part(text=json.dumps(code_quality_results, indent=2)),
    session_id=session_id,
    custom_metadata={
        "analysis_id": analysis_id,
        "agent": "code_quality_agent",
        "timestamp": datetime.now().isoformat()
    }
)

# Return result with artifact reference
return {
    **code_quality_results,
    "artifact_ref": f"artifact://{output_filename}"
}
```

### Example 3: Report Synthesizer Saving Final Report

```python
# In report_synthesizer_agent

# Generate comprehensive markdown report
markdown_report = generate_comprehensive_report(
    code_quality=context["code_quality_results"],
    security=context["security_results"],
    engineering=context["engineering_results"],
    carbon=context["carbon_results"]
)

# Save report to artifact
report_filename = f"report_{analysis_id}.md"
await artifact_service.save_artifact(
    app_name=app_name,
    user_id=user_id,
    filename=report_filename,
    artifact=types.Part(text=markdown_report),
    session_id=session_id,
    custom_metadata={
        "analysis_id": analysis_id,
        "report_type": "comprehensive",
        "timestamp": datetime.now().isoformat(),
        "issues_count": total_issues,
        "severity_breakdown": severity_counts
    }
)

return {
    "report": markdown_report,  # Inline for immediate display
    "artifact_ref": f"artifact://{report_filename}",
    "summary": {
        "total_issues": total_issues,
        "severity_breakdown": severity_counts
    }
}
```

### Example 4: Session State After Analysis

```python
# Session state after complete analysis

session.state = {
    "user_name": "Rahul Gupta",
    "user_preferences": {...},
    
    "current_analysis_id": None,  # Cleared after completion
    
    "analysis_history": [
        {
            "analysis_id": "analysis_20251118_143022",
            "timestamp": "2025-11-18T14:30:22Z",
            "status": "completed",
            "code_summary": {
                "language": "python",
                "files": 1,
                "total_lines": 450,
                "filename": "auth_service.py"
            },
            "artifacts": {
                "input_code": "artifact://code_input_20251118_143022.py",
                "final_report": "artifact://report_20251118_143022.md",
                "sub_agent_outputs": {
                    "code_quality": "artifact://analysis_20251118_143022_code_quality.json",
                    "security": "artifact://analysis_20251118_143022_security.json",
                    "engineering": "artifact://analysis_20251118_143022_engineering.json",
                    "carbon": "artifact://analysis_20251118_143022_carbon.json"
                }
            },
            "metrics": {
                "duration_seconds": 12.5,
                "issues_found": 8,
                "severity_breakdown": {
                    "critical": 0,
                    "high": 2,
                    "medium": 4,
                    "low": 2
                }
            },
            "agents_used": [
                "code_quality_agent",
                "security_agent",
                "engineering_practices_agent",
                "carbon_emission_agent",
                "report_synthesizer_agent"
            ]
        },
        # ... previous analyses
    ],
    
    "quality_metrics": {
        "total_analyses": 6,
        "total_issues_found": 45,
        "avg_issues_per_analysis": 7.5,
        "most_common_severity": "medium"
    }
}
```

---

## Scalability Considerations

### Current Design (MVP)

| Metric | Capacity | Notes |
|--------|----------|-------|
| Code size | < 5000 lines | Fits in single LLM context |
| Session size | < 100KB | Lightweight metadata only |
| Artifact size | No limit | Stored separately on disk |
| Concurrent users | 10-50 | File-based services sufficient |
| Analysis history | 100 analyses | Stored in session state |

### Future Scaling (Phase 2+)

**When you need to scale beyond MVP:**

1. **Large Codebases (> 10,000 lines)**
   - Implement chunking strategy
   - Process files incrementally
   - Stream results as available
   
2. **High Concurrency (> 100 users)**
   - Move to database-backed session service (PostgreSQL, Spanner)
   - Implement artifact service with cloud storage (GCS, S3)
   - Add caching layer (Redis)

3. **Long-Term Memory**
   - Implement BaseMemoryService with vector database
   - Store embeddings of code patterns
   - Enable semantic search across historical analyses

4. **Distributed Processing**
   - Separate sub-agents into microservices
   - Use message queue for coordination (Pub/Sub, RabbitMQ)
   - Implement proper circuit breakers

### Performance Optimization

```python
# Future: Parallel checkpointing (don't block agents)
import asyncio

async def checkpoint_results_parallel(results: dict):
    """Save multiple sub-agent outputs in parallel."""
    tasks = [
        artifact_service.save_artifact(
            filename=f"analysis_{analysis_id}_{agent}.json",
            artifact=types.Part(text=json.dumps(output)),
            ...
        )
        for agent, output in results.items()
    ]
    await asyncio.gather(*tasks)
    
# Future: Lazy loading of artifacts
async def load_analysis_if_needed(analysis_id: str):
    """Load sub-agent outputs only when requested."""
    if analysis_id not in cache:
        cache[analysis_id] = await load_from_artifacts(analysis_id)
    return cache[analysis_id]
```

---

## Decision Summary

### ✅ RECOMMENDED APPROACH

**Use Hybrid Storage Strategy:**

1. **Session State** (JSONFileSessionService)
   - Store: Analysis metadata, user preferences, history summaries
   - Size: < 100KB per session
   - Benefits: Fast access, automatically persisted, survives restarts

2. **Artifact Service** (FileArtifactService - to implement)
   - Store: Input code, final reports, sub-agent detailed outputs
   - Size: Unlimited (separate files)
   - Benefits: Scalable, debuggable, doesn't bloat sessions

3. **Ephemeral Context** (In-memory during execution)
   - Store: Temporary sub-agent outputs during single analysis
   - Lifetime: Duration of one `run_async()` call
   - Benefits: Fast, leverages ADK's built-in state propagation
   - Safety: Checkpointed to artifacts after each sub-agent

### ❌ REJECTED APPROACHES

**Option A: Store everything in session state**
- ❌ Session files become huge (> 1MB)
- ❌ Slow to load/save
- ❌ Not scalable

**Option B: Only use ephemeral context (no checkpoints)**
- ❌ Data lost if agent fails mid-execution
- ❌ Can't resume interrupted analyses
- ❌ No audit trail

**Option C: Database for everything**
- ❌ Over-engineered for MVP
- ❌ External dependency
- ❌ Complexity without clear benefit yet

---

## Next Steps

### Implementation Checklist

- [ ] 1. Create `util/artifact_service.py` with `FileArtifactService`
- [ ] 2. Update `orchestrator_agent` to:
  - [ ] Generate analysis_id
  - [ ] Save input code to artifacts
  - [ ] Checkpoint sub-agent outputs
  - [ ] Update session state with analysis record
- [ ] 3. Add `output_key` to all sub-agents
- [ ] 4. Update `report_synthesizer_agent` to save markdown to artifacts
- [ ] 5. Update `main.py` to instantiate artifact_service
- [ ] 6. Test end-to-end flow with small code snippet
- [ ] 7. Test error recovery (kill process mid-analysis)
- [ ] 8. Add progress streaming (optional enhancement)
- [ ] 9. Document artifact URLs for API consumers

### Testing Plan

```python
# Test 1: Complete analysis flow
# - Submit code
# - Verify session state updated
# - Verify artifacts created in correct directories
# - Verify report generated

# Test 2: Error recovery
# - Start analysis
# - Kill process after 2 sub-agents complete
# - Restart, check session state
# - Verify checkpointed outputs in artifacts
# - Resume analysis

# Test 3: Large file handling
# - Submit 5000-line file
# - Verify session stays < 100KB
# - Verify artifact contains full code
# - Verify report references artifacts correctly

# Test 4: Concurrent users
# - Create 5 simultaneous analyses
# - Verify no file conflicts
# - Verify correct artifact isolation
```

---

## Conclusion

**Your multi-agent code review system should use:**

1. ✅ **JSONFileSessionService** (already implemented) for lightweight session metadata
2. ✅ **FileArtifactService** (to implement) for large files and detailed outputs
3. ✅ **Ephemeral context** for temporary data during execution, with checkpointing

**This design provides:**
- ✅ Resilience (checkpoints, resumability)
- ✅ Scalability (sessions stay small, artifacts scale independently)
- ✅ Debuggability (all outputs traceable)
- ✅ Performance (parallel execution, minimal blocking I/O)
- ✅ Simplicity (file-based, no external dependencies for MVP)

**Start with Phase 1 (FileArtifactService + orchestrator updates) and you'll have a production-ready system!**
