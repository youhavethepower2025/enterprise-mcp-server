# Security Documentation

Enterprise MCP Server is built with security as a first-class concern. This document outlines authentication, authorization, data protection, and best practices.

---

## Table of Contents

1. [Authentication Strategies](#authentication-strategies)
2. [Authorization & Access Control](#authorization--access-control)
3. [Audit Logging](#audit-logging)
4. [Secrets Management](#secrets-management)
5. [Tunnel Security (Claude Desktop)](#tunnel-security-claude-desktop)
6. [Rate Limiting](#rate-limiting)
7. [Data Protection](#data-protection)
8. [Deployment Security](#deployment-security)
9. [Vulnerability Management](#vulnerability-management)

---

## Authentication Strategies

### Pattern 1: Simple API Key

**Used for:** Cloudflare, GoDaddy

```python
# Header-based authentication
headers = {
    "X-Auth-Key": settings.CLOUDFLARE_API_KEY,
    "X-Auth-Email": settings.CLOUDFLARE_EMAIL
}
```

**Security considerations:**
- API keys stored in environment variables (never hardcoded)
- Keys rotated regularly (quarterly recommended)
- Different keys per environment (dev/staging/prod)

---

### Pattern 2: OAuth 2.0

**Used for:** QuickBooks, Google Workspace

#### Authorization Code Flow

```
1. User clicks "Connect QuickBooks"
   ↓
2. Redirect to QuickBooks auth URL
   https://appcenter.intuit.com/connect/oauth2
   ↓
3. User authorizes application
   ↓
4. QuickBooks redirects back with auth code
   https://your-server.com/oauth/callback?code=ABC123
   ↓
5. Exchange code for access token + refresh token
   POST https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer
   ↓
6. Store tokens encrypted in PostgreSQL
```

#### Implementation

```python
# app/ecosystems/quickbooks/oauth.py

async def exchange_code_for_tokens(auth_code: str):
    """Exchange authorization code for access token"""
    response = await client.post(
        "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": settings.QBO_REDIRECT_URI
        },
        auth=(settings.QBO_CLIENT_ID, settings.QBO_CLIENT_SECRET)
    )

    tokens = response.json()

    # Encrypt before storing
    encrypted_access = encrypt(tokens['access_token'])
    encrypted_refresh = encrypt(tokens['refresh_token'])

    await db.execute("""
        INSERT INTO oauth_tokens (
            ecosystem, access_token, refresh_token, expires_at
        ) VALUES ($1, $2, $3, $4)
    """, "quickbooks", encrypted_access, encrypted_refresh, ...)

    return tokens
```

#### Token Refresh

Tokens automatically refreshed before expiration:

```python
async def get_valid_token(ecosystem: str):
    """Get access token, refreshing if needed"""
    token = await db.fetchrow(
        "SELECT * FROM oauth_tokens WHERE ecosystem = $1",
        ecosystem
    )

    # Check expiration (refresh 5 minutes before expiry)
    if token['expires_at'] < datetime.now() + timedelta(minutes=5):
        token = await refresh_token(ecosystem)

    return decrypt(token['access_token'])
```

**Security considerations:**
- Client secret never exposed to frontend
- Tokens encrypted at rest (AES-256)
- Refresh tokens rotated on each use
- Callback URL validated (no open redirects)

---

### Pattern 3: Complex OAuth (Amazon SP-API)

Amazon requires:
1. OAuth 2.0 authorization → access token + refresh token
2. Additional seller credentials (Seller ID, MWS Auth Token)
3. Regional marketplace handling (US, EU, JP, etc.)
4. Multiple token types with different scopes

```python
# app/ecosystems/amazon/auth.py

class AmazonAuth:
    """Amazon SP-API authentication"""

    async def get_auth_headers(self, marketplace: str):
        """Generate signed request headers"""
        # 1. Get OAuth access token
        access_token = await self.get_access_token()

        # 2. Sign request with AWS Signature v4
        signature = self.sign_request(
            method="GET",
            url=endpoint,
            service="execute-api",
            region=self.get_region(marketplace)
        )

        return {
            "x-amz-access-token": access_token,
            "x-amz-date": timestamp,
            "Authorization": f"AWS4-HMAC-SHA256 {signature}"
        }
```

**Security considerations:**
- LWA (Login with Amazon) tokens expire after 1 hour
- Refresh tokens valid for up to 18 months
- AWS Signature v4 prevents request tampering
- Per-marketplace credentials isolation

---

## Authorization & Access Control

### Multi-Tenant Isolation

Each client/tenant has isolated:

```python
# Request context middleware
@app.middleware("http")
async def tenant_isolation(request: Request, call_next):
    """Ensure tenant-specific data access"""
    tenant_id = extract_tenant_from_auth(request)
    request.state.tenant_id = tenant_id

    # All DB queries automatically filtered
    response = await call_next(request)
    return response
```

### Row-Level Security

All database queries include tenant filtering:

```sql
-- Automatic tenant filtering in queries
SELECT * FROM tool_executions
WHERE tenant_id = $1  -- Always required
AND timestamp > $2;
```

### Role-Based Access Control (Future)

Planned for multi-user tenants:

```python
# Per-user permissions
{
    "admin": ["*"],  # All tools
    "manager": ["quickbooks.*", "gohighlevel.*"],
    "viewer": ["*.read_*"]  # Read-only tools
}
```

---

## Audit Logging

### Tool Execution Logging

Every MCP tool call logged to PostgreSQL:

```sql
CREATE TABLE tool_executions (
    id UUID PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    input_params JSONB,
    status_code INTEGER,
    response_time_ms INTEGER,
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    user_id TEXT,  -- If multi-user
    ip_address INET
);

-- Indexes for fast queries
CREATE INDEX idx_tool_tenant_time ON tool_executions(tenant_id, timestamp DESC);
CREATE INDEX idx_tool_name ON tool_executions(tool_name);
```

### Query Examples

```sql
-- Audit trail for compliance
SELECT
    tool_name,
    input_params->>'contact_id' as affected_record,
    status_code,
    timestamp,
    user_id
FROM tool_executions
WHERE tenant_id = 'acme-corp'
  AND timestamp > NOW() - INTERVAL '30 days'
ORDER BY timestamp DESC;

-- Error analysis
SELECT
    tool_name,
    COUNT(*) as error_count,
    AVG(response_time_ms) as avg_latency
FROM tool_executions
WHERE status_code >= 400
  AND timestamp > NOW() - INTERVAL '24 hours'
GROUP BY tool_name
ORDER BY error_count DESC;

-- User activity tracking
SELECT
    user_id,
    COUNT(DISTINCT tool_name) as tools_used,
    COUNT(*) as total_calls
FROM tool_executions
WHERE tenant_id = 'acme-corp'
  AND timestamp::date = CURRENT_DATE
GROUP BY user_id;
```

### Log Retention

- **Production:** 90 days minimum (compliance requirement)
- **Development:** 30 days
- **Archived:** Exported to S3/R2 for long-term storage

---

## Secrets Management

### Environment Variables

All credentials stored in `.env` file (never committed):

```bash
# .env (NEVER COMMIT THIS FILE)
DATABASE_URL=postgresql://user:secure_password@localhost/db
QUICKBOOKS_CLIENT_SECRET=abc123...
AMAZON_CLIENT_SECRET=xyz789...
```

### .env.example Template

Checked into git with placeholder values:

```bash
# .env.example (safe to commit)
DATABASE_URL=postgresql://user:password@localhost/db
QUICKBOOKS_CLIENT_SECRET=your_secret_here
AMAZON_CLIENT_SECRET=your_secret_here
```

### Production Secrets (Docker)

Use Docker secrets for production:

```yaml
# docker-compose.prod.yml
services:
  api:
    secrets:
      - qbo_client_secret
      - amazon_client_secret
    environment:
      QBO_CLIENT_SECRET_FILE: /run/secrets/qbo_client_secret

secrets:
  qbo_client_secret:
    external: true
  amazon_client_secret:
    external: true
```

### Secrets Rotation

Recommended rotation schedule:
- **API Keys:** Every 90 days
- **OAuth Client Secrets:** Annually (or on team member departure)
- **Database Passwords:** Every 6 months
- **Encryption Keys:** Annually with key versioning

---

## Tunnel Security (Claude Desktop)

### HTTPS Requirement

Claude Desktop MCP configuration requires HTTPS endpoints. Two secure options:

#### Option 1: ngrok (Development)

```bash
# Start tunnel
ngrok http 8000

# Output: https://abc123.ngrok-free.app → http://localhost:8000
```

**Security features:**
- ✅ TLS 1.3 encryption
- ✅ Free tier sufficient for testing
- ⚠️ URL changes on restart (dev only)

#### Option 2: Tailscale Funnel (Production)

```bash
# Start tunnel
tailscale funnel 8000

# Output: https://mcp.tailnet-name.ts.net → http://localhost:8000
```

**Security features:**
- ✅ WireGuard-based VPN (military-grade encryption)
- ✅ Stable URL (never changes)
- ✅ Access control via Tailscale ACLs
- ✅ Free for personal use

### AI Detection Workaround

**Problem:** Some HTTP-to-MCP bridges have "AI request detection" that may block Claude's traffic.

**Solution:**

1. **Identify if using a bridge with detection:**
   - Cloudflare Workers with "Bot Management"
   - Some reverse proxies with ML-based filtering

2. **Disable detection:**
   - Cloudflare: Disable "Bot Fight Mode" for your worker
   - nginx: Disable `ModSecurity` rules for MCP endpoints
   - Custom bridges: Check settings for AI/bot detection

3. **Whitelist Claude's user agent:**
   ```nginx
   # nginx example
   if ($http_user_agent ~* "Claude") {
       set $allow_request 1;
   }
   ```

### Tunnel Authentication (Optional)

Add API key validation before MCP:

```python
# Tunnel authentication middleware
@app.middleware("http")
async def validate_tunnel_auth(request: Request, call_next):
    """Validate requests coming through tunnel"""
    tunnel_secret = request.headers.get("X-Tunnel-Secret")

    if tunnel_secret != settings.TUNNEL_SECRET:
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized tunnel"}
        )

    return await call_next(request)
```

---

## Rate Limiting

### Per-Ecosystem Limits

Prevent API quota exhaustion:

```python
# Rate limiter configuration
RATE_LIMITS = {
    "quickbooks": 500 / 60,  # 500 requests per minute
    "amazon": 20 / 60,       # 20 requests per minute (SP-API limit)
    "gohighlevel": 1000 / 60 # 1000 requests per minute
}

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Enforce per-ecosystem rate limits"""
    tool_name = extract_tool_name(request)
    ecosystem = tool_name.split('.')[0]

    # Check rate limit
    key = f"ratelimit:{ecosystem}:{tenant_id}"
    current = await redis.incr(key)

    if current == 1:
        await redis.expire(key, 60)  # Reset after 60 seconds

    if current > RATE_LIMITS[ecosystem]:
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded"}
        )

    return await call_next(request)
```

### Response Caching

Reduce external API calls:

```python
# Cache GET requests for 5 minutes
@cache(ttl=300)
async def get_quickbooks_invoice(invoice_id: str):
    """Cached invoice retrieval"""
    response = await qbo_client.get(f"/invoice/{invoice_id}")
    return response.json()
```

**Cache invalidation** on write operations:

```python
async def update_invoice(invoice_id: str, data: dict):
    """Update invalidates cache"""
    response = await qbo_client.put(f"/invoice/{invoice_id}", json=data)

    # Invalidate cache
    await cache.delete(f"invoice:{invoice_id}")

    return response.json()
```

---

## Data Protection

### Encryption at Rest

OAuth tokens encrypted in PostgreSQL:

```python
from cryptography.fernet import Fernet

# Encryption key from environment (rotated annually)
cipher = Fernet(settings.ENCRYPTION_KEY)

def encrypt(plaintext: str) -> str:
    """Encrypt sensitive data"""
    return cipher.encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    """Decrypt sensitive data"""
    return cipher.decrypt(ciphertext.encode()).decode()
```

### Encryption in Transit

- ✅ TLS 1.3 for all external API calls
- ✅ HTTPS tunnel for Claude Desktop
- ✅ PostgreSQL SSL mode (production)

### Data Minimization

Only log what's needed:

```python
# ❌ DON'T log full request body (may contain PII)
logger.info(f"Tool called: {tool_name} with {request.json()}")

# ✅ DO log minimal metadata
logger.info(f"Tool called: {tool_name} by tenant {tenant_id}")
```

### GDPR Compliance

For EU customers:

```python
# Right to be forgotten
async def delete_tenant_data(tenant_id: str):
    """Permanently delete all tenant data"""
    await db.execute("DELETE FROM tool_executions WHERE tenant_id = $1", tenant_id)
    await db.execute("DELETE FROM oauth_tokens WHERE tenant_id = $1", tenant_id)
    await db.execute("DELETE FROM api_cache WHERE tenant_id = $1", tenant_id)

    logger.info(f"Deleted all data for tenant {tenant_id}")
```

---

## Deployment Security

### Production Checklist

- [ ] All environment variables set from secure source (not in code)
- [ ] Database password changed from default
- [ ] HTTPS enforced for all endpoints
- [ ] OAuth redirect URIs validated (no open redirects)
- [ ] Rate limiting enabled
- [ ] Audit logging configured
- [ ] Secrets rotation schedule documented
- [ ] Backup strategy implemented
- [ ] Monitoring alerts configured
- [ ] Security headers configured

### Security Headers

```python
@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"

    return response
```

### Network Security

```yaml
# docker-compose.prod.yml
networks:
  internal:
    driver: bridge
    internal: true  # No external access

services:
  postgres:
    networks:
      - internal  # DB not exposed to internet

  api:
    networks:
      - internal
      - default  # Only API has external access
```

---

## Vulnerability Management

### Dependency Scanning

```bash
# Check for known vulnerabilities
pip install safety
safety check --json

# Update dependencies
pip list --outdated
pip install -U package_name
```

### Regular Updates

- **Monthly:** Review and update dependencies
- **Weekly:** Check security advisories (GitHub, CVE databases)
- **Immediately:** Patch critical vulnerabilities (CVSS score > 7.0)

### Penetration Testing

Recommended annually:
1. OAuth flow testing (CSRF, token leakage)
2. SQL injection attempts
3. Rate limit bypass attempts
4. Authentication bypass testing
5. Secrets exposure scanning

---

## Incident Response

### Security Incident Procedure

1. **Detect:** Monitoring alerts, user reports
2. **Contain:** Disable affected credentials, isolate systems
3. **Investigate:** Review audit logs, identify scope
4. **Remediate:** Patch vulnerability, rotate secrets
5. **Notify:** Inform affected users (if required by law)
6. **Document:** Post-mortem and lessons learned

### Example: Leaked API Key

```bash
# 1. Immediately rotate the key
# In platform dashboard: Generate new API key

# 2. Update .env on all environments
QUICKBOOKS_CLIENT_SECRET=new_secret_here

# 3. Restart services
docker-compose restart

# 4. Review audit logs
SELECT * FROM tool_executions
WHERE timestamp > 'suspected_leak_time'
AND tool_name LIKE 'quickbooks.%';

# 5. Document incident
echo "$(date): QBO key rotated due to suspected exposure" >> security_log.txt
```

---

## Security Contacts

For security vulnerabilities, contact:

- **Email:** security@your-domain.com
- **PGP Key:** [Link to public key]
- **Response SLA:** 24 hours for critical, 72 hours for all others

Do NOT open public GitHub issues for security vulnerabilities.

---

## References

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [OAuth 2.0 Security Best Practices](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

**Last Updated:** November 2025
