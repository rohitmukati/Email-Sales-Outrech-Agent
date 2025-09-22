import os
from datetime import datetime
from dotenv import load_dotenv

import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec

# ---------------- Load environment variables ----------------
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("Please set GOOGLE_API_KEY in your environment")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
if not PINECONE_API_KEY:
    raise ValueError("Please set PINECONE_API_KEY in your environment")

# ---------------- Initialize clients ----------------
genai.configure(api_key=GOOGLE_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)

# ---------------- Create / connect to Pinecone index ----------------
index_name = "audio-transcripts-10000"
if index_name not in [idx["name"] for idx in pc.list_indexes()]:
    pc.create_index(
        name=index_name,
        dimension=768,  # embedding size
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

index = pc.Index(index_name)

# ---------------- Embedding function ----------------
def embed_text(text: str):
    """Generate embedding for given text using Gemini"""
    response = genai.embed_content(
        model="models/embedding-001",   # latest embedding model
        content=text,
        task_type="retrieval_query",    # 👈 query type for search
        output_dimensionality=768
    )
    return response["embedding"]

# ---------------- Store + Retrieve Example ----------------
if __name__ == "__main__":
    # 1️⃣ Upload Example
    text = "my name is rohit mukati."
    file_id = "sample_002"
    file_type = "txt"
    upload_time = datetime.utcnow().isoformat()

    embedding = embed_text(text)

    index.upsert(vectors=[{
        "id": file_id,
        "values": embedding,
        "metadata": {
            "text": text,
            "file_name": file_id,
            "file_type": file_type,
            "upload_time": upload_time
        }
    }])

    print(f"✅ Uploaded: {file_id}")

    # 2️⃣ Retrieval Example
    query_text = "what is my name "
    query_embedding = embed_text(query_text)

    results = index.query(
        vector=query_embedding,
        top_k=1,              # Top 3 results
        include_metadata=True # Original text bhi milega
    )

    print("\n🔎 Retrieval Results:")
    for match in results["matches"]:
        print(f"- ID: {match['id']} | Score: {match['score']:.4f}")
        print(f"  Text: {match['metadata']['text']}")
