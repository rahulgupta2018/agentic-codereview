# Intelligent Code Review Orchestrator - Custom Agent Design

**Design Pattern:** ReAct (Reasoning + Acting) with Conditional Agent Selection  
**Version:** 2.1  
**Date:** November 18, 2025  
**Related Documents:** [MULTI_AGENT_STATE_MANAGEMENT_DESIGN.md](./MULTI_AGENT_STATE_MANAGEMENT_DESIGN.md), [PHASE_2_ENHANCED_ORCHESTRATOR_DESIGN.md](./PHASE_2_ENHANCED_ORCHESTRATOR_DESIGN.md)

---

## 📚 Important Context

This document describes the **orchestration logic and agent selection pattern**. For details on:
- **Data storage** (artifacts, session state): See [MULTI_AGENT_STATE_MANAGEMENT_DESIGN.md](./MULTI_AGENT_STATE_MANAGEMENT_DESIGN.md)
- **Phase 2 enhancement** (PlanReActPlanner): See [PHASE_2_ENHANCED_ORCHESTRATOR_DESIGN.md](./PHASE_2_ENHANCED_ORCHESTRATOR_DESIGN.md)

### Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Custom Orchestrator Agent | ✅ Implemented | Phase 1 MVP with hardcoded if/elif logic |
| Input Classifier | ✅ Implemented | 7 request types (general_query, code_review_full, etc.) |
| Dynamic Agent Selection | ✅ Implemented | Conditional execution based on classification |
| InvocationContext Pattern | ✅ Implemented | Code flows through shared conversation context |
| Artifact Service | ❌ Planned | Phase 2 - code/report storage (see state management doc) |
| Checkpointing | 🟡 Stub Only | Method exists, not yet saving to disk |

### Design Document Relationship

This orchestrator design **complements** the state management design:

- **This Document (Orchestrator Design):**
  - **WHAT** agents to run (classification and selection logic)
  - **WHEN** to run them (ReAct pattern: Reason → Plan → Act → Synthesize)
  - **HOW** to coordinate them (Custom Agent with conditional if/elif)

- **State Management Design:**
  - **WHERE** to store data (session state vs artifacts)
  - **HOW** to persist data (JSONFileSessionService, FileArtifactService)
  - **WHAT** data to store (metadata vs large files)

Both designs work together:
```
User Input → Orchestrator (this doc) decides which agents to run
          → Agents execute and store outputs in session.state
          → State Management (other doc) handles persistence
          → Report Synthesizer reads from session.state
          → Phase 2: Artifact service stores large files
```

---

## 🎯 Core Concept

Your orchestrator should be a **Custom Agent** that:
1. **Reasons**: Analyzes the user input to determine what type of request it is
2. **Plans**: Decides which sub-agents to invoke (not blindly calling all)
3. **Acts**: Executes selected agents in parallel
4. **Synthesizes**: Always calls Report Synthesizer to consolidate results

### How Code Flows Through the System

**Key Concept:** In ADK, code flows through **InvocationContext**, not explicit parameters.

