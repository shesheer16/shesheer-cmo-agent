import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
import json
import chromadb
from sentence_transformers import SentenceTransformer

yaml_path = Path("data/sources/master_library.yaml")

print("📂 Loading YAML...")
with open(yaml_path, 'r', encoding='utf-8') as f:
    docs = list(yaml.safe_load_all(f))

print(f"✅ Loaded {len(docs)} documents\n")

# Initialize ChromaDB
print("🔧 Initializing ChromaDB...")
client = chromadb.PersistentClient(path="./data/chromadb")
collection = client.get_or_create_collection(
    name="shesheer_master_library",
    metadata={"hnsw:space": "cosine"}
)

# Initialize embedder
print("🤖 Loading embedder...\n")
embedder = SentenceTransformer('all-MiniLM-L6-v2')

chunk_count = 0

# Process each document
for doc_idx in range(1, 12):  # Documents 1-11
    doc = docs[doc_idx]
    
    # FRAMEWORKS
    if 'frameworks' in doc:
        print(f"📌 Processing frameworks...")
        for fw_id, fw_data in doc['frameworks'].items():
            text = f"Framework: {fw_data.get('title')}\n{json.dumps(fw_data, indent=2)}"
            embedding = embedder.encode(text).tolist()
            collection.add(
                ids=[f"fw_{fw_id}"],
                embeddings=[embedding],
                metadatas={"type": "framework", "title": fw_data.get('title')},
                documents=[text]
            )
            chunk_count += 1
        print(f"   ✅ Added {len(doc['frameworks'])} frameworks\n")
    
    # BOOKS
    if 'books' in doc:
        print(f"📚 Processing books...")
        total_books = 0
        for category, books_list in doc['books'].items():
            if isinstance(books_list, list):
                for book in books_list:
                    text = f"Book: {book.get('title')} by {book.get('author')}\n{json.dumps(book, indent=2)}"
                    embedding = embedder.encode(text).tolist()
                    collection.add(
                        ids=[book.get('id')],
                        embeddings=[embedding],
                        metadatas={"type": "book", "title": book.get('title'), "author": book.get('author')},
                        documents=[text]
                    )
                    chunk_count += 1
                    total_books += 1
        print(f"   ✅ Added {total_books} books\n")
    
    # PODCASTS
    if 'podcasts_youtube' in doc:
        print(f"🎙️ Processing podcasts...")
        total_pods = 0
        for category, pods_list in doc['podcasts_youtube'].items():
            if isinstance(pods_list, list):
                for pod in pods_list:
                    text = f"Podcast: {pod.get('name')} by {pod.get('host')}\n{json.dumps(pod, indent=2)}"
                    embedding = embedder.encode(text).tolist()
                    collection.add(
                        ids=[pod.get('id')],
                        embeddings=[embedding],
                        metadatas={"type": "podcast", "name": pod.get('name'), "host": pod.get('host')},
                        documents=[text]
                    )
                    chunk_count += 1
                    total_pods += 1
        print(f"   ✅ Added {total_pods} podcasts\n")
    
    # FOUNDERS
    if 'people_founders' in doc:
        print(f"👤 Processing founders...")
        for founder in doc['people_founders']:
            text = f"Founder: {founder.get('name')} ({founder.get('company_primary')})\n{json.dumps(founder, indent=2)}"
            embedding = embedder.encode(text).tolist()
            collection.add(
                ids=[founder.get('id')],
                embeddings=[embedding],
                metadatas={"type": "founder", "name": founder.get('name'), "company": founder.get('company_primary')},
                documents=[text]
            )
            chunk_count += 1
        print(f"   ✅ Added {len(doc['people_founders'])} founders\n")
    
    # VCs
    if 'venture_capitalists' in doc:
        print(f"💰 Processing VCs...")
        for vc in doc['venture_capitalists']:
            text = f"VC: {vc.get('name')} ({vc.get('firm')})\n{json.dumps(vc, indent=2)}"
            embedding = embedder.encode(text).tolist()
            collection.add(
                ids=[vc.get('id')],
                embeddings=[embedding],
                metadatas={"type": "vc", "name": vc.get('name'), "firm": vc.get('firm')},
                documents=[text]
            )
            chunk_count += 1
        print(f"   ✅ Added {len(doc['venture_capitalists'])} VCs\n")
    
    # ADVERTISING STRATEGISTS
    if 'advertising_strategists' in doc:
        print(f"🎨 Processing advertisers...")
        for strategist in doc['advertising_strategists']:
            text = f"Strategist: {strategist.get('name')}\n{json.dumps(strategist, indent=2)}"
            embedding = embedder.encode(text).tolist()
            collection.add(
                ids=[strategist.get('id')],
                embeddings=[embedding],
                metadatas={"type": "strategist", "name": strategist.get('name')},
                documents=[text]
            )
            chunk_count += 1
        print(f"   ✅ Added {len(doc['advertising_strategists'])} strategists\n")
    
    # DIGITAL LEADERS
    if 'digital_leaders' in doc:
        print(f"🚀 Processing digital leaders...")
        for leader in doc['digital_leaders']:
            text = f"Digital Leader: {leader.get('name')}\n{json.dumps(leader, indent=2)}"
            embedding = embedder.encode(text).tolist()
            collection.add(
                ids=[leader.get('id')],
                embeddings=[embedding],
                metadatas={"type": "leader", "name": leader.get('name')},
                documents=[text]
            )
            chunk_count += 1
        print(f"   ✅ Added {len(doc['digital_leaders'])} leaders\n")
    
    # DATA SOURCES
    if 'data_sources' in doc:
        print(f"📊 Processing data sources...")
        for source in doc['data_sources']:
            text = f"Data Source: {source.get('name')}\n{json.dumps(source, indent=2)}"
            embedding = embedder.encode(text).tolist()
            collection.add(
                ids=[source.get('id')],
                embeddings=[embedding],
                metadatas={"type": "data_source", "name": source.get('name'), "url": source.get('url')},
                documents=[text]
            )
            chunk_count += 1
        print(f"   ✅ Added {len(doc['data_sources'])} sources\n")
    
    # CAMPAIGNS
    if 'campaigns' in doc:
        print(f"📺 Processing campaigns...")
        for campaign in doc['campaigns']:
            text = f"Campaign: {campaign.get('brand')} - {campaign.get('campaign')}\n{json.dumps(campaign, indent=2)}"
            embedding = embedder.encode(text).tolist()
            collection.add(
                ids=[campaign.get('id')],
                embeddings=[embedding],
                metadatas={"type": "campaign", "brand": campaign.get('brand'), "name": campaign.get('campaign')},
                documents=[text]
            )
            chunk_count += 1
        print(f"   ✅ Added {len(doc['campaigns'])} campaigns\n")

print("=" * 60)
print(f"🎉 INGESTION COMPLETE!")
print(f"✅ Total chunks ingested: {chunk_count}")
print(f"✅ Collection: shesheer_master_library")
print(f"✅ Location: ./data/chromadb")
print("=" * 60)
