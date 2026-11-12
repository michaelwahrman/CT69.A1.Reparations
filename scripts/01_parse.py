"""Parse raw sources into tidy CSVs in data/processed/.  Standard library only.

Outputs
  enslaved_population_by_state_year.csv  state, year, enslaved  (1619-1865, annual, interpolated)
  wages_cpi.csv                          year, cpi, unskilled_hourly_nominal, unskilled_hourly_real_<base>
  land_by_state.csv                      state, total/federal/nonfederal acres, farmland by legal status, $/acre
  middle_passage.csv                     period, embarked, disembarked, died  (mainland North America)
  states_geometry.json                   projected state polygons for the web map
"""
import csv, html, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
MAN = os.path.join(ROOT, "data", "manual")
OUT = os.path.join(ROOT, "data", "processed")
PARAMS = json.load(open(os.path.join(ROOT, "scripts", "params.json")))
BASE = PARAMS["base_year"]

STATES = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
          "District of Columbia", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas",
          "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
          "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York",
          "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island",
          "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
          "West Virginia", "Wisconsin", "Wyoming"]


def num(s):
    s = s.strip().replace(",", "").replace("$", "").replace("%", "")
    if s in ("", "-", "–", "(D)", "(X)", "(NA)", "(Z)"):
        return None
    return float(s)


def read_manual_csv(name):
    with open(os.path.join(MAN, name), encoding="utf-8") as f:
        return list(csv.reader(l for l in f if not l.startswith("#")))


def interp(points, y):
    """Linear interpolation on sorted (year, value) points; 0 before first point; hold last value after."""
    if not points or y < points[0][0]:
        return 0.0
    for (y0, v0), (y1, v1) in zip(points, points[1:]):
        if y0 <= y <= y1:
            return v0 + (v1 - v0) * (y - y0) / (y1 - y0)
    return points[-1][1]


# ---------------------------------------------------------------- enslaved population
def census_1790_1860():
    t = open(os.path.join(RAW, "wikipedia_slavery_in_the_united_states_rev1382810880.wikitext"), encoding="utf-8").read()
    i = t.find("Total Slave Population in U.S., 1790–1860, by State and Territory")
    block = t[i:t.find("|}", i)]
    years = [1790, 1800, 1810, 1820, 1830, 1840, 1850, 1860]
    out = {}
    for line in block.split("\n"):
        m = re.match(r"\|align=left\|\s*(.+?)\s*\|\|(.*)", line)
        if not m:
            continue
        vals = [num(v) for v in m.group(2).split("||")]
        out[m.group(1).strip()] = {y: v for y, v in zip(years, vals) if v is not None}
    # Maine was part of Massachusetts until 1820; the 1790-1810 Massachusetts returns (incl. Maine) report 0 slaves.
    out["Maine"].update({1790: 0.0, 1800: 0.0, 1810: 0.0, 1820: 0.0})
    return out


def colonial_1630_1780():
    rows = read_manual_csv("hsus_colonial_Z1-19_negro_population.csv")
    years = [int(y) for y in rows[0][1:]]
    out = {}
    for r in rows[2:]:
        out[r[0]] = {y: float(v) for y, v in zip(years, r[1:]) if v != ""}
    # HSUS Z1-19 footnote 8: Virginia 1620 population "includes 20 Negroes"; the first recorded arrival was 1619.
    out["Virginia"][1620] = 20.0
    out["Virginia"][1619] = 20.0
    return out


