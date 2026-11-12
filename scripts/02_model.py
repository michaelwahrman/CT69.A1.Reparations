"""Labor-value NPV model + land purchase model.  Standard library only.

Reads data/processed/*.csv and scripts/params.json; writes
  data/processed/results.json          full results (all rates, both land modes)
  data/processed/summary_by_rate.csv   national totals per real interest rate
  data/processed/state_results_<r>.csv per-state table at each rate
  web/data/model_results.js                  same JSON for the browser (window.RESULTS = ...)
  web/data/states.js                   projected state polygons (window.STATES_GEO = ...)
"""
import csv, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")
WEB = os.path.join(ROOT, "web", "data")
P = json.load(open(os.path.join(ROOT, "scripts", "params.json")))
BASE = P["base_year"]


def fnum(x):
    return float(x) if x not in ("", None) else None


# ------------------------------------------------------------------ inputs
pop = {}
for r in csv.DictReader(open(os.path.join(PROC, "enslaved_population_by_state_year.csv"))):
    pop.setdefault(r["state"], {})[int(r["year"])] = float(r["enslaved"])
wage = {int(r["year"]): float(r[f"unskilled_hourly_real_{BASE}usd"])
        for r in csv.DictReader(open(os.path.join(PROC, "wages_cpi.csv")))}
land = {r["state"]: {k: (fnum(v) if k not in ("state", "withheld_imputed") else v) for k, v in r.items()}
        for r in csv.DictReader(open(os.path.join(PROC, "land_by_state.csv")))}
mp = list(csv.DictReader(open(os.path.join(PROC, "middle_passage.csv"))))


# ------------------------------------------------------------------ labor value
def labor_value_by_year(participation, hours, wage_mult, maint):
    """Undiscounted value of labor in constant BASE-year dollars, per state per year."""
    out = {}
    for st, series in pop.items():
        out[st] = {y: n * participation * hours * wage[y] * wage_mult * (1 - maint) for y, n in series.items()}
    return out


def pv(series_by_year, r):
    return sum(v * (1 + r) ** (BASE - y) for y, v in series_by_year.items())


base_lv = labor_value_by_year(P["labor_participation"], P["hours_per_worker_year"], P["wage_multiplier"],
                              P["maintenance_share_deducted"])
person_years = sum(sum(s.values()) for s in pop.values())
worker_years = person_years * P["labor_participation"]

rates = P["real_rates"]
pv_state = {r: {st: pv(lv, r) for st, lv in base_lv.items()} for r in rates}
pv_total = {r: sum(pv_state[r].values()) for r in rates}

# low / high bands: vary participation and hours together (wage series fixed)
def band(part, hrs):
    lv = labor_value_by_year(part, hrs, P["wage_multiplier"], P["maintenance_share_deducted"])
    return {r: sum(pv(s, r) for s in lv.values()) for r in rates}
pv_low = band(P["labor_participation_range"][0], P["hours_range"][0])
pv_high = band(P["labor_participation_range"][1], P["hours_range"][1])

# Illustrative sector split: enslaved people by occupation in 1850 (J.D.B. De Bow, as reported in the NBER
# chapter cited in METHODOLOGY.md). Applies to 1850 only; used here only to label shares of the 1850 workforce.
SECTORS_1850 = {"Cotton": 1815000, "Tobacco": 350000, "Sugar cane": 150000, "Rice": 125000, "Hemp": 60000,
                "Cities & towns (domestic, trades, industry)": 400000}
pop1850 = sum(s.get(1850, 0) for s in pop.values())
SECTORS_1850["Other / unallocated (rural non-staple, children, elderly, industry outside towns)"] = pop1850 - sum(SECTORS_1850.values())

# ------------------------------------------------------------------ land model
TIERS = [("corp_nonfamily", "Non-family corporations (farmland)"),
         ("partnership_and_family_corp", "Partnerships & family-held corporations (farmland)"),
         ("family_individual", "Family / individual farms"),
         ("other_nonfederal_land", "Other non-federal land (non-farm; priced at farm $/acre)")]


