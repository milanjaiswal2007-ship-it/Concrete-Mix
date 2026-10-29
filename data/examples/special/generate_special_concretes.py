"""Generates literature-anchored special-concrete mix records + keyword banks.
Each mix is closed on absolute volume (1 m3) by construction; strengths are INDICATIVE RANGES, not lab results."""
import json, csv, itertools, random
random.seed(7)
SG = dict(cement=3.15, fa=2.2, ggbs=2.9, sf=2.2, sand=2.65, ca=2.70, water=1.0, sp=1.08, quartz=2.65, lime=2.7,
          steel=7.85, pp=0.91, pva=1.3, glass=2.6, basalt=2.7, cf=1.8, cnt=1.8, gr=2.2, nano=2.2)
def r(x, n=1): return round(x, n)
def close(parts, air=0.0, agg=None):
    """parts: dict name->(kg,sg). agg: (fine_frac_by_vol, sg_f, sg_c, has_coarse). Returns mix dict with aggregates solved."""
    v = sum(m / (s * 1000) for m, s in parts.values()) + air
    rem = 1 - v
    assert rem > 0.08, f"no room for aggregate {rem}"
    out = {k: r(m, 1) for k, (m, s) in parts.items()}
    if agg:
        ff, sf, sc, coarse = agg
        if not coarse: ff = 1.0
        out["fine_aggregate_kg"] = r(rem * ff * sf * 1000, 0)
        if coarse: out["coarse_aggregate_kg"] = r(rem * (1 - ff) * sc * 1000, 0)
    out["entrapped_air_pct"] = r(air * 100, 1)
    return out
def vol_check(mix, sgmap):
    v = mix.get("entrapped_air_pct", 0) / 100
    for k, val in mix.items():
        if k in sgmap: v += val / (sgmap[k] * 1000)
    return r(v, 3)

RECS = []
def add(tcode, tname, group, n, statement, inputs, mix, sgmap, strength, props, curing, source, notes, kw_hint):
    vc = vol_check(mix, sgmap)
    rec = dict(
        id=f"{tcode}{n:03d}", group=group, concrete_type=tname, problem_statement=statement, inputs=inputs,
        mix_per_m3=mix, indicative_28d_compressive_MPa=strength, expected_properties=props, curing=curing,
        checks=dict(absolute_volume_closed=abs(vc - 1.0) < 0.02, positive_quantities=all(v > 0 for v in mix.values() if isinstance(v, (int, float)))),
        absolute_volume_sum=vc, verification_status="literature_based_unverified",
        source=source, notes=notes, keywords=kw_hint)
    rec["retrieval_text"] = (f"{statement} TYPE {tname}. MIX " + ", ".join(f"{k} {v}" for k, v in mix.items()) +
        f". STRENGTH {strength[0]}-{strength[1]} MPa. CURING {curing}. " + " ".join(kw_hint))
    RECS.append(rec)

# ---------------- 1 GEOPOLYMER ----------------
NAOH_SOL = {8: 262, 10: 314, 12: 361, 14: 404, 16: 444}  # g NaOH solids per kg solution (Hardjito & Rangan 2005)
n = 0
for (ggbs, M, ab, ss, cure) in itertools.product([0, 20, 30, 50], [8, 10, 12, 14, 16], [0.35, 0.40], [2.0, 2.5], ["heat60", "ambient"]):
    if (ggbs == 0 and cure == "ambient") or (ggbs > 0 and cure == "heat60" and M in (8, 16)): continue
    if (M, ab, ss) not in [(8,.35,2.5),(10,.4,2.0),(12,.35,2.5),(12,.4,2.5),(14,.35,2.5),(14,.4,2.0),(16,.4,2.5),(10,.35,2.5)] and random.random() > 0.35: continue
    if n >= 26: break
    n += 1
    binder = 400 + 10 * (n % 4)
    fa = binder * (1 - ggbs / 100); gg = binder * ggbs / 100
    liquid = binder * ab; sol_ss = liquid * ss / (1 + ss); sol_sh = liquid - sol_ss
    water_extra = 12 + 4 * (n % 3) + (8 if ggbs else 0); sp = 6 + (n % 3)
    mix = close({"fly_ash_class_F_kg": (fa, SG["fa"]), "ggbs_kg": (gg, SG["ggbs"]), "naoh_solution_kg": (sol_sh, 1.0 + 0.0308 * M),
                 "sodium_silicate_solution_kg": (sol_ss, 1.5), "extra_water_kg": (water_extra, 1.0), "superplasticiser_kg": (sp, SG["sp"])},
                air=0.015, agg=(0.30, SG["sand"], 2.70, True))
    sgm = {"fly_ash_class_F_kg": 2.2, "ggbs_kg": 2.9, "naoh_solution_kg": 1.0 + 0.0308 * M, "sodium_silicate_solution_kg": 1.5, "extra_water_kg": 1, "superplasticiser_kg": 1.08, "fine_aggregate_kg": 2.65, "coarse_aggregate_kg": 2.70}
    base = {8: 28, 10: 36, 12: 44, 14: 52, 16: 56}[M]
    if cure == "ambient": base = 24 + 0.45 * ggbs + (M - 8) * 1.2
    base *= 1.0 if ss == 2.5 else 0.95
    lo, hi = r(base * 0.85, 0), r(base * 1.15, 0)
    mix["naoh_solids_kg"] = r(sol_sh * NAOH_SOL[M] / 1000, 1)
    mix["alkaline_liquid_to_binder"] = ab; mix["Na2SiO3_to_NaOH_ratio"] = ss; mix["NaOH_molarity"] = M
    cur = "heat cure 60 C for 24 h after 1-day rest" if cure == "heat60" else "ambient cure (27-30 C) with sealed/moist protection"
    stmt = (f"Design a geopolymer concrete (alkali-activated {'fly ash' if not ggbs else 'fly ash + '+str(ggbs)+'% GGBS'}) with {M}M NaOH, "
            f"Na2SiO3/NaOH ratio {ss}, alkaline liquid/binder {ab}, 20 mm aggregate, {cur}. Target 28-day strength about {int((lo+hi)/2)} MPa.")
    add("GP", "geopolymer", "S1_geopolymer", n, stmt, dict(binder="fly_ash" + ("+ggbs" if ggbs else ""), ggbs_pct=ggbs, naoh_molarity=M, ss_sh_ratio=ss,
        alk_binder=ab, max_size=20, exposure="moderate", member="RCC", curing=cure, fck=int(round((lo + hi) / 2 / 5) * 5)), mix, sgm, [lo, hi],
        dict(workability="slump 100-200 mm typical; mixes with high GGBS stiffen quickly", density_kg_m3="2300-2450", shrinkage="low drying shrinkage reported for heat-cured FA mixes"),
        cur, "Hardjito & Rangan 2005 (Curtin Univ. Research Report GC1); Rangan 2008; Provis & van Deventer (eds.) RILEM TC 224-AAM 2014; Davidovits 2008",
        "Rangan-style design: Na2SiO3 solution SiO2/Na2O approx 2 (SiO2 29.4%, Na2O 14.7%, water 55.9%). No IS 10262 w/c law applies; strength is governed by molarity, Ca content and curing.",
        ["geopolymer concrete", "alkali activated concrete", "fly ash geopolymer", f"{M}M NaOH", "sodium silicate", "cement free concrete"] + (["GGBS geopolymer", "ambient cured geopolymer"] if ggbs else ["heat cured geopolymer"]))

# ---------------- 2 SELF-HEALING ----------------
n = 0
mech = [("crystalline", "crystalline admixture (xypex-type, 1% bwoc)", 0.01), ("bacterial", "Bacillus-based bacteria in expanded clay carriers with calcium lactate", 0.0),
        ("sap", "superabsorbent polymer (SAP)", 0.005), ("capsule", "polymer/silica-sol encapsulated healing agent", 0.0), ("autogenous", "autogenous healing via high SCM + fibres (ECC type)", 0.0)]
