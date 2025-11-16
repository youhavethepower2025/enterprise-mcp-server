# GoHighLevel API Sync Process

**Purpose**: Ensure our MCP tools stay in sync with GoHighLevel's API schemas and capabilities

**Challenge**: GoHighLevel's V1 API reached end-of-support Oct 31, 2025, but still works. We need to monitor for changes and eventually migrate to newer APIs.

---

## 1. API Discovery & Validation Process

### Before Building Any Tool:

**Step 1: Fetch Current API Documentation**
```bash
# Check official docs
https://marketplace.gohighlevel.com/docs/ghl/contacts/contacts-api/
```

**Step 2: Test the Raw API Endpoint**
```bash
# Make direct API call to see REAL schema
docker exec medtainer-mcp python3 << 'EOF'
import httpx
import os
import json

api_key = os.getenv('GOHIGHLEVEL_API_KEY')
location_id = os.getenv('GOHIGHLEVEL_LOCATION_ID')

response = httpx.get(
    'https://rest.gohighlevel.com/v1/contacts/',
    params={'limit': 1, 'locationId': location_id},
    headers={'Authorization': f'Bearer {api_key}'}
)

print(json.dumps(response.json(), indent=2))
EOF
```

**Step 3: Document the Schema**
Create schema file in `app/mcp/ecosystems/gohighlevel/schemas/`

**Step 4: Build Tool**
Create tool that matches the REAL schema

**Step 5: Test Tool**
```bash
# Test via MCP endpoint
curl -X POST http://localhost:8000/mcp/run/gohighlevel.{tool_name} \
  -H "Content-Type: application/json" \
  -d '{params}'
```

---

## 2. Current GoHighLevel API Schema (V1)

### Contact Object (As of 2025-11-12)

```json
{
  "id": "TyIkvwFhlCzbA3vZpQyT",
  "locationId": "tkRtAYWmUh0V4aTlsqfG",
  "contactName": "reno montagano",
  "firstName": "reno",
  "lastName": "montagano",
  "companyName": null,
  "email": "reno@qualityhort.com",
  "phone": "+16043773756",
  "dnd": false,
  "type": "vendor",
  "source": null,
  "assignedTo": "27QOvF8RavEm2n5makFY",
  "city": null,
  "state": null,
  "postalCode": null,
  "address1": null,
  "dateAdded": "2025-10-30T16:54:27.971Z",
  "dateUpdated": "2025-10-30T17:06:38.300Z",
  "dateOfBirth": null,
  "tags": [],
  "country": "US",
  "website": null,
  "timezone": "America/Los_Angeles",
  "lastActivity": 1761843999647,
  "customField": []
}
```

### Available Fields
- **Identity**: id, locationId
- **Name**: contactName, firstName, lastName
- **Company**: companyName
- **Contact**: email, phone, dnd
- **Type**: type (vendor, lead, etc.), source
- **Assignment**: assignedTo (user ID)
- **Address**: city, state, postalCode, address1, country
- **Dates**: dateAdded, dateUpdated, dateOfBirth
- **Categorization**: tags (array)
- **Web**: website
- **Settings**: timezone
- **Activity**: lastActivity (timestamp)
- **Custom**: customField (array)

### Pagination Schema
```json
{
  "meta": {
    "total": 1206,
    "nextPageUrl": "...",
    "startAfterId": "...",
    "startAfter": 1761843267971,
    "currentPage": 1,
    "nextPage": 2,
    "prevPage": null
  }
}
```

---

## 3. Schema Validation Tests

### Create Automated Tests

**File**: `tests/test_ghl_api_schema.py`

