"""Type schemas defining the single source of truth for all concrete types in ConcreteMix AI.

Each concrete type (conventional + 12 special concrete types) has an explicit schema.
Fields specify:
- key: field identifier
- label: human-readable form label
- kind: 'number' | 'select' | 'toggle' | 'text'
- unit: measurement unit if applicable
- default: recommended baseline value
- min: minimum boundary
- max: maximum boundary
- step: input increment step
- options: list of options for 'select' kinds
- help: tooltip/guidance text
- source_key: mapping to the reference dataset inputs or mix_per_m3
"""

from typing import Dict, List, Any, Optional

TYPE_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "conventional": {
        "name": "Conventional Concrete",
        "standard": "IS 10262:2019 & IS 456:2000",
        "description": "Standard hydraulic Portland cement concrete with optional SCMs (Fly Ash, GGBS, Silica Fume).",
        "disclaimer_required": False,
        "fields": [
            {
                "key": "fck",
                "label": "Characteristic Strength (fck)",
                "kind": "select",
                "unit": "MPa",
                "default": 30,
                "options": [
                    {"value": 15, "label": "M15 (Lean / Bedding)"},
                    {"value": 20, "label": "M20 (PCC / Light RCC)"},
                    {"value": 25, "label": "M25 (General RCC)"},
                    {"value": 30, "label": "M30 (Standard Frame)"},
                    {"value": 35, "label": "M35 (Commercial)"},
                    {"value": 40, "label": "M40 (Heavy Infrastructure)"},
                    {"value": 45, "label": "M45 (Bridges / Flyovers)"},
                    {"value": 50, "label": "M50 (Prestressed Girders)"},
                    {"value": 55, "label": "M55 (High Early Strength)"},
                    {"value": 60, "label": "M60 (High Strength Columns)"},
                ],
                "help": "28-day characteristic compressive cube strength in N/mm².",
                "source_key": "fck"
            },
            {
                "key": "exposure",
                "label": "Exposure Condition",
                "kind": "select",
                "default": "moderate",
                "options": [
                    {"value": "mild", "label": "Mild (Interior / Dry)"},
                    {"value": "moderate", "label": "Moderate (Sheltered / Normal Soil)"},
                    {"value": "severe", "label": "Severe (Coastal / Wetting & Drying)"},
                    {"value": "very severe", "label": "Very Severe (Sea Spray / De-icing)"},
                    {"value": "extreme", "label": "Extreme (Tidal Splash / Offshore)"},
                ],
                "help": "Environmental durability classification per IS 456:2000 Table 3.",
                "source_key": "exposure"
            },
            {
                "key": "member",
                "label": "Member Construction",
                "kind": "select",
                "default": "RCC",
                "options": [
                    {"value": "RCC", "label": "RCC (Reinforced Concrete)"},
                    {"value": "PCC", "label": "PCC (Plain Concrete)"},
                ],
                "help": "Governs Table 5 minimum binder and maximum w/c limits.",
                "source_key": "member"
            },
            {
                "key": "max_size",
                "label": "Max Nominal Aggregate Size",
                "kind": "select",
                "unit": "mm",
                "default": 20,
                "options": [
                    {"value": 20, "label": "20 mm (Standard Structural)"},
                    {"value": 10, "label": "10 mm (Congested / Thin Sections)"},
                    {"value": 40, "label": "40 mm (Mass Concrete / Rafts)"},
                ],
                "help": "Governs base mixing water content in IS 10262 Table 3.",
                "source_key": "max_size"
            },
            {
                "key": "slump",
                "label": "Target Workability (Slump)",
                "kind": "number",
                "unit": "mm",
                "default": 100,
                "min": 25,
                "max": 200,
                "step": 25,
                "help": "Slump at placement. Base water is for 50 mm (+3% per 25 mm extra slump).",
                "source_key": "slump"
            },
            {
                "key": "zone",
                "label": "Fine Aggregate Grading Zone",
                "kind": "select",
                "default": "II",
                "options": [
                    {"value": "II", "label": "Zone II (Standard River Sand)"},
                    {"value": "I", "label": "Zone I (Coarser Sand)"},
                    {"value": "III", "label": "Zone III (Finer Sand)"},
                    {"value": "IV", "label": "Zone IV (Very Fine Sand)"},
                ],
                "help": "Sand grading zone per IS 383 Table 4. Governs coarse aggregate volume fraction.",
                "source_key": "zone"
            },
            {
                "key": "cement_grade",
                "label": "Cement Type & Grade",
                "kind": "select",
                "default": 43,
                "options": [
                    {"value": 43, "label": "OPC 43 Grade (IS 269 Standard)"},
                    {"value": 53, "label": "OPC 53 Grade (IS 269 High Early)"},
                    {"value": 33, "label": "OPC 33 Grade (IS 269 Mass Concrete)"},
                    {"value": "PPC", "label": "PPC - Portland Pozzolana Cement (IS 1489, SG 3.00)"},
                    {"value": "PSC", "label": "PSC - Portland Slag Cement (IS 455, SG 3.00)"},
                ],
                "help": "Used to select strength vs w/c relationship from IS 10262 Figure 1 and cement specific gravity.",
                "source_key": "cement_grade"
            },
            {
                "key": "placement",
                "label": "Placement Method",
                "kind": "select",
                "default": "chute",
                "options": [
                    {"value": "chute", "label": "Chute / Skip / Tremie"},
                    {"value": "pump", "label": "Pumping (Applies 10% coarse aggregate reduction)"},
                ],
                "help": "Pumped concrete requires a 10% reduction in coarse aggregate volume.",
                "source_key": "placement"
            },
            {
                "key": "supervision",
                "label": "Degree of Supervision",
                "kind": "select",
                "default": "good",
                "options": [
                    {"value": "good", "label": "Good (Quality Control / Lab Testing)"},
                    {"value": "fair", "label": "Fair (Site Mixing)"},
                ],
                "help": "Controls assumed standard deviation s and margin factor X in Clause 4.2.",
                "source_key": "supervision"
            },
            {
                "key": "agg_type",
                "label": "Coarse Aggregate Shape",
                "kind": "select",
                "default": "angular",
                "options": [
                    {"value": "angular", "label": "Crushed Angular (Basalt/Granite Metal)"},
                    {"value": "subangular", "label": "Sub-angular / Semi-crushed"},
                    {"value": "gravel", "label": "Rounded River Gravel (-15 to -20 kg water)"},
                ],
                "help": "Rounded gravel reduces baseline mixing water requirement.",
                "source_key": "agg_type"
            },
            {
                "key": "scm_fly_ash_pct",
                "label": "Fly Ash Replacement",
                "kind": "number",
                "unit": "%",
                "default": 0,
                "min": 0,
                "max": 35,
                "step": 5,
                "help": "Class F fly ash percentage of total cementitious material.",
                "source_key": "scm_fa"
            },
            {
                "key": "scm_ggbs_pct",
                "label": "GGBS Replacement",
                "kind": "number",
                "unit": "%",
                "default": 0,
                "min": 0,
                "max": 60,
                "step": 5,
                "help": "Ground Granulated Blast Furnace Slag percentage.",
                "source_key": "scm_ggbs"
            },
            {
                "key": "scm_sf_pct",
                "label": "Silica Fume Replacement",
                "kind": "number",
                "unit": "%",
                "default": 0,
                "min": 0,
                "max": 15,
                "step": 1,
                "help": "Condensed micro-silica fume percentage.",
                "source_key": "scm_sf"
            },
            {
                "key": "sp_pct",
                "label": "Superplasticiser Dosage",
                "kind": "number",
                "unit": "%",
                "default": 0.8,
                "min": 0,
                "max": 2.5,
                "step": 0.1,
                "help": "PCE superplasticiser dosage by mass of cementitious material.",
                "source_key": "sp_pct"
            },
            {
                "key": "sp_wr",
                "label": "Chemical Water Reduction",
                "kind": "number",
                "unit": "%",
                "default": 20,
                "min": 0,
                "max": 35,
                "step": 1,
                "help": "Target water reduction achieved by PCE chemical admixture.",
                "source_key": "sp_wr"
            }
        ]
    },

        "geopolymer": {
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

    "self-healing": {
        "name": "Self-Healing Concrete",
        "standard": "RILEM TC 221-SHC / Jonkers & De Belie",
        "description": "Autogenous or autonomous crack-closing concrete via bacteria, crystalline agents, or capsules.",
        "disclaimer_required": True,
        "fields": [
            {
                "key": "healing_mechanism",
                "label": "Healing Mechanism",
                "kind": "select",
                "default": "bacterial",
                "options": [
                    {"value": "bacterial", "label": "Bacterial Spores (Bacillus + Calcium Lactate)"},
                    {"value": "crystalline", "label": "Hydrophilic Crystalline Admixture (PRAH)"},
                    {"value": "sap", "label": "Superabsorbent Polymers (SAP Hydrogel)"},
                    {"value": "capsule", "label": "Microencapsulated Healing Agent (Sodium Silicate)"},
                    {"value": "autogenous", "label": "Autogenous Hydration Promotion (High SCM)"},
                ],
                "help": "Primary chemical or biological agent closing crack widths up to 0.4 mm.",
                "source_key": "mechanism"
            },
            {
                "key": "w_cm",
                "label": "Water-Binder Ratio (w/cm)",
                "kind": "number",
                "unit": "ratio",
                "default": 0.45,
                "min": 0.38,
                "max": 0.50,
                "step": 0.01,
                "help": "Free water to cementitious material ratio.",
                "source_key": "w_cm"
            },
            {
                "key": "fly_ash_pct",
                "label": "Fly Ash Content",
                "kind": "number",
                "unit": "%",
                "default": 15,
                "min": 0,
                "max": 25,
                "step": 5,
                "help": "Provides unhydrated core particles for prolonged secondary autogenous healing.",
                "source_key": "fly_ash_pct"
            },
            {
                "key": "grade",
                "label": "Strength Grade",
                "kind": "select",
                "unit": "MPa",
                "default": "M30",
                "options": [
                    {"value": "M25", "label": "M25 (Foundations & Retaining Walls)"},
                    {"value": "M30", "label": "M30 (Standard Water Tanks / Basements)"},
                    {"value": "M35", "label": "M35 (Water Retaining Infrastructure)"},
                    {"value": "M40", "label": "M40 (Tunnels & Heavy Civil)"},
                ],
                "help": "Target strength class of the baseline concrete matrix.",
                "source_key": "grade"
            },
            {
                "key": "max_size",
                "label": "Max Aggregate Size",
                "kind": "select",
                "unit": "mm",
                "default": 20,
                "options": [
                    {"value": 20, "label": "20 mm Crushed Stone"},
                    {"value": 10, "label": "10 mm"},
                ],
                "help": "Nominal maximum aggregate size.",
                "source_key": "max_size"
            },
            {
                "key": "exposure",
                "label": "Durability Exposure",
                "kind": "select",
                "default": "severe",
                "options": [
                    {"value": "moderate", "label": "Moderate"},
                    {"value": "severe", "label": "Severe (Water Retaining / Underground)"},
                    {"value": "extreme", "label": "Extreme (Marine / Aggressive Chemical)"},
                ],
                "help": "Exposure condition.",
                "source_key": "exposure"
            }
        ]
    },

    "self-sensing": {
        "name": "Self-Sensing Smart Concrete",
        "standard": "Chung / Han, Ding & Ou",
        "description": "Electrically conductive piezoresistive composite for continuous structural health monitoring.",
        "disclaimer_required": True,
        "fields": [
            {
                "key": "conductive_filler",
                "label": "Conductive Functional Filler",
                "kind": "select",
                "default": "carbon_nanotubes",
                "options": [
                    {"value": "carbon_nanotubes", "label": "Carbon Nanotubes (MWCNT)"},
                    {"value": "carbon_fibre", "label": "Chopped Carbon Fibres (Short)"},
                    {"value": "carbon_black", "label": "Conductive Carbon Black"},
                    {"value": "nickel_powder", "label": "Nickel Nanoparticles"},
                    {"value": "graphite", "label": "Graphene / Graphite Nanoplatelets"},
                    {"value": "hybrid", "label": "Hybrid (CNT + Carbon Fibre)"},
                ],
                "help": "Percolation threshold phase creating conductive paths across the matrix.",
                "source_key": "filler_type"
            },
            {
                "key": "filler_dose_pct",
                "label": "Filler Dose (% bwoc)",
                "kind": "number",
                "unit": "%",
                "default": 0.5,
                "min": 0.05,
                "max": 2.0,
                "step": 0.05,
                "help": "Percentage by weight of cement (bwoc). Close to electrical percolation threshold.",
                "source_key": "filler_dose_pct"
            },
            {
                "key": "w_b",
                "label": "Water-Binder Ratio (w/b)",
                "kind": "number",
                "unit": "ratio",
                "default": 0.38,
                "min": 0.35,
                "max": 0.42,
                "step": 0.01,
                "help": "Dense matrix ensures stable piezoresistive gauge factor.",
                "source_key": "w_b"
            },
            {
                "key": "max_size",
                "label": "Max Aggregate Size",
                "kind": "select",
                "unit": "mm",
                "default": 10,
                "options": [
                    {"value": 10, "label": "10 mm (Standard Sensing Mortar / Concrete)"},
                    {"value": 4.75, "label": "Sand Mortar (No Coarse Aggregate)"},
                ],
                "help": "Fine matrix minimizes aggregate interference on electrical percolation.",
                "source_key": "max_size"
            },
            {
                "key": "measurement_mode",
                "label": "Sensing Application",
                "kind": "select",
                "default": "strain_monitoring",
                "options": [
                    {"value": "strain_monitoring", "label": "Dynamic Strain & Vibration Monitoring"},
                    {"value": "traffic_sensing", "label": "Weigh-in-Motion / Vehicle Detection"},
                    {"value": "damage_cracking", "label": "Damage Localization & Crack Detection"},
                ],
                "help": "Governs expected piezoresistive gauge factor sensitivity.",
                "source_key": "application"
            }
        ]
    },

    "self-compacting": {
        "name": "Self-Compacting Concrete (SCC)",
        "standard": "EFNARC Guidelines / Okamura & Ouchi",
        "description": "Highly flowable, non-segregating concrete consolidating under self-weight without vibration.",
        "disclaimer_required": True,
        "fields": [
            {
                "key": "grade",
                "label": "Compressive Grade",
                "kind": "select",
                "unit": "MPa",
                "default": "M40",
                "options": [
                    {"value": "M25", "label": "M25 (Foundations)"},
                    {"value": "M30", "label": "M30 (Beams / Slabs)"},
                    {"value": "M40", "label": "M40 (Congested Columns / Walls)"},
                    {"value": "M50", "label": "M50 (Precast Elements)"},
                    {"value": "M60", "label": "M60 (High-Rise Cores)"},
                ],
                "help": "Target compressive strength class.",
                "source_key": "grade"
            },
            {
                "key": "filler_type",
                "label": "Mineral Filler Phase",
                "kind": "select",
                "default": "fly_ash",
                "options": [
                    {"value": "fly_ash", "label": "Class F Fly Ash (Spherical Rheology)"},
                    {"value": "ggbs", "label": "GGBS (Micro-Filler Density)"},
                    {"value": "limestone", "label": "Limestone Powder (< 63 µm)"},
                ],
                "help": "Increases paste volume and lubrication without raising hydration heat.",
                "source_key": "filler_type"
            },
            {
                "key": "powder_content",
                "label": "Powder Content (< 0.125 mm)",
                "kind": "number",
                "unit": "kg/m³",
                "default": 550,
                "min": 480,
                "max": 600,
                "step": 10,
                "help": "Total fines (cement + mineral fillers) providing viscosity and stopping segregation.",
                "source_key": "powder_content_kg"
            },
            {
                "key": "max_size",
                "label": "Max Aggregate Size",
                "kind": "select",
                "unit": "mm",
                "default": 16,
                "options": [
                    {"value": 16, "label": "16 mm (Standard SCC)"},
                    {"value": 12.5, "label": "12.5 mm (Dense Reinforcement)"},
                    {"value": 10, "label": "10 mm (Ultra-Congested Formwork)"},
                ],
                "help": "Smaller aggregate sizes prevent blocking between tight rebar cages.",
                "source_key": "max_size"
            },
            {
                "key": "slump_flow",
                "label": "Slump Flow Target",
                "kind": "number",
                "unit": "mm",
                "default": 680,
                "min": 650,
                "max": 800,
                "step": 10,
                "help": "Spread diameter on flow table per EFNARC (SF1: 550-650, SF2: 660-750, SF3: 760-850).",
                "source_key": "slump_flow_mm"
            },
            {
                "key": "member",
                "label": "Placement Situation",
                "kind": "select",
                "default": "congested_column",
                "options": [
                    {"value": "congested_column", "label": "Congested Vertical Column / Core Wall"},
                    {"value": "complex_formwork", "label": "Architectural / Intricate Formwork"},
                    {"value": "slab_floor", "label": "Flat Self-Leveling Slab Floor"},
                ],
                "help": "Structural element geometry.",
                "source_key": "member"
            }
        ]
    },

    "3d-printing": {
        "name": "3D-Printing Concrete (3DCP)",
        "standard": "Le et al. / Buswell et al. (Digital Fabrication)",
        "description": "Extrudable, thixotropic printable mortar with shape retention and layer buildability.",
        "disclaimer_required": True,
        "fields": [
            {
                "key": "binder_system",
                "label": "Binder Formulation",
                "kind": "select",
                "default": "opc_fa_sf",
                "options": [
                    {"value": "opc_fa_sf", "label": "OPC + Fly Ash + Silica Fume (Thixotropic)"},
                    {"value": "opc_ggbs", "label": "OPC + GGBS (Controlled Setting)"},
                    {"value": "opc_fa_mk", "label": "OPC + Fly Ash + Metakaolin (High Early Yield)"},
                ],
                "help": "Binder matrix tuned for early structural build-up rate without slumping.",
                "source_key": "binder_system"
            },
            {
                "key": "binder_content",
                "label": "Total Binder Content",
                "kind": "number",
                "unit": "kg/m³",
                "default": 800,
                "min": 700,
                "max": 900,
                "step": 20,
                "help": "High binder paste provides pumpability and lubrication in hose lines.",
                "source_key": "binder_kg"
            },
            {
                "key": "sand_to_binder_ratio",
                "label": "Sand : Binder Ratio",
                "kind": "number",
                "unit": "ratio",
                "default": 1.3,
                "min": 1.2,
                "max": 1.5,
                "step": 0.05,
                "help": "Mass ratio of fine graded sand (Dmax < 2mm) to binder powder.",
                "source_key": "sand_to_binder"
            },
            {
                "key": "w_b",
                "label": "Water-Binder Ratio (w/b)",
                "kind": "number",
                "unit": "ratio",
                "default": 0.32,
                "min": 0.28,
                "max": 0.38,
                "step": 0.01,
                "help": "Carefully controlled to maintain extrudability and avoid filament deformation.",
                "source_key": "w_b"
            },
            {
                "key": "pp_fiber",
                "label": "PP Micro-Fibers (Plastic Shrinkage)",
                "kind": "toggle",
                "default": True,
                "help": "Polypropylene micro-fibers (1-2 kg/m³) prevent early tensile tearing between layers.",
                "source_key": "pp_fiber"
            }
        ]
    },

    "uhpc": {
        "name": "Ultra-High Performance Concrete (UHPC)",
        "standard": "Richard & Cheyrezy / FHWA-HRT-06-103",
        "description": "150–200 MPa dense particle-packed matrix with steel micro-fibers and zero coarse aggregate.",
        "disclaimer_required": True,
        "fields": [
            {
                "key": "target_strength",
                "label": "Target Compressive Strength",
                "kind": "number",
                "unit": "MPa",
                "default": 150,
                "min": 105,
                "max": 190,
                "step": 5,
                "help": "28-day target cube/cylinder compressive strength.",
                "source_key": "target_strength"
            },
            {
                "key": "cement_content",
                "label": "Cement Dosage",
                "kind": "number",
                "unit": "kg/m³",
                "default": 750,
                "min": 650,
                "max": 950,
                "step": 25,
                "help": "High-fineness OPC 53 grade cement.",
                "source_key": "cement_kg"
            },
            {
                "key": "silica_fume_pct",
                "label": "Silica Fume (% of Cement)",
                "kind": "number",
                "unit": "%",
                "default": 25,
                "min": 20,
                "max": 30,
                "step": 1,
                "help": "Ultra-fine silica fume packs between cement grains and creates secondary C-S-H.",
                "source_key": "sf_pct"
            },
            {
                "key": "w_b",
                "label": "Water-Binder Ratio (w/b)",
                "kind": "number",
                "unit": "ratio",
                "default": 0.18,
                "min": 0.16,
                "max": 0.20,
                "step": 0.01,
                "help": "Extremely low w/b enabled by 3rd-generation PCE superplasticisers.",
                "source_key": "w_b"
            },
            {
                "key": "steel_fiber_vol_pct",
                "label": "Steel Micro-Fiber Dosage",
                "kind": "select",
                "unit": "vol %",
                "default": 2.0,
                "options": [
                    {"value": 2.0, "label": "2.0 vol % (~157 kg/m³ — Standard UHPC)"},
                    {"value": 1.5, "label": "1.5 vol % (~118 kg/m³ — Moderate Ductility)"},
                    {"value": 0.0, "label": "0.0 vol % (Dense Reactive Powder Mortar)"},
                ],
                "help": "Brass-coated high-tensile straight micro steel fibers (13/0.2 mm).",
                "source_key": "steel_fiber_vol_pct"
            },
            {
                "key": "curing",
                "label": "Curing Regime",
                "kind": "select",
                "default": "standard",
                "options": [
                    {"value": "standard", "label": "Standard Moist / Water Curing (20–25 °C)"},
                    {"value": "steam_90c", "label": "Accelerated Steam Heat Curing (90 °C for 48h)"},
                ],
                "help": "Steam curing at 90 °C accelerates pozzolanic reactions to reach >180 MPa in 4 days.",
                "source_key": "curing"
            }
        ]
    },

    "ecc": {
        "name": "Engineered Cementitious Composites (Bendable ECC)",
        "standard": "Victor Li (Univ. of Michigan) / RILEM SHCC",
        "description": "High-ductility fiber-reinforced mortar exhibiting 3–5% tensile strain capacity with micro-cracking.",
        "disclaimer_required": True,
        "fields": [
            {
                "key": "fa_to_cement_ratio",
                "label": "Fly Ash / Cement Ratio (FA/C)",
                "kind": "number",
                "unit": "ratio",
                "default": 2.0,
                "min": 1.2,
                "max": 2.2,
                "step": 0.1,
                "help": "High fly ash content tailors matrix toughness for steady-state crack bridging.",
                "source_key": "fa_to_cement"
            },
            {
                "key": "w_b",
                "label": "Water-Binder Ratio (w/b)",
                "kind": "number",
                "unit": "ratio",
                "default": 0.28,
                "min": 0.25,
                "max": 0.35,
                "step": 0.01,
                "help": "Low water content ensures dense interfacial bond with micro-fibers.",
                "source_key": "w_b"
            },
            {
                "key": "fiber_type",
                "label": "Reinforcing Micro-Fiber",
                "kind": "select",
                "default": "pva",
                "options": [
                    {"value": "pva", "label": "Oil-Coated PVA Micro-Fibers (Kuraray REC15)"},
                    {"value": "pe", "label": "High Tenacity Polyethylene (UHMWPE)"},
                    {"value": "pp", "label": "Polypropylene Micro-Fibers"},
                ],
                "help": "PVA fibers have chemical bond to cement; oil coating prevents rupture.",
                "source_key": "fiber_type"
            },
            {
                "key": "fiber_vol_pct",
                "label": "Fiber Volume Fraction",
                "kind": "number",
                "unit": "vol %",
                "default": 2.0,
                "min": 1.5,
                "max": 2.0,
                "step": 0.1,
                "help": "Standard ECC employs 2.0 vol % (~26 kg/m³ PVA) for pseudo strain-hardening.",
                "source_key": "fiber_vol_pct"
            }
        ]
    },

    "lightweight": {
        "name": "Lightweight / Cellular Concrete",
        "standard": "ACI 213R-14 / ACI 523.3R-14",
        "description": "Low-density structural or insulation concrete using expanded aggregates or pre-formed foam.",
        "disclaimer_required": True,
        "fields": [
            {
                "key": "variant",
                "label": "Lightweight Variant",
                "kind": "select",
                "default": "lwa_structural",
                "options": [
                    {"value": "lwa_structural", "label": "Structural Lightweight Aggregate (LWA)"},
                    {"value": "foam_cellular", "label": "Cellular Foamed Concrete (CLC)"},
                ],
                "help": "LWA is load-bearing; Cellular foam is thermal/acoustic insulation.",
                "source_key": "variant"
            },
            {
                "key": "lwa_type",
                "label": "Lightweight Aggregate Type",
                "kind": "select",
                "default": "expanded_clay",
                "options": [
                    {"value": "expanded_clay", "label": "Expanded Clay (LECA)"},
                    {"value": "pumice", "label": "Natural Pumice / Scoria"},
                    {"value": "sintered_fa", "label": "Sintered Fly Ash Pellet Aggregate"},
                    {"value": "expanded_shale", "label": "Expanded Shale / Slate"},
                    {"value": "oil_palm", "label": "Oil Palm Shell (Bio-Aggregate)"},
                ],
                "help": "Porous coarse aggregate phase.",
                "source_key": "lwa_type"
            },
            {
                "key": "cement_content",
                "label": "Cement Dosage",
                "kind": "number",
                "unit": "kg/m³",
                "default": 400,
                "min": 300,
                "max": 500,
                "step": 10,
                "help": "Cement content in paste phase.",
                "source_key": "cement_kg"
            },
            {
                "key": "w_c",
                "label": "Water-Cement Ratio (w/c)",
                "kind": "number",
                "unit": "ratio",
                "default": 0.40,
                "min": 0.35,
                "max": 0.50,
                "step": 0.01,
                "help": "Free water ratio excluding aggregate absorption compensation.",
                "source_key": "w_c"
            },
            {
                "key": "target_density",
                "label": "Target Oven-Dry Density",
                "kind": "number",
                "unit": "kg/m³",
                "default": 1600,
                "min": 400,
                "max": 1800,
                "step": 50,
                "help": "Structural LWA: 1400-1800 kg/m³. Foam concrete: 400-1200 kg/m³.",
                "source_key": "target_density"
            },
            {
                "key": "max_size",
                "label": "Max Lightweight Aggregate Size",
                "kind": "select",
                "unit": "mm",
                "default": 12.5,
                "options": [
                    {"value": 12.5, "label": "12.5 mm LECA / Pellet"},
                    {"value": 10, "label": "10 mm"},
                    {"value": 8, "label": "8 mm"},
                ],
                "help": "Smaller lightweight aggregate sizes offer higher particle crushing strength.",
                "source_key": "max_size"
            }
        ]
    },

    "co2-injected": {
        "name": "CO2-Injected / Mineralised Concrete",
        "standard": "CarbonCure / Monkman et al. (CCU Technology)",
        "description": "Permanent carbon dioxide mineralization during batching producing nano-calcium carbonate.",
        "disclaimer_required": True,
        "fields": [
            {
                "key": "grade",
                "label": "Baseline Grade",
                "kind": "select",
                "unit": "MPa",
                "default": "M30",
                "options": [
                    {"value": "M25", "label": "M25"},
                    {"value": "M30", "label": "M30 (Ready-Mix Benchmark)"},
                    {"value": "M35", "label": "M35"},
                    {"value": "M40", "label": "M40"},
                ],
                "help": "Target compressive strength class.",
                "source_key": "grade"
            },
            {
                "key": "co2_dose_pct",
                "label": "CO2 Dosing (% bwoc)",
                "kind": "number",
                "unit": "%",
                "default": 0.15,
                "min": 0.05,
                "max": 0.30,
                "step": 0.01,
                "help": "Liquid/gaseous CO2 injected into the drum during batching (% by weight of cement).",
                "source_key": "co2_dose_pct"
            },
            {
                "key": "cement_reduction_pct",
                "label": "Cement Clinker Reduction",
                "kind": "number",
                "unit": "%",
                "default": 5,
                "min": 0,
                "max": 8,
                "step": 1,
                "help": "Mineralization creates nano-CaCO3 seed crystals, allowing 5–8% cement reduction.",
                "source_key": "cement_reduction_pct"
            },
            {
                "key": "fly_ash_pct",
                "label": "Fly Ash Replacement",
                "kind": "select",
                "unit": "%",
                "default": 20,
                "options": [
                    {"value": 20, "label": "20% Fly Ash Blend"},
                    {"value": 0, "label": "0% (100% OPC Base)"},
                ],
                "help": "Supplementary fly ash blend.",
                "source_key": "fly_ash_pct"
            },
            {
                "key": "max_size",
                "label": "Max Aggregate Size",
                "kind": "select",
                "unit": "mm",
                "default": 20,
                "options": [
                    {"value": 20, "label": "20 mm Standard"},
                    {"value": 10, "label": "10 mm"},
                ],
                "help": "Maximum nominal coarse aggregate size.",
                "source_key": "max_size"
            }
        ]
    },

    "sea-sand": {
        "name": "Sea-Sand & Seawater Concrete (SS-SWC)",
        "standard": "Xiao & Teng / IS 456 Table 7 Durability Mandates",
        "description": "Marine dredged aggregate and seawater concrete paired exclusively with non-corrosive reinforcement.",
        "disclaimer_required": True,
        "fields": [
            {
                "key": "grade",
                "label": "Matrix Strength Grade",
                "kind": "select",
                "unit": "MPa",
                "default": "M35",
                "options": [
                    {"value": "M25", "label": "M25"},
                    {"value": "M30", "label": "M30"},
                    {"value": "M35", "label": "M35 (Marine Coastal Structure)"},
                    {"value": "M40", "label": "M40 (Island Infrastructure)"},
                ],
                "help": "Target characteristic strength.",
                "source_key": "grade"
            },
            {
                "key": "chloride_pct",
                "label": "Sea-Sand Chloride Content",
                "kind": "number",
                "unit": "%",
                "default": 0.05,
                "min": 0.01,
                "max": 0.10,
                "step": 0.01,
                "help": "Water-soluble chloride content by mass of sea-sand.",
                "source_key": "chloride_pct"
            },
            {
                "key": "mixing_water",
                "label": "Mixing Water Type",
                "kind": "select",
                "default": "seawater",
                "options": [
                    {"value": "seawater", "label": "Direct Seawater (TDS ~35,000 ppm)"},
                    {"value": "freshwater", "label": "Desalinated / Potable Freshwater"},
                ],
                "help": "Direct seawater mixing eliminates freshwater scarcity in island environments.",
                "source_key": "mixing_water"
            },
            {
                "key": "scm_type",
                "label": "SCM Chloride Binding Phase",
                "kind": "select",
                "default": "ggbs_40",
                "options": [
                    {"value": "ggbs_40", "label": "GGBS 40% (Forms Friedel's Salt to bind Cl-)"},
                    {"value": "fa_25", "label": "Fly Ash 25%"},
                    {"value": "sf8_fa20", "label": "Ternary: 8% Silica Fume + 20% Fly Ash"},
                    {"value": "none", "label": "None (100% OPC)"},
                ],
                "help": "Aluminate-rich SCMs chemically bind free chloride ions into calcium chloroaluminate.",
                "source_key": "scm_system"
            },
            {
                "key": "rebar_type",
                "label": "Reinforcement Type (MANDATORY)",
                "kind": "select",
                "default": "frp",
                "options": [
                    {"value": "frp", "label": "FRP Rebar (GFRP / BFRP / CFRP — Non-corrosive)"},
                    {"value": "stainless", "label": "Austenitic Stainless Steel Rebar"},
                    {"value": "epoxy", "label": "Epoxy-Coated Rebar (Strict monitoring)"},
                    {"value": "plain_steel", "label": "Plain Carbon Steel (PROHIBITED by IS 456 Table 7)"},
                ],
                "help": "Plain steel rebar experiences rapid pitting corrosion from chloride ions.",
                "source_key": "rebar_type"
            }
        ]
    },

    "pervious": {
        "name": "Pervious Concrete Pavement",
        "standard": "ACI 522R-10 / NRMCA Guidelines",
        "description": "Zero-fines porous concrete with interconnected voids for stormwater drainage and percolation.",
        "disclaimer_required": True,
        "fields": [
            {
                "key": "design_void_pct",
                "label": "Design Air Void Ratio",
                "kind": "number",
                "unit": "%",
                "default": 20,
                "min": 15,
                "max": 30,
                "step": 1,
                "help": "Interconnected void percentage ensuring hydraulic drainage (> 0.3 cm/s permeability).",
                "source_key": "void_ratio_pct"
            },
            {
                "key": "w_c",
                "label": "Water-Cement Ratio (w/c)",
                "kind": "number",
                "unit": "ratio",
                "default": 0.30,
                "min": 0.28,
                "max": 0.32,
                "step": 0.01,
                "help": "Strictly bounded: <0.28 causes paste friability; >0.32 causes paste to drain and seal bottom.",
                "source_key": "w_c"
            },
            {
                "key": "max_size",
                "label": "Coarse Aggregate Nominal Size",
                "kind": "select",
                "unit": "mm",
                "default": 10,
                "options": [
                    {"value": 10, "label": "10 mm Single-Sized (Optimum Voids & Texture)"},
                    {"value": 12.5, "label": "12.5 mm Single-Sized"},
                    {"value": 20, "label": "20 mm Single-Sized (High Percolation)"},
                ],
                "help": "Narrowly graded single-sized crushed rock without sand fines.",
                "source_key": "max_size"
            },
            {
                "key": "fine_aggregate_pct",
                "label": "Sand Addition (% of Aggregate)",
                "kind": "select",
                "unit": "%",
                "default": 0,
                "options": [
                    {"value": 0, "label": "0% (Zero Fines — Maximum Permeability)"},
                    {"value": 5, "label": "5% Sand (Enhanced Abrasion & Ravelling Resistance)"},
                ],
                "help": "Small fine aggregate additions (5%) enhance durability at slight void cost.",
                "source_key": "fine_aggregate_pct"
            }
        ]
    },

    "fiber-reinforced": {
        "name": "Fibre-Reinforced Concrete (FRC)",
        "standard": "ACI 544.1R / fib Model Code 2010",
        "description": "Discrete structural or micro fibers controlling plastic shrinkage cracking and post-crack ductility.",
        "disclaimer_required": True,
        "fields": [
            {
                "key": "fiber_type",
                "label": "Fiber Reinforcement Type",
                "kind": "select",
                "default": "steel_hooked",
                "options": [
                    {"value": "steel_hooked", "label": "Hooked-End Steel Fibers (DRAMIX 3D)"},
                    {"value": "steel_crimped", "label": "Crimped Steel Fibers"},
                    {"value": "pp_macro", "label": "Structural Polypropylene Macro-Fibers"},
                    {"value": "pp_micro", "label": "Polypropylene Micro-Fibers (Anti-crack)"},
                    {"value": "glass_ar", "label": "Alkali-Resistant AR Glass Fibers (GFRC)"},
                    {"value": "basalt", "label": "Basalt Fibers (High Thermal / Chemical)"},
                    {"value": "hybrid", "label": "Hybrid (Steel Hooked + PP Micro)"},
                ],
                "help": "Fiber material and geometry determining post-crack residual toughness class.",
                "source_key": "fiber_type"
            },
            {
                "key": "fiber_dose",
                "label": "Fiber Dosage",
                "kind": "number",
                "unit": "kg/m³",
                "default": 35,
                "min": 1,
                "max": 80,
                "step": 5,
                "help": "Typical ranges: Steel 25-60 kg/m³; Synthetic macro 4-8 kg/m³; Micro PP 0.9-2 kg/m³.",
                "source_key": "fiber_dose_kg"
            },
            {
                "key": "grade",
                "label": "Matrix Strength Grade",
                "kind": "select",
                "unit": "MPa",
                "default": "M35",
                "options": [
                    {"value": "M30", "label": "M30 (Industrial Pavement)"},
                    {"value": "M35", "label": "M35 (Heavy Duty Flooring)"},
                    {"value": "M40", "label": "M40 (Tunnel Shotcrete Lining)"},
                    {"value": "M50", "label": "M50 (Precast Segmental Lining)"},
                ],
                "help": "Characteristic compressive strength of base matrix.",
                "source_key": "grade"
            },
            {
                "key": "w_c",
                "label": "Water-Cement Ratio (w/c)",
                "kind": "number",
                "unit": "ratio",
                "default": 0.42,
                "min": 0.35,
                "max": 0.50,
                "step": 0.01,
                "help": "Matrix w/c ratio. Superplasticiser is added to maintain workability.",
                "source_key": "w_c"
            }
        ]
    }
}


def get_type_schema(concrete_type: str) -> Optional[Dict[str, Any]]:
    """Retrieve the explicit single-source-of-truth schema for a given concrete type."""
    norm = (concrete_type or "conventional").lower().replace("_", "-")
    return TYPE_SCHEMAS.get(norm, TYPE_SCHEMAS["conventional"])


def list_type_schemas() -> Dict[str, Dict[str, Any]]:
    """Return all type schemas."""
    return TYPE_SCHEMAS
