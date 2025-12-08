# Session Database Configuration

## Environment-Specific Database URIs

Copy this file to `.env` and set your database credentials.

### Development (Default)
```bash
# SQLite - Local file-based database
# Location: data/sessions/sessions.db
SESSION_DB_URI="sqlite:///$(pwd)/data/sessions/sessions.db"
```

### Staging
```bash
# PostgreSQL on Docker
SESSION_DB_URI="postgresql://adk_user:YOUR_PASSWORD@localhost:5432/adk_sessions"
```

### Production Options

#### Option 1: Google Cloud SQL
```bash
# Cloud SQL with Cloud SQL Proxy
SESSION_DB_URI="postgresql://adk_user:YOUR_PASSWORD@localhost:5432/adk_sessions"

# Cloud SQL with Unix socket (recommended for GKE/Cloud Run)
SESSION_DB_URI="postgresql://adk_user:YOUR_PASSWORD@/adk_sessions?host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME"
```

#### Option 2: AWS RDS
```bash
SESSION_DB_URI="postgresql://adk_user:YOUR_PASSWORD@adk-sessions.xxxxx.us-east-1.rds.amazonaws.com:5432/adk_sessions?sslmode=require"
```

#### Option 3: Azure Database for PostgreSQL
```bash
SESSION_DB_URI="postgresql://adk_user@adk-sessions:YOUR_PASSWORD@adk-sessions.postgres.database.azure.com:5432/adk_sessions?sslmode=require"
```

#### Option 4: Google Agent Engine (Fully Managed)
```bash
# No database setup needed - managed by Google
SESSION_DB_URI="agentengine://projects/YOUR_PROJECT/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID"
```

## Quick Start

### 1. Development Setup (SQLite)
```bash
# No configuration needed - default in scripts
./scripts/start_adk_api_server.sh
```

### 2. Staging Setup (PostgreSQL on Docker)
```bash
# Start PostgreSQL
docker-compose up -d postgres

# Set environment variable
export SESSION_DB_URI="postgresql://adk_user:devpassword@localhost:5432/adk_sessions"

# Start server
./scripts/start_adk_api_server.sh
```

### 3. Production Setup (Cloud SQL)
```bash
# Option A: Use Cloud SQL Proxy
cloud_sql_proxy -instances=PROJECT:REGION:adk-sessions=tcp:5432 &

# Option B: Use Unix socket (GKE)
# (Cloud SQL Proxy sidecar automatically mounted)

# Set credentials from Secret Manager
export DB_PASSWORD=$(gcloud secrets versions access latest --secret=adk-db-password)
export SESSION_DB_URI="postgresql://adk_user:${DB_PASSWORD}@localhost:5432/adk_sessions"

# Start server
./scripts/start_adk_api_server.sh
```

## Docker Compose for Staging

Create `docker-compose.yml` in project root:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: adk-postgres
    environment:
      POSTGRES_DB: adk_sessions
      POSTGRES_USER: adk_user
      POSTGRES_PASSWORD: devpassword
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U adk_user -d adk_sessions"]
      interval: 10s
      timeout: 5s
      retries: 5

  pgadmin:
    image: dpage/pgadmin4
    container_name: adk-pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@example.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      - postgres

volumes:
  postgres_data:
```

Start with:
```bash
docker-compose up -d
```

Access PgAdmin: http://localhost:5050

## Cloud SQL Setup

### Google Cloud SQL

```bash
# 1. Create Cloud SQL instance
gcloud sql instances create adk-sessions \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --availability-type=REGIONAL \
  --backup \
  --backup-start-time=03:00 \
  --enable-bin-log \
  --enable-point-in-time-recovery

# 2. Create database
gcloud sql databases create adk_sessions \
  --instance=adk-sessions

# 3. Create user
gcloud sql users create adk_user \
  --instance=adk-sessions \
  --password=$(openssl rand -base64 32)

# 4. Store password in Secret Manager
echo -n "YOUR_PASSWORD" | gcloud secrets create adk-db-password --data-file=-

# 5. Grant access to Cloud SQL Client
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member=serviceAccount:SERVICE_ACCOUNT@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/cloudsql.client
```

### AWS RDS

```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier adk-sessions \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.3 \
  --master-username adk_user \
  --master-user-password $(openssl rand -base64 32) \
  --allocated-storage 20 \
  --storage-type gp2 \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --multi-az \
  --publicly-accessible false \
  --vpc-security-group-ids sg-xxxxx

# Store password in AWS Secrets Manager
aws secretsmanager create-secret \
  --name adk-db-password \
  --secret-string "YOUR_PASSWORD"
