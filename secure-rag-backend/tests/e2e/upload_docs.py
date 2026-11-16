import time
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def main():
    import uuid
    uid = uuid.uuid4().hex[:6]
    username = f"eval_{uid}"
    email = f"eval_{uid}@acmecorp.com"
    
    print("Registering user...")
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "username": username,
        "email": email,
        "password": "password123",
        "role": "admin"
    })
    print(resp.status_code, resp.text)
    
    print("Logging in...")
    resp = requests.post(f"{BASE_URL}/auth/login", data={
        "username": username,
        "password": "password123"
    })
    print(resp.status_code, resp.text)
    resp.raise_for_status()
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    doc_ids = {}
    for filename in ["handbook.pdf", "security_policy.pdf"]:
        path = f"tests/e2e/data/{filename}"
        print(f"Uploading {filename}...")
        with open(path, "rb") as f:
            resp = requests.post(f"{BASE_URL}/docs/upload", files={"file": (filename, f, "application/pdf")}, headers=headers)
        
        resp.raise_for_status()
        doc_id = resp.json()["document_id"]
        doc_ids[filename] = doc_id
        print(f"Uploaded {filename}: {doc_id}")
    
    print("Waiting for ingestion to complete...")
    for filename, doc_id in doc_ids.items():
        while True:
            resp = requests.get(f"{BASE_URL}/docs/{doc_id}/status", headers=headers)
            status = resp.json()["status"]
            if status == "ready":
                print(f"{filename} is READY.")
                break
            elif status == "failed":
                print(f"{filename} FAILED: {resp.json().get('error_message')}")
                break
            time.sleep(1)

    print("--- DOCUMENT IDS ---")
    print(json.dumps(doc_ids, indent=2))
    
    with open("tests/e2e/doc_ids.json", "w") as f:
        json.dump(doc_ids, f)

if __name__ == "__main__":
    main()
