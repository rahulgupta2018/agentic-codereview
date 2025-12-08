# Session Database Schema Documentation

## Overview

Google ADK uses a relational database to store session state, user state, and interaction events. This document describes the schema, configuration options, and production deployment strategies.

## Database Schema

### Tables

#### 1. `app_states`
Stores global application-level state.

```sql
CREATE TABLE app_states (
    app_name TEXT PRIMARY KEY,      -- Agent application name (e.g., 'orchestrator_agent')
    state TEXT NOT NULL,             -- JSON serialized state
    update_time REAL NOT NULL        -- Unix timestamp of last update
);
```

**Example Row:**
```json
{
  "app_name": "orchestrator_agent",
  "state": "{\"config\": {\"version\": \"1.0\"}}",
  "update_time": 1733616000.0
}
```

#### 2. `user_states`
Stores per-user state across sessions.

```sql
CREATE TABLE user_states (
    app_name TEXT NOT NULL,          -- Agent application name
    user_id TEXT NOT NULL,           -- User identifier
    state TEXT NOT NULL,             -- JSON serialized user state
    update_time REAL NOT NULL,       -- Unix timestamp of last update
    PRIMARY KEY (app_name, user_id)
);
```

**Example Row:**
```json
{
  "app_name": "orchestrator_agent",
  "user_id": "github_user_123",
  "state": "{\"preferences\": {\"theme\": \"dark\"}}",
  "update_time": 1733616100.0
}
```

#### 3. `sessions`
Stores individual conversation/review sessions.

```sql
CREATE TABLE sessions (
    app_name TEXT NOT NULL,          -- Agent application name
    user_id TEXT NOT NULL,           -- User identifier
    id TEXT NOT NULL,                -- Session UUID (e.g., 'cbc6e7eb-c7be-4e28-85cc-3569627f7e0a')
    state TEXT NOT NULL,             -- JSON serialized session state
    create_time REAL NOT NULL,       -- Unix timestamp when session created
    update_time REAL NOT NULL,       -- Unix timestamp of last update
    PRIMARY KEY (app_name, user_id, id)
);
```

**Example Row:**
```json
{
  "app_name": "orchestrator_agent",
  "user_id": "testuser",
  "id": "cbc6e7eb-c7be-4e28-85cc-3569627f7e0a",
  "state": "{\"pr_number\": 42, \"repo\": \"owner/repo\"}",
  "create_time": 1733616108.0,
  "update_time": 1733616200.0
}
```

#### 4. `events`
Stores interaction events within sessions (messages, tool calls, agent responses).

```sql
CREATE TABLE events (
    id TEXT NOT NULL,                -- Event UUID
    app_name TEXT NOT NULL,          -- Agent application name
    user_id TEXT NOT NULL,           -- User identifier
    session_id TEXT NOT NULL,        -- Session UUID (foreign key)
    invocation_id TEXT NOT NULL,     -- Invocation tracking ID
    timestamp REAL NOT NULL,         -- Unix timestamp when event occurred
    event_data TEXT NOT NULL,        -- JSON serialized event data
    PRIMARY KEY (app_name, user_id, session_id, id),
    FOREIGN KEY (app_name, user_id, session_id) 
        REFERENCES sessions(app_name, user_id, id) 
        ON DELETE CASCADE
);
```

**Example Row:**
```json
{
  "id": "event_abc123",
  "app_name": "orchestrator_agent",
  "user_id": "testuser",
  "session_id": "cbc6e7eb-c7be-4e28-85cc-3569627f7e0a",
  "invocation_id": "inv_xyz789",
  "timestamp": 1733616150.0,
  "event_data": "{\"type\": \"user_message\", \"content\": \"Review this PR\"}"
}
```

## Configuration by Environment

### Development (SQLite)

**Location:** `/Users/rahulgupta/Documents/Coding/agentic-codereview/data/sessions/sessions.db`

**Pros:**
- ✅ No external dependencies
- ✅ File-based, easy to backup
- ✅ Perfect for local development
- ✅ Fast for single-user scenarios

**Cons:**
- ❌ Not suitable for production
- ❌ No concurrent write support
- ❌ Limited to single server
- ❌ No replication

**Configuration:**
```bash
adk api_server \
  --session_service_uri "sqlite:///$(pwd)/data/sessions/sessions.db" \
  .
```

### Staging (PostgreSQL on Docker)

**Setup:**
```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: adk_sessions
      POSTGRES_USER: adk_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
volumes:
  postgres_data:
```

**Pros:**
- ✅ Production-like environment
- ✅ Concurrent writes supported
- ✅ ACID compliance
- ✅ Can test replication

**Cons:**
- ⚠️ Requires Docker
- ⚠️ More complex setup

