"""Input validation for concrete mix design parameters.

Validates individual field values and cross-field consistency before
passing inputs to the IS 10262 calculation engine.
"""

from typing import Any, Dict, List, Tuple

# Valid exposure conditions
VALID_EXPOSURES = {"mild", "moderate", "severe", "very severe", "extreme"}
VALID_MEMBERS = {"RCC", "PCC"}
VALID_SIZES = {10, 20, 40}
VALID_ZONES = {"I", "II", "III", "IV"}
VALID_CEMENT_GRADES = {33, 43, 53}
VALID_SCM_TYPES = {"FA", "GGBS", "SF"}
VALID_PLACEMENTS = {"chute", "pump", "tremie", "manual"}
VALID_SUPERVISIONS = {"good", "very_good", "fair"}
VALID_AGG_TYPES = {"angular", "sub_angular", "gravel_crushed", "rounded"}


def validate_inputs(inputs: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Validate mix design inputs.

    Args:
        inputs: Dictionary of parsed / user-supplied design inputs.

    Returns:
        (errors, warnings) — errors prevent calculation; warnings are advisory.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # ── Required fields ──────────────────────────────────────────────────
    fck = inputs.get("fck")
    if fck is not None and isinstance(fck, str):
        try:
            fck = float(fck) if "." in fck else int(fck)
            inputs["fck"] = fck
        except (ValueError, TypeError):
            pass

    if fck is None:
        errors.append("Characteristic strength (fck) is required.")
    elif not isinstance(fck, (int, float)):
        errors.append("fck must be a number.")
    elif fck < 10 or fck > 80:
        errors.append(f"fck = {fck} MPa is outside the supported range (10–80).")
    elif fck > 60:
        warnings.append(
            f"fck = {fck} MPa exceeds the standard IS 10262 procedure range. "
            "Results are indicative and require trial-mix verification."
        )

    # Coerce numeric optional fields if passed as strings
    for num_key in ("slump", "cement_grade", "max_size", "sg_cement", "sg_fa", "sg_ca", "abs_fa", "abs_ca"):
        val = inputs.get(num_key)
        if val is not None and isinstance(val, str):
            try:
                inputs[num_key] = float(val) if "." in val else int(val)
            except (ValueError, TypeError):
                pass

    exposure = inputs.get("exposure")
    if exposure is None:
        errors.append("Exposure condition is required.")
    elif exposure not in VALID_EXPOSURES:
        errors.append(
            f"Exposure '{exposure}' is not valid. "
            f"Choose from: {', '.join(sorted(VALID_EXPOSURES))}."
        )

    # ── Optional but validated ───────────────────────────────────────────
    member = inputs.get("member", "RCC")
    if member not in VALID_MEMBERS:
        errors.append(f"Member type '{member}' is not valid. Use 'RCC' or 'PCC'.")

    max_size = inputs.get("max_size")
    if max_size is not None and max_size not in VALID_SIZES:
        warnings.append(
            f"Aggregate size {max_size} mm is non-standard. "
            "Standard sizes are 10, 20, 40 mm."
        )

    slump = inputs.get("slump")
    if slump is not None:
        if not isinstance(slump, (int, float)):
            errors.append("Slump must be a number (mm).")
        elif slump < 0 or slump > 250:
            errors.append(f"Slump {slump} mm is outside the plausible range (0–250).")
        elif slump > 200:
            warnings.append("Slump > 200 mm may require special workability control.")

    zone = inputs.get("zone")
    if zone is not None and zone not in VALID_ZONES:
        errors.append(f"Zone '{zone}' is not valid. Choose from: I, II, III, IV.")

    cement_grade = inputs.get("cement_grade")
    if cement_grade is not None and cement_grade not in VALID_CEMENT_GRADES:
        warnings.append(
            f"Cement grade {cement_grade} is not standard. "
            "Standard grades are 33, 43, 53."
        )

    placement = inputs.get("placement")
    if placement and placement not in VALID_PLACEMENTS:
        errors.append(f"Placement method '{placement}' is not valid. Choose from: {', '.join(sorted(VALID_PLACEMENTS))}.")

    supervision = inputs.get("supervision")
    if supervision and supervision not in VALID_SUPERVISIONS:
        errors.append(f"Supervision level '{supervision}' is not valid. Choose from: good, very_good, fair.")

    agg_type = inputs.get("agg_type")
    if agg_type and agg_type not in VALID_AGG_TYPES:
        errors.append(f"Aggregate type '{agg_type}' is not valid. Choose from: angular, sub_angular, gravel_crushed, rounded.")

    # ── Specific gravities (Bounded per IS standards) ─────────────────────
    sg_ranges = [
        ("sg_cement", "SG of cement (IS 269)", 2.80, 3.30),
        ("sg_fa", "SG of fine aggregate SSD (IS 2386)", 2.40, 2.95),
        ("sg_ca", "SG of coarse aggregate SSD (IS 2386)", 2.40, 3.10),
        ("sg_fa_scm", "SG of Fly Ash (IS 3812)", 1.90, 2.60),
        ("sg_ggbs", "SG of GGBS (IS 16714)", 2.80, 3.15),
        ("sg_sf", "SG of Silica Fume (IS 15388)", 2.00, 2.40),
        ("sg_sp", "SG of Chemical Admixture (IS 9103)", 1.05, 1.30),
    ]
    for field, label, lo, hi in sg_ranges:
        val = inputs.get(field)
        if val is not None:
            if not isinstance(val, (int, float)):
                errors.append(f"{label} must be a number.")
            elif val < lo or val > hi:
                errors.append(
                    f"{label} = {val} is outside valid physical test range ({lo} – {hi}). "
                    f"Please enter a value within {lo} to {hi}."
                )

    # ── Absorption / moisture ────────────────────────────────────────────
    for field, label, max_val in [
        ("abs_fa", "Water absorption of FA (%)", 5.0),
        ("abs_ca", "Water absorption of CA (%)", 3.0),
        ("fm_fa", "Free surface moisture of FA (%)", 8.0),
        ("fm_ca", "Free surface moisture of CA (%)", 4.0),
    ]:
        val = inputs.get(field)
        if val is not None:
            if not isinstance(val, (int, float)):
                errors.append(f"{label} must be a number.")
            elif val < 0:
                errors.append(f"{label} cannot be negative.")
            elif val > max_val:
                errors.append(f"{label} = {val}% exceeds allowable test limit of {max_val}%.")

    # ── SCM ──────────────────────────────────────────────────────────────
    scm = inputs.get("scm")
    if scm:
        total_pct = 0
        for item in scm:
            if isinstance(item, (list, tuple)):
                t, pct = item
            elif isinstance(item, dict):
                t, pct = item.get("type", ""), item.get("percent", 0)
            else:
                continue
            if t not in VALID_SCM_TYPES:
                errors.append(f"SCM type '{t}' is not supported. Use FA, GGBS, or SF.")
            total_pct += pct
        if total_pct > 70:
            errors.append(f"Total SCM replacement ({total_pct}%) exceeds 70%.")
        elif total_pct > 50:
            warnings.append(f"Total SCM replacement ({total_pct}%) is very high.")

    # ── Superplasticiser ─────────────────────────────────────────────────
    sp_pct = inputs.get("sp_pct")
    if sp_pct is not None:
        if sp_pct < 0 or sp_pct > 5:
            warnings.append(f"SP dosage {sp_pct}% is outside normal range (0–3%).")
    sp_wr = inputs.get("sp_wr")
    if sp_wr is not None:
        if sp_wr < 0 or sp_wr > 0.40:
            warnings.append(f"SP water reduction {sp_wr*100:.0f}% seems implausible.")

    # ── Cross-field checks ───────────────────────────────────────────────
    if fck and exposure:
        min_grades = {
            "mild": 20, "moderate": 25, "severe": 30,
            "very severe": 35, "extreme": 40,
        }
        if member == "PCC":
            min_grades = {
                "mild": 15, "moderate": 20, "severe": 20,
                "very severe": 20, "extreme": 25,
            }
        mg = min_grades.get(exposure, 0)
        if isinstance(fck, (int, float)) and fck < mg:
            errors.append(
                f"Grade M{int(fck)} does not meet the minimum grade M{mg} "
                f"required for {exposure} exposure ({member})."
            )

    return errors, warnings