def tiers_for(st):
    d = land[st]
    if not d.get("farm_real_estate_usd_per_acre_2025") or not d.get("nonfederal_acres"):
        return None
    other_nonfarm = max(d["nonfederal_acres"] - d["land_in_farms"], 0)
    return {"corp_nonfamily": d["corp_nonfamily"],
            "partnership_and_family_corp": d["partnership"] + d["corp_family_held"],
            "family_individual": d["family_individual"],
            "other_nonfederal_land": other_nonfarm}


def buy(st, value):
    t, price = tiers_for(st), land[st]["farm_real_estate_usd_per_acre_2025"]
    res = {"acres": {}, "cost": 0.0, "leftover": value}
    if t is None:
        return res
    left = value
    for k, _ in TIERS:
        a = min(t[k], left / price)
        res["acres"][k] = a
        left -= a * price
        if left < 1e-9 * max(value, 1):  # absorb floating-point residue so no fraction of an acre spills into the next tier
            left = 0.0
    res["cost"] = value - left
    res["leftover"] = left
    return res


buyable_value = {st: sum(tiers_for(st).values()) * land[st]["farm_real_estate_usd_per_acre_2025"]
                 for st in land if tiers_for(st)}
national_buyable = sum(buyable_value.values())

states_out = []
for st in land:
    d, t = land[st], tiers_for(st)
    states_out.append({
        "state": st, "total_acres": d["total_acres"], "federal_acres": d["federal_acres"],
        "nonfederal_acres": d["nonfederal_acres"], "price_per_acre": d["farm_real_estate_usd_per_acre_2025"],
        "tiers_acres": t, "buyable_value": buyable_value.get(st),
        "withheld_imputed": d["withheld_imputed"],
        "enslaved_1790": pop.get(st, {}).get(1790, 0), "enslaved_1860": pop.get(st, {}).get(1860, 0),
        "person_years": sum(pop.get(st, {}).values()),
        "by_rate": {}})

for r in rates:
    for so in states_out:
        st = so["state"]
        v_where = pv_state[r].get(st, 0.0)
        a = buy(st, v_where)
        share = min(pv_total[r] / national_buyable, 1.0)
        v_nat = buyable_value.get(st, 0) * share
        b = buy(st, v_nat)
        def pack(x, v):
            ac = sum(x["acres"].values())
            return {"value": v, "cost": x["cost"], "leftover": x["leftover"], "acres": ac,
                    "acres_by_tier": x["acres"],
                    "pct_nonfederal": (ac / so["nonfederal_acres"]) if so["nonfederal_acres"] and so["tiers_acres"] else None,
                    "pct_total": (ac / so["total_acres"]) if so["total_acres"] and so["tiers_acres"] else None}
        so["by_rate"][str(r)] = {"where_worked": pack(a, v_where), "national_spread": pack(b, v_nat)}

# ------------------------------------------------------------------ lives lost in transit (separate estimate)
deaths = [(int(m["period"][:4]) + 5, float(m["died_in_transit"])) for m in mp]
total_deaths = sum(d for _, d in deaths)
vsl_total = total_deaths * P["lives_lost"]["vsl_usd_2025"]
wy = P["lives_lost"]["working_years_lost"]
def forgone(r):
    s = 0.0
    for y0, n in deaths:
        for y in range(y0, min(y0 + wy, P["labor_end"] + 1)):  # cannot exceed the end of slavery
            s += n * P["hours_per_worker_year"] * wage[y] * (1 + r) ** (BASE - y)
    return s

lives = {"deaths": total_deaths,
         "embarked": sum(float(m["embarked"]) for m in mp), "disembarked": sum(float(m["disembarked"]) for m in mp),
         "vsl_each": P["lives_lost"]["vsl_usd_2025"], "vsl_total": vsl_total,
         "forgone_labor_by_rate": {str(r): forgone(r) for r in rates}}

# ------------------------------------------------------------------ benchmark vs Craemer (2015)
# Craemer: hours worked 1776-1865 x historical (nominal) free-labor wages, compounded at 3% to 2009 -> $5.9-14.2T.
# Reproduce that construction with this project's inputs as a validation check.
nominal = {int(r["year"]): fnum(r["unskilled_hourly_nominal_usd"]) for r in csv.DictReader(open(os.path.join(PROC, "wages_cpi.csv")))}
natpop = {}
for s in pop.values():
    for y, n in s.items():
        natpop[y] = natpop.get(y, 0) + n