All agents share the same `InvocationContext` containing:
- **Conversation history** (including user's message with code)
- **Session state** (for cross-agent data sharing via `ctx.session.state`)
- **Current turn content**

**What this means:**
- ❌ No template variables like `{code_input}` or `{user_message}`
- ✅ Agents automatically see conversation context
- ✅ Agents can extract code, pass to tools, store results in session.state
- ✅ Sub-agent outputs stored via `output_key` (e.g., "code_quality_analysis")
- ✅ Report synthesizer reads outputs from session.state

**Example Flow:**
```
User: "Review this code: def foo(): pass"
     ↓
InvocationContext (shared across all agents)
├─ conversation history: [User message with code]
├─ session.state: {} (empty initially)
└─ current turn content
     ↓
Classifier Agent → reads from conversation context
     ↓
session.state["request_classification"] = {...}
     ↓
Security Agent → reads code from conversation context
     ↓
session.state["security_analysis"] = {...}
     ↓
Report Synthesizer → reads session.state["security_analysis"]
```

**Future Enhancement (Phase 2):**
When artifact service is implemented (see [state management design](./MULTI_AGENT_STATE_MANAGEMENT_DESIGN.md)):
- Code will be saved to artifacts: `artifact://code_input_123.py`
- Reports will be saved to artifacts: `artifact://report_123.md`
- Session state will store artifact references, not full content

---

## Architecture: Intelligent Orchestrator

```
┌─────────────────────────────────────────────────────────────┐
│                      USER INPUT                              │
│         "Check this code for security issues"                │
│              OR "What can you do?"                           │
│              OR "Review this code"                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│        CUSTOM ORCHESTRATOR AGENT (ReAct Pattern)            │
│                                                              │
│  Step 1: REASONING (Classifier LLM Agent)                   │
│  ├─ Analyze input                                           │
│  ├─ Determine request type:                                 │
│  │  • "general_query" → Direct response                     │
│  │  • "code_review_full" → All agents                       │
│  │  • "code_review_security" → Security agent only          │
│  │  • "code_review_quality" → Code quality agent only       │
│  │  • "code_review_custom" → Selected agents                │
│  └─ Store decision in ctx.session.state                     │
│                                                              │
│  Step 2: PLANNING                                           │
│  ├─ Based on classification, select agents:                 │
│  │  agents_to_run = []                                      │
│  │  if "security" in request: agents_to_run += [security]   │
│  │  if "quality" in request: agents_to_run += [quality]     │
│  └─ Store plan in ctx.session.state                         │
│                                                              │
│  Step 3: ACTING (ParallelAgent for selected agents)         │
│  ├─ Run selected agents in parallel                         │
│  ├─ Each agent stores output under output_key               │
│  └─ Checkpoint outputs to artifacts                         │
│                                                              │
│  Step 4: SYNTHESIS (Always)                                 │
│  ├─ Report Synthesizer reads available outputs              │
│  ├─ Generates consolidated markdown report                  │
│  └─ Returns final report to user                            │
└─────────────────────────────────────────────────────────────┘
```

---

## Detailed Flow

### Phase 1: Input Classification (Reasoning)

```python
class CodeReviewOrchestratorAgent(BaseAgent):
    """
    Intelligent orchestrator that analyzes input and selectively 
    invokes sub-agents based on user needs.
    """
    
    # Declare sub-agents
    classifier_agent: LlmAgent          # NEW: Analyzes user intent
    code_quality_agent: LlmAgent
    security_agent: LlmAgent
    engineering_practices_agent: LlmAgent
    carbon_emission_agent: LlmAgent
    report_synthesizer_agent: LlmAgent
    
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Custom orchestration with intelligent agent selection."""
        
        # STEP 1: REASONING - Classify user input
        logger.info("[Orchestrator] Step 1: Analyzing user input...")
        
        async for event in self.classifier_agent.run_async(ctx):
            yield event
        
        # Get classification result
        classification = ctx.session.state.get("request_classification", {})
        request_type = classification.get("type", "code_review_full")
        has_code = classification.get("has_code", False)
        focus_areas = classification.get("focus_areas", [])
        
        logger.info(f"[Orchestrator] Classification: {request_type}")
        logger.info(f"[Orchestrator] Focus areas: {focus_areas}")
        
        # STEP 2: PLANNING - Decide which agents to run
        if request_type == "general_query":
            # Direct response, no code analysis needed
            logger.info("[Orchestrator] General query detected, responding directly")
            # Orchestrator responds inline (no sub-agents needed)
            return
        
        if not has_code:
            logger.info("[Orchestrator] No code detected, prompting user")
            # Ask user to provide code
            return
        
        # Build agent execution plan
        agents_to_run = []
        
        if request_type == "code_review_full" or not focus_areas:
            # Run all agents for comprehensive review
            agents_to_run = [
                self.code_quality_agent,
                self.security_agent,
                self.engineering_practices_agent,
                self.carbon_emission_agent
            ]
            logger.info("[Orchestrator] Full review requested - running all agents")
        else:
            # Selective execution based on focus areas
            if "quality" in focus_areas or "complexity" in focus_areas:
                agents_to_run.append(self.code_quality_agent)
            if "security" in focus_areas or "vulnerability" in focus_areas:
                agents_to_run.append(self.security_agent)
            if "engineering" in focus_areas or "solid" in focus_areas:
                agents_to_run.append(self.engineering_practices_agent)
            if "carbon" in focus_areas or "performance" in focus_areas:
                agents_to_run.append(self.carbon_emission_agent)
            
            logger.info(f"[Orchestrator] Selective review - running {len(agents_to_run)} agents")
        
        # Store plan in session for tracking
        ctx.session.state["execution_plan"] = {
            "agents_selected": [agent.name for agent in agents_to_run],
            "request_type": request_type,
            "timestamp": datetime.now().isoformat()
        }
        
        # STEP 3: ACTING - Execute selected agents in parallel
        if agents_to_run:
            logger.info("[Orchestrator] Step 3: Executing selected agents in parallel...")
            
            # Create dynamic parallel agent
            parallel_analysis = ParallelAgent(
                name="DynamicParallelAnalysis",
                sub_agents=agents_to_run
            )
            
            async for event in parallel_analysis.run_async(ctx):
                # Checkpoint each sub-agent output to artifact
                if event.author != "DynamicParallelAnalysis" and event.turn_complete:
                    await self._checkpoint_agent_output(ctx, event.author)
                yield event
        
        # STEP 4: SYNTHESIS - Always consolidate results
        logger.info("[Orchestrator] Step 4: Synthesizing final report...")
        
        async for event in self.report_synthesizer_agent.run_async(ctx):
            yield event
        
        logger.info("[Orchestrator] Code review workflow complete")
```

### Phase 2: Classifier Agent Design

```python
# NEW: Intelligent input classifier
classifier_agent = LlmAgent(
    name="InputClassifierAgent",
    model="gemini-2.0-flash",
    instruction="""You are an intelligent request classifier for a code review system.

Analyze the user's input and classify it into one of these categories:

1. **general_query**: User asking about system capabilities, general questions
   Examples: "What can you do?", "How does this work?", "Help me"
   
2. **code_review_full**: User wants comprehensive analysis (all aspects)
   Examples: "Review this code", "Analyze this", "Check everything"
   
3. **code_review_security**: User wants security-focused analysis only
   Examples: "Is this secure?", "Check for vulnerabilities", "Security review"
   
4. **code_review_quality**: User wants code quality analysis only
   Examples: "Check code quality", "Is this maintainable?", "Complexity analysis"
   
5. **code_review_engineering**: User wants engineering practices review only
   Examples: "SOLID principles?", "Best practices?", "Design patterns?"
   
6. **code_review_carbon**: User wants environmental impact analysis only
   Examples: "Carbon footprint?", "Energy efficiency?", "Performance optimization?"
   
7. **code_review_custom**: User specifies multiple specific areas
   Examples: "Check security and quality", "Review for SOLID and performance"

Your task:
1. Detect if code is present in the input (look for code patterns, functions, classes)
2. Identify the request type
3. Extract focus areas if user mentions specific aspects
4. Return structured classification

**Your Input:**
The user's input is available in the current conversation context. Analyze the user's message to determine the request type.

Output Format (JSON):
{
  "type": "code_review_security",
  "has_code": true,
  "focus_areas": ["security", "vulnerability"],
  "confidence": "high",
  "reasoning": "User explicitly asks about security, code snippet present"
}
""",
    input_schema=None,
    output_key="request_classification"
)
```

### Phase 3: Sub-Agent Configuration

```python
# All sub-agents have output_keys for storing results
code_quality_agent = LlmAgent(
    name="CodeQualityAgent",
    model="gemini-2.0-flash",
    instruction="""Analyze code quality for the provided code.
    
    **Your Input:**
    The code to analyze is available in the current conversation context (user's message).
    Extract the code from the user's message and pass it to your analysis tools.
    
    Analyze:
    - Cyclomatic complexity
    - Maintainability
    - Code smells
    
    Return structured results as JSON.""",
    output_key="code_quality_analysis",  # Note: output_key suffix changed to "_analysis"
    tools=[complexity_analyzer_tool, static_analyzer_tool, parse_code_ast_tool]
)

security_agent = LlmAgent(
    name="SecurityAgent",
    model="gemini-2.0-flash",
    instruction="""Analyze security vulnerabilities in the provided code.
    
    **Your Input:**
    The code to analyze is available in the current conversation context (user's message).
    Extract the code from the user's message and pass it to your security scanning tool.
    
    Check for:
    - SQL injection
    - XSS vulnerabilities
    - Authentication issues
    - OWASP Top 10
    
    Return structured results as JSON.""",
    output_key="security_analysis",
    tools=[security_vulnerability_scanner]
)

engineering_practices_agent = LlmAgent(
    name="EngineeringPracticesAgent",
    model="gemini-2.0-flash",
    instruction="""Review engineering practices in the provided code.
    
    **Your Input:**
    The code to analyze is available in the current conversation context (user's message).
    Extract the code from the user's message and pass it to your analysis tool.
    
    Evaluate:
    - SOLID principles
    - Design patterns
    - Testing strategy
    - Documentation quality
    
    Return structured results as JSON.""",
    output_key="engineering_practices_analysis",
    tools=[engineering_practices_evaluator]
)

carbon_emission_agent = LlmAgent(
    name="CarbonEmissionAgent",
    model="gemini-2.0-flash",
    instruction="""Analyze environmental impact of the provided code.
    
    **Your Input:**
    The code to analyze is available in the current conversation context (user's message).
    Extract the code from the user's message and pass it to your carbon footprint analysis tool.
    
    Assess:
    - Computational efficiency
    - Energy consumption
    - Optimization opportunities
    - Green software practices
    
    Return structured results as JSON.""",
    output_key="carbon_emission_analysis",
    tools=[carbon_footprint_analyzer]
)
```

### Phase 4: Report Synthesizer

```python
report_synthesizer_agent = LlmAgent(
    name="ReportSynthesizerAgent",
    model="gemini-2.0-flash",
    instruction="""Synthesize a comprehensive code review report.

**CRITICAL: How to Retrieve Data from Session State**

You have access to session state which contains:
1. **Execution Plan** (Key: "execution_plan")
   - agents_selected: list of agent names that ran
   - request_type: type of analysis requested
   - analysis_id: unique identifier
   - timestamp: when analysis started

2. **Agent Analysis Results** (Keys: specific to each agent)
   - "code_quality_analysis" (from CodeQualityAgent)
   - "security_analysis" (from SecurityAgent)
   - "engineering_practices_analysis" (from EngineeringPracticesAgent)
   - "carbon_emission_analysis" (from CarbonEmissionAgent)

**STEP 1:** Read execution_plan from session state
- Extract: analysis_id, timestamp, agents_selected, request_type

**STEP 2:** For each agent in agents_selected, retrieve its output from session state
- CodeQualityAgent → read session.state["code_quality_analysis"]
- SecurityAgent → read session.state["security_analysis"]
- EngineeringPracticesAgent → read session.state["engineering_practices_analysis"]
- CarbonEmissionAgent → read session.state["carbon_emission_analysis"]

**STEP 3:** Parse JSON outputs and aggregate findings

**STEP 4:** Create markdown report with ONLY sections for agents that ran

Your task:
1. Check which sub-agents produced outputs (based on agents_selected)
2. Aggregate all available findings
3. Prioritize by severity (critical → high → medium → low)
4. Remove duplicates
5. Generate comprehensive markdown report

Report Structure:
```markdown
# Code Review Report

**Analysis ID:** [from execution_plan.analysis_id]
**Date:** [from execution_plan.timestamp]
**Agents Used:** [from execution_plan.agents_selected]

## 📊 Executive Summary
- **Total Issues:** [count from all agent outputs]
- **Severity Breakdown:** [critical/high/medium/low counts]

## 🔍 Detailed Findings

[Include sections ONLY for agents in execution_plan.agents_selected]

### 🔒 Security Analysis (if SecurityAgent in agents_selected)
[Read from session.state["security_analysis"]]

### 📈 Code Quality Analysis (if CodeQualityAgent in agents_selected)
[Read from session.state["code_quality_analysis"]]

### ⚙️ Engineering Practices (if EngineeringPracticesAgent in agents_selected)
[Read from session.state["engineering_practices_analysis"]]

### 🌱 Environmental Impact (if CarbonEmissionAgent in agents_selected)
[Read from session.state["carbon_emission_analysis"]]

## 💡 Prioritized Recommendations
[Aggregate from all agents, sorted by severity]

## 📋 Action Items
[Concrete steps to address findings]
```

**Phase 2 Enhancement:**
When artifact service is implemented, save report to artifact:
- Filename: f"report_{analysis_id}.md"
- Store artifact reference in session state
""",
    output_key="final_report"
)
```

---

## Complete Custom Agent Implementation

```python
# agent_workspace/orchestrator_agent/agent.py

from typing import AsyncGenerator, List
from google.adk.agents import BaseAgent, LlmAgent, ParallelAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types
from datetime import datetime
import logging
from typing_extensions import override

logger = logging.getLogger(__name__)

class CodeReviewOrchestratorAgent(BaseAgent):
    """
    Intelligent code review orchestrator using ReAct pattern.
    
    Instead of blindly calling all sub-agents, this orchestrator:
    1. Analyzes user input to understand intent
    2. Selectively invokes only relevant agents
    3. Consolidates results through report synthesizer
    """
    
    # Declare all sub-agents as class attributes (Pydantic requirement)
    classifier_agent: LlmAgent
    code_quality_agent: LlmAgent
    security_agent: LlmAgent
    engineering_practices_agent: LlmAgent
    carbon_emission_agent: LlmAgent
    report_synthesizer_agent: LlmAgent
    
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(
        self,
        name: str,
        classifier_agent: LlmAgent,
        code_quality_agent: LlmAgent,
        security_agent: LlmAgent,
        engineering_practices_agent: LlmAgent,
        carbon_emission_agent: LlmAgent,
        report_synthesizer_agent: LlmAgent,
    ):
        """Initialize orchestrator with all sub-agents."""
        
        # Define top-level sub-agents list for framework
        # NOTE: ParallelAgent will be created dynamically, so not in this list
        sub_agents_list = [
            classifier_agent,
            code_quality_agent,
            security_agent,
            engineering_practices_agent,
            carbon_emission_agent,
            report_synthesizer_agent,
        ]
        
        # Call parent constructor with all agents
        super().__init__(
            name=name,
            classifier_agent=classifier_agent,
            code_quality_agent=code_quality_agent,
            security_agent=security_agent,
            engineering_practices_agent=engineering_practices_agent,
            carbon_emission_agent=carbon_emission_agent,
            report_synthesizer_agent=report_synthesizer_agent,
            sub_agents=sub_agents_list,
        )
    
    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """
        Custom orchestration logic implementing ReAct pattern:
        - Reason: Classify input
        - Plan: Select agents
        - Act: Execute in parallel
        - Synthesize: Generate report
        """
        logger.info(f"[{self.name}] 🚀 Starting intelligent code review workflow")
        
        # ===== STEP 1: REASONING - Classify User Input =====
        logger.info(f"[{self.name}] 🧠 Step 1: Analyzing user input...")
        
        async for event in self.classifier_agent.run_async(ctx):
            logger.info(f"[{self.name}] Classifier event: {event.author}")
            yield event
        
        # Get classification result from session state
        classification = ctx.session.state.get("request_classification", {})
        
        if not classification:
            logger.error(f"[{self.name}] ❌ Classification failed, aborting")
            return
        
        request_type = classification.get("type", "code_review_full")
        has_code = classification.get("has_code", False)
        focus_areas = classification.get("focus_areas", [])
        
        logger.info(f"[{self.name}] 📋 Classification Result:")
        logger.info(f"[{self.name}]   - Type: {request_type}")
        logger.info(f"[{self.name}]   - Has Code: {has_code}")
        logger.info(f"[{self.name}]   - Focus Areas: {focus_areas}")
        
        # ===== STEP 2: HANDLE SPECIAL CASES =====
        
        # Case 1: General query (no code analysis needed)
        if request_type == "general_query":
            logger.info(f"[{self.name}] 💬 General query detected, responding directly")
            
            # Generate direct response
            response_text = self._get_system_capabilities_response()
            
            # Create response event
            response_event = Event(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=response_text)]
                ),
                author=self.name,
                turn_complete=True
            )
            yield response_event
            return
        
        # Case 2: No code provided
        if not has_code:
            logger.info(f"[{self.name}] ⚠️ No code detected, prompting user")
            
            prompt_text = """I'm ready to analyze your code! However, I don't see any code in your message.

Please provide:
1. The code you'd like me to review (paste it directly or describe the file)
2. Optionally, specify what you'd like me to focus on:
   - 🔒 Security vulnerabilities
   - 📊 Code quality and complexity
   - ⚙️ Engineering practices (SOLID, patterns)
   - 🌱 Environmental impact (performance)
   - Or ask for a comprehensive review of all aspects

Example: "Review this Python function for security issues: [paste code]"
"""
            
            prompt_event = Event(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=prompt_text)]
                ),
                author=self.name,
                turn_complete=True
            )
            yield prompt_event
            return
        
        # ===== STEP 3: PLANNING - Select Agents =====
        logger.info(f"[{self.name}] 📝 Step 2: Planning agent execution...")
        
        agents_to_run: List[LlmAgent] = []
        
        # Determine which agents to run based on classification
        if request_type == "code_review_full" or not focus_areas:
            # Full comprehensive review - all agents
            agents_to_run = [
                self.code_quality_agent,
                self.security_agent,
                self.engineering_practices_agent,
                self.carbon_emission_agent,
            ]
            logger.info(f"[{self.name}] ✅ Full review: Running all 4 analysis agents")
        
        elif request_type == "code_review_security":
            agents_to_run = [self.security_agent]
            logger.info(f"[{self.name}] 🔒 Security-focused review")
        
        elif request_type == "code_review_quality":
            agents_to_run = [self.code_quality_agent]
            logger.info(f"[{self.name}] 📊 Quality-focused review")
        
        elif request_type == "code_review_engineering":
            agents_to_run = [self.engineering_practices_agent]
            logger.info(f"[{self.name}] ⚙️ Engineering practices review")
        
        elif request_type == "code_review_carbon":
            agents_to_run = [self.carbon_emission_agent]
            logger.info(f"[{self.name}] 🌱 Environmental impact review")
        
        elif request_type == "code_review_custom":
            # Custom selection based on focus areas
            if any(area in focus_areas for area in ["quality", "complexity", "maintainability"]):
                agents_to_run.append(self.code_quality_agent)
            if any(area in focus_areas for area in ["security", "vulnerability", "secure"]):
                agents_to_run.append(self.security_agent)
            if any(area in focus_areas for area in ["engineering", "solid", "practices", "patterns"]):
                agents_to_run.append(self.engineering_practices_agent)
            if any(area in focus_areas for area in ["carbon", "performance", "efficiency", "energy"]):
                agents_to_run.append(self.carbon_emission_agent)
            
            logger.info(f"[{self.name}] 🎯 Custom review: {len(agents_to_run)} agents selected")
        
        # Store execution plan in session for tracking and report synthesis
        execution_plan = {
            "agents_selected": [agent.name for agent in agents_to_run],
            "request_type": request_type,
            "focus_areas": focus_areas,
            "timestamp": datetime.now().isoformat(),
            "analysis_id": f"analysis_{datetime.now():%Y%m%d_%H%M%S}"
        }
        ctx.session.state["execution_plan"] = execution_plan
        logger.info(f"[{self.name}] 📌 Execution plan stored in session")
        
        # ===== STEP 4: ACTING - Execute Selected Agents in Parallel =====
        if agents_to_run:
            logger.info(f"[{self.name}] ⚡ Step 3: Executing {len(agents_to_run)} agents in parallel...")
            
            # Create dynamic parallel agent for selected agents
            parallel_analysis = ParallelAgent(
                name="DynamicParallelAnalysis",
                sub_agents=agents_to_run
            )
            
            # Execute and stream events
            async for event in parallel_analysis.run_async(ctx):
                # Log progress
                if event.turn_complete:
                    logger.info(f"[{self.name}] ✅ {event.author} completed")
                
                # Checkpoint completed agent outputs to artifacts
                if event.author != "DynamicParallelAnalysis" and event.turn_complete:
                    await self._checkpoint_agent_output(ctx, event.author)
                
                yield event
            
            logger.info(f"[{self.name}] ✅ All selected agents completed")
        else:
            logger.warning(f"[{self.name}] ⚠️ No agents selected for execution")
        
        # ===== STEP 5: SYNTHESIS - Always Consolidate Results =====
        logger.info(f"[{self.name}] 📊 Step 4: Synthesizing final report...")
        
        async for event in self.report_synthesizer_agent.run_async(ctx):
            logger.info(f"[{self.name}] Report synthesizer event: {event.author}")
            yield event
        
        logger.info(f"[{self.name}] ✅ Code review workflow complete!")
    
    async def _checkpoint_agent_output(self, ctx: InvocationContext, agent_name: str):
        """
        Checkpoint sub-agent output to session state.
        
        Phase 1 (Current): Stores metadata in session state
        Phase 2 (Future): Will save to artifact service for disk persistence
        
        See MULTI_AGENT_STATE_MANAGEMENT_DESIGN.md for Phase 2 artifact service implementation.
        """
        # Get agent's output from session state based on output_key
        output_key_map = {
            "CodeQualityAgent": "code_quality_analysis",
            "SecurityAgent": "security_analysis",
            "EngineeringPracticesAgent": "engineering_practices_analysis",
            "CarbonEmissionAgent": "carbon_emission_analysis",
        }
        
        output_key = output_key_map.get(agent_name)
        if not output_key:
            return
        
        agent_output = ctx.session.state.get(output_key)
        if not agent_output:
            return
        
        analysis_id = ctx.session.state.get("execution_plan", {}).get("analysis_id", "unknown")
        logger.info(f"[{self.name}] 💾 Checkpointed {agent_name} output (analysis_id: {analysis_id})")
        
        # Store checkpoint metadata in session state (Phase 1)
        ctx.session.state[f"checkpoint_{agent_name}"] = {
            "timestamp": datetime.now().isoformat(),
            "output_key": output_key,
            "analysis_id": analysis_id,
            "status": "completed"
        }
        
        # Phase 2: Will add artifact service integration
        # filename = f"analysis_{analysis_id}_{agent_name.lower()}.json"
        # await artifact_service.save_artifact(
        #     app_name=app_name,
        #     user_id=user_id,
        #     filename=filename,
        #     artifact=types.Part(text=json.dumps(agent_output)),
        #     session_id=ctx.session.id
        # )
    
    def _get_system_capabilities_response(self) -> str:
        """Generate response for general capability queries."""
        return """🤖 **AI Code Review Assistant**

I'm an intelligent multi-agent system that analyzes code across multiple quality dimensions.

**What I Can Do:**

🔍 **Comprehensive Code Analysis:**
- 📊 **Code Quality**: Complexity, maintainability, code smells
- 🔒 **Security**: Vulnerabilities, OWASP Top 10, authentication issues
- ⚙️ **Engineering Practices**: SOLID principles, design patterns, testability
- 🌱 **Environmental Impact**: Carbon footprint, performance optimization

**How to Use:**

1. **Full Review** (all aspects):
   "Review this code" or "Analyze this function"

2. **Targeted Review** (specific focus):
   "Check this for security issues"
   "Analyze code quality"
   "Review for SOLID principles"
   "Check carbon footprint"

3. **Custom Review** (multiple areas):
   "Review this for security and quality"

**Ready to analyze your code!** Just paste your code and specify what you'd like me to focus on.
"""


# ===== Instantiate All Agents =====

# 1. Classifier Agent (NEW!)
classifier_agent = LlmAgent(
    name="InputClassifierAgent",
    model=get_agent_model(),
    instruction="""[Instruction from earlier section]""",
    output_key="request_classification"
)

# 2-5. Analysis Agents (with output_keys)
code_quality_agent = LlmAgent(
    name="CodeQualityAgent",
    model=get_agent_model(),
    instruction="""...""",
    output_key="code_quality_results",
    tools=[complexity_analyzer_tool, static_analyzer_tool]
)

# ... (security, engineering, carbon agents)

# 6. Report Synthesizer
report_synthesizer_agent = LlmAgent(
    name="ReportSynthesizerAgent",
    model=get_agent_model(),
    instruction="""...""",
    output_key="final_report"
)

# 7. Create Custom Orchestrator
orchestrator_agent = CodeReviewOrchestratorAgent(
    name="CodeReviewOrchestrator",
    classifier_agent=classifier_agent,
    code_quality_agent=code_quality_agent,
    security_agent=security_agent,
    engineering_practices_agent=engineering_practices_agent,
    carbon_emission_agent=carbon_emission_agent,
    report_synthesizer_agent=report_synthesizer_agent,
)
```

---

## Benefits of This Design

### ✅ **Intelligence**
- Doesn't blindly run all agents
- Understands user intent
- Saves compute resources

### ✅ **Efficiency**
- Only invokes relevant agents
- "Check security" → Security agent only
- "Full review" → All agents

### ✅ **User Experience**
- Faster responses for targeted queries
- Handles general questions without code analysis
- Clear feedback on what's happening

### ✅ **Flexibility**
- Easy to add new agent types
- Easy to modify selection logic
- Supports complex conditional flows

### ✅ **Maintainability**
- Clear separation: Reason → Plan → Act → Synthesize
- All logic in one Custom Agent
- Easy to debug and trace execution

---

## Comparison: Old vs New Design

### ❌ **Old Design (LlmAgent Orchestrator)**
```python
orchestrator_agent = LlmAgent(
    name="orchestrator_agent",
    model=model,
    instruction="Route to sub-agents...",
    sub_agents=[
        code_quality_agent,
        security_agent,
        engineering_practices_agent,
        carbon_emission_agent,
        report_synthesizer_agent
    ]
)
```
**Problems:**
- ❌ Always calls ALL sub-agents (wasteful)
- ❌ Can't handle general queries
- ❌ No conditional logic
- ❌ LLM decides routing (unreliable)

### ✅ **New Design (Custom Agent with ReAct)**
```python
orchestrator_agent = CodeReviewOrchestratorAgent(
    name="CodeReviewOrchestrator",
    classifier_agent=classifier_agent,  # NEW: Analyzes intent
    code_quality_agent=code_quality_agent,
    security_agent=security_agent,
    engineering_practices_agent=engineering_practices_agent,
    carbon_emission_agent=carbon_emission_agent,
    report_synthesizer_agent=report_synthesizer_agent,
)
```
**Advantages:**
- ✅ Intelligent agent selection
- ✅ Handles general queries
- ✅ Conditional execution paths
- ✅ You control orchestration logic
- ✅ Reliable, deterministic behavior

---

## Implementation Checklist

### Phase 1: Core Custom Agent
- [ ] Create `CodeReviewOrchestratorAgent` class inheriting from `BaseAgent`
- [ ] Implement `_run_async_impl` with 4-step flow (Reason → Plan → Act → Synthesize)
- [ ] Create `InputClassifierAgent` (LlmAgent)
- [ ] Update existing sub-agents with proper `output_key`
- [ ] Test basic flow: "Review this code" → All agents → Report

### Phase 2: Conditional Logic
- [ ] Implement request type handling (general_query, code_review_full, etc.)
- [ ] Add dynamic agent selection based on classification
- [ ] Test targeted queries: "Check security" → Security agent only
- [ ] Test custom queries: "Review security and quality" → 2 agents

### Phase 3: Enhanced Features
- [ ] Add checkpointing after each sub-agent
- [ ] Integrate with artifact service
- [ ] Add progress logging/streaming
- [ ] Handle edge cases (no code, invalid requests)

### Phase 4: Report Synthesis
- [ ] Update Report Synthesizer to handle partial results
- [ ] Add sections conditionally based on which agents ran
- [ ] Save report to artifact
- [ ] Update session state with analysis record

---

## Testing Plan

```python
# Test 1: General query (no code analysis)
user_input = "What can you do?"
# Expected: Direct response, no sub-agents invoked

# Test 2: Full review
user_input = "Review this code: def foo(): pass"
# Expected: All 4 analysis agents + synthesizer

# Test 3: Security focus
user_input = "Check this for security issues: [code]"
# Expected: Security agent only + synthesizer

# Test 4: Custom multi-focus
user_input = "Review this for security and code quality: [code]"
# Expected: Security + Code Quality agents + synthesizer

# Test 5: No code provided
user_input = "Check security"
# Expected: Prompt user to provide code
```

---

## Conclusion

Your intuition is **100% correct**! The orchestrator should:

1. ✅ **Think First** (ReAct reasoning via classifier)
2. ✅ **Plan** (Select relevant agents, not all)
3. ✅ **Act** (Parallel execution of selected agents)
4. ✅ **Synthesize** (Report consolidation always)

This design makes your system:
- **Intelligent** (understands user intent)
- **Efficient** (doesn't waste resources)
- **Scalable** (easy to add new agents/logic)
- **User-friendly** (faster, smarter responses)

**Next Step:** Implement the `CodeReviewOrchestratorAgent` as a Custom Agent inheriting from `BaseAgent`!

---

## 📝 Design Documentation Notes

### About Placeholder Syntax in This Document

Earlier versions of this document used placeholder syntax like `{code_input}` and `{user_message}`. These were **conceptual placeholders** to represent "code that will be available to agents."

**Important Clarifications:**

1. **ADK doesn't use template variables** - All data flows through `InvocationContext`
2. **Code is NOT passed as explicit parameters** - Agents read from conversation context
3. **Sub-agent outputs are stored via `output_key`** - Not template variables
4. **Current implementation uses InvocationContext correctly** - See actual code in `/agent_workspace/orchestrator_agent/`

The placeholder syntax was used during design phase to represent:
- "Code will be available somehow" → **Reality:** Through conversation context
- "Outputs will be accessible" → **Reality:** Via session.state with output_keys
- "Reports will reference data" → **Reality:** Report synthesizer reads session.state

**Why the confusion occurred:**
- Design was written before ADK patterns were fully understood
- State management design (separate doc) would handle data flow
- Placeholders were conceptual, not literal ADK syntax

**Current correct pattern:**
```python
# ❌ Old conceptual design (placeholders)
instruction = "Read code from: {code_input}"

# ✅ Actual implementation (InvocationContext)
instruction = """
The code to analyze is available in the current conversation context (user's message).
Extract the code from the user's message and pass it to your analysis tools.
"""
```

This document has been updated to reflect **actual ADK patterns** used in the implementation.
