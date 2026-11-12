"""Quality-assurance / verification checks.  Writes docs/QA_REPORT.md (+ .html via 04_docs.py).

Exit code 1 if any check FAILS.  Checks are grouped:
  S  source integrity        T  transcription & cross-source checks     L  literature numbers re-found in saved sources
  M  model / unit / totals   G  land-purchase invariants                X  lives-lost estimate
Plus one-at-a-time sensitivity runs (informational).
Standard library, except checks L3 (needs `pypdf` to read a PDF); if pypdf is missing that check is reported as SKIP.
"""
import csv, hashlib, html, importlib.util, json, os, re, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW, MAN, PROC = (os.path.join(ROOT, "data", d) for d in ("raw", "manual", "processed"))
P = json.load(open(os.path.join(ROOT, "scripts", "params.json")))
R = json.load(open(os.path.join(PROC, "results.json")))
checks = []


def check(cid, desc, ok, detail, status=None):
    checks.append((cid, desc, status or ("PASS" if ok else "FAIL"), detail))


def rows_manual(name):
    return list(csv.reader(l for l in open(os.path.join(MAN, name), encoding="utf-8") if not l.startswith("#")))


def text(name):
    return open(os.path.join(RAW, name), encoding="utf-8", errors="replace").read()


def flat(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)))


# ---- load model module helpers (parsers) without re-running them
spec = importlib.util.spec_from_file_location("parse", os.path.join(ROOT, "scripts", "01_parse.py"))
parse = importlib.util.module_from_spec(spec); spec.loader.exec_module(parse)

# ================================================================ S: source integrity
man = json.load(open(os.path.join(RAW, "MANIFEST.json")))
bad = [n for n, m in man.items() if hashlib.sha256(open(os.path.join(RAW, n), "rb").read()).hexdigest() != m["sha256"]]
check("S1", "Raw files match SHA-256 recorded in data/raw/MANIFEST.json", not bad, f"{len(man)} files; mismatches: {bad or 'none'}")
log = rows_manual("source_verification_log.csv")
hdr = log[0]; log = [dict(zip(hdr, r)) for r in log[1:]]
used_unverified = [r["id"] for r in log if r["status"] != "verified" and r["used_in_calculation"].startswith("yes")]
check("S2", "No partial/unverified source number is used in any calculation", not used_unverified,
      f"{len(log)} logged claims; verified {sum(r['status'].startswith('verified') for r in log)}, "
      f"partial {sum(r['status']=='partial' for r in log)}, unverified {sum(r['status']=='unverified' for r in log)} (context only)")

# ================================================================ T: transcription & cross-source
rows = rows_manual("hsus_colonial_Z1-19_negro_population.csv")
yrs = rows[0][1:]; tot = rows[1]
bad = [y for j, y in enumerate(yrs, 1) if sum(int(r[j] or 0) for r in rows[2:]) != int(tot[j])]
check("T1", "HSUS Z1-19 transcription: each year's colony values sum to the printed total", not bad,
      f"{len(yrs)} year columns checked; mismatched: {bad or 'none'}")

rows = rows_manual("slavevoyages_estimates_mainland_na_by_decade.csv")
body = [r for r in rows[1:] if r[0] != "Totals"]; totrow = next(r for r in rows if r[0] == "Totals")
bad = [rows[0][j] for j in range(1, 11) if sum(int(r[j]) for r in body) != int(totrow[j])]
check("T2", "SlaveVoyages copy: decade rows sum to the web page's Totals row (10 columns)", not bad, f"mismatched: {bad or 'none'}")

off = {int(r[0]): int(r[1]) for r in rows_manual("census1860_intro_slave_totals.csv")[1:]}
pop = {}
for r in csv.DictReader(open(os.path.join(PROC, "enslaved_population_by_state_year.csv"))):
    pop.setdefault(int(r["year"]), 0); pop[int(r["year"])] += float(r["enslaved"])
dev = {y: (pop[y] - v) / v for y, v in off.items()}
worst = max(abs(d) for d in dev.values())
check("T3", "Per-state census series sums vs OFFICIAL national totals (1860 Census intro p. viii), |dev| < 0.5%",
      worst < 0.005, "; ".join(f"{y}: {pop[y]:,.0f} vs {v:,} ({100*dev[y]:+.2f}%)" for y, v in off.items()))
