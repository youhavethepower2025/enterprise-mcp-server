# MCP Implementation Guide: GoHighLevel & QuickBooks Integration

## Overview

This guide provides step-by-step instructions to implement **real API integration** for GoHighLevel and QuickBooks ecosystems in the MedTainer MCP server. Currently, these integrations return mock data. Your task is to replace mock responses with actual API calls.

## Prerequisites

### API Documentation Location
**CRITICAL:** All API documentation for these integrations exists in:
```
/Users/johnberfelo/AI Projects/Docs/gohighlevel/
/Users/johnberfelo/AI Projects/Docs/quickbooks/
```

**Required Reading Before Implementation:**
1. `/Users/johnberfelo/AI Projects/Docs/gohighlevel/endpoints.md` - GoHighLevel API endpoints
2. `/Users/johnberfelo/AI Projects/Docs/gohighlevel/connections.md` - GoHighLevel auth requirements
3. `/Users/johnberfelo/AI Projects/Docs/gohighlevel/workflows.md` - Business logic context
4. `/Users/johnberfelo/AI Projects/Docs/quickbooks/endpoints.md` - QuickBooks API endpoints
5. `/Users/johnberfelo/AI Projects/Docs/quickbooks/connections.md` - QuickBooks auth (OAuth 2.0)
6. `/Users/johnberfelo/AI Projects/Docs/quickbooks/workflows.md` - Business logic context

### Current State
- **All infrastructure exists**: FastAPI server, tool registry, base clients
- **Mock data works**: All 12 tools return sample data
- **What's missing**: Real HTTP calls to external APIs

---

## Part 1: GoHighLevel Integration

### Files to Modify
```
app/mcp/ecosystems/gohighlevel/client.py
app/mcp/ecosystems/gohighlevel/tools.py (if needed)
```

### Step 1: Review API Documentation
Read the following files to understand the API:
- `/Users/johnberfelo/AI Projects/Docs/gohighlevel/endpoints.md`
- `/Users/johnberfelo/AI Projects/Docs/gohighlevel/connections.md`

**Key Information to Extract:**
- Base URL (likely already correct in `settings.gohighlevel_base_url`)
- Authentication method (Bearer token, API key in headers, etc.)
- Exact endpoint paths for:
  - Listing contacts
  - Retrieving pipeline/stage information
- Required query parameters
- Response structure
- Rate limits and error codes

### Step 2: Implement `list_contacts()` Method

**Current Code** (`app/mcp/ecosystems/gohighlevel/client.py:14-19`):
```python
def list_contacts(self, limit: int = 10) -> List[dict]:
    if not self.api_key:
        return sample_contacts()[:limit]
    # Placeholder for real API interaction
    # return self.get("/contacts/", params={"limit": limit})
    return sample_contacts()[:limit]
```

**Your Task:**
1. Uncomment and fix the `self.get()` call with the correct endpoint from the docs
2. Add error handling with try/except
3. Map the API response to the expected format (match mock data structure)
4. Add logging for successful and failed calls
5. Keep the fallback to mock data if API key is missing

**Implementation Requirements:**
```python
def list_contacts(self, limit: int = 10) -> List[dict]:
    """
    Fetch contacts from GoHighLevel API.

    Args:
        limit: Maximum number of contacts to return

    Returns:
        List of contact dictionaries with structure matching sample_contacts()

    Raises:
        Should NOT raise - catch exceptions and log errors, return empty list or mock data
    """
    # 1. Check if API key exists - if not, return mock data
    if not self.api_key:
        logger.warning("No GoHighLevel API key configured, returning sample data")
        return sample_contacts()[:limit]

    try:
        # 2. Make the actual API call using self.get()
        #    Consult endpoints.md for the correct path and parameters
        #    Example: response = self.get("/v1/contacts/", params={"limit": limit})

        # 3. Extract the data from response
        #    API might return {"contacts": [...]} or just [...]

        # 4. Transform API response to match the mock data structure
        #    Look at sample_contacts() to see expected format

        # 5. Log success
        logger.info(f"Successfully fetched {len(contacts)} contacts from GoHighLevel")

        # 6. Return the transformed data
        return contacts[:limit]

    except httpx.HTTPStatusError as e:
        # Handle HTTP errors (400, 401, 403, 404, 500, etc.)
        logger.error(f"GoHighLevel API error: {e.response.status_code} - {e.response.text}")
        return sample_contacts()[:limit]

    except httpx.RequestError as e:
        # Handle network errors (connection timeout, DNS failure, etc.)
        logger.error(f"GoHighLevel network error: {str(e)}")
        return sample_contacts()[:limit]

    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"Unexpected error fetching GoHighLevel contacts: {str(e)}")
        return sample_contacts()[:limit]
```

