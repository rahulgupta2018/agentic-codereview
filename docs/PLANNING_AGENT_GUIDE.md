# Planning Agent - Implementation Guide

## Overview

The **PlanningAgent** is an intelligent agent selection system using Google ADK's **PlanReActPlanner** pattern. It analyzes code review requests and determines which analysis agents should run, optimizing for both thoroughness and efficiency.

## Architecture

### Location
`agent_workspace/orchestrator_agent/sub_agents/planning_agent/`

### Pattern: Plan-ReAct
```
┌─────────────────────────────────────────────┐
│ PLAN-REACT PATTERN                          │
├─────────────────────────────────────────────┤
│                                             │
│ 1. PLAN:                                    │
│    ├─ Analyze request intent                │
│    ├─ Identify required analyses            │
│    └─ Determine execution strategy          │
│                                             │
│ 2. REACT (Act):                             │
│    ├─ Call proxy tools (selections)         │
│    ├─ select_security_analysis()            │
│    ├─ select_quality_analysis()             │
│    ├─ select_practices_analysis()           │
│    └─ select_carbon_analysis()              │
│                                             │
│ 3. OUTPUT:                                  │
│    └─ Execution plan (JSON)                 │
│        ├─ selected_agents: [...]            │
│        ├─ execution_mode: "parallel"        │
│        ├─ reasoning: "..."                  │
│        └─ estimated_duration: "..."         │
│                                             │
└─────────────────────────────────────────────┘
```

## Key Concepts

### 1. Proxy Tools (Not Execution Tools)

**Important:** The planning agent's tools don't execute analysis - they're **selection markers**.

```python
# ❌ WRONG UNDERSTANDING
select_security_analysis()  # Doesn't run security analysis!

# ✅ CORRECT UNDERSTANDING
select_security_analysis()  # Marks security agent for selection
# Orchestrator reads this call and runs SecurityAgent later
```

**How it works:**
1. PlanningAgent calls proxy tools
2. Tools return `{status: 'success', agent: 'security'}`
3. Orchestrator intercepts tool calls
4. Orchestrator creates ExecutionPipeline with selected agents
5. ExecutionPipeline actually runs the analysis agents

### 2. PlanReActPlanner

**What is it?**
- Built-in ADK planner for intelligent decision-making
- Combines Planning (reasoning) + ReAct (tool usage)
- LLM decides which tools to call based on context

**How it differs from regular Agent:**

| Feature | Regular Agent | Agent with PlanReActPlanner |
|---------|---------------|----------------------------|
| Tool usage | Direct tool calls | Planned tool selection |
| Reasoning | Implicit | Explicit planning phase |
| Multi-step | Sequential | Plan → Act → Reflect |
| Decision quality | Good | Better (systematic) |

```python
# Regular Agent
agent = Agent(
    tools=[tool1, tool2],
    instruction="Use tools to solve task"
)

# Agent with PlanReActPlanner
planning_agent = Agent(
    planner=PlanReActPlanner(),  # ← Adds planning capability
    tools=[select_tool1, select_tool2],
    instruction="Plan which tools to use, then use them"
)
```

### 3. Execution Modes

**Parallel (Default):**
```python
{
    "execution_mode": "parallel",
    "selected_agents": ["security", "code_quality", "engineering"]
}

# Runs simultaneously:
ParallelAgent(
    sub_agents=[SecurityAgent, CodeQualityAgent, EngineeringAgent]
)
```

**Sequential (Rare):**
```python
{
    "execution_mode": "sequential",
    "selected_agents": ["quality", "practices"]  
}

# Runs one after another:
SequentialAgent(
    sub_agents=[CodeQualityAgent, EngineeringAgent]
)
```

**When to use sequential?**
- Analysis B depends on results from Analysis A
- Example: Practices analysis needs quality metrics first
- **Note:** Most analyses are independent → use parallel

## Input Context

The planning agent receives rich context from upstream agents:

### From SourceDetector
```json
{
    "source_detection": {
        "source": "github_webhook" | "web_ui",
        "github_context": {
            "repo": "owner/repo",
            "pr_number": 123,
            "head_sha": "abc123"
        }
    }
}
```

### From GitHubFetcher (if webhook)
```json
{
    "github_pr_data": {
        "pr_number": 123,
        "title": "Add authentication",
        "files": [
            {
                "filename": "auth.py",
                "language": "python",
                "additions": 50
            }
        ]
    }
}
```

### From Classifier (if Web UI)
```json
{
    "classification": {
        "type": "code_review_security",
        "focus_areas": ["authentication", "input_validation"]
    }
}
```

### User Message
```
"Please review this authentication code for security issues"
```

## Decision Logic

### Comprehensive Review
```
Input: "Review this code"
       (No specific focus mentioned)

Logic:
├─ No specific area mentioned
├─ Default to thorough analysis
└─ SELECT ALL agents

Output:
{
    "selected_agents": ["security", "code_quality", "engineering", "carbon"],
    "execution_mode": "parallel",
    "reasoning": "Comprehensive review requested without specific focus..."
}
```

