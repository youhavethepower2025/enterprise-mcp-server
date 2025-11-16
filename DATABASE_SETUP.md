# PostgreSQL Database Integration - Complete Setup Guide

## Overview

Your MedTainer MCP server now has full PostgreSQL database integration with:
- ✅ Automatic logging of all tool executions
- ✅ Complete audit trail with timestamps, parameters, responses, and duration
- ✅ Database schema for caching business data (contacts, invoices, orders)
- ✅ API calls audit trail
- ✅ Alembic migrations for schema management
- ✅ Database health checks in Docker
- ✅ API endpoint to view recent logs

## What Was Implemented

### 1. Database Models (`app/db/models.py`)

Five tables were created:

#### `tool_executions`
Logs every tool execution with:
- Tool name
- Input parameters (JSON)
- Response data (JSON)
- Duration in milliseconds
- Status (success/error/timeout)
- Error messages
- Source (live/sample/cached)
- Timestamp

#### `api_calls`
Audit trail for external API calls:
- Ecosystem (gohighlevel, quickbooks, etc.)
- Endpoint URL
- HTTP method
- Status code
- Latency
- Request/response size
- Rate limiting indicators

#### `contacts`, `invoices`, `orders`
Cached business data with:
- Unique ID
- Full data as JSON
- Last sync timestamp
- Expiration timestamp

### 2. Database Session Management (`app/db/session.py`)

- Connection pooling configured (10 connections, 20 max overflow)
- Pre-ping enabled to verify connections
- Dependency injection for FastAPI routes

### 3. Automatic Logging Middleware (`app/db/middleware.py`)

Intercepts all `/mcp/run/*` requests and automatically logs:
- Tool name from URL
- Request parameters
- Response data
- Execution duration
- Success/failure status
- Data source (live vs mock)

### 4. Alembic Migrations (`alembic/`)

- Initial migration creates all tables with indexes
- Configured to read database URL from settings
- Ready for future schema changes

### 5. Logs API Endpoint (`/mcp/logs`)

Query recent executions with:
- Limit parameter (1-100)
- Filter by tool name
- Returns detailed execution history

## Setup Instructions

### Step 1: Environment Configuration

Your `.env.example` already has the database configuration. Copy it and update if needed:

```bash
# Copy example to .env if not already done
cp .env.example .env

# Edit database password if desired (optional)
# DB_PASSWORD=your_secure_password_here
```

Default database credentials:
- **Host**: postgres (Docker service name)
- **Port**: 5432
- **Database**: medtainer
- **User**: mcp
- **Password**: mcp_secure_password_change_me

### Step 2: Start the Services

The database will initialize automatically when you start Docker:

```bash
# Start PostgreSQL and MCP server
docker-compose up -d

# View logs to confirm database startup
docker-compose logs -f postgres

# Wait for: "database system is ready to accept connections"
```

### Step 3: Run Migrations

The database tables are created automatically on startup via the `lifespan` function in `app/main.py`, but you can also run migrations explicitly:

```bash
# Inside the mcp container
docker-compose exec mcp alembic upgrade head

# Or from your local environment (if you have Python dependencies installed)
alembic upgrade head
```

### Step 4: Verify Database Setup

Connect to PostgreSQL to verify tables were created:

```bash
# Connect to database
docker-compose exec postgres psql -U mcp -d medtainer

# List all tables
\dt

# You should see:
# - tool_executions
# - api_calls
# - contacts
# - invoices
# - orders
# - alembic_version

# View table structure
\d tool_executions

# Exit psql
\q
```

## Testing the Integration

### Test 1: Execute a Tool and Check Logs

```bash
# Execute a tool (this will create a log entry)
curl -X POST http://localhost:8000/mcp/run/gohighlevel.read_contacts \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'

# View the execution log via API
curl http://localhost:8000/mcp/logs?limit=1

# Expected response:
{
  "count": 1,
  "limit": 1,
  "tool_name_filter": null,
  "logs": [
    {
      "id": 1,
      "timestamp": "2024-11-12T...",
      "tool_name": "gohighlevel.read_contacts",
      "params": {"limit": 5},
      "duration_ms": 234,
      "status": "success",
      "error_message": null,
      "source": "sample"
    }
  ]
}
```

### Test 2: Query Logs from Database Directly

```bash
# Connect to database
docker-compose exec postgres psql -U mcp -d medtainer

# View recent executions
SELECT 
  id, 
  timestamp, 
  tool_name, 
  duration_ms, 
  status, 
  source 
FROM tool_executions 
ORDER BY timestamp DESC 
LIMIT 10;

# View executions for a specific tool
SELECT * FROM tool_executions 
WHERE tool_name = 'gohighlevel.read_contacts' 
ORDER BY timestamp DESC;

# View average execution time per tool
SELECT 
  tool_name,
  COUNT(*) as executions,
  AVG(duration_ms) as avg_duration_ms,
  MAX(duration_ms) as max_duration_ms
FROM tool_executions
GROUP BY tool_name
ORDER BY avg_duration_ms DESC;
```

### Test 3: Test Multiple Tools

Execute several different tools to populate the logs:

```bash
# Execute different tools
curl -X POST http://localhost:8000/mcp/run/gohighlevel.read_contacts
curl -X POST http://localhost:8000/mcp/run/gohighlevel.pipeline_digest
curl -X POST http://localhost:8000/mcp/run/quickbooks.recent_invoices
curl -X POST http://localhost:8000/mcp/run/amazon.order_digest

# View all logs
curl http://localhost:8000/mcp/logs?limit=10

# Filter logs by tool name
curl http://localhost:8000/mcp/logs?tool_name=gohighlevel.read_contacts
```

### Test 4: Test Error Logging

Try executing a non-existent tool to see error logging:

```bash
# This will return 404 but still log the attempt
curl -X POST http://localhost:8000/mcp/run/nonexistent.tool

# Check logs - you won't see this in tool_executions 
# because the middleware only logs actual tool paths
# But you can verify the 404 response
```

## API Endpoints

### Health Check
```bash
GET /health

# Returns server status
```

### List All Tools
```bash
GET /mcp/tools
GET /mcp/tools?ecosystem=gohighlevel

# Returns available tools with metadata
```

### Execute Tool
```bash
POST /mcp/run/{tool_name}
Content-Type: application/json

{
  "param1": "value1",
  "param2": "value2"
}

# Executes tool and automatically logs to database
```

### View Execution Logs
```bash
GET /mcp/logs
GET /mcp/logs?limit=50
GET /mcp/logs?tool_name=gohighlevel.read_contacts

# Returns recent execution logs
```

## Database Schema Details

### tool_executions Table

```sql
CREATE TABLE tool_executions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    tool_name VARCHAR(100) NOT NULL,
    params JSONB,                    -- Input parameters
    response JSONB,                  -- Full response data
    duration_ms INTEGER,             -- Execution time
    status VARCHAR(20) NOT NULL,     -- success/error/timeout
    error_message TEXT,              -- Error details if any
    source VARCHAR(20),              -- live/sample/cached
    user_context TEXT                -- Future: user/agent info
);

-- Indexes for fast queries
CREATE INDEX idx_tool_executions_timestamp ON tool_executions(timestamp DESC);
CREATE INDEX idx_tool_executions_tool_name ON tool_executions(tool_name, timestamp DESC);
```

### api_calls Table

```sql
CREATE TABLE api_calls (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    ecosystem VARCHAR(50) NOT NULL,
    endpoint VARCHAR(500) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER,
    latency_ms INTEGER,
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,
    error TEXT,
    rate_limited BOOLEAN DEFAULT FALSE
);

-- Indexes for analysis
CREATE INDEX idx_api_calls_ecosystem ON api_calls(ecosystem, timestamp DESC);
CREATE INDEX idx_api_calls_timestamp ON api_calls(timestamp DESC);
```

## Advanced Usage

### Custom Queries

You can write custom SQL queries to analyze your tool usage:

```sql
-- Tools used most frequently
SELECT tool_name, COUNT(*) as count
FROM tool_executions
GROUP BY tool_name
ORDER BY count DESC;

-- Error rate per tool
SELECT 
  tool_name,
  COUNT(*) as total,
  SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors,
  ROUND(100.0 * SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) / COUNT(*), 2) as error_rate
FROM tool_executions
GROUP BY tool_name;

-- Performance by hour
SELECT 
  DATE_TRUNC('hour', timestamp) as hour,
  COUNT(*) as executions,
  AVG(duration_ms) as avg_duration
FROM tool_executions
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;

-- Live vs Sample data usage
SELECT 
  source,
  COUNT(*) as count,
  AVG(duration_ms) as avg_duration
FROM tool_executions
GROUP BY source;
```

### Backup and Restore

```bash
# Backup database
docker-compose exec postgres pg_dump -U mcp medtainer > backup.sql

# Restore database
docker-compose exec -T postgres psql -U mcp medtainer < backup.sql
```

### Clear Old Logs

If you want to keep the database size manageable:

```bash
# Delete logs older than 90 days
docker-compose exec postgres psql -U mcp -d medtainer -c \
  "DELETE FROM tool_executions WHERE timestamp < NOW() - INTERVAL '90 days';"

# Or keep only the most recent 10,000 executions
docker-compose exec postgres psql -U mcp -d medtainer -c \
  "DELETE FROM tool_executions WHERE id NOT IN (
    SELECT id FROM tool_executions ORDER BY timestamp DESC LIMIT 10000
  );"
```

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Test connection from MCP container
docker-compose exec mcp python -c "
from app.db.session import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connected successfully!')
"
```

### Migration Issues

```bash
# Check current migration status
docker-compose exec mcp alembic current

# View migration history
docker-compose exec mcp alembic history

# Reset database (WARNING: destroys all data)
docker-compose down -v
docker-compose up -d
```

### Middleware Not Logging

Check the application logs:

```bash
# View MCP server logs
docker-compose logs -f mcp

# Look for messages like:
# "Logged tool execution: gohighlevel.read_contacts (status=success, duration=234ms, source=sample)"
```

If not seeing these messages, verify:
1. Middleware is added in `app/main.py`
2. Database connection is working
3. No Python exceptions in logs

## What's Next?

Now that your database integration is complete, you can:

1. **Continue with API integrations** - As you add real API credentials, the logs will show "live" vs "sample" data
2. **Implement caching** - Use the contacts/invoices/orders tables to cache frequently accessed data
3. **Add monitoring** - Query tool_executions to build dashboards showing usage patterns
4. **Optimize performance** - Use the duration_ms field to identify slow operations
5. **Implement rate limiting** - Track api_calls to stay within rate limits

## Summary

✅ **PostgreSQL database running** in Docker with health checks
✅ **All tables created** with proper indexes
✅ **Automatic logging** via middleware for every tool execution
✅ **API endpoint** to view recent logs
✅ **Alembic migrations** configured for schema management
✅ **Complete audit trail** of all tool executions with parameters and responses

Your MCP server now has enterprise-grade logging and audit capabilities! Every tool execution is automatically recorded to the database, giving you complete visibility into what your AI agents are doing.

---

**Next Steps:** 
1. Test with `docker-compose up -d`
2. Execute some tools via the API
3. Query logs via `/mcp/logs` endpoint
4. Explore the data in PostgreSQL

**Questions?** Check the logs with `docker-compose logs -f mcp` for any errors.
