import os

# 1. Update Backend Schema
schema_path = r"e:\SRAG\secure-rag-backend\app\models\schemas.py"
with open(schema_path, "r", encoding="utf-8") as f:
    s_content = f.read()

if "decompose: bool = True" not in s_content:
    s_content = s_content.replace(
        'top_k: Optional[int] = None                      # override RETRIEVAL_TOP_K',
        'top_k: Optional[int] = None\n    decompose: bool = True'
    )
    with open(schema_path, "w", encoding="utf-8") as f:
        f.write(s_content)


# 2. Update Backend Route
route_path = r"e:\SRAG\secure-rag-backend\app\api\routes_chat.py"
with open(route_path, "r", encoding="utf-8") as f:
    r_content = f.read()

r_content = r_content.replace('decompose=True,', 'decompose=request.decompose,')
with open(route_path, "w", encoding="utf-8") as f:
    f.write(r_content)


# 3. Update Frontend Client
client_path = r"e:\SRAG\secure-rag-frontend\src\api\client.js"
with open(client_path, "r", encoding="utf-8") as f:
    c_content = f.read()

c_content = c_content.replace(
    'body: JSON.stringify({ query, mode, decompose })',
    'body: JSON.stringify({ query: query, retrieval_mode: mode, decompose: decompose })'
)
with open(client_path, "w", encoding="utf-8") as f:
    f.write(c_content)

print("Patched all files successfully.")
