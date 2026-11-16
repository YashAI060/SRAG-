import os
import sys
import time
import requests
import json
from pathlib import Path

# Add project root to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.security import create_access_token
from datetime import timedelta

DATASETS_DIR = Path(__file__).parent / "datasets_v2"
DOCS_DIR = DATASETS_DIR / "documents"

def get_benchmark_token() -> str:
    # Use the same secret key and algorithm to mint a token for the benchmark tenant
    return create_access_token(
        subject="evaluator",
        role="admin",
        tenant_id="benchmark",
        expires_delta=timedelta(hours=2)
    )

def bootstrap(api_url: str):
    print("============================================================")
    print("BOOTSTRAPPING BENCHMARK CORPUS")
    print("============================================================")
    
    token = get_benchmark_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    with open(DATASETS_DIR / "manifest.json") as f:
        manifest = json.load(f)
        
    print(f"Dataset Version: {manifest['dataset_version']}")
    print(f"Corpus Version: {manifest['corpus_version']}")
    print(f"Tenant ID: benchmark\n")
    
    documents = manifest["documents"]
    doc_ids = []
    
    # 1. Upload Documents
    for doc in documents:
        file_path = DOCS_DIR / doc["file"]
        if not file_path.exists():
            print(f"❌ ERROR: Missing source document {doc['file']} in {DOCS_DIR}")
            sys.exit(1)
            
        print(f"Uploading {doc['file']}...")
        with open(file_path, "rb") as f:
            resp = requests.post(
                f"{api_url}/api/v1/docs/upload",
                headers=headers,
                files={"file": (doc["file"], f, "application/pdf")}
            )
            
        if resp.status_code not in (200, 202):
            print(f"❌ Failed to upload {doc['file']}: {resp.text}")
            sys.exit(1)
            
        result = resp.json()
        doc_ids.append(result["document_id"])
        
        # Prevent Qdrant local SQLite concurrent transaction errors
        time.sleep(1.5)
        
    # 2. Wait for Ingestion
    print("\nWaiting for ingestion to complete...")
    for doc_id in doc_ids:
        start_time = time.time()
        ready = False
        while time.time() - start_time < 60:
            resp = requests.get(f"{api_url}/api/v1/docs/{doc_id}", headers=headers)
            if resp.status_code == 200:
                status = resp.json()["status"]
                if status == "ready":
                    ready = True
                    break
                if status == "failed":
                    print(f"❌ Ingestion failed for doc {doc_id}")
                    sys.exit(1)
            time.sleep(2)
            
        if not ready:
            print(f"❌ Timeout waiting for document {doc_id} to ingest.")
            sys.exit(1)
            
    print("✅ All documents ingested successfully.\n")

if __name__ == "__main__":
    api_url = os.environ.get("API_URL", "http://localhost:8000")
    bootstrap(api_url)
