# Cache Directory

**Status:** Phase 2 - Not Implemented

## Purpose

This directory is reserved for content-hash based caching to avoid redundant LLM calls for duplicate code submissions.

## Implementation Status

- ✅ Infrastructure exists: `util/result_cache.py` with `SimpleResultCache` class
- ❌ **Not integrated** into orchestrator or agents
- ❌ **Not in use** currently

## How It Would Work (Phase 2)

```python
# Before running analysis
cache = get_cache()
cached_result = cache.get(code, analysis_type="full")
if cached_result:
    return cached_result  # Skip LLM call

# After analysis
cache.set(code, analysis_type="full", result=analysis_output)
```

## Why Not Phase 1?

1. **Artifacts serve as permanent storage** - Historical lookups available via `analysis_id`
2. **Sessions handle in-conversation state** - ADK manages agent outputs within a session
3. **Cache is for deduplication only** - Only valuable if duplicate code submissions occur
4. **Added complexity** - Requires hash computation, TTL management, eviction policies

## Phase 2 Integration Plan

When implementing:
1. Add cache lookup in orchestrator before running analysis agents
2. Compute content hash of submitted code
3. Check cache for existing results (within TTL)
4. Store results after successful analysis
5. Add cache statistics to metrics/observability
6. Consider Redis for distributed caching in production

## Current Alternatives

- **Artifacts**: Long-term storage at `agent_workspace/artifacts/`
- **Sessions**: Conversation state at `agent_workspace/sessions/`

Both provide persistence without the need for deduplication caching in Phase 1.
