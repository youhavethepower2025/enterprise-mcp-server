# MCP OAuth Fixes Applied - November 17, 2025

## Summary

We've diagnosed and fixed the "Auth Complete, No POST /mcp" failure by comparing your implementation against the comprehensive MCP research document you provided.

## Root Cause: Malformed OAuth Scope

**The Problem:**
- Your discovery metadata declared: `"scopes_supported": ["claudeai", ""]`
- Claude Desktop requested: `scope=claudeai+` (which decodes to `"claudeai "` with trailing space)
- Your server stored and returned: `scope: "claudeai "` (including empty scope)
- Claude's backend proxy **silently rejected** the malformed scope and never made the POST /mcp request

**From the research:**
> "The JSON response from the POST /token (code exchange) must contain... a scope field (a space-delimited string of the scopes that were actually granted). A missing field is a likely cause of the 'Auth Complete, No POST' silent failure."

The scope field was present, but its VALUE was malformed.

## Fixes Applied

### Fix #1: Corrected Scopes Declaration ✅
**File:** `app/api/routes.py:78`

```python
# BEFORE (WRONG):
"scopes_supported": ["claudeai", ""]  # ❌ Empty string caused scope mismatch

# AFTER (FIXED):
"scopes_supported": ["claudeai"]  # ✅ Clean scope declaration
```

### Fix #2: Strip Whitespace from Token Response ✅
**File:** `app/api/routes.py:251`

```python
# BEFORE:
"scope": auth_code_data["scope"]  # ❌ Could contain "claudeai " with trailing space

# AFTER (FIXED):
"scope": auth_code_data["scope"].strip()  # ✅ Removes whitespace
```

### Fix #3: RFC 9728 Path-Suffixed Discovery Endpoints ✅
**File:** `app/api/routes.py:96-114`

Added two new endpoints to handle Claude's dual-path discovery probing:

```python
@router.get("/.well-known/oauth-protected-resource/mcp")
async def oauth_protected_resource_metadata_mcp():
    """Serves identical metadata from MCP-suffixed path"""
    return await oauth_protected_resource_metadata()

@router.get("/.well-known/oauth-authorization-server/mcp")
async def oauth_authorization_server_metadata_mcp():
    """Serves identical metadata from MCP-suffixed path"""
    return await oauth_authorization_server_metadata()
```

**Why needed (from research):**
> "The Claude client exhibits inconsistent behavior when searching for OAuth discovery documents. It probes for metadata at both the RFC-specified root and an RFC 9728-derived path suffixed with the MCP endpoint. Servers must serve identical discovery metadata from both paths to ensure robust connectivity."

## Deployment Status

✅ **DEPLOYED** to production (24.199.118.227) at 20:15 UTC
✅ **Container restarted** - medtainer-mcp-local running with fixes

## Testing Instructions

### Step 1: Clear Claude Desktop Cache (CRITICAL)
Claude Desktop may have cached the old OAuth state. You MUST:
1. **Remove the MCP server** from Claude Desktop settings
2. **Restart Claude Desktop** completely (quit and relaunch)
3. **Re-add the MCP server:** `https://medtainer.aijesusbro.com`

