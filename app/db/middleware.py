"""Middleware for logging tool executions to database."""

import time
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
from app.db.session import SessionLocal
from app.db.models import ToolExecution
import logging

logger = logging.getLogger(__name__)


class ToolLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that automatically logs all tool executions to the database.
    
    This intercepts requests to /mcp/run/* endpoints and logs:
    - Tool name
    - Parameters
    - Response
    - Duration
    - Success/failure status
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only log tool execution endpoints
        if not request.url.path.startswith("/mcp/run/"):
            return await call_next(request)

        # Extract tool name from path
        tool_name = request.url.path.replace("/mcp/run/", "")
        
        # Record start time
        start_time = time.time()
        
        # Get request body for logging
        params = None
        if request.method == "POST":
            try:
                body_bytes = await request.body()
                if body_bytes:
                    params = json.loads(body_bytes)
                # Reset body so downstream handlers can read it
            except Exception as e:
                logger.warning(f"Failed to read request body: {e}")

        # Execute the request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Get response body if it's a regular response (not streaming)
        response_data = None
        try:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            if response_body:
                try:
                    response_data = json.loads(response_body.decode())
                except json.JSONDecodeError:
                    response_data = {"raw": response_body.decode(errors="ignore")}

            response = Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        except Exception as e:
            logger.warning(f"Failed to capture response body: {e}")

        # Log to database (in background, don't block response)
        try:
            await self._log_execution(
                tool_name=tool_name,
                params=params,
                response_data=response_data,
                status_code=response.status_code,
                duration_ms=duration_ms
            )
        except Exception as e:
            logger.error(f"Failed to log tool execution: {e}", exc_info=True)
        
        return response

    async def _log_execution(
        self,
        tool_name: str,
        params: dict | None,
        response_data: dict | None,
        status_code: int,
        duration_ms: int
    ):
        """Log execution to database."""
        db = SessionLocal()
        try:
            # Determine status and error message
            status = "success" if 200 <= status_code < 300 else "error"
            error_message = None
            source = "live"
            
            # Extract source from response if available
            if response_data and isinstance(response_data, dict):
                metadata = response_data.get("metadata", {})
                if metadata:
                    source = metadata.get("source", "live")
                
                # Check for errors in response
                if response_data.get("status") == "error":
                    status = "error"
                    error_message = response_data.get("message", "Unknown error")
            
            execution = ToolExecution(
                tool_name=tool_name,
                params=params,
                response=response_data,
                duration_ms=duration_ms,
                status=status,
                error_message=error_message,
                source=source
            )
            db.add(execution)
            db.commit()
            logger.info(
                f"Logged tool execution: {tool_name} "
                f"(status={status}, duration={duration_ms}ms, source={source})"
            )
        except Exception as e:
            logger.error(f"Database logging failed: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()
