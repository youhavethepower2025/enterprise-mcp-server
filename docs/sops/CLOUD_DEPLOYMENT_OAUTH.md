# MedTainer MCP - Cloud Deployment with OAuth Authentication

**Status**: ✅ LIVE on DigitalOcean (as of Nov 20, 2025)
**URL**: https://medtainer.aijesusbro.com/mcp
**Server**: DigitalOcean Droplet (24.199.118.227)

---

## Overview

This is a **cloud-deployed MCP server** with **OAuth 2.1 authentication** accessible via Claude Desktop's new Connectors UI. This is NOT a local stdio MCP - it's a full HTTP+SSE server with OAuth flow.

### Key Architecture Components

1. **FastAPI MCP Server** - Python/FastAPI serving MCP protocol over HTTP+SSE
2. **OAuth 2.1 + PKCE** - Full authorization code flow with token management
3. **Cloudflare Tunnel** - HTTPS proxy from edge to DigitalOcean backend
4. **PostgreSQL + Redis** - Database and token storage
5. **Docker Compose** - Container orchestration

---

## Infrastructure Setup

### DigitalOcean Droplet

```bash
# Server Details
IP: 24.199.118.227
OS: Ubuntu (Docker pre-installed)
User: root
Password: MedT@iner2024!Secure
```

### Cloudflare Tunnel Configuration

**Tunnel ID**: `edbfc982-d5e1-47ee-bf8f-7ffa65cec842`

**Config Location**: `/etc/cloudflared/config.yml`

```yaml
tunnel: edbfc982-d5e1-47ee-bf8f-7ffa65cec842
credentials-file: /root/.cloudflared/edbfc982-d5e1-47ee-bf8f-7ffa65cec842.json

ingress:
  - hostname: medtainer.aijesusbro.com
    service: http://localhost:8000
  - service: http_status:404
```

**Tunnel runs as systemd service**:
```bash
# Check status
ssh root@24.199.118.227 "systemctl status cloudflared"

# View logs
ssh root@24.199.118.227 "journalctl -u cloudflared -f"
```

### Docker Compose Stack

**Location**: `/root/medtainer-dev/docker-compose.yml`

```yaml
services:
  postgres:
    image: postgres:16-alpine
    ports: ["5434:5432"]  # External: 5434, Internal: 5432

  redis:
    image: redis:7-alpine
    ports: ["6381:6379"]  # External: 6381, Internal: 6379

  mcp:
    build: .
    ports: ["8000:8000"]
    environment:
      REDIS_HOST: redis
      REDIS_PORT: 6379
      DB_HOST: postgres
      DB_PORT: 5432
```

**Container Names**:
- `medtainer-postgres` (PostgreSQL database)
- `medtainer-redis` (Token/session cache)
- `medtainer-mcp-local` (Main MCP server)

---

## OAuth 2.1 Implementation

### OAuth Endpoints

All OAuth endpoints are **publicly accessible** (no auth required for OAuth flow):

```
GET  /.well-known/oauth-authorization-server/mcp
GET  /.well-known/oauth-protected-resource/mcp
GET  /authorize  (or POST)
POST /token
```

### OAuth Flow

1. **Discovery** - Claude Desktop fetches metadata:
   ```
   GET /.well-known/oauth-protected-resource/mcp
   ```
   Returns:
   ```json
   {
     "resource": "https://medtainer.aijesusbro.com/mcp",
     "authorization_servers": ["https://medtainer.aijesusbro.com"],
     "bearer_methods_supported": ["header"],
     "scopes_supported": ["read", "write"],
     "mcp_endpoints": ["https://medtainer.aijesusbro.com/mcp"]
   }
   ```

2. **Authorization** - User redirected to authorize:
   ```
   GET /authorize?client_id=claude-desktop&redirect_uri=...&scope=read+write&state=...&code_challenge=...
   ```
   Server generates auth code and redirects to Claude callback.

3. **Token Exchange** - Claude exchanges code for token:
   ```
   POST /token
   grant_type=authorization_code&code=...&code_verifier=...
   ```
   Server returns access token (stored in Redis with 1hr TTL).

