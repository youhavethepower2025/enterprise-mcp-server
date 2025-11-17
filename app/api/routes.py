import redis
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse, RedirectResponse
import json
import asyncio
import logging
import os
import time
from urllib.parse import urlencode

# --- Redis Client Initialization ---
# Assuming Redis is accessible at redis://redis:6380 within the Docker network
# or redis://localhost:6380 if running locally outside Docker Compose
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6380))
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# --- Minimal, From-Scratch OAuth 2.1 Implementation ---

# OAuth credentials for Claude Desktop
CLIENT_ID = "claude-desktop"
CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "medtainer-mcp-secret-2024")  # Load from env
REDIRECT_URI = "https://claude.ai/api/mcp/auth_callback"  # Actual Claude Desktop redirect URI

logger = logging.getLogger(__name__)
router = APIRouter()

# --- OAuth Discovery Endpoints (RFC 9728) ---

@router.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_metadata():
    """
    RFC 8414 - OAuth 2.0 Authorization Server Metadata
    Tells clients where to find OAuth endpoints
    """
    return {
        "issuer": "https://medtainer.aijesusbro.com",
        "authorization_endpoint": "https://medtainer.aijesusbro.com/authorize",
        "token_endpoint": "https://medtainer.aijesusbro.com/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],  # PKCE doesn't require client_secret
    }

@router.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata():
    """
    RFC 9728 - OAuth 2.0 Protected Resource Metadata
    Tells clients where to find the MCP endpoint
    """
    return {
        "resource": "https://medtainer.aijesusbro.com",
        "authorization_servers": ["https://medtainer.aijesusbro.com"],
        "bearer_methods_supported": ["header"],
        "resource_documentation": "https://medtainer.aijesusbro.com",
        "mcp_endpoint": "https://medtainer.aijesusbro.com/mcp",  # Tell Claude where MCP is!
    }

@router.get("/authorize")
async def oauth_authorize(
    request: Request,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    response_type: str,
    code_challenge: str = None,  # PKCE support
    code_challenge_method: str = None  # PKCE support
):
    """
    OAuth 2.1 authorization endpoint with PKCE support.
    Validates client and generates authorization code.
    """
    if client_id != CLIENT_ID:
        raise HTTPException(status_code=400, detail="Invalid client_id")
    if redirect_uri != REDIRECT_URI:
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Invalid response_type")

    # Generate authorization code
    auth_code = os.urandom(16).hex()

    # Store code with PKCE challenge if provided
    code_data = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "code_challenge": code_challenge,  # Store for PKCE validation
        "code_challenge_method": code_challenge_method
    }
    redis_client.setex(f"auth_code:{auth_code}", 600, json.dumps(code_data))

    # Redirect back with authorization code
    params = {
        "code": auth_code,
        "state": state
    }
    return RedirectResponse(url=f"{redirect_uri}?{urlencode(params)}")

@router.post("/token")
async def oauth_token(
    request: Request,
    grant_type: str = Form(...),
    code: str = Form(...),
    redirect_uri: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(None),  # Optional for PKCE
    code_verifier: str = Form(None)  # PKCE code verifier
):
    """
    OAuth 2.1 token endpoint with PKCE support.
    Exchanges authorization code for access token.
    Supports both client_secret and PKCE flows.
    """
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="Invalid grant_type")
    if client_id != CLIENT_ID:
        raise HTTPException(status_code=400, detail="Invalid client_id")
    if redirect_uri != REDIRECT_URI:
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")

    # Retrieve and delete the authorization code from Redis
    code_json = redis_client.get(f"auth_code:{code}")
    if not code_json:
        raise HTTPException(status_code=400, detail="Invalid or expired authorization code")

    auth_code_data = json.loads(code_json)
    redis_client.delete(f"auth_code:{code}") # Code is single-use

    # Validate client_id from stored code data
    if auth_code_data["client_id"] != client_id:
        raise HTTPException(status_code=400, detail="Mismatched client_id")

    # PKCE validation (OAuth 2.1)
    code_challenge = auth_code_data.get("code_challenge")
    if code_challenge:
        # PKCE flow - validate code_verifier
        if not code_verifier:
            raise HTTPException(status_code=400, detail="code_verifier required for PKCE")

        # Verify code_verifier matches code_challenge
        import hashlib
        import base64
        verifier_hash = hashlib.sha256(code_verifier.encode()).digest()
        verifier_challenge = base64.urlsafe_b64encode(verifier_hash).decode().rstrip('=')

        if verifier_challenge != code_challenge:
            raise HTTPException(status_code=400, detail="Invalid code_verifier")
    else:
        # Traditional flow - validate client_secret
        if not client_secret or client_secret != CLIENT_SECRET:
            raise HTTPException(status_code=400, detail="Invalid client_secret")
    if auth_code_data["redirect_uri"] != redirect_uri:
        raise HTTPException(status_code=400, detail="Mismatched redirect_uri")

    # The code is valid, so we can issue an access token.
    access_token = os.urandom(32).hex()
    
    # Store the token in Redis with an expiration (e.g., 1 hour)
    token_data = {
        "client_id": client_id,
        "scope": auth_code_data["scope"]
    }
    redis_client.setex(f"access_token:{access_token}", 3600, json.dumps(token_data)) # 3600 seconds = 1 hour

    # Return the access token
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": auth_code_data["scope"]
    }

# --- MCP Endpoint ---

from app.mcp.tool_registry import registry

