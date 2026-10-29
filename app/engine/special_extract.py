"""Per-type parameter extractors for special concrete types.

Provides isolated regex and heuristic extraction tailored to each concrete type schema.
Prevents any conventional IS 10262 fields (cement grade, FA zone, placement, supervision,
or conventional standard defaults like M30) from leaking into special concrete types.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from app.engine.type_schemas import TYPE_SCHEMAS, get_type_schema


def _find_number_near(text: str, keywords: List[str], is_float: bool = False) -> Optional[float]:
    """Find a number immediately before or after any of the keywords.
    E.g.: '30% GGBS', 'GGBS 30%', 'GGBS at 30 %', '30 percent slag'.
    """
    pattern_num = r"(\d+(?:\.\d+)?)" if is_float else r"(\d+)"
    for kw in keywords:
        escaped_kw = re.escape(kw)
        # Pattern 1: number before keyword (e.g. 30% GGBS, 30 percent GGBS, 30 GGBS)
        p1 = rf"{pattern_num}\s*(?:%|\s*percent)?\s*(?:of\s+)?{escaped_kw}"
        m1 = re.search(p1, text, re.IGNORECASE)
        if m1:
            return float(m1.group(1)) if is_float else int(m1.group(1))

        # Pattern 2: keyword before number (e.g. GGBS 30%, GGBS at 30%, GGBS: 30%, GGBS is 30%, GGBS replacement of 40%)
        p2 = rf"{escaped_kw}\s*(?:at|is|of|ratio|content|dose|dosage|addition|replacement)?\s*(?:of\s*)?(?::|=|\s)?\s*{pattern_num}\s*(?:%|\s*percent)?"
        m2 = re.search(p2, text, re.IGNORECASE)
        if m2:
            return float(m2.group(1)) if is_float else int(m2.group(1))

    return None


def _extract_strength(text: str) -> Optional[int]:
    """Extract target strength or grade number from text."""
    # Pattern: Target strength 40 MPa, 40 N/mm2, 40MPa
    m = re.search(r"(?:target\s*strength|characteristic\s*strength|strength|fck)\s*(?:of|is|at|:)?\s*(\d{2,3})\s*(?:MPa|N/mm2|n/mm2)?", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    
    # Standalone MPa / N/mm2
    m2 = re.search(r"(\d{2,3})\s*(?:MPa|N/mm2)", text, re.IGNORECASE)
    if m2:
        return int(m2.group(1))

    # M30 / M40 / M150
    m3 = re.search(r"\bM\s*(\d{2,3})\b", text, re.IGNORECASE)
    if m3:
        return int(m3.group(1))

    return None


def _extract_max_size(text: str) -> Optional[float]:
    """Extract max aggregate size (e.g. 20 mm aggregate, 10mm MSA)."""
    m = re.search(r"(\d{1,2}(?:\.\d)?)\s*mm\s*(?:max(?:imum)?\s*(?:aggregate|size)?|nominal|agg|msa)?", text, re.IGNORECASE)
    if m:
        val = float(m.group(1))
        if val in (10, 12, 12.5, 16, 20, 40):
            return 12.5 if val == 12 else (int(val) if val.is_integer() else val)
    return None


def extract_special_inputs(problem_text: str, concrete_type: str) -> Dict[str, Any]:
    """Extract schema parameters specifically for the given special concrete type.

    Guarantees:
    - Only fields present in TYPE_SCHEMAS[concrete_type] are returned.
    - No IS 10262 conventional fields are injected.
    - Values outside schema min/max are clamped and reported in clamped_keys and warnings.
    """
    schema = get_type_schema(concrete_type)
    fields = schema.get("fields", [])
    field_map = {f["key"]: f for f in fields}

    parsed: Dict[str, Any] = {}
    extracted_keys: List[str] = []
    clamped_keys: Dict[str, Any] = {}
    facts: List[Dict[str, Any]] = []
    assumptions: List[Dict[str, Any]] = []
    warnings: List[str] = []

    text = problem_text or ""

    # Common exposure & member extraction if in schema
    if "exposure" in field_map:
        for exp in ["extreme", "very severe", "severe", "moderate", "mild"]:
            if exp in text.lower():
                parsed["exposure"] = exp
                extracted_keys.append("exposure")
                facts.append({"field": "exposure", "value": exp, "source": f"Text specified '{exp}' exposure"})
                break

    if "member" in field_map:
        if re.search(r"\bPCC\b|plain\s*concrete|unreinforced", text, re.IGNORECASE):
            parsed["member"] = "PCC"
            extracted_keys.append("member")
            facts.append({"field": "member", "value": "PCC", "source": "Text specified PCC"})
        elif re.search(r"\bRCC\b|reinforced|beam|column|slab", text, re.IGNORECASE):
            parsed["member"] = "RCC"
            extracted_keys.append("member")
            facts.append({"field": "member", "value": "RCC", "source": "Text specified RCC / structural member"})

    if "max_size" in field_map:
        ms = _extract_max_size(text)
        if ms is not None:
            parsed["max_size"] = ms
            extracted_keys.append("max_size")
            facts.append({"field": "max_size", "value": ms, "source": f"Found {ms} mm max aggregate size"})

    # ─────────────────────────────────────────────────────────────────────────
    # TYPE SPECIFIC EXTRACTION
    # ─────────────────────────────────────────────────────────────────────────
    if concrete_type == "geopolymer":
        # 1. NaOH molarity (e.g. 12M NaOH, 12 M NaOH, 12 molar, NaOH 12M)
        m_molarity = re.search(r"(\d{1,2})\s*M\s*(?:NaOH|molar|sodium\s*hydroxide)?", text, re.IGNORECASE)
        if not m_molarity:
            m_molarity = re.search(r"(?:NaOH|sodium\s*hydroxide)\s*(?:of|is|at|:)?\s*(\d{1,2})\s*M?", text, re.IGNORECASE)
        if m_molarity:
            val = int(m_molarity.group(1))
            parsed["naoh_molarity"] = val
            extracted_keys.append("naoh_molarity")
            facts.append({"field": "naoh_molarity", "value": val, "source": f"Extracted {val}M NaOH"})

        # 2. Na2SiO3 / NaOH ratio (e.g. Na2SiO3/NaOH ratio 2.5, Na2SiO3:NaOH 2.5, silicate to hydroxide ratio 2.5)
        m_ratio = re.search(r"(?:Na2SiO3\s*/\s*NaOH|silicate\s*(?:to|/)\s*(?:hydroxide|NaOH)|alkali\s*ratio|silicate\s*ratio)\s*(?:ratio)?\s*(?:of|is|at|:)?\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if m_ratio:
            val = float(m_ratio.group(1))
            parsed["silicate_to_hydroxide_ratio"] = val
            extracted_keys.append("silicate_to_hydroxide_ratio")
            facts.append({"field": "silicate_to_hydroxide_ratio", "value": val, "source": f"Extracted silicate/hydroxide ratio {val}"})

        # 3. GGBS % (e.g. 30% GGBS, GGBS 30%, 30% slag)
        ggbs_val = _find_number_near(text, ["GGBS", "slag", "GGBFS"], is_float=False)
        if ggbs_val is not None:
            parsed["ggbs_pct"] = int(ggbs_val)
            extracted_keys.append("ggbs_pct")
            facts.append({"field": "ggbs_pct", "value": int(ggbs_val), "source": f"Extracted GGBS content {int(ggbs_val)}%"})
            parsed["binder_system"] = "fly_ash_ggbs"
            extracted_keys.append("binder_system")
        elif re.search(r"fly\s*ash\s*(?:only|alone|100%)", text, re.IGNORECASE):
            parsed["binder_system"] = "fly_ash"
            parsed["ggbs_pct"] = 0
            extracted_keys.append("binder_system")
            extracted_keys.append("ggbs_pct")

        # 4. Alkaline liquid / binder ratio (e.g. alkaline liquid to binder 0.38, AL/B 0.35)
        m_alb = re.search(r"(?:alkaline\s*liquid\s*(?:to\s*binder|\/\s*binder)?|AL\s*/\s*B)\s*(?:ratio)?\s*(?:of|is|at|:)?\s*(0\.\d+)", text, re.IGNORECASE)
        if m_alb:
            val = float(m_alb.group(1))
            parsed["alkaline_liquid_to_binder"] = val
            extracted_keys.append("alkaline_liquid_to_binder")
            facts.append({"field": "alkaline_liquid_to_binder", "value": val, "source": f"Extracted alkaline liquid/binder ratio {val}"})

        # 5. Curing (ambient vs heat/steam 60°C)
        if re.search(r"\bambient\b|room\s*temp(?:erature)?", text, re.IGNORECASE):
            parsed["curing"] = "ambient"
            extracted_keys.append("curing")
            facts.append({"field": "curing", "value": "ambient", "source": "Specified ambient curing"})
        elif re.search(r"heat|oven|steam|60\s*°?C", text, re.IGNORECASE):
            parsed["curing"] = "heat_60c"
            extracted_keys.append("curing")
            facts.append({"field": "curing", "value": "heat_60c", "source": "Specified heat curing (60°C)"})

        # 6. Target strength
        str_val = _extract_strength(text)
        if str_val is not None:
            parsed["target_strength"] = str_val
            extracted_keys.append("target_strength")
            facts.append({"field": "target_strength", "value": str_val, "source": f"Target strength {str_val} MPa"})

    elif concrete_type == "self-healing":
        # Mechanism
        if re.search(r"bacteri(?:a|al)|bacillus|microbial", text, re.IGNORECASE):
            parsed["healing_mechanism"] = "bacterial"
            extracted_keys.append("healing_mechanism")
        elif re.search(r"crystallin", text, re.IGNORECASE):
            parsed["healing_mechanism"] = "crystalline"
            extracted_keys.append("healing_mechanism")
        elif re.search(r"\bsap\b|superabsorbent", text, re.IGNORECASE):
            parsed["healing_mechanism"] = "sap"
            extracted_keys.append("healing_mechanism")
        elif re.search(r"capsule|encapsulat", text, re.IGNORECASE):
            parsed["healing_mechanism"] = "capsule"
            extracted_keys.append("healing_mechanism")
        elif re.search(r"autogenous", text, re.IGNORECASE):
            parsed["healing_mechanism"] = "autogenous"
            extracted_keys.append("healing_mechanism")

        # w/cm
        m_wcm = re.search(r"(?:w/cm|w/c|water\s*[-/]?cementitious)\s*(?:ratio)?\s*(?:of|is|at|:)?\s*(0\.\d+)", text, re.IGNORECASE)
        if m_wcm:
            parsed["w_cm"] = float(m_wcm.group(1))
            extracted_keys.append("w_cm")

        # fly ash %
        fa_val = _find_number_near(text, ["fly ash", "FA", "PFA"])
        if fa_val is not None:
            parsed["fly_ash_pct"] = int(fa_val)
            extracted_keys.append("fly_ash_pct")

        # grade
        str_val = _extract_strength(text)
        if str_val:
            parsed["grade"] = f"M{str_val}"
            extracted_keys.append("grade")

    elif concrete_type == "self-sensing":
        if re.search(r"nanotube|CNT", text, re.IGNORECASE):
            parsed["conductive_filler"] = "carbon_nanotubes"
            extracted_keys.append("conductive_filler")
        elif re.search(r"carbon\s*fib(?:re|er)", text, re.IGNORECASE):
            parsed["conductive_filler"] = "carbon_fiber"
            extracted_keys.append("conductive_filler")
        elif re.search(r"carbon\s*black", text, re.IGNORECASE):
            parsed["conductive_filler"] = "carbon_black"
            extracted_keys.append("conductive_filler")
        elif re.search(r"steel\s*fib(?:re|er)", text, re.IGNORECASE):
            parsed["conductive_filler"] = "steel_fiber"
            extracted_keys.append("conductive_filler")
        elif re.search(r"graphite|graphene", text, re.IGNORECASE):
            parsed["conductive_filler"] = "graphite"
            extracted_keys.append("conductive_filler")

        # dose % bwoc
        dose = _find_number_near(text, ["filler", "dose", "dosage", "bwoc", "cnt", "fiber", "fibre"], is_float=True)
        if dose is not None and dose <= 5.0:
            parsed["filler_dose_pct"] = dose
            extracted_keys.append("filler_dose_pct")

        # w/b
        m_wb = re.search(r"(?:w/b|w/c|water\s*[-/]?binder)\s*(?:ratio)?\s*(?:of|is|at|:)?\s*(0\.\d+)", text, re.IGNORECASE)
        if m_wb:
            parsed["w_b"] = float(m_wb.group(1))
            extracted_keys.append("w_b")

    elif concrete_type == "self-compacting":
        str_val = _extract_strength(text)
        if str_val:
            parsed["grade"] = f"M{str_val}"
            extracted_keys.append("grade")

        if re.search(r"limestone|lsp", text, re.IGNORECASE):
            parsed["filler_type"] = "limestone_powder"
            extracted_keys.append("filler_type")
        elif re.search(r"ggbs|slag", text, re.IGNORECASE):
            parsed["filler_type"] = "ggbs"
            extracted_keys.append("filler_type")
        elif re.search(r"fly\s*ash|fa", text, re.IGNORECASE):
            parsed["filler_type"] = "fly_ash"
            extracted_keys.append("filler_type")

        # powder content
        m_pow = re.search(r"(\d{3})\s*kg(?:/m3)?\s*(?:powder|binder)", text, re.IGNORECASE)
        if m_pow:
            parsed["powder_content"] = int(m_pow.group(1))
            extracted_keys.append("powder_content")

        # slump flow
        m_sf = re.search(r"(\d{3})\s*mm\s*(?:slump\s*flow|flow)", text, re.IGNORECASE)
        if not m_sf:
            m_sf = re.search(r"slump\s*flow\s*(?:of|is|at|:)?\s*(\d{3})", text, re.IGNORECASE)
        if m_sf:
            parsed["slump_flow"] = int(m_sf.group(1))
            extracted_keys.append("slump_flow")

    elif concrete_type == "3d-printing":
        if re.search(r"metakaolin", text, re.IGNORECASE):
            parsed["binder_system"] = "opc_fa_metakaolin"
            extracted_keys.append("binder_system")
        elif re.search(r"ggbs|slag", text, re.IGNORECASE):
            parsed["binder_system"] = "opc_ggbs"
            extracted_keys.append("binder_system")

        # binder content
        m_bind = re.search(r"(\d{3})\s*kg(?:/m3)?\s*binder", text, re.IGNORECASE)
        if m_bind:
            parsed["binder_content"] = int(m_bind.group(1))
            extracted_keys.append("binder_content")

        # sand to binder
        m_sb = re.search(r"sand\s*(?::|to|\/)\s*binder\s*(?:ratio)?\s*(?:of|is|at|:)?\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if m_sb:
            parsed["sand_to_binder_ratio"] = float(m_sb.group(1))
            extracted_keys.append("sand_to_binder_ratio")

        # w/b
        m_wb = re.search(r"(?:w/b|w/c)\s*(?:ratio)?\s*(?:of|is|at|:)?\s*(0\.\d+)", text, re.IGNORECASE)
        if m_wb:
            parsed["w_b"] = float(m_wb.group(1))
            extracted_keys.append("w_b")

        if re.search(r"no\s*fib|without\s*fib", text, re.IGNORECASE):
            parsed["pp_fiber"] = False
            extracted_keys.append("pp_fiber")
        elif re.search(r"pp\s*fib|polypropylene\s*fib|fibre|fiber", text, re.IGNORECASE):
            parsed["pp_fiber"] = True
            extracted_keys.append("pp_fiber")

    elif concrete_type == "uhpc":
        str_val = _extract_strength(text)
        if str_val and str_val >= 90:
            parsed["target_strength"] = str_val
            extracted_keys.append("target_strength")
        
        # cement content
        m_cem = re.search(r"(\d{3})\s*kg(?:/m3)?\s*cement", text, re.IGNORECASE)
        if m_cem:
            parsed["cement_content"] = int(m_cem.group(1))
            extracted_keys.append("cement_content")

        # silica fume %
        sf_val = _find_number_near(text, ["silica fume", "SF", "microsilica"])
        if sf_val is not None:
            parsed["silica_fume_pct"] = int(sf_val)
            extracted_keys.append("silica_fume_pct")

        # w/b
        m_wb = re.search(r"(?:w/b|w/c)\s*(?:ratio)?\s*(?:of|is|at|:)?\s*(0\.\d+)", text, re.IGNORECASE)
        if m_wb:
            parsed["w_b"] = float(m_wb.group(1))
            extracted_keys.append("w_b")

        # steel fibre vol %
        m_fib = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:vol(?:ume)?)?\s*(?:steel\s*)?fib(?:re|er)", text, re.IGNORECASE)
        if m_fib:
            parsed["steel_fiber_vol_pct"] = float(m_fib.group(1))
            extracted_keys.append("steel_fiber_vol_pct")

        # curing
        if re.search(r"steam|90\s*°?C|heat", text, re.IGNORECASE):
            parsed["curing"] = "steam_90c"
            extracted_keys.append("curing")
        elif re.search(r"standard|water|28\s*day|normal", text, re.IGNORECASE):
            parsed["curing"] = "standard"
            extracted_keys.append("curing")

    elif concrete_type == "ecc":
        # FA / cement ratio
        m_fac = re.search(r"(?:FA|fly\s*ash)\s*(?:\/|to|:)\s*cement\s*(?:ratio)?\s*(?:of|is|at|:)?\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if m_fac:
            parsed["fa_to_cement_ratio"] = float(m_fac.group(1))
            extracted_keys.append("fa_to_cement_ratio")

        # w/b
        m_wb = re.search(r"(?:w/b|w/c)\s*(?:ratio)?\s*(?:of|is|at|:)?\s*(0\.\d+)", text, re.IGNORECASE)
        if m_wb:
            parsed["w_b"] = float(m_wb.group(1))
            extracted_keys.append("w_b")

        # fiber type
        if re.search(r"\bpva\b", text, re.IGNORECASE):
            parsed["fiber_type"] = "pva"
            extracted_keys.append("fiber_type")
        elif re.search(r"\bpe\b|polyethylene", text, re.IGNORECASE):
            parsed["fiber_type"] = "pe"
            extracted_keys.append("fiber_type")
        elif re.search(r"\bpp\b|polypropylene", text, re.IGNORECASE):
            parsed["fiber_type"] = "pp"
            extracted_keys.append("fiber_type")

        # fiber vol %
        fib_val = _find_number_near(text, ["fiber", "fibre", "vol", "pva", "pe"], is_float=True)
        if fib_val is not None and fib_val <= 5.0:
            parsed["fiber_vol_pct"] = fib_val
            extracted_keys.append("fiber_vol_pct")

    elif concrete_type == "lightweight":
        if re.search(r"foam|foamed|cellular", text, re.IGNORECASE):
            parsed["variant"] = "foamed"
            extracted_keys.append("variant")
        elif re.search(r"structural|lwa", text, re.IGNORECASE):
            parsed["variant"] = "lwa_structural"
            extracted_keys.append("variant")

        # LWA type
        if re.search(r"pumice", text, re.IGNORECASE):
            parsed["lwa_type"] = "pumice"
            extracted_keys.append("lwa_type")
        elif re.search(r"sintered", text, re.IGNORECASE):
            parsed["lwa_type"] = "sintered_fa"
            extracted_keys.append("lwa_type")
        elif re.search(r"shale", text, re.IGNORECASE):
            parsed["lwa_type"] = "expanded_shale"
            extracted_keys.append("lwa_type")
        elif re.search(r"oil\s*palm", text, re.IGNORECASE):
            parsed["lwa_type"] = "oil_palm_shell"
            extracted_keys.append("lwa_type")
        elif re.search(r"clay|expanded\s*clay", text, re.IGNORECASE):
            parsed["lwa_type"] = "expanded_clay"
            extracted_keys.append("lwa_type")

        # target density
        m_dens = re.search(r"(\d{3,4})\s*kg/m3\s*(?:density)?", text, re.IGNORECASE)
        if not m_dens:
            m_dens = re.search(r"density\s*(?:of|is|at|:)?\s*(\d{3,4})", text, re.IGNORECASE)
        if m_dens:
            parsed["target_density"] = int(m_dens.group(1))
            extracted_keys.append("target_density")

        m_wc = re.search(r"(?:w/c|w/b)\s*(?:ratio)?\s*(?:of|is|at|:)?\s*(0\.\d+)", text, re.IGNORECASE)
        if m_wc:
            parsed["w_c"] = float(m_wc.group(1))
            extracted_keys.append("w_c")

    elif concrete_type == "co2-injected":
        str_val = _extract_strength(text)
        if str_val:
            parsed["grade"] = f"M{str_val}"
            extracted_keys.append("grade")

        co2_val = _find_number_near(text, ["CO2", "carbon dioxide"], is_float=True)
        if co2_val is not None:
            parsed["co2_dose_pct"] = co2_val
            extracted_keys.append("co2_dose_pct")

        m_red = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:cement\s*reduc|reduction)", text, re.IGNORECASE)
        if m_red:
            parsed["cement_reduction_pct"] = float(m_red.group(1))
            extracted_keys.append("cement_reduction_pct")

        fa_val = _find_number_near(text, ["fly ash", "FA"])
        if fa_val is not None:
            parsed["fly_ash_pct"] = int(fa_val)
            extracted_keys.append("fly_ash_pct")

    elif concrete_type == "sea-sand":
        str_val = _extract_strength(text)
        if str_val:
            parsed["grade"] = f"M{str_val}"
            extracted_keys.append("grade")

        cl_val = _find_number_near(text, ["chloride", "cl-", "cl"], is_float=True)
        if cl_val is not None:
            parsed["chloride_pct"] = cl_val
            extracted_keys.append("chloride_pct")

        if re.search(r"seawater", text, re.IGNORECASE):
            parsed["mixing_water"] = "seawater"
            extracted_keys.append("mixing_water")
        elif re.search(r"fresh|freshwater|tap\s*water", text, re.IGNORECASE):
            parsed["mixing_water"] = "freshwater"
            extracted_keys.append("mixing_water")

        # SCM
        if re.search(r"ggbs|slag", text, re.IGNORECASE):
            parsed["scm_type"] = "ggbs_40"
            extracted_keys.append("scm_type")
        elif re.search(r"silica\s*fume|sf", text, re.IGNORECASE):
            parsed["scm_type"] = "sf8_fa20"
            extracted_keys.append("scm_type")
        elif re.search(r"fly\s*ash|fa", text, re.IGNORECASE):
            parsed["scm_type"] = "fly_ash_25"
            extracted_keys.append("scm_type")
        elif re.search(r"no\s*scm|without\s*scm|none", text, re.IGNORECASE):
            parsed["scm_type"] = "none"
            extracted_keys.append("scm_type")

        # Rebar
        if re.search(r"frp|gfrp|bfrp", text, re.IGNORECASE):
            parsed["rebar_type"] = "frp"
            extracted_keys.append("rebar_type")
        elif re.search(r"stainless", text, re.IGNORECASE):
            parsed["rebar_type"] = "stainless_steel"
            extracted_keys.append("rebar_type")
        elif re.search(r"epoxy", text, re.IGNORECASE):
            parsed["rebar_type"] = "epoxy_coated"
            extracted_keys.append("rebar_type")
        elif re.search(r"plain|black|carbon\s*steel", text, re.IGNORECASE):
            parsed["rebar_type"] = "plain_steel"
            extracted_keys.append("rebar_type")

    elif concrete_type == "pervious":
        void_val = _find_number_near(text, ["void", "voids", "porosity"], is_float=True)
        if void_val is not None:
            parsed["design_void_pct"] = void_val
            extracted_keys.append("design_void_pct")

        m_wc = re.search(r"(?:w/c|water\s*[-/]?cement)\s*(?:ratio)?\s*(?:of|is|at|:)?\s*(0\.\d+)", text, re.IGNORECASE)
        if m_wc:
            parsed["w_c"] = float(m_wc.group(1))
            extracted_keys.append("w_c")

        fa_val = _find_number_near(text, ["sand", "fine aggregate"])
        if fa_val is not None:
            parsed["fine_aggregate_pct"] = int(fa_val)
            extracted_keys.append("fine_aggregate_pct")

    elif concrete_type == "fiber-reinforced":
        if re.search(r"hooked", text, re.IGNORECASE):
            parsed["fiber_type"] = "steel_hooked"
            extracted_keys.append("fiber_type")
        elif re.search(r"crimped", text, re.IGNORECASE):
            parsed["fiber_type"] = "steel_crimped"
            extracted_keys.append("fiber_type")
        elif re.search(r"macro\s*pp|macro\s*poly", text, re.IGNORECASE):
            parsed["fiber_type"] = "pp_macro"
            extracted_keys.append("fiber_type")
        elif re.search(r"micro\s*pp|micro\s*poly", text, re.IGNORECASE):
            parsed["fiber_type"] = "pp_micro"
            extracted_keys.append("fiber_type")
        elif re.search(r"glass|ar-glass", text, re.IGNORECASE):
            parsed["fiber_type"] = "glass_ar"
            extracted_keys.append("fiber_type")
        elif re.search(r"basalt", text, re.IGNORECASE):
            parsed["fiber_type"] = "basalt"
            extracted_keys.append("fiber_type")
        elif re.search(r"hybrid", text, re.IGNORECASE):
            parsed["fiber_type"] = "hybrid"
            extracted_keys.append("fiber_type")

        # fiber dose kg/m3
        m_dose = re.search(r"(\d+(?:\.\d+)?)\s*kg(?:/m3)?\s*(?:fib(?:re|er))?", text, re.IGNORECASE)
        if not m_dose:
            m_dose = re.search(r"(?:dose|dosage|addition)\s*(?:of|is|at|:)?\s*(\d+(?:\.\d+)?)\s*kg", text, re.IGNORECASE)
        if m_dose:
            parsed["fiber_dose"] = float(m_dose.group(1))
            extracted_keys.append("fiber_dose")

        str_val = _extract_strength(text)
        if str_val:
            parsed["grade"] = f"M{str_val}"
            extracted_keys.append("grade")

        m_wc = re.search(r"(?:w/c|w/b)\s*(?:ratio)?\s*(?:of|is|at|:)?\s*(0\.\d+)", text, re.IGNORECASE)
        if m_wc:
            parsed["w_c"] = float(m_wc.group(1))
            extracted_keys.append("w_c")

    # ─────────────────────────────────────────────────────────────────────────
    # ENFORCE SCHEMA BOUNDARIES & DEFAULT POPULATION (CLAMP & WARN)
    # ─────────────────────────────────────────────────────────────────────────
    for f in fields:
        k = f["key"]
        min_v = f.get("min")
        max_v = f.get("max")
        default_v = f.get("default")

        if k in parsed:
            val = parsed[k]
            # Check numerical bounds
            if isinstance(val, (int, float)) and min_v is not None and max_v is not None:
                if val < min_v:
                    clamped_keys[k] = {"original": val, "clamped": min_v, "min": min_v, "max": max_v, "label": f["label"]}
                    warnings.append(f"{f['label']} ({val}) is below valid range [{min_v}, {max_v}]; clamped to {min_v}.")
                    parsed[k] = min_v
                elif val > max_v:
                    clamped_keys[k] = {"original": val, "clamped": max_v, "min": min_v, "max": max_v, "label": f["label"]}
                    warnings.append(f"{f['label']} ({val}) exceeds valid range [{min_v}, {max_v}]; clamped to {max_v}.")
                    parsed[k] = max_v
        else:
            # Set default from schema
            parsed[k] = default_v
            assumptions.append({"field": k, "value": default_v, "reason": f"Default recommended parameter from {concrete_type} literature benchmark"})

    return {
        "concrete_type": concrete_type,
        "parsed": parsed,
        "extracted_keys": extracted_keys,
        "clamped_keys": clamped_keys,
        "facts": facts,
        "assumptions": assumptions,
        "warnings": warnings,
    }
