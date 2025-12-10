# Dynamic Router Agent - Implementation Plan

**Created**: December 3, 2025  
**Updated**: December 7, 2025 - **GitHub Pipeline Priority**  
**Status**: Phases 1-3 Complete, Phase 4 Ready  
**Based On**: [DYNAMIC_ROUTER_AGENT_DESIGN.md](./DYNAMIC_ROUTER_AGENT_DESIGN.md)

---

## 🔄 December 7, 2025 Update - Architecture Decision

### Key Changes

**Discovery**: ADK 1.19.0 agents can only have **ONE parent**. This means we cannot create both WebPipeline and GitHubPipeline simultaneously as they would try to share the same `dynamic_router` agent.

**Decision**: 
- ✅ **Prioritize GitHub Pipeline** (production integration)
- ⏸️ **Defer Web Pipeline** (ADK web UI for development)
- 🔄 **Future**: Implement agent cloning pattern

**Impact on Implementation**:
```diff
- root_agent = _create_web_pipeline()      # Was: Web UI first
+ root_agent = _create_github_pipeline()   # Now: GitHub integration first
```

**Current Status**:
- ✅ Phase 1: Cleanup complete (dead code removed)
- ✅ Phase 2: DynamicRouterAgent built (ParallelAgent wrapper)
- ✅ Phase 3: Orchestrator integrated (GitHub pipeline only)
- 🔄 Phase 4: Testing ready (GitHub-focused tests)
- ⏸️ Phase 5: Documentation pending

---

## 🎯 Executive Summary

**Problem**: Analysis agents never execute because ADK 1.19.0's `SequentialAgent` cannot dynamically inject agents at runtime. The `_create_execution_pipeline()` method exists but is **never called** - it's dead code.

**Root Cause**: 
- Current orchestrator tries to use `dynamic_agents` and `routing_function` which don't exist in ADK 1.19.0
- **ADK Limitation**: Each agent can only have ONE parent (cannot reuse agents in multiple pipelines)
- `_create_execution_pipeline()` method is orphaned - no caller
- WebPipeline returns a simple pass-through Agent, not a real pipeline

**Solution**: Implement `DynamicRouterAgent` as a sub-agent that acts as middleware in the SequentialAgent flow.

**Implementation Priority**: 
- ✅ **GitHub Pipeline First** (production integration priority)
- ✅ **Sequential Execution** (accuracy over speed for PR reviews)
- ⏸️ **Web Pipeline Deferred** (ADK single-parent constraint)
- 🔄 **Future**: Implement agent cloning for multiple pipelines

**Execution Strategy**:
- **Sequential** (not parallel) - Each analysis agent runs to completion before the next
- Prioritizes thoroughness and accuracy over speed
- GitHub PRs are async - users don't wait for immediate response

---

## 📊 Current State Analysis

### ✅ What We Have (Components to KEEP)

| Component | Location | Status | Purpose |
|-----------|----------|--------|---------|
| **ClassifierAgent** | `sub_agents/classifier_agent/` | ⏸️ Available | Classifies user intent (Web UI only - deferred) |
| **PlanningAgent** | `sub_agents/planning_agent/` | ✅ Working | Uses PlanReActPlanner, outputs execution_plan |
| **SecurityAgent** | `sub_agents/security_agent/` | ✅ Working | Security vulnerability scanning |
| **CodeQualityAgent** | `sub_agents/code_quality_agent/` | ✅ Working | Complexity & quality analysis |
| **EngineeringPracticesAgent** | `sub_agents/engineering_practices_agent/` | ✅ Working | Best practices evaluation |
| **CarbonEmissionAgent** | `sub_agents/carbon_emission_agent/` | ✅ Working | Carbon footprint analysis |
| **ReportSynthesizerAgent** | `sub_agents/report_synthesizer_agent/` | ✅ Working | Generates final markdown report |
| **GitHubFetcherAgent** | `sub_agents/github_fetcher_agent/` | ✅ Working | Fetches PR data from GitHub API |
| **GitHubPublisherAgent** | `sub_agents/github_publisher_agent/` | ✅ Working | Posts review to GitHub PR |
| **FileArtifactService** | `util/artifact_service.py` | ✅ Working | Saves artifacts to disk |
| **JSONFileSessionService** | `util/session.py` | ✅ Working | Session management |
| **Tools** | `tools/` directory | ✅ Working | Analysis tools (complexity, security, etc.) |

### ❌ What's BROKEN (Components to FIX/REMOVE)

