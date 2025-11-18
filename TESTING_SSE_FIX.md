# Testing the SSE Handshake Fix

## What Was Fixed

### Problem
The MCP client connected briefly but disconnected immediately due to:
1. **Nginx timeout** - 60s `proxy_read_timeout` killed long-lived SSE connections
2. **Wrong Content-Type** - Used `application/x-ndjson` instead of `text/event-stream`
3. **Wrong message format** - Sent `{json}\n` instead of `data: {json}\n\n`
4. **No keepalive** - Proxies killed idle connections

### Solution
1. **Updated nginx config** - Separate location block for `/mcp` and `/sse` with:
   - `proxy_buffering off` - No buffering for real-time streaming
   - `proxy_read_timeout 3600s` - 1 hour timeout instead of 60s
   - `chunked_transfer_encoding on` - Proper streaming support
   - CORS headers for cross-origin connections

2. **Fixed SSE response** - Changed to:
   - Content-Type: `text/event-stream`
   - Headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no`

3. **Proper SSE format** - Messages now formatted as:
   ```
   data: {"jsonrpc":"2.0",...}

   ```

4. **Keepalive pings** - Sends `: keepalive\n\n` every 30 seconds

---

## Deployment Steps

### Step 1: Update Nginx Configuration on Server

SSH to your server and update the nginx config:

```bash
# SSH to server
ssh user@your-server

# Backup current config
sudo cp /etc/nginx/sites-available/medtainer-mcp /etc/nginx/sites-available/medtainer-mcp.backup

# Update with new config
sudo nano /etc/nginx/sites-available/medtainer-mcp
# (Copy content from nginx-config-example.conf in this repo)

# Test nginx config
sudo nginx -t

# If test passes, reload nginx
sudo systemctl reload nginx
```

### Step 2: Deploy Updated MCP Code

```bash
# Pull latest code
cd /path/to/medtainer-dev
git pull origin claude/fix-mcp-handshake-01Rd26pmzqeLcEmmZEYvGAEu

# Rebuild and restart containers
docker-compose down
docker-compose up -d --build

# Verify containers are running
docker-compose ps
```

### Step 3: Verify Logs

```bash
# Watch MCP server logs
docker logs medtainer-mcp-local -f

# In another terminal, watch nginx logs
sudo tail -f /var/log/nginx/medtainer-mcp-error.log
```

---

## Testing

### Test 1: Basic SSE Connection (No Auth)

Test if SSE endpoint is accessible:

```bash
curl -N -H "X-API-Key: your-api-key-here" \
  https://medtainer.aijesusbro.com/mcp
```

**Expected output:**
```
data: {"jsonrpc":"2.0","method":"server/initialized","params":{}}

: keepalive

: keepalive
```

The connection should:
- ✅ Return `server/initialized` notification immediately
- ✅ Send `: keepalive` every 30 seconds
- ✅ Stay connected for > 60 seconds (proving timeout fix works)
- ✅ NOT disconnect after 60 seconds

### Test 2: SSE Connection Longevity

Test that connection stays alive for at least 2 minutes:

```bash
# This will stay connected and show keepalive pings
timeout 120 curl -N -H "X-API-Key: your-api-key-here" \
  https://medtainer.aijesusbro.com/mcp
```

**Expected:**
- Should see at least 4 keepalive pings (every 30s for 2 minutes)
- Connection should NOT timeout on server side

### Test 3: Full MCP Handshake with Client

If you have a test MCP client:

```bash
# Example with mcp-client-test tool (if available)
mcp-client-test connect https://medtainer.aijesusbro.com/mcp \
  --api-key your-api-key-here
