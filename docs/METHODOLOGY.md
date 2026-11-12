# CT69.A1.Reparations: Methodology, sources, assumptions

Status: first full pass, 2026-11-12. All numbers come from `python scripts/run_all.py`; see `data/processed/`.

**Scope.** This values the *labor* of enslaved people in what became the United States, 1619–1865, as a clinical economic quantity. It does **not** value the harm of enslavement, lost freedom, violence, family separation, or post-1865 discrimination. Every figure is a model output under stated assumptions, not a measurement. The interest-rate assumption dominates everything else (§5).

---

## 1. Questions and headline answers

| # | Question | Answer (source / method) | Confidence |
|---|---|---|---|
| 1a | Africans embarked on ships bound for mainland North America | **472,381** (SlaveVoyages *Estimates*, 1501–1866) | Medium. These are imputed estimates; ±10–15% is plausible. |
| 1b | Died in transit (Middle Passage) | **83,638** (17.7%), embarked minus disembarked. Documented voyages alone: 16.1% (n = 1,756) | Medium. Excludes deaths before embarkation and after landing. |
| 1c | Landed and sold | **388,743** landed directly from Africa. Practically all were sold on arrival. Add roughly **50,000** reshipped from the Caribbean 1701–75 (O'Malley 2014, as summarized in Klooster's review; partial period). | Medium. The Caribbean figure is partial and secondary. |
| 1d | Domestic (interstate) sales 1790–1860 | About **1 million** forced interstate relocations. This is a widely repeated secondary figure, **not verified here** (see Wikipedia "Slavery in the United States", citing Morgan 2002). | Low. It is a secondary citation. |
| 2a | Enslaved people (and descendants) who lived 1619–1865 | **About 10 million** (Hacker 2020). This model counts **181.2 million person-years** of enslavement and **117.8 million worker-years** (at 65% participation). | Census years are high quality. Colonial years are estimates. |
| 2b | Where | By state (`data/processed/enslaved_population_by_state_year.csv`). The largest are VA, SC, NC, GA, MD, AL, MS, KY, TN, LA. | High for 1790–1860 (US Census). |
| 2c | What work (1850 snapshot) | Of 3.20M enslaved in 1850: cotton 1.815M, tobacco 350k, sugar 150k, rice 125k, hemp 60k, cities and towns about 400k, other or unassigned about 304k. These are people **of all ages** (De Bow, *Statistical View*, p. 94, quoted in Evans 1962). | Low–medium. De Bow does not give his basis. |
| 3 | Present value of the labor | **$0.75T** undiscounted (constant 2025 $). **$5.0T at 1% real**, **$37.5T at 2%**, **$332T at 3%** (full table in §5). | The *method* is defensible. The *rate* is a value judgment. |
| 4 | Land it would buy | Buyable non-federal land in the 48 contiguous states is worth about **$7.1T** at USDA 2025 farm prices. At **1% real**, the labor value is 71% of that. In the "state where the labor was done" mode, the 10 main slave states are bought out completely. At **≥1.5% real**, the value exceeds all buyable land in the 48 states. | Medium. The land prices are farm prices, which undervalue urban land (§6). |
| 5 | Lives lost at sea (separate) | 83,638 deaths × US DOT value of a statistical life $14.2M = **$1.19T**. Alternative, forgone labor: $0.12T at 1%, $27T at 3%. | A value judgment. Reported separately and never added to item 3. |

---

## 2. Data sources (all in `data/raw/`, SHA-256 in `data/raw/MANIFEST.json`)