### Step 2: Attempt Connection
When you re-add the server:
1. OAuth flow should complete (you'll see the browser redirect)
2. **NEW BEHAVIOR:** Claude's proxy should now make the POST /mcp request!

### Step 3: Watch the Logs
```bash
ssh root@24.199.118.227 "docker logs medtainer-mcp-local -f"
```

**Expected successful log sequence:**
```
=== OAUTH TOKEN SUCCESS === Returning access token to client
[~1-2 second delay]
=== MCP SSE CONNECTION START === Method: POST, Path: /mcp  ← THIS IS NEW!
=== OAUTH SUCCESS === Token valid: xyz789ab...
=== AUTH SUCCESS === Method: oauth
=== REQUEST BODY === Received 142 bytes  ← Should have initialize data
=== REQUEST PARSED === Line 0: method=initialize, id=1
=== INITIALIZE DETECTED === Found initialize request
=== SESSION CREATED === New session ID: <uuid>
=== SSE EVENT 2 === Sending response for request_id=1
```

### Step 4: Verify in Claude Desktop
If successful, you should see:
- MCP server shows as **"Connected"** (green indicator)
- Tools are discoverable in Claude's interface
- You can invoke MCP tools through conversation

## What Changed vs. Research Document

### Compliance Status

| Requirement | Before | After | Status |
|------------|--------|-------|--------|
| Streamable HTTP transport | ✅ | ✅ | Implemented |
| OAuth 2.1 + PKCE | ✅ | ✅ | Implemented |
| `claudeai` scope support | ❌ Malformed | ✅ Fixed | **FIXED** |
| Dual discovery paths | ❌ Missing | ✅ Added | **FIXED** |
| Token response `scope` field | ❌ Malformed | ✅ Fixed | **FIXED** |
| SSE correct headers | ✅ | ✅ | Implemented |
| JSON-RPC 2.0 protocol | ✅ | ✅ | Implemented |

## Potential Remaining Issues

If the connection **still** fails after applying these fixes:

### Issue #1: Cloudflare Tunnel Buffering
The Cloudflare tunnel might be buffering or modifying requests. Check:
```bash
ssh root@24.199.118.227 "cloudflared tunnel info medtainer"
```

### Issue #2: Claude Proxy Bug
The research mentions a known bug where Claude's proxy fails for certain domain names:
> "Several reports document a specific bug (step=start_error) where Claude's proxy fails to initiate the OAuth flow when pointed at a production domain, but works perfectly for a preview deployment domain."

If you continue to see "Auth Complete, No POST," this may be an Anthropic-side issue requiring their support.

### Issue #3: Token Validation
Claude's proxy may validate additional token claims (aud, iss) that we're not setting. If needed, we can:
1. Generate JWT tokens instead of random strings
2. Include proper claims (aud, iss, exp, etc.)
3. Sign with JWKS

## Debug Commands

### Check OAuth Discovery Endpoints
```bash
# Root paths
curl https://medtainer.aijesusbro.com/.well-known/oauth-authorization-server | jq
curl https://medtainer.aijesusbro.com/.well-known/oauth-protected-resource | jq

# Path-suffixed (NEW)
curl https://medtainer.aijesusbro.com/.well-known/oauth-authorization-server/mcp | jq
curl https://medtainer.aijesusbro.com/.well-known/oauth-protected-resource/mcp | jq
```

### Check Redis Token State
```bash
# See all access tokens
ssh root@24.199.118.227 "docker exec medtainer-redis redis-cli KEYS 'access_token:*'"

# Get token details
ssh root@24.199.118.227 "docker exec medtainer-redis redis-cli GET 'access_token:<token>'"
```

### Monitor Real-Time Logs
```bash
# All logs with enhanced markers
ssh root@24.199.118.227 "docker logs medtainer-mcp-local -f"

# Just OAuth flow
ssh root@24.199.118.227 "docker logs medtainer-mcp-local -f" | grep "=== OAUTH"

# Just SSE connections (the critical one!)
ssh root@24.199.118.227 "docker logs medtainer-mcp-local -f" | grep "=== MCP SSE"
```

## Success Criteria

Connection is WORKING when you see:
1. ✅ OAuth flow completes without errors
2. ✅ `=== MCP SSE CONNECTION START ===` appears in logs (within 2 seconds of token success)
3. ✅ Initialize request is received and processed
4. ✅ Session is created
5. ✅ Claude Desktop shows "Connected" status
6. ✅ Tools are available in conversation

## Files Modified

1. `app/api/routes.py` - OAuth scope fixes + discovery endpoints
2. `DIAGNOSIS_AND_FIX.md` - Detailed root cause analysis
3. `FIXES_APPLIED.md` - This file

## Next Steps

1. **Test the connection** following the instructions above
2. **Report results** - Did you see the POST /mcp request in logs?
3. **If successful:** Document the working configuration
4. **If still failing:** Capture full logs and we'll investigate further

---
**Deployed:** 2025-11-17 20:15 UTC
**Server:** 24.199.118.227
**Container:** medtainer-mcp-local
**Status:** ✅ READY FOR TESTING
