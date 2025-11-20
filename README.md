# Enterprise MCP Server

> Production-ready MCP server template with multi-platform integration, authentication, and audit logging.

## What It Does

FastAPI-based MCP server designed for real-world client deployments. Orchestrates multiple cloud ecosystems through a single API surface that AI agents can access:

- **CRM:** GoHighLevel contact management, pipeline tracking, workflow automation
- **Finance:** QuickBooks invoicing with OAuth 2.0 authentication
- **Infrastructure:** Cloudflare DNS/CDN management
- **Domains:** GoDaddy registrar and DNS configuration
- **Documents:** Google Workspace integration (Docs, Sheets, Drive)
- **Commerce:** Amazon Seller Central via SP-API

## Key Features

### Production-Ready
- ✅ PostgreSQL audit database with Alembic migrations
- ✅ Environment-based configuration (.env management)
- ✅ Docker Compose deployment (dev + production configs)
- ✅ Health checks and comprehensive logging
- ✅ Request validation and error handling

### Security-Focused
- ✅ API key authentication per ecosystem
- ✅ OAuth 2.0 implementation (QuickBooks, Google Workspace)
- ✅ Complex OAuth patterns (Amazon SP-API with refresh tokens)
- ✅ Rate limiting and request throttling
- ✅ Full audit trail of all tool executions

### Tunnel-Optimized
- ✅ HTTPS tunnel support (ngrok/Tailscale) for Claude Desktop
- ✅ MCP stdio bridge included (`mcp_stdio_bridge.py`)
- ✅ Documentation for AI detection workarounds
- ✅ Works with HTTP and stdio MCP transports

### Multi-Tenant Capable
- Per-client credential isolation
- Tenant-specific rate limits
- Isolated data storage patterns
- Configurable per-ecosystem permissions

---

## Quick Start

### Prerequisites
- Docker Desktop
- Python 3.11+ (for local development)
- Claude Desktop (optional, for testing)

### 1. Clone and Configure

```bash
git clone https://github.com/youhavethepower2025/enterprise-mcp-server.git
cd enterprise-mcp-server

# Create environment file
cp .env.example .env

# Edit with your API credentials
nano .env
```

### 2. Start with Docker

```bash
# Development mode
docker-compose up -d

# Production mode
docker-compose -f docker-compose.prod.yml up -d

# Verify server is running
curl http://localhost:8000/health
```

### 3. Alternative: Local Development

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --port 8000
```

---

## Architecture

### System Overview

```
┌──────────────────────────────────────────┐
│ Claude Desktop (via HTTPS Tunnel)        │
│ ngrok/Tailscale → HTTPS endpoint         │
└──────────────┬───────────────────────────┘
               │ HTTPS/MCP Protocol
               ▼
┌──────────────────────────────────────────┐
│ Enterprise MCP Server (FastAPI)          │
│  ├─ Tool Registry                        │
│  ├─ Auth Middleware                      │
│  ├─ Rate Limiter                         │
│  ├─ Audit Logger (PostgreSQL)           │
│  └─ Ecosystem Handlers                   │
└──────────────┬───────────────────────────┘
               │
       ┌───────┼────────┬─────────┬────────┬────────┐
       ▼       ▼        ▼         ▼        ▼        ▼
     GHL      QBO    Cloudflare GoDaddy  Google  Amazon
```

### Database Schema

- **tool_executions** - Audit trail of all MCP tool calls
- **api_cache** - Response caching for rate limit optimization
- **oauth_tokens** - Secure OAuth token storage with encryption
- **client_config** - Multi-tenant configuration

Managed with Alembic migrations for version control.

---

## Integration Patterns

### Pattern 1: Simple API Key (Cloudflare, GoDaddy)

```python
# Ecosystem handler with API key auth
headers = {
    "X-Auth-Key": settings.CLOUDFLARE_API_KEY,
    "X-Auth-Email": settings.CLOUDFLARE_EMAIL
}
response = await client.post(endpoint, headers=headers, json=data)
```

### Pattern 2: OAuth 2.0 (QuickBooks, Google Workspace)

```python
# OAuth flow implementation
1. Generate authorization URL
2. Handle callback with auth code
3. Exchange code for access token + refresh token
4. Store tokens encrypted in PostgreSQL
5. Auto-refresh before expiration
```

See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) for detailed OAuth patterns.

### Pattern 3: Complex OAuth (Amazon SP-API)

Amazon requires:
- OAuth 2.0 authorization
- Additional seller credentials
- Regional marketplace handling
- Multiple refresh token types

See `app/ecosystems/amazon/` for full implementation.

---

## Tools by Ecosystem

### GoHighLevel (CRM)
- `gohighlevel.read_contacts` - List contacts with filters
- `gohighlevel.create_contact` - Add new leads
- `gohighlevel.update_pipeline` - Manage deal stages
- `gohighlevel.trigger_workflow` - Automation

### QuickBooks (Finance)
- `quickbooks.list_invoices` - Query invoices
- `quickbooks.create_draft_invoice` - Draft billing
- `quickbooks.get_customer` - Customer lookup
- OAuth 2.0 authenticated

### Cloudflare (Infrastructure)
- `cloudflare.list_dns_records` - DNS management
- `cloudflare.create_dns_record` - Add records
- `cloudflare.audit_infrastructure` - Zone analysis

### GoDaddy (Domains)
- `godaddy.list_domains` - Domain catalog
- `godaddy.get_dns_records` - DNS configuration
- `godaddy.update_dns` - Modify records

### Google Workspace (Documents)
- `google.list_documents` - Document catalog
- `google.sync_sheet` - Spreadsheet integration
- OAuth 2.0 authenticated

### Amazon (Commerce)
- `amazon.get_orders` - Order digest
- `amazon.inventory_snapshot` - Stock levels
- Complex OAuth + SP-API credentials

---

## Security

### Authentication

- Environment-based API key management
- No hardcoded credentials anywhere in codebase
- OAuth 2.0 implementation with secure token storage
- Per-ecosystem authentication strategies

### Audit Logging

All tool executions logged to PostgreSQL:

```sql
SELECT
    tool_name,
    status_code,
    response_time_ms,
    timestamp,
    tenant_id
