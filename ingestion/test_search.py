
import os
from openai import OpenAI
from supabase import create_client

# Connect to OpenAI and Supabase
openai_client = OpenAI()

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SECRET_KEY"]
)

# Investor relations test question
question = "What is Ameresco's outlook for 2026?"

print("\nInvestor question:", question)
print("\nSearching Ameresco documents...\n")

# Convert the question into an embedding
response = openai_client.embeddings.create(
    model="text-embedding-3-small",
    input=question
)

query_embedding = response.data[0].embedding

# Search Supabase for the most relevant passages
results = supabase.rpc(
    "match_document_chunks",
    {
        "query_embedding": query_embedding,
        "match_count": 5
    }
).execute()

if not results.data:
    print("No matching documents found.")

else:
    for index, match in enumerate(results.data, start=1):

        print(f"\n--- RESULT {index} ---")

        print("Document ID:", match["document_id"])
        print("Similarity:", round(match["similarity"], 3))

        # Retrieve source document information
        document_response = (
            supabase.table("documents")
            .select("*")
            .eq("id", match["document_id"])
            .limit(1)
            .execute()
        )

        if document_response.data:
            document = document_response.data[0]

            print(
                "Source document:",
                document.get("filename", "Unknown")
            )

            print(
                "Document path:",
                document.get("relative_path", "Unknown")
            )

            print(
                "Document metadata:",
                document
            )

        else:
            print("Source document: Not found")

        # Display retrieved passage
        print("\nRelevant passage:")
        print(match["content"][:1000])

        print("-" * 60)

print("\nSearch complete.")
