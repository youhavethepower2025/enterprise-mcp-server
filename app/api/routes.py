import redis
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse, RedirectResponse, Response
import json
import asyncio
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
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

# --- MCP Session Management (Streamable HTTP) ---
# Sessions track client state across multiple POST requests
# Key: session_id -> Value: {client_info, created_at, last_activity}
mcp_sessions = {}

def create_session(client_info: dict) -> str:
    """Create a new MCP session and return session ID"""
    session_id = str(uuid.uuid4())
    mcp_sessions[session_id] = {
        "client_info": client_info,
        "created_at": datetime.utcnow(),
        "last_activity": datetime.utcnow()
    }
    logger.info(f"Created MCP session: {session_id}")
    return session_id

def get_session(session_id: str) -> dict:
    """Get session by ID, update last_activity"""
    if session_id in mcp_sessions:
        mcp_sessions[session_id]["last_activity"] = datetime.utcnow()
        return mcp_sessions[session_id]
    return None

def cleanup_old_sessions():
    """Remove sessions older than 1 hour"""
    cutoff = datetime.utcnow() - timedelta(hours=1)
    to_remove = [sid for sid, sess in mcp_sessions.items()
                 if sess["last_activity"] < cutoff]
    for sid in to_remove:
        del mcp_sessions[sid]
        logger.info(f"Cleaned up expired session: {sid}")

# --- OAuth Discovery Endpoints (RFC 9728) ---

@router.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_metadata():
    """
    RFC 8414 - OAuth 2.0 Authorization Server Metadata
    Tells clients where to find OAuth endpoints
    """
    base_url = "https://medtainer.aijesusbro.com"
    metadata = {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/authorize",
        "token_endpoint": f"{base_url}/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],  # ✅ Added refresh_token
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": ["read", "write"],  # ✅ FIXED: Standard scopes like working example
        "resource_parameter_supported": True  # ✅ NEW: MCP-specific claim
    }
    logger.info(f"OAuth Authorization Server Metadata requested - returning: {json.dumps(metadata, indent=2)}")
    return metadata

@router.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata():
    """
    RFC 9728 - OAuth 2.0 Protected Resource Metadata
    Tells clients where to connect with Bearer token
    CRITICAL: resource MUST match the MCP endpoint URL exactly (June 2025 spec)
    """
    base_url = "https://medtainer.aijesusbro.com"
    mcp_endpoint = f"{base_url}/mcp"
    return {
        "resource": mcp_endpoint,
        "authorization_servers": [base_url],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["read", "write"],
        "mcp_endpoints": [mcp_endpoint]  # Array format per latest research
    }

@router.get("/.well-known/oauth-protected-resource/mcp")
async def oauth_protected_resource_metadata_mcp():
    """
    RFC 9728 path-suffixed discovery endpoint.
    Claude client probes this path before falling back to root.
    Returns identical metadata to root endpoint.
    """
    logger.info("OAuth Protected Resource Metadata requested (MCP-suffixed path)")
    return await oauth_protected_resource_metadata()

@router.get("/.well-known/oauth-authorization-server/mcp")
async def oauth_authorization_server_metadata_mcp():
    """
    RFC 9728 path-suffixed discovery endpoint.
    Claude client probes this path before falling back to root.
    Returns identical metadata to root endpoint.
    """
    logger.info("OAuth Authorization Server Metadata requested (MCP-suffixed path)")
    return await oauth_authorization_server_metadata()

