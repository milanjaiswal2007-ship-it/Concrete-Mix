"""Examples API — CRUD and search for solved mix design examples."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models import Example
from app.rag.examples import ExampleManager

router = APIRouter(prefix="/api/examples", tags=["examples"])


def _mgr() -> ExampleManager:
    return ExampleManager(SessionLocal)


@router.get("")
def list_examples(
    grade: Optional[str] = Query(None),
    exposure: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    group: Optional[str] = Query(None),
    concrete_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List examples with optional filters."""
    examples, total = _mgr().list_examples(grade, exposure, zone, group, concrete_type, limit, offset)
    return {"total": total, "limit": limit, "offset": offset, "results": examples}


@router.get("/stats")
def example_statistics():
    """Get statistics about the example collection."""
    return _mgr().get_statistics()


@router.get("/concrete-types")
def get_concrete_types():
    """Get list of 12 special concrete types + conventional with metadata, counts, and descriptions."""
    stats = _mgr().get_statistics()
    counts = stats.get("by_concrete_type", {})

    types_metadata = [
        {
            "slug": "conventional",
            "name": "Conventional Concrete (IS 10262)",
            "standard": "IS 10262:2019 / IS 456:2000",
            "count": counts.get("conventional", 100),
            "keyword_count": 50,
            "description": "Standard deterministic mix design using OPC 33/43/53, PPC, PSC, and mineral admixtures (fly ash, GGBS, silica fume).",
            "is_special": False,
        },
        {
            "slug": "geopolymer",
            "name": "Geopolymer Concrete",
            "standard": "RILEM TC 224-AAM / Curtin GC1",
            "count": counts.get("geopolymer", 26),
            "keyword_count": 100,
            "description": "Zero-cement alkali-activated binders synthesized from fly ash, slag, sodium hydroxide, and sodium silicate.",
            "is_special": True,
        },
        {
            "slug": "self-healing",
            "name": "Self-Healing Concrete",
            "standard": "RILEM TC 221-SHC",
            "count": counts.get("self-healing", 25),
            "keyword_count": 100,
            "description": "Autonomous bio-mineralization or chemical microencapsulation to seal microcracks automatically on moisture ingress.",
            "is_special": True,
        },
        {
            "slug": "self-sensing",
            "name": "Self-Sensing / Smart Concrete",
            "standard": "Ou & Han (2009)",
            "count": counts.get("self-sensing", 28),
            "keyword_count": 100,
            "description": "Piezoresistive structural health monitoring concrete loaded with carbon nanotubes, graphene, or conductive fibres.",
            "is_special": True,
        },
        {
            "slug": "self-compacting",
            "name": "Self-Compacting Concrete (SCC)",
            "standard": "EFNARC (2005) / ACI 237R",
            "count": counts.get("self-compacting", 26),
            "keyword_count": 100,
            "description": "Highly flowable, non-segregating mix filling complex formwork and congested rebar under its own self-weight.",
            "is_special": True,
        },
        {
            "slug": "3d-printing",
            "name": "3D Printable Concrete (3DCP)",
            "standard": "Buswell et al. (2018)",
            "count": counts.get("3d-printing", 25),
            "keyword_count": 100,
            "description": "Extrusion-based mortar/concrete with high early buildability, thixotropic open time, and shape retention.",
            "is_special": True,
        },
        {
            "slug": "uhpc",
            "name": "Ultra-High Performance Concrete (UHPC)",
            "standard": "AFGC/SETRA (2013) / FHWA",
            "count": counts.get("uhpc", 26),
            "keyword_count": 100,
            "description": "Dense particle packing with micro silica, low w/b (<0.22), steel microfibres, and compressive strength exceeding 120–180 MPa.",
            "is_special": True,
        },
        {
            "slug": "ecc",
            "name": "Engineered Cementitious Composites (ECC)",
            "standard": "Li (2003)",
            "count": counts.get("ecc", 25),
            "keyword_count": 100,
            "description": "High-ductility bendable concrete with >3% tensile strain capacity via PVA microfibres and steady-state microcracking.",
            "is_special": True,
        },
        {
            "slug": "lightweight",
            "name": "Lightweight / Cellular Concrete",
            "standard": "ACI 213R / ACI 523R",
            "count": counts.get("lightweight", 27),
            "keyword_count": 100,
            "description": "Low-density structural and thermal insulation concrete incorporating expanded clay (LECA), pumice, or pre-formed foam.",
            "is_special": True,
        },
        {
            "slug": "co2-injected",
            "name": "CO₂-Injected / Mineralised Concrete",
            "standard": "Monkman et al. (2016)",
            "count": counts.get("co2-injected", 23),
            "keyword_count": 100,
            "description": "Permanent sequestration of liquid carbon dioxide during batching to precipitate nano-CaCO₃ and accelerate early strength.",
            "is_special": True,
        },
        {
            "slug": "sea-sand",
            "name": "Sea-Sand / Seawater Concrete",
            "standard": "Xiao et al. (2017) / IS 456 Table 7",
            "count": counts.get("sea-sand", 26),
            "keyword_count": 100,
            "description": "Marine-resource concrete using unwashed/desalinated sea sand and seawater, paired with corrosion-resistant FRP or stainless rebar.",
            "is_special": True,
        },
        {
            "slug": "pervious",
            "name": "Pervious / Porous Concrete",
            "standard": "ACI 522R / NRMCA",
            "count": counts.get("pervious", 23),
            "keyword_count": 100,
            "description": "No-fines concrete with 15–30% interconnected voids for stormwater drainage, groundwater recharge, and permeable pavements.",
            "is_special": True,
        },
        {
            "slug": "fiber-reinforced",
            "name": "Fibre-Reinforced Concrete (FRC)",
            "standard": "ACI 544.1R / RILEM TC 162",
            "count": counts.get("fiber-reinforced", 30),
            "keyword_count": 100,
            "description": "Dispersed macro and micro fibres (steel, synthetic, basalt, glass) enhancing toughness, post-crack ductility, and impact resistance.",
            "is_special": True,
        },
    ]
    return types_metadata