| Source | What it gives | File / access |
|---|---|---|
| **SlaveVoyages, Trans-Atlantic Slave Trade Database, *Estimates*** (Eltis, Richardson et al.; legacy.slavevoyages.org/assessment/estimates). Retrieved 2026-11-12. | Embarked and disembarked by decade for 5 mainland North America regions | `data/manual/slavevoyages_estimates_mainland_na_by_decade.csv` (copied from the web form: all flags, 10-year rows, specific disembarkation regions) |
| SlaveVoyages voyage-level export `tastdb-exp-2019.csv` | Cross-check of documented voyages (MJSELIMP1 = 20000, mainland North America) | fetched by `00_fetch.py` |
| **US Census Bureau, *Historical Statistics of the US, Colonial Times to 1970*, Series Z 1–19**, p. 1168 | "Negro" population by colony, 1630–1780 | Scanned PDF. Hand-transcribed to `data/manual/hsus_colonial_Z1-19_negro_population.csv`. **Every column sums exactly to the printed total.** |
| **US Census 1790–1860** slave population by state (primary: 1850 Census, *Statistical View* ch. V; 1860 *Population* volume, introduction) | Enslaved people by state and census year | The Wikipedia table transcribing these (revision 1382810880) is parsed. The 1860 total of 3,953,760 matches the census. |
| **MeasuringWorth**: Officer & Williamson, *Annual Wages in the United States, 1774–Present*; Williamson, *The Annual CPI for the US, 1774–Present* | Index of unskilled labor costs (1860 = 100, 1774–1940); production-worker hourly pay ($, 1790–); CPI (1982–84 = 100) | `mw_uswage.html`, `mw_uscpi.html` |
| **USDA NASS, *Land Values 2025 Summary*** (Aug 2025) | Farm real estate $/acre by state, 2025 (48 states; no AK or HI) | `land0825.txt` |
| **USDA NASS, *2022 Census of Agriculture*, Vol. 1, US/State, Table 45** | Land in farms by the operation's legal status for tax purposes, by state | `coa2022_usv1.txt` |
| **Congressional Research Service, R42346, *Federal Land Ownership: Overview and Data*, Table 1** | Total and federal acreage by state, as of 2024-09-30 (five agencies) | `crs_R42346_federal_land_ownership.html` |
| **US DOT, *Departmental Guidance on Valuation of a Statistical Life*** | VSL = $14.2M for 2025 analyses | value in `scripts/params.json` (from the DOT guidance page) |
| us-atlas 3.0.1 (Census cartographic boundaries 1:10m, Albers USA) | State outlines for the map | `us-atlas_states-albers-10m.json` |

Literature used for checks and context: Craemer, T. (2015), "Estimating Slavery Reparations: Present Value Comparisons of Historical Multigenerational Reparations Policies," *Social Science Quarterly* 96(2): 639–655. Hacker, J. D. (2020), "From '20. and odd' to 10 million: the growth of the slave population in the United States," *Slavery & Abolition* 41(4): 840–855. Evans, R. (1962), "The Economics of American Negro Slavery," in *Aspects of Labor Economics*, NBER, pp. 185–256. O'Malley, G. (2014), *Final Passages: The Intercolonial Slave Trade of British America, 1619–1807*.

---

## 3. Method

**Labor value.** For state *s* and year *y*:

```
V(s,y) = Enslaved(s,y) × participation × hours/yr × w_real(y) × wage_multiplier × (1 − maintenance_share)
PV(r)  = Σ_s Σ_y V(s,y) × (1 + r)^(2025 − y)
```

* `Enslaved(s,y)` combines colonial estimates for 1630–1780 and census counts for 1790–1860, linearly interpolated year by year. Virginia is set to 20 for 1619–1620. 1861–1865 holds the 1860 count.
* `w_real(y)` is the hourly wage of unskilled free labor, in 2025 dollars. MeasuringWorth's unskilled-labor index is converted to dollars per hour using the average ratio of production-worker pay to the index over 1850–1870 (k = $0.000777 per index point, which gives **$0.078/hr nominal in 1860**). It is then deflated with MeasuringWorth's CPI. Before 1774 there is no series, so the 1774 real wage is held constant.
* The result: **1860 real wage ≈ $3.11/hr (2025 $)**, or about $9,300 a year at 3,000 hours.
* `r` is a **real** (inflation-adjusted) rate, because the values are already in constant dollars.