### Security Focused
```
Input: "Is this authentication code secure?"

Logic:
├─ Keywords: "secure", "authentication"
├─ Security concern identified
└─ SELECT security (only)

Output:
{
    "selected_agents": ["security"],
    "execution_mode": "parallel",
    "reasoning": "User specifically asked about security..."
}
```

### Multiple Areas
```
Input: "Check security and performance"

Logic:
├─ Keywords: "security", "performance"
├─ Multiple concerns identified
└─ SELECT security, carbon, quality

Output:
{
    "selected_agents": ["security", "carbon", "code_quality"],
    "execution_mode": "parallel",
    "reasoning": "User requested security and performance analysis..."
}
```

### Quality + Practices
```
Input: "Is this code too complex? Does it follow best practices?"

Logic:
├─ Keywords: "complex", "best practices"
├─ Quality and practices concerns
└─ SELECT quality, practices

Output:
{
    "selected_agents": ["code_quality", "engineering"],
    "execution_mode": "parallel",
    "reasoning": "User concerned with complexity and best practices..."
}
```

## Output Format

### Success Case
```json
{
    "selected_agents": ["security", "code_quality"],
    "execution_mode": "parallel",
    "reasoning": "User requested security review of authentication code. Including quality analysis to identify complexity issues that might introduce security bugs.",
    "estimated_duration": "3-4 minutes",
    "analysis_focus": {
        "security": "High priority - authentication code requires thorough security review",
        "code_quality": "Medium priority - complexity can lead to security issues"
    }
}
```

### Error Case
```json
{
    "status": "error",
    "error": "No code detected in request",
    "reasoning": "Cannot perform code analysis without code",
    "recommendation": "Please provide code or GitHub PR for review"
}
```

## Proxy Tool Details

### select_security_analysis

**When to use:**
- User mentions: security, vulnerabilities, exploits, SQL injection, XSS, CSRF
- Code handles: user input, authentication, authorization, sensitive data
- Comprehensive review (always include)

**What it analyzes:**
- Security vulnerabilities (OWASP Top 10)
- Authentication/authorization issues
- Input validation problems
- Cryptography weaknesses
- Sensitive data exposure
- Dependency vulnerabilities

### select_quality_analysis

**When to use:**
- User mentions: quality, complexity, maintainability, code smells
- Questions about: readability, structure, refactoring
- Comprehensive review (always include)

**What it analyzes:**
- Cyclomatic complexity
- Code maintainability index
- Code smells and anti-patterns
- Duplication detection
- Function length and parameter count

### select_practices_analysis

**When to use:**
- User mentions: best practices, SOLID, design patterns, architecture
- Questions about: testing, documentation, code organization
- Comprehensive review (always include)

**What it analyzes:**
- SOLID principles compliance
- Design pattern usage
- Testing strategy and coverage
- Documentation quality
- Code organization

### select_carbon_analysis

**When to use:**
- User mentions: performance, efficiency, optimization, scalability
- Questions about: resource usage, "green" code
- Comprehensive review (optional - only if performance critical)

**What it analyzes:**
- Computational efficiency
- Algorithm complexity (Big O)
- Resource usage (CPU, memory, I/O)
- Energy consumption patterns
- Database query optimization

## Usage in Orchestrator

### GitHubPipeline
```python
github_pipeline = SequentialAgent(
    name="GitHubPipeline",
    sub_agents=[
        github_fetcher_agent,    # 1. Fetch PR data
        planning_agent,          # 2. Decide which agents to run ← HERE
        # 3. ExecutionPipeline created dynamically based on plan
        report_synthesizer,      # 4. Consolidate results
        github_publisher         # 5. Post to GitHub
    ]
)
```

### WebPipeline
```python
web_pipeline = SequentialAgent(
    name="WebPipeline",
    sub_agents=[
        classifier_agent,        # 1. Classify user intent
        planning_agent,          # 2. Decide which agents to run ← HERE
        # 3. ExecutionPipeline created dynamically based on plan
        report_synthesizer       # 4. Consolidate results
    ]
)
```

### Dynamic ExecutionPipeline Creation

The orchestrator intercepts PlanningAgent's output:

```python
async def create_execution_pipeline(self, context):
    """Create execution pipeline based on planning decision."""
    
    # Get plan from PlanningAgent output
    plan = context.state.get('execution_plan')
    
    # Map agent names to agent instances
    agent_map = {
        "security": self.security_agent,
        "code_quality": self.code_quality_agent,
        "engineering": self.engineering_agent,
        "carbon": self.carbon_agent
    }
    
    # Build selected agents list
    selected = [agent_map[name] for name in plan['selected_agents']]
    
    # Create appropriate pipeline
    if plan['execution_mode'] == 'parallel':
        return ParallelAgent(
            name="ParallelExecution",
            sub_agents=selected
        )
    else:
        return SequentialAgent(
            name="SequentialExecution",
            sub_agents=selected
        )
```

