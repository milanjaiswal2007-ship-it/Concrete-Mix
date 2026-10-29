"""
Batch ingest all PDF papers from 'paper 1 references' and 'paper 2 references'
into the database (Document and DocumentChunk models) with full Geopolymer tagging.
"""
import os
import re
import sys
import hashlib
import warnings
from pathlib import Path

# Suppress fonttools warning noise
warnings.filterwarnings("ignore")

from app.database import SessionLocal, init_db
from app.models import Document, DocumentChunk
from app.rag.ingestion import DocumentIngester

def clean_title(first_page_text, fallback):
    lines = [l.strip() for l in first_page_text.split('\n') if len(l.strip()) > 8]
    # Filter out common headers/metadata lines
    bad_prefixes = ("http", "doi", "issn", "volume", "journal", "available online", "elsevier", "springer", "wiley", "applied sciences", "materials", "construction and building")
    candidate_lines = []
    for l in lines[:10]:
        l_lower = l.lower()
        if not any(l_lower.startswith(p) for p in bad_prefixes) and len(l) > 12:
            candidate_lines.append(l)
    if candidate_lines:
        return candidate_lines[0][:200]
    return fallback

def run():
    init_db()
    db = SessionLocal()
    ingester = DocumentIngester(SessionLocal, upload_dir="data/documents")

    folders = [
        r"c:\Users\Prakash\OneDrive\Desktop\paper 1 references",
        r"c:\Users\Prakash\OneDrive\Desktop\paper 2 references"
    ]

    all_files = []
    for folder in folders:
        folder_path = Path(folder)
        if folder_path.exists():
            for f in folder_path.glob("*.pdf"):
                all_files.append((f.name, str(f)))

    # Deduplicate by filename
    unique_files = {}
    for name, fpath in all_files:
        if name not in unique_files:
            unique_files[name] = fpath

    print(f"Total unique PDF research papers found: {len(unique_files)}")

    ingested_count = 0
    duplicate_count = 0
    error_count = 0

    for idx, (filename, fpath) in enumerate(unique_files.items(), 1):
        try:
            with open(fpath, "rb") as fh:
                content_hash = hashlib.sha256(fh.read()).hexdigest()[:16]
            stored_name = f"{content_hash}_{filename}"

            existing = db.query(Document).filter(Document.filename == stored_name).first()
            if existing:
                duplicate_count += 1
                if idx % 20 == 0 or idx == len(unique_files):
                    print(f"[{idx}/{len(unique_files)}] Processed (already existing: {duplicate_count})")
                continue

            # Extract text to get clean title guess
            pages = ingester.extract_text_pdf(fpath)
            first_text = pages[0]["text"] if pages else ""
            paper_title = clean_title(first_text, filename)

            # Ingest using ingester
            res = ingester.ingest_file(
                filepath=fpath,
                original_name=filename,
                standard_name="Geopolymer Research Literature",
                edition=f"Paper: {paper_title[:100]}"
            )

            if res["status"] in ("processed", "duplicate"):
                ingested_count += 1
            else:
                error_count += 1
                print(f"Failed {filename}: {res.get('errors')}")

        except Exception as e:
            error_count += 1
            print(f"Error processing {filename}: {e}")

        if idx % 10 == 0 or idx == len(unique_files):
            print(f"[{idx}/{len(unique_files)}] Ingested: {ingested_count}, Existing: {duplicate_count}, Errors: {error_count}")

    total_docs = db.query(Document).count()
    total_chunks = db.query(DocumentChunk).count()
    print(f"\nIngestion Complete!")
    print(f"Total Documents in Database: {total_docs}")
    print(f"Total Searchable Chunks in Database: {total_chunks}")
    db.close()

if __name__ == "__main__":
    run()
