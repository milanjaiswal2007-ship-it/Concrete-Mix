"""ConcreteMix AI — FastAPI application entry point.

Server-rendered pages via Jinja2 + REST API for the calculation engine,
RAG retrieval, and example management.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from app.config import settings
from app.database import init_db, SessionLocal
from app.engine.type_schemas import TYPE_SCHEMAS
from app.rag.examples import ExampleManager
from app.models import Example

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="IS 10262:2019 concrete mix design platform with RAG retrieval",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── Static files & templates ─────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ── Custom Jinja2 filters ────────────────────────────────────────────────────
def json_filter(value):
    """Serialize value to JSON and mark as safe so Jinja2 won't HTML-escape it."""
    return Markup(json.dumps(value, ensure_ascii=False, default=str))

templates.env.filters["tojson"] = json_filter


# ── API routers ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "app": "ConcreteMix AI", "version": settings.APP_VERSION}

from app.api.design import router as design_router
from app.api.examples import router as examples_router
from app.api.search import router as search_router
from app.api.documents import router as documents_router
from app.api.admin import router as admin_router
from app.api.concrete_types import router as concrete_types_router

app.include_router(design_router)
app.include_router(examples_router)
app.include_router(search_router)
app.include_router(documents_router)
app.include_router(admin_router)
app.include_router(concrete_types_router)


# ── Startup ──────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    """Initialise database and build search index on first run."""
    init_db()
    logger.info("Database initialised")

    # Auto-import bundled examples if DB is empty
    db = SessionLocal()
    try:
        count = db.query(Example).count()
        mgr = ExampleManager(SessionLocal)
        rebuild_needed = False

        if count == 0:
            jsonl = os.path.join(settings.DATA_DIR, "examples", "mix_problems.jsonl")
            if os.path.exists(jsonl):
                result = mgr.import_from_jsonl(jsonl)
                logger.info("Auto-imported bundled conventional examples: %s", result)
                rebuild_needed = True

        # Auto-import special concrete records if none exist
        special_count = db.query(Example).filter(Example.concrete_type != "conventional").count()
        if special_count == 0:
            special_jsonl = os.path.join(settings.DATA_DIR, "examples", "special", "special_concrete_mixes.jsonl")
            if os.path.exists(special_jsonl):
                res_special = mgr.import_special_from_jsonl(special_jsonl)
                logger.info("Auto-imported special concrete examples: %s", res_special)
                rebuild_needed = True

        if rebuild_needed:
            # Build search index across all conventional & special records
            docs = mgr.get_for_search_index()
            if docs:
                from app.rag.embeddings import TFIDFEmbedder
                from app.rag.search import HybridSearcher
                embedder = TFIDFEmbedder()
                searcher = HybridSearcher(embedder)
                searcher.index_documents(docs)
                embedder.save_index()
                logger.info("Search index built with %d documents", len(docs))
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════
# HTML PAGE ROUTES (server-rendered)
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
def landing_page(request: Request):
    """Landing page — hero, features, workflow preview, FAQ."""
    # Get example stats for the page
    db = SessionLocal()
    try:
        example_count = db.query(Example).count()
    finally:
        db.close()
    return templates.TemplateResponse(request=request, name="index.html", context={
        "title": f"{settings.APP_NAME} — IS 10262 Concrete Mix Design",
        "description": "Design concrete mixes per IS 10262:2019 with deterministic calculations, RAG retrieval, and 100+ solved examples.",
        "example_count": example_count,
        "base_url": settings.BASE_URL,
    })


@app.get("/design", response_class=HTMLResponse)
@app.get("/conventional", response_class=HTMLResponse)
@app.get("/design/conventional", response_class=HTMLResponse)
def design_page(request: Request):
    """Conventional Mix Design Workbench (OPC / PPC / PSC) — IS 10262:2019."""
    return templates.TemplateResponse(request=request, name="design.html", context={
        "title": "Conventional Mix Design (OPC / PPC / PSC) — ConcreteMix AI",
        "description": "IS 10262:2019 proportioning calculator for OPC 33/43/53, PPC, and PSC with natural language statement solver.",
        "base_url": settings.BASE_URL,
        "type_schemas": TYPE_SCHEMAS,
    })


