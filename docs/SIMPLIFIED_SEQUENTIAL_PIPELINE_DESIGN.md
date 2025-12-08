# Simplified Sequential Agent Pipeline Design

**Status**: Design Review (December 8, 2025)  
**Date**: December 8, 2025  
**Architecture Pattern**: Deterministic Sequential Pipeline  
**Priority**: GitHub Integration with ADK Built-in Artifacts  
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

ADK organizes artifacts by:
- **Session ID**: Each API request gets unique session
- **User ID**: Identified from API request
- **App Name**: `orchestrator_agent`

**Expected Structure** (managed by ADK):
```
ADK_STORAGE/
└── artifacts/
    └── orchestrator_agent/
        └── <user_id>/
            └── <session_id>/
                ├── security_analysis.json
                ├── quality_analysis.json
                ├── engineering_analysis.json
                ├── carbon_analysis.json
                └── final_report.md
```

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

## 🚀 Implementation Plan

### Phase 1: Update Orchestrator (2-3 hours)

1. **Remove complexity**:
   ```python
   # DELETE these agents/components:
   - classifier_agent/
   - planning_agent/
   - dynamic_router_agent/
   - Agent registry dict
   - Proxy selection tools
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

## 🔍 Open Questions

1. **ADK Artifact API**: 
   - Does ADK 1.17.0 provide `tool_context.load_artifact(filename)`?
   - Or do we need `tool_context.list_artifacts()` + query?
   - Check ADK documentation for artifact retrieval APIs

2. **GitHub Publisher**:
   - Should it load report from artifacts or session state?
   - Artifacts are more reliable (persisted)

3. **Error Handling**:
   - If analysis agent fails, should pipeline continue?
   - Or stop and return partial results?

4. **Artifact Cleanup**:
   - Should old artifacts be deleted after PR closes?
   - Retention policy (30 days, 90 days)?

---

## 📚 References

- [ADK Sequential Workflows](https://raphaelmansuy.github.io/adk_training/docs/sequential_workflows)
- [ADK Artifact Documentation](https://developers.google.com/adk/artifacts) (TODO: verify link)
- [GitHub PR Review API](https://docs.github.com/en/rest/pulls/reviews)

---

## ✏️ Next Steps

**Immediate**:
1. ✅ Review and approve this simplified design
2. ⏳ Verify ADK 1.17.0 artifact API capabilities
3. ⏳ Create implementation task breakdown
4. ⏳ Update agent_workspace/ structure

**Future Considerations**:
- Web UI pipeline (if needed later)
- Agent parallelization (if speed becomes critical)
- Selective agent execution (if resources constrained)

But for now: **Keep it simple, make it work, iterate based on real usage.**

---

*End of Design Document*