| Component | Location | Issue | Action |
|-----------|----------|-------|--------|
| **SourceDetectorAgent** | `sub_agents/source_detector_agent/` | ❌ Obsolete | **REMOVE** - Not needed with new design |
| **_create_execution_pipeline()** | `agent.py` lines 196-260 | ❌ Dead code | **REMOVE** - Never called |
| **_create_web_pipeline()** | `agent.py` lines 285-309 | ❌ Returns dummy Agent | **REPLACE** with real SequentialAgent |
| **_create_github_pipeline()** | `agent.py` lines 262-283 | ❌ Missing router | **UPDATE** to include DynamicRouterAgent |
| **_create_root_workflow()** | `agent.py` lines 311-331 | ❌ Incorrect pattern | **REPLACE** - No need for root wrapper |
| **_route_by_source()** | `agent.py` lines 165-193 | ❌ Unused | **REMOVE** - dynamic_agents doesn't exist |
| **_get_agent_map()** | `agent.py` lines 150-163 | ⚠️ Underutilized | **KEEP** but use in DynamicRouterAgent |

### 🆕 What We Need to BUILD

| Component | Location | Purpose | Priority |
|-----------|----------|---------|----------|
| **DynamicRouterAgent** | `sub_agents/dynamic_router_agent/agent.py` | Middleware that wraps all agents in SequentialAgent for thorough, sequential execution | **P0 - Critical** |
| **Updated Orchestrator** | `agent.py` | Create agent registry, instantiate routers, wire into pipelines | **P0 - Critical** |

---

## 🏗️ Architecture Decision: GitHub Pipeline Priority

### ADK 1.19.0 Single-Parent Constraint

**Discovery**: During Phase 3 implementation, we discovered that ADK agents can only have ONE parent:

```python
# ❌ FAILS: Agent already has parent
web_pipeline = SequentialAgent(sub_agents=[..., dynamic_router, ...])
github_pipeline = SequentialAgent(sub_agents=[..., dynamic_router, ...])
# Error: Agent `DynamicRouter` already has a parent agent
```

### Decision Matrix

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **Prioritize GitHub Pipeline** | ✅ Production use case<br>✅ Real integration value<br>✅ Automated PR reviews | ❌ No ADK web UI for testing | ✅ **CHOSEN** |
| **Prioritize Web Pipeline** | ✅ Easy testing via ADK UI<br>✅ Interactive development | ❌ Not production use case<br>❌ Manual testing only | ❌ Rejected |
| **Agent Cloning** | ✅ Support both pipelines | ❌ Complex implementation<br>❌ Requires custom cloning logic | 🔄 Future work |
| **Separate Agent Instances** | ✅ Simple solution | ❌ 2x memory usage<br>❌ Tool registration conflicts | 🔄 Future work |

### Implementation Strategy

**Phase 3 (Current)**:
```python
class CodeReviewOrchestrator:
    def __init__(self):
        # ... load all agents ...
        
        # Create agent registry
        self.analysis_agent_registry = {
            "security": self.security_agent,
            "code_quality": self.code_quality_agent,
            "engineering": self.engineering_agent,
            "carbon": self.carbon_agent,
        }
        
        # Create dynamic router
        self.dynamic_router = DynamicRouterAgent(
            agent_registry=self.analysis_agent_registry
        )
        
        # ✅ PRIORITY: GitHub Pipeline
        self.root_agent = self._create_github_pipeline()
        
        # ❌ DISABLED: Web Pipeline (agent parent conflict)
        # self.web_pipeline = self._create_web_pipeline()
```

**GitHub Pipeline Structure**:
```
GitHubPipeline (SequentialAgent) - root_agent
  ├─ github_fetcher_agent        # Fetch PR data from GitHub API
  ├─ planning_agent              # Select which analyses to run
  ├─ dynamic_router              # Execute all agents SEQUENTIALLY
  │   ├─ security_agent          # ← Runs first, completes fully
  │   ├─ code_quality_agent      # ← Runs second, completes fully
  │   ├─ engineering_agent       # ← Runs third, completes fully
  │   └─ carbon_agent            # ← Runs fourth, completes fully
  ├─ report_synthesizer_agent    # Generate markdown report
  └─ github_publisher_agent      # Post review to PR

Note: Sequential execution prioritizes accuracy over speed.
Each agent completes before the next starts.
```

**Web Pipeline** (Deferred):
- Status: Not implemented (would conflict with GitHub pipeline)
- Alternative: Use GitHub pipeline with mock PR data for testing
- Future: Implement agent cloning pattern

### Testing Strategy

Without ADK Web UI, we'll use:
1. **Unit Tests**: Test individual agents
2. **Integration Tests**: Test pipeline with mock GitHub payloads
3. **E2E Tests**: Test full flow with test repository
4. **Manual Testing**: Direct Python script execution or API endpoints

---

## 🔍 Code Review Findings

### File: `agent_workspace/orchestrator_agent/agent.py`

