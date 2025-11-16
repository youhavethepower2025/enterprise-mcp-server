"""
Production-grade authentication middleware for MedTainer MCP Server
"""

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Verify API key from Authorization header.

    Expected format: Authorization: Bearer <API_KEY>

    Args:
        credentials: HTTPAuthorizationCredentials from FastAPI Security

    Returns:
        The validated API key

    Raises:
        HTTPException: 401 if key is missing or invalid
    """
    if not credentials:
        logger.warning("Missing authorization credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get the token from credentials
    provided_key = credentials.credentials

    # Get the valid API key from settings
    valid_key = settings.mcp_api_key

    if not valid_key:
        logger.error("MCP_API_KEY not configured in environment")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication not configured"
        )

    # Constant-time comparison to prevent timing attacks
    if not secrets_compare(provided_key, valid_key):
        logger.warning(f"Invalid API key attempt: {provided_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"API key validated: {provided_key[:8]}...")
    return provided_key


def secrets_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing attacks.

    Args:
        a: First string
        b: Second string

    Returns:
        True if strings are equal, False otherwise
    """
    import hmac
    return hmac.compare_digest(a.encode(), b.encode())
