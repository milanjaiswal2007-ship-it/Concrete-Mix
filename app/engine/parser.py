"""Natural-language problem statement parser for concrete mix design.

Extracts structured parameters from free-form text using domain-aware
regex, civil engineering synonym dictionaries, and IS Code clause citations.
Zero external LLM is required — completely deterministic, transparent, and robust.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


# ── Numbers & Basic Units ───────────────────────────────────────────────────
_NUM = r"[\d]+(?:\.[\d]+)?"

_GRADE_RE = re.compile(r"\bM\s*(\d{2,3})\b", re.I)

# High strength / standard / lean concrete heuristics
_HIGH_STRENGTH_RE = re.compile(
    r"\b(high\s*strength(?:\s*concrete)?|hsc|very\s*high\s*strength|high\s*grade)\b", re.I
)
_ULTRA_HIGH_STRENGTH_RE = re.compile(
    r"\b(ultra\s*high\s*strength|uhpc|m70|m80)\b", re.I
)
_MEDIUM_STRENGTH_RE = re.compile(
    r"\b(standard\s*concrete|medium\s*strength|commercial\s*building|multi[\s-]story|residential\s*frame)\b", re.I
)
_LEAN_CONCRETE_RE = re.compile(
    r"\b(lean\s*concrete|pcc\s*bedding|mass\s*pcc|mud\s*mat|blinding\s*layer)\b", re.I
)

# ── Exposure Condition Keywords (Engineering Mappings) ──────────────────────
# Extreme exposure keywords
_EXTREME_RE = re.compile(
    r"\b(extreme|tidal\s*zone|marine\s*tidal|sea\s*wall|offshore|wave\s*action|submerged\s*in\s*sea\s*water|splash\s*zone)\b",
    re.I,
)
# Very Severe exposure keywords
_VERY_SEVERE_RE = re.compile(
    r"\b(very\s*severe|sea\s*water\s*spray|jetty|marine\s*atmosphere|corrosive\s*fumes|sulphate|sulfate|de[\s-]icing\s*salts|effluent|sewage\s*tank)\b",
    re.I,
)
# Severe exposure keywords (Coastal region defaults to Severe per IS 456 Table 3)
_SEVERE_RE = re.compile(
    r"\b(severe|coastal|marine|sea\s*shore|salt\s*spray|alternate\s*wetting\s*and\s*drying|heavy\s*rain|under\s*sea\s*water|underwater|immersed\s*in\s*sea\s*water|corrosive)\b",
    re.I,
)
# Moderate exposure keywords
_MODERATE_RE = re.compile(
    r"\b(moderate|sheltered\s*from\s*severe\s*rain|buried|subsoil|in\s*ground|foundation|non[\s-]aggressive\s*soil|saturated\s*steam|industrial\s*atmosphere|freezing|cold\s*weather)\b",
    re.I,
)
# Mild exposure keywords
_MILD_RE = re.compile(
    r"\b(mild|internal|interior|indoor|dry\s*environment|office|living\s*room|inside\s*building|enclosed)\b",
    re.I,
)

# ── Member / Structure Types ────────────────────────────────────────────────
_PCC_RE = re.compile(
    r"\b(pcc|plain\s*concrete|unreinforced|gravity\s*dam|bedding|leveling\s*course|mud\s*mat)\b",
    re.I,
)
_RCC_RE = re.compile(
    r"\b(rcc|reinforced|column|beam|slab|footing|retaining\s*wall|raft|pile|pier|girder)\b",
    re.I,
)

# ── Aggregate Maximum Nominal Size ──────────────────────────────────────────
_SIZE_EXPLICIT_RE = re.compile(
    rf"\b({_NUM})\s*mm\s*(?:nominal|maximum|max|aggregate|agg|coarse\s*aggregate|ca|metal|gravel|stone)",
    re.I,
)
_SIZE_EXPLICIT_RE2 = re.compile(
    rf"(?:nominal|maximum|max)\s*(?:aggregate\s*)?size\s*(?:is|of|=|:)?\s*({_NUM})\s*mm",
    re.I,
)
_SIZE_10MM_HEURISTIC_RE = re.compile(
    r"\b(10\s*mm|congested|thin\s*section|precast|scc|self[\s-]compacting|dense\s*reinforcement)\b",
    re.I,
)
_SIZE_40MM_HEURISTIC_RE = re.compile(
    r"\b(40\s*mm|mass\s*concrete|dam|thick\s*raft|large\s*footing|mass\s*pour)\b",
    re.I,
)

# ── Workability / Slump ─────────────────────────────────────────────────────
_SLUMP_EXPLICIT_RE = re.compile(rf"slump\s*(?:of|is|=|:)?\s*({_NUM})\s*mm", re.I)
_SLUMP_FLOW_RE = re.compile(r"slump\s*flow\s*(?:of|is|=|:)?\s*(\d{3})", re.I)

# Workability semantic keywords
_VERY_HIGH_WORKABILITY_RE = re.compile(
    r"\b(self[\s-]compacting|scc|tremie|underwater\s*concrete|flowable|very\s*high\s*workability)\b",
    re.I,
)
_PUMPED_WORKABILITY_RE = re.compile(
    r"\b(pump(?:ed|able|ing)|pipe\s*line|high[\s-]rise\s*pumping|congested\s*joint)\b",
    re.I,
)
_MODERATE_WORKABILITY_RE = re.compile(
    r"\b(normal\s*placing|slab|beam|column|manually\s*placed|lightly\s*reinforced)\b",
    re.I,
)
_LOW_WORKABILITY_RE = re.compile(
    r"\b(pavement|mass\s*concrete|roller\s*compacted|vibrated|low\s*slump|stiff)\b",
    re.I,
)

# ── Fine Aggregate Grading Zones ────────────────────────────────────────────
_ZONE_EXPLICIT_RE = re.compile(
    r"(?:grading\s*)?zone\s*[:=\s-]*(IV|III|II|I|4|3|2|1)\b", re.I
)
_ZONE_COARSE_SAND_RE = re.compile(r"\b(coarse\s*sand|crushed\s*stone\s*sand|quarry\s*sand)\b", re.I)
_ZONE_FINE_SAND_RE = re.compile(r"\b(very\s*fine\s*sand|sea\s*sand|pit\s*sand|silt)\b", re.I)

_ZONE_MAP = {"1": "I", "2": "II", "3": "III", "4": "IV"}

# ── Cement Grade & Type ─────────────────────────────────────────────────────
_PPC_RE = re.compile(r"\b(?:ppc|portland\s*pozzolana\s*cement)\b", re.I)
_PSC_RE = re.compile(r"\b(?:psc|portland\s*slag\s*cement)\b", re.I)
_CEMENT_GRADE_RE = re.compile(r"\b(?:OPC\s*)?(\d{2})\s*grade", re.I)
_OPC_53_HINT_RE = re.compile(r"\b(53|opc\s*53|high\s*early\s*strength|fast\s*track|rapid\s*hardening)\b", re.I)
_OPC_33_HINT_RE = re.compile(r"\b(33|opc\s*33|low\s*strength|low\s*heat)\b", re.I)

# ── Placement & Supervision & Aggregate Shape ──────────────────────────────
_TREMIE_RE = re.compile(r"\b(tremie|underwater\s*concreting|bored\s*cast\s*in\s*situ|diaphragm\s*wall)\b", re.I)
_CHUTE_RE = re.compile(r"\b(chute|manual\s*placing|crane\s*and\s*bucket|skip)\b", re.I)

_SUPERVISION_VERY_GOOD_RE = re.compile(r"\b(very\s*good\s*(?:supervision|control)|excellent\s*(?:control|qa)|precast\s*plant|rmc\s*plant|computerised\s*batching)\b", re.I)
_SUPERVISION_FAIR_RE = re.compile(r"\b(fair\s*(?:supervision|control)|site\s*mixing|manual\s*batching|ordinary\s*control)\b", re.I)
_SUPERVISION_GOOD_RE = re.compile(r"\b(good\s*(?:supervision|control)|standard\s*control|well[\s-]controlled)\b", re.I)

_AGG_SUB_ANGULAR_RE = re.compile(r"\b(sub[\s-]angular)\b", re.I)
_AGG_GRAVEL_CRUSHED_RE = re.compile(r"\b(gravel\s*with\s*crushed|crushed\s*gravel)\b", re.I)
_AGG_ROUNDED_RE = re.compile(r"\b(rounded\s*gravel|river\s*gravel|rounded\s*aggregate|un-?crushed\s*gravel)\b", re.I)
_AGG_ANGULAR_RE = re.compile(r"\b(angular|crushed\s*angular|crushed\s*stone|crushed\s*rock|quarry\s*metal|basalt|granite)\b", re.I)

# ── Specific Gravities & Physical Properties ────────────────────────────────
_SG_CEMENT_RE = re.compile(rf"(?:SG|specific\s*gravity)\s*(?:of\s*)?(?:cement)\s*(?:is|=|:)?\s*({_NUM})", re.I)
_SG_FA_RE = re.compile(rf"(?:SG|specific\s*gravity)\s*(?:of\s*)?(?:fine\s*aggregate|FA|sand)\s*(?:is|=|:)?\s*({_NUM})", re.I)
_SG_CA_RE = re.compile(rf"(?:SG|specific\s*gravity)\s*(?:of\s*)?(?:coarse\s*aggregate|CA)\s*(?:is|=|:)?\s*({_NUM})", re.I)
_SG_FA_SCM_RE = re.compile(rf"(?:SG|specific\s*gravity)\s*(?:of\s*)?(?:fly\s*ash|pfa)\s*(?:is|=|:)?\s*({_NUM})", re.I)
_SG_GGBS_RE = re.compile(rf"(?:SG|specific\s*gravity)\s*(?:of\s*)?(?:GGBS|slag)\s*(?:is|=|:)?\s*({_NUM})", re.I)
_SG_SF_RE = re.compile(rf"(?:SG|specific\s*gravity)\s*(?:of\s*)?(?:silica\s*fume|SF|micro\s*silica)\s*(?:is|=|:)?\s*({_NUM})", re.I)
_SG_SP_RE = re.compile(rf"(?:SG|specific\s*gravity)\s*(?:of\s*)?(?:chemical\s*admixture|admixture|superplasticis[ez]r|SP)\s*(?:is|=|:)?\s*({_NUM})", re.I)

_ABS_FA_RE = re.compile(rf"(?:water\s*)?absorption\s*(?:of\s*)?(?:fine\s*aggregate|FA|sand)\s*(?:is|=|:)?\s*({_NUM})\s*%", re.I)
_ABS_CA_RE = re.compile(rf"(?:water\s*)?absorption\s*(?:of\s*)?(?:coarse\s*aggregate|CA)\s*(?:is|=|:)?\s*({_NUM})\s*%", re.I)
_FM_FA_RE = re.compile(rf"(?:free\s*)?(?:surface\s*)?moisture\s*(?:of|in)?\s*(?:fine\s*aggregate|FA|sand)\s*(?:is|=|:)?\s*({_NUM})\s*%", re.I)
_FM_CA_RE = re.compile(rf"(?:free\s*)?(?:surface\s*)?moisture\s*(?:of|in)?\s*(?:coarse\s*aggregate|CA)\s*(?:is|=|:)?\s*({_NUM})\s*%", re.I)

# ── SCMs & Admixtures ───────────────────────────────────────────────────────
_FA_RE = re.compile(rf"(?:fly\s*ash|pfa)\s*(?:at|of|@|=|:)?\s*({_NUM})\s*%", re.I)
_FA_MENTION = re.compile(r"\b(fly\s*ash|pulverised\s*fuel\s*ash|pfa)\b", re.I)

_GGBS_RE = re.compile(rf"(?:GGBS|slag|ground\s*granulated)\s*(?:at|of|@|=|:)?\s*({_NUM})\s*%", re.I)
_GGBS_MENTION = re.compile(r"\b(ggbs|slag|ground\s*granulated\s*blast\s*furnace\s*slag)\b", re.I)

_SF_RE = re.compile(rf"(?:silica\s*fume|SF|micro\s*silica)\s*(?:at|of|@|=|:)?\s*({_NUM})\s*%", re.I)
_SF_MENTION = re.compile(r"\b(silica\s*fume|micro\s*silica|sf)\b", re.I)

_SP_PCT_RE = re.compile(rf"(?:super\s*plasticis[ez]r?|SP|admixture|plasticizer)\s*(?:at|of|@|=|:)?\s*({_NUM})\s*%", re.I)
_SP_WR_RE = re.compile(rf"({_NUM})\s*%\s*water\s*reduction", re.I)
_SP_MENTION = re.compile(r"\b(super\s*plasticis[ez]r|admixture|chemical\s*admixture|plasticizer|retarder)\b", re.I)


def parse_problem(text: str) -> Dict[str, Any]:
    """Parse a natural-language problem statement into structured inputs.

    Outputs explicit, clause-referenced engineering justifications for why
    every parameter was chosen or inferred.
    """
    if not text:
        text = ""

    parsed: Dict[str, Any] = {}
    facts: List[Tuple[str, Any, str]] = []
    assumptions: List[Tuple[str, Any, str]] = []
    missing: List[Tuple[str, str]] = []
    warnings: List[str] = []

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Concrete Grade (fck)
    # ─────────────────────────────────────────────────────────────────────────
    m = _GRADE_RE.search(text)
    if m:
        parsed["fck"] = int(m.group(1))
        facts.append(("fck", parsed["fck"], f"Grade '{m.group()}' explicitly stated by user"))
    elif _ULTRA_HIGH_STRENGTH_RE.search(text):
        parsed["fck"] = 70
        assumptions.append(("fck", 70, "IS 10262:2019 Table 2 & Annex E defines Ultra-High Strength Concrete as >= M65. Adopted M70 standard benchmark."))
    elif _HIGH_STRENGTH_RE.search(text):
        parsed["fck"] = 60
        assumptions.append(("fck", 60, "IS 456:2000 Clause 6.1 categorises M60-M80 as 'High Strength Concrete (HSC)'. Standard M60 adopted."))
    elif _LEAN_CONCRETE_RE.search(text):
        parsed["fck"] = 15
        assumptions.append(("fck", 15, "IS 456:2000 Table 5 allows M15 minimum grade for unreinforced plain concrete (PCC) bedding/mud mats."))
    else:
        parsed["fck"] = 30
        assumptions.append(("fck", 30, "IS 456:2000 Clause 6.1 standard structural concrete for general RCC frames and columns defaults to M30."))

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Exposure Condition (IS 456 Table 3 & 5)
    # ─────────────────────────────────────────────────────────────────────────
    if _EXTREME_RE.search(text):
        parsed["exposure"] = "extreme"
        facts.append(("exposure", "extreme", "IS 456:2000 Table 3 (Clause 8.2.2.1): Members in tidal zone / sea water splash zone classified as 'Extreme'."))
    elif _VERY_SEVERE_RE.search(text):
        parsed["exposure"] = "very severe"
        facts.append(("exposure", "very severe", "IS 456:2000 Table 3: Concrete surface exposed to sea water spray, corrosive fumes or de-icing salts classified as 'Very Severe'."))
    elif _SEVERE_RE.search(text):
        parsed["exposure"] = "severe"
        facts.append(("exposure", "severe", "IS 456:2000 Table 3: Concrete exposed to coastal environment, alternate wetting & drying, or sea water immersion classified as 'Severe'."))
    elif _MODERATE_RE.search(text):
        parsed["exposure"] = "moderate"
        facts.append(("exposure", "moderate", "IS 456:2000 Table 3: Concrete sheltered from severe rain or buried in non-aggressive soil classified as 'Moderate'."))
    elif _MILD_RE.search(text):
        parsed["exposure"] = "mild"
        facts.append(("exposure", "mild", "IS 456:2000 Table 3: Concrete surfaces completely sheltered against weather or aggressive conditions classified as 'Mild'."))
    else:
        parsed["exposure"] = "moderate"
        assumptions.append(("exposure", "moderate", "IS 456:2000 Table 3: Default baseline exposure for general outdoor foundations and sheltered structural frames is 'Moderate'."))

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Structural Member Type
    # ─────────────────────────────────────────────────────────────────────────
    if _PCC_RE.search(text) and not _RCC_RE.search(text):
        parsed["member"] = "PCC"
        facts.append(("member", "PCC", "IS 456:2000 Table 5: Governed by Plain Concrete (PCC) minimum cement and w/c limits."))
    else:
        parsed["member"] = "RCC"
        if _RCC_RE.search(text):
            facts.append(("member", "RCC", "IS 456:2000 Table 5: Governed by Reinforced Concrete (RCC) minimum binder and maximum w/c limits."))
        else:
            assumptions.append(("member", "RCC", "IS 456:2000 Clause 26: Standard civil structures are designed with reinforced steel; assumed RCC."))

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Maximum Nominal Aggregate Size
    # ─────────────────────────────────────────────────────────────────────────
    m = _SIZE_EXPLICIT_RE.search(text) or _SIZE_EXPLICIT_RE2.search(text)
    if m:
        sz = int(float(m.group(1)))
        parsed["max_size"] = sz
        facts.append(("max_size", sz, f"Explicit nominal aggregate size of {sz} mm specified by user."))
    elif _SIZE_40MM_HEURISTIC_RE.search(text):
        parsed["max_size"] = 40
        assumptions.append(("max_size", 40, "IS 456:2000 Clause 5.3.3: 40 mm nominal aggregate recommended for mass concrete blocks and thick rafts to reduce heat of hydration."))
    elif _SIZE_10MM_HEURISTIC_RE.search(text):
        parsed["max_size"] = 10
        assumptions.append(("max_size", 10, "IS 456:2000 Clause 5.3.3: 10 mm aggregate recommended for congested reinforcement and self-compacting concrete to avoid honeycombing."))
    else:
        parsed["max_size"] = 20
        assumptions.append(("max_size", 20, "IS 456:2000 Clause 5.3.3 & IS 10262 Table 3: 20 mm is the standard nominal maximum aggregate size for general RCC works."))

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Workability / Target Slump
    # ─────────────────────────────────────────────────────────────────────────
    m = _SLUMP_EXPLICIT_RE.search(text)
    if m:
        parsed["slump"] = int(float(m.group(1)))
        facts.append(("slump", parsed["slump"], f"Workability requirement: {parsed['slump']} mm slump explicitly specified."))
    elif _VERY_HIGH_WORKABILITY_RE.search(text):
        parsed["slump"] = 175
        assumptions.append(("slump", 175, "IS 456:2000 Clause 7.1: Flowing/self-compacting concrete requires high workability slump of 150-180 mm."))
    elif _PUMPED_WORKABILITY_RE.search(text):
        parsed["slump"] = 125
        assumptions.append(("slump", 125, "IS 10262:2019 Clause 5.3 & IS 456 Clause 7.1: Pumped concrete through boom/pipeline typically requires 100-125 mm slump."))
    elif _LOW_WORKABILITY_RE.search(text):
        parsed["slump"] = 50
        assumptions.append(("slump", 50, "IS 456:2000 Clause 7.1 Table 6: Mass concrete and vibrated pavements specify low workability slump of 25-50 mm."))
    else:
        parsed["slump"] = 100
        assumptions.append(("slump", 100, "IS 456:2000 Clause 7.1: Normal beams, columns, and slabs with pump/crane placing standardise on 75-100 mm slump."))

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Placement Method & Pumping Check
    # ─────────────────────────────────────────────────────────────────────────
    if _TREMIE_RE.search(text):
        parsed["placement"] = "tremie"
        parsed["pumped"] = False
        facts.append(("placement", "tremie", "IS 456:2000 Clause 14.2 & Table 5: Underwater tremie placement requires flowable concrete (slump 150-200mm) and min binder 350 kg/m³."))
    elif _PUMPED_WORKABILITY_RE.search(text):
        parsed["placement"] = "pump"
        parsed["pumped"] = True
        facts.append(("placement", "pump", "IS 10262:2019 Clause 5.5.1: Pumping method mandates 10% coarse aggregate volume reduction for pipe lubrication."))
    else:
        parsed["placement"] = "chute"
        parsed["pumped"] = False
        assumptions.append(("placement", "chute", "IS 456:2000: Default placement method is crane/skip/chute pouring."))

    # ─────────────────────────────────────────────────────────────────────────
    # 6b. Degree of Supervision / Site Quality Control (IS 10262 Table 2)
    # ─────────────────────────────────────────────────────────────────────────
    if _SUPERVISION_VERY_GOOD_RE.search(text):
        parsed["supervision"] = "very_good"
        facts.append(("supervision", "very_good", "IS 10262:2019 Table 2: Precast/RMC certified computerised control reduces standard deviation s by 0.5 N/mm²."))
    elif _SUPERVISION_FAIR_RE.search(text):
        parsed["supervision"] = "fair"
        facts.append(("supervision", "fair", "IS 456:2000 Table 8 footnote: Ordinary site batching/fair control increases standard deviation s by 1.0 N/mm²."))
    else:
        parsed["supervision"] = "good"
        assumptions.append(("supervision", "good", "IS 10262:2019 Table 2: Assumes 'Good' supervision standard batching with tested aggregates."))

    # ─────────────────────────────────────────────────────────────────────────
    # 6c. Aggregate Shape & Petrography (IS 10262 Table 3 & 5)
    # ─────────────────────────────────────────────────────────────────────────
    if _AGG_ROUNDED_RE.search(text):
        parsed["agg_type"] = "rounded"
        facts.append(("agg_type", "rounded", "IS 10262:2019 Table 3 Note 1 & Table 5: Rounded gravel reduces water demand by 20 kg/m³ and increases CA volume by +0.02."))
    elif _AGG_GRAVEL_CRUSHED_RE.search(text):
        parsed["agg_type"] = "gravel_crushed"
        facts.append(("agg_type", "gravel_crushed", "IS 10262:2019 Table 3 Note 1: Gravel with crushed particles reduces water demand by 15 kg/m³."))
    elif _AGG_SUB_ANGULAR_RE.search(text):
        parsed["agg_type"] = "sub_angular"
        facts.append(("agg_type", "sub_angular", "IS 10262:2019 Table 3 Note 1: Sub-angular aggregate reduces water demand by 10 kg/m³."))
    else:
        parsed["agg_type"] = "angular"
        assumptions.append(("agg_type", "angular", "IS 10262:2019 Table 3: Standard baseline assumes crushed angular coarse aggregate (quarry metal)."))

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Fine Aggregate Grading Zone
    # ─────────────────────────────────────────────────────────────────────────
    m = _ZONE_EXPLICIT_RE.search(text)
    if m:
        raw_z = m.group(1)
        z = _ZONE_MAP.get(raw_z, raw_z.upper())
        parsed["zone"] = z
        facts.append(("zone", z, f"IS 383:2016 Table 4: User specified Fine Aggregate Grading Zone {z}."))
    elif _ZONE_COARSE_SAND_RE.search(text):
        parsed["zone"] = "I"
        assumptions.append(("zone", "I", "IS 383:2016 Table 4: Crushed quarry sand has higher coarseness, corresponding to Zone I grading."))
    elif _ZONE_FINE_SAND_RE.search(text):
        parsed["zone"] = "IV"
        assumptions.append(("zone", "IV", "IS 383:2016 Table 4: Silt-rich or very fine pit sand corresponds to Zone IV grading."))
    else:
        parsed["zone"] = "II"
        assumptions.append(("zone", "II", "IS 383:2016 Table 4: Zone II natural river sand represents the standard median grading across Indian batching plants."))

    # ─────────────────────────────────────────────────────────────────────────
    # 8. Cement Grade & Type
    # ─────────────────────────────────────────────────────────────────────────
    if _PPC_RE.search(text):
        parsed["cement_grade"] = "PPC"
        parsed["cement_type"] = "ppc"
        facts.append(("cement_grade", "PPC", "IS 1489 (Part 1): Portland Pozzolana Cement specified (w/c curve follows 43 grade, standard SG 3.00)."))
        if "sg_cement" not in parsed:
            parsed["sg_cement"] = 3.00
    elif _PSC_RE.search(text):
        parsed["cement_grade"] = "PSC"
        parsed["cement_type"] = "psc"
        facts.append(("cement_grade", "PSC", "IS 455: Portland Slag Cement specified (w/c curve follows 43 grade, standard SG 3.00)."))
        if "sg_cement" not in parsed:
            parsed["sg_cement"] = 3.00
    else:
        m = _CEMENT_GRADE_RE.search(text)
        if m:
            cg = int(m.group(1))
            parsed["cement_grade"] = cg
            facts.append(("cement_grade", cg, f"IS 269:2015: User specified OPC {cg} grade cement."))
        elif parsed.get("fck", 30) >= 40 or _OPC_53_HINT_RE.search(text):
            parsed["cement_grade"] = 53
            assumptions.append(("cement_grade", 53, "IS 269:2015 & IS 10262:2019: Higher grade concrete (>= M40) requires OPC 53 grade for high early strength gain."))
        elif _OPC_33_HINT_RE.search(text):
            parsed["cement_grade"] = 33
            assumptions.append(("cement_grade", 33, "IS 269:2015: Low heat requirements for massive sections specify OPC 33 grade."))
        else:
            parsed["cement_grade"] = 43
            assumptions.append(("cement_grade", 43, "IS 269:2015: OPC 43 grade is standard general-purpose cement for Indian structural construction."))

    # ─────────────────────────────────────────────────────────────────────────
    # 9. Specific Gravities & Water Absorption
    # ─────────────────────────────────────────────────────────────────────────
    for field, regex, default, label, is_ref in [
        ("sg_cement", _SG_CEMENT_RE, 3.15, "SG of Cement", "IS 269:2015 standard specific gravity for OPC is 3.15."),
        ("sg_fa", _SG_FA_RE, 2.65, "SG of Fine Aggregate", "IS 2386 (Part 3): Typical specific gravity for natural river sand in India is 2.60 - 2.70 (adopted 2.65)."),
        ("sg_ca", _SG_CA_RE, 2.74, "SG of Coarse Aggregate", "IS 2386 (Part 3): Typical specific gravity for crushed basalt/granite metal in India is 2.65 - 2.80 (adopted 2.74)."),
        ("sg_fa_scm", _SG_FA_SCM_RE, 2.20, "SG of Fly Ash", "IS 3812: Standard specific gravity for pulverized fuel ash is 2.20."),
        ("sg_ggbs", _SG_GGBS_RE, 3.00, "SG of GGBS", "IS 16714: Standard specific gravity for ground granulated blast furnace slag is 3.00."),
        ("sg_sf", _SG_SF_RE, 2.20, "SG of Silica Fume", "IS 15388: Standard specific gravity for micro-silica fume is 2.20."),
        ("sg_sp", _SG_SP_RE, 1.145, "SG of Chemical Admixture", "IS 9103: Standard specific gravity for liquid PCE superplasticiser is 1.145."),
    ]:
        m = regex.search(text)
        if m:
            parsed[field] = float(m.group(1))
            facts.append((field, parsed[field], f"User provided testing lab value: {label} = {parsed[field]}."))
        else:
            parsed[field] = default
            assumptions.append((field, default, is_ref))

    for field, regex, default, label in [
        ("abs_fa", _ABS_FA_RE, 1.0, "FA water absorption"),
        ("abs_ca", _ABS_CA_RE, 0.5, "CA water absorption"),
        ("fm_fa", _FM_FA_RE, 0.0, "FA surface moisture"),
        ("fm_ca", _FM_CA_RE, 0.0, "CA surface moisture"),
    ]:
        m = regex.search(text)
        if m:
            parsed[field] = float(m.group(1))
            facts.append((field, parsed[field], f"{label} = {parsed[field]}% specified by user."))
        else:
            parsed[field] = default

    # ─────────────────────────────────────────────────────────────────────────
    # 10. Supplementary Cementitious Materials (SCMs)
    # ─────────────────────────────────────────────────────────────────────────
    scm_list: List[Tuple[str, float]] = []

    m = _FA_RE.search(text)
    if m:
        pct = float(m.group(1))
        scm_list.append(("FA", pct))
        facts.append(("scm", f"Fly Ash {pct}%", f"User specified {pct}% Fly Ash replacement per IS 3812 Part 1."))
    elif _FA_MENTION.search(text):
        scm_list.append(("FA", 25.0))
        assumptions.append(("scm", "Fly Ash @ 25%", "IS 10262:2019 Clause 5.2.1: Recommended optimum fly ash replacement for durability and workability is 25%."))

    m = _GGBS_RE.search(text)
    if m:
        pct = float(m.group(1))
        scm_list.append(("GGBS", pct))
        facts.append(("scm", f"GGBS {pct}%", f"User specified {pct}% GGBS replacement per IS 16714."))
    elif _GGBS_MENTION.search(text):
        scm_list.append(("GGBS", 40.0))
        assumptions.append(("scm", "GGBS @ 40%", "IS 10262:2019 Clause 5.2.2: Recommended optimum slag replacement for sulphate and marine resistance is 40%."))

    m = _SF_RE.search(text)
    if m:
        pct = float(m.group(1))
        scm_list.append(("SF", pct))
        facts.append(("scm", f"Silica Fume {pct}%", f"User specified {pct}% Silica Fume addition per IS 15388."))
    elif _SF_MENTION.search(text) or parsed.get("fck", 30) >= 60:
        scm_list.append(("SF", 8.0))
        assumptions.append(("scm", "Silica Fume @ 8%", "IS 10262:2019 Clause 5.2.3 & Annex E: High-strength concrete (>= M60) mandates 5-10% silica fume for micro-filler densification."))

    if scm_list:
        parsed["scm"] = scm_list

    # ─────────────────────────────────────────────────────────────────────────
    # 11. Chemical Admixtures (Superplasticisers)
    # ─────────────────────────────────────────────────────────────────────────
    m_sp = _SP_PCT_RE.search(text)
    m_wr = _SP_WR_RE.search(text)

    if m_sp:
        parsed["sp_pct"] = float(m_sp.group(1))
        facts.append(("sp_pct", parsed["sp_pct"], f"User specified {parsed['sp_pct']}% chemical admixture per IS 9103."))
    elif _SP_MENTION.search(text) or parsed.get("pumped") or parsed.get("slump", 0) >= 125 or parsed.get("fck", 0) >= 50:
        parsed["sp_pct"] = 1.0
        assumptions.append(("sp_pct", 1.0, "IS 9103 & IS 10262:2019 Clause 5.3: High slump / pumped / high strength concrete specifies 1.0% superplasticiser dosage for rheology."))

    if m_wr:
        parsed["sp_wr"] = float(m_wr.group(1)) / 100.0
        facts.append(("sp_wr", parsed["sp_wr"], f"User specified {int(parsed['sp_wr']*100)}% water reduction from admixture."))
    elif parsed.get("sp_pct"):
        parsed["sp_wr"] = 0.20
        assumptions.append(("sp_wr", 0.20, "IS 10262:2019 Clause 5.3: Modern polycarboxylate ether (PCE) superplasticisers routinely deliver 20% water reduction."))

    return {
        "parsed": parsed,
        "facts": [{"field": f, "value": v, "source": s} for f, v, s in facts],
        "assumptions": [{"field": f, "value": v, "reason": r} for f, v, r in assumptions],
        "missing": [{"field": f, "reason": r} for f, r in missing],
        "warnings": warnings,
    }