#### Lines 1-40: ✅ **KEEP** - Documentation & Imports
- **Status**: Accurate architecture diagram (but not yet implemented)
- **Action**: Update diagram after DynamicRouterAgent implementation

#### Lines 50-60: ✅ **KEEP** - Service Initialization
```python
_artifact_service = FileArtifactService(base_dir="../storage_bucket/artifacts")
_session_service = JSONFileSessionService(uri="jsonfile://../storage_bucket")
register_services(artifact_service=_artifact_service, session_service=_session_service)
```
- **Status**: Working correctly
- **Action**: No changes needed

#### Lines 63-72: ✅ **KEEP** - Sub-agent Imports
- **Status**: All imports valid
- **Action**: Add `from .sub_agents.dynamic_router_agent.agent import DynamicRouterAgent`

#### Lines 90-143: ✅ **KEEP** - Orchestrator `__init__`
- **Status**: Loads all agents correctly
- **Action**: Add agent registry creation and DynamicRouterAgent instantiation

#### Lines 150-163: ⚠️ **REFACTOR** - `_get_agent_map()`
```python
def _get_agent_map(self) -> Dict[str, Agent]:
    return {
        "security": self.security_agent,
        "code_quality": self.code_quality_agent,
        "engineering": self.engineering_agent,
        "carbon": self.carbon_agent
    }
```
- **Current Usage**: Used by `_create_execution_pipeline()` (dead code)
- **New Usage**: Will be used by DynamicRouterAgent constructor
- **Action**: Rename to `analysis_agent_registry` and move to `__init__`

#### Lines 165-193: ❌ **DELETE** - `_route_by_source()`
```python
def _route_by_source(self, context, result) -> str:
    source = result.get('source', 'web_ui')
    if source == 'github_webhook':
        return 'github_pipeline'
    else:
        return 'web_pipeline'
```
- **Issue**: `dynamic_agents` and `routing_function` don't exist in ADK 1.19.0
- **Evidence**: Comment on line 315 confirms this
- **Action**: **DELETE** - Not needed with separate pipeline entry points

#### Lines 196-260: ❌ **DELETE** - `_create_execution_pipeline()`
```python
def _create_execution_pipeline(self, context) -> Optional[Agent]:
    execution_plan = context.session.state.get('execution_plan')
    # ... creates ParallelAgent or SequentialAgent dynamically
```
- **Issue**: This method is **NEVER CALLED** - it's dead code
- **Evidence**: No caller exists in codebase
- **Root Cause**: ADK 1.19.0 doesn't support mid-pipeline injection
- **Action**: **DELETE** - Logic moves into DynamicRouterAgent

#### Lines 262-283: ⚠️ **UPDATE** - `_create_github_pipeline()`
```python
def _create_github_pipeline(self) -> SequentialAgent:
    return SequentialAgent(
        name="GitHubPipeline",
        sub_agents=[
            self.github_fetcher,
            self.planning_agent_github,
            # ExecutionPipeline inserted here dynamically  ← ❌ THIS NEVER HAPPENS!
            self.report_synthesizer_github,
            self.github_publisher
        ],
        description="GitHub webhook processing pipeline"
    )
```
- **Issue**: Comment says "ExecutionPipeline inserted here dynamically" but that's impossible
- **Action**: **INSERT** `self.dynamic_router_github` between planning and report synthesizer

#### Lines 285-309: ⏸️ **DEFER** - `_create_web_pipeline()`
```python
def _create_web_pipeline(self) -> Agent:
    # Return a simple pass-through agent
    # The actual orchestration will happen in the parent
    return Agent(
        name="WebPipeline",
        model=get_sub_agent_model(),
        description="Web UI pipeline coordinator",
        instruction="""You are a pipeline coordinator. 
        Simply acknowledge the user's request and pass it through.
        Say: 'Processing your code review request...'
        """.strip()
    )
```
- **Issue**: This is a **dummy agent** that does nothing!
- **Root Cause**: Comment says "ADK 1.19.0 doesn't support dynamic sub-agent injection"
- **Action**: **DEFER** - GitHub pipeline takes priority due to ADK single-parent constraint

#### Lines 311-331: ❌ **REPLACE** - `_create_root_workflow()`
```python
def _create_root_workflow(self) -> Agent:
    # Return WebPipeline as the root for ADK web UI
    web_pipeline = self._create_web_pipeline()
    
    logger.info("✅ [Orchestrator] Using WebPipeline as root agent for ADK web UI")
    logger.info("⚠️  [Orchestrator] GitHub webhook support requires separate API endpoint")
    
    return web_pipeline
```
- **Issue**: Just returns dummy WebPipeline
- **Action**: **REPLACE** - Directly return proper SequentialAgent, no wrapper needed