FROM tool_executions
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
```

### Rate Limiting

- Configurable per-ecosystem limits
- Database caching reduces external API calls
- Intelligent retry logic with exponential backoff

### Tunnel Security

**Claude Desktop MCP Requirements:**

1. Must use HTTPS endpoint (ngrok or Tailscale)
2. **IMPORTANT:** Some HTTP bridges have "AI request detection"
   - This can block Claude's requests as automated traffic
   - Solution: Disable detection in bridge settings
   - Documented in tunnel setup guides

See [SECURITY.md](SECURITY.md) for comprehensive security documentation.

---

## Deployment

### Development (Local Docker)

```bash
docker-compose up -d
```

Access at `http://localhost:8000`

### Production (DigitalOcean/Railway/Render)

```bash
# Deploy script included
./deploy_to_do.sh

# Or use production compose file
docker-compose -f docker-compose.prod.yml up -d
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for platform-specific guides.

### Claude Desktop Integration

Two tunnel options documented:

1. **ngrok** (free, for testing)
   - URL changes on restart
   - Good for development

2. **Tailscale Funnel** (free, for production)
   - Permanent URL
   - Stable, secure, no DNS config needed

See [QUICK_START.md](QUICK_START.md) for step-by-step tunnel setup.

---

## Use Cases

This template is designed for:

- **Client-specific MCP deployments** - Adapt to any business's ecosystem
- **Multi-tenant SaaS MCP servers** - Serve multiple clients from one deployment
- **Enterprise AI agent backends** - Production-grade infrastructure
- **Custom automation platforms** - Build on the integration patterns

---

## Documentation

- **[QUICK_START.md](QUICK_START.md)** - Get running in 5 minutes
- **[DATABASE_SETUP.md](DATABASE_SETUP.md)** - PostgreSQL and Alembic guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment patterns
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Adding new ecosystems
- **[LOGGING_GUIDE.md](LOGGING_GUIDE.md)** - Observability and debugging
- **[GOHIGHLEVEL_SYNC_PROCESS.md](GOHIGHLEVEL_SYNC_PROCESS.md)** - CRM integration example
- **[CLAUDE.md](CLAUDE.md)** - Complete architecture and roadmap

---

## Project Structure

```
enterprise-mcp-server/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── ecosystems/              # Platform integrations
│   │   ├── gohighlevel/
│   │   ├── quickbooks/
│   │   ├── cloudflare/
│   │   ├── godaddy/
│   │   ├── google/
│   │   └── amazon/
│   └── mcp/                     # MCP protocol implementation
├── alembic/                     # Database migrations
├── tests/                       # Integration tests
├── docker-compose.yml           # Development stack
├── docker-compose.prod.yml      # Production stack
├── mcp_stdio_bridge.py          # stdio transport bridge
└── deploy_to_do.sh             # Deployment script
```

---

## Adapting This Template

### 1. Add Your Ecosystem

```bash
# Create ecosystem folder
mkdir -p app/ecosystems/your_platform

# Implement handler
touch app/ecosystems/your_platform/client.py
touch app/ecosystems/your_platform/tools.py
touch app/ecosystems/your_platform/schemas.py
```

### 2. Define Tools

```python
# app/ecosystems/your_platform/tools.py
YOUR_PLATFORM_TOOLS = [{
    "name": "your_platform.do_something",
    "description": "Description for AI agents",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param1": {"type": "string"}
        },
        "required": ["param1"]
    }
}]
```

### 3. Register in Tool Registry

See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) for complete walkthrough.

---

## Built With

- **Python 3.11+** - Core language
- **FastAPI** - Web framework
- **PostgreSQL** - Database and audit logs
- **Alembic** - Database migrations
- **Docker Compose** - Orchestration
- **Pydantic** - Data validation
- **MCP Protocol** - Model Context Protocol

---

## What Makes This Special

### Production-Tested
- Built for real client deployment
- Handles authentication complexity (OAuth 2.0, multi-stage flows)
- Full audit trail for compliance
- Error handling and retry logic

### Security-First
- No credentials in code
- Encrypted token storage
- Per-ecosystem auth patterns
- Rate limiting and validation

### Developer-Friendly
- Alembic migrations (version controlled schema)
- Comprehensive documentation
- Test scaffolding included
- Easy to extend with new platforms

### Claude Desktop Ready
- Tunnel setup documented (ngrok/Tailscale)
- AI detection workaround guide
- stdio bridge included
- 5-minute quickstart

---

## Testing

```bash
# Run all tests
pytest

# Test specific ecosystem
pytest tests/test_gohighlevel.py

# Test with coverage
pytest --cov=app tests/
```

---

## Contributing

This is a template - fork and adapt for your needs:

1. **Use it** - Deploy for your clients or business
2. **Extend it** - Add your platform integrations
3. **Share learnings** - Open issues with patterns you discover

---

## License

MIT License - See LICENSE file for details

---

## Acknowledgments

- Built for [Claude Code](https://claude.com/claude-code) integration
- Follows [MCP Protocol](https://modelcontextprotocol.io) specification
- OAuth patterns adapted from real-world client deployments
- Tunnel guides tested with ngrok and Tailscale

---

**Questions or want to discuss MCP architecture?** Open an issue.
