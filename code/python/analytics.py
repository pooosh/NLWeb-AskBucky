#!/usr/bin/env python3
"""
CORRECTED Analytics module for AskBucky - Privacy-friendly product analytics

This version uses the proper aiohttp middleware pattern.
"""

import os
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from aiohttp import web
import logging

logger = logging.getLogger(__name__)

# Configuration constants
COOKIE_UID = "ab_uid"
COOKIE_SID = "ab_sid"
SESSION_TTL = 30 * 60  # 30 minutes
COOKIE_MAX_AGE = 31536000  # 1 year for user ID

# UTM parameter tracking
UTM_PARAMS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content']


def _now_iso() -> str:
    """Get current time in ISO format with Z suffix"""
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def get_or_set_ids(request: web.Request, response) -> tuple[str, str]:
    """
    Get or create user ID and session ID, setting appropriate cookies
    
    Args:
        request: The aiohttp request object
        response: The response object to set cookies on (any type)
        
    Returns:
        tuple: (user_id, session_id)
    """
    # Get existing user ID or create new one
    uid = request.cookies.get(COOKIE_UID)
    if not uid:
        uid = f"ab_{uuid.uuid4().hex[:16]}"
    
    # Get existing session ID
    sid = request.cookies.get(COOKIE_SID)
    
    # Check if session is still valid (simple rolling session)
    now = int(time.time())
    if sid:
        try:
            # Extract timestamp from session ID (format: sess_timestamp)
            ts = int(sid.rsplit("_", 1)[-1])
            if now - ts > SESSION_TTL:
                sid = None
        except (ValueError, IndexError):
            sid = None
    
    # Create new session if needed
    if not sid:
        sid = f"sess_{now}"
    
    # Set/refresh cookies - only if response supports it
    try:
        if hasattr(response, 'set_cookie'):
            response.set_cookie(
                COOKIE_UID, 
                uid, 
                max_age=COOKIE_MAX_AGE, 
                httponly=True, 
                secure=True, 
                samesite="Lax"
            )
            response.set_cookie(
                COOKIE_SID, 
                f"{sid}_{now}", 
                max_age=SESSION_TTL, 
                httponly=True, 
                secure=True, 
                samesite="Lax"
            )
    except Exception as e:
        logger.debug(f"Could not set cookies: {e}")
    
    return uid, sid


def extract_utm_params(request: web.Request) -> Dict[str, str]:
    """
    Extract UTM parameters from request query string or cookies
    
    Args:
        request: The aiohttp request object
        
    Returns:
        dict: UTM parameters with default values
    """
    utm_data = {
        'utm_source': 'direct',
        'utm_medium': '(none)',
        'utm_campaign': '(none)',
        'utm_term': '(none)',
        'utm_content': '(none)'
    }
    
    # First check query parameters (for new visits)
    for param in UTM_PARAMS:
        value = request.query.get(param)
        if value:
            utm_data[param] = value
    
    # Then check cookies (for returning visits)
    for param in UTM_PARAMS:
        if utm_data[param] in ['direct', '(none)']:
            cookie_value = request.cookies.get(param)
            if cookie_value:
                utm_data[param] = cookie_value
    
    return utm_data


def set_utm_cookies(request: web.Request, response) -> None:
    """
    Set UTM cookies from query parameters if they exist
    
    Args:
        request: The aiohttp request object
        response: The response object to set cookies on (any type)
    """
    try:
        if not hasattr(response, 'set_cookie'):
            return
            
        for param in UTM_PARAMS:
            value = request.query.get(param)
            if value:
                response.set_cookie(
                    param,
                    value,
                    max_age=COOKIE_MAX_AGE,
                    httponly=True,
                    secure=True,
                    samesite="Lax"
                )
    except Exception as e:
        logger.debug(f"Could not set UTM cookies: {e}")


def log_event(event_name: str, user_id: str, session_id: str, **props) -> None:
    """
    Log an analytics event to stdout (for Cloud Logging ingestion)
    
    Args:
        event_name: Name of the event (e.g., 'page_view', 'ask_answered')
        user_id: Anonymous user identifier
        session_id: Session identifier
        **props: Additional event properties
    """
    event = {
        "type": "event",
        "event_name": event_name,
        "event_time": _now_iso(),
        "user_id": user_id,
        "session_id": session_id,
        "props": props
    }
    
    # Print to stdout as single-line JSON for Cloud Logging
    try:
        print(json.dumps(event, ensure_ascii=False), flush=True)
    except Exception as e:
        logger.error(f"Failed to log analytics event: {e}")


def log_page_view(request: web.Request, response, 
                 path: str = "/", sitetag: Optional[str] = None) -> None:
    """
    Log a page view event
    
    Args:
        request: The aiohttp request object
        response: The response object (any type)
        path: The page path being viewed
        sitetag: Current site tag if applicable
    """
    try:
        uid, sid = get_or_set_ids(request, response)
        set_utm_cookies(request, response)
        
        utm_data = extract_utm_params(request)
        
        log_event(
            "page_view",
            uid,
            sid,
            path=path,
            sitetag=sitetag,
            referrer=request.headers.get("referer", ""),
            user_agent=request.headers.get("user-agent", ""),
            **utm_data
        )
    except Exception as e:
        logger.error(f"Failed to log page view: {e}")


# CORRECTED Analytics middleware using proper aiohttp pattern
@web.middleware
async def analytics_middleware(request: web.Request, handler):
    """
    CORRECTED Analytics middleware for automatic tracking
    
    Uses the proper aiohttp middleware pattern with @web.middleware decorator.
    
    Args:
        request: The aiohttp request object
        handler: The next handler in the chain
        
    Returns:
        The response from the handler
    """
    start_time = time.time()
    
    try:
        # Process the request - ALWAYS call the handler first
        response = await handler(request)
        
        # Track page views for GET requests to static content
        if (request.method == 'GET' and 
            not request.path.startswith('/ask') and
            not request.path.startswith('/api/') and
            not request.path.startswith('/health')):
            
            # Get current sitetag if available
            sitetag = request.query.get('sitetag')
            
            # Log page view - this will handle response type gracefully
            log_page_view(request, response, path=request.path, sitetag=sitetag)
        
        return response
        
    except Exception as e:
        # Log errors without interfering with the response
        logger.error(f"Analytics middleware error: {e}")
        # Re-raise the exception to let other middleware handle it
        raise
    finally:
        # Log request timing
        duration_ms = int((time.time() - start_time) * 1000)
        if duration_ms > 1000:  # Log slow requests
            logger.warning(f"Slow request: {request.path} took {duration_ms}ms")