@router.api_route("/authorize", methods=["GET", "POST"])
async def oauth_authorize(
    request: Request,
    client_id: str = Form(None),
    redirect_uri: str = Form(None),
    scope: str = Form(None),
    state: str = Form(None),
    response_type: str = Form(None),
    code_challenge: str = Form(None),  # PKCE support
    code_challenge_method: str = Form(None)  # PKCE support
):
    """
    OAuth 2.1 authorization endpoint with PKCE support.
    Accepts both GET (query params) and POST (form data) requests.
    Validates client and generates authorization code.
    """
    # Extract parameters from query string if not in form (GET request)
    if client_id is None:
        params = dict(request.query_params)
        client_id = params.get("client_id")
        redirect_uri = params.get("redirect_uri")
        scope = params.get("scope")
        state = params.get("state")
        response_type = params.get("response_type")
        code_challenge = params.get("code_challenge")
        code_challenge_method = params.get("code_challenge_method")

    logger.info(f"=== OAUTH AUTHORIZE START === method={request.method}, client_id={client_id}, scope={scope}")
    logger.debug(f"redirect_uri={redirect_uri}, response_type={response_type}, state={state[:20] if state else 'None'}...")
    logger.debug(f"PKCE: code_challenge={code_challenge[:20] if code_challenge else 'None'}..., method={code_challenge_method}")

    if client_id != CLIENT_ID:
        logger.error(f"=== OAUTH ERROR === Invalid client_id: {client_id} (expected: {CLIENT_ID})")
        raise HTTPException(status_code=400, detail="Invalid client_id")
    if redirect_uri != REDIRECT_URI:
        logger.error(f"=== OAUTH ERROR === Invalid redirect_uri: {redirect_uri} (expected: {REDIRECT_URI})")
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")
    if response_type != "code":
        logger.error(f"=== OAUTH ERROR === Invalid response_type: {response_type} (expected: code)")
        raise HTTPException(status_code=400, detail="Invalid response_type")

    # Generate authorization code
    auth_code = os.urandom(16).hex()
    logger.info(f"=== OAUTH CODE GENERATED === code={auth_code[:16]}...")

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
    logger.info(f"=== OAUTH CODE STORED === Stored in Redis with 600s TTL")
    logger.debug(f"Code data: {json.dumps(code_data, indent=2)}")

    # Redirect back with authorization code
    params = {
        "code": auth_code,
        "state": state
    }
    redirect_url = f"{redirect_uri}?{urlencode(params)}"
    logger.info(f"=== OAUTH REDIRECT === Redirecting to: {redirect_url[:100]}...")
    return RedirectResponse(url=redirect_url)

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
    logger.info(f"=== OAUTH TOKEN START === grant_type={grant_type}, client_id={client_id}")
    logger.debug(f"code={code[:16]}..., redirect_uri={redirect_uri}")
    logger.debug(f"Has client_secret: {client_secret is not None}, Has code_verifier: {code_verifier is not None}")

    if grant_type != "authorization_code":
        logger.error(f"=== OAUTH ERROR === Invalid grant_type: {grant_type}")
        raise HTTPException(status_code=400, detail="Invalid grant_type")
    if client_id != CLIENT_ID:
        logger.error(f"=== OAUTH ERROR === Invalid client_id: {client_id}")
        raise HTTPException(status_code=400, detail="Invalid client_id")
    if redirect_uri != REDIRECT_URI:
        logger.error(f"=== OAUTH ERROR === Invalid redirect_uri: {redirect_uri}")
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")

    # Retrieve and delete the authorization code from Redis
    logger.debug(f"=== REDIS LOOKUP === Checking for auth_code:{code[:16]}...")
    code_json = redis_client.get(f"auth_code:{code}")
    if not code_json:
        logger.error(f"=== OAUTH ERROR === Authorization code not found or expired: {code[:16]}...")
        raise HTTPException(status_code=400, detail="Invalid or expired authorization code")

    auth_code_data = json.loads(code_json)
    logger.info(f"=== OAUTH CODE FOUND === Retrieved code data from Redis")
    logger.debug(f"Code data: {json.dumps(auth_code_data, indent=2)}")

    redis_client.delete(f"auth_code:{code}") # Code is single-use
    logger.debug(f"=== REDIS DELETE === Authorization code deleted (single-use)")

    # Validate client_id from stored code data
    if auth_code_data["client_id"] != client_id:
        logger.error(f"=== OAUTH ERROR === Mismatched client_id in stored code")
        raise HTTPException(status_code=400, detail="Mismatched client_id")

    # PKCE validation (OAuth 2.1)
    code_challenge = auth_code_data.get("code_challenge")
    if code_challenge:
        logger.info(f"=== PKCE VALIDATION === Code challenge present, validating verifier")
        # PKCE flow - validate code_verifier
        if not code_verifier:
            logger.error(f"=== PKCE ERROR === No code_verifier provided but code_challenge exists")
            raise HTTPException(status_code=400, detail="code_verifier required for PKCE")

        # Verify code_verifier matches code_challenge
        import hashlib
        import base64
        verifier_hash = hashlib.sha256(code_verifier.encode()).digest()
        verifier_challenge = base64.urlsafe_b64encode(verifier_hash).decode().rstrip('=')

        logger.debug(f"Expected challenge: {code_challenge[:20]}...")
        logger.debug(f"Computed challenge: {verifier_challenge[:20]}...")

        if verifier_challenge != code_challenge:
            logger.error(f"=== PKCE ERROR === Code verifier does not match challenge")
            raise HTTPException(status_code=400, detail="Invalid code_verifier")
        logger.info(f"=== PKCE SUCCESS === Code verifier validated")
    else:
        logger.info(f"=== TRADITIONAL AUTH === No PKCE, validating client_secret")
        # Traditional flow - validate client_secret
        if not client_secret or client_secret != CLIENT_SECRET:
            logger.error(f"=== OAUTH ERROR === Invalid or missing client_secret")
            raise HTTPException(status_code=400, detail="Invalid client_secret")
        logger.info(f"=== CLIENT SECRET SUCCESS === Secret validated")

    if auth_code_data["redirect_uri"] != redirect_uri:
        logger.error(f"=== OAUTH ERROR === Mismatched redirect_uri in code data")
        raise HTTPException(status_code=400, detail="Mismatched redirect_uri")

    # The code is valid, so we can issue an access token.
    access_token = os.urandom(32).hex()
    logger.info(f"=== ACCESS TOKEN GENERATED === token={access_token[:16]}...")

    # CRITICAL FIX (Nov 2025): Generate refresh_token per GitHub Issue #11814
    # Claude Desktop expects refresh_token even if not used
    refresh_token = os.urandom(32).hex()
    logger.info(f"=== REFRESH TOKEN GENERATED === token={refresh_token[:16]}...")

    # CRITICAL FIX (Nov 2025): Add aud (audience) claim per GitHub Issue #11814
    # The aud claim must match the resource URL from .well-known/oauth-protected-resource
    base_url = "https://medtainer.aijesusbro.com"
    mcp_endpoint = f"{base_url}/mcp"

    # Store the token in Redis with an expiration (e.g., 1 hour)
    # CRITICAL FIX: Add all required JWT claims per OAuth 2.1 + JWT spec
    # Claude Desktop validates these claims locally before attempting connection
    import time
    current_time = int(time.time())
    token_data = {
        "iss": base_url,  # ✅ Issuer - must match issuer in /.well-known/oauth-authorization-server
        "sub": client_id,  # ✅ Subject - identity of the token holder (client in this case)
        "aud": mcp_endpoint,  # ✅ Audience - must match resource URL
        "iat": current_time,  # ✅ Issued At - timestamp when token was created
        "exp": current_time + 3600,  # ✅ Expiration - token expires in 1 hour
        "client_id": client_id,
        "scope": auth_code_data["scope"]
    }
    redis_client.setex(f"access_token:{access_token}", 3600, json.dumps(token_data)) # 3600 seconds = 1 hour

    # Store refresh token with longer expiration (7 days)
    refresh_token_data = {
        "client_id": client_id,
        "scope": auth_code_data["scope"],
        "access_token": access_token
    }
    redis_client.setex(f"refresh_token:{refresh_token}", 604800, json.dumps(refresh_token_data)) # 7 days

    logger.info(f"=== ACCESS TOKEN STORED === Stored in Redis with 3600s TTL")
    logger.info(f"=== REFRESH TOKEN STORED === Stored in Redis with 604800s TTL (7 days)")
    logger.debug(f"Token data: {json.dumps(token_data, indent=2)}")

    # Return the access token
    response = {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": refresh_token,  # ✅ CRITICAL: Include refresh_token
        "scope": auth_code_data["scope"].strip()  # ✅ FIXED: Strip whitespace from scope
    }
    logger.info(f"=== OAUTH TOKEN SUCCESS === Returning access token + refresh token to client")
    logger.info(f"=== TOKEN RESPONSE === {json.dumps(response, indent=2)}")

    # CRITICAL FIX (Nov 2025): Ensure strict application/json Content-Type
    from fastapi.responses import JSONResponse
    return JSONResponse(content=response, media_type="application/json")

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

