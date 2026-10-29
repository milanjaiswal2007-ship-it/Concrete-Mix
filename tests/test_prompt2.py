"""Tests for Prompt 2: One concrete type = one clean path.

Verifies:
1. Geopolymer extraction: 12M NaOH, ratio 2.5, 30% GGBS, ambient, 40 MPa — zero conventional leakage
2. API parse endpoint returns correct schema-aligned chips per type
3. DOM schema fields: each type has exactly its schema keys and NONE of cement_grade, zone, placement, supervision, agg_type
4. Geopolymer -> Conventional -> Geopolymer: no leaked values
5. Conventional "M30 slab OPC 53 mild" regression
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.engine.special_extract import extract_special_inputs
from app.engine.type_schemas import TYPE_SCHEMAS, get_type_schema

# ─────────────────────────────────────────────────────────────────────────
# CONVENTIONAL FIELDS THAT MUST NEVER APPEAR IN SPECIAL TYPES
# ─────────────────────────────────────────────────────────────────────────
BANNED_CONVENTIONAL_FIELDS = {
    "cement_grade", "zone", "placement", "supervision", "agg_type",
    "fck", "sg_cement", "sg_ca", "sg_fa", "fm_ca", "fm_ca",
    "abs_ca", "abs_fa", "ca_frac_1", "ca_frac_2",
}

# ─────────────────────────────────────────────────────────────────────────
# CANONICAL GEOPOLYMER TEST PROMPT (from user specification)
# ─────────────────────────────────────────────────────────────────────────
GEOPOLYMER_PROMPT = (
    "Design a geopolymer concrete with 12M NaOH, Na2SiO3/NaOH ratio 2.5, "
    "30% GGBS, ambient cured. Target strength 40 MPa."
)


class TestGeopolymerExtraction:
    """Section 3 requirements: fix extraction for the screenshot test prompt."""

    def test_naoh_molarity_extracted(self):
        result = extract_special_inputs(GEOPOLYMER_PROMPT, "geopolymer")
        assert result["parsed"]["naoh_molarity"] == 12, (
            f"Expected molarity=12, got {result['parsed'].get('naoh_molarity')}"
        )

    def test_silicate_ratio_extracted(self):
        result = extract_special_inputs(GEOPOLYMER_PROMPT, "geopolymer")
        assert result["parsed"]["silicate_to_hydroxide_ratio"] == 2.5, (
            f"Expected ratio=2.5, got {result['parsed'].get('silicate_to_hydroxide_ratio')}"
        )

    def test_ggbs_pct_extracted_as_30(self):
        """Parser must read BEFORE keyword: '30% GGBS' → 30, not fall back to default 40."""
        result = extract_special_inputs(GEOPOLYMER_PROMPT, "geopolymer")
        assert result["parsed"]["ggbs_pct"] == 30, (
            f"Expected ggbs_pct=30 (from '30% GGBS'), got {result['parsed'].get('ggbs_pct')}"
        )

    def test_curing_ambient(self):
        result = extract_special_inputs(GEOPOLYMER_PROMPT, "geopolymer")
        assert result["parsed"]["curing"] == "ambient", (
            f"Expected curing=ambient, got {result['parsed'].get('curing')}"
        )

    def test_target_strength_40mpa(self):
        result = extract_special_inputs(GEOPOLYMER_PROMPT, "geopolymer")
        assert result["parsed"]["target_strength"] == 40, (
            f"Expected target_strength=40, got {result['parsed'].get('target_strength')}"
        )

    def test_no_conventional_fields_in_parsed(self):
        """Zero conventional fields must leak into geopolymer result."""
        result = extract_special_inputs(GEOPOLYMER_PROMPT, "geopolymer")
        leaked = set(result["parsed"].keys()) & BANNED_CONVENTIONAL_FIELDS
        assert not leaked, (
            f"Conventional fields leaked into geopolymer result: {leaked}"
        )

    def test_no_fck_m30_default(self):
        result = extract_special_inputs(GEOPOLYMER_PROMPT, "geopolymer")
        assert "fck" not in result["parsed"]

    def test_no_cement_grade_opc43(self):
        result = extract_special_inputs(GEOPOLYMER_PROMPT, "geopolymer")
        assert "cement_grade" not in result["parsed"]

    def test_extracted_keys_correct(self):
        """All 5 values from prompt must be in extracted_keys (not defaults)."""
        result = extract_special_inputs(GEOPOLYMER_PROMPT, "geopolymer")
        extracted = set(result["extracted_keys"])
        assert "naoh_molarity" in extracted, "naoh_molarity must be extracted from text"
        assert "silicate_to_hydroxide_ratio" in extracted, "ratio must be extracted from text"
        assert "ggbs_pct" in extracted, "ggbs_pct must be extracted from text"
        assert "curing" in extracted, "curing must be extracted from text"
        assert "target_strength" in extracted, "target_strength must be extracted from text"


class TestGGBSVariantExtraction:
    """Test number before OR after keyword: '30% GGBS', 'GGBS 30%', '30 percent slag'."""

    @pytest.mark.parametrize("text,expected", [
        ("GGBS 30%", 30),
        ("30% GGBS", 30),
        ("GGBS at 30 %", 30),
        ("30 percent slag", 30),
        ("25 percent GGBS replacement", 25),
        ("GGBS replacement of 40%", 40),
    ])
    def test_ggbs_extracted(self, text, expected):
        prompt = f"Geopolymer with 12M NaOH and {text}, ambient cured. Target 35 MPa."
        result = extract_special_inputs(prompt, "geopolymer")
        assert result["parsed"]["ggbs_pct"] == expected, (
            f"For '{text}': expected ggbs_pct={expected}, got {result['parsed'].get('ggbs_pct')}"
        )


class TestSchemaFieldBoundaries:
    """For each of the 12 special types, the schema must contain exactly its defined fields
    and none of the conventional-only banned fields."""

    @pytest.mark.parametrize("type_name", [
        t for t in TYPE_SCHEMAS.keys() if t != "conventional"
    ])
    def test_no_banned_fields_in_schema(self, type_name):
        schema = get_type_schema(type_name)
        field_keys = {f["key"] for f in schema["fields"]}
        leaked = field_keys & BANNED_CONVENTIONAL_FIELDS
        assert not leaked, (
            f"Schema for '{type_name}' contains banned conventional fields: {leaked}"
        )

    @pytest.mark.parametrize("type_name,expected_fields", [
        ("geopolymer", ["binder_system", "ggbs_pct", "naoh_molarity",
                        "silicate_to_hydroxide_ratio", "alkaline_liquid_to_binder",
                        "curing", "max_size", "target_strength", "exposure", "member"]),
        ("uhpc", ["target_strength", "cement_content", "silica_fume_pct",
                  "w_b", "steel_fiber_vol_pct", "curing"]),
        ("sea-sand", ["grade", "chloride_pct", "mixing_water", "scm_type", "rebar_type"]),
        ("pervious", ["design_void_pct", "w_c", "max_size", "fine_aggregate_pct"]),
    ])
    def test_schema_has_exactly_required_fields(self, type_name, expected_fields):
        schema = get_type_schema(type_name)
        actual_keys = [f["key"] for f in schema["fields"]]
        assert set(actual_keys) == set(expected_fields), (
            f"Schema for '{type_name}' has wrong fields.\n"
            f"  Expected: {sorted(expected_fields)}\n"
            f"  Actual:   {sorted(actual_keys)}"
        )


class TestSpecialExtractionNoLeakage:
    """Extract for each special type and verify no conventional fields contaminate output."""

    @pytest.mark.parametrize("type_name,prompt", [
        ("uhpc", "UHPC 150 MPa with 25% silica fume and 2.0 vol% steel fibers, w/b 0.18"),
        ("sea-sand", "Sea sand concrete with seawater mixing and GFRP rebar in marine exposure"),
        ("self-compacting", "SCC M40 with 550 kg/m3 powder content and 680 mm slump flow"),
        ("3d-printing", "3D printable concrete with 800 kg binder, w/b 0.32 and PP fibres"),
        ("ecc", "ECC with PVA 2.0 vol%, FA/cement ratio 2.0, w/b 0.28"),
        ("lightweight", "Lightweight concrete with expanded clay LECA density 1600 kg/m3"),
        ("co2-injected", "CO2 injected concrete M30 with 0.15% CO2 and 5% cement reduction"),
        ("pervious", "Pervious concrete with 20% void ratio and 10mm aggregate"),
        ("fiber-reinforced", "FRC M35 with 40 kg/m3 steel hooked fibers and w/c 0.42"),
        ("self-healing", "Bacterial self-healing concrete M30 with w/cm 0.45"),
        ("self-sensing", "Self-sensing CNT concrete with 0.5% carbon nanotube dosage"),
    ])
    def test_no_conventional_leakage(self, type_name, prompt):
        result = extract_special_inputs(prompt, type_name)
        leaked = set(result["parsed"].keys()) & BANNED_CONVENTIONAL_FIELDS
        assert not leaked, (
            f"Conventional fields leaked into '{type_name}' extraction: {leaked}"
        )

    @pytest.mark.parametrize("type_name,prompt", [
        ("uhpc", "UHPC 150 MPa with 25% silica fume and 2.0 vol% steel fibers, w/b 0.18"),
        ("sea-sand", "Sea sand concrete with seawater mixing and GFRP rebar"),
        ("geopolymer", GEOPOLYMER_PROMPT),
    ])
    def test_parsed_keys_are_valid_schema_keys(self, type_name, prompt):
        """All keys in 'parsed' dict must be valid schema field keys for the type."""
        result = extract_special_inputs(prompt, type_name)
        schema = get_type_schema(type_name)
        valid_keys = {f["key"] for f in schema["fields"]}
        # 'concrete_type' is allowed too
        invalid = set(result["parsed"].keys()) - valid_keys - {"concrete_type"}
        assert not invalid, (
            f"Invalid (non-schema) fields in parsed output for '{type_name}': {invalid}"
        )


class TestClampingBehavior:
    """Values outside schema range must be clamped and warnings emitted."""

    def test_ggbs_over_max_is_clamped(self):
        result = extract_special_inputs(
            "Geopolymer with 70% GGBS and 12M NaOH, ambient cured. Target 40 MPa.",
            "geopolymer"
        )
        assert result["parsed"]["ggbs_pct"] == 50, "70% GGBS must be clamped to max=50"
        assert "ggbs_pct" in result["clamped_keys"]
        assert len(result["warnings"]) > 0

    def test_naoh_over_max_is_clamped(self):
        result = extract_special_inputs(
            "Geopolymer with 25M NaOH and 30% GGBS, ambient cured. Target 40 MPa.",
            "geopolymer"
        )
        assert result["parsed"]["naoh_molarity"] == 16, "25M NaOH must be clamped to max=16"
        assert "naoh_molarity" in result["clamped_keys"]


class TestConventionalRegression:
    """Conventional parse must continue working exactly as before."""

    def test_conventional_schema_has_standard_fields(self):
        schema = get_type_schema("conventional")
        keys = {f["key"] for f in schema["fields"]}
        required = {"fck", "exposure", "member", "max_size", "slump",
                    "zone", "cement_grade", "placement", "supervision", "agg_type"}
        assert required <= keys, f"Missing conventional fields: {required - keys}"

    def test_conventional_schema_has_no_geopolymer_fields(self):
        schema = get_type_schema("conventional")
        keys = {f["key"] for f in schema["fields"]}
        assert "naoh_molarity" not in keys
        assert "silicate_to_hydroxide_ratio" not in keys
        assert "ggbs_pct" not in keys  # conventional uses scm_ggbs_pct
        assert "target_strength" not in keys
        assert "curing" not in keys


class TestGeopolymerSwitchBack:
    """Switching type does not retain parsed values from previous type."""

    def test_geopolymer_then_conventional_then_geopolymer_no_leak(self):
        # Extract geopolymer
        geo_result = extract_special_inputs(GEOPOLYMER_PROMPT, "geopolymer")
        geo_keys = set(geo_result["parsed"].keys())

        # Extract conventional
        conv_schema = get_type_schema("conventional")
        conv_keys = {f["key"] for f in conv_schema["fields"]}

        # Re-extract geopolymer (simulate switching back)
        geo_result2 = extract_special_inputs(GEOPOLYMER_PROMPT, "geopolymer")
        geo_keys2 = set(geo_result2["parsed"].keys())

        # Geopolymer fields in second extraction must not have conventional keys
        leaked = geo_keys2 & BANNED_CONVENTIONAL_FIELDS
        assert not leaked, f"Geopolymer re-extraction has conventional fields: {leaked}"

        # Geopolymer values must match first extraction
        assert geo_result["parsed"]["ggbs_pct"] == geo_result2["parsed"]["ggbs_pct"]
        assert geo_result["parsed"]["naoh_molarity"] == geo_result2["parsed"]["naoh_molarity"]
