# Phase 2: Production Scaling Plan

## Overview
This document outlines the scaling strategy for moving from MVP (low volume) to production (high volume) for the AI Code Review Multi-Agent System.

## Current MVP Implementation (Phase 1) ✅

### What's Already Working:
1. **Intelligent Agent Orchestration**
   - Classifier-based selective agent invocation
   - Only runs relevant agents based on user request
   - Reduces unnecessary LLM calls by ~60-80%

2. **Result Caching**
   - File-based cache with TTL (1 hour default)
   - Content-hash based deduplication
   - Avoids redundant analysis for identical code

3. **Code Optimization**
   - Automatic comment/docstring stripping for large files
   - Token reduction ~20-30% for typical codebases
   - Optimizes LLM input without losing code logic

4. **Artifact Storage & Session Management**
   - Persistent storage for code inputs, reports, analysis outputs
   - Session state tracking with analysis history
   - Service registry pattern for loose coupling

5. **Error Handling**
   - JSON parsing with markdown fence stripping
   - Graceful degradation when services unavailable
   - Built-in retry logic via ADK/tenacity

### Current Limitations:
- No request queuing (requests block on API availability)
- No advanced rate limiting (relies on API-level limits)
- No load-aware scheduling
- No metrics/monitoring infrastructure
- File-based cache (not suitable for multi-instance deployments)

---

## Phase 2: High-Volume Production Features

### 1. **Request Queuing & Priority System** 🚦

**Problem:** Multiple concurrent users can overwhelm API quota
**Solution:** Async request queue with priority levels

#### Implementation:
```python
# util/request_queue.py
class PriorityRequestQueue:
    """
    Async priority queue for LLM requests
    - HIGH: Production PRs, critical security reviews
    - MEDIUM: Standard code reviews
    - LOW: Experimental/learning requests
    """
    
    async def enqueue(request, priority="MEDIUM")
    async def process_queue()  # Background worker
    async def get_queue_stats()
```

**Tech Stack:**
- **Simple**: Python `asyncio.Queue` + priority handling
- **Production**: Redis Queue (RQ) or Celery for distributed task processing

**Metrics to Track:**
- Queue depth by priority
- Average wait time
- Throughput (requests/minute)

---

### 2. **Advanced Rate Limiting** ⏱️

**Problem:** Need fine-grained control over API usage per user/tenant
**Solution:** Token bucket algorithm with per-user limits

#### Implementation:
```python
# util/rate_limiter.py
class TokenBucketRateLimiter:
    """
    - 100 requests/minute per user (configurable)
    - Burst capacity: 10 requests
    - Refill rate: 1.67 tokens/second
    """
    
    async def acquire(user_id: str) -> bool
    async def get_user_quota(user_id: str) -> dict
```

**Storage:**
- **MVP Phase 2**: In-memory with periodic persistence
- **Production**: Redis for distributed rate limiting

**Features:**
- Per-user quotas
- Tenant-level limits (for enterprise customers)
- Graceful rejection with retry-after headers

---

### 3. **Distributed Caching** 🗄️

**Problem:** File-based cache doesn't work across multiple instances
**Solution:** Redis-backed distributed cache

#### Implementation:
```python
# util/distributed_cache.py
class RedisResultCache:
    """
    Redis-backed cache with:
    - Automatic expiration (TTL)
    - LRU eviction policy
    - Cluster support for high availability
    """
    
    def get(code: str, analysis_type: str) -> Optional[dict]
    def set(code: str, analysis_type: str, result: dict, ttl: int = 3600)
    def invalidate(pattern: str)  # For cache busting
```

**Benefits:**
- Shared cache across all instances
- Faster lookup than file-based
- Built-in expiration and eviction

**Redis Configuration:**
```yaml
# docker-compose.yml
redis:
  image: redis:7-alpine
  command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
  ports:
    - "6379:6379"
```

---

### 4. **Load-Aware Scheduling** 📊

**Problem:** System continues to make requests even when APIs are overloaded
**Solution:** Circuit breaker pattern with adaptive throttling