for (key, desc, dose), (wc, grade, scm) in itertools.product(mech, [(0.45, 30, 0), (0.40, 35, 15), (0.38, 40, 25), (0.50, 25, 0), (0.42, 35, 20)]):
    n += 1
    cem = {0.45: 380, 0.40: 400, 0.38: 420, 0.50: 360, 0.42: 390}[wc]
    c = cem * (1 - scm / 100); f = cem * scm / 100; w = cem * wc
    parts = {"cement_kg": (c, SG["cement"]), "fly_ash_kg": (f, SG["fa"]), "water_kg": (w, 1.0)}
    sgm = {"cement_kg": 3.15, "fly_ash_kg": 2.2, "water_kg": 1.0, "fine_aggregate_kg": 2.65, "coarse_aggregate_kg": 2.7}
    extra = {}
    if key == "crystalline": parts["crystalline_admixture_kg"] = (cem * 0.01, 2.5); sgm["crystalline_admixture_kg"] = 2.5; extra = dict(dose="1% by mass of binder (typical 0.8-2%)")
    if key == "bacterial":
        parts["calcium_lactate_kg"] = (cem * 0.01, 1.49); parts["bacteria_loaded_expanded_clay_kg"] = (60 + 5 * (n % 4), 1.3); sgm.update(calcium_lactate_kg=1.49, bacteria_loaded_expanded_clay_kg=1.3)
        extra = dict(spores="approx 1e8-1e9 spores per kg carrier, calcium lactate 0.5-1.5% bwoc")
    if key == "sap": parts["sap_kg"] = (cem * 0.005, 1.1); parts["extra_internal_curing_water_kg"] = (cem * 0.005 * 10, 1.0); sgm.update(sap_kg=1.1, extra_internal_curing_water_kg=1.0)
    if key == "capsule": parts["healing_capsules_kg"] = (12 + (n % 3) * 4, 1.1); sgm["healing_capsules_kg"] = 1.1
    if key == "autogenous": parts["pva_fibre_kg"] = (13, SG["pva"]); sgm["pva_fibre_kg"] = SG["pva"]; parts["superplasticiser_kg"] = (3.5, 1.08); sgm["superplasticiser_kg"] = 1.08
    mix = close(parts, 0.02, (0.36, 2.65, 2.7, key != "autogenous"))
    mix.update({"w_cm": wc, "scm_pct": scm}); mix.update(extra)
    lo = {30: 34, 35: 40, 40: 46, 25: 29}[grade]
    stmt = (f"Design a self-healing concrete of grade M{grade} using {desc}, w/cm {wc}, {'with ' + str(scm) + '% fly ash, ' if scm else ''}20 mm aggregate. "
            f"Target crack width healed 0.15-0.4 mm in wet-dry cycles.")
    add("SH", "self-healing", "S2_self_healing", n, stmt, dict(mechanism=key, w_cm=wc, scm_pct=scm, max_size=20, fck=grade, exposure="severe", member="RCC"), mix, sgm,
        [lo, lo + 10], dict(healable_crack_width_mm={"crystalline": "0.2-0.4", "bacterial": "0.15-0.8", "sap": "0.1-0.3", "capsule": "0.1-0.5", "autogenous": "<0.06 (ECC type, multiple micro-cracks)"}[key],
                            recovery="water tightness recovery typically assessed by permeability/capillary tests after wet-dry cycles"), "water curing 28 d; healing assessed via 14-56 d wet/dry or submerged cycles",
        "De Belie et al. 2018 Adv. Mater. Interfaces 5(17); Jonkers et al. 2010 Ecol. Eng. 36; Ferrara et al. 2018 Constr. Build. Mater. 167 (crystalline); Snoeck & De Belie 2015 (SAP); RILEM TC 221-SHC (Mihashi) ",
        "Mechanism-specific doses are indicative literature ranges; healing performance depends heavily on crack width and moisture availability. Verify with supplier datasheet.",
        ["self healing concrete", f"{key} healing", "crack healing", "autonomous healing", "microbial concrete", "crystalline waterproofing"] if True else [])

# ---------------- 3 SELF-SENSING ----------------
n = 0
sens = [("carbon_fibre", "short carbon fibre (6 mm)", [0.2, 0.4, 0.6, 1.0]), ("cnt", "multi-walled carbon nanotubes with PCE dispersant", [0.05, 0.1, 0.3, 0.5]),
        ("carbon_black", "carbon black", [0.5, 1.0, 2.0]), ("steel_fibre", "steel fibre (13 mm micro)", [0.5, 1.0, 1.5]), ("graphite", "graphite/graphene nano-platelets", [0.5, 1.0, 2.0]), ("hybrid", "hybrid CF + steel fibre", [0.3, 0.6])]
for (key, desc, doses), wb in itertools.product(sens, [0.35, 0.42]):
    for d in doses:
        if n >= 28: break
        n += 1
        cem = 450; c = cem * 0.9; sfu = cem * 0.1
        parts = {"cement_kg": (c, 3.15), "silica_fume_kg": (sfu, 2.2), "water_kg": (cem * wb, 1.0), "superplasticiser_kg": (4 + 3 * (d > 0.3), 1.08)}
        sgm = {"cement_kg": 3.15, "silica_fume_kg": 2.2, "water_kg": 1.0, "superplasticiser_kg": 1.08, "fine_aggregate_kg": 2.65, "coarse_aggregate_kg": 2.7}
        fibre_mass = cem * d / 100
        parts["conductive_filler_kg"] = (fibre_mass, SG["steel"] if key == "steel_fibre" else 1.8); sgm["conductive_filler_kg"] = SG["steel"] if key == "steel_fibre" else 1.8
        if key == "cnt": parts["dispersant_pce_kg"] = (fibre_mass * 3, 1.05); sgm["dispersant_pce_kg"] = 1.05
        mix = close(parts, 0.025, (0.40, 2.65, 2.7, True)); mix.update({"w_cb": wb, "filler_dosage_pct_bwoc": d})
        stmt = (f"Design a self-sensing (piezoresistive) concrete using {desc} at {d}% by mass of binder, w/b {wb}, 10 mm aggregate, "
                f"for structural health monitoring of beams/bridge decks (fractional change in resistivity under compressive load).")
        add("SS", "self-sensing", "S3_self_sensing", n, stmt, dict(filler=key, dose_pct=d, w_b=wb, max_size=10, exposure="moderate", member="RCC", fck=35), mix, sgm,
            [34, 55], dict(gauge_factor="roughly 50-500 (mortar/paste lab specimens; concrete usually lower)", percolation_threshold={"carbon_fibre": "approx 0.5-1.0% bwoc", "cnt": "approx 0.1-0.5% bwoc", "carbon_black": "approx 1-3% bwoc"}.get(key, "see source"),
                           measurement="2-probe or 4-probe DC/AC resistivity, FCR vs strain"), "moist cure 28 d, oven-dry or saturated state must be fixed before measurement",
            "Chung 2000/2002 (Mater. Sci. Eng. R / Smart Mater. Struct.); Han, Ding, Ou et al. 2015 Sensors 15 'Self-sensing concrete'; Ou & Han 2009; D'Alessandro et al. 2016",
            "Self-sensing performance depends on moisture and polarisation, not just mix proportions; most published data are on paste/mortar and need scaling. Indicative only.",
            ["self sensing concrete", "piezoresistive concrete", "smart concrete", "structural health monitoring", "conductive concrete", f"{key.replace('_',' ')} concrete"])

