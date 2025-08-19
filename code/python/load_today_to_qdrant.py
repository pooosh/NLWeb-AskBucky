# NLWeb/code/python/load_today_to_qdrant.py
import os, argparse, json, uuid, sys
from pathlib import Path
from typing import Iterable
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Environment variable validation
def validate_env():
    required_vars = ["QDRANT_URL", "OPENAI_API_KEY"]
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

JSONLD_DIR = os.getenv("JSONLD_DIR", "../../data/jsonld")
MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
COLL = os.getenv("QDRANT_COLLECTION", "askbucky")

def iter_jsonld_files(root: Path, date_str: str) -> Iterable[Path]:
    for p in root.rglob("*.json"):
        if date_str in str(p):
            yield p
    for p in root.rglob("*.jsonld"):
        if date_str in str(p):
            yield p

def extract_text(obj) -> str:
    if isinstance(obj, dict):
        parts = []
        for k, v in obj.items():
            if k in ("text", "content", "description", "name", "title"):
                if isinstance(v, str): parts.append(v)
            parts.append(extract_text(v))
        return "\n".join([p for p in parts if p])
    if isinstance(obj, list):
        return "\n".join(extract_text(x) for x in obj)
    if isinstance(obj, str):
        return obj
    return ""

def ensure_indexes(client: QdrantClient, coll: str):
    # Idempotent: avoid "index required" errors on filters
    for field in ("sitetag", "doc_id"):
        try:
            client.create_payload_index(
                coll,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD
            )
        except Exception:
            pass  # already exists or server ignores

def file_doc_id(path: str) -> str:
    return Path(path).stem  # e.g., 'gordon-avenue-market_lunch_1849_2025-08-23'

def exists_today_for_doc(client: QdrantClient, coll: str, sitetag: str, doc_id: str) -> bool:
    resp = client.count(
        collection_name=coll,
        count_filter=models.Filter(must=[
            models.FieldCondition(key="sitetag", match=models.MatchValue(value=sitetag)),
            models.FieldCondition(key="doc_id",  match=models.MatchValue(value=doc_id)),
        ]),
        exact=True
    )
    return getattr(resp, "count", 0) > 0

def main():
    # Validate environment variables first
    validate_env()
    
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", required=True)
    ap.add_argument("--yesterday", required=True)
    args = ap.parse_args()

    q_url = os.environ["QDRANT_URL"]
    q_key = os.getenv("QDRANT_API_KEY")
    oai = OpenAI()
    qd = QdrantClient(url=q_url, api_key=q_key, timeout=30.0)
    coll = os.getenv("QDRANT_COLLECTION", "askbucky")
    ensure_indexes(qd, coll)
    
    # ensure collection exists (size must match your embeddings)
    emb_dim = int(os.getenv("EMBEDDING_DIM", "1536"))
    try:
        qd.get_collection(COLL)
    except Exception:
        qd.create_collection(
            collection_name=COLL,
            vectors_config=models.VectorParams(size=emb_dim, distance=models.Distance.COSINE),
            optimizers_config=models.OptimizersConfigDiff(indexing_threshold=1),  # Force immediate indexing
        )
    # ensure filterable fields
    for field, schema in (("sitetag", models.PayloadSchemaType.KEYWORD),
                          ("site",    models.PayloadSchemaType.KEYWORD)):
        try:
            qd.create_payload_index(
                collection_name=COLL,
                field_name=field,
                field_schema=schema,
            )
        except Exception:
            pass  # already exists / non-fatal
    
    # Force indexing for existing collections
    try:
        qd.update_collection(
            collection_name=COLL,
            optimizers_config=models.OptimizersConfigDiff(indexing_threshold=1)
        )
        print(f"Updated collection {COLL} to force immediate indexing")
    except Exception as e:
        print(f"Warning: Could not update collection indexing threshold: {e}")

    # 1) delete only yesterday's points (keep today's for incremental updates)
    yesterday_tag = f"menus_{args.yesterday}"
    try:
        qd.delete(
            collection_name=COLL,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=[
                    models.FieldCondition(
                        key="sitetag",
                        match=models.MatchValue(value=yesterday_tag)
                    )
                ])
            ),
        )
        print(f"deleted sitetag={yesterday_tag}")
    except Exception as e:
        print(f"warn: delete {yesterday_tag} failed: {e}")

    # 2) upsert today’s points
    t_tag = f"menus_{args.today}"
    jsonld_path = Path(JSONLD_DIR)
    if not jsonld_path.exists():
        raise SystemExit(f"JSONLD directory does not exist: {jsonld_path}")
    
    files = list(iter_jsonld_files(jsonld_path, args.today))
    if not files:
        raise SystemExit(f"No JSON-LD found under {jsonld_path} for {args.today}")
    
    print(f"Found {len(files)} JSON-LD files for {args.today}")

    pts = []
    for fp in files:
        # Check if this file already exists for today
        doc_id = file_doc_id(str(fp))
        if exists_today_for_doc(qd, coll, t_tag, doc_id):
            print(f"skip_existing: {doc_id} already embedded for {t_tag}")
            continue
            
        try:
            data = json.loads(fp.read_text())
        except Exception:
            continue
        text = extract_text(data).strip()
        if not text:
            continue
        
        # Generate embedding with error handling
        try:
            response = oai.embeddings.create(model=MODEL, input=text)
            emb = response.data[0].embedding
            if not emb:
                print(f"Warning: Empty embedding for {fp.name}")
                continue
        except Exception as e:
            print(f"Error generating embedding for {fp.name}: {e}")
            continue
        
        # Parse site and meal from filename
        name = fp.name.rsplit(".", 1)[0]
        parts = name.split("_")
        site = parts[0] if len(parts) > 0 else None          # e.g., 'rhetas-market'
        meal = parts[1] if len(parts) > 1 else None          # e.g., 'lunch'
        
        # Extract name from the data
        item_name = ""
        if isinstance(data, dict):
            if "name" in data:
                item_name = data["name"]
            elif "title" in data:
                item_name = data["title"]
            elif "description" in data:
                item_name = data["description"][:100]  # Truncate long descriptions
        
        payload = {
            "sitetag": t_tag,                # menus_YYYY-MM-DD (today)
            "site": site,                    # Site name
            "name": item_name,               # Item name for search results
            "schema_json": json.dumps(data), # Full schema data for search results
            "url": f"file://{fp}",           # URL for search results
            "meal": meal,                    # optional but handy
            "date": args.today,              # explicit date of this load
            "source": str(fp),
            "kind": "nutrislice",
            "doc_id": doc_id,                # File identifier for future skips
        }
        
        pts.append(models.PointStruct(
            id=str(uuid.uuid4()),
            vector=emb,
            payload=payload
        ))

        if len(pts) >= 128:
            qd.upsert(collection_name=COLL, points=pts); pts = []

    if pts:
        qd.upsert(collection_name=COLL, points=pts)

    print(f"loaded {t_tag} from {len(files)} files")

if __name__ == "__main__":
    main()
