"""
Deterministic concrete mix design calculator (IS 10262:2019 procedure + IS 456:2000 limits).

IMPORTANT: every lookup table below was encoded from working knowledge of the codes, NOT copied
from your licensed copy. Entries tagged VERIFY must be checked against your PDFs before you
treat the dataset as ground truth. All tables live in this one file so fixing a value and
re-running generate_dataset.py regenerates all 100 problems consistently.
"""
import math

# ---------------------------------------------------------------- tables ----------------
# IS 10262:2019 - assumed standard deviation (N/mm2)                         [VERIFY]
def std_dev(fck, supervision="good"):
    """Assumed standard deviation per IS 10262:2019 Table 2 & IS 456:2000 Table 8.
    
    supervision: 'good' (standard batching & control), 'very_good' (tight RMC/precast), or 'fair' (site mixing).
    """
    if fck <= 15:
        base_s = 3.5
    elif fck <= 25:
        base_s = 4.0
    elif fck <= 60:
        base_s = 5.0
    else:
        base_s = 6.0

    if supervision == "fair":
        return base_s + 1.0  # IS 456 Table 8 footnote
    elif supervision == "very_good":
        return max(base_s - 0.5, 3.0)
    return base_s

# IS 10262:2019 - "X" in  f'ck = fck + X                                      [VERIFY]
def x_factor(fck):
    if fck <= 15: return 5.0
    if fck <= 25: return 5.5
    if fck <= 45: return 6.5
    return 8.0

# IS 10262:2019 Fig.1 (w/c vs 28-day strength by cement grade) approximated as f = A*exp(-B*w/c)
# Digitised approximately -> replace with your curve values.                  [VERIFY]
STRENGTH_CURVE = {33: (110.0, 2.40), 43: (129.0, 2.27), 53: (157.0, 2.32)}

# IS 456:2000 Table 5 - limits for exposure (20 mm aggregate): (max w/c, min cement kg/m3, min grade)
IS456_TABLE5_RCC = {
    "mild":        (0.55, 300, 20),
    "moderate":    (0.50, 300, 25),
    "severe":      (0.45, 320, 30),
    "very severe": (0.45, 340, 35),
    "extreme":     (0.40, 360, 40),
}
IS456_TABLE5_PCC = {
    "mild":        (0.60, 220, 15),
    "moderate":    (0.60, 240, 20),
    "severe":      (0.50, 250, 20),
    "very severe": (0.45, 260, 20),
    "extreme":     (0.40, 280, 25),
}
MAX_CEMENT = 450      # IS 456 cl.8.2.4.2, cement excluding SCM
MAX_CEMENTITIOUS = 550  # dataset convention for blended mixes                 [VERIFY]

# IS 10262:2019 - max water content (kg/m3) for 50 mm slump, angular aggregate, no admixture
WATER_50MM = {10: 208, 20: 186, 40: 165}
SLUMP_WATER_STEP = 0.03   # +3 % per 25 mm above 50 mm
# Entrapped air (% of concrete volume)                                         [VERIFY - 2009 used 3/2/1]
ENTRAPPED_AIR = {10: 1.5, 20: 1.0, 40: 0.8}
# Volume of coarse aggregate per unit volume of total aggregate at w/c = 0.50
CA_FRACTION = {
    10: {"IV": 0.50, "III": 0.48, "II": 0.46, "I": 0.44},
    20: {"IV": 0.66, "III": 0.64, "II": 0.62, "I": 0.60},
    40: {"IV": 0.75, "III": 0.73, "II": 0.71, "I": 0.69},
}
CA_FRACTION_PER_0_05_WC = 0.01   # +0.01 per 0.05 decrease in w/c (and vice versa)
PUMPING_CA_REDUCTION = 0.10      # reduce CA fraction by 10 % for pumpable concrete
# Cementitious uplift when SCMs used (dataset convention)                       [VERIFY]
SCM_UPLIFT = {"FA": 0.10, "GGBS": 0.05, "SF": 0.0}
SCM_SG = {"FA": 2.20, "GGBS": 2.90, "SF": 2.20}
SP_SG = 1.08


