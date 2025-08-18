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
    
    # ensure collection exists (size must match your embeddings)
    emb_dim = int(os.getenv("EMBEDDING_DIM", "1536"))
    try:
        qd.get_collection(COLL)
    except Exception:
        qd.create_collection(
            collection_name=COLL,
            vectors_config=models.VectorParams(size=emb_dim, distance=models.Distance.COSINE),
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

    # 1) delete today's and yesterday's points (idempotent)
    for tag in (f"menus_{args.today}", f"menus_{args.yesterday}"):
        try:
            qd.delete(
                collection_name=COLL,
                points_selector=models.FilterSelector(
                    filter=models.Filter(must=[
                        models.FieldCondition(
                            key="sitetag",
                            match=models.MatchValue(value=tag)
                        )
                    ])
                ),
            )
            print(f"deleted sitetag={tag}")
        except Exception as e:
            print(f"warn: delete {tag} failed: {e}")

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
        try:
            data = json.loads(fp.read_text())
        except Exception:
            continue
        text = extract_text(data).strip()
        if not text:
            continue
        emb = oai.embeddings.create(model=MODEL, input=text).data[0].embedding
        
        # Parse site and meal from filename
        name = fp.name.rsplit(".", 1)[0]
        parts = name.split("_")
        site = parts[0] if len(parts) > 0 else None          # e.g., 'rhetas-market'
        meal = parts[1] if len(parts) > 1 else None          # e.g., 'lunch'
        
        payload = {
            "sitetag": t_tag,                # menus_YYYY-MM-DD (today)
            "site": site,                    # <-- add this
            "meal": meal,                    # optional but handy
            "date": args.today,              # explicit date of this load
            "source": str(fp),
            "kind": "nutrislice",
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