**Validation against the literature.** Rebuilding Craemer's construction with these inputs (1776–1865, nominal wages compounded at 3% to 2009) gives **$3.9T**, against his published **$5.9–14.2T**. Same order of magnitude, a little lower, consistent with this model's lower wage and participation assumptions. Note that a 3% *nominal* rate on nominal wages is roughly a 1.5% *real* rate. That is why the "real 3%" result here ($332T) is so much larger than Craemer's.

**Land purchase** (per state, value V to spend):
1. **Purchasable land** = non-federal acres (CRS) split into four tiers, bought in this order:
   1. Non-family corporate farmland
   2. Partnerships and family-held corporations
   3. Family or individual farms
   4. Other non-federal land: non-federal acres minus land in farms. This includes state, municipal, urban and forest land.
2. **Excluded:** federal land, and farmland under "Other: estate or trust, prison farm, grazing association, American Indian Reservation", so tribal land is never "bought".
3. **Price:** USDA 2025 farm real estate $/acre for every tier (§6). The cost is acres bought × price. Value beyond the state's purchasable land is reported as **unspent**.
4. **Two allocation modes:**
   * *State where the labor was done*: each state's share of the present value buys land in that state.
   * *All states, same share*: the national present value buys the same fraction of every contiguous state's purchasable land.

**Lives lost (item 5).** Deaths = embarked − disembarked, by decade. Two separate methods:
* (a) Deaths × VSL. The VSL is already a present-day value, so it is not compounded.
* (b) Forgone labor: each person who died is credited with 30 years of the same hourly labor value from the decade's midpoint, capped at 1865, and compounded at r.

Neither is added to the labor total, and descendants who were never born are not counted.

---

## 4. Assumptions (all live in `scripts/params.json`)

| ID | Assumption | Value | Why / range tested |
|---|---|---|---|
| A1 | Share of the enslaved population doing productive labor | 0.65 | Excludes young children and the very old. Band 0.55–0.75. Not taken from a single source. |
| A2 | Hours per worker per year | 3,000 | Roughly 10–11 h × 280–300 days. Band 2,500–3,500. An assumption, not a sourced figure. |
| A3 | 1861–1865 population | held at 1860 | War-time emancipation was gradual; this slightly overstates 1863–65. |
| A4 | Wage benchmark | unskilled free labor (MeasuringWorth) × 1.0 | Skilled, domestic and artisan work would be worth more; field labor in the South was often paid less. |
| A5 | Pre-1774 wage | held at the 1774 real level | No US series exists. Matters a lot at high rates, because early years compound longest. |
| A6 | Maintenance deduction | 0% | The brief values the labor itself. Setting it to, e.g., 0.3–0.5 scales every result proportionally. |
| A7 | Colonial "Negro" population = enslaved | upper bound | Includes a small free Black population before 1780. |
| A8 | Colonial-to-state mapping | colony → modern state | Kentucky and Tennessee are taken from their own HSUS rows. Maine 1790–1820 is 0 (reported under Massachusetts). |
| A9 | Farmland withheld by USDA "(D)" | the residual (land in farms minus disclosed categories) split in proportion to US shares | Affects AK, NH, RI (flagged in the data and the tooltips). |
| A10 | Land price | 2025 farm real estate $/acre (includes buildings) for all purchasable land | See §6. |
| A11 | Base year | 2025 (latest full year of CPI) | — |
| A12 | Census "All States" 1790 = 694,207 excludes the Southwest Territory (Tennessee, 3,417); this model includes it | +3,417 | — |

---

## 5. Sensitivity to the interest rate (the dominant assumption)

Present value of the labor, in 2025 dollars. The band varies A1 and A2 together.

