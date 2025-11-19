#!/usr/bin/env python3
"""
Test MCP HTTP+SSE connection to MedTainer
Simulates what Claude Desktop should be doing
"""
import requests
import json
import time
import sys

API_KEY = "y4lEXubCO9-0Fjs4kVFg4A-NIseySW9piTerGBoNw_A"
BASE_URL = "https://medtainer.aijesusbro.com"

def test_sse_connection():
    """Test SSE connection with API key auth"""
    print("🔍 Testing MCP SSE Connection to MedTainer\n")

    # Step 1: Test health endpoint
    print("1️⃣ Testing health endpoint...")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"   ✅ Health check: {resp.json()}\n")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}\n")
        return

    # Step 2: Test discovery endpoints
    print("2️⃣ Testing OAuth discovery endpoints...")
    try:
        resp = requests.get(f"{BASE_URL}/.well-known/oauth-authorization-server", timeout=5)
        print(f"   ✅ Authorization server metadata: {resp.status_code}")

        resp = requests.get(f"{BASE_URL}/.well-known/oauth-protected-resource", timeout=5)
        data = resp.json()
        print(f"   ✅ Protected resource metadata: {json.dumps(data, indent=2)}\n")
    except Exception as e:
        print(f"   ❌ Discovery failed: {e}\n")
        return

    # Step 3: Test SSE connection with API key
    print("3️⃣ Testing SSE connection with API key...")
    print(f"   Connecting to: {BASE_URL}/mcp")

    headers = {
        "X-API-Key": API_KEY,
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache"
    }

    try:
        # Make streaming GET request
        with requests.get(
            f"{BASE_URL}/mcp",
            headers=headers,
            stream=True,
            timeout=10
        ) as resp:
            print(f"   Status: {resp.status_code}")
            print(f"   Content-Type: {resp.headers.get('Content-Type')}")

            if resp.status_code != 200:
                print(f"   ❌ Connection failed: {resp.text}")
                return

            print(f"   ✅ SSE stream opened!\n")

            # Step 4: Read SSE events
            print("4️⃣ Reading SSE events...")
            event_count = 0

            for line in resp.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    print(f"   📨 {line}")
                    event_count += 1

                    # Stop after a few events for testing
                    if event_count >= 3:
                        print("\n   ✅ Received SSE events successfully!")
                        break

            # Step 5: Send MCP initialize request
            print("\n5️⃣ Testing MCP initialize (would need POST with body)...")
            print("   Note: Full bidirectional testing requires separate POST request")

    except requests.exceptions.Timeout:
        print(f"   ⚠️  Connection timeout (server might be waiting for POST body)")
    except Exception as e:
        print(f"   ❌ SSE connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sse_connection()