@app.get("/special", response_class=HTMLResponse)
@app.get("/design/special", response_class=HTMLResponse)
def special_design_page(request: Request):
    """Special Concrete Mix Workbench — Geopolymer and 11 literature-anchored special concrete types."""
    return templates.TemplateResponse(request=request, name="special_design.html", context={
        "title": "Special Concrete Mix Workbench (Geopolymer & High-Performance) — ConcreteMix AI",
        "description": "Direct parameter-driven mix formulation for Geopolymer (195 literature mixes) and 11 special concrete families.",
        "base_url": settings.BASE_URL,
        "type_schemas": TYPE_SCHEMAS,
    })


@app.get("/library", response_class=HTMLResponse)
def library_page(request: Request):
    """Knowledge Library — browse and search solved examples."""
    return templates.TemplateResponse(request=request, name="library.html", context={
        "title": "Knowledge Library — ConcreteMix AI",
        "description": "Browse 100+ solved concrete mix design examples with IS code references.",
        "base_url": settings.BASE_URL,
    })


@app.get("/examples/{example_id}", response_class=HTMLResponse)
def example_detail_page(request: Request, example_id: str):
    """Example detail page."""
    mgr = ExampleManager(SessionLocal)
    example = mgr.get_example(example_id)
    if not example:
        return templates.TemplateResponse(request=request, name="404.html", context={
            "title": "Not Found"
        }, status_code=404)
    return templates.TemplateResponse(request=request, name="example_detail.html", context={
        "title": f"Example {example_id} — ConcreteMix AI",
        "description": f"Solved mix design: {example.get('grade', '')} concrete, {example.get('exposure', '')} exposure",
        "example": example,
        "base_url": settings.BASE_URL,
    })


@app.get("/methodology", response_class=HTMLResponse)
def methodology_page(request: Request):
    """Technical Methodology page."""
    return templates.TemplateResponse(request=request, name="methodology.html", context={
        "title": "Technical Methodology — ConcreteMix AI",
        "description": "How ConcreteMix AI calculates mix designs: deterministic IS 10262 engine, hybrid retrieval, validation.",
        "base_url": settings.BASE_URL,
    })


@app.get("/docs", response_class=HTMLResponse)
def docs_page(request: Request):
    """Documentation & FAQ page."""
    return templates.TemplateResponse(request=request, name="docs.html", context={
        "title": "Documentation — ConcreteMix AI",
        "description": "User guide, FAQ, and technical documentation for ConcreteMix AI.",
        "base_url": settings.BASE_URL,
    })


@app.get("/sources", response_class=HTMLResponse)
def sources_page(request: Request):
    """Research literature references page."""
    return templates.TemplateResponse(request=request, name="sources.html", context={
        "title": "Research Literature Sources & Citations — ConcreteMix AI",
        "description": "Published standards, technical committee reports, and landmark papers anchoring the 301 special concrete reference mix dataset.",
        "base_url": settings.BASE_URL,
    })


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    """Admin panel page."""
    return templates.TemplateResponse(request=request, name="admin.html", context={
        "title": "Admin — ConcreteMix AI",
        "base_url": settings.BASE_URL,
    })


# ── SEO educational pages ────────────────────────────────────────────────────

@app.get("/learn/{type_slug}-mix-design", response_class=HTMLResponse)
def special_type_learn_page(request: Request, type_slug: str):
    """Dynamic SEO educational guide for 12 special concrete types."""
    from app.engine.concrete_type import SPECIAL_TYPES, TYPE_DETAILS
    if type_slug not in SPECIAL_TYPES:
        return templates.TemplateResponse(request=request, name="404.html", context={
            "title": "Page Not Found",
            "base_url": settings.BASE_URL,
        }, status_code=404)

    meta = dict(TYPE_DETAILS.get(type_slug, {}))
    meta["slug"] = type_slug

    # Load top 15 keywords for this type
    kw_path = os.path.join(settings.DATA_DIR, "examples", "special", "keyword_banks.json")
    type_kws = []
    if os.path.exists(kw_path):
        try:
            with open(kw_path, "r", encoding="utf-8") as f:
                kb = json.load(f)
                type_kws = kb.get(type_slug, [])[:15]
        except Exception:
            type_kws = []

    # Pull 3 sample mixes from database
    db = SessionLocal()
    sample_mixes = []
    try:
        samples = db.query(Example).filter(Example.concrete_type == type_slug).limit(3).all()
        mgr = ExampleManager(SessionLocal)
        sample_mixes = [mgr._to_dict(s) for s in samples]
        meta["count"] = db.query(Example).filter(Example.concrete_type == type_slug).count()
    finally:
        db.close()

    return templates.TemplateResponse(request=request, name="seo/special-type.html", context={
        "title": f"{meta['name']} Mix Design Guide & Reference Proportions — ConcreteMix AI",
        "type_slug": type_slug,
        "type_meta": meta,
        "type_keywords": type_kws,
        "sample_mixes": sample_mixes,
        "base_url": settings.BASE_URL,
    })