**Validation Checklist:**
- [ ] Correct endpoint path from documentation
- [ ] Correct authentication header format
- [ ] Response transformation matches mock data structure
- [ ] Error handling for all exception types
- [ ] Logging for success and failure cases
- [ ] Fallback to mock data on any error
- [ ] Type hints are correct

### Step 3: Implement `pipeline_digest()` Method

**Current Code** (`app/mcp/ecosystems/gohighlevel/client.py:21-26`):
```python
def pipeline_digest(self) -> List[dict]:
    data = self.list_contacts(limit=25)
    summary = {}
    for contact in data:
        summary[contact["stage"]] = summary.get(contact["stage"], 0) + 1
    return [{"stage": stage, "count": count} for stage, count in summary.items()]
```

**Your Task:**
This method currently aggregates from `list_contacts()`. Determine if GoHighLevel has a dedicated pipeline/stage API endpoint by checking the documentation.

**Option A:** If a dedicated pipeline endpoint exists:
- Implement direct API call to that endpoint
- Transform response to match current output format

**Option B:** If no dedicated endpoint exists:
- Keep current implementation (it will use the real `list_contacts()` you just implemented)
- Verify the "stage" field exists in the contact data structure

**Implementation Notes:**
- Add the same error handling pattern as `list_contacts()`
- Add logging
- Ensure return format matches: `[{"stage": str, "count": int}, ...]`

### Step 4: Add Required Imports

Add to the top of `client.py` if not already present:
```python
import logging
from typing import List

logger = logging.getLogger(__name__)
```

### Step 5: Test GoHighLevel Integration

Create a simple test script or use pytest:
```python
# Test with mock data (no API key)
from app.mcp.ecosystems.gohighlevel.client import GoHighLevelClient
client = GoHighLevelClient()
contacts = client.list_contacts(limit=5)
print(f"Mock test: Got {len(contacts)} contacts")

# Test with real API key (set GOHIGHLEVEL_API_KEY in .env)
# Run the server and call: POST http://localhost:8000/mcp/run/gohighlevel.read_contacts
```

---

## Part 2: QuickBooks Integration

### Files to Modify
```
app/mcp/ecosystems/quickbooks/client.py
app/mcp/ecosystems/quickbooks/tools.py (if needed)
```

### Step 1: Review API Documentation

Read the following files to understand the API:
- `/Users/johnberfelo/AI Projects/Docs/quickbooks/endpoints.md`
- `/Users/johnberfelo/AI Projects/Docs/quickbooks/connections.md`

**Key Information to Extract:**
- Base URL format (includes company ID in path)
- Authentication method (OAuth 2.0 access token)
- Exact endpoint paths for:
  - Querying invoices
  - Creating invoices
- Required headers and request format
- Response structure
- OAuth token refresh requirements (if applicable)

**CRITICAL: OAuth Consideration**
QuickBooks uses OAuth 2.0. Check `connections.md` to see if:
- You need to implement token refresh logic
- Access tokens have expiration times
- A refresh token is required

For initial implementation, assume the access token in `.env` is valid and fresh. OAuth refresh can be added later if needed.

### Step 2: Implement `ledger_summary()` Method

**Current Code** (`app/mcp/ecosystems/quickbooks/client.py:14-18`):
```python
def ledger_summary(self) -> List[dict]:
    if not self.api_key:
        return sample_invoices()
    # Placeholder for real GET query
    # return self.get(f"/{settings.quickbooks_company_id}/query?query=SELECT * FROM Invoice")
    return sample_invoices()
```

**Your Task:**
1. Implement the actual QuickBooks query for outstanding invoices
2. Use the correct endpoint format from `endpoints.md`
3. Transform response to match `sample_invoices()` structure
4. Add error handling and logging

