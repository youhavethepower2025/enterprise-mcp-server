#!/usr/bin/env python3
"""
Test MCP HTTP+SSE with POST method
Properly simulates Claude Desktop's connection
"""
import requests
import json
import threading
import time

API_KEY = "y4lEXubCO9-0Fjs4kVFg4A-NIseySW9piTerGBoNw_A"
BASE_URL = "https://medtainer.aijesusbro.com"

class MCPClient:
    def __init__(self):
        self.request_id = 0

    def test_connection(self):
        print("🔍 Testing MCP HTTP+SSE Connection (POST method)\n")

        headers = {
            "X-API-Key": API_KEY,
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache"
        }

        # MCP initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        print(f"📤 Sending initialize request to {BASE_URL}/mcp")
        print(f"   Method: POST")
        print(f"   Request: {json.dumps(init_request, indent=2)}\n")

        try:
            # Make POST request with streaming response
            with requests.post(
                f"{BASE_URL}/mcp",
                headers=headers,
                data=json.dumps(init_request),
                stream=True,
                timeout=15
            ) as resp:
                print(f"📊 Response Status: {resp.status_code}")
                print(f"   Content-Type: {resp.headers.get('Content-Type')}\n")

                if resp.status_code != 200:
                    print(f"❌ Connection failed: {resp.text}")
                    return False

                print("✅ SSE stream opened! Reading events...\n")

                event_count = 0
                for line in resp.iter_lines():
                    if not line:
                        continue

                    line = line.decode('utf-8')

                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        try:
                            data = json.loads(data_str)
                            event_count += 1
                            print(f"📨 Event #{event_count}:")
                            print(f"   {json.dumps(data, indent=2)}\n")

                            # Check if we got initialize response
                            if data.get('id') == 1 and 'result' in data:
                                print("✅ Initialize successful!")
                                print(f"   Server: {data['result'].get('serverInfo', {}).get('name')}")
                                print(f"   Version: {data['result'].get('serverInfo', {}).get('version')}")
                                return True

                        except json.JSONDecodeError as e:
                            print(f"⚠️  Failed to parse JSON: {data_str}")

                    # Stop after getting initialize response or 10 events
                    if event_count >= 10:
                        print("⏸️  Stopping after 10 events...")
                        break

        except requests.exceptions.Timeout:
            print("⏱️  Connection timeout")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

        return False

if __name__ == "__main__":
    client = MCPClient()
    success = client.test_connection()

    if success:
        print("\n🎉 MCP connection test PASSED!")
    else:
        print("\n❌ MCP connection test FAILED")
        exit(1)