4. **MCP Connection** - Authenticated requests to MCP endpoint:
   ```
   POST /mcp
   Authorization: Bearer {access_token}
   Accept: application/json, text/event-stream
   ```

### Token Management

**Storage**: Redis (in-memory cache)
**Format**: Random 128-character hex string
**Expiration**: 3600 seconds (1 hour)
**Refresh**: Not implemented (tokens expire, re-auth required)

**Token Data Structure**:
```python
{
    "iss": "https://medtainer.aijesusbro.com",  # Issuer
    "sub": "claude-desktop",                     # Subject (client_id)
    "aud": "https://medtainer.aijesusbro.com/mcp", # Audience (resource)
    "iat": 1732064400,                           # Issued at timestamp
    "exp": 1732068000,                           # Expiration timestamp
    "client_id": "claude-desktop",
    "scope": "read write"
}
```

---

## Cloudflare WAF Configuration

### The Critical Fix: Bot Fight Mode Bypass

**Problem**: Cloudflare's Super Bot Fight Mode was blocking Claude Desktop's Electron user agent, causing silent connection failures after OAuth completed.

**Solution**: Created WAF rule to skip bot detection for `/mcp` endpoint.

### WAF Rule Details

**Rule ID**: `1621a66ce5d346d69c58db16fcbf00bf`
**Ruleset ID**: `812ff8906c75475ab9a5c4b06e4191ee`
**Phase**: `http_request_firewall_custom`

**Expression**:
```
(http.host eq "medtainer.aijesusbro.com" and http.request.uri.path eq "/mcp")
```

**Action**: Skip phases:
- `http_ratelimit` (Rate limiting)
- `http_request_sbfm` (Super Bot Fight Mode)

**Created via API**:
```bash
curl -X PUT "https://api.cloudflare.com/client/v4/zones/c42aeeb4c6da8a14d33808f4f321f321/rulesets/phases/http_request_firewall_custom/entrypoint" \
  -H "Authorization: Bearer gWbANxar1WFWh-GTi2IhtcdUBmmw2Cb47KIz9Q1n" \
  -H "Content-Type: application/json" \
  --data '{
    "rules": [{
      "action": "skip",
      "action_parameters": {
        "phases": ["http_ratelimit", "http_request_sbfm"]
      },
      "expression": "(http.host eq \"medtainer.aijesusbro.com\" and http.request.uri.path eq \"/mcp\")",
      "description": "Skip Bot Fight Mode for Claude Desktop MCP endpoint",
      "enabled": true
    }]
  }'
```

**Verify Rule**:
```bash
curl -X GET "https://api.cloudflare.com/client/v4/zones/c42aeeb4c6da8a14d33808f4f321f321/rulesets/phases/http_request_firewall_custom/entrypoint" \
  -H "Authorization: Bearer gWbANxar1WFWh-GTi2IhtcdUBmmw2Cb47KIz9Q1n" | jq '.result.rules'
```

---

## MCP Server Implementation

### SSE Stream Handler

**Endpoint**: `POST /mcp`
**Content-Type**: `text/event-stream`
**Authentication**: OAuth Bearer token (in `Authorization` header)

**Request Flow**:
1. Validate Bearer token from Redis
2. Parse JSON-RPC request from POST body
3. Process MCP method (initialize, tools/list, tools/call, etc.)
4. Stream SSE response with result

**SSE Event Format**:
```
event: message
data: {"jsonrpc":"2.0","id":1,"result":{...}}

```

**Keepalive**: Sends comment (`:`) every 15 seconds to keep connection alive.

### MCP Methods Implemented

- `initialize` - Handshake with protocol version and capabilities
- `tools/list` - Returns available tools (GoHighLevel, QuickBooks, etc.)
- `tools/call` - Executes a tool with provided arguments
- `prompts/list` - Returns available prompts (none currently)
- `resources/list` - Returns available resources (none currently)

---

## Deployment Process

### Initial Deployment

