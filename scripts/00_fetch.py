"""Download every machine-fetchable raw source into data/raw/ and record SHA-256 checksums.

Run:  python scripts/00_fetch.py          (skips files that already exist)
      python scripts/00_fetch.py --force  (re-download everything)

Sources that cannot be fetched by script are kept in data/manual/ with provenance notes:
  - slavevoyages_estimates_mainland_na_by_decade.csv (copied from the SlaveVoyages Estimates web form)
  - hsus_colonial_Z1-19_negro_population.csv (hand-transcribed from a scanned Census PDF, totals verified)
Standard library only.
"""
import hashlib, json, os, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
UA = {"User-Agent": "Mozilla/5.0 (research script; CT69.A1.Reparations)"}

SOURCES = [
    # (filename, url, POST data or None, description)
    ("land0825.txt",
     "https://esmis.nal.usda.gov/sites/default/release-files/pn89d6567/2n49w148w/1g05hb655/land0825.txt",
     None, "USDA NASS, Land Values 2025 Summary (Aug 2025): farm real estate $/acre by state"),
    ("coa2022_usv1.txt",
     "https://www.nass.usda.gov/sites/default/files/publications/agcensus/2022/Full_Report/Volume_1,_Chapter_2_US_State_Level/usv1.txt",
     None, "USDA NASS, 2022 Census of Agriculture, Vol. 1 Ch. 2 (US & State), full text; Table 45 legal status by state"),
    ("crs_R42346_federal_land_ownership.html",
     "https://www.everycrsreport.com/reports/R42346.html",
     None, "Congressional Research Service R42346, Federal Land Ownership: Overview and Data (Table 1, acreage as of 2024-09-30)"),
    ("wikipedia_slavery_in_the_united_states_rev1382810880.wikitext",
     "https://en.wikipedia.org/w/index.php?title=Slavery_in_the_United_States&action=raw&oldid=1382810880",
     None, "Wikipedia transcription of US Census slave population by state 1790-1860 (primary: 1850 Compendium ch. V; 1860 Population vol.)"),
    ("tastdb-exp-2019.csv",
     "https://legacy.slavevoyages.org/documents/download/tastdb-exp-2019.csv",
     None, "SlaveVoyages Trans-Atlantic Slave Trade Database, voyage-level 2019 export (documented voyages; used as cross-check)"),
    ("hsus_colonial_chZ.pdf",
     "https://www2.census.gov/library/publications/1975/compendia/hist_stats_colonial-1970/hist_stats_colonial-1970p2-chZ.pdf",
     None, "Historical Statistics of the US, Colonial Times to 1970, ch. Z (scan; Series Z 1-19 p.1168)"),
    ("mw_uswage.html",
     "https://www.measuringworth.com/datasets/uswage/result.php",
     {"use[]": ["UNSKILLED", "MANCOMP"], "year_source": "1774", "year_result": "2025"},
     "MeasuringWorth: Officer & Williamson, Annual Wages in the US (unskilled index 1860=100; production worker hourly comp)"),
    ("mw_uscpi.html",
     "https://www.measuringworth.com/datasets/uscpi/result.php",
     {"year_source": "1774", "year_result": "2025"},
     "MeasuringWorth: Williamson, The Annual Consumer Price Index for the US, 1774-present (1982-84=100)"),
    # --- literature / verification sources (used by scripts/03_qa.py to re-check cited numbers) ---
    ("census1860_slaves_intro.pdf",
     "https://www2.census.gov/library/publications/decennial/1860/population/1860a-02.pdf",
     None, "1860 Census, Population volume introduction (scan); p. viii 'Census of slaves and free colored'"),
    ("craemer2015_repec.html", "https://ideas.repec.org/a/bla/socsci/v96y2015i2p639-655.html",
     None, "Craemer (2015) Social Science Quarterly 96(2) abstract (RePEc)"),
    ("hacker2020_pmc.html", "https://pmc.ncbi.nlm.nih.gov/articles/PMC7716878/",
     None, "Hacker (2020) Slavery & Abolition 41(4), full text (PMC7716878)"),
    ("nber_c0606_evans1962.pdf", "https://www.nber.org/system/files/chapters/c0606/c0606.pdf",
     None, "Evans (1962) 'The Economics of American Negro Slavery', NBER; p.188 fn.4 quotes De Bow 1850 occupation counts"),
    # NOTE: transportation.gov (US DOT VSL guidance) refuses scripted requests (HTTP 'Access Denied');
    # it was verified manually in a browser; see data/manual/source_verification_log.csv.
    ("us-atlas_states-albers-10m.json",
     "https://cdn.jsdelivr.net/npm/us-atlas@3.0.1/states-albers-10m.json",
     None, "us-atlas 3.0.1 (Census cartographic boundary 1:10m, Albers USA projected TopoJSON) for the map"),
]


def fetch(url, data):
    body = urllib.parse.urlencode(data, doseq=True).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=UA)
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def main():
    force = "--force" in sys.argv
    os.makedirs(RAW, exist_ok=True)
    manifest = {}
    for name, url, data, desc in SOURCES:
        path = os.path.join(RAW, name)
        if force or not os.path.exists(path):
            print("downloading", name)
            blob = fetch(url, data)
            with open(path, "wb") as f:
                f.write(blob)
        blob = open(path, "rb").read()
        manifest[name] = {"url": url, "post": data, "description": desc,
                          "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}
        print(f"  {name}: {len(blob):,} bytes")
    with open(os.path.join(RAW, "MANIFEST.json"), "w") as f:
        json.dump(manifest, f, indent=2)


if __name__ == "__main__":
    main()