**Implementation Requirements:**
```python
def ledger_summary(self) -> List[dict]:
    """
    Query QuickBooks for outstanding invoices.

    Returns:
        List of invoice dictionaries matching sample_invoices() structure
    """
    # 1. Check if access token and company ID exist
    if not self.api_key or not settings.quickbooks_company_id:
        logger.warning("QuickBooks credentials incomplete, returning sample data")
        return sample_invoices()

    try:
        # 2. Construct the query
        #    QuickBooks uses SQL-like queries: "SELECT * FROM Invoice WHERE Balance > '0'"
        #    Check endpoints.md for the correct query syntax

        # 3. Make the API call
        #    Example: response = self.get(
        #        f"/{settings.quickbooks_company_id}/query",
        #        params={"query": query_string}
        #    )

        # 4. Extract invoice data from response
        #    QuickBooks response structure: {"QueryResponse": {"Invoice": [...]}}

        # 5. Transform to match sample_invoices() format
        #    Map QuickBooks fields to expected fields:
        #    - invoice_id, customer, amount, status, due_date, etc.

        # 6. Log success
        logger.info(f"Successfully fetched {len(invoices)} invoices from QuickBooks")

        return invoices

    except httpx.HTTPStatusError as e:
        logger.error(f"QuickBooks API error: {e.response.status_code} - {e.response.text}")
        # Check for 401 Unauthorized - might mean token expired
        if e.response.status_code == 401:
            logger.error("QuickBooks access token may be expired - refresh required")
        return sample_invoices()

    except httpx.RequestError as e:
        logger.error(f"QuickBooks network error: {str(e)}")
        return sample_invoices()

    except Exception as e:
        logger.error(f"Unexpected error fetching QuickBooks invoices: {str(e)}")
        return sample_invoices()
```

**Validation Checklist:**
- [ ] Company ID included in URL path
- [ ] Query syntax matches QuickBooks API format
- [ ] Response parsing handles QueryResponse wrapper
- [ ] Field mapping matches mock data structure
- [ ] Error handling includes OAuth-specific errors (401)
- [ ] Logging for success and failure
- [ ] Fallback to mock data

### Step 3: Implement `create_invoice()` Method

**Current Code** (`app/mcp/ecosystems/quickbooks/client.py:20-22`):
```python
def create_invoice(self, payload: dict) -> dict:
    # Placeholder for real POST
    return {"invoice_id": "MOCK-INV-001", "status": "mock_created"}
```

**Your Task:**
1. Implement the actual QuickBooks invoice creation endpoint
2. Transform the simple payload format to QuickBooks required format
3. Handle response and return created invoice data
4. Add error handling and validation

**Implementation Requirements:**
```python
def create_invoice(self, payload: dict) -> dict:
    """
    Create a draft invoice in QuickBooks.

    Args:
        payload: Simplified invoice data
            {
                "customer": str,
                "line_items": [{"description": str, "amount": float}]
            }

    Returns:
        Created invoice data with at minimum: invoice_id, status
    """
    if not self.api_key or not settings.quickbooks_company_id:
        logger.warning("QuickBooks credentials incomplete, returning mock response")
        return {"invoice_id": "MOCK-INV-001", "status": "mock_created"}

    try:
        # 1. Transform the simple payload to QuickBooks format
        #    QuickBooks requires specific structure - check endpoints.md
        #    Example structure:
        #    {
        #        "Line": [{
        #            "Amount": 100.00,
        #            "DetailType": "SalesItemLineDetail",
        #            "SalesItemLineDetail": {
        #                "ItemRef": {"value": "1"},
        #                "Qty": 1
        #            },
        #            "Description": "Custom order"
        #        }],
        #        "CustomerRef": {"value": "123"},
        #        ...
        #    }

        # 2. NOTE: You may need to look up customer ID by name
        #    QuickBooks uses CustomerRef IDs, not names
        #    For MVP, you can hardcode a test customer ID or add a lookup method

        # 3. Make the POST request
        #    endpoint = f"/{settings.quickbooks_company_id}/invoice"
        #    response = self.post(endpoint, json=qb_payload)

        # 4. Extract invoice data from response
        #    Response structure: {"Invoice": {...}}

        # 5. Return simplified response
        #    At minimum: invoice_id, status, customer

        logger.info(f"Successfully created invoice {invoice_id} in QuickBooks")
        return result

    except httpx.HTTPStatusError as e:
        logger.error(f"QuickBooks API error creating invoice: {e.response.status_code}")
        logger.error(f"Response: {e.response.text}")
        return {"invoice_id": "ERROR", "status": "failed", "error": str(e)}

    except Exception as e:
        logger.error(f"Unexpected error creating QuickBooks invoice: {str(e)}")
        return {"invoice_id": "ERROR", "status": "failed", "error": str(e)}
```

**Note on Customer Lookup:**
QuickBooks requires customer IDs, not names. For initial testing:
1. **Option A:** Hardcode a test customer ID from your QuickBooks account
2. **Option B:** Add a helper method `_lookup_customer(name: str) -> Optional[str]` that queries for the customer
3. **Option C:** Modify the tool to accept customer ID instead of name

Choose the approach that makes sense for testing. Document your choice in comments.

