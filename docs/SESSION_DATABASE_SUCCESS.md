# ✅ Session Database - Properly Configured

## Success Summary

The session database is now properly organized and configured with production-ready structure.

## ✅ What Was Accomplished

### 1. Database Location - Properly Organized
```
OLD (Incorrect):
❌ /Users/rahulgupta/Documents/Coding/agentic-codereview/agent_workspace/sessions.db

NEW (Correct):
✅ /Users/rahulgupta/Documents/Coding/agentic-codereview/data/sessions/sessions.db
```

**Benefits:**
- Clear separation of data from code
- Follows standard project structure conventions
- Easy to backup/restore
- Excluded from git via .gitignore

### 2. Database Schema - Verified Working

**Tables Created:**
```sql
✅ app_states   - Global application state
✅ user_states  - Per-user state across sessions
✅ sessions     - Individual conversation/review sessions
✅ events       - Interaction events within sessions
```

**Test Query Result:**
```bash
$ sqlite3 data/sessions/sessions.db "SELECT app_name, user_id, id, state FROM sessions;"

orchestrator_agent|testuser|4d68ccb1-f798-4c02-9c61-86df509ea90a|{"test": "proper_location"}
```

### 3. Configuration Files Created

#### `.env` (Active Configuration)
```bash
ENVIRONMENT=development
GEMINI_API_KEY=AIzaSyDG1WH01KTYXHkKvSDE0Ps-B7Edtv1hTbU
GEMINI_MODEL=gemini-2.5-flash
# SESSION_DB_URI not set = defaults to SQLite at data/sessions/sessions.db
```

#### `.env.example` (Template)
- Development: SQLite (default)
- Staging: PostgreSQL on Docker
- Production: Cloud SQL / RDS / Azure

#### `docker-compose.yml`
- PostgreSQL 15 for staging
- PgAdmin for database management
- Configurable via environment variables

#### `.gitignore`
```bash
# Properly excludes:
data/sessions/*.db
*.db-journal
*.db-wal
.env
.env.local
```

### 4. Scripts Updated

**`start_adk_api_server.sh`:**
- ✅ Uses `data/sessions/sessions.db` by default
- ✅ Respects `SESSION_DB_URI` environment variable
- ✅ Creates `data/sessions/` directory automatically
- ✅ Fixed health check (uses `/docs` endpoint)

### 5. Documentation Created

| File | Purpose |
|------|---------|
| `docs/SESSION_DATABASE_SCHEMA.md` | Complete schema documentation |
| `docs/SESSION_DATABASE_CONFIG.md` | Environment-specific configurations |
| `docker-compose.yml` | Staging PostgreSQL setup |
| `Dockerfile.api` | Containerized deployment |

## 📊 Database Schema Details

### Tables Structure

```sql
-- Application-level state
CREATE TABLE app_states (
    app_name TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    update_time REAL NOT NULL
);

-- Per-user state
CREATE TABLE user_states (
    app_name TEXT NOT NULL,
    user_id TEXT NOT NULL,
    state TEXT NOT NULL,
    update_time REAL NOT NULL,
    PRIMARY KEY (app_name, user_id)
);

-- Sessions (conversations/reviews)
CREATE TABLE sessions (
    app_name TEXT NOT NULL,
    user_id TEXT NOT NULL,
    id TEXT NOT NULL,                -- UUID
    state TEXT NOT NULL,             -- JSON state
    create_time REAL NOT NULL,
    update_time REAL NOT NULL,
    PRIMARY KEY (app_name, user_id, id)
);

-- Events within sessions
CREATE TABLE events (
    id TEXT NOT NULL,
    app_name TEXT NOT NULL,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    invocation_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    event_data TEXT NOT NULL,        -- JSON event data
    PRIMARY KEY (app_name, user_id, session_id, id),
    FOREIGN KEY (app_name, user_id, session_id) 
        REFERENCES sessions(app_name, user_id, id) 
        ON DELETE CASCADE
);
```

## 🚀 Usage by Environment

### Development (Current - SQLite)
```bash
# Default - no configuration needed
./scripts/start_adk_api_server.sh

# Database location
ls -lh data/sessions/sessions.db
```

### Staging (PostgreSQL on Docker)
```bash
# 1. Start PostgreSQL
docker-compose up -d postgres

# 2. Set environment variable
export SESSION_DB_URI="postgresql://adk_user:devpassword@localhost:5432/adk_sessions"

# 3. Start server
./scripts/start_adk_api_server.sh

# 4. (Optional) Access PgAdmin
open http://localhost:5050
```

### Production (Cloud SQL - Google Cloud)
```bash
# 1. Create Cloud SQL instance
gcloud sql instances create adk-sessions \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --availability-type=REGIONAL \
  --backup

# 2. Create database and user
gcloud sql databases create adk_sessions --instance=adk-sessions
gcloud sql users create adk_user --instance=adk-sessions --password=SECURE_PASSWORD

# 3. Store password in Secret Manager
echo -n "SECURE_PASSWORD" | gcloud secrets create adk-db-password --data-file=-

# 4. Start Cloud SQL Proxy
cloud_sql_proxy -instances=PROJECT:REGION:adk-sessions=tcp:5432 &

# 5. Set environment variable
export DB_PASSWORD=$(gcloud secrets versions access latest --secret=adk-db-password)
export SESSION_DB_URI="postgresql://adk_user:${DB_PASSWORD}@localhost:5432/adk_sessions"

# 6. Start server
./scripts/start_adk_api_server.sh
```

