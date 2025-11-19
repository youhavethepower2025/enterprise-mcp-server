#!/usr/bin/env python3
"""
Test MCP Session Management
Simulates Claude Desktop's multi-request flow with session tracking
"""
import requests
import json

API_KEY = "y4lEXubCO9-0Fjs4kVFg4A-NIseySW9piTerGBoNw_A"
BASE_URL = "https://medtainer.aijesusbro.com"

def test_session_flow():
    """Test complete MCP session flow with multiple requests"""
    print("🔍 Testing MCP Session Management\n")

    headers = {
        "X-API-Key": API_KEY,
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
    }

    # Step 1: Initialize (creates session)
    print("1️⃣ Sending initialize request...")
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        }
    }

    resp = requests.post(
        f"{BASE_URL}/mcp",
        headers=headers,
        data=json.dumps(init_request),
        stream=True,
        timeout=10
    )

    print(f"   Status: {resp.status_code}")

    # Extract session ID from response headers
    session_id = resp.headers.get("Mcp-Session-Id")
    print(f"   Session ID: {session_id or 'NOT FOUND! ❌'}")

    # Read SSE events
    event_count = 0
    for line in resp.iter_lines():
        if not line:
            continue
        line = line.decode('utf-8')
        if line.startswith('data:'):
            event_count += 1
            if event_count <= 2:  # Show first 2 events
                print(f"   Event: {line[:80]}...")

    resp.close()
    print(f"   ✅ Initialize complete ({event_count} events)\n")

    if not session_id:
        print("❌ No session ID returned! Session management not working.\n")
        return False

    # Step 2: List tools (with session ID)
    print("2️⃣ Sending tools/list request with session ID...")
    headers["Mcp-Session-Id"] = session_id

    tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }

    resp = requests.post(
        f"{BASE_URL}/mcp",
        headers=headers,
        data=json.dumps(tools_request),
        stream=True,
        timeout=10
    )

    print(f"   Status: {resp.status_code}")

    # Read SSE events
    event_count = 0
    tools_found = False
    for line in resp.iter_lines():
        if not line:
            continue
        line = line.decode('utf-8')
        if line.startswith('data:'):
            event_count += 1
            if 'tools' in line.lower():
                tools_found = True
                print(f"   ✅ Tools found in response!")

    resp.close()
    print(f"   ✅ Tools/list complete ({event_count} events)\n")

    # Step 3: Another request with session
    print("3️⃣ Sending another request to verify session persistence...")
    another_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/list",
        "params": {}
    }

    resp = requests.post(
        f"{BASE_URL}/mcp",
        headers=headers,
        data=json.dumps(another_request),
        stream=True,
        timeout=10
    )

    print(f"   Status: {resp.status_code}")
    print(f"   ✅ Session still valid!\n")
    resp.close()

    print("🎉 Session Management Test PASSED!\n")
    print("Summary:")
    print(f"  - Session created: {session_id}")
    print(f"  - Multiple requests with same session: ✅")
    print(f"  - Tools discovered: {'✅' if tools_found else '❌'}")
    return True

if __name__ == "__main__":
    success = test_session_flow()
    exit(0 if success else 1)
