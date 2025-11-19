# Enhanced MCP Server Logging Guide

## Overview

Comprehensive logging has been added to track the complete OAuth + SSE handshake lifecycle. Every critical step now has detailed logging with standardized markers for easy searching.

## Log Markers

All enhanced logs use `===` markers for easy filtering:

```bash
# View only OAuth flow
docker logs medtainer-mcp-local | grep "=== OAUTH"

# View only SSE stream events
docker logs medtainer-mcp-local | grep "=== SSE"

# View session management
docker logs medtainer-mcp-local | grep "=== SESSION"

# View request processing
docker logs medtainer-mcp-local | grep "=== REQUEST"

# View stream closure (critical for debugging)
docker logs medtainer-mcp-local | grep "=== STREAM CLOSING"
```

## Complete OAuth + SSE Flow

### 1. OAuth Discovery
```
# Claude Desktop discovers OAuth endpoints
GET /.well-known/oauth-authorization-server
GET /.well-known/oauth-protected-resource
```

### 2. Authorization Request
```
=== OAUTH AUTHORIZE START === client_id=claude-desktop, scope=claudeai
=== OAUTH CODE GENERATED === code=abc123def456...
=== OAUTH CODE STORED === Stored in Redis with 600s TTL
=== OAUTH REDIRECT === Redirecting to: https://claude.ai/api/mcp/auth_callback...
```

### 3. Token Exchange
```
=== OAUTH TOKEN START === grant_type=authorization_code, client_id=claude-desktop
=== REDIS LOOKUP === Checking for auth_code:abc123def456...
=== OAUTH CODE FOUND === Retrieved code data from Redis
=== PKCE VALIDATION === Code challenge present, validating verifier
=== PKCE SUCCESS === Code verifier validated
=== ACCESS TOKEN GENERATED === token=xyz789abc123...
=== ACCESS TOKEN STORED === Stored in Redis with 3600s TTL
=== OAUTH TOKEN SUCCESS === Returning access token to client
```

### 4. SSE Connection Establishment
```
=== MCP SSE CONNECTION START === Method: POST, Path: /mcp, Client: 172.18.0.1
Request headers:
  authorization: Bearer xyz789abc123...
  mcp-session-id: (or None for first request)

=== OAUTH FLOW === Attempting OAuth token validation
=== OAUTH SUCCESS === Token valid: xyz789ab...
=== AUTH SUCCESS === Method: oauth

=== SESSION MANAGEMENT === Checking for existing session
=== SESSION === No session ID provided (likely initialize or first request)

=== REQUEST BODY === Received 0 bytes
=== WARNING === Empty request body - client may send requests via separate POST
```

### 5. SSE Stream Lifecycle
```
=== SSE STREAM START === Beginning event generation
=== SSE EVENT 0 === Sent priming event (empty comment for reconnection)
=== SSE EVENT 1 === Sent endpoint event: {...}

=== PROCESSING START === Processing 0 initial requests
=== NO INITIAL REQUESTS === No requests in body to process
=== PROCESSING COMPLETE === All 0 requests processed

=== RESPONSE LOOP START === Waiting for responses from queue
=== STREAM CLOSING === Processing complete, no more requests. Timeouts: 1, Loop iterations: 2
=== CRITICAL === MCP spec requires stream to stay open, but we have no keepalive mechanism!

=== SSE STREAM END === Stream closed after sending 2 events total
=== STREAM STATS === Loop iterations: 2, Timeout count: 1
```

## Current Issue: Premature Stream Closure

**Problem:** The stream closes after sending 2 events (priming + endpoint) because:

1. Claude Desktop makes initial connection with empty body
2. Server sends required priming + endpoint events
3. Server waits 0.1s for responses
4. No responses (because no requests were sent)
5. Processing task is done (0 requests to process)
6. Stream closes

**What Should Happen:** Per MCP spec, the stream should stay open indefinitely, waiting for:
- Client to send subsequent requests
- Client to disconnect
- Keepalive events to prevent timeout

## What to Look For in Logs

### Successful OAuth Flow
- ✅ `=== OAUTH SUCCESS === Token valid`
- ✅ `=== AUTH SUCCESS === Method: oauth`
- ✅ `=== ACCESS TOKEN STORED === Stored in Redis`

### Stream Lifecycle
- ✅ `=== SSE STREAM START ===` - Stream begins
- ✅ `=== SSE EVENT 0 ===` - Priming event sent
- ✅ `=== SSE EVENT 1 ===` - Endpoint event sent
- ⚠️ `=== STREAM CLOSING === Processing complete` - **This is the problem**
- ⚠️ `=== CRITICAL === MCP spec requires stream to stay open` - Known issue

