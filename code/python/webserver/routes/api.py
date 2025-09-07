"""Core API routes for aiohttp server"""

from aiohttp import web
import logging
import json
import time
import os
from typing import Dict, Any
from methods.whoHandler import WhoHandler
from methods.generate_answer import GenerateAnswer
from webserver.aiohttp_streaming_wrapper import AioHttpStreamingWrapper
from core.retriever import get_vector_db_client
from core.utils.utils import get_param
import analytics

logger = logging.getLogger(__name__)


def setup_api_routes(app: web.Application):
    """Setup core API routes"""
    # Query endpoints
    app.router.add_get('/ask', ask_handler)
    app.router.add_post('/ask', ask_handler)
    
    # Info endpoints
    app.router.add_get('/who', who_handler)
    app.router.add_get('/sites', sites_handler)
    



async def ask_handler(request: web.Request) -> web.Response:
    """Handle /ask endpoint for generating answers"""
    
    # Track request start time for latency measurement
    start_time = time.time()
    
    # Get query parameters
    query_params = dict(request.query)
    
    # For POST requests, merge body parameters
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                body_data = await request.json()
                query_params.update(body_data)
            elif request.content_type == 'application/x-www-form-urlencoded':
                body_data = await request.post()
                query_params.update(dict(body_data))
        except Exception as e:
            logger.warning(f"Failed to parse POST body: {e}")
    
    # Extract key parameters for analytics
    query = get_param(query_params, "query", str, "")
    site = get_param(query_params, "site", str, "all")
    sitetag = get_param(query_params, "sitetag", str, None)
    
    # Check if SSE streaming is requested
    is_sse = request.get('is_sse', False)
    streaming = get_param(query_params, "streaming", str, "True")
    streaming = streaming not in ["False", "false", "0"]
    
    if is_sse or streaming:
        return await handle_streaming_ask(request, query_params, start_time)
    else:
        return await handle_regular_ask(request, query_params, start_time)