```bash
# 1. SSH into server
ssh root@24.199.118.227

# 2. Clone/update code
cd /root
git clone <repo> medtainer-dev  # or rsync from local

# 3. Create .env file (see Environment Variables below)
cd medtainer-dev
nano .env

# 4. Build and start containers
docker-compose build --no-cache
docker-compose up -d

# 5. Verify services
docker ps -a
docker logs medtainer-mcp-local --tail 50
```

### Code Updates (from local machine)

```bash
# Sync code to production
cd /Users/aijesusbro/AI\ Projects/medtainer-dev
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '.git' \
  --exclude 'postgres_data' --exclude 'redis_data' \
  . root@24.199.118.227:/root/medtainer-dev/

# Restart containers
ssh root@24.199.118.227 "cd /root/medtainer-dev && docker-compose restart mcp"

# View logs
ssh root@24.199.118.227 "docker logs medtainer-mcp-local -f"
```

---

## Environment Variables

**Location**: `/root/medtainer-dev/.env`

```bash
# FastAPI / MCP Settings
APP_NAME=MedTainer MCP Server
ENVIRONMENT=production
API_BASE_URL=http://localhost:8000
LOG_LEVEL=INFO

# GoHighLevel - MedTainer Account
GOHIGHLEVEL_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
GOHIGHLEVEL_BASE_URL=https://rest.gohighlevel.com/v1
GOHIGHLEVEL_LOCATION_ID=tkRtAYWmUh0V4aTlsqfG

# GoDaddy
GODADDY_API_KEY=AQ8qpVgtLyu_8WdoJQzkQCpNYRa2vF4Vun
GODADDY_API_SECRET=TVAsKELXABsongop7rVjKv

# DigitalOcean
DIGITALOCEAN_API_TOKEN=dop_v1_e51f560d3fcdbfea2273059609cf63f86cef71118358d7afa996b0464e5fdd2f

# PostgreSQL Database
POSTGRES_USER=mcp
POSTGRES_PASSWORD=MedT@iner2024!SecureDB
POSTGRES_DB=medtainer
DATABASE_URL=postgresql://mcp:MedT@iner2024!SecureDB@postgres:5432/medtainer

DB_HOST=postgres
DB_PORT=5432
DB_NAME=medtainer
DB_USER=mcp
DB_PASSWORD=MedT@iner2024!SecureDB

# MCP Server Authentication
MCP_API_KEY=y4lEXubCO9-0Fjs4kVFg4A-NIseySW9piTerGBoNw_A
```

---

## Connecting from Claude Desktop

### 1. Open Claude Desktop Connectors UI

Click "+" → "Add OAuth Connector"

### 2. Enter MCP URL

```
https://medtainer.aijesusbro.com/mcp
```

### 3. Authenticate via Browser

- Browser opens to authorize endpoint
- Click "Approve" (auto-approved in current implementation)
- Redirected back to Claude Desktop

### 4. Connection Established

Claude Desktop will show "Connected" status and tools will be available.

---

## Troubleshooting

### Check Container Status

```bash
ssh root@24.199.118.227 "docker ps -a"
```

Expected output:
```
CONTAINER ID   IMAGE                    STATUS         PORTS                    NAMES
xxx            medtainer-dev_mcp        Up 2 hours     0.0.0.0:8000->8000/tcp   medtainer-mcp-local
xxx            postgres:16-alpine       Up 2 hours     0.0.0.0:5434->5432/tcp   medtainer-postgres
xxx            redis:7-alpine           Up 2 hours     0.0.0.0:6381->6379/tcp   medtainer-redis
```

### View MCP Server Logs

```bash
# All logs
ssh root@24.199.118.227 "docker logs medtainer-mcp-local -f"

# OAuth-specific logs
ssh root@24.199.118.227 "docker logs medtainer-mcp-local -f | grep OAUTH"

# MCP connection logs
ssh root@24.199.118.227 "docker logs medtainer-mcp-local -f | grep 'POST /mcp'"
```

### Test OAuth Flow Manually