#### Lines 333-370: ✅ **KEEP** - Exports
- **Status**: Correct pattern
- **Action**: No changes (still export root_agent for ADK CLI)

---

## 📁 Directory Structure Changes

### Current Structure
```
agent_workspace/orchestrator_agent/
├── agent.py                          # Main orchestrator (needs updates)
└── sub_agents/
    ├── source_detector_agent/        # ❌ REMOVE
    ├── classifier_agent/             # ✅ KEEP
    ├── planning_agent/               # ✅ KEEP
    ├── security_agent/               # ✅ KEEP
    ├── code_quality_agent/           # ✅ KEEP
    ├── engineering_practices_agent/  # ✅ KEEP
    ├── carbon_emission_agent/        # ✅ KEEP
    ├── report_synthesizer_agent/     # ✅ KEEP
    ├── github_fetcher_agent/         # ✅ KEEP
    └── github_publisher_agent/       # ✅ KEEP
```

### Target Structure
```
agent_workspace/orchestrator_agent/
├── agent.py                          # ✅ UPDATED
└── sub_agents/
    ├── dynamic_router_agent/         # 🆕 NEW
    │   ├── __init__.py
    │   └── agent.py
    ├── classifier_agent/             # ✅ KEEP
    ├── planning_agent/               # ✅ KEEP
    ├── security_agent/               # ✅ KEEP
    ├── code_quality_agent/           # ✅ KEEP
    ├── engineering_practices_agent/  # ✅ KEEP
    ├── carbon_emission_agent/        # ✅ KEEP
    ├── report_synthesizer_agent/     # ✅ KEEP
    ├── github_fetcher_agent/         # ✅ KEEP
    └── github_publisher_agent/       # ✅ KEEP
```

---

## 🚀 Implementation Plan

### Phase 1: Preparation (Clean up deprecated code)

**Priority**: P0 (Must do first to avoid confusion)

#### Task 1.1: Remove source_detector_agent ❌
- **Why**: Not needed - Web UI and GitHub webhook have separate entry points
- **Files to delete**:
  - `agent_workspace/orchestrator_agent/sub_agents/source_detector_agent/`
  - All files in directory (agent.py, __init__.py)
- **Files to update**:
  - `agent_workspace/orchestrator_agent/agent.py`: Remove import
  - `agent_workspace/orchestrator_agent/sub_agents/__init__.py`: Remove from exports
- **Verification**: `grep -r "source_detector" agent_workspace/` returns no results

#### Task 1.2: Remove dead code from orchestrator ❌
- **File**: `agent_workspace/orchestrator_agent/agent.py`
- **Delete**:
  - Lines 165-193: `_route_by_source()` method
  - Lines 196-260: `_create_execution_pipeline()` method
  - Lines 311-331: `_create_root_workflow()` method
- **Reason**: All three methods are unused/broken
- **Verification**: Run `grep "_route_by_source\|_create_execution_pipeline\|_create_root_workflow" agent_workspace/orchestrator_agent/agent.py` returns nothing

---

### Phase 2: Build DynamicRouterAgent (Independent component)

**Priority**: P0 (Core functionality)

#### Task 2.1: Create directory structure 🆕
```bash
mkdir -p agent_workspace/orchestrator_agent/sub_agents/dynamic_router_agent
touch agent_workspace/orchestrator_agent/sub_agents/dynamic_router_agent/__init__.py
touch agent_workspace/orchestrator_agent/sub_agents/dynamic_router_agent/agent.py
```

#### Task 2.2: Implement DynamicRouterAgent class 🆕
- **File**: `agent_workspace/orchestrator_agent/sub_agents/dynamic_router_agent/agent.py`
- **Source**: Copy from [DYNAMIC_ROUTER_AGENT_DESIGN.md](./DYNAMIC_ROUTER_AGENT_DESIGN.md) lines 300-500
- **Key features**:
  - Constructor takes `agent_registry`, `max_concurrent_agents`, `large_code_threshold`
  - `_run_async_impl()` with 4 phases:
    1. Read execution_plan from session state
    2. Filter agent_registry by selected_agents
    3. Create dynamic ParallelAgent/SequentialAgent
    4. Execute and yield events
  - Resource management (controlled parallel, sequential for large code)
- **Dependencies**:
  ```python
  from google.adk.agents import BaseAgent, ParallelAgent, SequentialAgent
  from google.adk.core import InvocationContext, Event
  from typing import AsyncGenerator, Dict, List, Optional
  import logging
  ```
- **Verification**: File compiles without errors

#### Task 2.3: Create __init__.py exports 🆕
- **File**: `agent_workspace/orchestrator_agent/sub_agents/dynamic_router_agent/__init__.py`
- **Content**:
  ```python
  from .agent import DynamicRouterAgent
  
  __all__ = ["DynamicRouterAgent"]
  ```