@router.get("/keywords/{concrete_type}")
def get_keywords_for_type(concrete_type: str):
    """Get the 100 reference keywords for a specific concrete type."""
    import os
    from app.config import settings
    path = os.path.join(settings.DATA_DIR, "examples", "special", "keyword_banks.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Keyword banks not found")

    try:
        with open(path, "r", encoding="utf-8") as f:
            banks = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if concrete_type not in banks:
        raise HTTPException(status_code=404, detail=f"Concrete type '{concrete_type}' not found in keyword banks")

    return {
        "concrete_type": concrete_type,
        "count": len(banks[concrete_type]),
        "keywords": banks[concrete_type],
    }


@router.get("/search")
def search_examples(
    q: str = Query(..., min_length=2),
    top_k: int = Query(10, ge=1, le=50),
    concrete_type: Optional[str] = Query(None),
):
    """Search examples by query text with optional concrete_type filtering."""
    from app.rag.search import HybridSearcher
    from app.rag.embeddings import TFIDFEmbedder

    embedder = TFIDFEmbedder()
    if not embedder.load_index():
        # Build index on the fly
        docs = _mgr().get_for_search_index()
        if not docs:
            return {"query": q, "total": 0, "results": []}
        searcher = HybridSearcher(embedder)
        searcher.index_documents(docs)
    else:
        searcher = HybridSearcher(embedder)
        searcher.documents = [
            {"id": eid, "text": txt, "metadata": meta}
            for eid, txt, meta in zip(embedder.doc_ids, embedder.doc_texts, embedder.doc_metadata)
        ]
        from rank_bm25 import BM25Okapi
        import re
        tokenized = [re.findall(r"[a-z0-9]+", t.lower()) for t in embedder.doc_texts]
        if tokenized:
            searcher.bm25 = BM25Okapi(tokenized)
        searcher.tokenized_corpus = tokenized

    meta_filter = {"concrete_type": concrete_type} if concrete_type else None
    results = searcher.search(q, top_k=top_k, metadata_filter=meta_filter)
    return {"query": q, "total": len(results), "results": results}


@router.get("/{example_id}")
def get_example(example_id: str):
    """Get a single example by external ID (e.g. P001)."""
    ex = _mgr().get_example(example_id)
    if not ex:
        raise HTTPException(status_code=404, detail=f"Example '{example_id}' not found")
    return ex