def build_population():
    cen = census_1790_1860()
    col = colonial_1630_1780()
    y0, y1 = PARAMS["labor_start"], PARAMS["labor_end"]
    rows = []
    for st in STATES:
        pts = {}
        pts.update(col.get(st, {}))
        pts.update(cen.get(st, {}))
        if not pts:
            continue
        pts = sorted(pts.items())
        for y in range(y0, y1 + 1):
            v = interp(pts, min(y, 1860))  # 1861-1865: hold the 1860 count (assumption A3)
            if v > 0:
                rows.append((st, y, round(v, 1)))
    with open(os.path.join(OUT, "enslaved_population_by_state_year.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["state", "year", "enslaved"]); w.writerows(rows)
    tot1860 = sum(v for s, y, v in rows if y == 1860)
    tot1790 = sum(v for s, y, v in rows if y == 1790)
    print(f"population: 1790 total {tot1790:,.0f} (census 694,207 incl. rounding), 1860 total {tot1860:,.0f} (census 3,953,820 in table)")
    return rows


# ---------------------------------------------------------------- wages & CPI
def mw_table(name):
    t = open(os.path.join(RAW, name), encoding="utf-8", errors="replace").read()
    out = []
    for r in re.findall(r"<tr.*?</tr>", t, re.S):
        cells = [html.unescape(re.sub("<[^>]+>", "", c)).strip() for c in re.findall(r"<t[dh].*?</t[dh]>", r, re.S)]
        if cells and cells[0].isdigit():
            out.append(cells)
    return out


def build_wages():
    cpi = {int(r[0]): float(r[1]) for r in mw_table("mw_uscpi.html")}
    comp, idx = {}, {}
    for r in mw_table("mw_uswage.html"):
        y = int(r[0])
        if len(r) == 3:   # 1790-1940: production-worker hourly comp ($), unskilled index (1860=100)
            comp[y], idx[y] = float(r[1]), float(r[2])
        elif len(r) == 2 and y < 1790:  # 1774-1789: unskilled index only
            idx[y] = float(r[1])
        else:
            comp[y] = float(r[1])
    # Scale the unskilled-labor INDEX to dollars per hour using the mean ratio comp/index over 1850-1870
    # (the published hourly comp is rounded to whole cents, so single early years are too coarse).
    a0, a1 = PARAMS["wage_anchor_years"]
    k = sum(comp[y] / idx[y] for y in range(a0, a1 + 1)) / (a1 - a0 + 1)
    real1774 = k * idx[1774] * cpi[BASE] / cpi[1774]
    rows = []
    for y in range(PARAMS["labor_start"], PARAMS["labor_end"] + 1):
        if y in idx:
            nom = k * idx[y]
            real = nom * cpi[BASE] / cpi[y]
            rows.append((y, cpi[y], round(nom, 5), round(real, 4), "MW unskilled index x k"))
        else:  # before 1774: no US CPI/wage series; hold the 1774 REAL wage (assumption A5)
            rows.append((y, "", "", round(real1774, 4), "held at 1774 real level"))
    with open(os.path.join(OUT, "wages_cpi.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year", "cpi_1982_84_100", "unskilled_hourly_nominal_usd", f"unskilled_hourly_real_{BASE}usd", "note"])
        w.writerows(rows)
    print(f"wages: k={k:.6f} $/hr per index point; 1860 nominal unskilled ${k*idx[1860]:.3f}/hr; "
          f"1860 real ${k*idx[1860]*cpi[BASE]/cpi[1860]:.2f}/hr ({BASE}$); CPI {BASE}={cpi[BASE]}")
    return k


# ---------------------------------------------------------------- land
def crs_federal():
    t = open(os.path.join(RAW, "crs_R42346_federal_land_ownership.html"), encoding="utf-8").read()
    i = t.find("Table 1. Total Federal Land")
    tb = t[t.find("<table", i):]
    tb = tb[:tb.find("</table>")]
    out = {}
    for r in re.findall(r"<tr.*?</tr>", tb, re.S):
        c = [html.unescape(re.sub("<[^>]+>", "", x)).strip() for x in re.findall(r"<t[dh].*?</t[dh]>", r, re.S)]
        if c and c[0] == "D.C.":
            c[0] = "District of Columbia"
        if len(c) >= 3 and c[0] not in STATES and c[0][:-1] in STATES:
            c[0] = c[0][:-1]  # strip footnote letter, e.g. "Hawaiia"
        if len(c) >= 3 and c[0] in STATES:
            out[c[0]] = (num(c[2]), num(c[1]))  # total acres, federal acres
    return out


def nass_land_values():
    out = {}
    lines = open(os.path.join(RAW, "land0825.txt"), encoding="utf-8", errors="replace").read().split("\n")
    # skip the table of contents (its lines end in dot leaders + page number)
    i = next(k for k, l in enumerate(lines) if l.startswith("Farm Real Estate Average Value per Acre - Regions") and ".." not in l)
    j = next(k for k, l in enumerate(lines) if k > i and l.startswith("Cropland Average Value per Acre") and ".." not in l)
    for l in lines[i:j]:
        m = re.match(r"\s+([A-Z][A-Za-z ]+?)\s*(?:\d/)?\s*\.+:(.*)", l)
        if m and m.group(1).strip() in STATES:
            vals = m.group(2).split()
            out[m.group(1).strip()] = num(vals[4])  # 2025 column
    return out


def coa_legal_status():
    """2022 Census of Agriculture, US/State volume, Table 45: land in farms (acres) by legal status for tax purposes."""
    lines = open(os.path.join(RAW, "coa2022_usv1.txt"), encoding="utf-8", errors="replace").read().split("\n")
    a = next(k for k, l in enumerate(lines) if l.startswith("Table 45.  Selected Operation and Producer Characteristics"))
    b = next(k for k, l in enumerate(lines) if k > a and l.startswith("Table 46."))
    cats = [("Family or individual", "family_individual"), ("Partnership ....", "partnership"),
            ("Family held ....", "corp_family_held"), ("Other than family held", "corp_nonfamily"),
            ("American Indian Reservation, etc.", "other_trust_tribal_institutional")]
    out, cols, cur, in_legal = {}, [], None, False
    for l in lines[a:b]:
        if re.match(r"\s+Item\s+:", l):
            cols = [c.strip() for c in l.split(":")[1:]]
        if l.startswith("OPERATION'S LEGAL STATUS"):
            in_legal = True
        if l.startswith("-----"):
            in_legal = False
        if not in_legal:
            continue
        for key, name in cats:
            if key in l:
                cur = name
        if cur and re.search(r"acres:", l):
            vals = l.split("acres:")[1].split()
            for st, v in zip(cols, vals):
                out.setdefault(st, {})[cur] = num(v)
            cur = None
    # Land in farms per state from Table 1 (State Summary Highlights)
    t1 = next(k for k, l in enumerate(lines) if l.startswith("Table 1.  State Summary Highlights"))
    t2 = next(k for k, l in enumerate(lines) if k > t1 and l.startswith("Table 2."))
    for l in lines[t1:t2]:
        if re.match(r"\s+Item\s+:", l):
            cols = [c.strip() for c in l.split(":")[1:]]
        if l.startswith("Land in farms ....") and "acres:" in l:
            for st, v in zip(cols, l.split("acres:")[1].split()):
                out.setdefault(st, {})["land_in_farms"] = num(v)
    # Withheld (D) cells: allocate the residual (land in farms minus disclosed categories) across withheld
    # categories in proportion to the U.S. shares of those categories (assumption A9). Flag it.
    us = out["United States"]
    for st, d in out.items():
        names = [n for _, n in cats]
        missing = [n for n in names if d.get(n) is None]
        d["withheld_imputed"] = ",".join(missing)
        if missing:
            resid = max(d["land_in_farms"] - sum(d[n] for n in names if d.get(n) is not None), 0)
            w = sum(us[n] for n in missing)
            for n in missing:
                d[n] = resid * us[n] / w
    return out


def build_land():
    fed, price, coa = crs_federal(), nass_land_values(), coa_legal_status()
    cols = ["state", "total_acres", "federal_acres", "nonfederal_acres", "farm_real_estate_usd_per_acre_2025",
            "land_in_farms", "family_individual", "partnership", "corp_family_held", "corp_nonfamily",
            "other_trust_tribal_institutional", "withheld_imputed"]
    rows = []
    for st in STATES:
        tot, f = fed.get(st, (None, None))
        c = coa.get(st, {})
        rows.append([st, tot, f, (tot - f) if tot is not None else None, price.get(st)] +
                    [c.get(k) for k in cols[5:]])
    with open(os.path.join(OUT, "land_by_state.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows)
    us = coa["United States"]
    print(f"land: {len(fed)} states w/ CRS area, {len(price)} w/ NASS $/acre, CoA US farmland {us['land_in_farms']:,.0f} ac; "
          f"non-family corporate {us['corp_nonfamily']:,.0f} ac ({100*us['corp_nonfamily']/us['land_in_farms']:.1f}%)")


# ---------------------------------------------------------------- middle passage
def build_middle_passage():
    rows = read_manual_csv("slavevoyages_estimates_mainland_na_by_decade.csv")
    hdr, out = rows[0], []
    for r in rows[1:]:
        if r[0] == "Totals":  # page totals row, used only by QA check T2
            continue
        v = [float(x) for x in r[1:]]
        emb, dis = sum(v[0::2]), sum(v[1::2])
        out.append((r[0], emb, dis, emb - dis))
    with open(os.path.join(OUT, "middle_passage.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["period", "embarked", "disembarked", "died_in_transit"]); w.writerows(out)
    E, D = sum(o[1] for o in out), sum(o[2] for o in out)
    print(f"middle passage (estimates, mainland N. America): embarked {E:,.0f}, disembarked {D:,.0f}, died {E-D:,.0f} ({100*(E-D)/E:.1f}%)")
    # cross-check with documented voyages (voyage-level file), broad region 20000 = Mainland North America
    e = d = n = 0
    with open(os.path.join(RAW, "tastdb-exp-2019.csv"), encoding="latin-1") as f:
        for r in csv.DictReader(f):
            if r["MJSELIMP1"] == "20000" and r["SLAXIMP"] and r["SLAMIMP"]:
                e += float(r["SLAXIMP"]); d += float(r["SLAMIMP"]); n += 1
    print(f"  cross-check, documented voyages (n={n}): embarked {e:,.0f}, disembarked {d:,.0f}, mortality {100*(e-d)/e:.1f}%")
    return E, D, e, d, n


# ---------------------------------------------------------------- map geometry
def build_geometry():
    topo = json.load(open(os.path.join(RAW, "us-atlas_states-albers-10m.json")))
    sc, tr = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0; pts = []
        for dx, dy in arc:
            x += dx; y += dy
            pts.append((round(x * sc[0] + tr[0], 1), round(y * sc[1] + tr[1], 1)))
        arcs.append(pts)

    def ring(idxs):
        pts = []
        for i in idxs:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(a if not pts else a[1:])
        return pts

    out = {}
    for g in topo["objects"]["states"]["geometries"]:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        out[g["properties"]["name"]] = [[ring(r) for r in p] for p in polys]
    json.dump(out, open(os.path.join(OUT, "states_geometry.json"), "w"), separators=(",", ":"))
    print(f"geometry: {len(out)} states/territories")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    build_population()
    build_wages()
    build_land()
    build_middle_passage()
    build_geometry()