## Testing

### Unit Test Example
```python
import pytest
from agent_workspace.orchestrator_agent.sub_agents.planning_agent import planning_agent

@pytest.mark.asyncio
async def test_planning_agent_security_focus():
    """Test planning agent selects security for security queries."""
    
    # Setup context
    context = {
        'user_message': 'Is this authentication code secure?',
        'source_detection': {'source': 'web_ui'},
        'classification': {
            'type': 'code_review_security',
            'focus_areas': ['authentication']
        }
    }
    
    # Run planning agent
    result = await planning_agent.run_async(context)
    plan = result.state['execution_plan']
    
    # Verify plan
    assert 'security' in plan['selected_agents']
    assert plan['execution_mode'] == 'parallel'
    assert len(plan['selected_agents']) == 1  # Security only
```

### Integration Test Example
```python
@pytest.mark.asyncio
async def test_full_pipeline_with_planning():
    """Test complete pipeline with planning agent."""
    
    # Create pipeline
    pipeline = SequentialAgent(
        sub_agents=[
            classifier_agent,
            planning_agent,
            # ExecutionPipeline created dynamically
        ]
    )
    
    # Run pipeline
    result = await pipeline.run_async({
        'user_message': 'Comprehensive code review please'
    })
    
    # Verify plan was created
    plan = result.state['execution_plan']
    assert len(plan['selected_agents']) == 4  # All agents
    assert plan['execution_mode'] == 'parallel'
```

## Best Practices

### ✅ Do

1. **Trust the Planner**: PlanReActPlanner is intelligent - let it decide
2. **Provide Context**: Give rich context (user_message, github_pr_data, classification)
3. **Use Parallel by Default**: Most analyses are independent
4. **Include Reasoning**: Always output clear reasoning for selections
5. **Handle Edge Cases**: No code? Unclear intent? Handle gracefully

### ❌ Don't

1. **Don't Over-Specify**: Let planner decide based on context
2. **Don't Ignore Context**: Use all available context (source, PR data, classification)
3. **Don't Force Sequential**: Only use if analyses truly depend on each other
4. **Don't Skip Reasoning**: Always explain why agents were selected
5. **Don't Execute in Tools**: Proxy tools are markers, not executors

## Debugging

### Enable Verbose Logging
```python
import logging
logging.getLogger('google.adk.planners').setLevel(logging.DEBUG)
logging.getLogger('planning_agent').setLevel(logging.DEBUG)
```

### Inspect Tool Calls
```python
async for event in planning_agent.run_async(context):
    if event.type == 'TOOL_CALL_START':
        print(f"Tool: {event.tool_name}")
        print(f"Args: {event.arguments}")
    elif event.type == 'TOOL_CALL_RESULT':
        print(f"Result: {event.result}")
```

### Check Plan Output
```python
result = await planning_agent.run_async(context)
plan = result.state['execution_plan']

print(f"Selected: {plan['selected_agents']}")
print(f"Mode: {plan['execution_mode']}")
print(f"Reasoning: {plan['reasoning']}")
```

## Common Issues

### Issue 1: No Agents Selected
**Symptom:** `selected_agents` is empty array

**Causes:**
- Unclear user intent
- No code detected
- Invalid request format

**Solution:**
- Default to comprehensive review (all agents)
- Check for code presence
- Provide clear error message

### Issue 2: Wrong Execution Mode
**Symptom:** Sequential used when parallel would work

**Causes:**
- Over-cautious planning
- Incorrect dependency assumptions

**Solution:**
- Use parallel by default
- Only use sequential if true dependency exists
- Document why sequential is needed

### Issue 3: Inconsistent Tool Calls
**Symptom:** Tool calls don't match selected_agents

**Causes:**
- Planning logic error
- Output parsing issues

**Solution:**
- Validate tool calls match output
- Ensure consistent agent naming
- Add validation in orchestrator

## Performance Considerations

### Planning Overhead
- **Time**: ~2-3 seconds for planning decision
- **Tokens**: ~500-1000 tokens (instruction + context)
- **Worth it?**: Yes - saves time by avoiding unnecessary analyses

### Optimization Tips
1. **Cache Plans**: Similar requests → same plan (cache by hash)
2. **Parallel by Default**: Faster execution for independent analyses
3. **Early Exit**: If clearly security-only, don't over-plan
4. **Context Pruning**: Only pass relevant context to planner

## See Also

- **Design Doc**: `docs/PHASE_2_REVISED_DESIGN.md` (lines 1342-1410)
- **ADK Planners**: https://raphaelmansuy.github.io/adk_training/docs/workflows-orchestration
- **Tool Capabilities**: https://raphaelmansuy.github.io/adk_training/docs/tools-capabilities
- **GitHub Agents**: `docs/GITHUB_AGENTS_GUIDE.md`
- **Orchestrator**: `agent_workspace/orchestrator_agent/agent.py`