---

### Phase 3: Update Orchestrator (Wire everything together)

**Priority**: P0 (Critical integration)

#### Task 3.1: Add import for DynamicRouterAgent
- **File**: `agent_workspace/orchestrator_agent/agent.py`
- **Location**: After line 72 (after other sub-agent imports)
- **Add**:
  ```python
  from .sub_agents.dynamic_router_agent.agent import DynamicRouterAgent
  ```

#### Task 3.2: Create agent registry in `__init__`
- **File**: `agent_workspace/orchestrator_agent/agent.py`
- **Location**: After line 143 (after loading all analysis agents)
- **Add**:
  ```python
  # =====================================================================
  # AGENT REGISTRY FOR DYNAMIC ROUTING
  # =====================================================================
  
  logger.info("🔧 [Orchestrator] Creating agent registry for dynamic routing...")
  
  self.analysis_agent_registry = {
      "security": self.security_agent,
      "code_quality": self.code_quality_agent,
      "engineering": self.engineering_agent,
      "carbon": self.carbon_agent,
  }
  
  logger.info(f"✅ [Orchestrator] Agent registry created with {len(self.analysis_agent_registry)} agents")
  ```

#### Task 3.3: Create DynamicRouterAgent instance
- **File**: `agent_workspace/orchestrator_agent/agent.py`
- **Location**: After agent registry creation
- **Note**: Only ONE instance due to ADK single-parent constraint
- **Add**:
  ```python
  # =====================================================================
  # DYNAMIC ROUTER AGENT
  # =====================================================================
  
  logger.info("🔧 [Orchestrator] Creating dynamic router agent...")
  
  # Single instance for GitHub pipeline (ADK single-parent constraint)
  self.dynamic_router = DynamicRouterAgent(
      agent_registry=self.analysis_agent_registry
  )
  
  logger.info("✅ [Orchestrator] Dynamic router agent created")
  ```

#### Task 3.4: ⏸️ DEFERRED - `_create_web_pipeline()`
- **Status**: DEFERRED (ADK single-parent constraint)
- **Reason**: Cannot create both pipelines simultaneously - agents can only have ONE parent
- **Priority**: GitHub pipeline takes priority for production use
- **Action**: NOT implementing in this phase
- **Future Work**: Implement agent cloning pattern to support both pipelines

#### Task 3.5: Update `_create_github_pipeline()`
- **File**: `agent_workspace/orchestrator_agent/agent.py`
- **Location**: Lines 262-283
- **Replace**:
  ```python
  # Comment: # ExecutionPipeline inserted here dynamically
  ```
  **With**:
  ```python
  self.dynamic_router_github,    # ← NEW: Dynamic agent execution
  ```
- **Full updated method**:
  ```python
  def _create_github_pipeline(self) -> SequentialAgent:
      """
      Create GitHub webhook processing pipeline.
      
      Pipeline Flow:
      1. GitHubFetcher → Fetch PR data from GitHub
      2. PlanningAgent → Decide which analysis agents to run
      3. DynamicRouterAgent → Read plan, dynamically execute selected agents
      4. ReportSynthesizer → Consolidate results
      5. GitHubPublisher → Post review comments to PR
      """
      return SequentialAgent(
          name="GitHubPipeline",
          sub_agents=[
              self.github_fetcher,
              self.planning_agent_github,
              self.dynamic_router_github,    # ← NEW: Dynamic agent execution
              self.report_synthesizer_github,
              self.github_publisher
          ],
          description="GitHub webhook processing pipeline with dynamic agent selection"
      )
  ```

#### Task 3.6: Update root agent creation - **GITHUB PIPELINE PRIORITY**
- **File**: `agent_workspace/orchestrator_agent/agent.py`
- **Location**: After router creation
- **Change**: Use GitHub pipeline as root (not Web pipeline)
- **Replace**:
  ```python
  self.root_agent = self._create_web_pipeline()
  ```
  **With**:
  ```python
  # GitHub Pipeline is the root for production integration
  self.root_agent = self._create_github_pipeline()
  logger.info("✅ [Orchestrator] Root agent: GitHubPipeline (production priority)")
  logger.info("⏸️  [Orchestrator] Web pipeline: Deferred (ADK single-parent constraint)")
  ```

#### Task 3.7: Update module exports
- **File**: `agent_workspace/orchestrator_agent/agent.py`
- **Location**: Bottom of file (module-level exports)
- **Update**:
  ```python
  # Export root_agent for ADK (now GitHubPipeline)
  root_agent = _orchestrator.get_agent()
  
  # Export orchestrator for programmatic access
  orchestrator = _orchestrator
  
  # Log pipeline status
  logger.info("✅ [Orchestrator] Root agent: GitHubPipeline")
  logger.info("⏸️  [Orchestrator] Web pipeline: Not available (single-parent constraint)")
  ```

