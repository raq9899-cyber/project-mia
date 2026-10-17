from pathlib import Path
import json
import os

from supabase import create_client


INPUT_DIR = Path("ingestion_output")
REPORT_PATH = INPUT_DIR / "ingestion_report.json"
CHUNKS_PATH = INPUT_DIR / "chunk_index.json"

COMPANY = "Ameresco"


def document_type_from_path(relative_path: str) -> str:
    parts = Path(relative_path).parts

    if not parts:
        return "Unknown"

    return parts[0]


def main():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SECRET_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SECRET_KEY must be set."
        )

    if not REPORT_PATH.exists():
        raise FileNotFoundError(REPORT_PATH)

    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(CHUNKS_PATH)

    supabase = create_client(
        supabase_url,
        supabase_key,
    )

    report = json.loads(
        REPORT_PATH.read_text(encoding="utf-8")
    )

    chunks = json.loads(
        CHUNKS_PATH.read_text(encoding="utf-8")
    )

    successful_documents = [
        item
        for item in report
        if item["status"] == "success"
    ]

    document_ids = {}

    print(
        f"Uploading {len(successful_documents)} documents..."
    )

    for record in successful_documents:
        existing = (
            supabase
            .table("documents")
            .select("id")
            .eq("relative_path", record["relative_path"])
            .execute()
        )

        if existing.data:
            document_id = existing.data[0]["id"]

        else:
            inserted = (
                supabase
                .table("documents")
                .insert(
                    {
                        "filename": record["filename"],
                        "relative_path": record["relative_path"],
                        "extension": record["extension"],
                        "company": COMPANY,
                        "document_type": document_type_from_path(
                            record["relative_path"]
                        ),
                    }
                )
                .execute()
            )

            document_id = inserted.data[0]["id"]

        document_ids[
            record["relative_path"]
        ] = document_id

    print(
        f"Documents ready: {len(document_ids)}"
    )

    print(
        f"Uploading {len(chunks)} chunks..."
    )

    uploaded = 0
    skipped = 0

    for index, chunk in enumerate(chunks, start=1):
        document_id = document_ids[
            chunk["relative_path"]
        ]

        existing = (
            supabase
            .table("document_chunks")
            .select("id")
            .eq("document_id", document_id)
            .eq("chunk_number", chunk["chunk_number"])
            .execute()
        )

        if existing.data:
            skipped += 1

        else:
            clean_text = (
                chunk["text"]
                .replace("\x00", "")
            )

            (
                supabase
                .table("document_chunks")
                .insert(
                    {
                        "document_id": document_id,
                        "chunk_number": chunk["chunk_number"],
                        "text": clean_text,
                    }
                )
                .execute()
            )

            uploaded += 1

        if index % 100 == 0:
            print(
                f"Processed {index}/{len(chunks)} chunks"
            )

    print("\n--- SUPABASE UPLOAD SUMMARY ---")
    print(
        f"Documents available: {len(document_ids)}"
    )
    print(
        f"New chunks uploaded: {uploaded}"
    )
    print(
        f"Existing chunks skipped: {skipped}"
    )
    print(
        f"Total chunks processed: {len(chunks)}"
    )


if __name__ == "__main__":
    main()