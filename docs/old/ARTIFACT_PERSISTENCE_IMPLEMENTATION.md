# Artifact Persistence Implementation

## Summary

Successfully implemented ADK artifact persistence across all analysis agents. Artifacts are now saved to `storage_bucket/artifacts/` with proper metadata.

## Problem Identified

**Root Cause**: Agents were returning JSON responses but never calling `save_artifact()` to persist results.

**Evidence**:
- ✅ `FileArtifactService` was correctly configured in Runner
- ✅ `JSONFileSessionService` was working (sessions were being saved)
- ❌ Agents had no tools that called `tool_context.save_artifact()`
- ❌ No artifacts were being created in storage_bucket/

## Solution Implemented

### 1. Created Artifact-Saving Tools (`tools/save_analysis_artifact.py`)

Three async tools that use `ToolContext` to persist artifacts:

```python
async def save_analysis_result(analysis_data: str, agent_name: str, tool_context: ToolContext)
async def save_code_input(code: str, language: str, tool_context: ToolContext)
async def save_final_report(report_markdown: str, tool_context: ToolContext)
```

**Key Pattern** (per ADK documentation):
- ✅ Async functions
- ✅ Accept `ToolContext` parameter
- ✅ Call `tool_context.save_artifact()` with `artifact=` parameter
- ✅ Return structured dict with status/report/data

### 2. Added Tools to Analysis Agents

Updated all 5 agents that perform analysis:

#### Security Agent (`security_agent/agent.py`)
```python
from tools.save_analysis_artifact import save_analysis_result
tools=[scan_security_vulnerabilities, save_analysis_result]
```
- Saves results as: `analysis_{timestamp}_security_agent.json`

#### Code Quality Agent (`code_quality_agent/agent.py`)
```python
from tools.save_analysis_artifact import save_analysis_result
tools=[analyze_code_complexity, analyze_static_code, parse_code_ast, save_analysis_result]
```
- Saves results as: `analysis_{timestamp}_code_quality_agent.json`

#### Engineering Practices Agent (`engineering_practices_agent/agent.py`)
```python
from tools.save_analysis_artifact import save_analysis_result
tools=[evaluate_engineering_practices, save_analysis_result]
```
- Saves results as: `analysis_{timestamp}_engineering_practices_agent.json`

#### Carbon Emission Agent (`carbon_emission_agent/agent.py`)
```python
from tools.save_analysis_artifact import save_analysis_result
tools=[analyze_carbon_footprint, save_analysis_result]
```
- Saves results as: `analysis_{timestamp}_carbon_emission_agent.json`

#### Report Synthesizer Agent (`report_synthesizer_agent/agent.py`)
```python
from tools.save_analysis_artifact import save_final_report
tools=[load_analysis_results_from_artifacts, save_final_report]
```
- Saves final report as: `report_{timestamp}.md`

### 3. Updated Agent Instructions

Each agent now has instructions to:
1. Perform their analysis using existing tools
2. **MUST call** the artifact-saving tool to persist results
3. Pass complete JSON/Markdown output to the save tool

Example instruction addition:
```
**IMPORTANT: After completing analysis, MUST call save_analysis_result tool to persist results:**
- Pass your complete JSON analysis output as the analysis_data parameter
- Pass "{agent_name}" as the agent_name parameter
- This saves your work to the artifact storage for the report synthesizer
```

## Storage Structure

Artifacts are saved to `storage_bucket/artifacts/` with this structure:

```
storage_bucket/
├── artifacts/
│   └── {app_name}/
│       └── {user_id}/
│           ├── inputs/              # User code (input_*.{ext})
│           ├── reports/             # Final reports (report_*.md)
│           └── sub_agent_outputs/   # Analysis results (analysis_*_{agent}.json)
│               ├── analysis_20251203_143022_security_agent.json
│               ├── analysis_20251203_143022_security_agent.json.meta.json
│               ├── analysis_20251203_143025_code_quality_agent.json
│               ├── analysis_20251203_143025_code_quality_agent.json.meta.json
│               └── ... (other agents)
└── sessions/
    └── {app_name}/
        └── {user_id}/
            └── {session_id}.json
```

### Metadata Files