**Validation Checklist:**
- [ ] Payload transformation matches QuickBooks format
- [ ] Customer reference handled (ID lookup or hardcoded for testing)
- [ ] Line items formatted correctly
- [ ] POST endpoint path is correct
- [ ] Response parsing extracts invoice ID
- [ ] Error handling includes validation errors (400)
- [ ] Returns structured error response on failure

### Step 4: Update BaseAPIClient Authentication

Check `app/mcp/common/base_client.py` to ensure the `_headers()` method correctly handles QuickBooks auth:

**QuickBooks requires:**
- `Authorization: Bearer {access_token}` header
- `Accept: application/json` header
- Company ID in the URL path (not in headers)

The current `BaseAPIClient._headers()` should already handle Bearer tokens, but verify:
```python
def _headers(self) -> dict:
    headers = {"Content-Type": "application/json"}
    if self.api_key:
        headers["Authorization"] = f"Bearer {self.api_key}"
    return headers
```

If this looks correct, no changes needed. QuickBooks uses `access_token` which is passed as `api_key` in the client initialization.

### Step 5: Test QuickBooks Integration

Test both methods:

**Test 1: Ledger Summary**
```bash
# Set credentials in .env:
# QUICKBOOKS_COMPANY_ID=your_company_id
# QUICKBOOKS_ACCESS_TOKEN=your_access_token

# Start server
uvicorn app.main:app --reload

# Test endpoint
curl -X POST http://localhost:8000/mcp/run/quickbooks.ledger_summary
```

**Test 2: Create Invoice**
```bash
curl -X POST http://localhost:8000/mcp/run/quickbooks.create_draft_invoice \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Customer",
    "amount": 100.00
  }'
```

---

## Part 3: Configuration & Environment Setup

### Update .env File
When API keys are obtained, add them to `.env`:

```bash
# GoHighLevel
GOHIGHLEVEL_API_KEY=your_ghl_api_key_here
GOHIGHLEVEL_BASE_URL=https://rest.gohighlevel.com/v1

# QuickBooks
QUICKBOOKS_COMPANY_ID=your_company_id
QUICKBOOKS_ACCESS_TOKEN=your_oauth_access_token
QUICKBOOKS_BASE_URL=https://quickbooks.api.intuit.com/v3/company
```

### Verify Configuration Loading
The `app/core/config.py` already handles these. Verify by:
```python
from app.core.config import settings
print(settings.gohighlevel_api_key)  # Should print your key
print(settings.quickbooks_company_id)  # Should print your company ID
```

---

## Part 4: Testing & Validation

### Manual Testing Checklist

**GoHighLevel:**
- [ ] With no API key: Returns mock data
- [ ] With invalid API key: Returns mock data + error logged
- [ ] With valid API key: Returns real data
- [ ] Test `gohighlevel.read_contacts` with limit parameter
- [ ] Test `gohighlevel.pipeline_digest`

**QuickBooks:**
- [ ] With no credentials: Returns mock data
- [ ] With invalid token: Returns mock data + error logged
- [ ] With valid token: Returns real invoices
- [ ] Test `quickbooks.ledger_summary`
- [ ] Test `quickbooks.create_draft_invoice` with test customer

### Automated Test Updates

Update `/tests/test_tools.py` to include tests with mocked API responses:
```python
def test_gohighlevel_real_api_format():
    """Test that real API response transformation works"""
    # Mock httpx response
    # Verify response matches expected format

def test_quickbooks_handles_auth_error():
    """Test that 401 errors are handled gracefully"""
    # Mock 401 response
    # Verify fallback to mock data
```

---

## Part 5: Success Criteria

### You're Done When:

1. **GoHighLevel Integration:**
   - ✅ `list_contacts()` makes real API call with valid key
   - ✅ Falls back to mock data on error
   - ✅ Logs all API calls and errors
   - ✅ Returns data matching mock structure
   - ✅ `pipeline_digest()` works (either via API or aggregation)

2. **QuickBooks Integration:**
   - ✅ `ledger_summary()` queries real invoices
   - ✅ `create_invoice()` creates real draft invoices
   - ✅ Falls back to mock data on error
   - ✅ Handles OAuth errors (401) with clear logging
   - ✅ Returns data matching mock structure

3. **Testing:**
   - ✅ Manual test with real API keys succeeds
   - ✅ Server starts without errors
   - ✅ All endpoints return 200 responses
   - ✅ Logs show "Successfully fetched X items" messages

4. **Documentation:**
   - ✅ Any assumptions documented in code comments
   - ✅ Customer lookup strategy documented (for QuickBooks)
   - ✅ Any deviations from this guide explained

