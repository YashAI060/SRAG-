import os

filepath = r"e:\SRAG\secure-rag-frontend\src\components\Sidebar.jsx"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("setDocs(data);", "setDocs(data.documents || []);")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Sidebar.jsx patched.")