@router.head("/mcp")  # ✅ Handle HEAD probe requests
async def mcp_endpoint_head(request: Request):
    """
    Handle HEAD requests to /mcp.
    Returns 200 OK to indicate endpoint exists.
    OAuth discovery happens via WWW-Authenticate header, but HEAD should succeed
    to allow Claude to proceed to POST/GET with Bearer token.
    """
    auth_header = request.headers.get("authorization", "")

    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        token_data_str = redis_client.get(f"access_token:{token}")
        if token_data_str:
            logger.info(f"=== HEAD /mcp === Authenticated request with valid token - returning 200")
            from fastapi import Response
            return Response(status_code=200)

    # ✅ CRITICAL FIX per Gemini research: Unauthenticated HEAD must return 401
    # This tells Claude "this resource is protected, use the token you just got"
    # Returning 200 confuses Claude into thinking the endpoint is public
    logger.info(f"=== HEAD /mcp === Unauthenticated - returning 401 to trigger token usage")
    from fastapi import Response
    return Response(
        status_code=401,
        headers={
            "WWW-Authenticate": f'Bearer realm="MCP Server", resource_metadata_uri="https://medtainer.aijesusbro.com/.well-known/oauth-protected-resource"'
        }
    )

@router.post("/mcp")  # MCP HTTP+SSE requires POST for bidirectional streaming
async def mcp_endpoint_post(request: Request):
    """MCP HTTP+SSE endpoint - POST for client requests"""
    return await sse_handler(request)

