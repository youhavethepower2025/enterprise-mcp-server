from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_tools_returns_ecosystems():
    response = client.get("/mcp/tools")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 6
    ecosystems = {tool["ecosystem"] for tool in payload["tools"]}
    assert {
        "gohighlevel",
        "quickbooks",
        "google_workspace",
        "amazon",
        "cloudflare",
        "godaddy",
        "freshbooks",
    }.issubset(ecosystems)


def test_run_tool_uses_mock_payloads():
    response = client.post("/mcp/run/gohighlevel.read_contacts", json={"limit": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "contacts" in payload["data"]
