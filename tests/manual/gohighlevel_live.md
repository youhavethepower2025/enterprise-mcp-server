# GoHighLevel Live Test Plan

These steps exercise the MCP server against the real GoHighLevel tenant using **read-only** operations. Run them whenever you need to confirm the integration before handing control back to John.

> ⚠️ Assumes `docker compose up -d` is already running inside `AI Projects/MedTainer MCP`.

## 1. Health Check
```bash
docker compose exec mcp python - <<'PY'
import httpx
print(httpx.get('http://localhost:8000/health').json())
PY
```

## 2. Contacts Snapshot
```bash
docker compose exec mcp python - <<'PY'
import httpx, json
resp = httpx.post(
    'http://localhost:8000/mcp/run/gohighlevel.read_contacts',
    json={'limit': 5},
    timeout=60,
)
print(json.dumps(resp.json(), indent=2)[:1200])
PY
```
Expected result: `status=ok`, `metadata.source=live`, and live contacts in `data.contacts`.

## 3. Pipeline Digest
```bash
docker compose exec mcp python - <<'PY'
import httpx, json
resp = httpx.post('http://localhost:8000/mcp/run/gohighlevel.pipeline_digest', json={}, timeout=60)
print(json.dumps(resp.json(), indent=2))
PY
```

## 4. Database Verification
```bash
docker compose exec postgres psql -U mcp medtainer -c \
"SELECT id, tool_name, status, source, params, jsonb_pretty(response) AS response
   FROM tool_executions
  ORDER BY id DESC LIMIT 5;"
```
Confirms each run is logged with the exact payload returned to the user.

## 5. Notes
- All commands are read-only; nothing is pushed into GoHighLevel.
- The `contacts` cache table is unused today. Live payloads live inside `tool_executions.response`.
- Rerun this checklist after dependency upgrades or code changes touching GoHighLevel tools.