async def handle_mcp_request(request_data: dict, response_queue: asyncio.Queue):
    method = request_data.get("method")
    params = request_data.get("params", {})
    request_id = request_data.get("id")

    logger.info(f"Processing MCP method: {method}, id: {request_id}")
    response_data = None

    try:
        if method == "initialize":
            response_data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {},
                        "prompts": {},
                        "logging": {}
                    },
                    "serverInfo": {
                        "name": "medtainer-mcp",
                        "version": "1.3.0" # Version bump
                    }
                }
            }
        elif method == "tools/list":
            enabled_ecosystems = {"gohighlevel", "godaddy", "digitalocean"}
            tools = registry.list_tools()
            filtered_tools = [
                tool for tool in tools
                if tool.get("ecosystem") in enabled_ecosystems
            ]
            response_data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": filtered_tools}
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            result = registry.execute(tool_name, tool_args)
            result_dict = result.model_dump()
            response_data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result_dict
            }
        else:
            response_data = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}", exc_info=True)
        response_data = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }
    
    if response_data:
        await response_queue.put(response_data)

async def read_requests(request: Request, response_queue: asyncio.Queue):
    try:
        async for line in request.stream():
            line = line.decode('utf-8').strip()
            if not line:
                continue

            logger.debug(f"Received raw line: {line}")
            try:
                request_data = json.loads(line)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON: {line}")
                continue

            if "id" in request_data:
                asyncio.create_task(handle_mcp_request(request_data, response_queue))
            else:
                logger.info(f"Received notification: {request_data.get('method')}")

    except Exception as e:
        logger.error(f"Error reading request stream: {e}", exc_info=True)
    finally:
        logger.info("Request stream closed.")
        await response_queue.put(None)

# --- Token Validation Middleware ---
from starlette.middleware.base import BaseHTTPMiddleware

class TokenValidationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/sse":
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return HTMLResponse(status_code=401, content="Unauthorized")
            
            token_string = auth_header.split(" ")[1]
            
            # Check if token exists and is not expired in Redis
            token_json = redis_client.get(f"access_token:{token_string}")
            if not token_json:
                return HTMLResponse(status_code=401, content="Invalid or expired Token")
            
            # Optionally, you could parse token_json here if you stored more data
            # token_data = json.loads(token_json)
            # if token_data["client_id"] != CLIENT_ID:
            #     return HTMLResponse(status_code=401, content="Invalid Token Client")
        
        response = await call_next(request)
        return response

# --- Main SSE Endpoint ---

@router.get("/mcp")  # MCP spec requires /mcp not /sse
async def mcp_endpoint(request: Request):
    """MCP HTTP+SSE endpoint - the official MCP SSE endpoint"""
    return await sse_handler(request)

@router.get("/sse")  # Keep for backward compatibility
async def sse_endpoint(request: Request):
    """Legacy SSE endpoint - redirects to /mcp"""
    return await sse_handler(request)

async def sse_handler(request: Request):
    """
    MCP Server-Sent Events endpoint with dual authentication:
    - Option 1: OAuth Bearer token (for Claude Desktop)
    - Option 2: API Key via X-API-Key header (for direct access)
    """
    # Check for authentication
    auth_header = request.headers.get("authorization", "")
    api_key_header = request.headers.get("x-api-key", "")

    # Debug logging
    logger.info(f"SSE connection attempt - Authorization header: {auth_header[:50] if auth_header else 'None'}")
    logger.info(f"SSE connection attempt - X-API-Key header: {api_key_header[:20] if api_key_header else 'None'}")

    authenticated = False
    auth_method = None

    # Try OAuth token first
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
        logger.debug(f"Checking OAuth token in Redis: access_token:{token[:16]}...")
        token_data_str = redis_client.get(f"access_token:{token}")
        if token_data_str:
            authenticated = True
            auth_method = "oauth"
            logger.info(f"SSE connection authenticated via OAuth token: {token[:8]}...")
        else:
            logger.warning(f"OAuth token not found in Redis: {token[:16]}...")

    # Fall back to API key
    if not authenticated and api_key_header:
        from app.core.config import settings
        if settings.mcp_api_key and api_key_header == settings.mcp_api_key:
            authenticated = True
            auth_method = "api_key"
            logger.info(f"SSE connection authenticated via API key: {api_key_header[:8]}...")

    # Reject if no valid auth
    if not authenticated:
        logger.warning("SSE connection rejected: No valid authentication")
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide either OAuth Bearer token or X-API-Key header"
        )

    logger.info(f"SSE connection established (auth: {auth_method})")
    response_queue = asyncio.Queue()

    async def event_generator():
        read_task = asyncio.create_task(read_requests(request, response_queue))
        
        init_notification = {
            "jsonrpc": "2.0",
            "method": "server/initialized",
            "params": {}
        }
        yield json.dumps(init_notification) + '\n'
        logger.info("Sent server/initialized notification.")

        try:
            while True:
                response_data = await response_queue.get()
                if response_data is None:
                    break
                
                response_str = json.dumps(response_data) + '\n'
                logger.debug(f"Sending response: {response_str.strip()}")
                yield response_str
                
        except asyncio.CancelledError:
            logger.info("Event generator cancelled.")
        finally:
            read_task.cancel()
            logger.info("SSE stream closed.")

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

@router.get("/health")
def health_check() -> dict:
    return {
        "app": "medtainer-mcp",
        "status": "ok",
    }