#### Implementation:
```python
# util/circuit_breaker.py
class APICircuitBreaker:
    """
    States: CLOSED (normal) -> OPEN (failing) -> HALF_OPEN (testing)
    
    Triggers:
    - 429 (rate limit) -> Reduce QPS by 50%
    - 503 (unavailable) -> Open circuit for 30s
    - Success in HALF_OPEN -> Close circuit
    """
    
    async def call_with_protection(api_fn, *args, **kwargs)
    def get_circuit_state() -> str
    def get_failure_rate() -> float
```

**Adaptive Throttling:**
- Start at 100% QPS
- On 429: Reduce to 50% → 25% → 10%
- On success: Gradually increase 10% → 25% → 50% → 100%
- Exponential backoff with jitter

---

### 5. **Metrics & Observability** 📈

**Problem:** No visibility into system performance and bottlenecks
**Solution:** Comprehensive monitoring with Prometheus + Grafana

#### Metrics to Collect:
```python
# util/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
requests_total = Counter('code_review_requests_total', 'Total requests', ['type', 'status'])
request_duration = Histogram('code_review_duration_seconds', 'Request duration')

# LLM metrics
llm_tokens_used = Counter('llm_tokens_total', 'Total tokens consumed', ['agent', 'model'])
llm_api_errors = Counter('llm_api_errors_total', 'API errors', ['error_type'])

# Cache metrics
cache_hits = Counter('cache_hits_total', 'Cache hits')
cache_misses = Counter('cache_misses_total', 'Cache misses')

# Queue metrics
queue_depth = Gauge('request_queue_depth', 'Current queue depth', ['priority'])
queue_wait_time = Histogram('queue_wait_seconds', 'Time in queue')
```

#### Dashboard Panels:
1. **Request Volume**: Requests/min by type
2. **Success Rate**: % successful vs failed requests
3. **API Health**: Error rate by error type (429, 503, etc.)
4. **Cache Performance**: Hit rate over time
5. **Token Usage**: Daily/monthly consumption trends
6. **Response Time**: P50, P95, P99 latencies
7. **Queue Status**: Depth and wait times by priority

**Alerting Rules:**
- Error rate > 10% for 5 minutes
- Average response time > 30 seconds
- Queue depth > 100 requests
- API quota usage > 80% of limit

---

### 6. **Batch Processing** 📦

**Problem:** Reviewing multiple files one-by-one is inefficient
**Solution:** Batch API calls when analyzing multiple files

#### Implementation:
```python
# orchestrator/batch_processor.py
class BatchCodeReviewer:
    """
    Group multiple code files into single API call
    - Max batch size: 10 files or 50K tokens
    - Parallel batching for multiple agents
    """
    
    async def review_batch(files: List[CodeFile]) -> Dict[str, AnalysisResult]
```

**Use Cases:**
- Pull request with 20 changed files
- Reviewing entire module/package
- Periodic codebase health scans

**Optimization:**
- Group small files together
- Process large files individually
- Respect token limits per batch

---

### 7. **Horizontal Scaling** 🚀

**Problem:** Single instance can't handle 100+ concurrent users
**Solution:** Load-balanced multi-instance deployment

#### Architecture:
```
                    ┌─────────────┐
                    │  Load       │
                    │  Balancer   │
                    │  (nginx)    │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
    │  ADK App  │   │  ADK App  │   │  ADK App  │
    │ Instance1 │   │ Instance2 │   │ Instance3 │
    └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
          │                │                │
          └────────────────┼────────────────┘
                           │
                    ┌──────▼──────┐
                    │   Redis     │ (cache + queue)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  PostgreSQL │ (sessions + artifacts)
                    └─────────────┘
```

**Required Changes:**
1. Replace file-based services with database-backed:
   - `FileArtifactService` → `S3ArtifactService` or `DatabaseArtifactService`
   - `JSONFileSessionService` → `PostgreSQLSessionService`
2. Use Redis for cache and request queue
3. Stateless application instances (all state in DB/Redis)