```python
"""Tests to ensure GoHighLevel API schema hasn't changed."""

import httpx
import pytest
from app.core.config import settings


class TestGoHighLevelAPISchema:
    """Test suite to detect GoHighLevel API changes."""

    @pytest.fixture
    def ghl_client(self):
        """Real API client."""
        return httpx.Client(
            base_url="https://rest.gohighlevel.com/v1",
            headers={"Authorization": f"Bearer {settings.gohighlevel_api_key}"},
        )

    def test_contact_schema_fields(self, ghl_client):
        """Verify contact object has expected fields."""
        response = ghl_client.get(
            "/contacts/",
            params={"limit": 1, "locationId": settings.gohighlevel_location_id},
        )
        assert response.status_code == 200

        data = response.json()
        assert "contacts" in data
        assert len(data["contacts"]) > 0

        contact = data["contacts"][0]

        # Required fields
        required_fields = [
            "id",
            "locationId",
            "firstName",
            "lastName",
            "email",
            "phone",
            "dateAdded",
            "dateUpdated",
        ]

        for field in required_fields:
            assert field in contact, f"Missing required field: {field}"

    def test_contact_pagination_schema(self, ghl_client):
        """Verify pagination metadata structure."""
        response = ghl_client.get(
            "/contacts/",
            params={"limit": 10, "locationId": settings.gohighlevel_location_id},
        )
        data = response.json()

        assert "meta" in data
        meta = data["meta"]

        # Pagination fields
        pagination_fields = ["total", "nextPageUrl", "currentPage", "nextPage"]
        for field in pagination_fields:
            assert field in meta, f"Missing pagination field: {field}"

    def test_api_authentication(self, ghl_client):
        """Verify API key is valid."""
        response = ghl_client.get(
            "/contacts/",
            params={"limit": 1, "locationId": settings.gohighlevel_location_id},
        )
        assert response.status_code == 200, "API authentication failed"

    def test_rate_limit_headers(self, ghl_client):
        """Check if rate limit info is provided."""
        response = ghl_client.get(
            "/contacts/",
            params={"limit": 1, "locationId": settings.gohighlevel_location_id},
        )
        # Document what rate limit headers exist
        rate_headers = {k: v for k, v in response.headers.items() if "rate" in k.lower() or "limit" in k.lower()}
        print(f"Rate limit headers: {rate_headers}")
```

### Run Tests Regularly
```bash
# Run schema validation tests
docker exec medtainer-mcp pytest tests/test_ghl_api_schema.py -v

# Run before deploying new tools
docker exec medtainer-mcp pytest tests/ -v
```

---

## 4. Tool Development Process

### For Each New Tool:

**1. Research**
- Check official GoHighLevel docs
- Make raw API call to test endpoint
- Document request/response schema

**2. Create Schema File**
```python
# app/mcp/ecosystems/gohighlevel/schemas/contact.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class GHLContact(BaseModel):
    """GoHighLevel contact schema (validated against real API)."""

    id: str
    locationId: str
    contactName: Optional[str]
    firstName: Optional[str]
    lastName: Optional[str]
    companyName: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    dnd: bool = False
    type: Optional[str]  # vendor, lead, etc.
    source: Optional[str]
    assignedTo: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postalCode: Optional[str]
    address1: Optional[str]
    dateAdded: datetime
    dateUpdated: datetime
    dateOfBirth: Optional[datetime]
    tags: List[str] = []
    country: Optional[str]
    website: Optional[str]
    timezone: Optional[str]
    lastActivity: Optional[int]
    customField: List[dict] = []
```

**3. Build Client Method**
```python
# app/mcp/ecosystems/gohighlevel/client.py
def get_contact(self, contact_id: str) -> dict:
    """Get single contact by ID."""
    response = self.get(f"/contacts/{contact_id}")
    # Validate against schema
    contact = GHLContact(**response)
    return contact.dict()
```

**4. Build Tool**
```python
# app/mcp/ecosystems/gohighlevel/tools.py
class GetContactTool(BaseTool):
    metadata = ToolMetadata(
        name="gohighlevel.get_contact",
        description="Get complete details for a specific contact",
        ecosystem="gohighlevel",
    )

    def run(self, contact_id: str) -> ToolResponse:
        contact = self.client.get_contact(contact_id)
        return ToolResponse(status="ok", data={"contact": contact})
```

