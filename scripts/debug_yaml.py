import yaml
from pathlib import Path

yaml_path = Path("data/sources/master_library.yaml")

with open(yaml_path, 'r', encoding='utf-8') as f:
    docs = list(yaml.safe_load_all(f))

print(f"Total documents: {len(docs)}\n")

for i, doc in enumerate(docs):
    print(f"--- DOCUMENT {i} ---")
    if isinstance(doc, dict):
        print(f"Keys: {list(doc.keys())[:5]}")  # First 5 keys
        print(f"Type: {type(doc)}")
    else:
        print(f"Type: {type(doc)}")
        print(f"Content preview: {str(doc)[:100]}")
    print()