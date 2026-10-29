# Sources used to anchor the special-concrete dataset

Every record in `special_concrete_mixes.jsonl` carries its own `source` field. Proportions are LITERATURE-ANCHORED REPRESENTATIVE MIXES
(typical dose/ratio ranges + absolute-volume closure at 1 m3), NOT copies of one lab's test results.
`verification_status = "literature_based_unverified"` on all records. Promote to "verified" only after you check the cited paper/standard.

| Type | Primary references |
|---|---|
| Geopolymer | Hardjito & Rangan (2005) *Development and properties of low-calcium fly ash-based geopolymer concrete*, Curtin Univ. Research Report GC1; Rangan (2008); Davidovits (2008) *Geopolymer Chemistry and Applications*; Provis & van Deventer (eds.) RILEM TC 224-AAM (2014); plus 128 research papers (10,726 chunks ingested in SQLite RAG database) covering Fly Ash Class F & C, GGBS / Slag (AAS), Metakaolin, Silica Fume, Rice Husk Ash, Red Mud, Solid anhydrous activators (one-part), KOH/K2SiO3 systems, fiber reinforcement (steel, PP, PVA, basalt), and sustainable aggregates (RCA, M-Sand). |
| Self-healing | De Belie et al. (2018) Adv. Mater. Interfaces 5(17); Jonkers et al. (2010) Ecol. Eng. 36; Ferrara et al. (2018) Constr. Build. Mater. 167; Snoeck & De Belie (2015); RILEM TC 221-SHC |
| Self-sensing | Chung (2000, 2002); Han, Ding, Ou et al. (2015) Sensors 15; Ou & Han (2009); D'Alessandro et al. (2016) |
| Self-compacting | EFNARC (2005) SCC Specification & Guidelines; Okamura & Ouchi (2003) J. Adv. Concr. Technol. 1(1); ACI 237R-07; Nan Su et al. (2001) Cem. Concr. Res. 31 |
| 3D printing | Le et al. (2012) Mater. Struct. 45 / Cem. Concr. Res. 42; Buswell et al. (2018) Cem. Concr. Res. 112; Panda & Tan (2018); Paul et al. (2018) |
| UHPC | Richard & Cheyrezy (1995) Cem. Concr. Res. 25; Graybeal (2006) FHWA-HRT-06-103; Yu, Spiesz & Brouwers (2014) Cem. Concr. Compos. 55; AFGC/SETRA (2013); fib (2013) UHPFRC |
| ECC | Li (2003) J. Adv. Concr. Technol. 1(3); Li et al. (2001) ACI Mater. J.; Yang et al. (2007) ACI Mater. J. 104; Wang & Li (2007) |
| Lightweight | ACI 213R-14; ACI 211.2; ACI 523.3R-14 (cellular); Chandra & Berntsson (2002); Ramamurthy et al. (2009) Cem. Concr. Compos. 31; Narayanan & Ramamurthy (2000) |
| CO2-injected | Monkman, MacDonald, Hooton & Sandberg (2016) Cem. Concr. Compos. 74; Monkman & Shao (2006/2010); Shi et al. (2012); CarbonCure technical docs |
| Sea sand / seawater | Xiao, Qiang, Nanni & Zhang (2017) Constr. Build. Mater. 155; Teng et al. (2018, PolyU); Dhondy et al. (2019); IS 456:2000 Cl. 8.2.5 & Table 7; IS 383:2016 |
| Pervious | ACI 522R-10; Tennis, Leming & Akers (2004) PCA EB302; NRMCA guide; Neithalath et al. (2010) Cem. Concr. Compos. 32 |
| Fibre reinforced | ACI 544.1R-96; ACI 544.4R; RILEM TC 162-TDF (2003); fib Model Code 2010; Bentur & Mindess (2007) |

## Known limits (be honest in your viva / report)
* I had no internet access in the build sandbox, so I did NOT re-fetch these papers; values come from well-known published ranges and recipes.
  Before presenting, spot-check 3-5 mixes per type against the cited paper.
* Strength values are indicative ranges (+/-15%), not measurements.
* NaOH solids per kg solution (8M=262, 10M=314, 12M=361, 14M=404, 16M=444 g/kg) follow Hardjito & Rangan; Na2SiO3 composition SiO2 29.4 / Na2O 14.7 / H2O 55.9 %.
* Self-sensing, 3D printing, CO2-injected and self-healing values are the least standardised in the literature -> treat as "typical research recipes".