@router.get("/mcp")  # MCP spec: GET for server-initiated notifications
async def mcp_endpoint_get(request: Request):
    """MCP HTTP+SSE endpoint - GET for server→client notifications (SSE stream)"""
    logger.info("GET /mcp - Server-initiated notification stream requested")
    return await sse_handler(request)

@router.post("/sse")  # Keep for backward compatibility
async def sse_endpoint_post(request: Request):
    """Legacy SSE endpoint - POST method"""
    return await sse_handler(request)

@router.get("/sse")  # Keep for backward compatibility
async def sse_endpoint(request: Request):
    """Legacy SSE endpoint - GET method"""
    return await sse_handler(request)

async def sse_handler(request: Request):
    """
    MCP Server-Sent Events endpoint with dual authentication:
    - Option 1: OAuth Bearer token (for Claude Desktop)
    - Option 2: API Key via X-API-Key header (for direct access)
    """
    # === LOGGING ENHANCEMENT: Connection Metadata ===
    client_ip = request.client.host if request.client else "unknown"
    request_method = request.method
    request_path = request.url.path

    logger.info(f"=== MCP SSE CONNECTION START === Method: {request_method}, Path: {request_path}, Client: {client_ip}")

    # Log all headers (sanitized)
    logger.debug("Request headers:")
    for header_name, header_value in request.headers.items():
        # Sanitize sensitive headers
        if header_name.lower() in ['authorization', 'x-api-key']:
            safe_value = header_value[:20] + "..." if len(header_value) > 20 else header_value
            logger.debug(f"  {header_name}: {safe_value}")
        else:
            logger.debug(f"  {header_name}: {header_value}")

    # Log Accept header for debugging but don't reject
    accept_header = request.headers.get("accept", "")
    logger.info(f"=== ACCEPT HEADER === {accept_header}")

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
        logger.info(f"=== OAUTH FLOW === Attempting OAuth token validation")
        logger.debug(f"Checking OAuth token in Redis: access_token:{token[:16]}...")
        token_data_str = redis_client.get(f"access_token:{token}")
        if token_data_str:
            authenticated = True
            auth_method = "oauth"
            logger.info(f"=== OAUTH SUCCESS === Token valid: {token[:8]}...")
            logger.debug(f"Token data from Redis: {token_data_str}")
        else:
            logger.warning(f"=== OAUTH FAILURE === Token not found in Redis: {token[:16]}...")
            # Check if there are ANY tokens in Redis
            all_keys = redis_client.keys("access_token:*")
            logger.debug(f"Total access tokens in Redis: {len(all_keys)}")
            if all_keys:
                logger.debug(f"Sample token keys: {all_keys[:3]}")

    # Fall back to API key
    if not authenticated and api_key_header:
        logger.info(f"=== API KEY FLOW === Attempting API key validation")
        from app.core.config import settings
        if settings.mcp_api_key and api_key_header == settings.mcp_api_key:
            authenticated = True
            auth_method = "api_key"
            logger.info(f"=== API KEY SUCCESS === Key valid: {api_key_header[:8]}...")
        else:
            logger.warning(f"=== API KEY FAILURE === Invalid key: {api_key_header[:8]}...")

    # Reject if no valid auth
    if not authenticated:
        logger.warning("=== AUTH REJECTED === No valid authentication method")
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide either OAuth Bearer token or X-API-Key header"
        )

    logger.info(f"=== AUTH SUCCESS === Method: {auth_method}")
    response_queue = asyncio.Queue()

    # --- MCP Session Management (Streamable HTTP) ---
    session_id = request.headers.get("Mcp-Session-Id")
    session = None
    is_initialize = False

    logger.info(f"=== SESSION MANAGEMENT === Checking for existing session")
    if session_id:
        session = get_session(session_id)
        logger.info(f"=== SESSION === Request with session ID: {session_id} (valid: {session is not None})")
        if session:
            logger.debug(f"Session data: {session}")
    else:
        logger.info("=== SESSION === No session ID provided (likely initialize or first request)")

    # Read POST body FIRST before starting SSE stream
    body_bytes = await request.body()
    logger.info(f"=== REQUEST BODY === Received {len(body_bytes)} bytes")

    if len(body_bytes) > 0:
        logger.debug(f"Body preview (first 200 chars): {body_bytes[:200]}")
    else:
        logger.warning("=== WARNING === Empty request body - client may send requests via separate POST")

    # Parse JSON-RPC requests from body
    initial_requests = []
    if body_bytes:
        try:
            body_text = body_bytes.decode('utf-8')
            logger.debug(f"Body text length: {len(body_text)} chars")
            # Handle single JSON object or NDJSON (multiple lines)
            lines = body_text.strip().split('\n')
            logger.debug(f"Split into {len(lines)} lines")
            for i, line in enumerate(lines):
                if line.strip():
                    req = json.loads(line)
                    initial_requests.append(req)
                    logger.info(f"=== REQUEST PARSED === Line {i}: method={req.get('method')}, id={req.get('id')}")
                    # Check if this is an initialize request
                    if req.get('method') == 'initialize':
                        is_initialize = True
                        logger.info(f"=== INITIALIZE DETECTED === Found initialize request with params: {req.get('params', {})}")
            logger.info(f"=== TOTAL REQUESTS === Parsed {len(initial_requests)} requests (is_initialize={is_initialize})")
        except Exception as e:
            logger.error(f"=== PARSE ERROR === Failed to parse request body: {e}", exc_info=True)

    async def event_generator():
        event_id = 0
        last_keepalive = time.time()
        keepalive_interval = 15  # Send keepalive every 15 seconds
        logger.info(f"=== SSE STREAM START === Beginning event generation with keepalive every {keepalive_interval}s")

        # Per MCP spec: Send priming event with ID and empty data for reconnection support
        yield f"id: {event_id}\n:\n\n"
        logger.info(f"=== SSE EVENT {event_id} === Sent priming event (empty comment for reconnection)")
        event_id += 1

        # Send endpoint event (MCP convention)
        endpoint_event = {
            "jsonrpc": "2.0",
            "method": "endpoint",
            "params": {
                "uri": "https://medtainer.aijesusbro.com/mcp"
            }
        }
        yield f"id: {event_id}\ndata: {json.dumps(endpoint_event)}\n\n"
        logger.info(f"=== SSE EVENT {event_id} === Sent endpoint event: {endpoint_event}")
        event_id += 1

        # Process initial requests in background task so responses can be sent immediately
        async def process_requests():
            try:
                logger.info(f"=== PROCESSING START === Processing {len(initial_requests)} initial requests")
                if len(initial_requests) == 0:
                    logger.warning("=== NO INITIAL REQUESTS === No requests in body to process")
                for i, req in enumerate(initial_requests):
                    logger.info(f"=== PROCESSING REQUEST {i+1}/{len(initial_requests)} === method={req.get('method')}, id={req.get('id')}")
                    await handle_mcp_request(req, response_queue)
                    logger.info(f"=== REQUEST PROCESSED === Response queued for request {req.get('id')}")
                logger.info(f"=== PROCESSING COMPLETE === All {len(initial_requests)} requests processed")
            except Exception as e:
                logger.error(f"=== PROCESSING ERROR === Error processing requests: {e}", exc_info=True)

        # Start processing requests in background
        process_task = asyncio.create_task(process_requests())
        logger.info(f"=== BACKGROUND TASK === Started processing task")

        try:
            # Send responses as they're queued AND send keepalives to keep connection alive
            loop_count = 0
            keepalive_count = 0
            logger.info(f"=== RESPONSE LOOP START === Waiting for responses from queue (with keepalive)")

            while True:
                loop_count += 1
                if loop_count % 100 == 0:  # Log every 100 iterations (less noise)
                    logger.debug(f"=== LOOP ITERATION {loop_count} === Stream alive, keepalives sent: {keepalive_count}")

                # Wait for response with 1 second timeout to check for keepalive needs
                try:
                    response_data = await asyncio.wait_for(response_queue.get(), timeout=1.0)

                    if response_data is None:
                        logger.info(f"=== STREAM CLOSING === Received None signal from queue (client disconnect)")
                        break

                    # SSE format with event ID: "id: N\ndata: <json>\n\n"
                    response_str = f"id: {event_id}\ndata: {json.dumps(response_data)}\n\n"
                    logger.info(f"=== SSE EVENT {event_id} === Sending response for request_id={response_data.get('id')}")
                    logger.debug(f"Response data: {json.dumps(response_data, indent=2)}")
                    yield response_str
                    event_id += 1
                    last_keepalive = time.time()  # Reset keepalive timer after sending data

                except asyncio.TimeoutError:
                    # No response in queue - check if we need to send keepalive
                    current_time = time.time()
                    if current_time - last_keepalive >= keepalive_interval:
                        # Send keepalive comment (SSE spec: lines starting with : are ignored by client)
                        yield ": keepalive\n\n"
                        keepalive_count += 1
                        last_keepalive = current_time
                        logger.debug(f"=== KEEPALIVE {keepalive_count} === Sent keepalive comment to maintain connection")

                    # DON'T break - keep the stream alive!
                    # The stream should only close when:
                    # 1. Client disconnects (response_data is None)
                    # 2. Connection error occurs (caught in except blocks)
                    # 3. Client cancels the request (asyncio.CancelledError)
                    continue

        except asyncio.CancelledError:
            logger.info("=== STREAM CANCELLED === Event generator cancelled by client")
            process_task.cancel()
        except Exception as e:
            logger.error(f"=== STREAM ERROR === Unexpected error in event generator: {e}", exc_info=True)
        finally:
            logger.info(f"=== SSE STREAM END === Stream closed after sending {event_id} events and {keepalive_count} keepalives")
            logger.info(f"=== STREAM STATS === Loop iterations: {loop_count}, Total duration: {time.time() - (last_keepalive - keepalive_interval * keepalive_count):.1f}s")

    # Create session for initialize requests
    response_headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"  # Disable nginx buffering
    }

    logger.info(f"=== RESPONSE HEADERS === Preparing response headers")
    logger.debug(f"Headers: {response_headers}")

    if is_initialize:
        # Create new MCP session
        client_info = initial_requests[0].get('params', {}).get('clientInfo', {}) if initial_requests else {}
        new_session_id = create_session({
            "client_info": client_info,
            "auth_method": auth_method
        })
        response_headers["Mcp-Session-Id"] = new_session_id
        logger.info(f"=== SESSION CREATED === New session ID: {new_session_id}")
        logger.debug(f"Client info: {client_info}")
    else:
        logger.info(f"=== NO SESSION CREATED === Not an initialize request")

    logger.info(f"=== RETURNING STREAMING RESPONSE === Starting SSE stream with media_type=text/event-stream")
    logger.debug(f"Final response headers: {response_headers}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=response_headers
    )

@router.get("/")
@router.head("/")
async def root_endpoint(request: Request):
    """
    Root endpoint handler - Returns 401 to trigger OAuth discovery.
    Per MCP spec, unauthenticated requests should get 401 with WWW-Authenticate header.
    """
    # Check if request has valid Bearer token
    auth_header = request.headers.get("authorization", "")

    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        token_data_str = redis_client.get(f"access_token:{token}")
        if token_data_str:
            # Valid token - return OK
            logger.info(f"=== ROOT ACCESS === Authenticated request to / with valid token")
            return {
                "app": "medtainer-mcp",
                "status": "ok",
                "authenticated": True
            }

    # No valid auth - return 401 to trigger OAuth
    logger.info(f"=== ROOT ACCESS === Unauthenticated {request.method} / - returning 401 to trigger OAuth")
    from fastapi import Response
    return Response(
        status_code=401,
        headers={
            "WWW-Authenticate": f'Bearer realm="MCP Server", resource_metadata_uri="https://medtainer.aijesusbro.com/.well-known/oauth-protected-resource"'
        },
        content="Authentication required"
    )

@router.get("/health")
def health_check() -> dict:
    return {
        "app": "medtainer-mcp",
        "status": "ok",
    }
