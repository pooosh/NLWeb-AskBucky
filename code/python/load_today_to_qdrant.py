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

JSONLD_DIR = os.getenv("JSONLD_DIR", "data/jsonld")
MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
COLL = os.getenv("QDRANT_COLLECTION", "nlweb_documents")

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

    # 1) delete yesterday’s points
    y_tag = f"menus_{args.yesterday}"
    try:
        qd.delete(
            collection_name=COLL,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=[
                    models.FieldCondition(
                        key="sitetag",
                        match=models.MatchValue(value=y_tag)
                    )
                ])
            ),
        )
        print(f"deleted sitetag={y_tag}")
    except Exception as e:
        print(f"warn: delete yesterday failed: {e}")

    # 2) upsert today’s points
    t_tag = f"menus_{args.today}"
    files = list(iter_jsonld_files(Path(JSONLD_DIR), args.today))
    if not files:
        raise SystemExit(f"No JSON-LD found under {JSONLD_DIR} for {args.today}")

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
        pts.append(models.PointStruct(
            id=str(uuid.uuid4()),
            vector=emb,
            payload={"sitetag": t_tag, "source": str(fp), "kind": "nutrislice"}
        ))

        if len(pts) >= 128:
            qd.upsert(collection_name=COLL, points=pts); pts = []

    if pts:
        qd.upsert(collection_name=COLL, points=pts)

    print(f"loaded {t_tag} from {len(files)} files")

if __name__ == "__main__":
    main()
