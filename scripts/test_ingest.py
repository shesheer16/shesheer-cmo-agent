import yaml
import json
from pathlib import Path

yaml_path = Path("data/sources/master_library.yaml")

print("📂 Loading YAML...")
with open(yaml_path, 'r', encoding='utf-8') as f:
    docs = list(yaml.safe_load_all(f))

print(f"✅ Loaded {len(docs)} documents\n")

# Test: Check document 1 (frameworks)
doc1 = docs[1]
print(f"Document 1 keys: {list(doc1.keys())}")
print(f"Frameworks count: {len(doc1.get('frameworks', {}))}")

# Test: Check document 2 (books)
doc2 = docs[2]
print(f"Document 2 keys: {list(doc2.keys())}")
print(f"Books count: {len(doc2.get('books', {}))}")

# Test: Check document 9 (campaigns)
doc9 = docs[9]
print(f"Document 9 keys: {list(doc9.keys())}")
print(f"Campaigns count: {len(doc9.get('campaigns', []))}")

print("\n✅ YAML structure verified!")