---

### Phase 3.5: API Infrastructure (NEW - Required for Testing)

**Priority**: P0 (Must complete before Phase 4)

**Rationale**: All testing should be done via API calls, not direct Python imports. This ensures we test the production workflow exactly as it will be used.

#### Task 3.8: Create FastAPI server
- **File**: `api_server.py` (create new)
- **Purpose**: REST API server for GitHub webhook integration
- **Endpoints**:
  - `GET /health` - Health check
  - `POST /api/github/webhook` - GitHub PR webhook handler
  - `GET /api/status/{session_id}` - Check pipeline status
- **Features**:
  - Background task execution (async pipeline processing)
  - Session management integration
  - Artifact service integration
  - Proper error handling and logging
- **Technology**: FastAPI + Uvicorn
- **Dependencies**: Add to `requirements-api.txt`

#### Task 3.9: Create API test infrastructure
- **Files**:
  - `tests/api/test_github_webhook.py` - Main API test suite
  - `tests/api/run_api_tests.py` - Test runner script
  - `requirements-api.txt` - API dependencies
- **Purpose**: Test complete workflow via HTTP API calls
- **Mock Data**: GitHub PR webhook payload with realistic code changes

#### Task 3.10: Verify API server works
- **Method**: Manual verification
- **Steps**:
  1. Install API dependencies: `pip install -r requirements-api.txt`
  2. Start server: `python api_server.py`
  3. Check health: `curl http://localhost:8000/health`
  4. Verify orchestrator loads correctly
  5. Check logs for any errors
- **Expected Output**:
  ```json
  {
    "status": "healthy",
    "root_agent": "GitHubPipeline",
    "agents_available": 4
  }
  ```

---

### Phase 4: Testing via API (Verify everything works)

**Priority**: P1 (Must verify before production)

**Testing Philosophy**: All tests call API endpoints, not direct Python imports. This validates the production workflow.

#### Task 4.1: Unit tests for DynamicRouterAgent
- **File**: `tests/unit/test_dynamic_router.py` (create new)
- **Tests**:
  1. `test_router_executes_selected_agents()` - Only selected agents run
  2. `test_router_handles_empty_plan()` - Graceful skip if no plan
  3. `test_router_handles_unknown_agents()` - Logs warning for invalid names
  4. `test_router_full_parallel_mode()` - All agents run concurrently
  5. `test_router_controlled_parallel_mode()` - Batched execution (2 at a time)
  6. `test_router_sequential_mode()` - One agent at a time
  7. `test_router_large_code_threshold()` - Auto-switch to sequential

#### Task 4.2: ⏸️ DEFERRED - Integration test - Web pipeline
- **Status**: DEFERRED (Web pipeline not implemented)
- **Reason**: GitHub pipeline takes priority
- **Alternative**: Test GitHub pipeline with mock PR data

#### Task 4.3: ✅ API Integration Test - GitHub Pipeline
- **File**: `tests/api/test_github_webhook.py` ✅ CREATED
- **Method**: HTTP POST to `/api/github/webhook`
- **Test Flow**:
  1. Start API server
  2. POST mock GitHub webhook payload to `/api/github/webhook`
  3. Verify response: `{"status": "queued", "session_id": "..."}`
  4. Poll `/api/status/{session_id}` until completion
  5. Verify final status: `{"status": "completed", "report_ready": true}`
  6. Check artifacts in `storage_bucket/artifacts/`
- **Mock Payload**: Realistic PR with security issues (hardcoded secrets, SQL injection)
- **Expected Agents**: Security, Code Quality, Engineering, Carbon (sequential execution)
- **Validation**:
  - ✅ GitHubFetcher extracts PR data
  - ✅ PlanningAgent selects appropriate agents
  - ✅ DynamicRouterAgent executes agents sequentially
  - ✅ Each agent completes before next starts
  - ✅ Artifacts saved for each agent
  - ✅ ReportSynthesizer generates final report
  - ✅ GitHubPublisher formats review comment

#### Task 4.4: E2E test - Artifact persistence
- **File**: `tests/e2e/test_end_to_end_artifact_flow.py` (create new)
- **Test**:
  1. Run full GitHub pipeline with mock PR data and 2 agents selected
  2. Verify artifacts created in `storage_bucket/artifacts/.../sub_agent_outputs/`
  3. Verify analysis files exist: `analysis_*_security.json`, `analysis_*_quality.json`
  4. Verify report saved: `storage_bucket/artifacts/.../reports/report_*.md`
  5. Check file contents are valid JSON/Markdown

