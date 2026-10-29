# ConcreteMix AI — IS 10262:2019 Concrete Mix Design Platform

**ConcreteMix AI** is a production-oriented, code-compliant civil engineering platform for concrete mix proportioning and code verification.

Tagline: *From design requirements to code-verified concrete mix proportions.*

---

## Features
- **Two-Tier Proportioning Architecture**:
  - **Tier 1 (IS 10262:2019 Engine)**: 100% deterministic mathematical proportioning procedure of **IS 10262:2019** and durability limits of **IS 456:2000 (Table 5)** for conventional OPC, PPC, and PSC with SCMs.
  - **Tier 2 (Literature-Anchored Reference Engine)**: Recognizes and proportions **12 Advanced Concrete Types** (301 published reference mixes) with nearest-neighbor literature retrieval, physical absolute volume closure, and statutory constraint auditing.
- **12 Special Concrete Types Supported**:
  1. Geopolymer (Alkali-activated fly ash / GGBS, 8–16M NaOH)
  2. Self-Healing Concrete (Bacterial spores, crystalline admixtures, microencapsulation)
  3. Self-Sensing Concrete (Piezoresistive CNT, carbon fibers, graphene nanoplatelets)
  4. Self-Compacting Concrete (SCC, EFNARC guidelines, powder content 450–650 kg/m³)
  5. 3D-Printed Concrete (3DCP, buildability, thixotropy, layer extrudability)
  6. Ultra-High Performance Concrete (UHPC, 150–200 MPa, w/b $\le$ 0.22, steel fibers)
  7. Engineered Cementitious Composites (ECC / Bendable Concrete, PVA fibers, 2–5% tensile ductility)
  8. Lightweight Concrete (LECA lightweight aggregate & cellular foam concrete)
  9. CO2-Mineralized / Injected Concrete (CarbonCure, Solidia accelerated carbonation)
  10. Sea-Sand & Seawater Concrete (SS-SWC with non-corrosive FRP reinforcement)
  11. Pervious Concrete (Hydraulic conductivity, 15–25% interconnected void ratio)
  12. Fiber-Reinforced Concrete (FRC / SFRC / Synthetic macro-fibers)
- **Natural Language Parsing & Keyword Detection**: Deterministic regex extraction and multi-word phrase matching across 1,200+ specialized keywords with word-boundary disambiguation.
- **401 Solved Problems Knowledge Base**:
  - 100 Conventional IS 10262 benchmark problems (Groups A–F)
  - 301 Literature-verified special concrete reference mixes
- **Hybrid Retrieval (RAG)**: BM25 keyword matching combined with offline TF-IDF cosine semantic search and structural metadata filtering (`concrete_type`, `grade`, `exposure`).
- **Strict Disclaimers & Statutory Badging**: Clear literature reference disclaimers and amber/green verification status badges on all special mix outputs. IS 10262 code is preserved untouched.

---

## Directory Structure
```
concretemix-ai/
├── app/
│   ├── config.py             # App settings (Pydantic)
│   ├── database.py           # SQLite + SQLAlchemy synchronous engine
│   ├── models.py             # ORM models (Example, Document, DocumentChunk, DesignSession)
│   ├── schemas.py            # Pydantic request/response schemas
│   ├── main.py               # FastAPI entrypoint, template routes & SEO
│   ├── engine/
│   │   ├── is10262.py        # Preserved deterministic IS 10262:2019 calculation engine
│   │   ├── parser.py         # Natural-language problem statement parser
│   │   └── validator.py      # Input validation & cross-field durability boundary checks
│   ├── rag/
│   │   ├── embeddings.py     # Offline TF-IDF vectorizer & cosine similarity indexer
│   │   ├── search.py         # Hybrid BM25 + TF-IDF searcher with metadata filtering
│   │   ├── examples.py       # 100 Solved benchmark examples manager & similarity ranker
│   │   └── ingestion.py      # Document chunking & PDF/DOCX text extraction pipeline
│   ├── api/
│   │   ├── design.py         # POST /api/design calculation endpoint
│   │   ├── examples.py       # GET /api/examples & /api/examples/{id}
│   │   ├── search.py         # GET /api/search hybrid query endpoint
│   │   ├── documents.py      # PDF upload & inspection endpoints
│   │   └── admin.py          # Admin re-indexing & database statistics
│   ├── templates/            # High-end Jinja2 templates (Inter + Tailwind CSS)
│   │   ├── base.html
│   │   ├── index.html        # Landing page
│   │   ├── design.html       # 7-Step Mix Design Workbench
│   │   ├── library.html      # 100 Solved Problems Knowledge Library
│   │   ├── example_detail.html # Deep-dive problem solution & audit
│   │   ├── methodology.html  # Technical calculation methodology
│   │   ├── docs.html         # Documentation & FAQ
│   │   ├── admin.html        # Protected ingestion management
│   │   └── seo/              # Educational SEO pages
│   └── static/
├── data/
│   ├── concretemix.db        # SQLite database (100 problems imported)
│   ├── tfidf_index/          # Persisted TF-IDF vocabulary, doc matrix & IDF weights
│   └── examples/             # Raw JSONL and summary CSV datasets
├── tests/
│   └── test_engine.py        # Pytest test suite
└── requirements.txt
```

---

## Quickstart

### 1. Requirements
- Python 3.10+ (tested on Python 3.13)

### 2. Run the Platform
Navigate to the project root and launch Uvicorn:
```bash
cd concretemix-ai
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser at:
- **Application Overview**: [http://localhost:8000](http://localhost:8000)
- **Mix Design Workbench**: [http://localhost:8000/design](http://localhost:8000/design)
- **100 Solved Problems Library**: [http://localhost:8000/library](http://localhost:8000/library)
- **Interactive OpenAPI Docs**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

### 3. Run the Automated Tests
```bash
python -m pytest tests -v
```
All 4 test suites will run and verify calculations, parsing, boundaries, and retrieval.