def _r(x, n=1):
    return round(x, n)


def design(p):
    """p: dict of inputs. Returns dict with steps, mix, checks."""
    steps = []

    def add(name, clause, clause_stmt, value, calculation="", note="", has_graph=False, graph_data=None):
        steps.append({
            "step": name,
            "clause": clause,
            "clause_statement": clause_stmt,
            "value": value,
            "calculation": calculation,
            "note": note,
            "has_graph": has_graph,
            "graph_data": graph_data
        })

    fck = p["fck"]
    exp = p["exposure"]
    member = p.get("member", "RCC")
    size = p["max_size"]
    slump = p["slump"]
    zone = p.get("zone", "II")
    raw_grade = p.get("cement_grade", 43)
    cement_type_input = str(p.get("cement_type", "")).lower()
    raw_str = str(raw_grade).strip().upper()

    if raw_str == "PPC" or "ppc" in cement_type_input:
        cement_type = "PPC"
        grade = 43
        sg_c = p.get("sg_cement", 3.00)
        cement_label = "PPC (IS 1489)"
    elif raw_str == "PSC" or "psc" in cement_type_input:
        cement_type = "PSC"
        grade = 43
        sg_c = p.get("sg_cement", 3.00)
        cement_label = "PSC (IS 455)"
    else:
        cement_type = "OPC"
        try:
            grade = int(raw_grade)
            if grade not in (33, 43, 53):
                grade = 43
        except (ValueError, TypeError):
            grade = 43
        sg_c = p.get("sg_cement", 3.15)
        cement_label = f"OPC {grade} (IS 269)"

    supervision = p.get("supervision", "good")
    placement = p.get("placement", "chute")
    agg_type = p.get("agg_type", "angular")

    # Specific gravities (with user/lab overrides)
    sg_fa, sg_ca = p.get("sg_fa", 2.65), p.get("sg_ca", 2.74)
    sg_sp = p.get("sg_sp", 1.145)
    
    scm_sg_map = {
        "FA": p.get("sg_fa_scm", 2.20),
        "GGBS": p.get("sg_ggbs", 3.00),
        "SF": p.get("sg_sf", 2.20),
    }

    scms = p.get("scm", [])            # list of (type, percent of total cementitious)
    sp_pct = p.get("sp_pct", 0.0)      # % by mass of cementitious
    sp_wr = p.get("sp_wr", 0.0)        # fractional water reduction from admixture
    pumped = p.get("pumped", False) or (placement == "pump")
    special = p.get("special")         # None | "scc"
    advanced = p.get("advanced", False)

    # ─────────────────────────────────────────────────────────────────────────
    # Step 1: Target Mean Compressive Strength
    # ─────────────────────────────────────────────────────────────────────────
    s, X = std_dev(fck, supervision), x_factor(fck)
    ft1 = fck + 1.65 * s
    ft2 = fck + X
    ft = max(ft1, ft2)
    add(
        name="Step 1: Target Mean Strength (f'ck)",
        clause="IS 10262:2019 Clause 4.2",
        clause_stmt="f'ck = max(fck + 1.65 × s, fck + X), where s is standard deviation from Table 2 and X is factor based on grade.",
        value=_r(ft, 2),
        calculation=f"fck + 1.65s = {fck} + 1.65 × {s:.1f} = {ft1:.2f} N/mm² vs fck + X = {fck} + {X:.1f} = {ft2:.2f} N/mm² -> Governed = {ft:.2f} N/mm²",
        note=f"Assumed standard deviation s={s} N/mm² (Supervision: {supervision.replace('_', ' ').title()}), X={X} N/mm²."
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 2: Water-Cement Ratio from Strength Curve (IS 10262 Fig. 1)
    # ─────────────────────────────────────────────────────────────────────────
    A, B = STRENGTH_CURVE[grade]
    wc_strength = math.log(A / ft) / B
    add(
        name="Step 2: w/c Ratio from Strength Curve (Figure 1)",
        clause="IS 10262:2019 Clause 5.1 & Figure 1",
        clause_stmt=f"Relationship between 28-day compressive strength of concrete and water-cement ratio for {cement_label}.",
        value=_r(wc_strength, 3),
        calculation=f"w/c = ln(A / f'ck) / B = ln({A} / {ft:.2f}) / {B} = {wc_strength:.3f} (for {cement_label} curve: f = {A}·exp(-{B}·w/c))",
        note=f"Interpolated directly from statutory strength curve for {cement_label}.",
        has_graph=True,
        graph_data={
            "cement_grade": grade,
            "cement_label": cement_label,
            "target_fck": _r(ft, 2),
            "wc_strength": _r(wc_strength, 3),
            "A": A,
            "B": B
        }
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 3: Durability Limits & Final Adopted w/c (IS 456 Table 5)
    # ─────────────────────────────────────────────────────────────────────────
    tbl = IS456_TABLE5_PCC if member == "PCC" else IS456_TABLE5_RCC
    wc_max, c_min, g_min = tbl[exp]
    if placement == "tremie":
        c_min = max(c_min, 350)  # IS 456 underwater / tremie placement minimum binder
    wc = math.floor(min(wc_strength, wc_max) * 100) / 100
    gov = "durability" if wc_max < wc_strength else "strength"
    add(
        name="Step 3: Durability Limits & Adopted w/c",
        clause="IS 456:2000 Clause 8.2.2.1 Table 5",
        clause_stmt="Minimum cementitious material content, maximum free water-cement ratio and minimum grade of concrete for different exposures with normal weight aggregates of 20 mm nominal maximum size.",
        value=wc,
        calculation=f"Durability max w/c = {wc_max:.2f} ({exp.upper()} exposure, {member}) vs Strength w/c = {wc_strength:.3f} -> Adopted w/c = min({wc_strength:.3f}, {wc_max}) = {wc:.2f}",
        note=f"Governed by {gov}. Min cement content = {c_min} kg/m³, Min grade = M{g_min}."
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 4: Water Content & Aggregate Shape Selection (IS 10262 Table 3)
    # ─────────────────────────────────────────────────────────────────────────
    w0_base = WATER_50MM[size]
    agg_w_adj = 0
    if agg_type == "sub_angular":
        agg_w_adj = -10
    elif agg_type == "gravel_crushed":
        agg_w_adj = -15
    elif agg_type == "rounded":
        agg_w_adj = -20
    w0 = w0_base + agg_w_adj
    add(
        name="Step 4: Water Content & Aggregate Shape",
        clause="IS 10262:2019 Table 3 & Clause 5.3",
        clause_stmt="Maximum water content per cubic metre of concrete for nominal maximum size of aggregate (for 50 mm slump, angular coarse aggregate without admixture).",
        value=_r(w0, 1),
        calculation=f"Base water for {size} mm aggregate = {w0_base} kg/m³. Aggregate shape correction ({agg_type.replace('_',' ')}) = {agg_w_adj} kg/m³ -> Base water = {w0} kg/m³",
        note=f"Table 3 Note 1: Angular is base; sub-angular reduces by 10kg; gravel with crushed reduces by 15kg; rounded reduces by 20kg."
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 5: Workability / Slump Adjustment
    # ─────────────────────────────────────────────────────────────────────────
    w_slump = w0
    if slump > 50:
        w_slump = w0 * (1 + SLUMP_WATER_STEP * (slump - 50) / 25)
    add(
        name="Step 5: Workability / Slump Adjustment",
        clause="IS 10262:2019 Clause 5.3",
        clause_stmt="For slumps exceeding 50 mm, the water content is increased by 3 percent for every additional 25 mm slump.",
        value=_r(w_slump, 1),
        calculation=f"Target slump = {slump} mm (+{slump - 50} mm above 50 mm). Water increase = +{SLUMP_WATER_STEP * (slump - 50) / 25 * 100:.1f}% -> Water = {w0} × (1 + 0.03 × {slump - 50}/25) = {w_slump:.1f} kg/m³",
        note=f"Required workability slump = {slump} mm."
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 6: Chemical Superplasticiser Water Reduction
    # ─────────────────────────────────────────────────────────────────────────
    w = w_slump
    if sp_wr:
        w = w_slump * (1 - sp_wr)
    add(
        name="Step 6: Chemical Superplasticiser Dosage & Water Reduction",
        clause="IS 10262:2019 Clause 5.3.3 & IS 9103",
        clause_stmt="Water reduction of 20 to 30 percent and above may be achieved with the use of superplasticisers conforming to IS 9103.",
        value=_r(w, 1),
        calculation=f"Dosage = {sp_pct}% of cementitious, Chemical water reduction = {sp_wr*100:.0f}% -> Net water = {w_slump:.1f} × (1 - {sp_wr:.2f}) = {w:.1f} kg/m³",
        note=f"Conforms to IS 9103. Superplasticiser mass will be calculated in absolute volume step."
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 7: Cementitious Material Content Calculation
    # ─────────────────────────────────────────────────────────────────────────
    cementitious_base = w / wc
    cementitious = max(cementitious_base, float(c_min))
    if special == "scc":
        cementitious = max(cementitious, 450.0)

    uplift = 0.0
    if scms:
        uplift = max(SCM_UPLIFT[t] for t, _ in scms)
        cementitious *= (1 + uplift)
    add(
        name="Step 7: Total Cementitious Content & SCM Uplift",
        clause="IS 10262:2019 Clause 5.4 & 5.2",
        clause_stmt="Cementitious material content = Water / (w/c), verified against Table 5 minimum binder and Clause 8.2.4.2 maximum cement limit.",
        value=_r(cementitious, 0),
        calculation=f"Water / Adopted w/c = {w:.1f} / {wc:.2f} = {cementitious_base:.1f} kg/m³ (Raised to Table 5 min {c_min} kg/m³). SCM uplift (+{uplift*100:.0f}%) -> Total Binder = {cementitious:.0f} kg/m³",
        note=f"Clause 5.2 recommendation: Increase total binder by {uplift*100:.0f}% when mineral admixtures are used for equivalent 28-day strength."
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 8: Mineral Admixture (SCM) Breakdown
    # ─────────────────────────────────────────────────────────────────────────
    scm_mass = {t: cementitious * pct / 100 for t, pct in scms}
    cement = cementitious - sum(scm_mass.values())
    wcm_actual = w / cementitious
    scm_desc = " + ".join([f"{t} ({pct}%): {scm_mass[t]:.0f} kg/m³" for t, pct in scms]) if scms else f"None (100% {cement_label})"
    add(
        name="Step 8: Cement & Mineral Admixture (SCM) Breakdown",
        clause="IS 10262:2019 Clause 5.2 & IS 3812 / 16714 / 15388",
        clause_stmt="Optimum replacement levels for fly ash (15 to 30%), GGBS (25 to 50%), and silica fume (5 to 10%) per respective Indian Standards.",
        value={"cement": _r(cement, 0), **{k: _r(v, 0) for k, v in scm_mass.items()}},
        calculation=f"Net {cement_label} = {cementitious:.0f} - {sum(scm_mass.values()):.0f} = {cement:.0f} kg/m³; SCM Additions: {scm_desc}",
        note=f"Actual water-cementitious ratio w/cm = {w:.1f} / {cementitious:.0f} = {wcm_actual:.3f} (Permissible max = {wc_max})."
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 9: Coarse & Fine Aggregate Volume Fractions
    # ─────────────────────────────────────────────────────────────────────────
    base_ca_frac = CA_FRACTION[size][zone]
    ca_wc_adj = CA_FRACTION_PER_0_05_WC * (0.50 - wcm_actual) / 0.05
    ca_shape_adj = 0.02 if agg_type == "rounded" else 0.0
    frac_before_pump = base_ca_frac + ca_wc_adj + ca_shape_adj
    frac = frac_before_pump
    if pumped:
        frac *= (1 - PUMPING_CA_REDUCTION)
    if special == "scc":
        frac = 0.50
    frac = round(frac, 3)
    add(
        name="Step 9: Coarse & Fine Aggregate Volume Fractions",
        clause="IS 10262:2019 Table 5 & Clause 5.5",
        clause_stmt="Volume of coarse aggregate per unit volume of total aggregate for different zones of fine aggregate for water-cement ratio of 0.50.",
        value=frac,
        calculation=f"Table 5 base CA fraction for {size}mm Zone {zone} = {base_ca_frac}. w/c correction ({0.50 - wcm_actual:+.3f} from 0.50) = {ca_wc_adj:+.3f}. Shape correction = {ca_shape_adj:+.2f} -> Fraction = {frac_before_pump:.3f}",
        note=f"Coarse Aggregate volume fraction = {frac:.3f}, Fine Aggregate fraction = {1 - frac:.3f}."
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 10: Placement Method Adjustment
    # ─────────────────────────────────────────────────────────────────────────
    placement_details = "Chute / crane placing: Standard aggregate proportions retained."
    if pumped:
        placement_details = f"Pumping placement: Coarse aggregate fraction reduced by 10% (from {frac_before_pump:.3f} to {frac:.3f}) per IS 10262 Cl 5.5.1 to ensure adequate lubrication mortar."
    elif placement == "tremie":
        placement_details = f"Tremie underwater placement: Flowable slump maintained and minimum cementitious content verified >= 350 kg/m³ per IS 456 Cl 14.2."
    add(
        name="Step 10: Placement Method Verification",
        clause="IS 10262:2019 Clause 5.5.1 & IS 456 Clause 14.2",
        clause_stmt="For pumpable concrete, coarse aggregate content may be reduced up to 10 percent; for tremie placing, flowable slump and min binder 350 kg/m³ are mandated.",
        value=placement.title(),
        calculation=placement_details,
        note=f"Selected placing method: {placement.upper()}."
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 11: Absolute Volume Calculations per m³
    # ─────────────────────────────────────────────────────────────────────────
    sp_mass = sp_pct / 100 * cementitious
    air = ENTRAPPED_AIR[size] / 100
    v_c = cement / (sg_c * 1000)
    v_scm = sum(m / (scm_sg_map.get(t, 2.20) * 1000) for t, m in scm_mass.items())
    v_w = w / 1000
    v_sp = sp_mass / (sg_sp * 1000)
    v_agg = 1 - (v_c + v_scm + v_w + v_sp + air)
    ca = v_agg * frac * sg_ca * 1000
    fa = v_agg * (1 - frac) * sg_fa * 1000
    add(
        name="Step 11: Absolute Volume & Aggregate Masses (SSD)",
        clause="IS 10262:2019 Clause 5.6 & 5.7",
        clause_stmt="Absolute volume of constituent = Mass / (Specific Gravity × 1000). Total volume of aggregate = 1 - (V_cement + V_SCM + V_water + V_SP + V_air).",
        value={"fine_ssd": _r(fa, 0), "coarse_ssd": _r(ca, 0)},
        calculation=f"V_c={v_c:.4f}m³, V_scm={v_scm:.4f}m³, V_w={v_w:.4f}m³, V_sp={v_sp:.4f}m³, V_air={air:.4f}m³ -> V_total_agg = 1 - {v_c+v_scm+v_w+v_sp+air:.4f} = {v_agg:.4f} m³",
        note=f"CA (SSD) = {v_agg:.4f} × {frac:.3f} × {sg_ca} × 1000 = {ca:.0f} kg; FA (SSD) = {v_agg:.4f} × {1-frac:.3f} × {sg_fa} × 1000 = {fa:.0f} kg."
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Step 12: Field Batching Moisture & Absorption Adjustments
    # ─────────────────────────────────────────────────────────────────────────
    fm_fa, fm_ca = p.get("fm_fa", 0.0), p.get("fm_ca", 0.0)
    abs_fa, abs_ca = p.get("abs_fa", 0.0), p.get("abs_ca", 0.0)
    delta_w_fa = fa * (fm_fa - abs_fa) / 100
    delta_w_ca = ca * (fm_ca - abs_ca) / 100
    w_adj = max(w - delta_w_fa - delta_w_ca, 0.0)
    fa_adj = fa * (1 + fm_fa / 100)
    ca_adj = ca * (1 + fm_ca / 100)
    add(
        name="Step 12: Field Batching Adjustments for Moisture & Absorption",
        clause="IS 10262:2019 Clause 5.7 & Annex C",
        clause_stmt="The mix proportions should be adjusted for the water absorption and free moisture content of coarse and fine aggregates measured as per IS 2386 (Part 3).",
        value={"water_field": _r(w_adj, 1), "fine_field": _r(fa_adj, 0), "coarse_field": _r(ca_adj, 0)},
        calculation=f"Net water correction = {-(delta_w_fa + delta_w_ca):+.1f} kg (FA free moisture {fm_fa}%, abs {abs_fa}%; CA free moisture {fm_ca}%, abs {abs_ca}%). Field Batch: Water={w_adj:.1f} kg, FA={fa_adj:.0f} kg, CA={ca_adj:.0f} kg",
        note="Mixer batching quantities adjusted from SSD condition to actual field stockpile moisture."
    )

    mix = {
        "cement": _r(cement, 0), "scm": {k: _r(v, 0) for k, v in scm_mass.items()},
        "water": _r(w, 1), "fine_aggregate_ssd": _r(fa, 0), "coarse_aggregate_ssd": _r(ca, 0),
        "admixture": _r(sp_mass, 2),
        "cementitious_total": _r(cementitious, 0), "w_cm": round(wcm_actual, 3),
        "ratio_by_mass_cementitious": f"1 : {fa/cementitious:.2f} : {ca/cementitious:.2f}",
        "field_adjusted": {"water": _r(w_adj, 1), "fine_aggregate": _r(fa_adj, 0), "coarse_aggregate": _r(ca_adj, 0)},
    }

    # 9 checks
    pred = A * math.exp(-B * wcm_actual)
    vol_sum = v_c + v_scm + v_w + v_sp + air + ca / (sg_ca * 1000) + fa / (sg_fa * 1000)
    max_c = 540 if advanced else MAX_CEMENT
    max_cm = 600 if advanced else MAX_CEMENTITIOUS
    checks = {
        "volume_sums_to_1": abs(vol_sum - 1) < 1e-6,
        "w_cm_within_durability_limit": wcm_actual <= wc_max + 1e-9,
        "min_cementitious_met": cementitious >= c_min - 1e-9,
        "cement_within_max": cement <= max_c,
        "cementitious_within_max": cementitious <= max_cm,
        "grade_meets_exposure_minimum": fck >= g_min,
        "predicted_strength_ge_target": pred >= ft,
        "aggregate_volume_positive": v_agg > 0.5,
    }
    return {
        "target_strength": round(ft, 2), "w_c_adopted": wc, "predicted_28d_mean": round(pred, 1),
        "mix_per_m3": mix, "steps": steps, "checks": checks, "all_checks_pass": all(checks.values()),
    }
