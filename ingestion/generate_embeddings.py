
import os
import time

from openai import OpenAI
from supabase import create_client

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 25
PAGE_SIZE = 500


def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is missing.")

    if not os.getenv("SUPABASE_URL"):
        raise RuntimeError("SUPABASE_URL is missing.")

    if not os.getenv("SUPABASE_SECRET_KEY"):
        raise RuntimeError("SUPABASE_SECRET_KEY is missing.")

    openai_client = OpenAI()
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SECRET_KEY"),
    )

    print("Connecting to Supabase...")

    # Retrieve all chunks without loading existing embeddings.
    chunks = []
    start = 0

    while True:
        response = (
            supabase.table("document_chunks")
            .select("id,text")
            .is_("embedding", "null")
            .order("id")
            .range(start, start + PAGE_SIZE - 1)
            .execute()
        )

        page = response.data or []
        chunks.extend(page)

        if len(page) < PAGE_SIZE:
            break

        start += PAGE_SIZE

    # Ignore empty text records.
    chunks = [
        chunk for chunk in chunks
        if chunk.get("text") and chunk["text"].strip()
    ]

    print(f"Chunks needing embeddings: {len(chunks)}")

    if not chunks:
        print("All chunks already have embeddings!")
        return

    completed = 0

    for offset in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[offset:offset + BATCH_SIZE]

        texts = [
            chunk["text"].replace("\x00", "").strip()
            for chunk in batch
        ]

        # Generate embeddings in one OpenAI API request.
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
        )

        # Save each embedding immediately.
        for chunk, item in zip(batch, response.data):
            embedding = item.embedding

            (
                supabase.table("document_chunks")
                .update({"embedding": embedding})
                .eq("id", chunk["id"])
                .execute()
            )

            completed += 1

        print(
            f"Embedded and saved: {completed}/{len(chunks)}"
        )

        time.sleep(0.2)

    print("\n--- EMBEDDING SUMMARY ---")
    print(f"New embeddings saved: {completed}")
    print("Model:", EMBEDDING_MODEL)
    print("Status: Complete")


if __name__ == "__main__":
    main()