**Configuration:**
```bash
adk api_server \
  --session_service_uri "postgresql://adk_user:${DB_PASSWORD}@localhost:5432/adk_sessions" \
  .
```

### Production (Cloud SQL / Managed PostgreSQL)

#### Option 1: Google Cloud SQL (Recommended for GCP)

**Pros:**
- ✅ Fully managed by Google
- ✅ Automatic backups
- ✅ High availability
- ✅ Automatic failover
- ✅ Integrated with GCP IAM
- ✅ Private IP for security

**Setup:**
1. Create Cloud SQL instance:
```bash
gcloud sql instances create adk-sessions \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --backup \
  --backup-start-time=03:00
```

2. Create database:
```bash
gcloud sql databases create adk_sessions \
  --instance=adk-sessions
```

3. Create user:
```bash
gcloud sql users create adk_user \
  --instance=adk-sessions \
  --password=${DB_PASSWORD}
```

**Configuration:**
```bash
# Using Cloud SQL Proxy
cloud_sql_proxy -instances=PROJECT:REGION:adk-sessions=tcp:5432 &

adk api_server \
  --session_service_uri "postgresql://adk_user:${DB_PASSWORD}@localhost:5432/adk_sessions" \
  --trace_to_cloud \
  .
```

**Connection String Format:**
```
postgresql://USER:PASSWORD@/DATABASE?host=/cloudsql/PROJECT:REGION:INSTANCE
```

#### Option 2: AWS RDS PostgreSQL

**Pros:**
- ✅ Fully managed by AWS
- ✅ Multi-AZ deployment
- ✅ Read replicas
- ✅ Automatic backups

**Setup:**
```bash
aws rds create-db-instance \
  --db-instance-identifier adk-sessions \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.3 \
  --master-username adk_user \
  --master-user-password ${DB_PASSWORD} \
  --allocated-storage 20 \
  --backup-retention-period 7 \
  --multi-az
```

**Configuration:**
```bash
adk api_server \
  --session_service_uri "postgresql://adk_user:${DB_PASSWORD}@adk-sessions.xxxxx.us-east-1.rds.amazonaws.com:5432/adk_sessions" \
  .
```

#### Option 3: Azure Database for PostgreSQL

**Setup:**
```bash
az postgres flexible-server create \
  --resource-group adk-rg \
  --name adk-sessions \
  --location eastus \
  --admin-user adk_user \
  --admin-password ${DB_PASSWORD} \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 15
```

**Configuration:**
```bash
adk api_server \
  --session_service_uri "postgresql://adk_user:${DB_PASSWORD}@adk-sessions.postgres.database.azure.com:5432/adk_sessions?sslmode=require" \
  .
```

#### Option 4: Agent Engine Sessions (Google Cloud)

**For Google Cloud deployments**, use Agent Engine's built-in session management:

```bash
adk api_server \
  --session_service_uri "agentengine://projects/PROJECT_ID/locations/REGION/reasoningEngines/ENGINE_ID" \
  .
```

**Pros:**
- ✅ No database management needed
- ✅ Fully integrated with Google Cloud
- ✅ Automatic scaling
- ✅ Built-in tracing

## Database Initialization

ADK automatically creates tables on first run. No manual schema creation needed!

**First Run:**
```bash
adk api_server --session_service_uri "sqlite:///./data/sessions/sessions.db" .
```

ADK will:
1. Create database file if it doesn't exist
2. Create all tables with proper schema
3. Set up indexes for performance
4. Enable foreign key constraints

## Connection Pooling

For production PostgreSQL deployments, ADK uses SQLAlchemy connection pooling:

**Default Settings:**
- Pool size: 5 connections
- Max overflow: 10 connections
- Pool timeout: 30 seconds
- Pool recycle: 3600 seconds

**Custom Configuration:**
```python
# Set via environment variables
export SQLALCHEMY_POOL_SIZE=20
export SQLALCHEMY_MAX_OVERFLOW=30
export SQLALCHEMY_POOL_TIMEOUT=60
```

## Backup Strategies

### SQLite (Development)
```bash
# Simple file copy
cp data/sessions/sessions.db data/sessions/sessions.db.backup

# Or use SQLite backup command
sqlite3 data/sessions/sessions.db ".backup 'backup/sessions_$(date +%Y%m%d).db'"
```

### PostgreSQL (Production)

#### Automated Backups (Cloud SQL)
```bash
# Cloud SQL automatically backs up daily
# Restore to a point in time:
gcloud sql backups restore BACKUP_ID \
  --backup-instance=adk-sessions \
  --backup-instance=adk-sessions
```