craemer_style = sum(natpop[y] * P["labor_participation"] * P["hours_per_worker_year"] * nominal[y] * 1.03 ** (2009 - y)
                    for y in range(1776, 1866))

# ------------------------------------------------------------------ write
results = {
    "benchmark_craemer_style_2009usd": craemer_style,
    "base_year": BASE, "params": P, "rates": rates,
    "national": {str(r): {"pv": pv_total[r], "pv_low": pv_low[r], "pv_high": pv_high[r]} for r in rates},
    "undiscounted_constant_dollars": pv_total[0.0],
    "person_years": person_years, "worker_years": worker_years,
    "national_buyable_value": national_buyable,
    "sectors_1850": SECTORS_1850, "pop_1850": pop1850,
    "tiers": TIERS, "states": states_out, "lives_lost": lives,
}
os.makedirs(WEB, exist_ok=True)
json.dump(results, open(os.path.join(PROC, "results.json"), "w"), indent=1)
with open(os.path.join(WEB, "model_results.js"), "w") as f:
    f.write("window.RESULTS = " + json.dumps(results, separators=(",", ":")) + ";\n")
with open(os.path.join(WEB, "states.js"), "w") as f:
    f.write("window.STATES_GEO = " + open(os.path.join(PROC, "states_geometry.json")).read() + ";\n")

with open(os.path.join(PROC, "summary_by_rate.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["real_rate", "pv_labor_usd_2025", "pv_low", "pv_high", "share_of_buyable_land_value_48_states",
                "lives_lost_forgone_labor_pv"])
    for r in rates:
        w.writerow([r, round(pv_total[r]), round(pv_low[r]), round(pv_high[r]),
                    round(pv_total[r] / national_buyable, 4), round(lives["forgone_labor_by_rate"][str(r)])])
for r in rates:
    with open(os.path.join(PROC, f"state_results_r{r*100:g}pct.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["state", "pv_labor_performed_here", "acres_bought_where_worked", "pct_nonfederal_where_worked",
                    "cost_where_worked", "unspent_where_worked", "corp_acres", "partnership_famcorp_acres",
                    "family_acres", "other_acres", "pct_nonfederal_national_spread", "cost_national_spread"])
        for so in states_out:
            a, b = so["by_rate"][str(r)]["where_worked"], so["by_rate"][str(r)]["national_spread"]
            t = a["acres_by_tier"]
            w.writerow([so["state"], round(a["value"]), round(a["acres"]), a["pct_nonfederal"], round(a["cost"]),
                        round(a["leftover"]), round(t.get("corp_nonfamily", 0)), round(t.get("partnership_and_family_corp", 0)),
                        round(t.get("family_individual", 0)), round(t.get("other_nonfederal_land", 0)),
                        b["pct_nonfederal"], round(b["cost"])])

# console summary
T = 1e12
print(f"person-years enslaved 1619-1865: {person_years:,.0f}; worker-years: {worker_years:,.0f}")
print(f"undiscounted labor value (constant {BASE}$): ${pv_total[0.0]/T:.2f}T")
print(f"buyable land value, 48 states (excl. federal & tribal/trust farmland), at farm $/acre: ${national_buyable/T:.1f}T")
for r in rates:
    print(f"  r={r:.1%}: PV ${pv_total[r]/T:,.1f}T  (band ${pv_low[r]/T:,.1f}-{pv_high[r]/T:,.1f}T)  "
          f"= {pv_total[r]/national_buyable:,.1%} of buyable land")
print(f"benchmark, Craemer-style construction (1776-1865, nominal wages, 3% nominal, 2009$): ${craemer_style/T:.1f}T "
      f"vs. published $5.9-14.2T")
print(f"middle passage deaths: {total_deaths:,.0f}; VSL method ${vsl_total/T:.2f}T; "
      f"forgone-labor @3% ${lives['forgone_labor_by_rate']['0.03']/T:.2f}T")
