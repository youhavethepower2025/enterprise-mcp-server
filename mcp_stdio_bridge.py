#!/usr/bin/env python3
"""
MCP stdio bridge for Claude Desktop.

This script acts as a bridge between Claude Desktop (which uses stdio MCP)
and our HTTP-based FastAPI MCP server.
"""

import sys
import json
import logging
from typing import Any, Dict
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Configure logging to stderr (stdout is reserved for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# HTTP server URL
SERVER_URL = "http://localhost:8000"


def send_response(response: Dict[str, Any]) -> None:
    """Send JSON response to stdout."""
    try:
        json.dump(response, sys.stdout)
        sys.stdout.write('\n')
        sys.stdout.flush()
    except BrokenPipeError:
        # Client closed the connection - this is expected during shutdown
        logger.debug("Client closed connection (broken pipe)")
        pass


def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Forward request to HTTP server and return response."""
    try:
        method = request.get("method")
        params = request.get("params", {})

        logger.info(f"Received MCP request: {method}")

        if method == "initialize":
            # Return server capabilities
            # Use the protocol version requested by client, or default to 2024-11-05
            client_protocol = params.get("protocolVersion", "2024-11-05")
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "protocolVersion": client_protocol,
                    "serverInfo": {
                        "name": "medtainer",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": {},
                        "resources": {},  # Automatic context injection
                        "prompts": {}     # Guided workflows
                    }
                }
            }

        elif method == "tools/list":
            # Fetch tools from HTTP server
            with urlopen(f"{SERVER_URL}/mcp/tools", timeout=10.0) as response:
                tools_data = json.loads(response.read().decode())

            # Convert to MCP protocol format
            mcp_tools = []
            for tool in tools_data.get("tools", []):
                tool_name = tool["name"]

                # MCP requires tool names to match ^[a-zA-Z0-9_]{1,64}$
                # Replace dots with underscores to comply with validation
                mcp_tool_name = tool_name.replace(".", "_")

                # Define input schemas for tools that need parameters
                input_schema = {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": True  # Allow any properties
                }

                # Tools that require specific parameters
                if "analyze_contact" in tool_name:
                    input_schema = {
                        "type": "object",
                        "properties": {
                            "contact_id": {
                                "type": "string",
                                "description": "The ID of the contact to analyze"
                            }
                        },
                        "required": ["contact_id"],
                        "additionalProperties": False
                    }
                elif "get_domain" in tool_name and tool_name != "godaddy.list_domains":
                    input_schema = {
                        "type": "object",
                        "properties": {
                            "domain": {
                                "type": "string",
                                "description": "Domain name (e.g., medtainer.com)"
                            }
                        },
                        "required": ["domain"],
                        "additionalProperties": False
                    }
                elif "get_dns_records" in tool_name or "get_mx_records" in tool_name or "get_subdomains" in tool_name or "get_domain_contacts" in tool_name:
                    input_schema = {
                        "type": "object",
                        "properties": {
                            "domain": {
                                "type": "string",
                                "description": "Domain name (e.g., medtainer.com)"
                            }
                        },
                        "required": ["domain"],
                        "additionalProperties": False
                    }
                elif "check_domain_availability" in tool_name:
                    input_schema = {
                        "type": "object",
                        "properties": {
                            "domain": {
                                "type": "string",
                                "description": "Domain name to check (e.g., example.com)"
                            }
                        },
                        "required": ["domain"],
                        "additionalProperties": False
                    }
                elif "contact-deep-dive" in tool_name:
                    input_schema = {
                        "type": "object",
                        "properties": {
                            "contact_name": {
                                "type": "string",
                                "description": "Name of the contact to analyze"
                            }
                        },
                        "required": ["contact_name"],
                        "additionalProperties": False
                    }
                # Action tools - write operations
                elif "create_contact" in tool_name:
                    input_schema = {
                        "type": "object",
                        "properties": {
                            "first_name": {"type": "string", "description": "Contact's first name"},
                            "last_name": {"type": "string", "description": "Contact's last name"},
                            "email": {"type": "string", "description": "Email address"},
                            "phone": {"type": "string", "description": "Phone number"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags to apply"},
                            "source": {"type": "string", "description": "Source of contact"}
                        },
                        "required": ["first_name"],
                        "additionalProperties": True
                    }
                elif "update_contact" in tool_name:
                    input_schema = {
                        "type": "object",
                        "properties": {
                            "contact_id": {"type": "string", "description": "ID of contact to update"},
                            "first_name": {"type": "string", "description": "New first name"},
                            "last_name": {"type": "string", "description": "New last name"},
                            "email": {"type": "string", "description": "New email"},
                            "phone": {"type": "string", "description": "New phone"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags to add"}
                        },
                        "required": ["contact_id"],
                        "additionalProperties": True
                    }
                elif "send_sms" in tool_name:
                    input_schema = {
                        "type": "object",
                        "properties": {
                            "contact_id": {"type": "string", "description": "ID of contact to message"},
                            "message": {"type": "string", "description": "SMS message text"}
                        },
                        "required": ["contact_id", "message"],
                        "additionalProperties": False
                    }
                elif "add_note" in tool_name:
                    input_schema = {
                        "type": "object",
                        "properties": {
                            "contact_id": {"type": "string", "description": "ID of contact"},
                            "note": {"type": "string", "description": "Note text to add"}
                        },
                        "required": ["contact_id", "note"],
                        "additionalProperties": False
                    }
                elif "add_tags" in tool_name:
                    input_schema = {
                        "type": "object",
                        "properties": {
                            "contact_id": {"type": "string", "description": "ID of contact"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags to add"}
                        },
                        "required": ["contact_id", "tags"],
                        "additionalProperties": False
                    }
                elif "remove_tags" in tool_name:
                    input_schema = {
                        "type": "object",
                        "properties": {
                            "contact_id": {"type": "string", "description": "ID of contact"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags to remove"}
                        },
                        "required": ["contact_id", "tags"],
                        "additionalProperties": False
                    }

                mcp_tools.append({
                    "name": mcp_tool_name,
                    "description": tool["description"],
                    "inputSchema": input_schema
                })

            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "tools": mcp_tools
                }
            }

        elif method == "tools/call":
            # Call tool via HTTP server
            mcp_tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            # Convert MCP tool name back to internal format (underscores -> dots)
            # MCP names use underscores (gohighlevel_read_contacts)
            # Internal names use dots (gohighlevel.read_contacts)
            internal_tool_name = mcp_tool_name.replace("_", ".", 1)  # Replace first underscore only

            logger.info(f"Calling tool: {internal_tool_name} (MCP name: {mcp_tool_name}) with args: {tool_args}")

            # Make POST request with JSON body
            req = Request(
                f"{SERVER_URL}/mcp/run/{internal_tool_name}",
                data=json.dumps(tool_args).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urlopen(req, timeout=30.0) as response:
                result = json.loads(response.read().decode())

            # Convert to MCP protocol format
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }

        elif method == "resources/list":
            # Fetch resources from HTTP server
            with urlopen(f"{SERVER_URL}/mcp/resources", timeout=10.0) as response:
                resources_data = json.loads(response.read().decode())

            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "resources": resources_data.get("resources", [])
                }
            }

        elif method == "resources/read":
            # Read specific resource content
            uri = params.get("uri")
            logger.info(f"Reading resource: {uri}")

            # Make GET request to fetch resource content
            with urlopen(f"{SERVER_URL}/mcp/resources/read?uri={uri}", timeout=10.0) as response:
                resource_content = json.loads(response.read().decode())

            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": resource_content.get("mimeType", "text/plain"),
                            "text": resource_content.get("content", "")
                        }
                    ]
                }
            }

        elif method == "prompts/list":
            # Fetch prompts from HTTP server
            with urlopen(f"{SERVER_URL}/mcp/prompts", timeout=10.0) as response:
                prompts_data = json.loads(response.read().decode())

            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "prompts": prompts_data.get("prompts", [])
                }
            }

        elif method == "prompts/get":
            # Get specific prompt
            prompt_name = params.get("name")
            prompt_args = params.get("arguments", {})
            logger.info(f"Getting prompt: {prompt_name}")

            # Make POST request to get prompt
            req = Request(
                f"{SERVER_URL}/mcp/prompts/get",
                data=json.dumps({"name": prompt_name, "arguments": prompt_args}).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urlopen(req, timeout=10.0) as response:
                prompt_result = json.loads(response.read().decode())

            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "messages": prompt_result.get("messages", [])
                }
            }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }

    except Exception as e:
        logger.error(f"Error handling request: {e}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }


def main():
    """Main loop: read from stdin, process, write to stdout."""
    logger.info("MCP stdio bridge starting...")
    logger.info(f"Connecting to HTTP server at {SERVER_URL}")

    try:
        # Read requests from stdin line by line
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)

                # Check if this is a notification (no id field)
                # Notifications should NOT receive responses
                if "id" not in request:
                    logger.info(f"Received notification: {request.get('method')} - no response needed")
                    continue

                response = handle_request(request)
                send_response(response)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
                # Don't send response if we can't even parse the request

    except KeyboardInterrupt:
        logger.info("Bridge shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