check("T3b", "1860 national total reproduced exactly (3,953,760)", round(pop[1860]) == off[1860], f"{pop[1860]:,.0f}")

crs = text("crs_R42346_federal_land_ownership.html")
i = crs.find("Table 1. Total Federal Land"); tb = crs[crs.find("<table", i):]; tb = tb[:tb.find("</table>")]
cells = [[html.unescape(re.sub("<[^>]+>", "", x)).strip() for x in re.findall(r"<t[dh].*?</t[dh]>", r, re.S)]
         for r in re.findall(r"<tr.*?</tr>", tb, re.S)]
tbl = " ".join(" ".join(c) for c in cells)
m = re.search(r"U\.S\. Total ([\d,]+) ([\d,]+) ([\d.]+)%", tbl)
fed = parse.crs_federal()
s_tot, s_fed = sum(v[0] for v in fed.values()), sum(v[1] for v in fed.values())
us_fed, us_tot = (float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))) if m else (None, None)
check("T4", "CRS Table 1: 50 state rows + D.C. sum to the U.S. Total row (total acres and federal acres)",
      m and abs(s_tot - us_tot) < 1 and abs(s_fed - us_fed) / us_fed < 0.001,
      f"states {len(fed)}; total {s_tot:,.0f} vs {us_tot:,.0f}; federal {s_fed:,.0f} vs {us_fed:,.0f}")

land = list(csv.DictReader(open(os.path.join(PROC, "land_by_state.csv"))))
coa = parse.coa_legal_status()
cats = ["family_individual", "partnership", "corp_family_held", "corp_nonfamily", "other_trust_tribal_institutional"]
us = coa["United States"]
gap_us = sum(us[c] for c in cats) - us["land_in_farms"]
full = [s for s, d in coa.items() if s != "United States" and not d["withheld_imputed"]]
gaps = {s: abs(sum(coa[s][c] for c in cats) - coa[s]["land_in_farms"]) for s in full}
check("T5", "Census of Agriculture Table 45: legal-status acres sum to land in farms (US and every state without withheld cells)",
      abs(gap_us) < 1 and max(gaps.values()) < 1,
      f"US gap {gap_us:,.0f} ac; {len(full)} states exact; {50-len(full)} states with (D) cells imputed: "
      + ", ".join(s for s, d in coa.items() if d['withheld_imputed']))

lv = text("land0825.txt")
m = re.search(r"United States 2/ \.+:(.*)", lv)
us_avg = float(m.group(1).split()[4].replace(",", ""))
wsum = sum(float(r["farm_real_estate_usd_per_acre_2025"]) * float(r["land_in_farms"]) for r in land if r["farm_real_estate_usd_per_acre_2025"])
asum = sum(float(r["land_in_farms"]) for r in land if r["farm_real_estate_usd_per_acre_2025"])
check("T6", "NASS: state $/acre weighted by 2022 land in farms reproduces the published US average within 5%",
      abs(wsum / asum / us_avg - 1) < 0.05, f"weighted {wsum/asum:,.0f} vs published {us_avg:,.0f} $/acre ({100*(wsum/asum/us_avg-1):+.1f}%)")

mp = list(csv.DictReader(open(os.path.join(PROC, "middle_passage.csv"))))
E = sum(float(r["embarked"]) for r in mp); D = sum(float(r["disembarked"]) for r in mp)
e = d = n = 0
with open(os.path.join(RAW, "tastdb-exp-2019.csv"), encoding="latin-1") as f:
    for r in csv.DictReader(f):
        if r["MJSELIMP1"] == "20000" and r["SLAXIMP"] and r["SLAMIMP"]:
            e += float(r["SLAXIMP"]); d += float(r["SLAMIMP"]); n += 1
check("T7", "Middle Passage mortality: estimates vs documented voyages agree within 3 percentage points",
      abs((E - D) / E - (e - d) / e) < 0.03, f"estimates {100*(E-D)/E:.1f}% vs documented {100*(e-d)/e:.1f}% (n={n} voyages)")

