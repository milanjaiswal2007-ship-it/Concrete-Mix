"""Keyword-based concrete type detector for 12 special concrete types.

Uses normalized phrase matching from keyword_banks.json with phrase-length
weighting, acronym detection, and explicit domain-specific disambiguation rules.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SPECIAL_TYPES = [
    "geopolymer",
    "self-healing",
    "self-sensing",
    "self-compacting",
    "3d-printing",
    "uhpc",
    "ecc",
    "lightweight",
    "co2-injected",
    "sea-sand",
    "pervious",
    "fiber-reinforced",
]

# Acronyms with word boundaries and fixed high weight
ACRONYMS = {
    "SCC": ("self-compacting", 3.5),
    "UHPC": ("uhpc", 4.0),
    "UHPFRC": ("uhpc", 4.5),
    "ECC": ("ecc", 3.5),
    "SHCC": ("ecc", 3.5),
    "CLC": ("lightweight", 3.0),
    "AAC": ("lightweight", 3.0),
    "LWC": ("lightweight", 3.0),
    "MICP": ("self-healing", 3.5),
    "FRC": ("fiber-reinforced", 3.0),
    "SFRC": ("fiber-reinforced", 3.5),
    "3DCP": ("3d-printing", 3.5),
}

# Core domain-defining root terms for each special concrete type
CORE_TYPE_KEYWORDS = {
    "geopolymer": [
        "geopolymer", "alkali activated", "fly ash based geopolymer",
        "slag based geopolymer", "naoh molarity", "sodium silicate solution"
    ],
    "self-healing": [
        "self healing", "autonomous healing", "autogenous healing",
        "bacterial concrete", "bacteria healing", "healing concrete", "microcapsule healing",
        "crystalline waterproofing healing", "bacillus", "microbial induced"
    ],
    "self-sensing": [
        "self sensing", "self monitoring", "piezoresistive",
        "piezoresistivity", "smart concrete", "carbon nanotube sensing", "conductive concrete",
        "electrical resistivity sensing"
    ],
    "self-compacting": [
        "self compacting", "self consolidating",
        "scc", "slump flow", "v funnel", "l box", "u box", "efnarc"
    ],
    "3d-printing": [
        "3d printing", "3d printed", "3dcp",
        "extrusion based", "contour crafting", "printable concrete", "buildability"
    ],
    "uhpc": [
        "uhpc", "ultra high performance", "uhpfrc",
        "reactive powder concrete", "rpc"
    ],
    "ecc": [
        "ecc", "engineered cementitious composite",
        "shcc", "strain hardening cementitious", "bendable concrete"
    ],
    "lightweight": [
        "lightweight", "light weight", "leca", "expanded clay",
        "foamed concrete", "foam concrete", "cellular concrete", "aerated concrete",
        "pumice aggregate", "perlite concrete", "vermiculite concrete", "autoclaved aerated"
    ],
    "co2-injected": [
        "co2 injected", "co2 mineralization", "co2 mineralised",
        "co2 mineralized", "carbon curing", "carbon dioxide injection", "carboncure"
    ],
    "sea-sand": [
        "sea sand", "seawater concrete", "sea water concrete",
        "seawater mixing", "sea water mixing", "marine sand concrete", "desalinated sea sand"
    ],
    "pervious": [
        "pervious", "porous concrete", "permeable concrete", "no fines concrete",
        "drainable concrete"
    ],
    "fiber-reinforced": [
        "fiber reinforced", "frc", "sfrc", "steel fiber", "synthetic fiber",
        "polypropylene fiber", "basalt fiber", "glass fiber reinforced"
    ],
}

_KEYWORD_BANKS: Optional[Dict[str, List[str]]] = None
_NORMALIZED_BANKS: Optional[Dict[str, List[Tuple[str, float, int]]]] = None


def normalize_text(text: str) -> str:
    """Normalize text: lowercase, normalize fiber/fibre, 3d, collapse hyphens/spaces."""
    if not text:
        return ""
    t = text.lower()
    # Normalize fibre <-> fiber
    t = t.replace("fibre", "fiber")
    # Normalize 3 d / 3-d / 3d
    t = re.sub(r"\b3\s*d\b", "3d", t)
    t = re.sub(r"\b3-d\b", "3d", t)
    # Collapse hyphens, underscores to spaces
    t = re.sub(r"[-_]", " ", t)
    # Strip extraneous punctuation, keep alphanumeric and periods
    t = re.sub(r"[^\w\s\.]", " ", t)
    # Collapse multiple spaces
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _load_keyword_banks() -> None:
    """Load keyword_banks.json once and precompute normalized keyword patterns."""
    global _KEYWORD_BANKS, _NORMALIZED_BANKS
    if _KEYWORD_BANKS is not None:
        return

    from app.config import settings

    path = os.path.join(
        settings.DATA_DIR, "examples", "special", "keyword_banks.json"
    )
    if not os.path.exists(path):
        # Fallback to local path relative to this file
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "examples", "special", "keyword_banks.json"
        )

    try:
        with open(path, "r", encoding="utf-8") as f:
            _KEYWORD_BANKS = json.load(f)
    except Exception as e:
        logger.error("Could not load keyword_banks.json from %s: %e", path, e)
        _KEYWORD_BANKS = {t: [] for t in SPECIAL_TYPES}

    _NORMALIZED_BANKS = {}
    for ctype, kws in _KEYWORD_BANKS.items():
        norm_list = []
        for kw in kws:
            kw_norm = normalize_text(kw)
            if not kw_norm:
                continue
            words = kw_norm.split()
            n_words = len(words)
            # multi-word phrases weigh more: 1 + 0.5 * (n_words - 1)
            weight = 1.0 + 0.5 * (n_words - 1)
            norm_list.append((kw_norm, weight, n_words))
        # Sort so longer phrases match first
        norm_list.sort(key=lambda x: (x[2], len(x[0])), reverse=True)
        _NORMALIZED_BANKS[ctype] = norm_list


def detect_concrete_type(text: str) -> Dict[str, Any]:
    """Detect concrete type from problem text using weighted keywords and disambiguation rules.

    Returns:
        {
            "type": Optional[str],         # Slug or None if conventional
            "confidence": float,           # 0.0 to 1.0
            "matched_keywords": List[str], # List of matched keywords
            "runner_up": Optional[str],    # Next best candidate slug
            "scores": Dict[str, float],    # Raw score per type
        }
    """
    if not text:
        return {
            "type": None,
            "detected_type": None,
            "confidence": 0.0,
            "matched_keywords": [],
            "runner_up": None,
            "scores": {},
        }

    _load_keyword_banks()
    norm_text = normalize_text(text)
    scores: Dict[str, float] = {t: 0.0 for t in SPECIAL_TYPES}
    matched: Dict[str, List[str]] = {t: [] for t in SPECIAL_TYPES}

    # 1. Exact acronym checks on original text (case-insensitive word boundary)
    for acronym, (ctype, weight) in ACRONYMS.items():
        if re.search(rf"\b{acronym}\b", text, re.I):
            scores[ctype] += weight
            matched[ctype].append(acronym)

    # 1b. Core root term checks
    for ctype, root_terms in CORE_TYPE_KEYWORDS.items():
        for term in root_terms:
            norm_term = normalize_text(term)
            if re.search(rf"\b{re.escape(norm_term)}\b", norm_text):
                scores[ctype] += 3.0
                matched[ctype].append(term)

    # 2. Phrase matching against keyword banks
    for ctype, kw_entries in (_NORMALIZED_BANKS or {}).items():
        for kw_norm, weight, n_words in kw_entries:
            # Build regex with word boundaries
            pattern = rf"\b{re.escape(kw_norm)}\b"
            if re.search(pattern, norm_text):
                scores[ctype] += weight
                matched[ctype].append(kw_norm)

    # 3. Disambiguation Rules

    # Rule 4: "previous" typo check - must NOT trigger pervious
    if "previous" in norm_text and not re.search(r"\bpervious\b", norm_text):
        # strip any accidental pervious matches
        scores["pervious"] = 0.0
        matched["pervious"] = []

    # Rule 3: Seawater / sea water alone near curing/coastal without mixing/sea sand
    # Do NOT trigger sea-sand unless explicit "sea sand" or "seawater concrete" or "mixing with sea water"
    has_sea_sand = bool(re.search(r"\bsea\s*sand\b", norm_text))
    has_seawater_mixing = bool(
        re.search(
            r"\b(?:seawater|sea\s*water)\s*(?:mixing|concrete|mix|slurry|batching)\b|\b(?:mixing|batched)\s*(?:with|using)?\s*(?:seawater|sea\s*water)\b",
            norm_text,
        )
    )
    if not (has_sea_sand or has_seawater_mixing):
        # Mere mention of sea water in coastal/tidal context is conventional IS 456
        scores["sea-sand"] = 0.0
        matched["sea-sand"] = []

    # Rule 6: Self-compacting + UHPC -> UHPC takes priority
    if scores["uhpc"] > 0 and scores["self-compacting"] > 0:
        if re.search(r"\buhpc\b|\bultra\s*high\s*performance\b", norm_text):
            scores["uhpc"] += scores["self-compacting"]
            scores["self-compacting"] = 0.0

    # Rule 2: UHPC with steel fibre stays UHPC; generic steel fibre without UHPC/ECC -> fiber-reinforced
    if scores["uhpc"] > 0 and re.search(r"\buhpc\b|\bultra\s*high\s*performance\b", norm_text):
        scores["fiber-reinforced"] = 0.0

    # Rule 1: Self-healing vs ECC (both can use PVA or microfibres)
    # "self healing" + "ECC/PVA" -> ECC unless "bacteria|crystalline|capsule|SAP" present -> self-healing
    if re.search(r"\bself\s*healing\b|\bautogenous\s*healing\b|\bautonomous\s*healing\b", norm_text):
        if re.search(r"\b(?:ecc|pva)\b", norm_text):
            if re.search(r"\b(?:bacteria|bacterial|crystalline|capsule|microcapsule|sap|spores|bacillus)\b", norm_text):
                scores["self-healing"] += 5.0
                scores["ecc"] = 0.0
            else:
                scores["ecc"] += 5.0
                scores["self-healing"] = 0.0

    # Rule 5: Lightweight keywords boost
    if re.search(r"\b(?:foam|foamed|aerated|leca|lightweight|expanded\s*clay|pumice)\b", norm_text):
        scores["lightweight"] += 2.0

    # Rule 7: Negative filter for standard conventional concrete
    # If standard conventional phrases are present with no strong special keywords
    is_conventional_statement = bool(
        re.search(
            r"\b(?:opc\s*(?:33|43|53)|ppc|psc|is\s*10262|m\s*\d{2}\s*(?:mix|for|slab|beam|column))\b",
            norm_text,
        )
    )

    # Sort candidates
    sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_type, best_score = sorted_types[0]
    runner_up_type, runner_up_score = sorted_types[1] if len(sorted_types) > 1 else (None, 0.0)

    # Thresholding & margin
    # If no score or best_score < 2.0 -> conventional
    min_threshold = 2.0
    if best_score < min_threshold:
        return {
            "type": None,
            "detected_type": None,
            "confidence": 0.0,
            "matched_keywords": [],
            "runner_up": None,
            "scores": {k: round(v, 2) for k, v in scores.items() if v > 0},
        }

    # If conventional statement dominates without strong special keywords
    if is_conventional_statement and best_score < 3.5:
        return {
            "type": None,
            "detected_type": None,
            "confidence": 0.0,
            "matched_keywords": [],
            "runner_up": best_type,
            "scores": {k: round(v, 2) for k, v in scores.items() if v > 0},
        }

    # Check margin over runner-up (unless top score is very decisive >= 4.0)
    if runner_up_score > 0 and (best_score - runner_up_score) / best_score < 0.20 and best_score < 4.0:
        # Ambiguous candidate
        return {
            "type": None,
            "detected_type": None,
            "confidence": round(best_score / (best_score + runner_up_score + 1e-5), 2),
            "matched_keywords": matched.get(best_type, []),
            "runner_up": runner_up_type,
            "scores": {k: round(v, 2) for k, v in scores.items() if v > 0},
        }

    # Confidence calculation: bounded between 0.50 and 0.99
    confidence = min(0.99, max(0.50, round(best_score / (best_score + 2.0), 2)))

    return {
        "type": best_type,
        "detected_type": best_type,
        "confidence": confidence,
        "matched_keywords": list(dict.fromkeys(matched.get(best_type, []))),
        "runner_up": runner_up_type if runner_up_score > 0 else None,
        "scores": {k: round(v, 2) for k, v in scores.items() if v > 0},
    }


TYPE_DETAILS: Dict[str, Dict[str, Any]] = {
    "geopolymer": {
        "name": "Geopolymer Concrete",
        "definition": "Zero-cement alkali-activated concrete synthesised by activating aluminosilicate industrial by-products (low-calcium Class F fly ash, ground granulated blast furnace slag) with alkaline solutions of sodium hydroxide (NaOH) and sodium silicate (Na2SiO3). It exhibits high early strength, exceptional thermal stability up to 800°C, and superior acid/sulfate resistance.",
        "sources": [
            "Hardjito & Rangan (2005) Development and properties of low-calcium fly ash-based geopolymer concrete, Curtin Univ. Research Report GC1",
            "Davidovits (2008) Geopolymer Chemistry and Applications",
            "Provis & van Deventer (eds.) RILEM TC 224-AAM (2014) Alkali-Activated Materials",
        ],
    },
    "self-healing": {
        "name": "Self-Healing Concrete",
        "definition": "Bio-chemical smart concrete engineered with autonomous crack-sealing mechanisms. Uses dormant alkaliphilic bacterial spores (Bacillus pseudofirmus or B. cohnii) with calcium lactate nutrients, or encapsulated sodium silicate / crystalline mineral additives that precipitate calcite (CaCO3) upon water ingress to close microcracks up to 0.8 mm.",
        "sources": [
            "De Belie et al. (2018) Adv. Mater. Interfaces 5(17)",
            "Jonkers et al. (2010) Bacterial concrete: A biological approach to increase the duration of concrete structures, Ecol. Eng. 36",
            "RILEM TC 221-SHC Self-Healing Phenomena in Cement-Based Materials",
        ],
    },
    "self-sensing": {
        "name": "Self-Sensing / Smart Concrete",
        "definition": "Multifunctional structural health monitoring concrete loaded with electrically conductive functional fillers (carbon nanotubes, carbon nanofibres, graphene nanoplatelets, or nickel powder). It exhibits piezoresistivity — changing electrical resistivity reversibly under applied strain, stress, or crack initiation without embedded external sensors.",
        "sources": [
            "Chung (2002) Piezoresistive cement-based materials for smart structures",
            "Han, Ding, Ou et al. (2015) Self-sensing concrete with functional fillers, Sensors 15",
            "D'Alessandro et al. (2016) Piezoresistive properties of cementitious composites",
        ],
    },
    "self-compacting": {
        "name": "Self-Compacting Concrete (SCC)",
        "definition": "Highly fluid, non-segregating concrete that consolidates under its own self-weight without external vibration. Formulated with high powder volumes (450–650 kg/m³), limited coarse aggregate volumes, and polycarboxylate ether (PCE) superplasticisers to navigate heavily congested reinforcement without honeycombing.",
        "sources": [
            "EFNARC (2005) Specification and Guidelines for Self-Compacting Concrete",
            "Okamura & Ouchi (2003) Self-Compacting Concrete, J. Adv. Concr. Technol. 1(1)",
            "ACI 237R-07 Self-Consolidating Concrete",
        ],
    },
    "3d-printing": {
        "name": "3D Printable Concrete (3DCP)",
        "definition": "Extrusion-based cementitious composite tailored for additive construction without traditional formwork. Balances early open-time pumpability and extrudability with rapid thixotropic rebuild, high green strength buildability, and minimal interlayer cold-joint formation.",
        "sources": [
            "Le et al. (2012) Mix design and fresh properties for 3D printing, Mater. Struct. 45",
            "Buswell et al. (2018) 3D concrete printing fabrication, Cem. Concr. Res. 112",
            "Panda & Tan (2018) Rheological properties for 3D printing",
        ],
    },
    "uhpc": {
        "name": "Ultra-High Performance Concrete (UHPC)",
        "definition": "High-durability cementitious material with compressive strength exceeding 120–180 MPa and sustained post-crack tensile ductility. Achieved via continuous particle packing, ultra-low w/b ratio (<0.20), dense micro-silica matrix, elimination of coarse aggregates (>0.6 mm), and 1.5–2.5 vol% high-tensile steel microfibres.",
        "sources": [
            "Richard & Cheyrezy (1995) Composition of reactive powder concretes, Cem. Concr. Res. 25",
            "Graybeal (2006) Material Property Characterization of UHPC, FHWA-HRT-06-103",
            "AFGC/SETRA (2013) Ultra High Performance Fibre-Reinforced Concrete",
        ],
    },
    "ecc": {
        "name": "Engineered Cementitious Composites (ECC)",
        "definition": "Micromechanically designed fiber-reinforced composite (bendable concrete) achieving extreme tensile strain ductility exceeding 3–5% (over 300 times conventional concrete). Utilizes PVA microfibres with controlled matrix-fiber interface properties to maintain steady-state microcracking without localization.",
        "sources": [
            "Li (2003) On Engineered Cementitious Composites (ECC), J. Adv. Concr. Technol. 1(3)",
            "Li et al. (2001) Large volume fly ash engineered cementitious composites, ACI Mater. J.",
            "Wang & Li (2007) Engineered Cementitious Composites with PVA fibers",
        ],
    },
    "lightweight": {
        "name": "Lightweight / Cellular Concrete",
        "definition": "Structural or insulating concrete with oven-dry equilibrium density under 800–1800 kg/m³. Proportioned using expanded clay (LECA), volcanic pumice, expanded shale, or pre-formed surfactant foaming agents to dramatically reduce dead weight and provide superior thermal/acoustic insulation.",
        "sources": [
            "ACI 213R-14 Guide for Structural Lightweight-Aggregate Concrete",
            "ACI 523.3R-14 Guide for Cellular Concrete",
            "Ramamurthy et al. (2009) Classification of cellular concrete, Cem. Concr. Compos. 31",
        ],
    },
    "co2-injected": {
        "name": "CO₂-Injected / Mineralised Concrete",
        "definition": "Carbon-negative concrete technology where controlled doses of recycled industrial carbon dioxide (0.05–0.3% bwoc) are injected during wet batching. The CO₂ reacts instantly with hydrating calcium ions to precipitate thermodynamically stable nano-CaCO3 crystals, accelerating early strength and permitting a 5–10% cement reduction.",
        "sources": [
            "Monkman, MacDonald, Hooton & Sandberg (2016) Carbon dioxide upcycling, Cem. Concr. Compos. 74",
            "Monkman & Shao (2010) Integration of carbonated slag in concrete",
            "CarbonCure Technical Documentation",
        ],
    },
    "sea-sand": {
        "name": "Sea-Sand / Seawater Concrete",
        "definition": "Sustainable coastal infrastructure concrete utilizing untreated or desalinated marine dredged sand and seawater mixing. Because sea sand and seawater carry high chloride ions (0.05–0.15% Cl-), this mix must be paired strictly with non-corrosive GFRP/BFRP composite reinforcement or stainless steel, or deployed in mass unreinforced PCC.",
        "sources": [
            "Xiao, Qiang, Nanni & Zhang (2017) Seawater sea-sand concrete, Constr. Build. Mater. 155",
            "Teng et al. (2018) FRP composites in seawater sea-sand concrete structures, PolyU",
            "IS 456:2000 Cl. 8.2.5 & Table 7 Limits on Chlorides",
        ],
    },
    "pervious": {
        "name": "Pervious / Porous Concrete",
        "definition": "No-fines high-permeability pavement concrete containing little or no sand, creating 15–30% interconnected macropores. It allows stormwater runoff to infiltrate directly at rates of 120–700 L/min/m², recharging underlying aquifers while mitigating urban flash flooding and urban heat island effects.",
        "sources": [
            "ACI 522R-10 Report on Pervious Concrete",
            "Tennis, Leming & Akers (2004) Pervious Concrete Pavements, PCA EB302",
            "NRMCA Pervious Concrete Contractor Certification Guide",
        ],
    },
    "fiber-reinforced": {
        "name": "Fibre-Reinforced Concrete (FRC)",
        "definition": "Concrete containing uniformly dispersed, randomly oriented structural macro-fibres (hooked-end steel, corrugated polypropylene, basalt, or alkali-resistant glass). Fibre bridging prevents catastrophic brittle failure, increases post-crack flexural toughness (residual flexural strength), and dramatically enhances fatigue/impact resistance.",
        "sources": [
            "ACI 544.1R-96 State-of-the-Art Report on Fiber Reinforced Concrete",
            "RILEM TC 162-TDF (2003) Test and design methods for steel fibre reinforced concrete",
            "Bentur & Mindess (2007) Fibre Reinforced Cementitious Composites",
        ],
    },
}
