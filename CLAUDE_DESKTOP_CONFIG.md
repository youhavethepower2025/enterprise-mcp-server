# Claude Desktop Configuration for MedTainer MCP

## OAuth Credentials

**Server URL**: `https://medtainer.aijesusbro.com`

**OAuth Client ID**: `claude-desktop`

**OAuth Client Secret**: `nJHBiE_YwKXFis48s1LZKOA4VJASpn1A5O8rcVUnVA8`

---

## Configuration Steps

1. Open Claude Desktop Settings
2. Add new MCP server with the following:
   - **Name**: MedTainer MCP
   - **Server URL**: `https://medtainer.aijesusbro.com`
   - **Authentication**: OAuth
   - **Client ID**: `claude-desktop`
   - **Client Secret**: `nJHBiE_YwKXFis48s1LZKOA4VJASpn1A5O8rcVUnVA8`

3. Save and restart Claude Desktop

---

## Alternative: API Key Authentication

If OAuth doesn't work, you can use direct API key auth:

**API Key**: `y4lEXubCO9-0Fjs4kVFg4A-NIseySW9piTerGBoNw_A`

Add as custom header: `X-API-Key: y4lEXubCO9-0Fjs4kVFg4A-NIseySW9piTerGBoNw_A`

---

## Available Tools (26 total)

### GoHighLevel (13 tools)
- Contact management
- Pipeline tracking
- Intelligence insights
- Automated sync

### GoDaddy (8 tools)
- Domain management
- DNS configuration

### DigitalOcean (5 tools)
- Droplet management
- Infrastructure control

---

## Testing

Test the connection:
```bash
curl -H "X-API-Key: y4lEXubCO9-0Fjs4kVFg4A-NIseySW9piTerGBoNw_A" \
  https://medtainer.aijesusbro.com/sse
```

Should return MCP server initialization message.

---

**Production Server**: DigitalOcean (24.199.118.227)
**Status**: ✅ LIVE with authentication
**Auto-Sync**: Every 15 minutes (1,206 contacts)