#### Task 4.5: E2E test - Sequential execution verification
- **File**: `tests/e2e/test_sequential_execution.py` (create new)
- **Test**:
  1. Mock PR with 4 agents selected
  2. Verify sequential execution order: security → quality → engineering → carbon
  3. Verify each agent completes before next starts (check timestamps in logs)
  4. Verify all artifacts saved correctly
  5. Verify execution logs show sequential execution mode

#### Task 4.6: ✅ Automated API Test Suite
- **File**: `tests/api/run_api_tests.py` ✅ CREATED
- **Method**: Automated test runner that manages API server lifecycle
- **Features**:
  1. Checks API dependencies installed
  2. Starts API server in background
  3. Waits for server to be healthy
  4. Runs complete test suite via HTTP calls
  5. Stops server after tests complete
- **Usage**:
  ```bash
  # Install API dependencies
  pip install -r requirements-api.txt
  
  # Run automated test suite
  python tests/api/run_api_tests.py
  ```
- **Test Scenarios**:
  1. Health check (GET /health)
  2. Submit webhook (POST /api/github/webhook)
  3. Poll status (GET /api/status/{session_id})
  4. Verify completion and artifacts
- **Expected Output**:
  - ✅ API server starts successfully
  - ✅ Webhook accepted and queued
  - ✅ Pipeline executes sequentially
  - ✅ All 4 agents complete
  - ✅ Artifacts saved
  - ✅ Report generated
  - ✅ Final status: completed

**Manual Testing** (alternative):
```bash
# Terminal 1: Start API server
python api_server.py

# Terminal 2: Run tests
python tests/api/test_github_webhook.py
```

**Production Testing** (with real GitHub):
- Use ngrok tunnel: `ngrok http 8000`
- Configure GitHub webhook URL: `https://xxx.ngrok.io/api/github/webhook`
- Open/update a PR and watch the pipeline execute

---

### Phase 5: Documentation Updates

**Priority**: P2 (Important for maintainability)

#### Task 5.1: Update orchestrator architecture diagram
- **File**: `agent_workspace/orchestrator_agent/agent.py`
- **Location**: Lines 1-35 (docstring)
- **Action**: Update diagram to remove SourceDetector and show DynamicRouter

#### Task 5.2: Update README.md
- **File**: `README.md`
- **Add**: Section explaining DynamicRouterAgent pattern
- **Update**: Architecture diagram to show new flow

