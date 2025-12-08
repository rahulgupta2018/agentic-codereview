# Simplified Sequential Agent Pipeline Design

**Status**: Design Review (December 8, 2025)  
**Date**: December 8, 2025 (Simplified Architecture)  
**Architecture Pattern**: Deterministic Sequential Pipeline  
**Priority**: GitHub Integration with ADK Built-in Artifacts

---

## 🎯 Design Philosophy

**Goal**: Create a simple, maintainable, deterministic pipeline for GitHub PR code reviews.

**Key Principles**:
1. ✅ **Sequential execution** - all analysis agents run in order, every time
2. ✅ **No dynamic routing** - remove complexity of planning + dynamic selection
3. ✅ **ADK built-in artifacts** - use ADK's artifact system for persistence
4. ✅ **Session-based organization** - artifacts organized by session/user/PR
5. ✅ **Separate analysis pipeline** - encapsulate analysis agents for maintainability

**Inspiration**: [ADK Sequential Workflows](https://raphaelmansuy.github.io/adk_training/docs/sequential_workflows)

---

## 🏗️ Simplified Architecture

### Core Pipeline (GitHub Integration)

```
GitHub Webhook/API Call
         ↓
    Orchestrator Agent
         ↓
┌────────────────────────────────────────┐
│  GitHub PR Review Pipeline             │
│  (SequentialAgent - Deterministic)     │
└────────────────────────────────────────┘
         ↓
    ┌─────────┐
    │ Step 1: │  GitHub Fetcher Agent
    │  Fetch  │  • Fetch PR data from GitHub API (or mock)
    └─────────┘  • Extract: files, diffs, metadata
         ↓        • Store in session state: github_pr_data
         │
    ┌─────────┐
    │ Step 2: │  Analysis Pipeline (SequentialAgent)
    │ Analyze │  • Encapsulated sub-pipeline for maintainability
    └─────────┘  • All 4 agents run sequentially every time:
         ↓          1. Security Agent
         │             ├─ scan_security_vulnerabilities()
         │             ├─ Generate JSON analysis
         │             └─ save_artifact() → session/PR/security_analysis.json
         ↓          2. Code Quality Agent
         │             ├─ analyze_complexity(), analyze_static_code()
         │             ├─ Generate JSON analysis
         │             └─ save_artifact() → session/PR/quality_analysis.json
         ↓          3. Engineering Practices Agent
         │             ├─ evaluate_engineering_practices()
         │             ├─ Generate JSON analysis
         │             └─ save_artifact() → session/PR/engineering_analysis.json
         ↓          4. Carbon Emission Agent
         │             ├─ analyze_carbon_footprint()
         │             ├─ Generate JSON analysis
         │             └─ save_artifact() → session/PR/carbon_analysis.json
         │
    ┌─────────┐
    │ Step 3: │  Report Synthesizer Agent
    │ Report  │  • Load all 4 JSON artifacts (ADK artifact system)
    └─────────┘  • Synthesize comprehensive markdown report
         ↓        • save_artifact() → session/PR/final_report.md
         │
    ┌─────────┐
    │ Step 4: │  GitHub Publisher Agent
    │ Publish │  • Load final_report.md from artifacts
    └─────────┘  • Post to GitHub PR as comment
         ↓        • Add inline code annotations
         │        • Update PR review status
         ↓
    ✅ Complete
```

### Key Simplifications

**REMOVED** (Complexity):
- ❌ Planning Agent (no need to "decide" which agents to run)
- ❌ Dynamic Router Agent (no dynamic selection logic)
- ❌ Classifier Agent (GitHub webhook knows it's a PR review)
- ❌ Execution plan in session state (not needed)
- ❌ Proxy selection tools (select_security_agent, etc.)

**KEPT** (Essential):
- ✅ GitHub Fetcher (get PR data)
- ✅ Analysis Pipeline (all 4 agents, always run)
- ✅ Report Synthesizer (consolidate results)
- ✅ GitHub Publisher (post to GitHub)

**BENEFITS**:
1. **Simpler** - fewer agents, fewer state keys, easier to debug
2. **Deterministic** - same agents run every time, predictable behavior
3. **Maintainable** - analysis pipeline is separate, can be updated independently
4. **Reliable** - no LLM-based "planning" decisions, just execute
5. **ADK-native** - uses ADK's built-in artifact system properly

### Architecture Diagrams

#### Flow 1: Web UI Pipeline (ADK Web Interface)

```
┌────────────────────────────────────────────────────────────┐
│  WebPipeline (SequentialAgent) - STATIC structure          │
│  Entry: adk web (http://localhost:8800)                    │
└────────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┬───────────────┐
        │                │                │               │
        ▼                ▼                ▼               ▼
   ┌─────────┐    ┌────────────┐   ┌──────────────┐  ┌────────┐
   │Classifier│───▶│Planning    │──▶│DynamicRouter │─▶│Report  │
   │         │    │Agent       │   │Agent         │  │Synth   │
   │         │    │(PlanReAct) │   │              │  │        │
   └─────────┘    └────────────┘   └──────────────┘  └────────┘
        │              │                   │               │
        ▼              ▼                   ▼               ▼
   output_key:    output_key:        READS:          Generates
   request_       execution_         execution_plan  final_report
   classification plan               
                  {                       │
                    selected_agents:      ▼
                    ["security",    ┌─────────────────────────┐
                     "quality"]     │ DynamicRouterAgent      │
                  }                 │ Logic:                  │
                                    │ 1. Read execution_plan  │
                                    │ 2. Filter registry      │
                                    │ 3. Create ParallelAgent │
                                    │ 4. Execute pipeline     │
                                    │ 5. Yield events         │
                                    └─────────────────────────┘
                                              │
                                              ▼
                                    ┌─────────────────────────┐
                                    │ Dynamically created:    │
                                    │ ParallelAgent(          │
                                    │   sub_agents=[          │
                                    │     security_agent,     │
                                    │     quality_agent       │
                                    │   ]                     │
                                    │ )                       │
                                    └─────────────────────────┘
                                              │
                        ┌─────────────────────┴─────────────────────┐
                        │                                           │
                        ▼                                           ▼
                 security_agent                              quality_agent
                        │                                           │
                        ├─ scan_security_vulnerabilities()          ├─ analyze_code_complexity()
                        ├─ save_analysis_result()                   ├─ analyze_static_code()
                        │  └─▶ analysis_..._security.json           ├─ save_analysis_result()
                        │                                           │  └─▶ analysis_..._quality.json
                        ▼                                           ▼
                 Session State:                              Session State:
                 security_analysis                           code_quality_analysis
```

#### Flow 2: GitHub API Pipeline (Webhook Integration)

```
┌────────────────────────────────────────────────────────────┐
│  GitHubPipeline (SequentialAgent) - STATIC structure       │
│  Entry: POST /api/github/webhook (GitHub PR events)        │
└────────────────────────────────────────────────────────────┘
                         │
    ┌────────────────────┼──────────────────┬────────────┬────────────┐
    │                    │                  │            │            │
    ▼                    ▼                  ▼            ▼            ▼
┌─────────┐      ┌────────────┐    ┌──────────────┐  ┌────────┐  ┌──────────┐
│GitHub   │─────▶│Planning    │───▶│DynamicRouter │─▶│Report  │─▶│GitHub    │
│Fetcher  │      │Agent       │    │Agent         │  │Synth   │  │Publisher │
│         │      │(PlanReAct) │    │              │  │        │  │          │
└─────────┘      └────────────┘    └──────────────┘  └────────┘  └──────────┘
    │                  │                   │              │            │
    ▼                  ▼                   ▼              ▼            ▼
Fetches PR:      output_key:         READS:        Generates    Posts to GitHub:
- files          execution_          execution_    final_report - PR comments
- diffs          plan                plan                       - file annotations
- metadata                                                      - inline comments
    │
    ▼
Stores in session:
github_pr_data {
  pr_number: 123,
  files_changed: [...],
  diff: "...",
  author: "...",
  branch: "..."
}
                                            │
                                            ▼
                              ┌─────────────────────────┐
                              │ DynamicRouterAgent      │
                              │ (SequentialAgent)       │
                              │ Accuracy over speed     │
                              └─────────────────────────┘
                                            │
                                            ▼
                              ┌─────────────────────────┐
                              │ Sequential Execution:   │
                              │ 1. security_agent       │
                              │    (completes fully)    │
                              │ 2. code_quality_agent   │
                              │    (completes fully)    │
                              │ 3. engineering_agent    │
                              │    (completes fully)    │
                              │ 4. carbon_agent         │
                              │    (completes fully)    │
                              └─────────────────────────┘
                                            │
                                            ▼
                                     Each agent:
                              - Runs analysis tools
                              - Saves artifacts
                              - Writes to session state
                              - Then next agent starts
```

### Dual Flow Comparison

| Aspect | Web UI Pipeline | GitHub API Pipeline |
|--------|----------------|---------------------|
| **Entry Point** | `adk web` UI at http://localhost:8800 | `POST /api/github/webhook` |
| **Trigger** | Manual user input in web UI | GitHub webhook on PR events |
| **Input Source** | User text message with code | GitHub webhook payload (JSON) |
| **Pre-processing Agent** | **Classifier** (determines intent) | **GitHubFetcher** (fetches PR data) |
| **Code Location** | Inline in user message | Extracted from GitHub API + stored in session |
| **Session State Key** | `request_classification` | `github_pr_data` |
| **Planning Input** | Classification + user message | PR metadata + changed files |
| **DynamicRouter Input** | `execution_plan` (standard format) | `execution_plan` (same standard format) |
| **Agent Registry** | ✅ Same registry, same agents | ✅ Same registry, same agents |
| **Analysis Execution** | ✅ Same DynamicRouterAgent | ✅ Same DynamicRouterAgent |
| **Artifacts Saved** | ✅ Same location (storage_bucket) | ✅ Same location (storage_bucket) |
| **Report Format** | Markdown displayed in UI | Markdown + GitHub annotations |
| **Output Delivery** | Web UI display (final_report) | **GitHubPublisher** posts to PR |
| **Post-processing Agent** | None (report shown in UI) | **GitHubPublisher** (posts comments) |

### Key Design Insight: Reusable Router

The **DynamicRouterAgent is flow-agnostic**:
- Reads `execution_plan` from session state (same format for both flows)
- Uses agent registry (same for both flows)
- Executes selected agents dynamically (same mechanism)
- Saves artifacts to same location (storage_bucket)

**Only the endpoints differ**:
- **Web**: Classifier → Planning → Router → Report → UI
- **GitHub**: Fetcher → Planning → Router → Report → Publisher → GitHub PR

---

## 🏗️ Implementation Structure

### File Organization

```
agent_workspace/orchestrator_agent/
├── agent.py                          # Main orchestrator (only root agent file)
└── sub_agents/
    ├── classifier_agent/             # Web flow only
    ├── planning_agent/               # SHARED by both flows
    ├── dynamic_router_agent/         # NEW: Router agent (SHARED) ← Sub-agent!
    │   ├── __init__.py
    │   └── agent.py                  # DynamicRouterAgent implementation
    ├── github_fetcher_agent/         # GitHub flow only
    ├── github_publisher_agent/       # GitHub flow only
    ├── security_agent/               # SHARED (via router)
    ├── code_quality_agent/           # SHARED (via router)
    ├── engineering_practices_agent/  # SHARED (via router)
    ├── carbon_emission_agent/        # SHARED (via router)
    └── report_synthesizer_agent/     # SHARED by both flows

API Routes (for GitHub webhook):
api/
├── github/
│   └── webhook.py                    # POST /api/github/webhook
└── main.py                           # FastAPI app with routes
```

### Component Responsibilities

#### 1. **Classifier Agent** (Web flow only)
- **Input**: User message
- **Output**: `request_classification` in session state
- **Decision**: Is this a general query or code review?
- **Used by**: WebPipeline only

#### 2. **GitHub Fetcher Agent** (GitHub flow only)
- **Input**: GitHub webhook payload (PR number, repo)
- **Actions**:
  - Fetch PR details from GitHub API
  - Extract changed files and diffs
  - Store PR metadata
- **Output**: `github_pr_data` in session state
- **Format**:
  ```json
  {
    "pr_number": 123,
    "repository": "owner/repo",
    "files_changed": ["src/auth.py", "tests/test_auth.py"],
    "diff": "...",
    "author": "developer123",
    "branch": "feature/authentication"
  }
  ```
- **Used by**: GitHubPipeline only

#### 3. **Planning Agent** (SHARED)
- **Input**: 
  - **Web flow**: `request_classification` from session state
  - **GitHub flow**: `github_pr_data` from session state
- **Tools**: Proxy selection tools (select_security_agent, etc.)
- **Output**: `execution_plan` in session state (same format for both flows)
- **Format**:
  ```json
  {
    "selected_agents": ["security", "code_quality"],
    "execution_mode": "parallel",
    "reasoning": "User requested security + quality review"
  }
  ```
- **Used by**: Both WebPipeline and GitHubPipeline

#### 4. **Dynamic Router Agent** (SHARED - NEW)
- **Input**: `execution_plan` from session state
- **Registry**: Maps agent names → agent instances
  ```python
  {
    "security": security_agent,
    "code_quality": code_quality_agent,
    "engineering": engineering_agent,
    "carbon": carbon_agent
  }
  ```
- **Process**:
  1. Read `selected_agents` from execution_plan
  2. Filter agent_registry by selected names
  3. Create ParallelAgent/SequentialAgent with filtered agents
  4. Execute the dynamic pipeline
  5. Stream events through
- **Output**: None directly (analysis agents write to session state)
- **Used by**: Both WebPipeline and GitHubPipeline

#### 5. **Analysis Agents** (SHARED)
- **Agents**: security_agent, code_quality_agent, engineering_agent, carbon_agent
- **Execute**: Domain-specific analysis
- **Actions**:
  - Call analysis tools (scan_security_vulnerabilities, analyze_code_complexity, etc.)
  - Call `save_analysis_result()` to save artifacts
  - Write output to session state with their output_key
- **Artifacts**: Saved to `storage_bucket/artifacts/.../sub_agent_outputs/`
- **Used by**: Both flows (invoked by DynamicRouterAgent)

#### 6. **Report Synthesizer** (SHARED)
- **Input**: Analysis results from session state
- **Tool**: `load_analysis_results_from_artifacts()`
- **Output**: `final_report` markdown
- **Actions**:
  - Load artifacts from disk
  - Synthesize comprehensive report
  - Call `save_final_report()` to save artifact
- **Artifacts**: Saved to `storage_bucket/artifacts/.../reports/`
- **Used by**: Both WebPipeline and GitHubPipeline

#### 7. **GitHub Publisher Agent** (GitHub flow only)
- **Input**: `final_report` from session state
- **Actions**:
  - Parse markdown report
  - Create GitHub PR review comments
  - Post inline comments on specific lines
  - Post summary comment on PR
- **Output**: Posted to GitHub PR via GitHub API
- **Used by**: GitHubPipeline only

---

## 📝 Code Implementation

### DynamicRouterAgent Class

```python
# FILE: agent_workspace/orchestrator_agent/sub_agents/dynamic_router_agent/agent.py

from google.adk.agents import BaseAgent, ParallelAgent, SequentialAgent
from google.adk.core import InvocationContext, Event
from typing import AsyncGenerator, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class DynamicRouterAgent(BaseAgent):
    """
    Router agent that dynamically selects and executes analysis agents.
    
    This agent sits in a SequentialAgent pipeline and acts as a "smart router":
    - Reads execution_plan from session state (set by planning agent)
    - Filters agent registry by selected_agents
    - Creates dynamic ParallelAgent or SequentialAgent
    - Executes the dynamic pipeline with resource management
    - Yields all events transparently
    
    Design Pattern:
    - Static structure (SequentialAgent)
    - Dynamic execution (runtime agent selection)
    - Leverages ADK primitives (ParallelAgent/SequentialAgent)
    - Resource-aware execution (prevents API overload)
    
    Resource Management:
    - Limits concurrent agent execution (default: 2 agents at a time)
    - Adapts to code size (sequential for large code, parallel for small)
    - Prevents Gemini API timeout/quota errors
    
    Example Usage:
        agent_registry = {
            "security": security_agent,
            "code_quality": quality_agent,
            "engineering": engineering_agent,
            "carbon": carbon_agent
        }
        
        router = DynamicRouterAgent(
            agent_registry=agent_registry,
            max_concurrent_agents=2  # Limit for Gemini API
        )
        
        pipeline = SequentialAgent(sub_agents=[
            classifier,
            planning_agent,
            router,  # ← Reads plan and executes selected agents
            report_synthesizer
        ])
    """
    
    def __init__(
        self,
        agent_registry: Dict[str, BaseAgent],
        max_concurrent_agents: int = 2,
        large_code_threshold: int = 50000,
        **kwargs
    ):
        """
        Initialize router with agent registry and resource limits.
        
        Args:
            agent_registry: Mapping of agent names to agent instances.
                Keys should match the names used by planning agent in
                execution_plan.selected_agents.
                
                Example:
                {
                    "security": security_agent_instance,
                    "code_quality": code_quality_agent_instance,
                    "engineering": engineering_practices_agent_instance,
                    "carbon": carbon_emission_agent_instance
                }
            
            max_concurrent_agents: Maximum number of agents to run concurrently.
                Default: 2 (safe for Gemini API with large code)
                Set to 4+ for local Ollama with no rate limits
                Set to 1 for pure sequential execution
            
            large_code_threshold: Character count threshold to switch to sequential mode.
                Default: 50000 chars (~30K tokens for Gemini)
                If code exceeds this, router uses sequential mode to prevent timeouts
        """
        super().__init__(
            name="DynamicRouterAgent",
            description="Routes execution to dynamically selected analysis agents with resource management",
            **kwargs
        )
        self.agent_registry = agent_registry
        self.max_concurrent_agents = max_concurrent_agents
        self.large_code_threshold = large_code_threshold
        
        logger.info(f"🔧 [DynamicRouter] Initialized with {len(agent_registry)} agents in registry")
        logger.info(f"🔧 [DynamicRouter] Available agents: {list(agent_registry.keys())}")
        logger.info(f"🔧 [DynamicRouter] Resource limits: max_concurrent={max_concurrent_agents}, large_code_threshold={large_code_threshold}")
    
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        Core routing logic executed when agent runs in pipeline.
        
        Flow:
        1. Read execution_plan from session state
        2. Extract selected_agents list
        3. Filter agent_registry to get agent instances
        4. Create dynamic ParallelAgent or SequentialAgent
        5. Execute dynamic pipeline
        6. Yield all events
        
        Args:
            ctx: ADK invocation context with session state
            
        Yields:
            Event: All events from dynamically executed agents
        """
        # ===== PHASE 1: Read Execution Plan =====
        logger.info("📖 [DynamicRouter] Phase 1: Reading execution plan from session state...")
        
        execution_plan = ctx.session.state.get("execution_plan", {})
        
        if not execution_plan:
            logger.warning("⚠️  [DynamicRouter] No execution_plan found in session state")
            logger.info("💡 [DynamicRouter] This might be a general query - skipping analysis")
            return
        
        selected_agents = execution_plan.get("selected_agents", [])
        execution_mode = execution_plan.get("execution_mode", "parallel")
        
        logger.info(f"📋 [DynamicRouter] Execution plan loaded:")
        logger.info(f"   - Selected agents: {selected_agents}")
        logger.info(f"   - Execution mode (requested): {execution_mode}")
        
        if not selected_agents:
            logger.warning("⚠️  [DynamicRouter] No agents selected in execution_plan")
            logger.info("💡 [DynamicRouter] Skipping analysis phase")
            return
        
        # ===== PHASE 1.5: Resource-Aware Execution Mode Selection =====
        logger.info("🧠 [DynamicRouter] Phase 1.5: Determining optimal execution mode...")
        
        # Check code size to prevent API overload
        user_code = ctx.session.state.get("user_code", "")
        code_size = len(user_code)
        num_agents = len(selected_agents)
        
        # Override execution mode if code is too large
        if code_size > self.large_code_threshold:
            logger.warning(f"⚠️  [DynamicRouter] Large code detected: {code_size} chars (threshold: {self.large_code_threshold})")
            logger.info(f"💡 [DynamicRouter] Overriding to sequential mode to prevent API timeout")
            execution_mode = "sequential"
        elif execution_mode == "parallel" and num_agents > self.max_concurrent_agents:
            logger.info(f"💡 [DynamicRouter] Too many agents ({num_agents}) for full parallel execution")
            logger.info(f"💡 [DynamicRouter] Using controlled parallel mode (max {self.max_concurrent_agents} concurrent)")
            execution_mode = "controlled_parallel"
        
        logger.info(f"✅ [DynamicRouter] Final execution mode: {execution_mode}")
        logger.info(f"📊 [DynamicRouter] Code size: {code_size} chars, Agents: {num_agents}")
        
        # ===== PHASE 2: Filter Agent Registry =====
        logger.info("🔍 [DynamicRouter] Phase 2: Filtering agent registry...")
        
        agents_to_run = []
        missing_agents = []
        
        for agent_name in selected_agents:
            if agent_name in self.agent_registry:
                agent = self.agent_registry[agent_name]
                agents_to_run.append(agent)
                logger.info(f"  ✓ [DynamicRouter] Added {agent_name} to execution pipeline")
            else:
                missing_agents.append(agent_name)
                logger.warning(f"  ⚠️  [DynamicRouter] Unknown agent: {agent_name} (not in registry)")
        
        if missing_agents:
            logger.warning(f"⚠️  [DynamicRouter] Missing agents: {missing_agents}")
            logger.info(f"💡 [DynamicRouter] Available agents: {list(self.agent_registry.keys())}")
        
        if not agents_to_run:
            logger.error("❌ [DynamicRouter] No valid agents to run after filtering!")
            logger.error("❌ [DynamicRouter] Selected: {selected_agents}, Registry: {list(self.agent_registry.keys())}")
            return
        
        logger.info(f"✅ [DynamicRouter] Filtered to {len(agents_to_run)} valid agents")
        
        # ===== PHASE 3: Create Dynamic Execution Pipeline =====
        logger.info(f"🔧 [DynamicRouter] Phase 3: Creating dynamic {execution_mode} pipeline...")
        
        if execution_mode == "parallel":
            # Full parallel execution (small code, few agents)
            execution_pipeline = ParallelAgent(
                name="DynamicParallelExecution",
                sub_agents=agents_to_run,
                description=f"Parallel execution of {len(agents_to_run)} selected analysis agents"
            )
            logger.info(f"✅ [DynamicRouter] Created ParallelAgent (all {len(agents_to_run)} agents concurrent):")
            for i, agent in enumerate(agents_to_run, 1):
                logger.info(f"   {i}. {agent.name}")
        
        elif execution_mode == "controlled_parallel":
            # Controlled parallel execution (batches of max_concurrent_agents)
            # Implementation: Use ADK's SequentialAgent with ParallelAgent batches
            batches = [
                agents_to_run[i:i + self.max_concurrent_agents]
                for i in range(0, len(agents_to_run), self.max_concurrent_agents)
            ]
            
            batch_agents = []
            for batch_idx, batch in enumerate(batches, 1):
                batch_agent = ParallelAgent(
                    name=f"Batch{batch_idx}",
                    sub_agents=batch,
                    description=f"Parallel batch {batch_idx} with {len(batch)} agents"
                )
                batch_agents.append(batch_agent)
            
            execution_pipeline = SequentialAgent(
                name="ControlledParallelExecution",
                sub_agents=batch_agents,
                description=f"Batched execution: {len(batches)} batches of max {self.max_concurrent_agents} agents"
            )
            
            logger.info(f"✅ [DynamicRouter] Created Controlled Parallel Pipeline:")
            logger.info(f"   - Total agents: {len(agents_to_run)}")
            logger.info(f"   - Batches: {len(batches)}")
            logger.info(f"   - Max concurrent per batch: {self.max_concurrent_agents}")
            for batch_idx, batch in enumerate(batches, 1):
                logger.info(f"   Batch {batch_idx}: {[a.name for a in batch]}")
        
        else:
            # Pure sequential execution (large code or explicit request)
            execution_pipeline = SequentialAgent(
                name="DynamicSequentialExecution",
                sub_agents=agents_to_run,
                description=f"Sequential execution of {len(agents_to_run)} selected analysis agents"
            )
            logger.info(f"✅ [DynamicRouter] Created SequentialAgent (one at a time):")
            for i, agent in enumerate(agents_to_run, 1):
                logger.info(f"   {i}. {agent.name}")
        
        # ===== PHASE 4: Execute Dynamic Pipeline =====
        logger.info("⚡ [DynamicRouter] Phase 4: Executing dynamic pipeline...")
        logger.info(f"🚀 [DynamicRouter] Starting execution of {len(agents_to_run)} agents...")
        
        agent_count = 0
        async for event in execution_pipeline.run_async(ctx):
            # Stream events transparently through the router
            yield event
            
            # Log progress (only log agent completion events to avoid spam)
            if hasattr(event, 'author') and event.author in [a.name for a in agents_to_run]:
                agent_count += 1
                logger.info(f"✓ [DynamicRouter] Agent {agent_count}/{len(agents_to_run)} completed: {event.author}")
        
        logger.info(f"✅ [DynamicRouter] Dynamic pipeline execution complete!")
        logger.info(f"📊 [DynamicRouter] All {len(agents_to_run)} agents finished successfully")
```

### Orchestrator Integration

```python
# FILE: agent_workspace/orchestrator_agent/agent.py (updates)

from .sub_agents.dynamic_router_agent.agent import DynamicRouterAgent

class CodeReviewOrchestrator:
    """
    Main orchestrator for code review system.
    
    Uses DynamicRouterAgent pattern:
    - Static SequentialAgent structure
    - Dynamic agent selection at runtime
    - Planning agent selects which agents to run
    - Router agent executes only selected agents
    """
    
    def __init__(self):
        """Initialize orchestrator with all sub-agents and workflows."""
        
        logger.info("🚀 [Orchestrator] Initializing Deterministic Workflow Orchestrator")
        
        # ... existing agent initialization (classifier, planning, analysis agents) ...
        
        # =====================================================================
        # NEW: AGENT REGISTRY FOR DYNAMIC ROUTING
        # =====================================================================
        
        logger.info("🔧 [Orchestrator] Creating agent registry for dynamic routing...")
        
        self.analysis_agent_registry = {
            "security": self.security_agent,
            "code_quality": self.code_quality_agent,
            "engineering": self.engineering_agent,
            "carbon": self.carbon_agent,
        }
        
        logger.info(f"✅ [Orchestrator] Agent registry created with {len(self.analysis_agent_registry)} agents")
        
        # =====================================================================
        # NEW: DYNAMIC ROUTER AGENT
        # =====================================================================
        
        logger.info("🔧 [Orchestrator] Creating dynamic router agents...")
        
        # Create separate router instances for each pipeline to avoid parent conflicts
        # Configure resource limits based on LLM backend
        # - For Ollama (local): max_concurrent_agents=4 (no API limits)
        # - For Gemini (cloud): max_concurrent_agents=2 (prevent rate limits/timeouts)
        # - For large PRs: large_code_threshold=50000 (auto-switch to sequential)
        
        self.dynamic_router_web = DynamicRouterAgent(
            agent_registry=self.analysis_agent_registry,
            max_concurrent_agents=2,      # Safe default for Gemini
            large_code_threshold=50000    # ~30K tokens
        )
        
        self.dynamic_router_github = DynamicRouterAgent(
            agent_registry=self.analysis_agent_registry,
            max_concurrent_agents=2,      # Safe default for Gemini
            large_code_threshold=50000    # ~30K tokens
        )
        
        logger.info("✅ [Orchestrator] Dynamic router agents created")
        
        # ... rest of initialization ...
    
    def _create_web_pipeline(self) -> SequentialAgent:
        """
        Create Web UI request processing pipeline.
        
        Pipeline Flow:
        1. Classifier → Classify user intent and code presence
        2. PlanningAgent → Decide which analysis agents to run
        3. DynamicRouterAgent → Read plan, dynamically execute selected agents
        4. ReportSynthesizer → Consolidate results into markdown report
        
        The key innovation is DynamicRouterAgent which:
        - Reads execution_plan from session state
        - Filters agent_registry by selected_agents
        - Creates ParallelAgent with only selected agents
        - Executes the dynamic pipeline
        - Streams events transparently
        
        This allows static SequentialAgent structure with dynamic execution.
        """
        return SequentialAgent(
            name="WebPipeline",
            sub_agents=[
                self.classifier,
                self.planning_agent_web,
                self.dynamic_router_web,      # ← NEW: Reads plan and executes selected agents
                self.report_synthesizer_web
            ],
            description="Web UI pipeline with dynamic agent selection via router"
        )
    
    def _create_github_pipeline(self) -> SequentialAgent:
        """
        Create GitHub webhook processing pipeline.
        
        Pipeline Flow:
        1. GitHubFetcher → Fetch PR data from GitHub
        2. PlanningAgent → Decide which analysis agents to run
        3. DynamicRouterAgent → Read plan, dynamically execute selected agents
        4. ReportSynthesizer → Consolidate results
        5. GitHubPublisher → Post review comments to PR
        
        Key Differences from WebPipeline:
        - Uses GitHubFetcher instead of Classifier (different input source)
        - Uses GitHubPublisher at the end (posts to GitHub PR)
        - Everything else is SHARED (planning, router, analysis, report synthesis)
        """
        return SequentialAgent(
            name="GitHubPipeline",
            sub_agents=[
                self.github_fetcher,
                self.planning_agent_github,
                self.dynamic_router_github,    # ← NEW: Reads plan and executes selected agents
                self.report_synthesizer_github,
                self.github_publisher
            ],
            description="GitHub pipeline with dynamic agent selection via router"
        )
    
    def get_github_pipeline_agent(self) -> SequentialAgent:
        """
        Expose GitHub pipeline for API route usage.
        
        This is called by: POST /api/github/webhook
        
        Usage in FastAPI:
        ```python
        from agent_workspace.orchestrator_agent.agent import orchestrator
        
        @app.post("/api/github/webhook")
        async def github_webhook(payload: dict):
            github_pipeline = orchestrator.get_github_pipeline_agent()
            
            # Create context with webhook payload
            ctx = create_context_from_webhook(payload)
            
            # Execute pipeline
            async for event in github_pipeline.run_async(ctx):
                # Process events
                pass
            
            return {"status": "success"}
        ```
        """
        return self._create_github_pipeline()
```

---

## ⚡ Resource Management & API Protection

### Problem: API Overload with Parallel Execution

When using cloud LLMs (Gemini, OpenAI, etc.), naive parallel execution can cause:
- ❌ **Rate limit errors** (429 Too Many Requests)
- ❌ **Timeout errors** (Large code × multiple agents = massive token usage)
- ❌ **Quota exhaustion** (Burning through API credits quickly)
- ❌ **Degraded performance** (API throttling under load)

### Solution: Adaptive Execution Strategy

The DynamicRouterAgent implements **3-tier execution modes**:

#### 1. **Full Parallel** (Fast, for small code)
- **When**: Code < 50K chars AND ≤2 agents selected
- **Behavior**: All agents run simultaneously
- **Example**: User submits 100 lines of code, requests security + quality review
- **Result**: 2 agents run in parallel, complete in ~30 seconds

#### 2. **Controlled Parallel** (Balanced, for medium code)
- **When**: Code < 50K chars AND >2 agents selected
- **Behavior**: Agents run in batches of `max_concurrent_agents` (default: 2)
- **Example**: User submits 500 lines, requests all 4 agents (security, quality, engineering, carbon)
- **Execution**:
  ```
  Batch 1 (parallel): security_agent + quality_agent
  ↓ Wait for completion
  Batch 2 (parallel): engineering_agent + carbon_agent
  ```
- **Result**: 2 agents at a time, complete in ~60 seconds (vs 30s full parallel, 120s sequential)

#### 3. **Sequential** (Safe, for large code)
- **When**: Code > 50K chars (auto-detected) OR explicitly requested
- **Behavior**: Agents run one at a time
- **Example**: User submits entire module (2000 lines), requests all agents
- **Result**: Prevents Gemini timeout, takes longer but reliable

### Configuration

```python
# For Ollama (local, no limits)
router = DynamicRouterAgent(
    agent_registry=registry,
    max_concurrent_agents=4,        # Run all 4 agents in parallel
    large_code_threshold=100000     # Higher threshold (100K chars)
)

# For Gemini (cloud, with rate limits)
router = DynamicRouterAgent(
    agent_registry=registry,
    max_concurrent_agents=2,        # Max 2 concurrent LLM calls
    large_code_threshold=50000      # Lower threshold (50K chars)
)

# For strict resource constraints
router = DynamicRouterAgent(
    agent_registry=registry,
    max_concurrent_agents=1,        # Pure sequential
    large_code_threshold=10000      # Very low threshold
)
```

### Decision Matrix

| Code Size | Agents Selected | Execution Mode | Concurrency | Duration (est.) |
|-----------|----------------|----------------|-------------|-----------------|
| < 50K chars | 1-2 agents | **Full Parallel** | All agents | ~30s |
| < 50K chars | 3-4 agents | **Controlled Parallel** | 2 at a time | ~60s |
| > 50K chars | Any | **Sequential** | 1 at a time | ~120s |

### Benefits

✅ **Prevents API overload** - Limits concurrent LLM calls
✅ **Adapts to code size** - Auto-detects large code and switches to sequential
✅ **Configurable** - Tune limits based on LLM backend (Ollama vs Gemini)
✅ **Still faster than pure sequential** - Controlled parallel runs 2 agents at a time
✅ **Graceful degradation** - No hard failures, just slower execution for large code

### Future Enhancements

1. **Dynamic throttling** - Monitor API response times and adjust concurrency on the fly
2. **Token estimation** - Calculate exact token count before execution (more accurate than char count)
3. **Retry with backoff** - Automatic retry for transient API errors (429, 503)
4. **Code chunking** - Split massive PRs into chunks for analysis
5. **Result caching** - Cache analysis results to avoid re-running agents for duplicate code

---

## 🔄 Data Flow

### Session State Flow

```python
# 1. Classifier Agent runs
ctx.session.state["request_classification"] = {
    "type": "code_review_security",
    "has_code": True,
    "focus_areas": ["security"],
    "confidence": "high"
}

# 2. Planning Agent runs (reads request_classification)
#    Calls select_security_agent() tool
ctx.session.state["execution_plan"] = {
    "selected_agents": ["security"],
    "execution_mode": "parallel",
    "reasoning": "User explicitly requested security analysis"
}

# 3. DynamicRouterAgent runs (reads execution_plan)
#    - Filters agent_registry: gets [security_agent]
#    - Creates ParallelAgent with [security_agent]
#    - Executes it

# 4. Security Agent runs
#    - Calls scan_security_vulnerabilities(code)
#    - Calls save_analysis_result(analysis_data, "security_agent")
#    - Saves to: storage_bucket/artifacts/.../analysis_..._security.json
ctx.session.state["security_analysis"] = {
    "agent": "SecurityAnalysisAgent",
    "vulnerabilities": [...]
}

# 5. Report Synthesizer runs (reads security_analysis)
#    - Calls load_analysis_results_from_artifacts()
#    - Loads analysis_..._security.json
#    - Generates markdown report
#    - Calls save_final_report(report)
#    - Saves to: storage_bucket/artifacts/.../report_*.md
ctx.session.state["final_report"] = "# Security Analysis\n..."
```

---

## ✅ Benefits

### 1. **Minimal Code Changes**
- Only add one new agent: `DynamicRouterAgent`
- Update orchestrator `__init__` to create registry + router
- Update pipeline creation to include router in sub_agents
- No changes to existing agents

### 2. **ADK Native Patterns**
- Uses `SequentialAgent` for static structure
- Uses `ParallelAgent`/`SequentialAgent` for dynamic execution
- Leverages session state for agent communication
- No custom scheduling or event manipulation

### 3. **Clean Separation of Concerns**
- **Classifier**: Intent classification
- **Planning Agent**: Agent selection strategy
- **Router**: Execution orchestration
- **Analysis Agents**: Domain analysis
- **Report Synthesizer**: Result consolidation

### 4. **Debuggability**
- Clear handoff points between agents
- Extensive logging at each phase
- Session state inspection shows complete flow
- ADK tracing shows agent execution tree

### 5. **Extensibility**
- Add new analysis agents: Just add to registry
- Change execution logic: Only modify router
- Support new execution modes: Update router's pipeline creation
- Reuse router: Same class for Web + GitHub pipelines

### 6. **Performance**
- Only selected agents execute (saves LLM calls)
- Parallel execution when agents are independent
- Sequential execution when needed (rare)
- No overhead from skipped agents

---

## 🧪 Testing Strategy

### Unit Tests

```python
# tests/unit/test_dynamic_router.py

import pytest
from unittest.mock import Mock, AsyncMock
from agent_workspace.orchestrator_agent.sub_agents.dynamic_router_agent.agent import DynamicRouterAgent

@pytest.mark.asyncio
async def test_router_executes_selected_agents():
    """Test router only executes agents in execution_plan."""
    
    # Mock agents
    security_agent = Mock(name="security_agent")
    security_agent.run_async = AsyncMock(return_value=[])
    
    quality_agent = Mock(name="code_quality_agent")
    quality_agent.run_async = AsyncMock(return_value=[])
    
    engineering_agent = Mock(name="engineering_agent")
    engineering_agent.run_async = AsyncMock(return_value=[])
    
    # Create registry with all agents
    registry = {
        "security": security_agent,
        "code_quality": quality_agent,
        "engineering": engineering_agent
    }
    
    # Create router
    router = DynamicRouterAgent(agent_registry=registry)
    
    # Mock context with execution plan selecting only security + quality
    ctx = Mock()
    ctx.session.state = {
        "execution_plan": {
            "selected_agents": ["security", "code_quality"],
            "execution_mode": "parallel"
        }
    }
    
    # Execute router
    async for event in router.run_async(ctx):
        pass
    
    # Assertions
    assert security_agent.run_async.called
    assert quality_agent.run_async.called
    assert not engineering_agent.run_async.called  # ← Should NOT be called


@pytest.mark.asyncio
async def test_router_handles_empty_plan():
    """Test router gracefully handles empty execution plan."""
    
    router = DynamicRouterAgent(agent_registry={})
    
    ctx = Mock()
    ctx.session.state = {}  # No execution_plan
    
    # Should return early without error
    events = [e async for e in router.run_async(ctx)]
    assert len(events) == 0


@pytest.mark.asyncio
async def test_router_handles_unknown_agents():
    """Test router logs warning for unknown agent names."""
    
    security_agent = Mock(name="security_agent")
    security_agent.run_async = AsyncMock(return_value=[])
    
    registry = {"security": security_agent}
    router = DynamicRouterAgent(agent_registry=registry)
    
    ctx = Mock()
    ctx.session.state = {
        "execution_plan": {
            "selected_agents": ["security", "unknown_agent"],
            "execution_mode": "parallel"
        }
    }
    
    # Should execute security agent, log warning for unknown_agent
    async for event in router.run_async(ctx):
        pass
    
    assert security_agent.run_async.called
```

### Integration Tests

```python
# tests/integration/test_web_pipeline.py

@pytest.mark.asyncio
async def test_full_web_pipeline_with_dynamic_routing():
    """Test complete WebPipeline with dynamic router."""
    
    # Create orchestrator
    orchestrator = CodeReviewOrchestrator()
    web_pipeline = orchestrator._create_web_pipeline()
    
    # Mock context with code review request
    ctx = Mock()
    ctx.session.state = {}
    ctx.session.events = []
    
    # Create user message with code
    message = """
    Review this Python code for security issues:
    
    def get_user(user_id):
        query = f"SELECT * FROM users WHERE id = {user_id}"
        return db.execute(query)
    """
    
    # Execute pipeline
    events = [e async for e in web_pipeline.run_async(ctx)]
    
    # Assertions
    assert "request_classification" in ctx.session.state
    assert "execution_plan" in ctx.session.state
    assert "security" in ctx.session.state["execution_plan"]["selected_agents"]
    assert "security_analysis" in ctx.session.state
    assert "final_report" in ctx.session.state
```

### E2E Tests

```python
# tests/e2e/test_artifact_persistence.py

@pytest.mark.asyncio
async def test_artifacts_saved_via_dynamic_routing(tmp_path):
    """Test that artifacts are saved when agents execute via router."""
    
    # Setup artifact service with temp directory
    artifact_service = FileArtifactService(base_dir=str(tmp_path / "artifacts"))
    
    # Create orchestrator and run analysis
    # ... execute full pipeline ...
    
    # Verify artifacts created
    artifacts_dir = tmp_path / "artifacts" / "orchestrator_agent" / "user" / "sub_agent_outputs"
    assert artifacts_dir.exists()
    
    # Should have analysis files for selected agents
    analysis_files = list(artifacts_dir.glob("analysis_*_security.json"))
    assert len(analysis_files) > 0
    
    # Verify report saved
    reports_dir = tmp_path / "artifacts" / "orchestrator_agent" / "user" / "reports"
    report_files = list(reports_dir.glob("report_*.md"))
    assert len(report_files) > 0
```

---

## 🚀 Implementation Checklist

- [ ] Create `sub_agents/dynamic_router_agent/` directory
- [ ] Create `sub_agents/dynamic_router_agent/__init__.py`
- [ ] Create `sub_agents/dynamic_router_agent/agent.py` with `DynamicRouterAgent` class
- [ ] Update `CodeReviewOrchestrator.__init__`:
  - [ ] Create `analysis_agent_registry` dict
  - [ ] Create `dynamic_router_web` instance
  - [ ] Create `dynamic_router_github` instance
- [ ] Update `_create_web_pipeline`:
  - [ ] Add `self.dynamic_router_web` to sub_agents list
  - [ ] Update docstring
- [ ] Update `_create_github_pipeline`:
  - [ ] Add `self.dynamic_router_github` to sub_agents list
  - [ ] Update docstring
- [ ] Add logging throughout for debugging
- [ ] Write unit tests for `DynamicRouterAgent`
- [ ] Write integration tests for full pipeline
- [ ] Test with different agent selections:
  - [ ] Single agent (security only)
  - [ ] Multiple agents (security + quality)
  - [ ] All agents (comprehensive review)
  - [ ] No agents (general query)
- [ ] Verify artifacts saved correctly
- [ ] Update TODO list: Mark "Test end-to-end artifact flow" as complete

---

## 📊 Comparison with Alternatives

| Approach | Pros | Cons | Complexity |
|----------|------|------|------------|
| **Static SequentialAgent** (current, broken) | Simple, ADK native | Can't select agents dynamically | Low |
| **All agents + skip logic** | Uses ADK primitives | Wastes LLM calls, agents must check session state | Medium |
| **Custom orchestrator at root** | Full control | Bypasses ADK, reimplements scheduling | High |
| **Dynamic Router Agent** (proposed) | ✅ ADK native, ✅ Dynamic selection, ✅ Clean separation | Slightly more code than static | Medium |

---

## 🔮 Future Enhancements

### 1. **Caching in Router**
Add analysis result caching to router to avoid re-running agents for duplicate code:

```python
class DynamicRouterAgent(BaseAgent):
    def __init__(self, agent_registry, cache_service=None, **kwargs):
        self.cache_service = cache_service
    
    async def _run_async_impl(self, ctx):
        # Check cache before executing
        cache_key = hash(user_code + str(selected_agents))
        if cached := self.cache_service.get(cache_key):
            return cached
        
        # Execute agents...
        # Cache results
        self.cache_service.set(cache_key, results)
```

### 2. **Conditional Execution**
Add dependencies between agents:

```python
execution_plan = {
    "selected_agents": ["security", "quality"],
    "execution_mode": "parallel",
    "dependencies": {
        "quality": ["security"]  # Quality waits for security
    }
}
```

### 3. **Agent Priorities**
Execute high-priority agents first:

```python
execution_plan = {
    "selected_agents": [
        {"name": "security", "priority": 1},
        {"name": "quality", "priority": 2}
    ]
}
```

### 4. **Partial Failure Handling**
Continue execution if some agents fail:

```python
router = DynamicRouterAgent(
    agent_registry=registry,
    fail_fast=False  # Continue even if agents fail
)
```

### 5. **Agent Timeouts**
Add timeout per agent to prevent hanging:

```python
execution_plan = {
    "selected_agents": ["security", "quality"],
    "timeout_per_agent": 30  # seconds
}
```

---

## 📚 References

- **ADK Documentation**: [google-adk-agents](https://github.com/google/adk)
- **SequentialAgent**: Static agent pipeline execution
- **ParallelAgent**: Parallel agent execution
- **BaseAgent**: Custom agent implementation base class
- **Session State**: Agent communication via context

---

## 🎯 Success Criteria

Implementation is successful when:

### Core Functionality
1. ✅ Planning agent selects agents (e.g., `["security", "code_quality"]`)
2. ✅ Router reads execution_plan from session state
3. ✅ Router creates ParallelAgent with ONLY selected agents
4. ✅ Selected agents execute and call `save_analysis_result()`
5. ✅ Artifacts saved to `storage_bucket/artifacts/.../sub_agent_outputs/`
6. ✅ Report synthesizer loads artifacts successfully
7. ✅ Final report saved to `storage_bucket/artifacts/.../reports/`
8. ✅ Non-selected agents DO NOT execute (verify via logs)
9. ✅ General queries skip analysis phase entirely

### Resource Management
10. ✅ Small code (< 50K chars) with 2 agents → Full parallel execution
11. ✅ Small code (< 50K chars) with 4 agents → Controlled parallel (2 at a time)
12. ✅ Large code (> 50K chars) → Automatic switch to sequential mode
13. ✅ Max concurrent agents configurable (Ollama: 4, Gemini: 2)
14. ✅ No Gemini API timeout errors for large PRs
15. ✅ No rate limit errors (429) during batch agent execution

### Testing
16. ✅ All unit and integration tests pass
17. ✅ E2E test with 10K line code file (should use sequential mode)
18. ✅ E2E test with 4 agents on small code (should use controlled parallel)

---

**Next Step**: Implement `DynamicRouterAgent` class and integrate into orchestrator.
