# Copyright (c) 2025 Microsoft Corporation.
# Licensed under the MIT License

"""
Entry point for the NLWeb Sample App with aiohttp server.

WARNING: This code is under development and may undergo changes in future releases.
Backwards compatibility is not guaranteed at this time.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from aiohttp import web
from qdrant_store import search as qsearch

QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")

qdrant = None
if QDRANT_URL:
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=30.0)


async def main():
    # Load environment variables from .env file (useful locally)
    load_dotenv()

    # Suppress verbose HTTP client logging from OpenAI SDK
    import logging
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    # Suppress Azure SDK HTTP logging
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
    logging.getLogger("azure").setLevel(logging.WARNING)

    # Suppress webserver middleware INFO logs
    logging.getLogger("webserver.middleware.logging_middleware").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)

    # Initialize router
    import core.router as router
    router.init()

    # Initialize LLM providers
    import core.llm as llm
    llm.init()

    # Initialize retrieval clients
    import core.retriever as retriever
    retriever.init()

    # Read host/port for Cloud Run (and local dev fallback)
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))

    from webserver.aiohttp_server import AioHTTPServer
    server = AioHTTPServer()

    print(f"Starting aiohttp server on {host}:{port} ...")

    # Add search routes to the app
    routes = web.RouteTableDef()

    @routes.get("/v1/search")
    async def http_search(request: web.Request):
        q = request.query.get("q", "").strip()
        sitetag = request.query.get("sitetag")
        if not q:
            return web.json_response({"error": "missing q"}, status=400)
        hits = qsearch(q, top_k=8, sitetag=sitetag)
        out = []
        for h in hits:
            out.append({
                "id": str(h.id),
                "score": h.score,
                "payload": h.payload,
            })
        return web.json_response({"results": out})

    # Get the app instance and add routes
    app = await server.create_app()
    app.add_routes(routes)

    # Prefer explicit host/port; fall back to env-only if older signature
    try:
        await server.start(host=host, port=port)  # if supported by your AioHTTPServer
    except TypeError:
        # Back-compat path: some versions only read env vars internally
        os.environ["HOST"] = host
        os.environ["PORT"] = str(port)
        await server.start()


if __name__ == "__main__":
    asyncio.run(main())