**Deployment:**
```yaml
# docker-compose.prod.yml
services:
  app:
    image: code-review-system:latest
    deploy:
      replicas: 3
    environment:
      REDIS_URL: redis://redis:6379
      DATABASE_URL: postgresql://postgres:5432/codereview
  
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

---

## Implementation Priority

### Immediate (Next Sprint):
1. ✅ Code optimization (Done)
2. ✅ Result caching (Done)
3. 🔄 **Metrics collection** (Quick win, use existing Prometheus client)
4. 🔄 **Circuit breaker** (Protect against API overload)

### Short-term (1-2 months):
5. Request queue with priority
6. Advanced rate limiting per user
7. Grafana dashboards

### Medium-term (3-6 months):
8. Redis distributed cache
9. Batch processing for multi-file reviews
10. Load-aware adaptive scheduling

### Long-term (6-12 months):
11. Horizontal scaling infrastructure
12. Database-backed services
13. Multi-region deployment

---

## Cost-Benefit Analysis

### Phase 1 MVP (Current):
- **Cost**: ~$50-200/month (Gemini API free tier + basic hosting)
- **Capacity**: 10-50 users, 100-500 reviews/day
- **Suitable for**: Proof of concept, small teams

### Phase 2 Initial (Queue + Metrics):
- **Cost**: ~$200-500/month (API + Redis + monitoring)
- **Capacity**: 100-500 users, 1K-5K reviews/day
- **Suitable for**: Growing startup, medium teams

### Phase 2 Full (Distributed + Scaling):
- **Cost**: ~$1K-3K/month (Multi-instance + DB + observability)
- **Capacity**: 1K-10K users, 10K-50K reviews/day
- **Suitable for**: Enterprise deployment

---

## Success Metrics

### Phase 1 → Phase 2 Transition Criteria:
- [ ] Average queue wait time > 30 seconds
- [ ] Daily API quota usage > 80%
- [ ] Error rate > 5% due to rate limiting
- [ ] User complaints about slow response times

### Phase 2 Success Indicators:
- [ ] P95 response time < 10 seconds
- [ ] Cache hit rate > 40%
- [ ] API error rate < 2%
- [ ] Zero downtime during peak hours
- [ ] Successful handling of 10x traffic spike

---

## Testing Strategy

### Load Testing:
```python
# tests/load/test_concurrent_users.py
async def test_100_concurrent_reviews():
    """Simulate 100 users submitting code simultaneously"""
    tasks = [submit_review(f"user_{i}") for i in range(100)]
    results = await asyncio.gather(*tasks)
    assert all(r.status == "success" for r in results)
```

### Chaos Engineering:
- Simulate API failures (429, 503 errors)
- Kill random instances during load
- Network partition between app and Redis
- Database connection pool exhaustion

---

## Migration Path

### Step 1: Add Metrics (No Breaking Changes)
```bash
pip install prometheus-client
# Add metrics to existing code
```

### Step 2: Add Redis (Optional Fallback)
```bash
# Install Redis
docker run -d -p 6379:6379 redis:7-alpine

# Update cache to try Redis, fallback to file-based
if redis_available:
    cache = RedisResultCache()
else:
    cache = SimpleResultCache()  # existing
```

### Step 3: Enable Queue (Gradual Rollout)
```python
# Feature flag
ENABLE_REQUEST_QUEUE = os.getenv("ENABLE_REQUEST_QUEUE", "false") == "true"

if ENABLE_REQUEST_QUEUE:
    await queue.enqueue(request)
else:
    await process_request(request)  # direct processing
```

### Step 4: Multi-Instance Deployment
```bash
# Test with 2 instances
docker-compose up --scale app=2

# Monitor metrics, adjust configuration
# Scale to 3, then 5 instances
```

---

## Conclusion

**Current MVP is production-ready for**:
- Low-volume deployments (< 100 users)
- Internal team usage
- Proof of concept / beta testing

**Phase 2 features unlock**:
- High-volume production (1000+ users)
- Enterprise SLA requirements
- Multi-tenant deployments
- Geographic distribution

**Recommendation**: Deploy MVP now, monitor metrics, implement Phase 2 features based on actual usage patterns and bottlenecks observed in production.
