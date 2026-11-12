"""Run the full pipeline: fetch -> parse -> model -> QA -> docs (.md -> .html).
Usage: python scripts/run_all.py [--force]      (--force re-downloads sources)
Exits non-zero if any QA check FAILS (docs are still regenerated so the failing report can be read)."""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
qa_rc = 0
for step in ["00_fetch.py", "01_parse.py", "02_model.py", "03_qa.py", "04_docs.py"]:
    print(f"== {step}")
    args = [sys.executable, os.path.join(HERE, step)] + (sys.argv[1:] if step == "00_fetch.py" else [])
    rc = subprocess.run(args).returncode
    if step == "03_qa.py":
        qa_rc = rc
    elif rc:
        sys.exit(rc)
sys.exit(qa_rc)