# ---------------- 4 SCC ----------------
n = 0
for (grade, powder, wp, filler, ms) in itertools.product([25, 30, 40, 50, 60], [480, 540, 600], [0.9, 1.0], ["fa", "ggbs", "lime"], [12, 16]):
    if n >= 26: break
    if random.random() > 0.2: continue
    n += 1
    cem = {25: .5, 30: .55, 40: .62, 50: .68, 60: .72}[grade] * powder
    fil = powder - cem
    w = (powder * wp) / ((1 / 3.15 * 0.55 + 1 / 2.2 * 0.45) * 1000) * 0 + powder * (0.30 if grade >= 50 else 0.36 if grade >= 40 else 0.42)
    spv = 0.9 + 0.1 * (grade // 20)
    parts = {"cement_kg": (cem, 3.15), f"{ {'fa':'fly_ash','ggbs':'ggbs','lime':'limestone_powder'}[filler] }_kg": (fil, {"fa": 2.2, "ggbs": 2.9, "lime": 2.7}[filler]),
             "water_kg": (w, 1.0), "pce_superplasticiser_kg": (powder * spv / 100, 1.08), "vma_kg": (1.2, 1.02)}
    sgm = {k: s for k, (m_, s) in parts.items()}; sgm.update(fine_aggregate_kg=2.65, coarse_aggregate_kg=2.7)
    mix = close(parts, 0.015, (0.52, 2.65, 2.7, True))
    mix.update({"powder_content_kg_m3": powder, "w_powder_mass": r(w / powder, 2), "max_size_mm": ms})
    flow = 700 if grade < 50 else 680
    add("SC", "self-compacting", "S4_self_compacting", n,
        f"Design a self-compacting concrete (SCC) of grade M{grade} with powder content {powder} kg/m3 ({filler.upper()} filler), {ms} mm aggregate, slump flow {flow} mm for congested reinforcement; V-funnel 6-12 s, L-box H2/H1 >= 0.8.",
        dict(fck=grade, filler=filler, powder=powder, max_size=ms, slump_flow=flow, exposure="moderate", member="RCC", cement_grade=53), mix, sgm, [grade + 5, grade + 15],
        dict(slump_flow_mm="650-800 (SF2)", t500_s="2-5", v_funnel_s="6-12", l_box_h2_h1=">=0.80", sieve_segregation_pct="<=15", J_ring_mm="<=10"), "standard moist cure 28 d",
        "EFNARC 2005 Specification & Guidelines for SCC; Okamura & Ouchi 2003 J. Adv. Concr. Technol. 1(1); ACI 237R-07; Nan Su et al. 2001 Cem. Concr. Res. 31",
        "Coarse aggregate volume 28-35% of mix (EFNARC range 0.28-0.35 m3); sand volume ~40-50% of mortar. Trial-batch needed.",
        ["self compacting concrete", "SCC", "self consolidating concrete", "slump flow", "V funnel", "L box", "congested reinforcement", f"{filler} filler SCC"])

# ---------------- 5 3D PRINTING ----------------
n = 0
for (binder, sb, wb, scmcombo, fib) in itertools.product([700, 800, 900], [1.2, 1.5], [0.28, 0.32, 0.38], ["opc+fa+sf", "opc+ggbs", "opc+fa+metakaolin"], [0, 1.2]):
    if n >= 22: break
    if random.random() > 0.3: continue
    n += 1
    if scmcombo == "opc+fa+sf": parts_b = {"cement_kg": (binder * .7, 3.15), "fly_ash_kg": (binder * .22, 2.2), "silica_fume_kg": (binder * .08, 2.2)}
    elif scmcombo == "opc+ggbs": parts_b = {"cement_kg": (binder * .6, 3.15), "ggbs_kg": (binder * .4, 2.9)}
    else: parts_b = {"cement_kg": (binder * .65, 3.15), "fly_ash_kg": (binder * .25, 2.2), "metakaolin_kg": (binder * .10, 2.5)}
    parts = dict(parts_b); parts["water_kg"] = (binder * wb, 1.0); parts["pce_superplasticiser_kg"] = (binder * 0.008, 1.08); parts["viscosity_modifier_kg"] = (binder * 0.0015, 1.0)
    sand = binder * sb
    if fib: parts["pp_fibre_12mm_kg"] = (fib, 0.91)
    parts["sand_0_2mm_kg"] = (sand, 2.65)
    sgm = {k: s for k, (m_, s) in parts.items()}
    mix = {k: r(m_, 1) for k, (m_, s) in parts.items()}; mix["entrapped_air_pct"] = 2.0
    vc = vol_check(mix, sgm)
    # scale to close volume
    scale = 1 / vc if vc else 1
    for k in list(mix):
        if k != "entrapped_air_pct": mix[k] = r(mix[k] * scale, 1)
    mix.update({"w_b": wb, "sand_to_binder": sb, "max_particle_mm": 2})
    add("3D", "3d-printing", "S5_3d_printing", n,
        f"Design a 3D printable concrete (extrusion-based) with {scmcombo.replace('+',' + ').upper()} binder {binder} kg/m3, sand:binder {sb}:1, w/b {wb}, {'with PP fibre, ' if fib else ''}maximum particle size 2 mm; open time 40-60 min, buildable to 20+ layers.",
        dict(binder_system=scmcombo, binder=binder, sand_binder=sb, w_b=wb, max_size=2, exposure="moderate", member="RCC", fck=40), mix, sgm, [35, 70],
        dict(open_time_min="30-90", static_yield_stress_Pa="initial 0.5-2 kPa rising 0.1-0.5 kPa/min (thixotropy)", extrudability="pumpable through 20-40 mm nozzle", interlayer_bond="critical; keep layer interval < open time", shrinkage_risk="high (no coarse aggregate; use curing/wrap)"),
        "cover with plastic/curing compound immediately; wet cure 7 d",
        "Le, Austin, Lim, Buswell, Gibb, Thorpe 2012 Mater. Struct. 45 & Cem. Concr. Res. 42; Buswell et al. 2018 Cem. Concr. Res. 112; Panda & Tan 2018 Ceram. Int.; Paul et al. 2018 Virtual Phys. Prototyp. 13",
        "No coarse aggregate; rheology (thixotropy, yield stress) governs, not w/c strength law. Printer-specific tuning is always required.",
        ["3d printing concrete", "3D printed concrete", "additive manufacturing concrete", "extrusion printable mortar", "buildability", "open time", "thixotropy", "layer bonding"])

# ---------------- 6 UHPC ----------------
n = 0
for (cem, sfp, wb, fibpct, cure) in itertools.product([650, 750, 850, 950], [0.20, 0.25, 0.30], [0.16, 0.18, 0.20], [0, 1.5, 2.0], ["std", "steam90"]):
    if n >= 26: break
    if random.random() > 0.16: continue
    n += 1
    sfk = cem * sfp; qp = 200 + 15 * (n % 4); b = cem + sfk; w = b * wb
    parts = {"cement_kg": (cem, 3.15), "silica_fume_kg": (sfk, 2.2), "ground_quartz_kg": (qp, 2.65), "water_kg": (w, 1.0), "pce_hrwr_kg": (28 + 2 * (n % 4), 1.08)}
    if fibpct: parts["steel_fibre_13mm_kg"] = (fibpct / 100 * 7850, 7.85)
    sgm = {k: s for k, (m_, s) in parts.items()}; sgm["fine_aggregate_kg"] = 2.65
    mix = close(parts, 0.02, (1.0, 2.65, 2.7, False)); mix.update({"w_b": wb, "sf_to_cement": sfp, "steel_fibre_vol_pct": fibpct, "max_particle_mm": 0.6})
    base = 125 + (0.2 - wb) * -250 + 20 * (fibpct > 0) + (30 if cure == "steam90" else 0)
    lo, hi = r(base - 10, 0), r(base + 15, 0)
    add("UH", "uhpc", "S6_uhpc", n, f"Design ultra-high performance concrete (UHPC) with cement {cem} kg/m3, silica fume {int(sfp*100)}% of cement, w/b {wb}, {'steel fibre ' + str(fibpct) + '% by volume, ' if fibpct else 'no fibres, '}"
        f"{'steam/heat curing at 90 C for 48 h' if cure=='steam90' else 'standard moist curing'}; target compressive strength above 120 MPa.",
        dict(fck=int(min(100, (lo + hi) / 2)), compressive_target_MPa=int((lo + hi) / 2), w_b=wb, fibre_pct=fibpct, exposure="extreme", member="RCC", max_size=0.6, cure=cure), mix, sgm, [lo, hi],
        dict(flexural_MPa="15-45 with 2% steel fibre", elastic_modulus_GPa="45-55", chloride_diffusion="very low (<1e-13 m2/s)", flow_mm="200-260 on flow table"), "steam 90 C 48 h gives full strength within 2-4 days" if cure == "steam90" else "moist cure 28 d",
        "Richard & Cheyrezy 1995 Cem. Concr. Res. 25 (RPC); Graybeal 2006 FHWA-HRT-06-103; Yu, Spiesz, Brouwers 2014 Cem. Concr. Compos. 55; AFGC/SETRA 2013 UHPFRC Recommendations; fib Bulletin 2013 UHPFRC",
        "Particle-packing designed. Outside IS 10262 (max M80); Indian practice follows these international guides. Use only with strict QC.",
        ["UHPC", "ultra high performance concrete", "reactive powder concrete", "RPC", "UHPFRC", "ultra high strength", "Ductal type", "silica fume steel fibre"])

# ---------------- 7 ECC ----------------
n = 0
for (fac, wb, fibt, fibv, sandr) in itertools.product([1.2, 1.8, 2.2], [0.25, 0.30, 0.35], ["pva", "pe", "pp"], [1.5, 2.0], [0.36, 0.45]):
    if n >= 22: break
    if random.random() > 0.25: continue
    n += 1
    c = 500 if fac == 1.2 else 420 if fac == 1.8 else 370
    fsg = {"pva": SG["pva"], "pe": 0.97, "pp": 0.91}[fibt]; fibm = fibv / 100 * fsg * 1000
    while True:
        f = c * fac; b = c + f; w = b * wb
        if c / 3150 + f / 2200 + w / 1000 + fibv / 100 + 0.03 < 0.88: break
        c *= 0.96
    parts = {"cement_kg": (c, 3.15), "fly_ash_kg": (f, 2.2), "water_kg": (w, 1.0), "hrwr_kg": (6 + (0.35 - wb) * 20, 1.08), f"{fibt}_fibre_kg": (fibm, fsg)}
    sgm = {k: s for k, (m_, s) in parts.items()}; sgm["silica_sand_kg"] = 2.65
    mix = close(parts, 0.03, (1.0, 2.65, 2.7, False)); mix["silica_sand_kg"] = mix.pop("fine_aggregate_kg")
    mix.update({"fa_to_cement": fac, "w_b": wb, "fibre_vol_pct": fibv, "silica_sand_to_binder_target": sandr, "max_sand_mm": 0.3})
    lo = r(40 - 10 * (fac - 1.2) + (0.35 - wb) * 100 - 6, 0)
    add("EC", "ecc", "S7_ecc", n, f"Design an Engineered Cementitious Composite (ECC/SHCC) with FA/cement {fac}, w/b {wb}, {fibv}% {fibt.upper()} fibre by volume and fine silica sand; target tensile strain capacity 2-5% with multiple fine cracking.",
        dict(fa_cement=fac, w_b=wb, fibre=fibt, fibre_pct=fibv, max_size=0.3, exposure="severe", member="RCC", fck=40), mix, sgm, [max(lo, 30), max(lo, 30) + 22],
        dict(tensile_strain_capacity_pct=("2-5 (PVA M45 type)" if fibt == "pva" else "3-8 (PE) / 1-3 (PP)"), tensile_strength_MPa="4-6", crack_width_um="<100 (typically 60)", self_healing="enhanced autogenous healing from tight cracks"),
        "moist cure 28 d", "Li 2003 J. Adv. Concr. Technol. 1(3) (M45 mix: C:FA:S:W approx 1:1.2:0.8:0.53); Li et al. 2001 ACI Mater. J.; Yang et al. 2007 ACI Mater. J. 104 (high-FA ECC); Wang & Li 2007",
        "Micromechanics-tailored; fibre/matrix interface tuning (oiled PVA) is essential. Indicative only; verify strain-hardening by uniaxial tension test.",
        ["engineered cementitious composite", "ECC", "SHCC", "strain hardening cementitious composite", "bendable concrete", "PVA fibre composite", "high ductility concrete", "multiple cracking"])

# ---------------- 8 LIGHTWEIGHT ----------------
n = 0
lw = [("expanded_clay", "LECA/expanded clay", 0.95, 1.30, 1800), ("pumice", "pumice", 1.0, 1.1, 1700), ("sintered_fly_ash", "sintered fly ash aggregate", 1.5, 1.45, 1900), ("expanded_shale", "expanded shale", 1.1, 1.5, 1850), ("oil_palm_shell", "oil palm shell", 1.2, 1.2, 1950)]
for (key, desc, absn, sgl, rho), (cem, wc, sandfrac) in itertools.product(lw, [(400, 0.42, 0.9), (450, 0.38, 0.7), (380, 0.45, 1.0), (420, 0.40, 0.8)]):
    n += 1
    parts = {"cement_kg": (cem, 3.15), "water_kg": (cem * wc + 30, 1.0), "superplasticiser_kg": (3.5, 1.08)}
    sgm = {k: s for k, (m_, s) in parts.items()}; sgm.update(fine_aggregate_kg=2.65, coarse_aggregate_kg=sgl)
    mix = close(parts, 0.03, (0.36 * sandfrac / 0.9, 2.65, sgl, True))
    mix["natural_sand_kg"] = mix.pop("fine_aggregate_kg"); mix["lightweight_coarse_aggregate_kg"] = mix.pop("coarse_aggregate_kg")
    sgm["natural_sand_kg"] = 2.65; sgm["lightweight_coarse_aggregate_kg"] = sgl
    mix.update({"w_c_effective": wc, "lwa_pre_soak": "24 h saturated, surface dry or 80% pre-wet", "lwa_sg_oven_dry_assumed": sgl})
    dens = r(sum(v for k, v in mix.items() if k.endswith("_kg")) + 0, 0)
    add("LW", "lightweight", "S8_lightweight", n, f"Design structural lightweight aggregate concrete using {desc}, cement {cem} kg/m3, w/c {wc}, 12.5 mm LWA; target oven-dry density about {rho-300}-{rho} kg/m3 and 28-day strength M20-M30.",
        dict(lwa=key, cement=cem, w_c=wc, max_size=12.5, exposure="moderate", member="RCC", fck=25), mix, sgm, [18, 32],
        dict(fresh_density_kg_m3=dens, oven_dry_density_kg_m3=f"{rho-400}-{rho-150}", thermal_conductivity_W_mK="0.5-1.0", elastic_modulus_GPa="12-22"), "moist cure 7 d minimum; avoid LWA drying",
        "ACI 213R-14 Guide for Structural Lightweight-Aggregate Concrete; ACI 211.2 (LWC proportioning); Chandra & Berntsson 2002 Lightweight Aggregate Concrete (Noyes); EN 206 / Eurocode 2 Cl. 11; Neville, Properties of Concrete",
        "Absorption of LWA is a key variable (assumed values; use measured). Mixing water includes ~30 kg for LWA first-hour absorption. Verify density by trial.",
        ["lightweight concrete", "LWC", "lightweight aggregate concrete", "LECA concrete", "expanded clay aggregate", "structural lightweight", "low density concrete", f"{key.replace('_',' ')} concrete"])
# foam / aerated
for rho in [400, 600, 800, 1000, 1200, 1400, 1600]:
    n += 1
    cem = rho * 0.55 if rho < 1000 else rho * 0.30; sand = rho * 0.25 if rho < 1000 else rho * 0.55; w = cem * (0.45 if rho < 1000 else 0.50)
    tot = cem + sand + w; scale = rho / tot; cem, sand, w = cem * scale, sand * scale, w * scale
    vsolid = cem / 3150 + sand / 2650 + w / 1000
    foam = 1 - vsolid
    mix = {"cement_kg": r(cem, 0), "fine_sand_kg": r(sand, 0), "water_kg": r(w, 0), "preformed_foam_litres": r(foam * 1000, 0), "entrapped_air_pct": 0.0, "target_wet_density_kg_m3": rho}
    sgm = {"cement_kg": 3.15, "fine_sand_kg": 2.65, "water_kg": 1.0}
    mix_v = r(vsolid + foam, 3)
    add("LW", "lightweight", "S8_lightweight_foam", n, f"Design foamed (cellular) lightweight concrete of target density {rho} kg/m3 with preformed foam, cement-sand slurry, w/c {r(w/cem,2)}; for blocks, roof insulation and void filling.",
        dict(type="foam_concrete", density=rho, w_c=r(w / cem, 2), exposure="mild", member="PCC", fck=max(2, int(rho / 100 - 2))), {**mix, "volume_closure_check": mix_v},
        {**sgm}, [r(rho * 0.0035 if rho < 1000 else rho * 0.012 - 6, 1), r(rho * 0.006 if rho < 1000 else rho * 0.02 - 6, 1)],
        dict(thermal_conductivity_W_mK=r(0.08 + rho * 0.00012, 2), oven_dry_density_kg_m3=f"{int(rho*0.85)}-{int(rho*0.92)}", fresh_flow="slurry 140-180 mm flow cone"), "moist/plastic cover cure 7 d",
        "ACI 523.3R-14 Guide for Cellular Concretes; Ramamurthy, Nambiar & Ranjani 2009 Cem. Concr. Compos. 31 (classification and properties of foam concrete); Narayanan & Ramamurthy 2000 Cem. Concr. Compos. 22",
        "Strength-density relation approximate (rho 400->1-2 MPa, 1600->12-25 MPa). Foam stability and surfactant type control final density.",
        ["foam concrete", "cellular lightweight concrete", "CLC", "aerated concrete", "preformed foam", "low density concrete", "insulating concrete"])
    RECS[-1]["checks"]["absolute_volume_closed"] = abs(mix_v - 1) < 0.02; RECS[-1]["absolute_volume_sum"] = mix_v

# ---------------- 9 CO2 INJECTED ----------------
n = 0
for (grade, co2, cred, scm) in itertools.product([25, 30, 35, 40], [0.05, 0.10, 0.15, 0.30], [0, 4, 8], [0, 20]):
    if n >= 24: break
    if random.random() > 0.35: continue
    n += 1
    cem0 = {25: 330, 30: 350, 35: 380, 40: 410}[grade]; cem = cem0 * (1 - cred / 100); c = cem * (1 - scm / 100); f = cem * scm / 100; w = cem * 0.45 if grade >= 35 else cem * 0.48
    parts = {"cement_kg": (c, 3.15), "fly_ash_kg": (f, 2.2), "water_kg": (w, 1.0), "superplasticiser_kg": (cem * 0.006, 1.08)}
    sgm = {k: s for k, (m_, s) in parts.items()}; sgm.update(fine_aggregate_kg=2.65, coarse_aggregate_kg=2.7)
    mix = close(parts, 0.02, (0.36, 2.65, 2.7, True)); mix.update({"co2_injected_kg": r(cem * co2 / 100, 2), "co2_dose_pct_bwoc": co2, "cement_reduction_vs_ref_pct": cred, "w_cm": r(w / cem, 2)})
    add("CO", "co2-injected", "S9_co2_injected", n, f"Design a CO2-injected (CO2-mineralised) concrete of grade M{grade}, injecting {co2}% CO2 by mass of cement into fresh concrete during batching, with cement reduced {cred}% versus the reference mix{', and ' + str(scm) + '% fly ash' if scm else ''}.",
        dict(fck=grade, co2_pct=co2, cement_reduction_pct=cred, scm_pct=scm, max_size=20, exposure="moderate", member="RCC", slump=100), mix, sgm, [grade + 6, grade + 14],
        dict(strength_gain_vs_reference="reported 0-10% higher early/28 d strength at the same cement content for 0.05-0.15% dose", mechanism="nano-calcium carbonate (CaCO3) nucleation sites on C-S-H",
             co2_net_benefit="cement saving 3-8% -> approx 25-60 kg CO2e per m3 avoided (varies)"), "standard curing; keep slump control as CO2 slightly accelerates hydration",
        "Monkman, MacDonald, Hooton & Sandberg 2016 Cem. Concr. Compos. 74; Monkman & Shao 2006/2010 (carbonation curing); Shi et al. 2012 RILEM review of CO2 uptake; CarbonCure technical documentation",
        "Technology is proprietary equipment-dependent; dose is bwoc and reported ~0.05-0.15% in peer-reviewed tests. Cement reductions must be validated by plant trials.",
        ["CO2 injected concrete", "carbon dioxide mineralisation", "carbon utilisation concrete", "carbonated concrete", "CO2 sequestration concrete", "low carbon concrete", "carbon cured concrete"])

# ---------------- 10 SEA SAND / SEAWATER ----------------
n = 0
for (grade, sandcl, mixwater, scm, rebar) in itertools.product([25, 30, 40], [0.01, 0.03, 0.06, 0.10], ["fresh", "seawater"], ["ggbs40", "fa25", "sf8+fa20", "none"], ["frp", "stainless", "epoxy_coated", "plain_steel"]):
    if n >= 26: break
    if random.random() > 0.12: continue
    n += 1
    cem0 = {25: 360, 30: 390, 40: 440}[grade]
    cm = cem0; frac = {"ggbs40": ("ggbs_kg", 2.9, 0.4), "fa25": ("fly_ash_kg", 2.2, 0.25), "sf8+fa20": ("fa_plus_sf_kg", 2.2, 0.28), "none": ("none", 1, 0)}[scm]
    c = cm * (1 - frac[2]); f = cm * frac[2]; w = cm * (0.40 if grade == 40 else 0.43)
    parts = {"cement_kg": (c, 3.15), "water_kg": (w, 1.0), "superplasticiser_kg": (cm * 0.007, 1.08)}
    sgm = {"cement_kg": 3.15, "water_kg": 1.0, "superplasticiser_kg": 1.08, "washed_sea_sand_kg": 2.62, "coarse_aggregate_kg": 2.7}
    if f: parts[frac[0]] = (f, frac[1]); sgm[frac[0]] = frac[1]
    mix = close(parts, 0.02, (0.38, 2.62, 2.7, True))
    sand_kg = mix["fine_aggregate_kg"]; mix["washed_sea_sand_kg"] = mix.pop("fine_aggregate_kg")
    cl_sand = sand_kg * sandcl / 100; cl_water = w * (19.0 / 1000 if mixwater == "seawater" else 0.0002); cl_tot = r(cl_sand + cl_water + cm * 0.0002, 2)
    limit = {"frp": 99, "stainless": 99, "epoxy_coated": 1.2, "plain_steel": 0.6}[rebar]
    mix.update({"sea_sand_chloride_pct_by_mass": sandcl, "mixing_water": mixwater, "total_chloride_kg_per_m3_estimate": cl_tot, "is456_table7_limit_kg_m3_RCC": 0.6})
    add("SA", "sea-sand", "S10_sea_sand_seawater", n, f"Design M{grade} concrete using {'seawater mixing' if mixwater=='seawater' else 'fresh water'} and sea sand with {sandcl}% chloride by mass of sand, binder with {scm.replace('+',' + ')}, reinforced with {rebar.replace('_',' ')} bars for a coastal/marine structure; check total chloride content.",
        dict(fck=grade, sea_sand_cl_pct=sandcl, mixing_water=mixwater, scm=scm, rebar=rebar, max_size=20, exposure="very severe", member="RCC", slump=100), mix, sgm, [grade + 8, grade + 18],
        dict(chloride_check=("PASS for plain steel (<= 0.6 kg/m3)" if cl_tot <= 0.6 else ("PASS only with corrosion-resistant reinforcement (FRP/stainless)" if rebar in ("frp", "stainless") else "FAIL for steel reinforcement - wash sand / use SCM / change reinforcement")),
             early_strength="seawater slightly accelerates set; long-term strength 5-10% lower possible", durability="GGBS/FA improve chloride binding (Friedel's salt)"), "moist cure with fresh water 7 d",
        "Xiao, Qiang, Nanni, Zhang 2017 Constr. Build. Mater. 155 (sea sand & seawater concrete review); Teng et al. 2018 PolyU FRP-seawater sea-sand concrete; Dhondy, Remennikov & Shiekh 2019; IS 456:2000 Cl. 8.2.5.2 & Table 7 (chloride limits); IS 383:2016 (sand limits)",
        "Chloride is an estimate (sand + water + 0.02% in cement). IS 456 limits RCC to 0.6 kg/m3 total acid-soluble Cl; FRP/stainless allow higher. Washing or blending with river sand is standard practice.",
        ["sea sand concrete", "seawater concrete", "marine sand concrete", "sea water mixing", "chloride limit IS 456", "FRP reinforced seawater concrete", "coastal concrete", "island construction"])

# ---------------- 11 PERVIOUS ----------------
n = 0
for (ca_kg, voidp, wc, ms, fine) in itertools.product([1450, 1500, 1550], [15, 20, 25, 30], [0.28, 0.32], [10, 12.5, 20], [0, 5]):
    if n >= 26: break
    if random.random() > 0.25: continue
    n += 1
    ca_v = ca_kg / 2700; paste_v = 1 - ca_v - voidp / 100 - 0.0
    if paste_v < 0.08: continue
    fine_kg = fine / 100 * ca_kg
    paste_v_adj = paste_v - fine_kg / 2650
    k = 1 / 3.15 + wc  # volume per kg cement (m3/1000)
    cem = paste_v_adj * 1000 / k; w = cem * wc
    if not (270 <= cem <= 420): n -= 1; continue
    mix = {"cement_kg": r(cem, 0), "coarse_aggregate_kg": ca_kg, "fine_aggregate_kg": r(fine_kg, 0), "water_kg": r(w, 0), "sbr_latex_or_vma_kg": r(cem * 0.01, 1), "design_void_pct": voidp, "w_c": wc, "max_size_mm": ms}
    mixv = r(cem / 3150 + ca_kg / 2700 + fine_kg / 2650 + w / 1000 + cem * 0.01 / 1100 + voidp / 100, 3)
    perm = {15: "0.2-0.4", 20: "0.4-0.8", 25: "0.8-1.2", 30: "1.0-1.6"}[voidp]
    comp = {15: [18, 28], 20: [12, 20], 25: [8, 15], 30: [4, 10]}[voidp]
    add("PV", "pervious", "S11_pervious", n, f"Design pervious (no-fines/porous) concrete for parking and pavement with {voidp}% target void content, single-sized {ms} mm aggregate, w/c {wc}, paste-aggregate coated mix, permeability above 0.3 cm/s.",
        dict(void_pct=voidp, w_c=wc, max_size=ms, member="PCC", exposure="moderate", fck=max(10, int(sum(comp) / 2))), {**mix, "volume_closure_check": mixv}, {}, comp,
        dict(permeability_cm_s=perm, infiltration="high; ASTM C1701 field test", unit_weight_kg_m3="1600-2000", freeze_thaw="sensitive; use air entrainment/fine addition in cold climates"), "plastic sheet cover cure min 7 d (very critical; mix dries quickly)",
        "ACI 522R-10 Report on Pervious Concrete; Tennis, Leming & Akers 2004 PCA EB302 Pervious Concrete Pavements; NRMCA Pervious Concrete guide; Neithalath et al. 2010 Cem. Concr. Compos. 32; Chopra et al. 2007",
        "Design based on paste volume = 1 - aggregate absolute volume - design voids. Mix is stiff (slump 0-20 mm); trial slab and void test (ASTM C1688) required.",
        ["pervious concrete", "porous concrete", "no fines concrete", "permeable pavement", "drainage concrete", "stormwater concrete", "void content", "ground water recharge"])
    RECS[-1]["checks"]["absolute_volume_closed"] = abs(mixv - 1) < 0.02; RECS[-1]["absolute_volume_sum"] = mixv

# ---------------- 12 FIBER REINFORCED ----------------
n = 0
fibs = [("steel_hooked", "hooked-end steel fibre (60/80 aspect ratio)", [30, 40, 60, 80], 7.85), ("steel_crimped", "crimped steel fibre", [25, 40, 50], 7.85), ("pp_macro", "polypropylene macro fibre", [3, 5, 9], 0.91),
        ("pp_micro", "polypropylene micro fibre", [0.9, 1.5], 0.91), ("glass_ar", "alkali-resistant glass fibre", [3, 6], 2.6), ("basalt", "chopped basalt fibre", [3, 5, 7], 2.7), ("synthetic_hybrid", "steel + PP hybrid", [40, 60], 7.85)]
for (key, desc, doses, sgf), (grade, wc) in itertools.product(fibs, [(30, .45), (40, .40)]):
    for d in doses:
        if n >= 30: break
        n += 1
        cem = 400 if grade == 30 else 440; w = cem * wc - (4 if d > 40 else 0)
        parts = {"cement_kg": (cem, 3.15), "water_kg": (w, 1.0), "superplasticiser_kg": (cem * (0.006 + 0.00005 * d), 1.08), "fibre_kg": (d, sgf)}
        sgm = {k: s for k, (m_, s) in parts.items()}; sgm.update(fine_aggregate_kg=2.65, coarse_aggregate_kg=2.7)
        mix = close(parts, 0.02, (0.42, 2.65, 2.7, True)); mix.update({"fibre_type": key, "fibre_dose_kg_m3": d, "fibre_vol_pct": r(d / (sgf * 1000) * 100, 2), "w_c": wc, "max_size_mm": 20})
        add("FR", "fiber-reinforced", "S12_fibre_reinforced", n, f"Design fibre reinforced concrete (FRC) of grade M{grade} using {desc} at {d} kg/m3 (approx {mix['fibre_vol_pct']}% by volume), w/c {wc}, 20 mm aggregate; for industrial floors/tunnel linings/precast.",
            dict(fck=grade, fibre=key, dose=d, w_c=wc, max_size=20, exposure="moderate", member="RCC", slump=100), mix, sgm, [grade + 6, grade + 14],
            dict(flexural_toughness="residual strength fR1/fR3 per EN 14651; Re,3 per JSCE", slump_loss="10-40% vs plain mix depending on dose", crack_control="improved post-crack ductility; steel 30-60 kg/m3 typical for floors"), "standard moist curing; ensure uniform fibre dispersion (add fibres last)",
            "ACI 544.1R-96 (reapproved 2009) State-of-the-Art Report on FRC; ACI 544.4R design guide; RILEM TC 162-TDF 2003; fib Model Code 2010 (Cl. 5.6); Bentur & Mindess, Fibre Reinforced Cementitious Composites (2nd ed., 2007)",
            "Doses follow typical practice ranges; match fibre aspect ratio to maximum aggregate size and verify post-crack residual strength by 3/4-point bending test.",
            ["fibre reinforced concrete", "FRC", "steel fibre reinforced concrete", "SFRC", "polypropylene fibre concrete", "glass fibre concrete", "basalt fibre concrete", "hybrid fibre concrete"])

# ---------- keyword banks (100 per type) ----------
CORE = {
"geopolymer": "geopolymer concrete|geopolymer mix design|alkali activated concrete|alkali activated binder|alkali activated slag|AAS concrete|AAM concrete|fly ash geopolymer|GGBS geopolymer|metakaolin geopolymer|rice husk ash geopolymer|cement free concrete|zero cement concrete|green concrete|low carbon binder|sodium hydroxide molarity|NaOH 8M 10M 12M 14M 16M|sodium silicate solution|Na2SiO3 NaOH ratio|alkaline activator|alkaline liquid to binder ratio|activator modulus Ms|SiO2 Na2O ratio|heat cured geopolymer|ambient cured geopolymer|oven curing 60 C|Davidovits geopolymer|Rangan geopolymer|Hardjito Rangan|class F fly ash|low calcium fly ash|high calcium fly ash|geopolymer polymerisation|geopolysialate|N-A-S-H gel|C-A-S-H gel|potassium hydroxide activator|geopolymer strength 28 days|geopolymer setting time|geopolymer workability|geopolymer shrinkage|geopolymer acid resistance|geopolymer fire resistance|geopolymer precast|geopolymer paver|geopolymer sleeper|geopolymer sewer pipe|geopolymer bricks|IS 3812 fly ash|IS 16714 GGBS".split("|"),
"self-healing": "self healing concrete|autonomous healing|autogenous healing|crack healing concrete|bacterial concrete|bio concrete|bioconcrete|microbial induced calcite precipitation|MICP|Bacillus subtilis concrete|Bacillus pasteurii|Bacillus cohnii|calcium lactate|calcium carbonate precipitation|expanded clay carrier|bacteria spores concrete|crystalline admixture|crystalline waterproofing|Xypex|Penetron|PCC admixture|superabsorbent polymer concrete|SAP internal curing|encapsulated healing agent|polyurethane capsules|vascular network healing|shape memory polymer|sodium silicate healing|healing of cracks 0.3 mm|crack width healing|water tightness recovery|permeability recovery|wet dry cycles healing|RILEM TC 221|Jonkers|De Belie|Li Herbert healing|ECC self healing|fly ash autogenous healing|unhydrated cement healing|cementitious capillary crystalline|water retaining structures|basement waterproofing|tunnel lining healing|marine structure healing|durable concrete low maintenance|service life extension|self repairing concrete|living concrete|biological repair mortar|chloride ingress cracked concrete|corrosion protection crack".split("|"),
"self-sensing": "self sensing concrete|self monitoring concrete|smart concrete|piezoresistive concrete|electrically conductive concrete|conductive cement composite|carbon fibre concrete|short carbon fibre|CNT concrete|carbon nanotube cement|multi walled carbon nanotubes|MWCNT|carbon black cement|graphite concrete|graphene concrete|graphene oxide cement|steel fibre sensing|nickel powder concrete|fractional change in resistivity|FCR|gauge factor|four probe method|two probe method|electrical resistivity strain|percolation threshold|structural health monitoring|SHM concrete|bridge deck monitoring|damage detection concrete|stress sensing|strain sensing|crack detection concrete|weigh in motion concrete|traffic monitoring pavement|deicing conductive concrete|heating concrete|electromagnetic shielding concrete|Chung smart concrete|Han Ding Ou|dispersion CNT PCE|sonication CNT|polarisation effect|moisture effect resistivity|embedded sensor mortar|cement based sensor|piezoelectric cement|self sensing pavement|smart infrastructure|intelligent concrete|nano modified concrete|nanomaterial cement composite".split("|"),
"self-compacting": "self compacting concrete|SCC mix design|self consolidating concrete|SCC|flowable concrete|high flow concrete|slump flow test|T500 time|V funnel test|L box test|U box test|J ring test|sieve segregation|passing ability|filling ability|segregation resistance|EFNARC SCC|ACI 237R|Okamura method|Nan Su method|powder content SCC|viscosity modifying agent|VMA|PCE superplasticiser|polycarboxylate ether|limestone powder SCC|fly ash SCC|GGBS SCC|silica fume SCC|rice husk ash SCC|metakaolin SCC|congested reinforcement|dense reinforcement|thin sections|complex formwork|precast SCC|SCC columns|SCC tunnel|SCC bridge|SCC high rise|SCC pumping|formwork pressure SCC|SCC compressive strength|SCC water powder ratio|coarse aggregate volume SCC|rheology SCC|yield stress SCC|plastic viscosity|self levelling concrete|IS 10262 SCC|SCC IS 456|SCC grade M40|SCC grade M60".split("|"),
"3d-printing": "3D printing concrete|3D printed concrete|3DCP|additive manufacturing construction|digital fabrication concrete|extrusion based printing|contour crafting|printable concrete|printable mortar|buildability|extrudability|open time|pumpability printing|thixotropy|structuration rate|static yield stress|dynamic yield stress|green strength|layer height|layer interface bond|interlayer adhesion|cold joint printing|nozzle diameter|print speed|printer gantry|robotic arm printing|D-shape|binder jetting|shotcrete 3D printing|SC3DP|accelerator printing|set on demand|nano clay printing|attapulgite clay|silica fume printing|fly ash printing|limestone calcined clay printing|LC3 printing|fibre printed concrete|PP fibre printing|reinforcement in 3D printing|mesh reinforcement printing|printed house|printed bridge|IIT Madras 3D printed house|Tvasta|Le Loughborough mix|Buswell|Panda Tan|sand to binder ratio printing|printing concrete shrinkage|sustainable 3D printing|printed formwork".split("|"),
"uhpc": "UHPC|ultra high performance concrete|UHPFRC|reactive powder concrete|RPC 200|RPC 800|Ductal|CRC compact reinforced composite|ultra high strength concrete|200 MPa concrete|150 MPa concrete|120 MPa concrete|particle packing|Andreasen Andersen|modified Andreasen|dense packing|silica fume 25 percent|ground quartz powder|quartz sand 0.15 0.6 mm|steel fibre 2 percent|micro steel fibre|13 mm steel fibre|heat curing 90 C|steam curing UHPC|autoclave curing|w/b 0.16|w/b 0.2|HRWR|PCE UHPC|flow table UHPC|self consolidating UHPC|Graybeal FHWA|Richard Cheyrezy|AFGC UHPFRC|fib UHPFRC|Wille Naaman|bridge deck overlay UHPC|shear key connection UHPC|field cast joints UHPC|precast UHPC|facade panels UHPC|thin shell UHPC|blast resistant UHPC|impact resistant concrete|nuclear waste UHPC|marine UHPC|low permeability UHPC|chloride diffusion UHPC|green UHPC low cement|UHPC with GGBS|UHPC Indian practice".split("|"),
"ecc": "ECC|engineered cementitious composite|SHCC|strain hardening cementitious composite|HPFRCC|high performance fibre reinforced cementitious composite|bendable concrete|flexible concrete|ductile concrete|ductile cementitious composite|multiple cracking|strain hardening|tensile strain capacity 3 percent|PVA fibre|PVA ECC|PE fibre ECC|polyethylene fibre|polypropylene ECC|oiled PVA|fibre bridging|micromechanics|Victor Li|Li M45|ECC M45|green ECC|high volume fly ash ECC|HVFA ECC|limestone calcined clay ECC|LC3 ECC|slag ECC|crack width 60 micron|tight crack|self healing ECC|ECC link slab|ECC overlay|ECC repair|ECC retrofit|ECC beam column joint|ECC seismic|ECC shotcrete|sprayable ECC|ECC 3D printing|ECC bridge deck|ECC tensile test|uniaxial tension test|dog bone specimen|ECC silica sand|ECC superplasticiser|ECC cost|ECC durability|ECC energy absorption|ECC damage tolerance".split("|"),
"lightweight": "lightweight concrete|LWC|lightweight aggregate concrete|LWAC|structural lightweight concrete|LECA concrete|expanded clay aggregate|Leca|Lytag|sintered fly ash aggregate|expanded shale|expanded slate|pumice concrete|scoria concrete|vermiculite concrete|perlite concrete|oil palm shell concrete|OPS concrete|coconut shell concrete|EPS concrete|expanded polystyrene concrete|polystyrene beads|foam concrete|cellular lightweight concrete|CLC blocks|aerated concrete|AAC|autoclaved aerated concrete|preformed foam|foaming agent|protein foam|synthetic foam|foam density|low density concrete|insulating concrete|thermal insulation concrete|ACI 213R|ACI 211.2|oven dry density|air dry density|density 1800 kg/m3|density 600 kg/m3|LWA pre soaking|LWA absorption|water absorption of lightweight aggregate|floating concrete|roof screed|void filling|fill concrete|precast panels lightweight|dead load reduction|seismic lightweight concrete|IS 456 lightweight|IS 9142".split("|"),
"co2-injected": "CO2 injected concrete|CO2 mineralised concrete|carbon dioxide concrete|CarbonCure|carbon utilisation|CCU concrete|carbon sequestration concrete|carbon cured concrete|CO2 curing|carbonation curing|accelerated carbonation|nano calcium carbonate|CaCO3 nucleation|CO2 dose percent cement|0.1 percent CO2|CO2 dosing at batching|CO2 in ready mix|carbonated aggregates|carbonated recycled aggregate|CO2 mineral storage|low carbon concrete|net zero concrete|embodied carbon concrete|cement reduction|reduce cement content|clinker reduction|SCM and CO2|fly ash CO2 concrete|GGBS CO2 concrete|CO2 precast|CO2 masonry blocks|CO2 cured pavers|CO2 cured blocks|Solidia cement|carbon negative concrete|Monkman Shao|Monkman MacDonald Hooton|CO2 early strength|slump CO2|setting time CO2|durability CO2 concrete|EPD concrete|LCA concrete|GWP concrete|kg CO2e per m3|carbon credit concrete|green building concrete|IGBC concrete|GRIHA concrete|CO2 emission cement|decarbonising cement|ready mix CO2 technology".split("|"),
"sea-sand": "sea sand concrete|seawater concrete|sea water mixing|marine sand|ocean sand|dredged sand concrete|sea sand chloride|chloride content sand|washed sea sand|desalinated sea sand|seawater sea sand concrete|SSC|SWSSC|FRP bars seawater|GFRP reinforcement|BFRP bars|CFRP reinforcement|stainless steel rebar|epoxy coated rebar|corrosion resistant reinforcement|chloride limit IS 456|IS 456 Table 7|IS 456 clause 8.2.5|IS 383 sand|total chloride kg/m3|acid soluble chloride|water soluble chloride|shell content sand|sulphate in sea sand|island construction|Lakshadweep construction|Andaman construction|offshore concrete|coastal structure|jetty concrete|port concrete|breakwater concrete|artificial reef|seawater cement mortar|seawater curing|GGBS marine|fly ash marine concrete|silica fume marine|chloride binding|Friedel's salt|chloride diffusion|rapid chloride permeability|RCPT|NT Build 492|Xiao Nanni sea sand|Teng PolyU seawater concrete|Dhondy ocean sand".split("|"),
"pervious": "pervious concrete|porous concrete|permeable concrete|no fines concrete|previous concrete|open graded concrete|drainage concrete|permeable pavement|pervious pavement|porous pavement|stormwater management|storm water concrete|rainwater harvesting concrete|groundwater recharge|water recharge pavement|parking lot concrete|footpath concrete|cycle track concrete|green roof concrete|urban heat island|cool pavement|noise reducing pavement|void content|porosity 20 percent|permeability cm/s|coefficient of permeability|ASTM C1701|ASTM C1688|ACI 522R|ACI 522.1|NRMCA pervious|single sized aggregate|10 mm aggregate pervious|paste volume|aggregate cement ratio|w/c 0.3 pervious|SBR latex pervious|clogging pervious|maintenance vacuum sweeping|freeze thaw pervious|raveling resistance|pervious compressive strength|pervious flexural strength|pervious concrete India|IRC permeable|SUDS|sustainable urban drainage|LID low impact development|tree pit concrete|pervious concrete with fly ash|pervious concrete recycled aggregate|pervious concrete mix proportions".split("|"),
"fiber-reinforced": "fibre reinforced concrete|fiber reinforced concrete|FRC|SFRC|steel fibre reinforced concrete|steel fiber concrete|hooked end steel fibre|crimped steel fibre|Dramix|polypropylene fibre concrete|PPFRC|macro synthetic fibre|micro synthetic fibre|glass fibre reinforced concrete|GFRC|AR glass fibre|basalt fibre concrete|BFRC|carbon fibre concrete|natural fibre concrete|jute fibre concrete|coir fibre concrete|sisal fibre|hybrid fibre concrete|fibre volume fraction|fibre aspect ratio|fibre dosage kg/m3|fibre balling|fibre dispersion|workability fibre concrete|slump loss fibres|residual flexural strength|toughness index|ASTM C1609|EN 14651|JSCE SF4|RILEM TC 162-TDF|ACI 544|fib Model Code fibre|Bentur Mindess|industrial floors fibre|slab on grade fibre|tunnel lining fibre|shotcrete fibre|precast segments fibre|pavement fibre|crack control fibre|plastic shrinkage cracking fibre|fire spalling polypropylene|impact resistance fibre|blast resistant fibre concrete|IS 456 fibre|IS 10262 fibre".split("|"),
}
# long-tail templated expansion to ensure >=100 unique per type
APPS = ["bridge", "building", "pavement", "precast", "marine structure", "industrial floor", "foundation", "retaining wall", "dam repair", "tunnel", "residential", "high rise", "road", "canal lining", "water tank"]
QRY = ["mix design", "mix proportions per m3", "compressive strength", "durability", "cost", "India", "IS code", "example problem", "calculation", "kg per cubic metre", "trial mix", "literature review", "case study", "advantages and disadvantages", "water cement ratio", "curing", "workability", "sustainability", "research paper", "design procedure"]
KEYWORDS = {}
for t, core in CORE.items():
    seen = []; label = {"geopolymer": "geopolymer concrete", "self-healing": "self healing concrete", "self-sensing": "self sensing concrete", "self-compacting": "self compacting concrete", "3d-printing": "3D printed concrete", "uhpc": "UHPC",
        "ecc": "ECC", "lightweight": "lightweight concrete", "co2-injected": "CO2 injected concrete", "sea-sand": "sea sand concrete", "pervious": "pervious concrete", "fiber-reinforced": "fibre reinforced concrete"}[t]
    for k in core:
        if k.lower() not in [s.lower() for s in seen]: seen.append(k)
    for q in QRY:
        seen.append(f"{label} {q}")
    i = 0
    while len(seen) < 100: seen.append(f"{label} for {APPS[i % len(APPS)]}"); i += 1
    KEYWORDS[t] = seen[:100] if len(seen) >= 100 else seen
    # ensure uniqueness
    u = []; [u.append(x) for x in KEYWORDS[t] if x.lower() not in [y.lower() for y in u]]
    j = 0
    while len(u) < 100: u.append(f"{label} {APPS[j % len(APPS)]} {QRY[(j * 3) % len(QRY)]}"); j += 1
    KEYWORDS[t] = u[:100]

# attach per-record keyword subsets (type bank sampled) so retrieval text is rich but not noisy
for rec in RECS:
    bank = KEYWORDS[rec["concrete_type"]]
    rec["keywords"] = list(dict.fromkeys(rec["keywords"] + random.sample(bank, 12)))
    rec["retrieval_text"] += " " + " ".join(rec["keywords"])

with open("/home/claude/out/special_concrete_mixes.jsonl", "w", encoding="utf-8") as f:
    for r_ in RECS: f.write(json.dumps(r_, ensure_ascii=False) + "\n")
json.dump(KEYWORDS, open("/home/claude/out/keyword_banks.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
with open("/home/claude/out/keywords_all.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["concrete_type", "keyword"]); [w.writerow([t, k]) for t, ks in KEYWORDS.items() for k in ks]
with open("/home/claude/out/special_mix_summary.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["id", "concrete_type", "group", "strength_lo_MPa", "strength_hi_MPa", "abs_volume_sum", "volume_ok", "verification_status", "source"])
    for r_ in RECS: w.writerow([r_["id"], r_["concrete_type"], r_["group"], *r_["indicative_28d_compressive_MPa"], r_["absolute_volume_sum"], r_["checks"]["absolute_volume_closed"], r_["verification_status"], r_["source"]])
from collections import Counter
print(len(RECS), Counter(r_["concrete_type"] for r_ in RECS))
print({t: len(v) for t, v in KEYWORDS.items()})
bad = [r_["id"] for r_ in RECS if not r_["checks"]["absolute_volume_closed"]]
print("volume not closed:", bad)