async def handle_streaming_ask(request: web.Request, query_params: Dict[str, Any], start_time: float) -> web.StreamResponse:
    """Handle streaming (SSE) ask requests"""
    
    # Create SSE response
    response = web.StreamResponse(
        status=200,
        headers={
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )
    
    await response.prepare(request)
    
    # Log ask started event
    query = get_param(query_params, "query", str, "")
    site = get_param(query_params, "site", str, "all")
    sitetag = get_param(query_params, "sitetag", str, None)
    analytics.log_ask_started(request, response, query, site, sitetag)
    
    # Create aiohttp-compatible wrapper
    wrapper = AioHttpStreamingWrapper(request, response, query_params)
    await wrapper.prepare_response()
    
    try:
        # Determine which handler to use based on generate_mode
        generate_mode = query_params.get('generate_mode', 'none')
        
        if generate_mode == 'generate':
            handler = GenerateAnswer(query_params, wrapper)
            await handler.runQuery()
        else:
            # Use base NLWebHandler for other modes
            from core.baseHandler import NLWebHandler
            handler = NLWebHandler(query_params, wrapper)
            await handler.runQuery()
        
        # Send completion message
        await wrapper.write_stream({"message_type": "complete"})
        
        # Log successful ask answered event
        latency_ms = int((time.time() - start_time) * 1000)
        analytics.log_ask_answered(
            request, response, query, "success", 0, latency_ms, 
            site, sitetag, os.getenv("GEN_MODEL", "gpt-4o-mini")
        )
        
    except Exception as e:
        logger.error(f"Error in streaming ask handler: {e}", exc_info=True)
        await wrapper.send_error_response(500, str(e))
        
        # Log error event
        latency_ms = int((time.time() - start_time) * 1000)
        analytics.log_ask_answered(
            request, response, query, "error", 0, latency_ms,
            site, sitetag, os.getenv("GEN_MODEL", "gpt-4o-mini"), 
            error_message=str(e)
        )
    finally:
        await wrapper.finish_response()
    
    return response


async def handle_regular_ask(request: web.Request, query_params: Dict[str, Any], start_time: float) -> web.Response:
    """Handle non-streaming ask requests"""
    
    query = get_param(query_params, "query", str, "")
    site = get_param(query_params, "site", str, "all")
    sitetag = get_param(query_params, "sitetag", str, None)
    
    try:
        # Log ask started event
        response = web.json_response({})  # Temporary response for analytics
        analytics.log_ask_started(request, response, query, site, sitetag)
        
        # Determine which handler to use
        generate_mode = query_params.get('generate_mode', 'none')
        
        if generate_mode == 'generate':
            handler = GenerateAnswer(query_params, None)
        else:
            from core.baseHandler import NLWebHandler
            handler = NLWebHandler(query_params, None)
        
        # Run the query - it will return the complete response
        result = await handler.runQuery()
        
        # Calculate latency and determine status
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Determine status based on result
        status = "success"
        sources_count = 0
        
        if isinstance(result, dict):
            if result.get("message_type") == "error":
                status = "error"
            elif "items" in result:
                sources_count = len(result.get("items", []))
                if sources_count == 0:
                    status = "empty"
        
        # Create final response
        final_response = web.json_response(result)
        
        # Log ask answered event
        analytics.log_ask_answered(
            request, final_response, query, status, sources_count, latency_ms,
            site, sitetag, os.getenv("GEN_MODEL", "gpt-4o-mini")
        )
        
        return final_response
        
    except Exception as e:
        logger.error(f"Error in regular ask handler: {e}", exc_info=True)
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Create error response
        error_response = web.json_response({
            "message_type": "error",
            "error": str(e)
        }, status=500)
        
        # Log error event
        analytics.log_ask_answered(
            request, error_response, query, "error", 0, latency_ms,
            site, sitetag, os.getenv("GEN_MODEL", "gpt-4o-mini"),
            error_message=str(e)
        )
        
        return error_response


async def who_handler(request: web.Request) -> web.Response:
    """Handle /who endpoint"""
    
    try:
        # Get query parameters
        query_params = dict(request.query)
        
        # Run the who handler
        handler = WhoHandler(query_params, None)
        result = await handler.runQuery()
        
        return web.json_response(result)
        
    except Exception as e:
        logger.error(f"Error in who handler: {e}", exc_info=True)
        return web.json_response({
            "message_type": "error",
            "error": str(e)
        }, status=500)


async def sites_handler(request: web.Request) -> web.Response:
    """Handle /sites endpoint to get available sites"""
    
    try:
        # Get query parameters
        query_params = dict(request.query)
        
        # Check if streaming is requested
        streaming = get_param(query_params, "streaming", str, "False")
        streaming = streaming not in ["False", "false", "0"]
        
        # Create a retriever client
        retriever = get_vector_db_client(query_params=query_params)
        
        # Get the list of sites
        sites = await retriever.get_sites()
        
        # Prepare the response
        response_data = {
            "message-type": "sites",
            "sites": sites
        }
        
        if streaming or request.get('is_sse', False):
            # Return as SSE
            response = web.StreamResponse(
                status=200,
                headers={
                    'Content-Type': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no'
                }
            )
            await response.prepare(request)
            await response.write(f"data: {json.dumps(response_data)}\n\n".encode())
            
            # Log page view for sites endpoint
            sitetag = request.query.get('sitetag')
            analytics.log_page_view(request, response, path="/sites", sitetag=sitetag)
            
            return response
        else:
            # Return as JSON
            response = web.json_response(response_data)
            
            # Log page view for sites endpoint
            sitetag = request.query.get('sitetag')
            analytics.log_page_view(request, response, path="/sites", sitetag=sitetag)
            
            return response
            
    except Exception as e:
        logger.error(f"Error getting sites: {e}", exc_info=True)
        error_data = {
            "message-type": "error",
            "error": f"Failed to get sites: {str(e)}"
        }
        error_response = web.json_response(error_data, status=500)
        
        # Log error
        analytics.log_error(request, error_response, "api", str(e), site="all")
        
        return error_response





