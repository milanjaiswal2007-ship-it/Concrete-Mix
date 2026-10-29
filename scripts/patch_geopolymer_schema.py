"""Patch the geopolymer schema in type_schemas.py with expanded PnC fields."""
import re

with open('app/engine/type_schemas.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find bounds
geo_start = content.find('"geopolymer": {')
self_healing_start = content.find('"self-healing": {')

old_block = content[geo_start:self_healing_start]

NEW_GEOPOLYMER = '''    "geopolymer": {
        "name": "Geopolymer Concrete",
        "standard": "RILEM TC 224-AAM / Curtin GC1 (Hardjito & Rangan 2005) + 128 Research Papers",
        "description": "Zero-clinker alkali-activated aluminosilicate binder. Covers FA, GGBS, Metakaolin, Ternary blends, KOH activator, One-Part, Fiber-Reinforced and Recycled-Aggregate geopolymer systems — 195 literature-anchored PnC mixes from 128 papers.",
        "disclaimer_required": True,
        "fields": [
            {
                "key": "binder_system",
                "label": "Precursor Binder System",
                "kind": "select",
                "default": "fly_ash_ggbs",
                "options": [
                    {"value": "fly_ash_ggbs", "label": "Fly Ash (Class F) + GGBS Blend — Ambient Cured"},
                    {"value": "fly_ash_only", "label": "100% Fly Ash (Class F) — Heat Cured"},
                    {"value": "slag_rich", "label": "100% GGBS (Alkali-Activated Slag — AAS)"},
                    {"value": "metakaolin", "label": "Metakaolin-based (Davidovits classic)"},
                    {"value": "fa_metakaolin", "label": "Fly Ash + Metakaolin Blend"},
                    {"value": "ternary_fa_ggbs_sf", "label": "Ternary: FA + GGBS + Silica Fume"},
                    {"value": "ternary_fa_ggbs_rha", "label": "Ternary: FA + GGBS + Rice Husk Ash"},
                    {"value": "fa_red_mud", "label": "FA + GGBS + Red Mud (Waste Valorisation)"},
                    {"value": "one_part_dry", "label": "One-Part Dry-Mix (Just Add Water)"},
                ],
                "help": "Select the aluminosilicate precursor source. Determines reaction products (N-A-S-H, C-A-S-H gels), curing needs, and strength development.",
                "source_key": "binder_system"
            },
            {
                "key": "activator_system",
                "label": "Activator System",
                "kind": "select",
                "default": "naoh_na2sio3",
                "options": [
                    {"value": "naoh_na2sio3", "label": "NaOH + Na2SiO3 (Sodium Silicate — Standard)"},
                    {"value": "koh_k2sio3", "label": "KOH + K2SiO3 (Potassium — Fire Resistant >800C)"},
                    {"value": "solid_metasilicate", "label": "Solid Anhydrous Na-Metasilicate (One-Part)"},
                ],
                "help": "Potassium activator gives superior thermal stability up to 800 C. Sodium is cost-effective and widely researched.",
                "source_key": "activator_system"
            },
            {
                "key": "ggbs_pct",
                "label": "GGBS / Slag Share in Binder",
                "kind": "number",
                "unit": "%",
                "default": 30,
                "min": 0,
                "max": 100,
                "step": 5,
                "help": "0% = pure fly ash (heat cure needed). 15-50% enables ambient curing. 100% = AAS (high early strength, add borax retarder).",
                "source_key": "ggbs_pct"
            },
            {
                "key": "naoh_molarity",
                "label": "Alkali Hydroxide Molarity (NaOH or KOH)",
                "kind": "number",
                "unit": "M",
                "default": 12,
                "min": 6,
                "max": 16,
                "step": 1,
                "help": "Governs strength development. 8-10M = moderate; 12-14M = high strength; 16M = maximum dissolution. Higher molarity = higher viscosity.",
                "source_key": "NaOH_molarity"
            },
            {
                "key": "silicate_to_hydroxide_ratio",
                "label": "Silicate / Hydroxide Mass Ratio (ss/sh)",
                "kind": "number",
                "unit": "ratio",
                "default": 2.5,
                "min": 1.0,
                "max": 3.0,
                "step": 0.5,
                "help": "Higher ratio = more Si in activator -> denser N-A-S-H gel -> higher strength. Optimum 2.0-2.5.",
                "source_key": "Na2SiO3_to_NaOH_ratio"
            },
            {
                "key": "alkaline_liquid_to_binder",
                "label": "Alkaline Liquid / Binder Ratio",
                "kind": "number",
                "unit": "ratio",
                "default": 0.38,
                "min": 0.30,
                "max": 0.50,
                "step": 0.01,
                "help": "Total alkaline solution mass / precursor binder mass. Lower = denser paste but stiffer. Typical: 0.35-0.45.",
                "source_key": "alk_binder"
            },
            {
                "key": "curing",
                "label": "Curing Regime",
                "kind": "select",
                "default": "ambient",
                "options": [
                    {"value": "ambient", "label": "Ambient Room Temperature (23-28 C) — Sealed"},
                    {"value": "heat_60c", "label": "Heat Cured at 60 C for 24 h (after 24 h rest)"},
                    {"value": "heat_75c", "label": "Heat Cured at 75 C for 24 h (elevated temp)"},
                    {"value": "heat_90c", "label": "Heat Cured at 90 C for 24 h (high strength FA)"},
                    {"value": "water_cured", "label": "Water / Moist Immersion Curing (AAS)"},
                ],
                "help": "Pure FA needs thermal activation (>=60 C). GGBS-blended mixes develop strength at ambient. AAS benefits from water curing.",
                "source_key": "curing"
            },
            {
                "key": "fiber_type",
                "label": "Fibre Reinforcement (Optional)",
                "kind": "select",
                "default": "none",
                "options": [
                    {"value": "none", "label": "No Fibres (Plain Geopolymer)"},
                    {"value": "steel", "label": "Hooked-End Steel Fibres (1.0 vol%) — Ductile"},
                    {"value": "steel_low", "label": "Steel Fibres (0.5 vol%) — Crack Control"},
                    {"value": "pp", "label": "Polypropylene Micro-Fibres (0.3 vol%) — Fire Safe"},
                    {"value": "pva", "label": "PVA Fibres (1.5 vol%) — Strain-Hardening EGC"},
                    {"value": "basalt", "label": "Chopped Basalt Fibres (0.75 vol%) — Durable"},
                ],
                "help": "Fibres transform brittle geopolymer to ductile composite. PVA gives strain-hardening EGC. PP fibres prevent fire spalling.",
                "source_key": "fiber_type"
            },
            {
                "key": "aggregate_type",
                "label": "Aggregate System",
                "kind": "select",
                "default": "natural",
                "options": [
                    {"value": "natural", "label": "Natural River Sand + Crushed Granite (Standard)"},
                    {"value": "msand_100", "label": "100% Manufactured Sand (M-Sand) + Granite"},
                    {"value": "rca_50", "label": "50% Recycled Concrete Aggregate (RCA)"},
                    {"value": "rca_100", "label": "100% Recycled Concrete Aggregate (RCA) — Sustainable"},
                ],
                "help": "Geopolymer binder activates old mortar on RCA surfaces, reducing the strength penalty seen with OPC+RCA.",
                "source_key": "aggregate_type"
            },
            {
                "key": "max_size",
                "label": "Max Coarse Aggregate Size",
                "kind": "select",
                "unit": "mm",
                "default": 20,
                "options": [
                    {"value": 20, "label": "20 mm Crushed Stone"},
                    {"value": 14, "label": "14 mm"},
                    {"value": 10, "label": "10 mm (Fine-grained / MK mixes)"},
                ],
                "help": "Maximum nominal coarse aggregate size.",
                "source_key": "max_size"
            },
            {
                "key": "target_strength",
                "label": "Indicative Target Strength",
                "kind": "number",
                "unit": "MPa",
                "default": 40,
                "min": 20,
                "max": 90,
                "step": 5,
                "help": "Expected 28-day compressive strength. Governed by molarity, Si/Al ratio and curing — NOT by w/c law.",
                "source_key": "target_strength"
            },
            {
                "key": "exposure",
                "label": "Exposure / Durability Class",
                "kind": "select",
                "default": "moderate",
                "options": [
                    {"value": "moderate", "label": "Moderate — General Structures"},
                    {"value": "severe", "label": "Severe — Marine / Chemical / Fire (>600 C) Resistance"},
                    {"value": "very severe", "label": "Very Severe — Tidal / Aggressive Soils"},
                ],
                "help": "Geopolymers show exceptional resistance to sulphate, chloride, acid and elevated temperature vs OPC concrete.",
                "source_key": "exposure"
            },
            {
                "key": "member",
                "label": "Structural Member / Application",
                "kind": "select",
                "default": "RCC",
                "options": [
                    {"value": "RCC", "label": "RCC Column / Beam / Slab"},
                    {"value": "precast", "label": "Precast Element / Paver / Pipe / Sleeper"},
                    {"value": "industrial", "label": "Industrial Floor / Acid-Resistant Lining"},
                ],
                "help": "Application type influences curing method and durability requirements.",
                "source_key": "member"
            }
        ]
    },

    '''

new_content = content[:geo_start] + NEW_GEOPOLYMER + content[self_healing_start:]

with open('app/engine/type_schemas.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Patched type_schemas.py successfully!")
print(f"Old geopolymer block length: {len(old_block)}")
print(f"New geopolymer block length: {len(NEW_GEOPOLYMER)}")