# ================================================================ L: literature numbers re-found in saved sources
c = flat(text("craemer2015_repec.html"))
check("L1", "Craemer (2015): '$5.9 to $14.2 trillion' present in saved abstract", "5.9 to $14.2 trillion" in c, "data/raw/craemer2015_repec.html")
h = flat(text("hacker2020_pmc.html"))
check("L2", "Hacker (2020): 'approximately 10 million slaves' and '410 billion hours' present in saved article",
      "approximately 10 million slaves" in h and "410 billion hours" in h, "data/raw/hacker2020_pmc.html")
try:
    import pypdf
    t = " ".join((p.extract_text() or "") for p in pypdf.PdfReader(os.path.join(RAW, "nber_c0606_evans1962.pdf")).pages[:8])
    t = re.sub(r"\s+", " ", t)
    need = ["1,815,000 in cotton", "350,000 in tobacco", "150,000 in cane sugar", "125,000 in rice", "60,000 in hemp", "400,000 slaves lived in cities"]
    miss = [x for x in need if x not in t]
    check("L3", "Evans (1962) quoting De Bow: 1850 occupation counts present in saved PDF", not miss, f"missing: {miss or 'none'}")
except ImportError:
    check("L3", "Evans (1962) quoting De Bow: 1850 occupation counts present in saved PDF", True,
          "pypdf not installed: run `pip install pypdf` to enable", status="SKIP")
check("L4", "US DOT VSL $14.2M (2025): site blocks scripts; verified manually in a browser on 2026-11-12", True,
      "see data/manual/source_verification_log.csv V13", status="MANUAL")
cv = text("coa2022_usv1.txt")
check("L7", "Census of Agriculture: rented/leased land 345,889,019 ac (39% of 880,100,848) present in source",
      "345,889,019" in cv, f"{100*345889019/880100848:.1f}%")
for r in log:
    if r["status"] in ("partial", "unverified"):
        check(r["id"], f"{r['claim']} ({r['value_used']})", True, f"{r['status'].upper()}: {r['note']}; not used in calculations", status="FLAG")

# ================================================================ M: model checks
popst = {}
for r in csv.DictReader(open(os.path.join(PROC, "enslaved_population_by_state_year.csv"))):
    popst.setdefault(r["state"], {})[int(r["year"])] = float(r["enslaved"])
cen = parse.census_1790_1860()
bad = [(s, y) for s, d in cen.items() for y, v in d.items() if v > 0 and abs(popst.get(s, {}).get(y, 0) - v) > 0.5]
check("M1", "Annual interpolated series equals the census value at every census year and state", not bad, f"mismatches: {bad[:5] or 'none'}")
neg = [k for s in popst.values() for k, v in s.items() if v < 0]
check("M2", "No negative populations; series spans labor_start..labor_end", not neg and min(min(s) for s in popst.values()) >= P["labor_start"]
      and max(max(s) for s in popst.values()) <= P["labor_end"], f"years {min(min(s) for s in popst.values())}-{max(max(s) for s in popst.values())}")
W = list(csv.DictReader(open(os.path.join(PROC, "wages_cpi.csv"))))
w1860 = next(float(r["unskilled_hourly_nominal_usd"]) for r in W if r["year"] == "1860")
check("M3", "Wage scaling: 1860 unskilled $/hr consistent with MeasuringWorth 1860 production-worker comp ($0.08, cents-rounded)",
      abs(w1860 - 0.08) <= 0.006, f"model ${w1860:.4f}/hr; real wages all > 0: {all(float(r[f'unskilled_hourly_real_{P['base_year']}usd'])>0 for r in W)}")
N = R["national"]; rates = [str(x) for x in R["rates"]]
check("M4a", "PV at r=0 equals the undiscounted constant-dollar total", abs(N["0.0"]["pv"] - R["undiscounted_constant_dollars"]) < 1, f"${N['0.0']['pv']:,.0f}")
check("M4b", "PV strictly increases with the interest rate", all(N[a]["pv"] < N[b]["pv"] for a, b in zip(rates, rates[1:])), "")
st_sum = {k: sum(s["by_rate"][k]["where_worked"]["value"] for s in R["states"]) for k in rates}
dc = {k: 0 for k in rates}
check("M4c", "Sum of state values equals the national PV at every rate (units/totals)",
      all(abs(st_sum[k] / N[k]["pv"] - 1) < 1e-9 for k in rates), "all rates")