#### Manual pg_dump
```bash
# Full backup
pg_dump -h HOST -U adk_user -d adk_sessions > backup_$(date +%Y%m%d).sql

# Restore
psql -h HOST -U adk_user -d adk_sessions < backup_20251207.sql
```

## Monitoring & Maintenance

### Query Performance

**Index Coverage:**
```sql
-- Check if indexes exist
SELECT tablename, indexname, indexdef 
FROM pg_indexes 
WHERE schemaname = 'public';

-- Sessions by user query (should use index)
EXPLAIN ANALYZE 
SELECT * FROM sessions 
WHERE app_name = 'orchestrator_agent' 
  AND user_id = 'testuser';
```

### Database Size Monitoring

**SQLite:**
```bash
ls -lh data/sessions/sessions.db
```

**PostgreSQL:**
```sql
-- Database size
SELECT pg_size_pretty(pg_database_size('adk_sessions'));

-- Table sizes
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Cleanup Old Sessions

```sql
-- Delete sessions older than 30 days
DELETE FROM sessions 
WHERE update_time < EXTRACT(EPOCH FROM NOW() - INTERVAL '30 days');

-- Events are automatically deleted due to CASCADE
```

## Security Best Practices

### 1. Connection Security

**PostgreSQL SSL:**
```bash
adk api_server \
  --session_service_uri "postgresql://user:pass@host:5432/db?sslmode=require" \
  .
```

### 2. Credential Management

**Use environment variables:**
```bash
export DB_USER=adk_user
export DB_PASSWORD=$(cat /secrets/db_password)
export DB_HOST=adk-sessions.xxxxx.rds.amazonaws.com

adk api_server \
  --session_service_uri "postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:5432/adk_sessions" \
  .
```

**Or Google Secret Manager:**
```bash
export DB_PASSWORD=$(gcloud secrets versions access latest --secret=adk-db-password)
```

### 3. Network Security

**Cloud SQL Private IP:**
```bash
gcloud sql instances patch adk-sessions \
  --network=projects/PROJECT/global/networks/VPC_NAME \
  --no-assign-ip
```

## Disaster Recovery

### RTO/RPO Targets

| Environment | RTO (Recovery Time) | RPO (Recovery Point) | Strategy |
|-------------|---------------------|----------------------|----------|
| Development | 1 hour | 24 hours | Daily SQLite backups |
| Staging | 30 minutes | 1 hour | Automated PostgreSQL backups |
| Production | 5 minutes | 5 minutes | Cloud SQL HA + Point-in-time recovery |

### High Availability Setup

**Cloud SQL with Failover:**
```bash
gcloud sql instances create adk-sessions \
  --database-version=POSTGRES_15 \
  --tier=db-custom-2-7680 \
  --region=us-central1 \
  --availability-type=REGIONAL \  # Multi-zone HA
  --backup \
  --enable-bin-log \
  --enable-point-in-time-recovery
```

## Migration Path

### Dev → Staging → Production

```bash
# 1. Development (SQLite)
adk api_server --session_service_uri "sqlite:///./data/sessions/sessions.db" .

# 2. Staging (Local PostgreSQL)
adk api_server --session_service_uri "postgresql://localhost:5432/adk_sessions" .

# 3. Production (Cloud SQL)
adk api_server --session_service_uri "postgresql://prod.host:5432/adk_sessions?sslmode=require" .
```

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Development                          │
│  SQLite: data/sessions/sessions.db                      │
│  ✓ Local file                                           │
│  ✓ No dependencies                                      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                      Staging                             │
│  PostgreSQL on Docker Compose                           │
│  ✓ Production-like                                      │
│  ✓ Test migrations                                      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                     Production                           │
│  Google Cloud SQL (Multi-zone HA)                       │
│  ✓ Automatic backups                                    │
│  ✓ Point-in-time recovery                               │
│  ✓ Automatic failover                                   │
│  ✓ Read replicas                                        │
└─────────────────────────────────────────────────────────┘
```

## Cost Estimates (Monthly)

| Option | Cost | Use Case |
|--------|------|----------|
| SQLite | $0 | Development only |
| PostgreSQL (Docker) | $0 | Staging/testing |
| Cloud SQL (db-f1-micro) | ~$10 | Small production |
| Cloud SQL (db-custom-2-7680) | ~$100 | Production HA |
| Cloud SQL (db-custom-8-30720) | ~$400 | High-traffic production |

## References

- [ADK Session Service Documentation](https://github.com/googleapis/genai-agent-dev-kit)
- [Cloud SQL Pricing](https://cloud.google.com/sql/pricing)
- [SQLAlchemy Database URLs](https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls)
- [PostgreSQL High Availability](https://www.postgresql.org/docs/current/high-availability.html)

---

**Decision**: Use SQLite for development, PostgreSQL for staging, and Cloud SQL for production.
