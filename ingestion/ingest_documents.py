from pathlib import Path
import json
import sys

from pypdf import PdfReader
from docx import Document


SUPPORTED_EXTENSIONS = {".pdf", ".docx"}


def extract_pdf(path: Path) -> str:
    reader = PdfReader(path)
    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)

    return "\n".join(pages).strip()


def extract_docx(path: Path) -> str:
    doc = Document(path)
    return "\n".join(
        paragraph.text for paragraph in doc.paragraphs
    ).strip()


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return extract_pdf(path)

    if suffix == ".docx":
        return extract_docx(path)

    raise ValueError(f"Unsupported file type: {suffix}")


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print('python ingestion/ingest_documents.py "/path/to/Ameresco"')
        sys.exit(1)

    corpus_dir = Path(sys.argv[1]).expanduser().resolve()

    if not corpus_dir.exists():
        print(f"Folder not found: {corpus_dir}")
        sys.exit(1)

    output_dir = Path("ingestion_output")
    output_dir.mkdir(exist_ok=True)

    results = []

    files = sorted(
        p
        for p in corpus_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    print(f"\nFound {len(files)} supported files.\n")

    for index, path in enumerate(files, start=1):
        relative_path = path.relative_to(corpus_dir)

        record = {
            "filename": path.name,
            "relative_path": str(relative_path),
            "extension": path.suffix.lower(),
            "status": "pending",
            "characters": 0,
            "error": None,
        }

        try:
            text = extract_text(path)

            if not text.strip():
                record["status"] = "empty_text"
            else:
                record["status"] = "success"
                record["characters"] = len(text)

                text_file = output_dir / f"{index:03d}.txt"
                text_file.write_text(text, encoding="utf-8")

            print(
                f"[{index}/{len(files)}] "
                f"{record['status']}: {relative_path}"
            )

        except Exception as exc:
            record["status"] = "failed"
            record["error"] = str(exc)

            print(
                f"[{index}/{len(files)}] "
                f"FAILED: {relative_path} -> {exc}"
            )

        results.append(record)

    report_path = output_dir / "ingestion_report.json"
    report_path.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    successes = sum(r["status"] == "success" for r in results)
    empty = sum(r["status"] == "empty_text" for r in results)
    failed = sum(r["status"] == "failed" for r in results)

    print("\n--- INGESTION SUMMARY ---")
    print(f"Detected:       {len(results)}")
    print(f"Extracted:      {successes}")
    print(f"Empty text:     {empty}")
    print(f"Failed:         {failed}")
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()