check("M5", "Sensitivity band ordering low <= base <= high at every rate", all(N[k]["pv_low"] <= N[k]["pv"] <= N[k]["pv_high"] for k in rates), "")
hours = R["worker_years"] * P["hours_per_worker_year"]
check("M6", "Cross-check vs Hacker (2020): total hours within +/-25% of 410 billion", abs(hours / 410e9 - 1) < 0.25,
      f"model {hours/1e9:,.0f} billion hours ({100*(hours/410e9-1):+.0f}%)")
b = R["benchmark_craemer_style_2009usd"]
check("M7", "Benchmark: Craemer-style rebuild within a factor of 2 of his published $5.9-14.2T", 5.9e12 / 2 <= b <= 14.2e12 * 2,
      f"${b/1e12:.2f}T (2009$)")
check("M8", "Middle Passage: embarked >= disembarked in every decade; overall mortality 5-30%",
      all(float(r["embarked"]) >= float(r["disembarked"]) for r in mp) and 0.05 < (E - D) / E < 0.30, f"{100*(E-D)/E:.1f}%")

# ================================================================ G: land invariants
TK = ["corp_nonfamily", "partnership_and_family_corp", "family_individual", "other_nonfederal_land"]
viol = []
for s in R["states"]:
    t, price = s["tiers_acres"], s["price_per_acre"]
    for k in rates:
        for mode in ("where_worked", "national_spread"):
            x = s["by_rate"][k][mode]
            if x["cost"] > x["value"] * (1 + 1e-9) + 1: viol.append((s["state"], k, mode, "cost>value"))
            if abs(x["cost"] + x["leftover"] - x["value"]) > 1 + 1e-9 * x["value"]: viol.append((s["state"], k, mode, "cost+leftover!=value"))
            if not t:
                if x["acres"] > 0: viol.append((s["state"], k, mode, "bought without price"))
                continue
            a = x["acres_by_tier"]
            if abs(x["cost"] - x["acres"] * price) > 1 + 1e-9 * x["cost"]: viol.append((s["state"], k, mode, "cost!=acres*price"))
            for i, tk in enumerate(TK):
                if a[tk] > t[tk] + 1e-6: viol.append((s["state"], k, mode, f"{tk} over capacity"))
                if i and a[tk] > 0 and a[TK[i-1]] < t[TK[i-1]] - 1e-6: viol.append((s["state"], k, mode, f"{tk} before {TK[i-1]} exhausted"))
            if x["pct_nonfederal"] is not None and x["pct_nonfederal"] > 1 + 1e-12: viol.append((s["state"], k, mode, "pct>1"))
check("G1", "Land purchase invariants (cost<=value, cost+unspent=value, cost=acres*price, tier capacity, tier order, pct<=1)",
      not viol, f"{len(R['states'])} states x {len(rates)} rates x 2 modes; violations: {viol[:4] or 'none'}")
lr = {r["state"]: r for r in land}
over = [s["state"] for s in R["states"] if s["tiers_acres"] and
        max(s["by_rate"][k][m]["acres"] for k in rates for m in ("where_worked", "national_spread"))
        > float(lr[s["state"]]["nonfederal_acres"]) - float(lr[s["state"]]["other_trust_tribal_institutional"] or 0) + 1]
check("G2", "Federal land and tribal/trust farmland are never bought", not over, f"violations: {over or 'none'}")
for k in rates:
    pcts = {round(s["by_rate"][k]["national_spread"]["acres"] / sum(s["tiers_acres"].values()), 9) for s in R["states"] if s["tiers_acres"]}
    if len(pcts) > 1: break
check("G3", "'All states, same share' mode buys the same fraction of purchasable land in every state", len(pcts) == 1, f"fractions at last rate: {sorted(pcts)[:3]}")

# ================================================================ X: lives lost
L = R["lives_lost"]
check("X1", "Lives-lost VSL total = deaths x VSL ($14.2M)", abs(L["vsl_total"] - L["deaths"] * 14.2e6) < 1, f"{L['deaths']:,.0f} x $14.2M = ${L['vsl_total']/1e12:.2f}T")
check("X2", "Deaths equal embarked - disembarked (SlaveVoyages)", L["deaths"] == E - D == 83638, f"{L['deaths']:,.0f}")