### Production (AWS RDS)
```bash
# 1. Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier adk-sessions \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.3 \
  --master-username adk_user \
  --master-user-password SECURE_PASSWORD \
  --allocated-storage 20 \
  --backup-retention-period 7 \
  --multi-az

# 2. Get endpoint
aws rds describe-db-instances \
  --db-instance-identifier adk-sessions \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text

# 3. Set environment variable
export SESSION_DB_URI="postgresql://adk_user:SECURE_PASSWORD@ENDPOINT:5432/adk_sessions?sslmode=require"

# 4. Start server
./scripts/start_adk_api_server.sh
```

## 🔍 Verification Commands

### Check Database Location
```bash
ls -lh data/sessions/sessions.db
```

### View Schema
```bash
sqlite3 data/sessions/sessions.db ".schema"
```

### View All Sessions
```bash
sqlite3 data/sessions/sessions.db "SELECT * FROM sessions;"
```

### View Table Sizes
```bash
sqlite3 data/sessions/sessions.db "
SELECT 
    'app_states' as table_name, COUNT(*) as count FROM app_states
UNION ALL
SELECT 'user_states', COUNT(*) FROM user_states
UNION ALL
SELECT 'sessions', COUNT(*) FROM sessions
UNION ALL
SELECT 'events', COUNT(*) FROM events;
"
```

### Test API
```bash
# Create session
curl -X POST http://localhost:8000/apps/orchestrator_agent/users/testuser/sessions \
  -H "Content-Type: application/json" \
  -d '{"state": {}}'

# List sessions
curl http://localhost:8000/apps/orchestrator_agent/users/testuser/sessions
```

## 📦 Backup & Restore

### SQLite (Development)
```bash
# Backup
cp data/sessions/sessions.db data/sessions/sessions.db.$(date +%Y%m%d_%H%M%S)

# Restore
cp data/sessions/sessions.db.20251207_224100 data/sessions/sessions.db
```

### PostgreSQL (Production)
```bash
# Backup
pg_dump -h HOST -U adk_user adk_sessions | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore
gunzip -c backup_20251207.sql.gz | psql -h HOST -U adk_user adk_sessions
```

## 🔒 Security Best Practices

### 1. Git Exclusion
```bash
# .gitignore includes:
data/sessions/*.db
*.db-journal
.env
```

### 2. Environment Variables
```bash
# Never commit credentials
# Use .env (gitignored) for local
# Use Secret Manager for production
```

### 3. Database Permissions
```bash
# SQLite
chmod 600 data/sessions/sessions.db

# PostgreSQL
# Use IAM authentication for Cloud SQL
# Use SSL for all remote connections
```

## 📊 Monitoring

### Database Size
```bash
# SQLite
du -h data/sessions/sessions.db

# PostgreSQL
psql -h HOST -U adk_user -d adk_sessions -c "
SELECT pg_size_pretty(pg_database_size('adk_sessions'));"
```

### Active Sessions
```bash
# SQLite
sqlite3 data/sessions/sessions.db "
SELECT COUNT(*) as active_sessions FROM sessions 
WHERE update_time > unixepoch('now') - 3600;"  -- Updated in last hour

# PostgreSQL
psql -h HOST -U adk_user -d adk_sessions -c "
SELECT COUNT(*) FROM sessions 
WHERE update_time > EXTRACT(EPOCH FROM NOW() - INTERVAL '1 hour');"
```

## 🎯 Production Deployment Checklist

- [ ] Choose database backend (Cloud SQL / RDS / Azure)
- [ ] Create database instance with HA enabled
- [ ] Set up automated backups
- [ ] Configure point-in-time recovery
- [ ] Store credentials in Secret Manager
- [ ] Enable SSL/TLS connections
- [ ] Set up connection pooling
- [ ] Configure monitoring and alerts
- [ ] Test failover procedure
- [ ] Document recovery procedures

## 📚 References

- **Schema Documentation**: [docs/SESSION_DATABASE_SCHEMA.md](./SESSION_DATABASE_SCHEMA.md)
- **Configuration Guide**: [docs/SESSION_DATABASE_CONFIG.md](./SESSION_DATABASE_CONFIG.md)
- **ADK Session Service**: https://github.com/googleapis/genai-agent-dev-kit
- **SQLAlchemy Database URLs**: https://docs.sqlalchemy.org/en/20/core/engines.html

---

**Status**: ✅ Session database properly configured at `data/sessions/sessions.db`
**Date**: 2025-12-07
**Environment**: Development (SQLite)
**Next**: Test with staging PostgreSQL before production deployment
