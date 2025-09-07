#!/usr/bin/env python3
"""
Analytics module for AskBucky - Privacy-friendly product analytics

This module provides lightweight, privacy-friendly analytics tracking
for user behavior, conversion rates, and performance metrics.
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


def get_or_set_ids(request: web.Request, response: web.StreamResponse) -> tuple[str, str]:
    """
    Get or create user ID and session ID, setting appropriate cookies
    
    Args:
        request: The aiohttp request object
        response: The response object to set cookies on
        
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
    
    # Set/refresh cookies
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


def set_utm_cookies(request: web.Request, response: web.StreamResponse) -> None:
    """
    Set UTM cookies from query parameters if they exist
    
    Args:
        request: The aiohttp request object
        response: The response object to set cookies on
    """
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


def log_page_view(request: web.Request, response: web.StreamResponse, 
                 path: str = "/", sitetag: Optional[str] = None) -> None:
    """
    Log a page view event
    
    Args:
        request: The aiohttp request object
        response: The response object
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


def log_ask_started(request: web.Request, response: web.StreamResponse,
                   query: str, site: str = "all", sitetag: Optional[str] = None) -> None:
    """
    Log when a user starts asking a question
    
    Args:
        request: The aiohttp request object
        response: The response object
        query: The user's query
        site: The site being queried
        sitetag: Current site tag if applicable
    """
    try:
        uid, sid = get_or_set_ids(request, response)
        utm_data = extract_utm_params(request)
        
        log_event(
            "ask_started",
            uid,
            sid,
            query=query,
            query_len=len(query),
            site=site,
            sitetag=sitetag,
            **utm_data
        )
    except Exception as e:
        logger.error(f"Failed to log ask started: {e}")


def log_ask_answered(request: web.Request, response: web.StreamResponse,
                    query: str, status: str, sources_count: int, latency_ms: int,
                    site: str = "all", sitetag: Optional[str] = None,
                    model: str = "gpt-4o-mini", qdrant_hits: int = 0,
                    error_message: Optional[str] = None) -> None:
    """
    Log when a question is answered
    
    Args:
        request: The aiohttp request object
        response: The response object
        query: The user's query
        status: Answer status ('success', 'empty', 'error')
        sources_count: Number of sources found
        latency_ms: Response time in milliseconds
        site: The site being queried
        sitetag: Current site tag if applicable
        model: The LLM model used
        qdrant_hits: Number of hits from Qdrant
        error_message: Error message if status is 'error'
    """
    try:
        uid, sid = get_or_set_ids(request, response)
        utm_data = extract_utm_params(request)
        
        props = {
            "query": query,
            "query_len": len(query),
            "site": site,
            "sitetag": sitetag,
            "status": status,
            "sources_count": sources_count,
            "latency_ms": latency_ms,
            "model": model,
            "qdrant_hits": qdrant_hits,
            **utm_data
        }
        
        if error_message:
            props["error_message"] = error_message
        
        log_event("ask_answered", uid, sid, **props)
    except Exception as e:
        logger.error(f"Failed to log ask answered: {e}")


def log_error(request: web.Request, response: web.StreamResponse,
              error_type: str, error_message: str, 
              query: Optional[str] = None, site: str = "all") -> None:
    """
    Log application errors
    
    Args:
        request: The aiohttp request object
        response: The response object
        error_type: Type of error (e.g., 'validation', 'api', 'internal')
        error_message: Error message
        query: User query if applicable
        site: Site being accessed
    """
    try:
        uid, sid = get_or_set_ids(request, response)
        utm_data = extract_utm_params(request)
        
        props = {
            "error_type": error_type,
            "error_message": error_message,
            "site": site,
            **utm_data
        }
        
        if query:
            props["query"] = query
            props["query_len"] = len(query)
        
        log_event("error", uid, sid, **props)
    except Exception as e:
        logger.error(f"Failed to log error: {e}")


def log_daily_job_status(job_name: str, status: str, duration_ms: int = 0,
                        records_processed: int = 0, error_message: Optional[str] = None) -> None:
    """
    Log daily job execution status
    
    Args:
        job_name: Name of the job (e.g., 'data_load', 'qdrant_sync')
        status: Job status ('success', 'failed', 'partial')
        duration_ms: Job duration in milliseconds
        records_processed: Number of records processed
        error_message: Error message if failed
    """
    try:
        props = {
            "job_name": job_name,
            "status": status,
            "duration_ms": duration_ms,
            "records_processed": records_processed
        }
        
        if error_message:
            props["error_message"] = error_message
        
        log_event("daily_job", "system", "system", **props)
    except Exception as e:
        logger.error(f"Failed to log daily job status: {e}")


def log_qdrant_metrics(hits_count: int, total_points: int, search_time_ms: int,
                      collection_name: str) -> None:
    """
    Log Qdrant performance metrics
    
    Args:
        hits_count: Number of hits returned
        total_points: Total points in collection
        search_time_ms: Search time in milliseconds
        collection_name: Name of the collection searched
    """
    try:
        hit_rate = hits_count / total_points if total_points > 0 else 0
        
        log_event(
            "qdrant_metrics",
            "system",
            "system",
            hits_count=hits_count,
            total_points=total_points,
            hit_rate=hit_rate,
            search_time_ms=search_time_ms,
            collection_name=collection_name
        )
    except Exception as e:
        logger.error(f"Failed to log Qdrant metrics: {e}")


# Analytics middleware for automatic tracking
async def analytics_middleware(request: web.Request, handler):
    """
    Middleware to automatically track page views and set up analytics
    
    Args:
        request: The aiohttp request object
        handler: The next handler in the chain
        
    Returns:
        The response from the handler
    """
    start_time = time.time()
    
    try:
        # Process the request
        response = await handler(request)
        
        # Track page views for GET requests to static content
        if (request.method == 'GET' and 
            not request.path.startswith('/ask') and
            not request.path.startswith('/api/') and
            not request.path.startswith('/health')):
            
            # Get current sitetag if available
            sitetag = request.query.get('sitetag')
            
            # Log page view
            log_page_view(request, response, path=request.path, sitetag=sitetag)
        
        return response
        
    except Exception as e:
        # Log errors
        response = web.json_response({"error": str(e)}, status=500)
        log_error(request, response, "middleware", str(e))
        return response
    finally:
        # Log request timing
        duration_ms = int((time.time() - start_time) * 1000)
        if duration_ms > 1000:  # Log slow requests
            logger.warning(f"Slow request: {request.path} took {duration_ms}ms") 