### What's Missing
- ❌ `=== INITIALIZE DETECTED ===` - No initialize request in body
- ❌ `=== SESSION CREATED ===` - No session created
- ❌ `=== RESPONSE RECEIVED ===` - No tool responses (no requests)

## Next Steps

### Fix #1: Keep Stream Open with Keepalive
Add periodic keepalive events to prevent stream closure:

```python
# In event_generator(), change the timeout logic:
while True:
    try:
        response_data = await asyncio.wait_for(response_queue.get(), timeout=30.0)
    except asyncio.TimeoutError:
        # Send keepalive comment every 30 seconds
        yield f":\n\n"  # SSE comment (keepalive)
        logger.debug("=== KEEPALIVE === Sent heartbeat")
        continue  # Don't break, keep waiting
```

### Fix #2: Handle Initialize in Separate Request
Some MCP clients send initialize as a separate POST after establishing SSE stream:

```python
# Listen for incoming POST requests on /mcp while stream is open
# This is the "bidirectional SSE" pattern
```

### Fix #3: Increase Timeout Before Closing
Instead of closing after 0.1s of no activity, wait longer:

```python
# Change timeout from 0.1 to 5.0 seconds
response_data = await asyncio.wait_for(response_queue.get(), timeout=5.0)
```

## Testing Commands

### Deploy Enhanced Logging
```bash
cd /Users/aijesusbro/AI\ Projects/medtainer-dev
./deploy_logging_update.sh
```

### Watch Logs in Real-Time
```bash
ssh root@24.199.118.227 "docker logs medtainer-mcp-local -f"
```

### Filter Specific Flows
```bash
# Just OAuth
ssh root@24.199.118.227 "docker logs medtainer-mcp-local --tail 200" | grep "=== OAUTH"

# Just SSE stream
ssh root@24.199.118.227 "docker logs medtainer-mcp-local --tail 200" | grep "=== SSE"

# Critical issues only
ssh root@24.199.118.227 "docker logs medtainer-mcp-local --tail 200" | grep "=== CRITICAL"
```

### Check Redis State
```bash
# See all access tokens
ssh root@24.199.118.227 "docker exec medtainer-redis redis-cli KEYS 'access_token:*'"

# See all auth codes
ssh root@24.199.118.227 "docker exec medtainer-redis redis-cli KEYS 'auth_code:*'"

# Get token details
ssh root@24.199.118.227 "docker exec medtainer-redis redis-cli GET 'access_token:xyz789abc123...'"
```

## Debug Checklist

When investigating connection issues, check:

1. **OAuth flow completed?**
   - [ ] Authorization endpoint called
   - [ ] Token endpoint called
   - [ ] Access token generated and stored

2. **SSE connection authenticated?**
   - [ ] Bearer token sent by client
   - [ ] Token found in Redis
   - [ ] AUTH SUCCESS logged

3. **Session management?**
   - [ ] Session ID in request headers?
   - [ ] Session created for initialize?
   - [ ] Session retrieved for subsequent requests?

4. **Request body parsing?**
   - [ ] Body bytes > 0?
   - [ ] JSON-RPC requests parsed?
   - [ ] Initialize request detected?

5. **Stream lifecycle?**
   - [ ] Priming event sent?
   - [ ] Endpoint event sent?
   - [ ] How many events sent total?
   - [ ] Why did stream close?
   - [ ] Timeout count before closure?

## Expected vs Actual

### Expected (Working MCP Server)
```
1. Client connects → OAuth flow
2. Client gets access token
3. Client opens SSE stream with Bearer token
4. Server sends priming + endpoint events
5. Client sends initialize request (via POST to /mcp or in stream)
6. Server responds with initialize response
7. Stream stays open indefinitely
8. Client sends tools/list, tools/call requests
9. Server responds via SSE
10. Stream stays open until client disconnects
```

### Actual (Current Behavior)
```
1. Client connects → OAuth flow ✅
2. Client gets access token ✅
3. Client opens SSE stream with Bearer token ✅
4. Server sends priming + endpoint events ✅
5. Client sends initialize request ❌ (empty body)
6. Server waits 0.1s for response ⏱️
7. No response, processing done ❌
8. Stream closes after 2 events ❌
```

## Summary

The logging now provides complete visibility into:
- OAuth authorization and token exchange
- SSE stream establishment and authentication
- Request body parsing
- Event generation and transmission
- Stream closure decisions

**The core issue is clear:** Stream closes too quickly because there's no keepalive mechanism and no requests in the initial connection body.

**The fix:** Implement keepalive events OR handle initialize as a separate request OR increase timeout significantly.
