# CT69.A1.Reparations: context for resuming work

Read this file first to pick the project back up. It is a **science / reality-based** project under Harness 7, so the strict rules apply: every assumption documented, every cited number checked, and QA checks run with a generated report.

## The brief (from the user)
1. Estimate how many enslaved Africans were brought to what became the US, how many died in transit, and how many were sold here.
2. Estimate how many of them and their descendants did slave labor, in what kinds of work, and in which states.
3. Compute the net present value of that labor.
4. Show what that value would buy in land: the % of each state's land at current prices and the cost. Split land into corporate/agribusiness and family farms, taking from corporations first.
5. Optionally, give a separately documented value for the lives lost in transit.

Other points from the user:
* The money would go to a large non-profit that funds descendants' education and well-being.
* The approach deliberately values the **labor only**, clinically. The user knows this is debatable.
* Deliverables: a documented methodology with citations, reproducible scripts, and a three.js map of per-state % of land and cost.

## Where things are
* `index.html`: the viewer. Info is hidden at first; the **Info** button toggles it. URL parameters: `?rate=0.01&mode=where_worked|national_spread&metric=pct|cost|value&info=1`.
* `docs/METHODOLOGY.md`: sources, method, assumptions A1–A12, the interest-rate table, limitations.
* `docs/QA_REPORT.md`: all checks (latest run: 33 PASS, 0 FAIL, 1 MANUAL, 2 FLAG).
* `data/manual/source_verification_log.csv`: where each cited number was verified.
* `scripts/params.json`: every tunable assumption.
* `scripts/run_all.py`: rebuilds everything.

## Key results (2025 $, real interest rates)
* **Middle Passage, mainland North America** (SlaveVoyages Estimates): 472,381 embarked, 388,743 landed, 83,638 died (17.7%).
* **People:** 3,953,760 enslaved in 1860 (official census). 181.2M person-years of enslavement, 1619–1865. Hacker (2020) estimates about 10M people over the whole period.
* **Labor value:** $0.75T undiscounted. $5.0T at 1%, $37.5T at 2%, $332T at 3%. Each extra point multiplies the total by about 7–20×.
* **Benchmark:** rebuilt Craemer's way, the model gives $3.9T against his published $5.9–14.2T. The model's total hours are 353B against Hacker's 410B (−14%).
* **Land:** buyable non-federal land in the 48 contiguous states is worth $7.1T at USDA farm prices.
  * At 1%, the 10 main slave states are fully bought out.
  * Above ~1.5%, the value exceeds all buyable land.
  * Non-family corporations operate only 1.9% of farmland, so "corporations first" runs out fast.
* **Lives lost (separate):** 83,638 × DOT value of a statistical life ($14.2M) = $1.19T.

## Decisions and caveats so far
* Farm prices are used for all purchasable land, which undervalues urban land.
* USDA classifies farm *operations* by legal status, not *owners*.
* Tribal/trust farmland and federal land are never bought.
* The DOT value of a statistical life could only be verified by hand (the site blocks scripts).
* Two context figures are flagged and not used: about 1M interstate sales; about 50k reshipped from the Caribbean.

## Possible next steps (not started)
* State-level split of the labor by sector, using 1860 Census of Agriculture crop output by county.
* Better land prices: FHFA/AEI county land values for urban/residential land.
* Owner-level farmland data (USDA TOTAL 2014) for the corporate/family split.