```bash
# 1. Get metadata
curl https://medtainer.aijesusbro.com/.well-known/oauth-protected-resource/mcp | jq

# 2. Test authorize endpoint (will redirect)
curl -I "https://medtainer.aijesusbro.com/authorize?client_id=test&redirect_uri=http://localhost&scope=read&state=test&code_challenge=test&code_challenge_method=S256"

# 3. Check Cloudflare WAF rule
curl -X GET "https://api.cloudflare.com/client/v4/zones/c42aeeb4c6da8a14d33808f4f321f321/rulesets/phases/http_request_firewall_custom/entrypoint" \
  -H "Authorization: Bearer gWbANxar1WFWh-GTi2IhtcdUBmmw2Cb47KIz9Q1n" | jq '.result.rules'
```

### Common Issues

**Issue**: OAuth completes but no POST /mcp requests reach server
**Cause**: Cloudflare Bot Fight Mode blocking Electron user agent
**Fix**: Verify WAF rule is active (see Cloudflare WAF Configuration above)

**Issue**: Container crashes on startup
**Cause**: Missing environment variables or database connection failure
**Fix**: Check `.env` file and verify postgres container is healthy

**Issue**: Redis connection errors
**Cause**: Redis container not running or wrong host
**Fix**: Ensure `REDIS_HOST=redis` (Docker service name, not localhost)

---

## Key Files Reference

### Server Code

- `/app/main.py` - FastAPI application entry point
- `/app/api/routes.py` - OAuth + MCP endpoint implementations
- `/app/core/config.py` - Configuration management
- `/app/tools/` - Tool implementations (GHL, QuickBooks, etc.)

### Docker

- `Dockerfile` - Container build configuration
- `docker-compose.yml` - Multi-container stack definition
- `.env` - Environment variables

### Cloudflare

- `/etc/cloudflared/config.yml` - Tunnel configuration (on server)
- Cloudflare Dashboard → aijesusbro.com → Security → WAF

---

## Success Indicators

When everything is working correctly, you'll see these logs:

```
2025-11-20 00:10:02 | INFO | === MCP SSE CONNECTION START === Method: POST, Path: /mcp
2025-11-20 00:10:02 | INFO | === ACCEPT HEADER === application/json, text/event-stream
2025-11-20 00:10:02 | INFO | === OAUTH SUCCESS === Token valid: f5e91e46...
2025-11-20 00:10:02 | INFO | Processing MCP method: tools/list, id: 1
2025-11-20 00:10:02 | INFO | === SSE EVENT 2 === Sending response for request_id=1
2025-11-20 00:10:02 | INFO | === SSE STREAM END === Stream closed after sending 3 events
```

---

## Credentials Reference

**DigitalOcean**:
- Server: 24.199.118.227
- User: root
- Password: MedT@iner2024!Secure

**Cloudflare**:
- Account: aijesusbro.com
- Zone ID: c42aeeb4c6da8a14d33808f4f321f321
- API Token: gWbANxar1WFWh-GTi2IhtcdUBmmw2Cb47KIz9Q1n

**Database**:
- PostgreSQL: mcp / MedT@iner2024!SecureDB
- External Port: 5434 (connect from local)
- Internal Port: 5432 (within Docker network)

**Redis**:
- External Port: 6381
- Internal Port: 6379
- No password

---

## Architecture Diagram

```
┌─────────────────┐
│ Claude Desktop  │
└────────┬────────┘
         │ HTTPS
         │ (OAuth + MCP)
         ▼
┌──────────────────────────┐
│   Cloudflare Edge        │
│   - WAF Rule (skip SBFM) │
│   - Tunnel Proxy         │
└────────┬─────────────────┘
         │ HTTP
         │ (localhost:8000)
         ▼
┌──────────────────────────┐
│  DigitalOcean Droplet    │
│  (24.199.118.227)        │
│                          │
│  ┌────────────────────┐  │
│  │ FastAPI MCP Server │  │
│  │ (Port 8000)        │  │
│  └─────┬──────────────┘  │
│        │                 │
│  ┌─────▼──────┐  ┌─────▼──────┐
│  │ PostgreSQL │  │   Redis    │
│  │ (Port 5432)│  │ (Port 6379)│
│  └────────────┘  └────────────┘
│                          │
└──────────────────────────┘
```

---

**Last Updated**: November 20, 2025
**Status**: Production - Fully Operational
**Next Steps**: Implement tool functionality (currently scaffolded)
