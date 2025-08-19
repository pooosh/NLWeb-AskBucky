import os
from pathlib import Path

def resolve_qdrant_cfg():
    # Prefer canonical names, fall back to legacy aliases
    url = os.getenv("QDRANT_URL") or os.getenv("QDRANT_CLOUD_URL")
    api = os.getenv("QDRANT_API_KEY") or os.getenv("QDRANT_CLOUD_API_KEY")
    coll = (os.getenv("QDRANT_COLLECTION")
            or os.getenv("QDRANT_CLOUD_COLLECTION")
            or os.getenv("NLWEB_COLLECTION")
            or os.getenv("VECTOR_COLLECTION")
            or "askbucky")
    if url and api:
        return {"mode": "remote", "url": url, "api_key": api, "collection": coll}

    # Only allow local if explicitly opted in
    local_root = (Path(__file__).resolve().parents[2] / "data" / "db")  # .../NLWeb/data/db
    if os.getenv("QDRANT_USE_LOCAL", "").lower() in ("1", "true", "yes"):
        return {"mode": "local", "path": str(local_root), "collection": coll}

    raise ValueError("Qdrant credentials missing: set QDRANT_URL (:6333) and QDRANT_API_KEY") 