from pathlib import Path
import json


INPUT_DIR = Path("ingestion_output")
REPORT_PATH = INPUT_DIR / "ingestion_report.json"
OUTPUT_PATH = INPUT_DIR / "chunk_index.json"

CHUNK_SIZE = 1800
CHUNK_OVERLAP = 250


def chunk_text(text: str, chunk_size: int, overlap: int):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def main():
    if not REPORT_PATH.exists():
        raise FileNotFoundError(
            f"Missing ingestion report: {REPORT_PATH}"
        )

    report = json.loads(
        REPORT_PATH.read_text(encoding="utf-8")
    )

    indexed_chunks = []

    successful_records = [
        record for record in report
        if record["status"] == "success"
    ]

    print(f"Documents ready for chunking: {len(successful_records)}")

    for doc_number, record in enumerate(successful_records, start=1):
        text_path = INPUT_DIR / f"{doc_number:03d}.txt"

        if not text_path.exists():
            print(f"Missing extracted text: {text_path}")
            continue

        text = text_path.read_text(encoding="utf-8")

        chunks = chunk_text(
            text,
            CHUNK_SIZE,
            CHUNK_OVERLAP,
        )

        print(
            f"[{doc_number}/{len(successful_records)}] "
            f"{record['filename']} -> {len(chunks)} chunks"
        )

        for chunk_number, chunk in enumerate(chunks, start=1):
            indexed_chunks.append(
                {
                    "filename": record["filename"],
                    "relative_path": record["relative_path"],
                    "extension": record["extension"],
                    "document_number": doc_number,
                    "chunk_number": chunk_number,
                    "text": chunk,
                }
            )

    OUTPUT_PATH.write_text(
        json.dumps(indexed_chunks, indent=2),
        encoding="utf-8",
    )

    print("\n--- CHUNKING SUMMARY ---")
    print(f"Documents processed: {len(successful_records)}")
    print(f"Chunks created:      {len(indexed_chunks)}")
    print(f"Saved to:            {OUTPUT_PATH}")


if __name__ == "__main__":
    main()