**5. Test Tool**
```bash
# Test via MCP endpoint
curl -X POST http://localhost:8000/mcp/run/gohighlevel.get_contact \
  -H "Content-Type: application/json" \
  -d '{"contact_id": "TyIkvwFhlCzbA3vZpQyT"}' | python3 -m json.tool
```

**6. Write Unit Test**
```python
def test_get_contact_tool():
    """Test get_contact tool returns valid data."""
    # Mock API response
    # Test tool execution
    # Validate response schema
```

---

## 5. Monitoring for API Changes

### Weekly Check (Automated)

**Script**: `scripts/check_ghl_api_health.py`

```python
"""Weekly check for GoHighLevel API changes."""

import httpx
import json
from datetime import datetime


def check_api_health():
    """Check if API is working and schema is stable."""
    # Make test API call
    # Compare response schema to saved baseline
    # Alert if changes detected


def save_schema_snapshot():
    """Save current API schema for comparison."""
    # Make API calls to all endpoints
    # Save response structures
    # Commit to git for versioning


if __name__ == "__main__":
    check_api_health()
```

### Cron Job
```bash
# Check API health weekly
0 9 * * 1 cd /Users/johnberfelo/AI\ Projects/MedTainer\ MCP && docker compose exec -T mcp python scripts/check_ghl_api_health.py
```

### Manual Monthly Review
- Check GoHighLevel changelog
- Review marketplace.gohighlevel.com/docs/ for updates
- Test all tools against live API

---

## 6. Version Migration Plan

### When GoHighLevel Releases New API Version:

**Phase 1: Research**
- Document new endpoints and schemas
- Identify breaking changes
- Test new API version

**Phase 2: Parallel Implementation**
- Keep V1 tools working
- Build V2 tools alongside
- Add version selection in config

**Phase 3: Migration**
- Update tools to use V2
- Keep V1 as fallback
- Monitor for issues

**Phase 4: Deprecation**
- Remove V1 code after 3 months stable on V2

---

## 7. Emergency Response Process

### If API Suddenly Breaks:

**Step 1: Detect**
- Monitoring alerts fire
- Users report errors
- Tests fail

**Step 2: Diagnose**
```bash
# Check API directly
docker exec medtainer-mcp python3 << 'EOF'
import httpx
response = httpx.get('https://rest.gohighlevel.com/v1/contacts/...')
print(response.status_code)
print(response.json())
EOF
```

**Step 3: Fallback**
- Switch to mock data temporarily
- Alert user via logs
- Investigate issue

**Step 4: Fix**
- Update schemas if API changed
- Update tools to match new behavior
- Test thoroughly
- Deploy fix

---

## 8. Documentation Updates

### Keep These Docs Current:
1. **This file** - Update schema when API changes
2. **GOHIGHLEVEL_MAGNIFICENCE.md** - Update tool list and examples
3. **CLAUDE.md** - Update integration status
4. **Docs/gohighlevel/** - Update endpoint docs

### Process:
- Update docs BEFORE building tools
- Commit schema snapshots to git
- Document why changes were made

---

## Current Status (2025-11-12)

### API Version
- Using: V1 (end-of-support Oct 31, 2025)
- Status: Working, no support
- Migration: Not urgent, but should plan for V2

### Working Endpoints
- ✅ GET /contacts/ - List contacts (tested)
- ⏳ GET /contacts/{id} - Get single contact (needs testing)
- ⏳ POST /contacts/ - Create contact (needs testing)
- ⏳ PUT /contacts/{id} - Update contact (needs testing)
- ⏳ POST /contacts/{id}/tags - Add tag (needs testing)
- ⏳ DELETE /contacts/{id}/tags - Remove tag (needs testing)

### Next Steps
1. Test remaining contact endpoints
2. Document all schemas
3. Build tools incrementally with testing
4. Set up automated monitoring

---

**Last Updated**: 2025-11-12
**Tested Against**: GoHighLevel V1 API
**Schema Version**: 1.0