---

## Part 6: Common Issues & Troubleshooting

### Issue: "401 Unauthorized" from API
**Cause:** Invalid or expired credentials
**Solution:**
- Verify API key/token is correctly set in `.env`
- Check if token has expired (QuickBooks tokens expire)
- Verify base URL is correct for your account/region

### Issue: "Response structure doesn't match"
**Cause:** API response format differs from mock data
**Solution:**
- Log the raw API response: `logger.debug(f"Raw response: {response}")`
- Update transformation logic to match actual API structure
- Ensure all required fields are present in transformed data

### Issue: "ModuleNotFoundError" when importing
**Cause:** Missing imports or circular dependencies
**Solution:**
- Check all imports at top of file
- Ensure `logger = logging.getLogger(__name__)` is defined
- Restart server after code changes

### Issue: "Connection timeout"
**Cause:** Network issues or incorrect base URL
**Solution:**
- Verify base URL in settings
- Check internet connection
- Increase timeout in `base_client.py` if API is slow

---

## Part 7: Next Steps After Completion

Once GoHighLevel and QuickBooks are working:

1. **Test with real business workflows:**
   - Fetch actual contacts from GoHighLevel
   - Query real invoices from QuickBooks
   - Create a test invoice

2. **Monitor logs for issues:**
   - Check for rate limiting errors
   - Verify data quality
   - Ensure no sensitive data in logs

3. **Update documentation:**
   - Add any findings to the Docs folder
   - Document rate limits encountered
   - Note any API quirks discovered

4. **Prepare for remaining ecosystems:**
   - Use this implementation as a template
   - Google Workspace (OAuth similar to QuickBooks)
   - Amazon SP-API (OAuth with refresh tokens)
   - Cloudflare (API token like GoHighLevel)
   - GoDaddy (API key + secret)

---

## Questions or Issues?

If you encounter any issues:
1. Check the logs: `tail -f logs/app.log` (if file logging enabled)
2. Verify configuration: Print `settings` values
3. Test with curl: Isolate whether issue is in client or tool
4. Review API documentation again: Re-read the Docs folder files

**Remember:** The Docs folder contains business context that the APIs don't provide. Use it to understand WHY certain data is important, not just HOW to fetch it.

---

## Appendix: Quick Reference

### File Locations
```
Implementation files:
  app/mcp/ecosystems/gohighlevel/client.py
  app/mcp/ecosystems/quickbooks/client.py

API documentation:
  AI Projects/Docs/gohighlevel/
  AI Projects/Docs/quickbooks/

Configuration:
  app/core/config.py
  .env

Tests:
  tests/test_tools.py
```

### Useful Commands
```bash
# Run server locally
uvicorn app.main:app --reload

# Run tests
pytest -v

# Check logs (if you add file logging)
tail -f logs/app.log

# Test tool endpoint
curl -X POST http://localhost:8000/mcp/run/{tool_name} \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}'

# List all tools
curl http://localhost:8000/mcp/tools
```

---

**Good luck with the implementation! Follow this guide step-by-step, and you'll have working integrations.**

---

## Worklog – 2025-11-11 (Codex)
- Implemented resilient GoHighLevel client calls with real endpoints, logging, and graceful fallbacks (`app/mcp/ecosystems/gohighlevel/client.py`).
- Extended QuickBooks client to execute invoice queries, customer lookups, and invoice creation with OAuth headers plus payload transformation (`app/mcp/ecosystems/quickbooks/client.py`).
- Updated QuickBooks draft invoice tool to accept richer parameters and surface errors cleanly (`app/mcp/ecosystems/quickbooks/tools.py`).
- Enhanced shared base client/config/env scaffolding for new secrets and headers (`app/mcp/common/base_client.py`, `app/core/config.py`, `.env.example`).
- Integrated FreshBooks ecosystem with the MCP-standard registry, settings, and mock fallbacks (`app/mcp/ecosystems/freshbooks/*`, `app/mcp/common/mock_data.py`, `.env.example`).
- Added GoHighLevel location-aware parameters, verified live `/contacts/` responses via .venv test harness, and documented pipeline fallback behavior when `/opportunities/` is unavailable (`app/mcp/ecosystems/gohighlevel/client.py`).
- 2025-11-12: Exercised MCP inside Docker against live GoHighLevel, fixed logging middleware to avoid ASGI disconnects while capturing responses (`app/db/middleware.py`), and documented the read-only test plan (`tests/manual/gohighlevel_live.md`). Tool executions now land in `tool_executions` with full JSON payloads for voice-driven review.
