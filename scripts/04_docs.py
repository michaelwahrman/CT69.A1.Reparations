"""Shadow every .md file in the project with a self-contained .html file (Harness rule).  Standard library only.
Supports the Markdown used here: headings, paragraphs, bold/italic, inline code, links, fenced code, lists, tables, rules."""
import html, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = """:root{--bg:#fcfcfb;--ink:#0b0b0b;--muted:#52514e;--line:#dddcd6;--code:#f0efec;--a:#2a78d6;--pass:#0a7a3d;--fail:#b3261e}
@media (prefers-color-scheme:dark){:root{--bg:#1a1a19;--ink:#f0efec;--muted:#c3c2b7;--line:#33332f;--code:#262624;--a:#6da7ec;--pass:#5fd08f;--fail:#ff8a80}}
body{background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;max-width:1100px;margin:0 auto;padding:24px 16px 60px}
h1{font-size:24px}h2{font-size:19px;margin-top:28px;border-bottom:1px solid var(--line);padding-bottom:4px}h3{font-size:16px}
a{color:var(--a)}code{background:var(--code);padding:1px 4px;border-radius:4px;font-size:.92em}pre{background:var(--code);padding:10px 12px;border-radius:6px;overflow:auto}
pre code{background:none;padding:0}.tw{overflow-x:auto}table{border-collapse:collapse;font-size:13px;margin:10px 0}
th,td{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}th{color:var(--muted)}
.PASS{color:var(--pass);font-weight:700}.FAIL{color:var(--fail);font-weight:700}hr{border:0;border-top:1px solid var(--line)}"""


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*([^*]+)\*(?!\w)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: f'<a href="{m.group(2).replace(".md", ".html") if m.group(2).endswith(".md") and "://" not in m.group(2) else m.group(2)}">{m.group(1)}</a>', s)
    s = re.sub(r"<strong>(PASS|FAIL)</strong>", r'<strong class="\1">\1</strong>', s)
    return s


def convert(md):
    out, lines, i = [], md.split("\n"), 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(lines[i + 1:j])) + "</code></pre>"); i = j + 1; continue
        if re.match(r"#{1,6} ", l):
            n = len(l.split(" ")[0]); out.append(f"<h{n}>{inline(l[n+1:])}</h{n}>"); i += 1; continue
        if l.strip() == "---":
            out.append("<hr>"); i += 1; continue
        if l.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            t = ['<div class="tw"><table>', "<tr>" + "".join(f"<th>{inline(c)}</th>" for c in rows[0]) + "</tr>"]
            for r in rows[2:]:
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            out.append("\n".join(t) + "</table></div>"); continue
        if re.match(r"\s*([-*]|\d+\.) ", l):
            tag = "ol" if re.match(r"\s*\d+\.", l) else "ul"; items = []
            while i < len(lines) and re.match(r"\s*([-*]|\d+\.) ", lines[i]):
                items.append(re.sub(r"^\s*([-*]|\d+\.) ", "", lines[i])); i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>"); continue
        if l.strip() == "":
            i += 1; continue
        para = [l]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"(#|\||```|\s*([-*]|\d+\.) |---)", lines[i]):
            para.append(lines[i]); i += 1
        out.append("<p>" + inline(" ".join(para)) + "</p>")
    return "\n".join(out)


def main():
    n = 0
    for d, _, files in os.walk(ROOT):
        if any(p in d for p in (os.sep + "data", os.sep + "lib", os.sep + ".")):
            continue
        for f in files:
            if f.endswith(".md"):
                src = os.path.join(d, f)
                md = open(src, encoding="utf-8").read()
                title = (re.search(r"^# (.+)$", md, re.M) or [None, f])[1]
                page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                        f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body>\n"
                        f"<!-- generated from {f} by scripts/04_docs.py; edit the .md, not this file -->\n{convert(md)}\n</body></html>\n")
                open(src[:-3] + ".html", "w", encoding="utf-8").write(page); n += 1
    print(f"docs: {n} .md files shadowed as .html")


if __name__ == "__main__":
    main()