| Real rate | PV of labor | Band | ÷ buyable land in the 48 states ($7.1T) |
|---|---|---|---|
| 0% | $0.75T | $0.53–1.01T | 11% |
| 0.5% | $1.93T | $1.36–2.60T | 27% |
| 1% | $5.05T | $3.56–6.79T | 71% |
| 1.5% | $13.5T | $9.5–18.2T | 1.9× |
| 2% | $37.5T | $26.4–50.5T | 5.3× |
| 2.5% | $109T | $77–146T | 15× |
| 3% | $332T | $234–447T | 47× |
| 4% | $3,795T | — | 537× |
| 5% | $57,816T | — | 8,182× |
| 6% | $1.12 quintillion | — | 158,498× |

Each extra point of real interest multiplies the result by about 7× (at low rates) up to about 20× (at high rates). That is because labor from 1700 compounds for 325 years.

**Which rate is defensible?**
* Long-run real returns on safe assets (government debt) have historically been around 0–3%.
* Real equity returns have been around 5–7%. Applying them over 200–400 years produces sums far larger than all the world's wealth. That is a property of compounding, not a finding.
* **This project does not pick a single rate.** It shows the whole range. The visualization defaults to 3% only because Craemer's widely cited work uses 3% (nominal).

---

## 6. Known limitations, stated plainly

1. **Land prices.** USDA prices *farm* real estate. Urban and suburban land costs far more per acre, so "% of state land" is overstated where land is urban, and the cost is understated. There is no consistent statewide market price for all land types. The FHFA/AEI county land-value data cover residential land only.
2. **Corporate vs family farms.** The Census of Agriculture classifies *operations*, not *owners*. About 39% of farmland is rented, often from non-operator landlords, including investors and trusts. "Non-family corporations" hold only **16.6M of 880M farm acres (1.9%)** nationally. So "take from corporations first" runs out almost immediately, and most of the purchase falls on family-run operations and other land. USDA's only owner-level survey (TOTAL, 2014) is outdated.
3. **Sectors.** The crop split is a national 1850 snapshot of people of all ages, with no stated basis. It is not a state-by-state or year-by-year allocation of labor value. A better version would use 1860 Census of Agriculture crop output by county.
4. **Colonial counts** are HSUS estimates (decennial, rounded), not censuses.
5. **Middle Passage** figures cover deaths on board only. Deaths during capture, overland marches and coastal holding in Africa are much larger and not counted.
6. **Free Black people** are excluded from the census years (enslaved counts only) but included in the colonial years (A7).
7. **Not modeled:** stolen wages after 1865 (convict leasing, sharecropping), Jim Crow-era losses, and the value of the people as "capital" (slave prices). Each would be a separate study.

---

## 7. Verification

* Every cited number, and where and how it was checked, is listed in `data/manual/source_verification_log.csv`.
* `scripts/03_qa.py` re-runs the checks every time and writes [QA_REPORT.md](QA_REPORT.md). It covers:
  * source checksums
  * transcription totals
  * cross-source agreement, including official 1860-census decade totals, CRS state sums, the NASS US average, and SlaveVoyages estimates vs documented voyages
  * literature figures re-found in the saved sources
  * model unit and totals invariants, and an independent recomputation of the present value
  * land-purchase invariants
  * one-at-a-time sensitivity runs
* The run exits non-zero if any check fails.
* Two cited figures are flagged as partial or unverified (the ~1M interstate sales; the ~50k reshipped from the Caribbean). They are used for context only, never in a calculation.
* The US DOT VSL page blocks scripts, so it was verified by hand in a browser (logged as MANUAL).

## 8. Reproduce

```
python3 scripts/run_all.py            # fetch (skips existing) → parse → model → QA → .md→.html
python3 scripts/capture_images.py     # optional: refresh images/ with headless Edge/Chromium
```
Then open `index.html` (double-click; three.js r147 is bundled in `lib/three/`). Requires Python 3.10+. Optional `pypdf` enables QA check L3.
