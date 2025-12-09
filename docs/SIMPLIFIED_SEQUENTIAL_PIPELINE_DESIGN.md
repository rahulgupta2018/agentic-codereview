# Simplified Sequential Agent Pipeline Design

**Status**: ✅ Design Complete - Ready for Review (December 8, 2025)  
**Date**: December 8, 2025  
**Last Updated**: December 8, 2025 - Artifact system verified  
**Architecture Pattern**: Deterministic Sequential Pipeline  
**Priority**: GitHub Integration with ADK Built-in Artifacts  
**Artifact Solution**: ✅ Custom FileArtifactService (already implemented)  
**Inspiration**: [ADK Sequential Workflows](https://raphaelmansuy.github.io/adk_training/docs/sequential_workflows)

---

## 🎯 Design Philosophy

**Goal**: Create a simple, maintainable, deterministic pipeline for GitHub PR code reviews.

**Key Principles**:
1. ✅ **Sequential execution** - all analysis agents run in order, every time (deterministic)
2. ✅ **No dynamic routing** - remove complexity of planning + dynamic selection  
3. ✅ **ADK built-in artifacts** - use ADK's `tool_context.save_artifact()` for persistence
4. ✅ **Session-based organization** - artifacts organized by session/user/PR  
5. ✅ **Separate analysis pipeline** - encapsulate analysis agents as sub-pipeline for maintainability

### Why Simplify?

**Current Problems**:
- ❌ Planning Agent + Dynamic Router adds unnecessary complexity
- ❌ Agents don't reliably call `save_analysis_result()` tool (LLM inconsistency)
- ❌ Mixing session state and disk artifacts creates confusion
- ❌ Hard to debug when execution path varies

**Solution**:
- ✅ Fixed sequential pipeline - same agents, same order, every time
- ✅ ADK handles artifact persistence - no custom disk I/O
- ✅ Clear separation: Fetch → Analyze → Report → Publish
- ✅ Each step is predictable and testable

---

## 🏗️ Architecture Overview

### High-Level Flow

```
GitHub Webhook/API Call
         ↓
┌─────────────────────────────────────────┐
│      Orchestrator Agent (Root)          │
│   Entry point for all API requests      │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│    GitHub PR Review Pipeline            │
│      (SequentialAgent)                  │
└─────────────────────────────────────────┘
         ↓
    Step 1: Fetch
    Step 2: Analyze (nested pipeline)
    Step 3: Report
    Step 4: Publish
         ↓
    ✅ Complete
```

### Detailed Sequential Flow

```
┌──────────────────────────────────────────────────────────────┐
│ STEP 1: GitHub Fetcher Agent                                 │
├──────────────────────────────────────────────────────────────┤
│ Purpose: Fetch PR data from GitHub API                       │
│ Input:   github_context from session state                   │
│          { repo: "owner/repo", pr_number: 42, ... }          │
│ Tools:   • fetch_github_pr_files() or mock                   │
│ Output:  • session.state["github_pr_data"] = {               │
│            files: [...], diffs: [...], metadata: {...}       │
│          }                                                    │
└──────────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 2: Analysis Pipeline (SequentialAgent - NESTED)         │
├──────────────────────────────────────────────────────────────┤
│ Purpose: Encapsulate all analysis agents for maintainability │
│ Design:  Separate sub-pipeline within orchestrator           │
│ Execution: Sequential (deterministic order)                  │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ 2a. Security Agent                                     │  │
│ │ ──────────────────                                     │  │
│ │ • Call: scan_security_vulnerabilities(code)            │  │
│ │ • Generate: JSON with vulnerabilities, OWASP risks     │  │
│ │ • Save: tool_context.save_artifact(                    │  │
│ │         filename="security_analysis.json",             │  │
│ │         artifact=json_data                             │  │
│ │       )                                                │  │
│ │ • Location: ADK manages storage                        │  │
│ │             (artifacts/<session_id>/...)               │  │
│ └────────────────────────────────────────────────────────┘  │
│                        ↓                                      │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ 2b. Code Quality Agent                                 │  │
│ │ ──────────────────────                                 │  │
│ │ • Call: analyze_complexity(), analyze_static_code()    │  │
│ │ • Generate: JSON with metrics, quality issues          │  │
│ │ • Save: tool_context.save_artifact(                    │  │
│ │         filename="quality_analysis.json", ...          │  │
│ │       )                                                │  │
│ └────────────────────────────────────────────────────────┘  │
│                        ↓                                      │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ 2c. Engineering Practices Agent                        │  │
│ │ ───────────────────────────────                        │  │
│ │ • Call: evaluate_engineering_practices()               │  │
│ │ • Generate: JSON with best practice violations         │  │
│ │ • Save: tool_context.save_artifact(                    │  │
│ │         filename="engineering_analysis.json", ...      │  │
│ │       )                                                │  │
│ └────────────────────────────────────────────────────────┘  │
│                        ↓                                      │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ 2d. Carbon Emission Agent                              │  │
│ │ ─────────────────────────                              │  │
│ │ • Call: analyze_carbon_footprint()                     │  │
│ │ • Generate: JSON with environmental impact             │  │
│ │ • Save: tool_context.save_artifact(                    │  │
│ │         filename="carbon_analysis.json", ...           │  │
│ │       )                                                │  │
│ └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 3: Report Synthesizer Agent                             │
├──────────────────────────────────────────────────────────────┤
│ Purpose: Generate comprehensive markdown report              │
│ Input:   Load all analysis artifacts via ADK                 │
│ Tools:   • load_artifacts(session_id) → returns all JSONs    │
│          • ADK artifact system handles retrieval             │
│ Process: • Parse each analysis JSON                          │
│          • Synthesize findings into sections:                │
│            - Executive Summary                               │
│            - Security Vulnerabilities (table)                │
│            - Code Quality Metrics                            │
│            - Engineering Best Practices                      │
│            - Environmental Impact                            │
│            - Consolidated Recommendations                    │
│ Output:  • Comprehensive markdown document                   │
│          • Save: tool_context.save_artifact(                 │
│            filename="final_report.md", ...                   │
│          )                                                   │
└──────────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────────┐
│ STEP 4: GitHub Publisher Agent                               │
├──────────────────────────────────────────────────────────────┤
│ Purpose: Post review to GitHub PR                            │
│ Input:   Load final_report.md from ADK artifacts             │
│ Tools:   • post_github_pr_comment(report_md)                 │
│          • add_inline_annotations(findings)                  │
│ Actions: • Post main review comment with full report         │
│          • Add inline comments on specific code lines        │
│          • Update PR review status (approved/changes needed) │
│ Output:  GitHub PR updated with review                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementation Structure

### File Organization

```
agent_workspace/orchestrator_agent/
├── agent.py                               # Main orchestrator (root agent)
│   ├── _create_github_pipeline()          # Creates main pipeline
│   └── _create_analysis_pipeline()        # Creates nested analysis sub-pipeline
│
└── sub_agents/
    ├── github_fetcher_agent/              # Step 1
    │   ├── __init__.py
    │   └── agent.py
    │
    ├── analysis_agents/                   # Step 2 (grouped)
    │   ├── security_agent/
    │   │   ├── __init__.py
    │   │   └── agent.py
    │   ├── code_quality_agent/
    │   │   ├── __init__.py
    │   │   └── agent.py
    │   ├── engineering_practices_agent/
    │   │   ├── __init__.py
    │   │   └── agent.py
    │   └── carbon_emission_agent/
    │       ├── __init__.py
    │       └── agent.py
    │
    ├── report_synthesizer_agent/          # Step 3
    │   ├── __init__.py
    │   └── agent.py
    │
    └── github_publisher_agent/            # Step 4
        ├── __init__.py
        └── agent.py
```

### Code Structure (Orchestrator)

```python
# agent_workspace/orchestrator_agent/agent.py

from google.adk.agents import Agent, SequentialAgent

class CodeReviewOrchestratorAgent:
    """
    Orchestrator for GitHub PR code reviews.
    Creates a simple, deterministic sequential pipeline.
    """
    
    def __init__(self):
        # Load individual agents
        self.github_fetcher = self._load_github_fetcher()
        self.analysis_pipeline = self._create_analysis_pipeline()
        self.report_synthesizer = self._load_report_synthesizer()
        self.github_publisher = self._load_github_publisher()
        
        # Create main pipeline
        self.root_agent = self._create_github_pipeline()
    
    def _create_analysis_pipeline(self) -> SequentialAgent:
        """
        Create nested analysis pipeline.
        Encapsulates all 4 analysis agents for maintainability.
        """
        return SequentialAgent(
            name="AnalysisPipeline",
            sub_agents=[
                self._load_security_agent(),
                self._load_code_quality_agent(),
                self._load_engineering_agent(),
                self._load_carbon_agent(),
            ],
            description="Run all code analysis agents sequentially"
        )
    
    def _create_github_pipeline(self) -> SequentialAgent:
        """
        Create main GitHub PR review pipeline.
        Simple, deterministic, easy to understand.
        """
        return SequentialAgent(
            name="GitHubPRReviewPipeline",
            sub_agents=[
                self.github_fetcher,        # Step 1: Fetch
                self.analysis_pipeline,     # Step 2: Analyze (nested)
                self.report_synthesizer,    # Step 3: Report
                self.github_publisher,      # Step 4: Publish
            ],
            description="Complete GitHub PR review workflow"
        )
```

---

## 📦 ADK Artifact System Usage

### How ADK Artifacts Work

ADK provides built-in artifact management through `tool_context.save_artifact()`:

```python
# In analysis agent tool
async def scan_security_vulnerabilities(
    code: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """Scan code for security vulnerabilities."""
    
    # Perform analysis
    results = {
        "agent": "security_agent",
        "vulnerabilities": [...],
        "owasp_risks": [...]
    }
    
    # Save artifact via ADK
    from google.genai import types
    artifact_part = types.Part.from_text(
        text=json.dumps(results, indent=2)
    )
    
    version = await tool_context.save_artifact(
        filename="security_analysis.json",
        artifact=artifact_part
    )
    
    return {
        "status": "success",
        "artifact_version": version,
        "findings_count": len(results["vulnerabilities"])
    }
```

### Artifact Organization

**Our Implementation**: Custom `FileArtifactService` (extends ADK's `BaseArtifactService`)

ADK organizes artifacts by:
- **App Name**: `orchestrator_agent`
- **User ID**: Identified from API request
- **Subdirectory**: Automatically determined by filename pattern

**Actual Storage Structure** (managed by `FileArtifactService`):
```
storage_bucket/artifacts/
└── orchestrator_agent/
    └── <user_id>/
        ├── inputs/                          # code_input_*, input_*
        │   └── code_input_12345.py
        │       └── code_input_12345.py.meta.json
        ├── sub_agent_outputs/               # analysis_*
        │   ├── security_analysis.json
        │   │   └── security_analysis.json.meta.json
        │   ├── quality_analysis.json
        │   ├── engineering_analysis.json
        │   └── carbon_analysis.json
        ├── reports/                         # report_*
        │   └── final_report.md
        │       └── final_report.md.meta.json
        └── other/                           # everything else
```

**Key Features**:
- ✅ **Persistent** - files saved to disk, survive server restarts
- ✅ **No cloud dependency** - local file storage
- ✅ **Metadata tracking** - `.meta.json` files with timestamps, sizes, versions
- ✅ **Automatic categorization** - filename patterns determine subdirectory
- ✅ **ADK compatible** - implements `BaseArtifactService` interface

### Loading Artifacts (Report Synthesizer)

```python
# In report synthesizer agent
async def synthesize_report(
    tool_context: ToolContext
) -> str:
    """Load all analysis artifacts and create comprehensive report."""
    
    # ADK provides access to artifacts for current session
    # Implementation depends on ADK 1.17.0 artifact API
    
    session = tool_context.session
    session_id = session.id
    
    # Load artifacts (ADK API)
    security_data = await tool_context.load_artifact("security_analysis.json")
    quality_data = await tool_context.load_artifact("quality_analysis.json")
    engineering_data = await tool_context.load_artifact("engineering_analysis.json")
    carbon_data = await tool_context.load_artifact("carbon_analysis.json")
    
    # Synthesize markdown report
    report_md = generate_comprehensive_report(
        security=json.loads(security_data),
        quality=json.loads(quality_data),
        engineering=json.loads(engineering_data),
        carbon=json.loads(carbon_data)
    )
    
    # Save final report
    report_part = types.Part.from_text(text=report_md)
    await tool_context.save_artifact(
        filename="final_report.md",
        artifact=report_part
    )
    
    return report_md
```

---

## 🎭 Comparison: Old vs New Design

| Aspect | Old Design (Complex) | New Design (Simplified) |
|--------|---------------------|------------------------|
| **Pipeline Structure** | Fetcher → Planning → Router → Report → Publish | Fetcher → Analysis Pipeline → Report → Publish |
| **Agent Count** | 9 agents | 6 agents |
| **Dynamic Behavior** | Planning decides which agents run | All agents run every time (deterministic) |
| **Complexity** | Planning Agent + Dynamic Router + Registry | Simple SequentialAgent nesting |
| **Session State Keys** | 6+ keys (classification, plan, analyses) | 2 keys (github_pr_data, analyses) |
| **Artifact Persistence** | Custom tools + disk I/O | ADK built-in artifact system |
| **Maintainability** | Complex routing logic, hard to debug | Clear sequential flow, easy to understand |
| **Testability** | Hard (varies by planning decision) | Easy (same path every time) |
| **Execution Time** | ~4-5 minutes | ~4-5 minutes (same) |
| **Reliability** | LLM makes routing decisions | No LLM decisions, just execute |

### What We Removed

1. **Classifier Agent** - Not needed for GitHub webhooks (we know it's a PR review)
2. **Planning Agent** - Not needed when all agents run every time
3. **Dynamic Router** - Not needed without dynamic selection
4. **Proxy Tools** - `select_security_agent()`, etc. (not needed)
5. **Agent Registry** - Not needed without dynamic lookup
6. **execution_plan state** - Not needed without planning
7. **Custom save tools** - Use ADK's built-in `save_artifact()`

### What We Kept

1. **GitHub Fetcher** - Essential for getting PR data
2. **All 4 Analysis Agents** - Core value (security, quality, engineering, carbon)
3. **Report Synthesizer** - Essential for creating final output
4. **GitHub Publisher** - Essential for posting to GitHub
5. **Sequential Execution** - Proven reliable pattern

---

## ✅ Benefits of Simplified Design

### 1. **Predictability**
- Same agents run every time
- No LLM-based decisions that could vary
- Easy to test and validate

### 2. **Simplicity**
- Fewer agents = less code = less to maintain
- Clear linear flow: Fetch → Analyze → Report → Publish
- New team members can understand quickly

### 3. **Reliability**
- No reliance on LLM to "remember" to call save tools
- ADK handles artifact persistence
- Deterministic execution path

### 4. **Maintainability**
- Analysis pipeline is separate sub-pipeline
- Can update analysis agents independently
- Clear separation of concerns

### 5. **Debuggability**
- Same execution path every time
- Easy to add logging at each step
- Can test each agent in isolation

---

## 🔧 Artifact Service Configuration

### Current Setup (Already Working)

**Service Implementation**: `util/artifact_service.py`
```python
class FileArtifactService(BaseArtifactService):
    """Custom file-based artifact storage extending ADK's BaseArtifactService"""
    
    def __init__(self, base_dir: str = "./artifacts"):
        self.base_dir = Path(base_dir)
        # Creates storage_bucket/artifacts/ structure
    
    async def save_artifact(
        self, *, app_name, user_id, filename, artifact, 
        session_id=None, custom_metadata=None
    ) -> int:
        # Saves to {base_dir}/{app_name}/{user_id}/{subdir}/{filename}
        # Creates .meta.json with metadata
        return 1  # version number
    
    async def load_artifact(
        self, *, app_name, user_id, filename, 
        session_id=None, version=None
    ) -> Optional[types.Part]:
        # Loads from subdirectories (searches all)
        return types.Part(text=content)
    
    async def list_artifact_keys(
        self, *, app_name, user_id, session_id=None
    ) -> list[str]:
        # Returns list of relative paths
        return ["sub_agent_outputs/security_analysis.json", ...]
```

**Runner Configuration**: Already configured in `main.py` and `agent.py`
```python
from util.artifact_service import FileArtifactService

artifact_service = FileArtifactService(base_dir="../storage_bucket/artifacts")

runner = Runner(
    agent=orchestrator_agent,
    artifact_service=artifact_service,  # ← ADK uses this for all artifact calls
    session_service=session_service
)
```

**How It Works**:
1. Agent calls `tool_context.save_artifact(filename, artifact)`
2. ADK routes to our `FileArtifactService.save_artifact()`
3. Service saves file to disk with automatic subdirectory selection
4. Metadata saved alongside as `.meta.json`
5. Files persist across server restarts

**No Changes Needed** - Current artifact setup is production-ready!

---

## 🚀 Implementation Plan

### Phase 1: Update Orchestrator (2-3 hours)

1. **Disable unused complexity** (do NOT delete - keep for reference):
   ```python
   # DISABLE these agents/components by commenting out:
   # - classifier_agent/ imports and initialization
   # - planning_agent/ imports and initialization
   # - dynamic_router_agent/ imports and initialization
   # - Agent registry dict (comment out)
   # - Proxy selection tools (comment out in tool list)
   
   # Add comments explaining why disabled:
   # "Disabled for simplified sequential pipeline - see SIMPLIFIED_SEQUENTIAL_PIPELINE_DESIGN.md"
   ```

2. **Create analysis pipeline**:
   ```python
   def _create_analysis_pipeline(self) -> SequentialAgent:
       return SequentialAgent(
           name="AnalysisPipeline",
           sub_agents=[
               security_agent,
               code_quality_agent,
               engineering_agent,
               carbon_agent,
           ]
       )
   ```

3. **Simplify main pipeline**:
   ```python
   def _create_github_pipeline(self) -> SequentialAgent:
       return SequentialAgent(
           name="GitHubPRReviewPipeline",
           sub_agents=[
               github_fetcher,
               analysis_pipeline,      # Nested!
               report_synthesizer,
               github_publisher,
           ]
       )
   ```

### Phase 2: Update Analysis Agents (1-2 hours)

For each analysis agent:

1. **Simplify instructions** - remove mentions of planning/routing
2. **Keep artifact saving** - use ADK's `tool_context.save_artifact()`
3. **Remove output_key if not needed** - ADK saves artifacts anyway
4. **Focus on analysis quality** - simpler agents = better prompts

### Phase 3: Update Report Synthesizer (2-3 hours)

1. **Use ADK artifact loading**:
   ```python
   async def load_all_analyses(tool_context: ToolContext):
       # Query ADK artifact system for current session
       artifacts = await tool_context.list_artifacts()
       # Load each analysis JSON
       # Return dict of all analyses
   ```

2. **Synthesize comprehensive report**:
   - Parse all 4 JSON analyses
   - Create markdown with all sections
   - Save as `final_report.md` artifact

### Phase 4: Testing (2-3 hours)

1. **Unit tests** for each agent
2. **Integration test** for full pipeline
3. **E2E test** with mock GitHub data
4. **Validate artifacts** are saved correctly

### Phase 5: Documentation (1-2 hours)

1. Update README with new architecture
2. Update API documentation
3. Create architecture diagram
4. Update CHANGELOG

**Total Estimated Time**: 8-13 hours

---

## 📝 Session State Design

### Minimal State Keys

```python
session.state = {
    # Input (from API request)
    "github_context": {
        "repo": "owner/repo",
        "pr_number": 42,
        "head_sha": "abc123",
        ...
    },
    
    # Step 1 output
    "github_pr_data": {
        "files": [...],
        "diffs": [...],
        "metadata": {...}
    },
    
    # Steps 2a-2d outputs (optional - artifacts are primary storage)
    "security_analysis": {...},      # Also saved as artifact
    "quality_analysis": {...},       # Also saved as artifact
    "engineering_analysis": {...},   # Also saved as artifact
    "carbon_analysis": {...},        # Also saved as artifact
    
    # Step 3 output (optional - artifact is primary storage)
    "final_report": "..."            # Also saved as artifact
}
```

**Note**: Session state is ephemeral. Artifacts are the **source of truth** for persistent data.

---

## 🔍 Open Questions - ✅ RESOLVED

### 1. **ADK Artifact API** - ✅ CONFIRMED
   - ✅ **ADK 1.17.0 provides full artifact API** via `CallbackContext` (parent of `ToolContext`):
     - `async def save_artifact(filename: str, artifact: types.Part) -> int`
     - `async def load_artifact(filename: str, version: Optional[int] = None) -> Optional[types.Part]`
     - `async def list_artifacts() -> list[str]`
   - ✅ **Custom `FileArtifactService` already implemented** in `util/artifact_service.py`
     - Extends `BaseArtifactService` (ADK's abstract base class)
     - Provides persistent local file storage
     - Directory structure: `./artifacts/{app_name}/{user_id}/`
       - `inputs/` - Code files
       - `reports/` - Final reports
       - `sub_agent_outputs/` - Analysis results
       - `other/` - Miscellaneous
     - Saves with `.meta.json` metadata files
     - Already tested and working in codebase
   - ✅ **No need for ADK version change** - Current setup is optimal

### 2. **GitHub Publisher** - ✅ DECIDED
   - ✅ **Load report from artifacts** using `tool_context.load_artifact("final_report.md")`
   - Artifacts are persistent and reliable
   - Session state is ephemeral - use artifacts as source of truth

### 3. **Error Handling** - ✅ DECIDED
   - ✅ **Option A: Stop and return partial results (safer)**
   - If any analysis agent fails, pipeline stops immediately
   - Partial results available in session state and artifacts
   - Clear error reporting to user
   - Can add Option B (continue on error) later if needed for resilience

### 4. **Artifact Cleanup** - ✅ DECIDED
   - ✅ **Implement in Phase 2** after core pipeline is stable
   - Will add cleanup policy after validating core functionality
   - Considerations for Phase 2:
     - Retention policy (30/60/90 days)
     - Cleanup trigger (manual/scheduled/event-based)
     - Archive vs delete strategy
     - Disk space monitoring

---

## 🔧 Implementation Issue: Data Format Mismatch

### Problem Discovered During Testing (December 8, 2025)

**Symptom**: Pipeline executes successfully but analysis tools cannot process the code.

**Root Cause**: Data format mismatch between GitHub Fetcher and Analysis Tools:

```
GitHub Fetcher Output:
├─ session.state["github_pr_files"] = [
│    {
│      "filename": "ChatPanel.tsx",
│      "content": "import React...",      ← Full file content (string)
│      "language": "typescript",
│      "status": "added",
│      "additions": 378,
│      "patch": "@@ -0,0 +1,378 @@..."
│    }
│  ]

Analysis Tools Expected Input:
├─ tool_context.state["code"] = "..."      ← Raw code string
├─ tool_context.state["language"] = "..."  ← Language identifier
├─ tool_context.state["file_path"] = "..." ← File path
OR
├─ Repository path on disk to scan
```

**Impact**:
- ✅ Pipeline architecture works correctly
- ✅ All agents execute in sequence
- ❌ Tools return empty results ("No code provided")
- ❌ Final report shows no analysis findings

### Solution: GitHub Data Adapter Tool

**Option 1: Create GitHub Data Adapter Tool** ⭐ **RECOMMENDED**

This tool bridges the gap between GitHub API data structures and analysis tool expectations.

---

## 🛠️ GitHub Data Adapter Tool Design

### Purpose

Transform GitHub PR file data from `github_pr_files` session state into format that existing analysis tools can consume.

### Key Responsibilities

1. **Extract code from GitHub data structures**
2. **Prepare code for each analysis tool**
3. **Handle multiple files in PR**
4. **Preserve file context (filename, language, metadata)**

### Tool Specification

```python
# tools/github_data_adapter.py

def prepare_files_for_analysis(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Adapt GitHub PR files data for analysis tools.
    
    Reads github_pr_files from session state and transforms into
    format that analysis tools expect (code, language, file_path).
    
    Input (from session.state["github_pr_files"]):
        [
            {
                "filename": "src/ChatPanel.tsx",
                "content": "import React...",
                "language": "typescript",
                "status": "added",
                "additions": 378,
                "deletions": 0,
                "patch": "..."
            },
            ...
        ]
    
    Output (stored in session.state):
        {
            "files_prepared": True,
            "file_count": 2,
            "files": [
                {
                    "file_path": "src/ChatPanel.tsx",
                    "code": "import React...",
                    "language": "typescript",
                    "lines": 378,
                    "status": "added"
                },
                ...
            ],
            "current_file_index": 0,
            
            # Current file ready for tools
            "code": "import React...",              ← For analysis tools
            "language": "typescript",               ← For analysis tools
            "file_path": "src/ChatPanel.tsx"        ← For analysis tools
        }
    
    Returns:
        {
            "status": "success",
            "files_prepared": 2,
            "message": "Prepared 2 files for analysis"
        }
    """
```

### Integration into Sequential Pipeline

**Updated Step 2: Analysis Pipeline** (with adapter)

```
┌──────────────────────────────────────────────────────────────┐
│ STEP 2: Analysis Pipeline (SequentialAgent - NESTED)         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ 2.0 GitHub Data Adapter (NEW - First in pipeline)     │  │
│ │ ────────────────────────                               │  │
│ │ Purpose: Transform GitHub PR data for analysis tools   │  │
│ │                                                         │  │
│ │ Input:  session.state["github_pr_files"]              │  │
│ │ Tool:   prepare_files_for_analysis()                  │  │
│ │ Output: session.state["code"] = "..."                 │  │
│ │         session.state["language"] = "..."             │  │
│ │         session.state["file_path"] = "..."            │  │
│ │         session.state["files"] = [...]                │  │
│ │                                                         │  │
│ │ Strategy:                                              │  │
│ │ • Extract all files from github_pr_files              │  │
│ │ • Combine multi-file PRs into single analysis context │  │
│ │ • OR analyze each file separately (configurable)      │  │
│ │ • Set current file context for analysis tools         │  │
│ └────────────────────────────────────────────────────────┘  │
│                        ↓                                      │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ 2a. Security Agent                                     │  │
│ │ ──────────────────                                     │  │
│ │ Tools: scan_security_vulnerabilities()                 │  │
│ │        ↓ reads tool_context.state["code"]             │  │
│ │        ↓ reads tool_context.state["language"]         │  │
│ │        ↓ reads tool_context.state["file_path"]        │  │
│ └────────────────────────────────────────────────────────┘  │
│                        ↓                                      │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ 2b. Code Quality Agent                                 │  │
│ │ ───────────────────                                    │  │
│ │ Tools: analyze_code_complexity()                       │  │
│ │        analyze_static_code()                           │  │
│ │        parse_code_ast()                                │  │
│ │        ↓ All read from tool_context.state["code"]     │  │
│ └────────────────────────────────────────────────────────┘  │
│                        ↓                                      │
│ │ 2c. Engineering Practices Agent                        │  │
│ │ 2d. Carbon Emission Agent                              │  │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Multi-File PR Handling Strategy

**Strategy A: Concatenate All Files** ⭐ **RECOMMENDED FOR PHASE 1**

```python
# Combine all files into single analysis context
combined_code = ""
for file in github_pr_files:
    combined_code += f"\n\n# File: {file['filename']}\n"
    combined_code += f"# Language: {file['language']}\n"
    combined_code += file['content']
    combined_code += "\n\n"

session.state["code"] = combined_code
session.state["language"] = "multi"  # or dominant language
session.state["file_path"] = "PR_combined"
```

**Benefits**:
- Simple to implement
- Agents see full PR context
- Cross-file issue detection possible
- Works with current tools unchanged

**Limitations**:
- Large PRs may hit token limits
- Language-specific tools may struggle with multi-language

**Strategy B: Analyze Files Separately** (FUTURE - Phase 2)

```python
# Run each analysis agent multiple times (once per file)
for file in github_pr_files:
    session.state["code"] = file['content']
    session.state["language"] = file['language']
    session.state["file_path"] = file['filename']
    
    # Run all 4 analysis agents for this file
    await security_agent.run_async(ctx)
    await quality_agent.run_async(ctx)
    await engineering_agent.run_async(ctx)
    await carbon_agent.run_async(ctx)
    
    # Aggregate results per file
```

**Benefits**:
- Better for large multi-file PRs
- Language-specific tools work better
- More granular per-file findings

**Limitations**:
- More complex orchestration
- Misses cross-file issues
- Requires result aggregation logic

### Implementation Steps

**Phase 1: Minimum Viable Adapter**

1. **Create tool**: `tools/github_data_adapter.py`
   - Implement `prepare_files_for_analysis()` function
   - Use Strategy A (concatenate all files)
   - Store prepared data in session state

2. **Create agent**: `agent_workspace/orchestrator_agent/sub_agents/github_data_adapter_agent/`
   - Simple LLM agent with one tool
   - Instruction: "Call prepare_files_for_analysis() to transform GitHub PR data"
   - No complex logic needed

3. **Update AnalysisPipeline** in orchestrator:
   ```python
   def _create_analysis_pipeline(self) -> SequentialAgent:
       return SequentialAgent(
           name="AnalysisPipeline",
           sub_agents=[
               self.github_data_adapter,      # ← NEW (Step 0)
               self.security_agent,           # Step 1
               self.code_quality_agent,       # Step 2
               self.engineering_agent,        # Step 3
               self.carbon_agent,             # Step 4
           ]
       )
   ```

4. **Test with E2E test**:
   - Run existing test with ChatPanel.tsx + orecestrator_agent_bk.py
   - Verify tools receive code correctly
   - Verify analysis findings are non-empty

**Phase 2: Enhanced Multi-File Support** (FUTURE)

- Add Strategy B (per-file analysis)
- Implement result aggregation
- Handle language detection
- Token optimization for large PRs

### Test File Context

The E2E test uses real files from `/Users/rahulgupta/Documents/Coding/agentic-codereview/tests/test_files/`:

1. **ChatPanel.tsx** (378 lines, TypeScript)
   - React component with WebSocket logic
   - Has intentional issues for testing:
     - Complex nested useEffect logic
     - Reconnection loop potential
     - State management complexity

2. **orecestrator_agent_bk.py** (771 lines, Python)
   - Old orchestrator backup file
   - Complex async orchestration logic
   - Sequential execution patterns

**Test Expectations**:
- GitHub Fetcher loads both files with full content
- Data Adapter extracts and combines code
- Security Agent finds issues (MD5, hardcoded values, etc.)
- Quality Agent detects complexity issues
- Engineering Agent evaluates patterns
- Carbon Agent assesses efficiency
- Report Synthesizer creates comprehensive markdown

---

## 📚 References

- [ADK Sequential Workflows](https://raphaelmansuy.github.io/adk_training/docs/sequential_workflows)
- [ADK Artifact Documentation](https://developers.google.com/adk/artifacts) (TODO: verify link)
- [GitHub PR Review API](https://docs.github.com/en/rest/pulls/reviews)

---

## ✏️ Next Steps

### Phase 1 Implementation (December 8, 2025)

**Status**: ✅ COMPLETE - Pipeline architecture validated

**Completed**:
1. ✅ Simplified orchestrator to sequential pipeline (3 steps)
2. ✅ Created nested AnalysisPipeline (4 analysis agents)
3. ✅ Updated all agents to sequential context
4. ✅ Disabled planning/routing/dynamic selection
5. ✅ Tested E2E - pipeline executes correctly

**Issue Discovered**:
❌ Data format mismatch between GitHub Fetcher and Analysis Tools
- Fetcher provides: `{filename, content, language, ...}`
- Tools expect: `{code, language, file_path}` in tool_context.state

### Phase 1B: GitHub Data Adapter Implementation (NEXT)

**Priority**: 🔥 CRITICAL - Blocks complete E2E testing

**Tasks**:
1. ⏳ Create `tools/github_data_adapter.py`
   - Implement `prepare_files_for_analysis()` function
   - Use Strategy A (concatenate all files)
   - Transform github_pr_files → code/language/file_path

2. ⏳ Create `agent_workspace/orchestrator_agent/sub_agents/github_data_adapter_agent/`
   - Simple agent with single tool
   - Instruction: Call prepare_files_for_analysis()
   - No complex logic required

3. ⏳ Update orchestrator's `_create_analysis_pipeline()`
   - Add github_data_adapter as first agent
   - Ensure it runs before security/quality/engineering/carbon

4. ⏳ Test E2E with real files
   - Verify tools receive code correctly
   - Verify non-empty analysis findings
   - Verify comprehensive report generation

**Estimated Time**: 1-2 hours

**Success Criteria**:
- ✅ All analysis tools receive code successfully
- ✅ Security agent finds vulnerabilities
- ✅ Quality agent detects complexity issues
- ✅ Engineering agent evaluates patterns
- ✅ Carbon agent assesses efficiency
- ✅ Report synthesizer creates full markdown with findings

### Phase 2 Considerations (FUTURE)

**Future Enhancements**:
- Per-file analysis strategy (Strategy B)
- Token optimization for large PRs
- Result aggregation across files
- Artifact cleanup policy
- Web UI pipeline visualization
- Agent parallelization (if speed critical)

But for now: **Fix the data adapter, validate end-to-end, iterate based on real usage.**

---

*End of Design Document*