```

**Expected handshake flow:**
1. Client connects → Server sends `server/initialized`
2. Client sends `initialize` request
3. Server responds with capabilities
4. Connection stays open
5. Client can call tools

### Test 4: OAuth Flow (For Claude Desktop)

1. Configure Claude Desktop with:
   ```json
   {
     "mcpServers": {
       "medtainer": {
         "url": "https://medtainer.aijesusbro.com/mcp"
       }
     }
   }
   ```

2. Restart Claude Desktop

3. Check if MCP server appears in Claude's server list

4. Try using a tool: "Use medtainer to list GoDaddy domains"

**Expected:**
- OAuth flow completes successfully
- Claude discovers tools
- Tools execute and return results
- Connection stays stable

---

## Monitoring

### Check Nginx Access Logs

```bash
# Watch for /mcp endpoint requests
sudo tail -f /var/log/nginx/medtainer-mcp-access.log | grep "/mcp"
```

**Look for:**
- Status code 200 (not 401, 502, 504)
- Long response times (indicating connection is staying open)

### Check MCP Server Logs

```bash
docker logs medtainer-mcp-local -f
```

**Look for:**
- "SSE connection established (auth: oauth)" or "(auth: api_key)"
- "Sent server/initialized notification"
- "Sent SSE keepalive" every 30 seconds
- NO "SSE stream closed" immediately after connection

### Check Redis Token Storage (If OAuth)

```bash
# Connect to Redis container
docker exec -it medtainer-redis redis-cli

# List all keys
KEYS *

# Check access tokens
KEYS access_token:*

# Get token details (replace with actual token)
GET access_token:abc123...
```

---

## Troubleshooting

### Issue: Connection Still Drops After 60s

**Possible causes:**
1. Nginx config not reloaded: `sudo systemctl reload nginx`
2. Wrong nginx config file active: Check `/etc/nginx/sites-enabled/`
3. Cloudflare proxy in front of nginx: May need Cloudflare-specific settings

**Solution:**
```bash
# Verify which config is active
ls -la /etc/nginx/sites-enabled/

# Verify nginx is using new config
sudo nginx -T | grep -A 20 "location ~ \^/(mcp|sse)"
```

### Issue: Client Gets 401 Unauthorized

**Possible causes:**
1. OAuth token expired
2. API key incorrect
3. Redis not storing tokens

**Solution:**
```bash
# Test with API key directly
curl -N -H "X-API-Key: your-api-key" https://medtainer.aijesusbro.com/mcp

# Check Redis is accessible
docker exec -it medtainer-redis redis-cli PING
# Should return "PONG"

# Check MCP logs for auth errors
docker logs medtainer-mcp-local | grep -i "auth\|unauthorized"
```

### Issue: No Data Received

**Possible causes:**
1. Content-Type mismatch
2. Nginx buffering despite config
3. Client doesn't support SSE

**Solution:**
```bash
# Check response headers
curl -I -H "X-API-Key: your-api-key" https://medtainer.aijesusbro.com/mcp

# Should see:
# Content-Type: text/event-stream
# Cache-Control: no-cache
# X-Accel-Buffering: no
```

### Issue: Cloudflare Tunnel Buffering

If using Cloudflare Tunnel, it may buffer SSE streams. Add to tunnel config:

```yaml
# cloudflared config.yml
ingress:
  - hostname: medtainer.aijesusbro.com
    service: http://localhost:8000
    originRequest:
      noTLSVerify: true
      disableChunkedEncoding: false
      http2Origin: true
```

Restart cloudflared:
```bash
sudo systemctl restart cloudflared
```

---

## Success Criteria

✅ **Test 1 passes** - Basic SSE connection works
✅ **Test 2 passes** - Connection stays alive > 2 minutes
✅ **Keepalive pings** visible every 30 seconds
✅ **No timeout errors** in nginx logs
✅ **MCP client** successfully connects and stays connected
✅ **Tools execute** successfully via client

---

## Rollback Plan

If issues occur, rollback:

```bash
# Restore old nginx config
sudo cp /etc/nginx/sites-available/medtainer-mcp.backup /etc/nginx/sites-available/medtainer-mcp
sudo nginx -t
sudo systemctl reload nginx

# Rollback code
git checkout previous-commit-hash
docker-compose down
docker-compose up -d --build
```

---

## Next Steps After Success

1. **Monitor stability** - Run for 24 hours, check logs for errors
2. **Test with real client** - Claude Desktop or other MCP client
3. **Load testing** - Multiple concurrent SSE connections
4. **Security audit** - Ensure OAuth flow is secure
5. **Documentation** - Update main docs with new nginx requirements

---

**Last Updated:** 2025-11-18
**Branch:** claude/fix-mcp-handshake-01Rd26pmzqeLcEmmZEYvGAEu
**Issue:** MCP client connects briefly then disconnects - FIXED
