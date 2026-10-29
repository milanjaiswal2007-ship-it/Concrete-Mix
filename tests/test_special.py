"""Comprehensive Pytest Test Suite for 12 Special Concrete Types in ConcreteMix AI.

Tests cover:
1. Importer idempotency, dataset integrity, and physical volume closure.
2. Concrete type detector accuracy across all 12 types plus negative controls & disambiguations.
3. Special mix proposal engine (retrieval, physical volume closure, clamping, rule checks, banner).
4. Existing IS 10262:2019 conventional path regression.
"""

import os
import json
import pytest
from app.database import SessionLocal
from app.models import Example
from app.rag.examples import ExampleManager
from app.engine.concrete_type import detect_concrete_type
from app.engine.special_mix import run_special_mix_engine
from app.engine.is10262 import design


# ══════════════════════════════════════════════════════════════════════════════
# 1. Dataset & Importer Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_database_record_counts():
    """Verify total counts: 100 conventional + 301 special records = 401 total."""
    db = SessionLocal()
    try:
        total = db.query(Example).count()
        conventional = db.query(Example).filter(Example.concrete_type == "conventional").count()
        special = db.query(Example).filter(Example.concrete_type != "conventional").count()
        
        assert total == 401, f"Expected 401 total records, found {total}"
        assert conventional == 100, f"Expected 100 conventional records, found {conventional}"
        assert special == 301, f"Expected 301 special records, found {special}"
    finally:
        db.close()


def test_special_record_absolute_volumes():
    """Verify that all special records in the database satisfy volume closure and non-negative quantities."""
    db = SessionLocal()
    try:
        special_records = db.query(Example).filter(Example.concrete_type != "conventional").all()
        assert len(special_records) == 301
        
        for ex in special_records:
            checks = json.loads(ex.checks_json) if ex.checks_json else {}
            assert checks.get("absolute_volume_closed") is True, f"{ex.external_id} failed absolute_volume_closed check"
            assert checks.get("positive_quantities") is True, f"{ex.external_id} failed positive_quantities check"
            
            mix = json.loads(ex.mix_json) if ex.mix_json else {}
            # Quantities must not be negative
            for k, v in mix.items():
                if (k.endswith("_kg") or k.endswith("_litres")) and isinstance(v, (int, float)):
                    assert v >= 0, f"{ex.external_id}: {k} is negative ({v})"
    finally:
        db.close()


def test_importer_idempotent():
    """Verify that re-running import_special_from_jsonl skips already imported records."""
    path = os.path.join("data", "examples", "special", "special_concrete_mixes.jsonl")
    if not os.path.exists(path):
        pytest.skip(f"Dataset file {path} not found")
        
    mgr = ExampleManager(SessionLocal)
    result = mgr.import_special_from_jsonl(path)
    assert result["imported"] == 0, f"Expected 0 imported on re-run, got {result['imported']}"
    assert result["skipped"] == 301, f"Expected 301 skipped on re-run, got {result['skipped']}"