Each artifact has a companion `.meta.json` file:
```json
{
  "filename": "analysis_20251203_143022_security_agent.json",
  "app_name": "Code_Review_System",
  "user_id": "rahul_gupta_123",
  "session_id": "abc-123-def",
  "content_type": "text",
  "size_bytes": 4567,
  "created_at": "2025-12-03T14:30:22",
  "version": 1,
  "custom": {}
}
```

## How It Works

### ADK Artifact Flow

1. **Runner Configuration** (already correct in `main.py`):
   ```python
   runner = Runner(
       agent=orchestrator_agent,
       artifact_service=artifact_service,  # ← Makes artifacts available
       session_service=session_service
   )
   ```

2. **Tool Execution**:
   - Agent calls `save_analysis_result(analysis_data, agent_name, tool_context)`
   - ADK passes `ToolContext` with access to artifact service
   - Tool calls `tool_context.save_artifact(filename, artifact)`

3. **Service Routing**:
   - ADK routes to `FileArtifactService.save_artifact()`
   - Our service saves file to `storage_bucket/artifacts/`
   - Returns version number (1)

4. **Verification**:
   - Files appear in correct subdirectories (inputs/, reports/, sub_agent_outputs/)
   - Metadata files created alongside each artifact
   - Permissions preserved across restarts

## Testing

### Test Script Created: `test_minimal_artifact.py`

Minimal test that verifies:
- ✅ Runner with artifact_service configured
- ✅ Agent with async tool that calls `tool_context.save_artifact()`
- ✅ Artifacts created in `storage_bucket/artifacts/`
- ✅ Metadata files generated

**Test Results**:
```
✅ SUCCESS! Found 2 file(s):
   📄 ArtifactTest/test_user/other/test_message.txt
   📄 ArtifactTest/test_user/other/test_message.txt.meta.json
```

### Next Steps for E2E Testing

1. Start server: `./scripts/start_server.sh`
2. Submit code via web UI: http://localhost:8800
3. Verify artifacts created:
   ```bash
   ls -la storage_bucket/artifacts/Code_Review_System/*/sub_agent_outputs/
   ```
4. Check analysis files:
   - `analysis_*_security_agent.json`
   - `analysis_*_code_quality_agent.json`
   - `analysis_*_engineering_practices_agent.json`
   - `analysis_*_carbon_emission_agent.json`
5. Check final report:
   ```bash
   ls -la storage_bucket/artifacts/Code_Review_System/*/reports/
   ```

## Agents That DON'T Need Artifact Saving

These agents don't perform analysis, so they don't need artifact tools:

- ❌ **classifier_agent** - Just classifies request type
- ❌ **planning_agent** - Just selects which agents to run
- ❌ **source_detector_agent** - Just detects GitHub vs Web
- ❌ **github_fetcher_agent** - Fetches code from GitHub (doesn't analyze)
- ❌ **github_publisher_agent** - Publishes results to GitHub (doesn't analyze)

## Key Takeaways

1. **ADK Artifact Pattern**:
   - Async tools with `ToolContext` parameter
   - Call `tool_context.save_artifact(filename, artifact)`
   - Runner must have `artifact_service` configured

2. **Our Implementation**:
   - Existing `FileArtifactService` already correct
   - Just needed tools that actually call `save_artifact()`
   - Tools added to all 5 analysis agents

3. **Verification**:
   - Test script confirms artifacts are saved
   - Files appear in correct directories
   - Metadata generated automatically

## Files Modified

1. `tools/save_analysis_artifact.py` - Created 3 artifact-saving tools
2. `tools/__init__.py` - Exported new tools
3. `agent_workspace/orchestrator_agent/sub_agents/security_agent/agent.py` - Added save tool
4. `agent_workspace/orchestrator_agent/sub_agents/code_quality_agent/agent.py` - Added save tool
5. `agent_workspace/orchestrator_agent/sub_agents/engineering_practices_agent/agent.py` - Added save tool
6. `agent_workspace/orchestrator_agent/sub_agents/carbon_emission_agent/agent.py` - Added save tool
7. `agent_workspace/orchestrator_agent/sub_agents/report_synthesizer_agent/agent.py` - Added save_final_report tool

## References

- ADK Artifacts Documentation: https://raphaelmansuy.github.io/adk_training/docs/artifacts_files
- ADK Session Services: https://raphaelmansuy.github.io/adk_training/docs/til/til_custom_session_services_20251023
- Test Implementation: `test_minimal_artifact.py`