#### Task 5.3: Create CHANGELOG.md entry
- **File**: `docs/CHANGELOG.md` (create if doesn't exist)
- **Entry**:
  ```markdown
  ## [Version X.X.X] - 2025-12-03
  
  ### Added
  - DynamicRouterAgent for intelligent agent selection
  - Resource management (controlled parallel, sequential for large code)
  - Adaptive execution based on code size
  
  ### Fixed
  - Analysis agents now execute correctly (was broken due to static SequentialAgent)
  - Artifacts are saved to disk as expected
  
  ### Removed
  - SourceDetectorAgent (obsolete)
### Week 2: Integration (December 7, 2025 - COMPLETED)
8. ✅ **Monday**: Task 3.1 - Add import for DynamicRouterAgent
9. ✅ **Monday**: Task 3.2 - Create agent registry
10. ✅ **Monday**: Task 3.3 - Create DynamicRouterAgent instance (single instance)
11. ⏸️ **DEFERRED**: Task 3.4 - _create_web_pipeline() (ADK single-parent constraint)
12. ✅ **Tuesday**: Task 3.5 - Update _create_github_pipeline()
13. ✅ **Tuesday**: Task 3.6 - Update root agent creation (GitHub pipeline as root)
14. ✅ **Tuesday**: Task 3.7 - Update module exports
15. ✅ **Tuesday**: Design Change - Sequential execution (accuracy over speed)
16. ✅ **Wednesday**: Task 3.8 - Create FastAPI server (`api_server.py`)
17. ✅ **Wednesday**: Task 3.9 - Create API test infrastructure
18. 🔄 **PENDING**: Task 3.10 - Verify API server worksicRouterAgent class
5. ✅ **Wednesday**: Task 2.3 - Create __init__.py exports
6. ✅ **Thursday**: Task 4.1 - Write unit tests for DynamicRouterAgent
7. ✅ **Friday**: Run unit tests, fix bugs

### Week 2: Integration (December 7, 2025 - COMPLETED)
8. ✅ **Monday**: Task 3.1 - Add import for DynamicRouterAgent
9. ✅ **Monday**: Task 3.2 - Create agent registry
10. ✅ **Monday**: Task 3.3 - Create DynamicRouterAgent instance (single instance)
11. ⏸️ **DEFERRED**: Task 3.4 - _create_web_pipeline() (ADK single-parent constraint)
12. ✅ **Tuesday**: Task 3.5 - Update _create_github_pipeline()
13. ✅ **Tuesday**: Task 3.6 - Update root agent creation (GitHub pipeline as root)
14. ✅ **Tuesday**: Task 3.7 - Update module exports
15. ✅ **Tuesday**: Design Change - Sequential execution (accuracy over speed)
16. ⏸️ **DEFERRED**: Task 4.2 - Web pipeline integration test (no Web pipeline)
17. 🔄 **PENDING**: Task 4.3 - Write GitHub pipeline integration test
18. 🔄 **PENDING**: Task 4.4 - Write E2E artifact test

### Week 3: API Testing & Documentation (CURRENT PHASE)
19. 🔄 **PENDING**: Task 4.1 - Install API dependencies (`pip install -r requirements-api.txt`)
20. 🔄 **PENDING**: Task 4.3 - Run API integration tests (`python tests/api/run_api_tests.py`)
21. 🔄 **PENDING**: Task 4.4 - Verify artifacts generated in storage_bucket
22. 🔄 **PENDING**: Task 4.5 - Verify sequential execution in logs
23. 🔄 **PENDING**: Task 5.1 - Update architecture diagrams
24. 🔄 **PENDING**: Task 5.2 - Update README.md with API usage
25. 🔄 **PENDING**: Task 5.3 - Create CHANGELOG entry
26. 🔄 **PENDING**: Final review & deployment preparation

---

## ✅ Success Criteria

### Functional Requirements
- [x] Planning agent selects agents (e.g., `["security", "code_quality"]`)
- [ ] DynamicRouter reads execution_plan from session state
- [ ] DynamicRouter creates ParallelAgent with ONLY selected agents
- [ ] Selected agents execute and save artifacts
- [ ] Artifacts saved to `storage_bucket/artifacts/.../sub_agent_outputs/`
- [ ] Report synthesizer loads artifacts successfully
- [ ] Final report saved to `storage_bucket/artifacts/.../reports/`
- [ ] Non-selected agents DO NOT execute
- [ ] General queries skip analysis phase entirely

### Sequential Execution (Accuracy Over Speed)
- [ ] All analysis agents execute sequentially (security → quality → engineering → carbon)
- [ ] Each agent completes fully before next starts
- [ ] Execution order verified in logs with timestamps
- [ ] No Gemini API timeout errors for large PRs
- [ ] GitHub pipeline processes mock PR successfully

### Code Quality
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All E2E tests pass
- [ ] No deprecated code remains in codebase
- [ ] Code follows ADK best practices
- [ ] Comprehensive logging at each phase

---

## 🚨 Risk Mitigation

### Risk 1: DynamicRouterAgent breaks existing flows
- **Mitigation**: Implement unit tests BEFORE integration
- **Rollback**: Keep git branch with old code, easy revert

### Risk 2: Performance degradation with sequential mode
- **Mitigation**: Make `max_concurrent_agents` configurable
- **Monitoring**: Add timing logs to each execution mode

### Risk 3: Artifacts not saved correctly
- **Mitigation**: E2E test MUST verify file creation before merging
- **Validation**: Check file existence AND content validity

### Risk 4: Gemini API rate limits when switching from Ollama
- **Mitigation**: Default to `max_concurrent_agents=2` (safe for Gemini)
- **Testing**: Test with actual Gemini API before production
- **Config**: Make it easy to adjust limits via environment variable

---

## 📊 Metrics & Monitoring

### Development Metrics
- **Code Removed**: ~200 lines (dead code elimination)
- **Code Added**: ~300 lines (DynamicRouterAgent + updates)
- **Net Change**: +100 lines
- **Test Coverage Target**: >80% for DynamicRouterAgent

### Runtime Metrics (to add)
- **Execution Mode Distribution**: Track parallel vs controlled_parallel vs sequential
- **Agent Selection Frequency**: Which agents are selected most often
- **Execution Duration**: Time per agent, per mode
- **Artifact Creation Rate**: Success/failure ratio
- **API Call Count**: Track LLM calls to estimate costs

---

## 🎯 Next Steps After Implementation

1. **Monitor Production**: Watch logs for execution mode distribution
2. **Tune Thresholds**: Adjust `large_code_threshold` based on real data
3. **Optimize Prompts**: Improve PlanningAgent selection accuracy
4. **Add Caching**: Cache analysis results for duplicate code
5. **Implement Retry Logic**: Add exponential backoff for API failures
6. **Add Webhooks**: Complete GitHub integration with API endpoint

---

**Ready to Implement**: All components identified, sequence planned, success criteria defined. Begin with Phase 1: Cleanup deprecated code.