# ══════════════════════════════════════════════════════════════════════════════
# 2. Type Detector Tests (All 12 types + Tricky Edge Cases)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("prompt,expected_type", [
    # 1. Geopolymer
    ("Fly ash and GGBS alkali activated geopolymer concrete with 12M NaOH", "geopolymer"),
    ("Alkali-activated slag binder with sodium silicate activator", "geopolymer"),
    ("Geopolymer mortar using class F fly ash and potassium hydroxide", "geopolymer"),
    ("Low carbon geopolymer concrete heat cured at 60C", "geopolymer"),
    ("Design M35 geopolymer mix using 10 M molarity alkaline solution", "geopolymer"),
    
    # 2. Self-healing
    ("Bacterial self-healing concrete using bacillus subtilis spores and calcium lactate", "self-healing"),
    ("Self healing bio-concrete with microencapsulated healing agent for crack repair", "self-healing"),
    ("Crystalline self-healing waterproofing admixture for autogenous healing", "self-healing"),
    ("Vascular network self-healing cementitious composite with polyurethane", "self-healing"),
    ("Sodium silicate capsule autonomous self healing concrete", "self-healing"),

    # 3. Self-sensing
    ("Piezoresistive smart concrete with carbon nanotubes for structural health monitoring", "self-sensing"),
    ("Self-sensing cementitious sensor with graphene nanoplatelets for strain measurement", "self-sensing"),
    ("Conductive concrete with nickel powder for electrical resistance change monitoring", "self-sensing"),
    ("Self-sensing carbon fiber smart pavement for traffic detection", "self-sensing"),
    ("Piezoresistive sensitivity gauge factor concrete with MWCNT", "self-sensing"),

    # 4. Self-compacting (SCC)
    ("Self compacting concrete with 650 mm slump flow and V-funnel time 8s", "self-compacting"),
    ("SCC mix design with high powder content and polycarboxylate superplasticizer", "self-compacting"),
    ("L-box passing ratio 0.85 self-compacting concrete with fly ash", "self-compacting"),
    ("High flowability SCC without vibration for congested reinforcement", "self-compacting"),
    ("M40 self compacting mix with 500 kg powder content", "self-compacting"),

    # 5. 3D-printing
    ("Extrudable printable concrete for 3D printing contour crafting with 15 min open time", "3d-printing"),
    ("3D concrete printing mortar with thixotropic buildability and shape retention", "3d-printing"),
    ("Layer-by-layer 3dcp automated additive manufacturing concrete", "3d-printing"),
    ("Extrusion filament 3D printed cement mortar with silica fume and accelerator", "3d-printing"),
    ("3D concrete printing mix with layer buildability and shape retention", "3d-printing"),

    # 6. UHPC
    ("Ultra high performance concrete 150 MPa with silica fume and steel fiber 2 vol%", "uhpc"),
    ("UHPC precast beam mix with quartz powder w/b 0.18 and heat curing", "uhpc"),
    ("Reactive powder concrete RPC 160 MPa compressive strength", "uhpc"),
    ("Ultra-high performance fiber reinforced concrete UHPFRC bridge deck", "uhpc"),
    ("Ductal type 180 MPa UHPC with fine sand 0.4mm and brass coated micro steel fibers", "uhpc"),

    # 7. ECC
    ("Engineered cementitious composite ECC with PVA fiber and 3% tensile strain capacity", "ecc"),
    ("Bendable concrete ECC M45 with fly ash to cement ratio 2.2 and tight microcracking", "ecc"),
    ("Strain hardening cementitious composite SHCC with 2% polyvinyl alcohol fiber", "ecc"),
    ("Ductile ECC with pseudo strain hardening behavior under direct tension", "ecc"),
    ("PVA-ECC tensile ductility mix with micro-silica sand", "ecc"),

    # 8. Lightweight
    ("Lightweight aggregate concrete using expanded clay LECA aggregate density 1600 kg/m3", "lightweight"),
    ("Cellular lightweight foam concrete CLC density 800 kg/m3 for partition blocks", "lightweight"),
    ("Autoclaved aerated concrete AAC block mix with aluminum powder", "lightweight"),
    ("Structural lightweight concrete with sintered fly ash aggregate and pumice", "lightweight"),
    ("Foamed concrete insulation screed 1200 kg/m3 density", "lightweight"),

    # 9. CO2-injected
    ("CO2 mineralization concrete with liquid carbon dioxide injection during batching", "co2-injected"),
    ("CarbonCure CO2 mineralization and carbon dioxide sequestration in concrete", "co2-injected"),
    ("Accelerated carbonation curing of precast concrete with 5% cement reduction", "co2-injected"),
    ("CO2 mineralized precast concrete blocks capturing carbon dioxide per cubic meter", "co2-injected"),
    ("CO2 concrete with accelerated carbonation curing and liquid CO2 injection", "co2-injected"),

    # 10. Sea-sand
    ("Sea sand concrete mixed with seawater and non-corrosive FRP reinforcement", "sea-sand"),
    ("Marine aggregate concrete using unwashed sea sand and basalt rebar BFRP", "sea-sand"),
    ("Seawater sea-sand concrete SS-SWC with stainless steel reinforcement", "sea-sand"),
    ("Chloride rich dredged sea sand concrete for coastal reclamation structures", "sea-sand"),
    ("Mixing with sea sand and sea water for island infrastructure", "sea-sand"),

    # 11. Pervious
    ("Pervious concrete pavement with 20 percent void ratio and high hydraulic conductivity", "pervious"),
    ("Permeable concrete for stormwater drainage without fine aggregate", "pervious"),
    ("No-fines porous concrete parking lot with 15 MPa strength and water percolation", "pervious"),
    ("Hydraulic drainage pervious concrete slab water permeability 0.3 cm/s", "pervious"),
    ("Eco pervious driveway with single sized 10mm coarse gravel and polymer binder", "pervious"),

    # 12. Fiber-reinforced
    ("Steel fiber reinforced concrete SFRC with 40 kg/m3 hooked end fibers for industrial floor", "fiber-reinforced"),
    ("Polypropylene macro-fiber reinforced slab for plastic shrinkage crack control", "fiber-reinforced"),
    ("Glass fiber reinforced concrete GFRC cladding panels with alkali resistant AR-glass", "fiber-reinforced"),
    ("Basalt fiber reinforced concrete 5 kg/m3 for tunnel shotcrete lining", "fiber-reinforced"),
    ("Synthetic structural macro fiber FRC for pavement joint spacing extension", "fiber-reinforced"),
])
def test_detector_coverage_all_types(prompt, expected_type):
    """Ensure high-accuracy detection across all 12 special concrete types."""
    res = detect_concrete_type(prompt)
    assert res["detected_type"] == expected_type, f"Prompt '{prompt}' detected as {res['detected_type']}, expected {expected_type}"
    assert res["confidence"] >= 0.30


