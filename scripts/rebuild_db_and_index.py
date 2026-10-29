"""
Re-import special concrete examples (including expanded geopolymer PnC dataset)
into the database and rebuild the TF-IDF search index.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, init_db
from app.models import Example
from app.rag.examples import ExampleManager

def run():
    init_db()
    db = SessionLocal()
    mgr = ExampleManager(SessionLocal)

    # Clear existing special concrete examples
    deleted = db.query(Example).filter(Example.concrete_type != "conventional").delete()
    db.commit()
    print(f"Cleared {deleted} old special concrete records from DB.")

    # Re-import ALL special records (470 total: 195 geopolymer + 275 others)
    special_jsonl = "data/examples/special/special_concrete_mixes.jsonl"
    res = mgr.import_special_from_jsonl(special_jsonl)
    print(f"Imported special records: {res}")

    total_examples = db.query(Example).count()
    from sqlalchemy import func
    type_counts = db.query(Example.concrete_type, func.count(Example.id)).group_by(Example.concrete_type).all()
    print(f"\nTotal examples in DB: {total_examples}")
    print("Breakdown by type:")
    for t, c in sorted(type_counts, key=lambda x: -x[1]):
        print(f"  {t}: {c}")

    # Rebuild TF-IDF search index
    print("\nRebuilding TF-IDF search index...")
    docs = mgr.get_for_search_index()
    if docs:
        from app.rag.embeddings import TFIDFEmbedder
        from app.rag.search import HybridSearcher
        embedder = TFIDFEmbedder()
        searcher = HybridSearcher(embedder)
        searcher.index_documents(docs)
        print(f"TF-IDF index rebuilt with {len(docs)} documents.")
    else:
        print("No documents to index!")

    db.close()
    print("\nDone! Database and search index are fully updated.")

if __name__ == "__main__":
    run()