# ================================================================ sensitivity runs (one at a time)
spec = importlib.util.spec_from_file_location("model", os.path.join(ROOT, "scripts", "02_model.py"))
# re-implement the core PV quickly to avoid re-writing outputs
wage = {int(r["year"]): float(r[f"unskilled_hourly_real_{P['base_year']}usd"]) for r in W}
def pv_total(part=P["labor_participation"], hrs=P["hours_per_worker_year"], mult=1.0, maint=0.0, r=0.01, start=P["labor_start"], pre1774=None):
    s = 0.0
    for st in popst.values():
        for y, n in st.items():
            if y < start: continue
            w = wage[y] if (pre1774 is None or y >= 1774) else wage[1774] * pre1774
            s += n * part * hrs * w * mult * (1 - maint) * (1 + r) ** (P["base_year"] - y)
    return s
sens = []
for r in (0.0, 0.01, 0.03):
    base = pv_total(r=r)
    check(f"M9-{r:g}", f"Model PV reproduced independently by QA at r={r:.0%}", abs(base / N[str(r)]["pv"] - 1) < 1e-9, f"${base/1e12:,.3f}T")
    for name, kw in [("participation 0.55", dict(part=0.55)), ("participation 0.75", dict(part=0.75)),
                     ("hours 2,500", dict(hrs=2500)), ("hours 3,500", dict(hrs=3500)),
                     ("wage x0.6 (Southern farm-labor discount)", dict(mult=0.6)), ("maintenance deducted 30%", dict(maint=0.3)),
                     ("start 1776 (Craemer window)", dict(start=1776)), ("pre-1774 real wage x0.5", dict(pre1774=0.5))]:
        v = pv_total(r=r, **kw)
        sens.append((f"{r:.0%}", name, base, v))
lin = abs(pv_total(part=0.75, r=0.01) / pv_total(r=0.01) - 0.75 / 0.65) < 1e-9
check("M10", "PV scales exactly linearly with participation (unit consistency)", lin, "")

# ================================================================ write report
npass = sum(c[2] == "PASS" for c in checks); nfail = sum(c[2] == "FAIL" for c in checks)
other = {s: sum(c[2] == s for c in checks) for s in ("SKIP", "MANUAL", "FLAG")}
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
out = [f"# CT69.A1.Reparations: QA / verification report",
       "", f"Generated by `scripts/03_qa.py` on {now}. **{npass} PASS, {nfail} FAIL**, "
       + ", ".join(f"{v} {k}" for k, v in other.items()) + ".",
       "", "Status key: **PASS** automated check passed · **FAIL** automated check failed · **MANUAL** checked by a person in a browser (cannot be automated) · "
       "**FLAG** a number that is partial or unverified; quoted for context only, never used in a calculation · **SKIP** check could not run.", "",
       "| ID | Check | Result | Detail |", "|---|---|---|---|"]
for cid, desc, st, det in checks:
    out.append(f"| {cid} | {desc.replace('|', '/')} | **{st}** | {det.replace('|', '/')} |")
out += ["", "## Sensitivity runs (one assumption at a time)", "",
        "| Real rate | Change | Base PV | New PV | Ratio |", "|---|---|---|---|---|"]
for r, name, base, v in sens:
    out.append(f"| {r} | {name} | ${base/1e12:,.2f}T | ${v/1e12:,.2f}T | {v/base:.2f}x |")
out += ["", "Interest-rate sensitivity (all rates, with the participation/hours band) is in `data/processed/summary_by_rate.csv` and METHODOLOGY.md §5.",
        "", "## Source verification log", "", "Every cited number, where it was checked and how: `data/manual/source_verification_log.csv`.", "",
        "| ID | Claim | Status | Where checked | Used in calculation |", "|---|---|---|---|---|"]
for r in log:
    out.append(f"| {r['id']} | {r['claim']} | {r['status']} | {r['where_checked']} ({r['method']}) | {r['used_in_calculation']} |")
open(os.path.join(ROOT, "docs", "QA_REPORT.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print(f"QA: {npass} PASS, {nfail} FAIL, {other}")
for c in checks:
    if c[2] == "FAIL": print("  FAIL", c[0], c[1], c[3])
sys.exit(1 if nfail else 0)