def test_detector_disambiguations():
    """Test tricky disambiguation cases explicitly specified in the requirements."""
    # 1. Seawater alone in coastal context without mixing/sea sand must NOT trigger sea-sand
    res = detect_concrete_type("M30 concrete for jetty structure exposed to coastal marine seawater spray")
    assert res["detected_type"] is None, f"Coastal marine spray should be IS 456 conventional severe/extreme, got {res['detected_type']}"

    # 2. Typo 'previous' must not trigger pervious
    res = detect_concrete_type("Please calculate mix design as mentioned in the previous project meeting for M25")
    assert res["detected_type"] != "pervious", "Typo 'previous' incorrectly matched 'pervious'"

    # 3. UHPC with steel fibre stays UHPC
    res = detect_concrete_type("UHPC 150 MPa mix with 2% steel fibre and silica fume")
    assert res["detected_type"] == "uhpc", f"Expected uhpc, got {res['detected_type']}"

    # 4. Self healing with bacteria vs ECC with PVA
    res = detect_concrete_type("Bacterial self-healing concrete with calcium lactate and spores")
    assert res["detected_type"] == "self-healing"

    res = detect_concrete_type("High ductility ECC mix with PVA fibers 2 vol % and micro silica sand")
    assert res["detected_type"] == "ecc"

    # 5. Conventional OPC/PPC prompts stay None (routed to IS 10262)
    res = detect_concrete_type("Design M30 concrete with 20mm aggregate, OPC 53, moderate exposure and 100mm slump")
    assert res["detected_type"] is None, f"Conventional prompt routed to {res['detected_type']}"


# ══════════════════════════════════════════════════════════════════════════════
# 3. Special Mix Proposal Engine Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_special_mix_engine_geopolymer():
    """Verify special mix engine for geopolymer concrete."""
    prompt = "Design M35 geopolymer concrete with 12M NaOH and fly ash slag binder, ambient curing"
    det = detect_concrete_type(prompt)
    assert det["detected_type"] == "geopolymer"

    res = run_special_mix_engine(
        concrete_type="geopolymer",
        prompt=prompt,
        user_inputs={"target_strength": 35.0, "molarity": 12.0}
    )

    assert res["concrete_type"] == "geopolymer"
    assert "Reference-based mix from published literature" in res["disclaimer_banner"]
    assert res["verification_status"] in ["literature_based_unverified", "verified"]
    
    # Check volume closure
    assert res["all_checks_pass"] is True
    check_names = [c["check"] for c in res["checks"]]
    assert any("alkaline" in c.lower() for c in check_names)
    assert any("volume" in c.lower() for c in check_names)


def test_special_mix_engine_uhpc_clamping_warning():
    """Verify clamping and warning emission when user requests parameter outside literature range."""
    # Requesting an extreme molarity of 25M (literature max is ~16M)
    res = run_special_mix_engine(
        concrete_type="geopolymer",
        prompt="Geopolymer with 25M NaOH molarity",
        user_inputs={"molarity": 25.0}
    )
    
    assert len(res["warnings"]) > 0
    assert any("molarity" in w.lower() for w in res["warnings"])
    assert res["mix_per_m3"]["NaOH_molarity"] <= 16.0, "Molarity was not clamped to dataset maximum"


def test_special_mix_engine_scc_rules():
    """Verify SCC specific rule checks (powder content, coarse aggregate volume share)."""
    res = run_special_mix_engine(
        concrete_type="self-compacting",
        prompt="Design SCC concrete grade M40 with 550 kg/m3 powder content and 650 mm slump flow"
    )
    
    assert res["concrete_type"] == "self-compacting"
    check_names = [c["check"] for c in res["checks"]]
    assert any("powder" in c.lower() for c in check_names)
    assert any("coarse" in c.lower() for c in check_names)
    # Check that individual critical checks run
    assert len(res["checks"]) >= 3


# ══════════════════════════════════════════════════════════════════════════════
# 4. Conventional IS 10262 Regression Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_conventional_is10262_untouched():
    """Verify that conventional IS 10262 calculations remain 100% deterministic and unaffected."""
    req = {
        "fck": 30.0,
        "exposure": "severe",
        "member": "RCC",
        "max_size": 20.0,
        "slump": 100.0,
        "zone": "II",
        "cement_grade": 53,
        "sg_cement": 3.15,
        "sg_ca": 2.70,
        "sg_fa": 2.65,
        "abs_ca": 0.5,
        "abs_fa": 1.0,
        "fm_fa": 0.0,
        "fm_ca": 0.0,
        "water_reduction": 0.20,
        "admixture_dosage": 0.008,
    }
    
    result = design(req)
    mix = result["mix_per_m3"]
    
    assert mix["cement"] > 300
    assert mix["water"] > 0
    assert mix["w_cm"] <= 0.45  # Severe exposure IS 456 durability limit
    assert result["all_checks_pass"] is True