@app.get("/learn/concrete-mix-design-is-10262", response_class=HTMLResponse)
def seo_is10262(request: Request):
    return templates.TemplateResponse(request=request, name="seo/concrete-mix-design-is-10262.html", context={
        "title": "Concrete Mix Design as per IS 10262:2019 — Complete Guide",
        "description": "Learn how to design concrete mixes following IS 10262:2019 guidelines. Step-by-step procedure with examples.",
        "base_url": settings.BASE_URL,
    })


@app.get("/learn/target-mean-strength", response_class=HTMLResponse)
def seo_target_strength(request: Request):
    return templates.TemplateResponse(request=request, name="seo/target-mean-strength.html", context={
        "title": "Target Mean Strength Calculation for Concrete — IS 10262",
        "description": "How to calculate target mean compressive strength for concrete mix design using IS 10262:2019.",
        "base_url": settings.BASE_URL,
    })


@app.get("/learn/water-cement-ratio", response_class=HTMLResponse)
def seo_wc_ratio(request: Request):
    return templates.TemplateResponse(request=request, name="seo/water-cement-ratio.html", context={
        "title": "Water-Cement Ratio Selection in Concrete Mix Design",
        "description": "How to select and control water-cement ratio based on strength and durability requirements per IS 456.",
        "base_url": settings.BASE_URL,
    })


# ═══════════════════════════════════════════════════════════════════════════
# SEO FILES
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    return f"""User-agent: *
Allow: /
Allow: /library
Allow: /learn/
Disallow: /admin
Disallow: /api/admin
Disallow: /api/docs
Disallow: /api/redoc

Sitemap: {settings.BASE_URL}/sitemap.xml
"""


@app.get("/sitemap.xml")
def sitemap_xml():
    """XML sitemap for search engines."""
    now = datetime.utcnow().strftime("%Y-%m-%d")
    urls = [
        (f"{settings.BASE_URL}/", "1.0", "weekly"),
        (f"{settings.BASE_URL}/design", "0.9", "weekly"),
        (f"{settings.BASE_URL}/library", "0.8", "weekly"),
        (f"{settings.BASE_URL}/methodology", "0.7", "monthly"),
        (f"{settings.BASE_URL}/docs", "0.7", "monthly"),
        (f"{settings.BASE_URL}/learn/concrete-mix-design-is-10262", "0.8", "monthly"),
        (f"{settings.BASE_URL}/learn/target-mean-strength", "0.7", "monthly"),
        (f"{settings.BASE_URL}/learn/water-cement-ratio", "0.7", "monthly"),
    ]

    from app.engine.concrete_type import SPECIAL_TYPES
    for st in SPECIAL_TYPES:
        urls.append((f"{settings.BASE_URL}/learn/{st}-mix-design", "0.8", "monthly"))

    # Add example pages
    db = SessionLocal()
    try:
        examples = db.query(Example.external_id).all()
        for (eid,) in examples:
            urls.append((f"{settings.BASE_URL}/examples/{eid}", "0.5", "monthly"))
    finally:
        db.close()

    xml_entries = ""
    for url, priority, freq in urls:
        xml_entries += f"""  <url>
    <loc>{url}</loc>
    <lastmod>{now}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
  </url>\n"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{xml_entries}</urlset>"""

    return Response(content=xml, media_type="application/xml")


# ── Error pages ──────────────────────────────────────────────────────────────

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return Response(
            content=json.dumps({"detail": "Not found"}),
            status_code=404,
            media_type="application/json",
        )
    return templates.TemplateResponse(request=request, name="404.html", context={
        "title": "Page Not Found"
    }, status_code=404)