```

## Security Best Practices

### 1. Never Commit Credentials
```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo "*.db" >> .gitignore
echo "data/sessions/*.db" >> .gitignore
```

### 2. Use Secret Managers

**Google Cloud:**
```bash
export DB_PASSWORD=$(gcloud secrets versions access latest --secret=adk-db-password)
```

**AWS:**
```bash
export DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id adk-db-password --query SecretString --output text)
```

**Azure:**
```bash
export DB_PASSWORD=$(az keyvault secret show --name adk-db-password --vault-name YOUR_VAULT --query value -o tsv)
```

### 3. Use IAM Authentication (Cloud SQL)

```bash
# Enable IAM authentication
gcloud sql instances patch adk-sessions \
  --database-flags=cloudsql.iam_authentication=on

# Create IAM user
gcloud sql users create SERVICE_ACCOUNT@PROJECT_ID.iam \
  --instance=adk-sessions \
  --type=CLOUD_IAM_SERVICE_ACCOUNT

# Connect without password
SESSION_DB_URI="postgresql://SERVICE_ACCOUNT@PROJECT_ID.iam@/adk_sessions?host=/cloudsql/PROJECT:REGION:adk-sessions"
```

## Monitoring

### Health Checks

```bash
# SQLite
ls -lh data/sessions/sessions.db

# PostgreSQL
psql -h localhost -U adk_user -d adk_sessions -c "SELECT COUNT(*) FROM sessions;"
```

### Performance Monitoring

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity;

-- Database size
SELECT pg_size_pretty(pg_database_size('adk_sessions'));

-- Table sizes
SELECT tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE schemaname = 'public';

-- Slow queries (if pg_stat_statements enabled)
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

## Backup & Recovery

### SQLite (Development)

```bash
# Backup
cp data/sessions/sessions.db data/sessions/sessions.db.$(date +%Y%m%d_%H%M%S)

# Restore
cp data/sessions/sessions.db.20251207_120000 data/sessions/sessions.db
```

### PostgreSQL (Production)

```bash
# Backup
pg_dump -h HOST -U adk_user adk_sessions | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore
gunzip -c backup_20251207.sql.gz | psql -h HOST -U adk_user adk_sessions
```

### Cloud SQL Automated Backups

```bash
# List backups
gcloud sql backups list --instance=adk-sessions

# Create manual backup
gcloud sql backups create --instance=adk-sessions

# Restore from backup
gcloud sql backups restore BACKUP_ID --instance=adk-sessions
```

## Troubleshooting

### Connection Issues

```bash
# Test PostgreSQL connection
psql -h HOST -U adk_user -d adk_sessions -c "SELECT version();"

# Check Cloud SQL Proxy
cloud_sql_proxy -instances=PROJECT:REGION:adk-sessions=tcp:5432 -verbose

# Check ADK connection
adk api_server --session_service_uri "postgresql://..." --verbose .
```

### Performance Issues

```sql
-- Check for missing indexes
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public';

-- Analyze query plans
EXPLAIN ANALYZE SELECT * FROM sessions WHERE user_id = 'testuser';
```

## Migration Between Databases

### SQLite → PostgreSQL

```bash
# 1. Export data from SQLite
sqlite3 data/sessions/sessions.db ".dump" > sqlite_dump.sql

# 2. Convert to PostgreSQL format (manual or with tool)
# Note: May need to adjust syntax

# 3. Import to PostgreSQL
psql -h HOST -U adk_user -d adk_sessions < sqlite_dump.sql
```

## Cost Optimization

| Instance Type | vCPUs | RAM | Storage | Est. Monthly Cost | Use Case |
|---------------|-------|-----|---------|-------------------|----------|
| db-f1-micro | Shared | 0.6 GB | 10 GB | ~$10 | Development/testing |
| db-g1-small | Shared | 1.7 GB | 10 GB | ~$25 | Small production |
| db-custom-2-7680 | 2 | 7.5 GB | 20 GB | ~$100 | Production |
| db-custom-4-15360 | 4 | 15 GB | 50 GB | ~$200 | High traffic |

**Tips:**
- Use read replicas for read-heavy workloads
- Enable automatic storage increases
- Set up automated backups during off-peak hours
- Use connection pooling (built into ADK)

## References

- [ADK Session Service](https://github.com/googleapis/genai-agent-dev-kit)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [PostgreSQL Best Practices](https://www.postgresql.org/docs/current/)
- [SQLAlchemy Database URLs](https://docs.sqlalchemy.org/en/20/core/engines.html)
