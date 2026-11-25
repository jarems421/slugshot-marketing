"""Audit externally supplied research reports (Stage 4.6 Gemini reports).

Stdlib only. Reads Markdown reports from a local, git-ignored source folder and writes
machine-readable audit files to data/local/research/<stage>/.

  python scripts/research_audit.py extract   [--src DIR] [--out DIR]
  python scripts/research_audit.py dedupe    [--out DIR]
  python scripts/research_audit.py dois      [--out DIR]     # Crossref lookups (cached)
  python scripts/research_audit.py urls      [--out DIR]     # HTTP reachability (cached)
  python scripts/research_audit.py claims    [--out DIR] --checks FILE   # needle checks against cached sources
  python scripts/research_audit.py all

Bibliographic resolution is not claim verification: a DOI that resolves proves the paper
exists, not that it says what the report says. `claims` only searches saved source text
for the specific figures a report attributes to it.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import hashlib
import html
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SRC = ROOT / "research" / "sources" / "stage-4.6"
DEFAULT_OUT = ROOT / "data" / "local" / "research" / "stage-4.6"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SlugshotResearchAudit/1.0 (owner research audit; contact via repo)"

ID_RE = re.compile(r"^(S46(\d))-([A-Z]+)(\d+[a-z]?)\b")
ANY_ID_RE = re.compile(r"\bS46(\d)-([A-Z]+)(\d+[a-z]?)\b")
DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s\]\[)(|,;\"<>]+", re.I)
URL_RE = re.compile(r"https?://[^\s\]\[)(|\"<>]+")
YEAR_RE = re.compile(r"\b(19[4-9]\d|20[0-2]\d)\b")

# Prefix meaning differs per report; mapped explicitly rather than guessed.
TYPE_MAP = {
    "default": {"E": "evidence", "C": "claim", "P": "principle", "H": "hypothesis", "B": "bridge",
                "K": "concept", "CON": "concept", "M": "mechanism", "REF": "culture_card",
                "COL": "collection_brief", "PR": "principle"},
    "2": {"P": "evidence", "K": "evidence", "PR": "principle", "CON": "concept"},   # 4.6.2: P=platform, K=cultural evidence
    "3": {"K": "culture_card"},                                                   # 4.6.3: K = dated cultural reference card
    "4": {"K": "concept"},
}
EVIDENCE_SUBKIND = {("2", "P"): "platform", ("2", "K"): "cultural"}


def item_type(stage: str, prefix: str) -> str:
    return TYPE_MAP.get(stage, {}).get(prefix) or TYPE_MAP["default"].get(prefix, "other")


def norm_doi(d: str) -> str:
    d = d.strip().rstrip(".,;:)]}'’").lower()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d)
    # URL path tails that are not part of the DOI (publisher landing pages)
    d = re.sub(r"(/full|/pdf|/abstract|/epdf|\.full-text|\.full)$", "", d)
    if d.startswith(("10.1101/", "10.64898/")):            # preprint version suffix, e.g. v2
        d = re.sub(r"v\d+$", "", d)
    d = re.sub(r"^(10\.1108/[a-z]+-\d{2}-\d{4}-\d{4})/.*$", r"", d)   # emerald /article-number/slug
    return d


def norm_url(u: str) -> str:
    u = html.unescape(u.strip()).rstrip(".,;:)]}'’")
    p = urllib.parse.urlsplit(u)
    host = p.netloc.lower().removeprefix("www.").removeprefix("m.")
    path = p.path.rstrip("/")
    q = p.query if host in ("youtube.com", "support.google.com", "ofcom.org.uk") else ""
    # keep only identity-bearing query parts
    if host == "support.google.com":
        q = ""
    if host == "youtube.com" and q:
        q = "&".join(x for x in q.split("&") if x.startswith("v="))
    return f"{host}{path}" + (f"?{q}" if q else "")


def source_family(url_or_doi: str, has_doi: bool) -> str:
    s = url_or_doi.lower()
    rules = [
        (("create.roblox.com", "devforum.roblox.com", "about.roblox.com", "en.help.roblox.com", "q4cdn.com",
          "sec.gov/archives/edgar/data/1315098", "ir.roblox.com"), "roblox_first_party"),
        (("support.google.com", "blog.youtube", "developers.google.com", "services.google.com"), "youtube_google_first_party"),
        (("about.fb.com", "developers.facebook.com", "creators.facebook.com"), "meta_first_party"),
        (("tiktok.com",), "tiktok_first_party"),
        (("pewresearch.org",), "pew"),
        (("ofcom.org.uk",), "ofcom"),
        (("datareportal.com",), "datareportal_kepios"),
        (("ftc.gov", "federalregister.gov", "gov.uk", "ico.org.uk", "eur-lex.europa.eu", "europarl.europa.eu",
          "judiciary.senate.gov", "asa.org.uk", "inegi.org.mx", "oficinac.es", "unicef.org", "digital-strategy.ec.europa.eu",
          "incibe", "castillalamancha.es"), "regulator_or_official_statistics"),
        (("reddit.com",), "community_reddit"),
        (("youtube.com/shorts", "youtube.com/watch", "youtube.com/@", "youtube.com/slugterra"), "youtube_public_content"),
        (("rolimons.com", "romonitorstats.com", "rivalducks.com", "geeiq.com"), "roblox_third_party_tracker"),
        (("vidiq.com", "nexlev.io"), "youtube_third_party_tracker"),
        (("wikipedia.org", "knowyourmeme.com", "fanlore.org", "fandom.com", "merriam-webster.com"), "community_reference"),
    ]
    for keys, fam in rules:
        if any(k in s for k in keys):
            return fam
    if has_doi:
        return "literature"
    return "web_secondary"


def label_hint(label: str) -> str:
    """Map an organisation named in a citation label to a domain-like hint for source_family()."""
    l = label.lower()
    hints = [("roblox", "create.roblox.com"), ("youtube help", "support.google.com"), ("google / youtube", "support.google.com"),
             ("meta", "about.fb.com"), ("instagram", "about.fb.com"), ("tiktok", "tiktok.com"), ("pew", "pewresearch.org"),
             ("ofcom", "ofcom.org.uk"), ("datareportal", "datareportal.com"), ("ftc", "ftc.gov"), ("uk gov", "gov.uk"),
             ("netflix", "web"), ("national youth", "inegi.org.mx"), ("regulatory", "gov.uk"), ("reddit", "reddit.com"),
             ("know your meme", "knowyourmeme.com"), ("wikipedia", "wikipedia.org"), ("vidiq", "vidiq.com"),
             ("rolimon", "rolimons.com"), ("geeiq", "geeiq.com"), ("rivalducks", "rivalducks.com")]
    return " ".join(h for k, h in hints if k in l)


def parse_reports(src: Path):
    reports, occurrences, refs, interface = [], [], [], []
    for path in sorted(src.glob("4.6.*-gemini-report.md")):
        stage = path.name.split("-")[0]          # 4.6.1
        code = stage.split(".")[-1]              # 1
        raw = path.read_bytes()
        lines = raw.decode("utf-8").splitlines()
        reports.append({"report": stage, "file": path.name, "sha256": hashlib.sha256(raw).hexdigest(),
                        "lines": len(lines), "words": len(raw.decode("utf-8").split())})
        section = ""
        heading_lines = []
        for i, line in enumerate(lines, 1):
            if line.startswith("#"):
                section = line.lstrip("#").strip()
                heading_lines.append(i)
            m = ID_RE.match(line)
            if m:
                full = f"{m.group(1)}-{m.group(3)}{m.group(4)}"
                kind = "bibliography" if re.match(r"^\S+\s+[—-]\s", line) else "row"
                occurrences.append({"report": stage, "code": code, "id": full, "prefix": m.group(3),
                                    "line": i, "section": section, "kind": kind})
            for d in DOI_RE.findall(line):
                refs.append({"report": stage, "line": i, "section": section, "type": "doi", "value": norm_doi(d)})
            for u in URL_RE.findall(line):
                if "doi.org/" in u:
                    continue
                refs.append({"report": stage, "line": i, "section": section, "type": "url", "value": html.unescape(u).rstrip(".,;:)]}'"),
                             "norm": norm_url(u)})
        # Gemini citation-interface trailer: "<domain>\n<title>\nOpens in a new window"
        for i, line in enumerate(lines):
            if line.strip() == "Opens in a new window":
                dom = lines[i - 2].strip() if i >= 2 else ""
                title = lines[i - 1].strip() if i >= 1 else ""
                if title and re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", title):   # domain with no title
                    dom, title = title, ""
                interface.append({"report": stage, "line": i + 1, "domain": dom, "title": title})
        yield_report = {"stage": stage, "code": code, "lines": lines, "headings": heading_lines}
        reports[-1]["_ctx"] = yield_report
    return reports, occurrences, refs, interface


def block_text(lines, start, headings, max_lines=45):
    """Lines from an ID row until the next ID row or heading."""
    out = []
    for j in range(start - 1, min(len(lines), start - 1 + max_lines)):
        if j > start - 1 and (ID_RE.match(lines[j]) or lines[j].startswith("#")):
            break
        out.append(lines[j])
    return "\n".join(out)


def cmd_extract(args):
    src, out = Path(args.src), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    reports, occ, refs, interface = parse_reports(src)
    items = {}
    for o in occ:
        ctx = next(r["_ctx"] for r in reports if r["report"] == o["report"])
        t = item_type(o["code"], o["prefix"])
        key = o["id"]
        if key not in items:
            items[key] = {"id": key, "report": o["report"], "type": t,
                          "subkind": EVIDENCE_SUBKIND.get((o["code"], o["prefix"]), "literature_or_mixed" if t == "evidence" else ""),
                          "first_line": o["line"], "section": o["section"], "occurrences": []}
        items[key]["occurrences"].append({"line": o["line"], "kind": o["kind"], "section": o["section"]})
    for it in items.values():
        ctx = next(r["_ctx"] for r in reports if r["report"] == it["report"])
        rows = [x for x in it["occurrences"] if x["kind"] == "row"] or it["occurrences"]
        txt = block_text(ctx["lines"], rows[0]["line"], ctx["headings"])
        bib = [x for x in it["occurrences"] if x["kind"] == "bibliography"]
        if bib:
            txt += "\n" + ctx["lines"][bib[0]["line"] - 1]
        it["block_end_line"] = rows[0]["line"] + txt.count("\n")
        it["text"] = txt
        it["dois"] = sorted({norm_doi(d) for d in DOI_RE.findall(txt)})
        it["urls"] = sorted({html.unescape(u).rstrip(".,;:)]}'") for u in URL_RE.findall(txt) if "doi.org/" not in u})
        src_line = next((l for l in txt.split("\n")[1:] if l.strip()), "")
        it["source_line"] = src_line.strip()[:400]
        sm = re.match(r"\s*([A-ZÀ-Ý][A-Za-zÀ-ÿ'’\-]+)", src_line)
        it["first_author_guess"] = sm.group(1) if sm and it["type"] == "evidence" else ""
        ym = YEAR_RE.search(src_line)
        it["year_guess"] = ym.group(1) if ym and it["type"] == "evidence" else ""
        refs_in = set()
        for m in ANY_ID_RE.finditer(txt):
            refs_in.add(f"S46{m.group(1)}-{m.group(2)}{m.group(3)}")
        # short forms like "C003, C004" or "P001" inside the same report
        code = it["report"].split(".")[-1]
        for m in re.finditer(r"(?<![\w-])(E|C|P|H|B|K|CON|PR|REF|M|COL)(\d{2,3}[a-z]?)\b", txt):
            cand = f"S46{code}-{m.group(1)}{m.group(2)}"
            if cand in items or any(o["id"] == cand for o in occ):
                refs_in.add(cand)
        refs_in.discard(it["id"])
        it["refs"] = sorted(refs_in)
        cells = [c.strip() for c in txt.split("\t")]
        it["cells"] = cells[:14]
        if it["type"] == "claim":
            it.update(parse_claim_cells(cells))
    for r in reports:
        r.pop("_ctx")
    inv = sorted(items.values(), key=lambda x: (x["report"], x["first_line"]))
    (out / "inventory.json").write_text(json.dumps({"reports": reports, "items": inv}, indent=1, ensure_ascii=False), "utf-8")
    with open(out / "inventory.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "report", "type", "subkind", "first_line", "block_end_line", "section", "n_occurrences",
                    "dois", "n_urls", "first_author_guess", "year_guess", "refs", "source_line"])
        for it in inv:
            w.writerow([it["id"], it["report"], it["type"], it["subkind"], it["first_line"], it["block_end_line"],
                        it["section"], len(it["occurrences"]), ";".join(it["dois"]), len(it["urls"]),
                        it["first_author_guess"], it["year_guess"], ";".join(it["refs"]), it["source_line"][:200]])
    with open(out / "reference_occurrences.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["report", "line", "section", "type", "value", "norm"])
        w.writeheader()
        for r in refs:
            w.writerow({**r, "norm": r.get("norm", r["value"])})
    with open(out / "interface_citations.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["report", "line", "domain", "title"])
        w.writeheader()
        w.writerows(interface)
    counts = defaultdict(lambda: defaultdict(int))
    for it in inv:
        counts[it["report"]][it["type"]] += 1
    print(json.dumps({k: dict(v) for k, v in counts.items()}, indent=1))
    print(f"items={len(inv)} ref_occurrences={len(refs)} interface_citations={len(interface)}")


LEVELS = {"O", "D", "P", "I", "C", "R"}
SUPPORT = {"supported", "partially_supported", "unsupported", "indeterminate"}
STRENGTH = {"exploratory", "suggestive", "supported_descriptive", "convergent", "experimental"}


def parse_claim_cells(cells):
    out = {"claim_text": "", "level": "", "support_status": "", "strength": ""}
    if len(cells) > 1:
        out["claim_text"] = cells[1].strip()
    for c in cells[2:8]:
        c0 = c.split("\n")[0].strip()
        lv = re.match(r"^([ODPICR])(\s*/\s*[ODPICR])*\b", c0)
        if not out["level"] and lv and len(c0) < 40:
            out["level"] = c0
        elif not out["support_status"] and c0.split(" ")[0] in SUPPORT:
            out["support_status"] = c0
        elif not out["strength"] and c0.split(" ")[0] in STRENGTH:
            out["strength"] = c0
    if not out["level"] and out["claim_text"]:
        # some reports put the level on the last line of the claim-text cell
        parts = [p for p in out["claim_text"].split("\n") if p.strip()]
        if len(parts) > 1 and re.match(r"^[ODPICR](\s*/\s*[ODPICR])*(\s*\(.*\))?$", parts[-1].strip()):
            out["level"] = parts[-1].strip()
            out["claim_text"] = "\n".join(parts[:-1]).strip()
    out["claim_text"] = re.sub(r"\s+", " ", out["claim_text"]).strip()
    return out


def cmd_dedupe(args):
    out = Path(args.out)
    inv = json.loads((out / "inventory.json").read_text("utf-8"))
    ev = [i for i in inv["items"] if i["type"] == "evidence"]
    parent = {e["id"]: e["id"] for e in ev}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b, basis, links):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
        links.append({"a": a, "b": b, "basis": basis})

    links = []
    items_by_id = {e["id"]: e for e in ev}
    by_key = defaultdict(list)
    for e in ev:
        for d in e["dois"]:
            by_key[("doi", d)].append(e["id"])
        for u in e["urls"]:
            n = norm_url(u)
            if len(n.split("/")) > 1 and not n.endswith(("youtube.com", "reddit.com")):
                by_key[("url", n)].append(e["id"])
    for (kind, k), ids in by_key.items():
        ids = sorted(set(ids))
        for x in ids[1:]:
            union(ids[0], x, f"{kind}:{k}", links)
    # probable same work: same first-author surname + year, both literature, different reports, no DOI conflict
    probable = []
    lit = [e for e in ev if e["first_author_guess"] and e["year_guess"]]
    for i, a in enumerate(lit):
        for b in lit[i + 1:]:
            if a["first_author_guess"].lower() == b["first_author_guess"].lower() and a["year_guess"] == b["year_guess"] \
                    and find(a["id"]) != find(b["id"]):
                if a["dois"] and b["dois"] and not set(a["dois"]) & set(b["dois"]):
                    continue
                probable.append({"a": a["id"], "b": b["id"], "basis": f"author_year:{a['first_author_guess']} {a['year_guess']}"})
    # merge author-year pairs for scholarly works only; organisations publish many documents per year
    orgs = {"roblox", "tiktok", "youtube", "meta", "google", "pew", "ofcom", "instagram", "platform", "official",
            "public", "national", "preregistered", "university", "dual-task", "event", "short-form", "negative"}
    for p in probable:
        a_, b_ = items_by_id[p["a"]], items_by_id[p["b"]]
        p["merged"] = a_["first_author_guess"].lower() not in orgs
        if p["merged"]:
            union(p["a"], p["b"], p["basis"], links)
    clusters = defaultdict(list)
    for e in ev:
        clusters[find(e["id"])].append(e)
    register = []
    for n, (root, members) in enumerate(sorted(clusters.items(), key=lambda kv: kv[0]), 1):
        dois = sorted({d for m in members for d in m["dois"]})
        urls = sorted({u for m in members for u in m["urls"]})
        fam = source_family(" ".join(urls[:3]) + " " + " ".join(dois) + " " + label_hint(members[0]["source_line"]), bool(dois))
        if dois and fam == "web_secondary":
            fam = "literature"
        register.append({"source_id": f"SRC-{n:03d}", "member_ids": [m["id"] for m in members],
                         "reports": sorted({m["report"] for m in members}), "n_reports": len({m["report"] for m in members}),
                         "dois": dois, "n_urls": len(urls), "urls": urls[:12], "family": fam,
                         "label": members[0]["source_line"][:160]})
    (out / "source_register.json").write_text(json.dumps({"sources": register, "links": links, "probable_duplicates": probable},
                                                         indent=1, ensure_ascii=False), "utf-8")
    with open(out / "source_register.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source_id", "member_ids", "reports", "n_reports", "family", "dois", "n_urls", "label"])
        for r in register:
            w.writerow([r["source_id"], ";".join(r["member_ids"]), ";".join(r["reports"]), r["n_reports"], r["family"],
                        ";".join(r["dois"]), r["n_urls"], r["label"]])
    with open(out / "dedupe_mapping.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["evidence_id", "source_id"])
        for r in register:
            for m in r["member_ids"]:
                w.writerow([m, r["source_id"]])
    multi = [r for r in register if r["n_reports"] > 1]
    print(f"evidence_entries={len(ev)} unique_sources={len(register)} cross_report_sources={len(multi)} "
          f"probable_author_year_pairs={len(probable)}")


def http_get(url, timeout=25, accept=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept or "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.geturl(), r.headers.get("Content-Type", ""), r.read(80_000_000)


def cmd_dois(args):
    out = Path(args.out)
    cache = out / "cache" / "crossref"
    cache.mkdir(parents=True, exist_ok=True)
    inv = json.loads((out / "inventory.json").read_text("utf-8"))
    ev_by_doi = defaultdict(list)
    for it in inv["items"]:
        for d in it["dois"]:
            ev_by_doi[d].append(it)
    occ = list(csv.DictReader(open(out / "reference_occurrences.csv", encoding="utf-8")))
    all_dois = sorted({r["value"] for r in occ if r["type"] == "doi"} | set(ev_by_doi))
    texts = defaultdict(str)
    srcdir = Path(args.src)
    lines_by_report = {p.name.split("-")[0]: p.read_text("utf-8").splitlines() for p in srcdir.glob("4.6.*-gemini-report.md")}
    for r in occ:
        if r["type"] == "doi":
            texts[r["value"]] += "\n" + lines_by_report[r["report"]][int(r["line"]) - 1]
    for d, its in ev_by_doi.items():
        texts[d] += "\n" + "\n".join(i["text"] for i in its)

    def fetch(d):
        f = cache / (hashlib.sha1(d.encode()).hexdigest() + ".json")
        if f.exists():
            return d, json.loads(f.read_text("utf-8"))
        rec = {"doi": d}
        try:
            st, _, _, body = http_get("https://api.crossref.org/works/" + urllib.parse.quote(d, safe="/:;()"),
                                      accept="application/json")
            msg = json.loads(body)["message"]
            rec.update({"registry": "crossref", "status": "resolved", "title": " ".join(msg.get("title") or []),
                        "authors": [a.get("family", a.get("name", "")) for a in msg.get("author", [])][:12],
                        "year": ((msg.get("issued") or {}).get("date-parts") or [[None]])[0][0],
                        "container": " ".join(msg.get("container-title") or []), "type": msg.get("type")})
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(3)
                return fetch(d)
            rec.update({"status": f"crossref_http_{e.code}"})
            try:   # DataCite / other registries via doi.org handle API
                st, _, _, body = http_get("https://doi.org/api/handles/" + urllib.parse.quote(d, safe="/"), accept="application/json")
                h = json.loads(body)
                rec.update({"registry": "doi.org_handle", "status": "resolved" if h.get("responseCode") == 1 else "unresolved"})
                if h.get("responseCode") == 1:
                    try:
                        st2, _, _, b2 = http_get("https://api.datacite.org/dois/" + urllib.parse.quote(d, safe="/"), accept="application/json")
                        a = json.loads(b2)["data"]["attributes"]
                        rec.update({"registry": "datacite", "title": " ".join(t.get("title", "") for t in a.get("titles", [])),
                                    "authors": [c.get("familyName", c.get("name", "")) for c in a.get("creators", [])][:12],
                                    "year": a.get("publicationYear")})
                    except Exception:
                        pass
            except urllib.error.HTTPError as e2:
                rec.update({"registry": "none", "status": "unresolved", "handle_http": e2.code})
            except Exception as e2:
                rec.update({"status": "error", "error": str(e2)[:200]})
        except Exception as e:
            rec.update({"status": "error", "error": str(e)[:200]})
        if rec.get("status") != "error":
            f.write_text(json.dumps(rec, ensure_ascii=False), "utf-8")
        time.sleep(0.15)
        return d, rec

    with cf.ThreadPoolExecutor(2) as ex:
        results = dict(ex.map(fetch, all_dois))
    rows = []
    for d in all_dois:
        rec = results[d]
        t = texts[d]
        tl = fold(t)
        title_overlap = author_hit = year_hit = None
        if rec.get("status") == "resolved" and rec.get("title"):
            tw = [w for w in re.findall(r"[a-z]{4,}", fold(rec["title"]))]
            title_overlap = round(sum(1 for w in set(tw) if w in tl) / max(1, len(set(tw))), 2) if tw else None
        if rec.get("authors"):
            author_hit = any(a and fold(a) in tl for a in rec["authors"][:3])
        if rec.get("year"):
            year_hit = str(rec["year"]) in t or str(int(rec["year"]) - 1) in t or str(int(rec["year"]) + 1) in t
        verdict = doi_verdict(rec, title_overlap, author_hit, year_hit)
        rows.append({"doi": d, "status": rec.get("status"), "registry": rec.get("registry", ""), "verdict": verdict,
                     "record_title": rec.get("title", "")[:200], "record_authors": ";".join(rec.get("authors", [])[:5]),
                     "record_year": rec.get("year", ""), "record_container": rec.get("container", "")[:120],
                     "title_word_overlap": title_overlap, "first3_author_in_report": author_hit, "year_within_1": year_hit,
                     "evidence_ids": ";".join(sorted({i["id"] for i in ev_by_doi.get(d, [])})),
                     "reports": ";".join(sorted({r["report"] for r in occ if r["type"] == "doi" and r["value"] == d}))})
    with open(out / "doi_verification.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    tally = defaultdict(int)
    for r in rows:
        tally[r["verdict"]] += 1
    print(f"unique_dois={len(rows)}", dict(tally))


def fold(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def doi_verdict(rec, overlap, author, year):
    if rec.get("status") == "error":
        return "lookup_error"
    if rec.get("status") != "resolved":
        return "does_not_resolve"
    if overlap is None and author is None:
        return "resolves_no_metadata"
    bad = []
    if author is False:
        bad.append("author")
    if overlap is not None and overlap < 0.4:
        bad.append("title")
    if year is False:
        bad.append("year")
    if not bad:
        return "match"
    if bad == ["title"] and author:
        return "match_author_title_unstated"   # report often paraphrases titles
    return "mismatch_" + "_".join(bad)


def cmd_urls(args):
    out = Path(args.out)
    cache = out / "cache" / "pages"
    cache.mkdir(parents=True, exist_ok=True)
    occ = list(csv.DictReader(open(out / "reference_occurrences.csv", encoding="utf-8")))
    urls = {}
    for r in occ:
        if r["type"] == "url":
            urls.setdefault(r["norm"], r["value"])
    if args.limit:
        urls = dict(list(urls.items())[: args.limit])

    def check(item):
        norm, url = item
        key = hashlib.sha1(norm.encode()).hexdigest()
        meta_f = cache / f"{key}.meta.json"
        if meta_f.exists():
            return json.loads(meta_f.read_text("utf-8"))
        meta = {"norm": norm, "url": url}
        try:
            st, final, ctype, body = http_get(url, timeout=25)
            meta.update({"http": st, "final_url": final, "content_type": ctype.split(";")[0], "bytes": len(body)})
            text = extract_text(body, ctype, cache / key)
            (cache / f"{key}.txt").write_text(text, "utf-8")
            meta["text_chars"] = len(text)
            m = re.search(r"<title[^>]*>(.*?)</title>", body[:200000].decode("utf-8", "ignore"), re.I | re.S)
            meta["page_title"] = html.unescape(m.group(1)).strip()[:200] if m else ""
            meta["outcome"] = "ok"
        except urllib.error.HTTPError as e:
            meta.update({"http": e.code, "outcome": {404: "not_found", 410: "gone"}.get(e.code,
                         "blocked_or_auth" if e.code in (401, 403, 429, 999) else "http_error")})
        except Exception as e:
            meta.update({"http": None, "outcome": "network_error", "error": str(e)[:160]})
        if meta["outcome"] != "network_error":
            meta_f.write_text(json.dumps(meta, ensure_ascii=False), "utf-8")
        return meta

    with cf.ThreadPoolExecutor(12) as ex:
        res = list(ex.map(check, urls.items()))
    with open(out / "url_checks.csv", "w", newline="", encoding="utf-8") as f:
        fields = ["norm", "url", "outcome", "http", "final_url", "content_type", "bytes", "text_chars", "page_title", "error"]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(res)
    tally = defaultdict(int)
    for r in res:
        tally[r["outcome"]] += 1
    print(f"unique_urls={len(res)}", dict(tally))


def extract_text(body: bytes, ctype: str, stem: Path) -> str:
    if b"%PDF" in body[:1024] or "pdf" in ctype:
        pdf = stem.with_suffix(".pdf")
        pdf.write_bytes(body)
        try:
            return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, timeout=120).stdout.decode("utf-8", "ignore")
        except Exception:
            return ""
    t = body.decode("utf-8", "ignore")
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t))


def cmd_claims(args):
    """Search cached source text for the figures a report attributes to it.

    checks file: JSON list of {check_id, report_ids[], claim, urls[], needles[] (all must be found
    in at least one source), any_needles[] (optional, at least one), note}
    """
    out = Path(args.out)
    cache = out / "cache" / "pages"
    checks = json.loads(Path(args.checks).read_text("utf-8"))
    rows = []
    for c in checks:
        found_in, misses, snippets, fetched = [], set(c.get("needles", [])), {}, []
        for url in c["urls"]:
            key = hashlib.sha1(norm_url(url).encode()).hexdigest()
            tf, mf = cache / f"{key}.txt", cache / f"{key}.meta.json"
            if not tf.exists():
                try:
                    st, final, ctype, body = http_get(url)
                    tf.write_text(extract_text(body, ctype, cache / key), "utf-8")
                    mf.write_text(json.dumps({"norm": norm_url(url), "url": url, "http": st, "outcome": "ok"}), "utf-8")
                except urllib.error.HTTPError as e:
                    fetched.append(f"{url} -> HTTP {e.code}")
                    continue
                except Exception as e:
                    fetched.append(f"{url} -> {type(e).__name__}")
                    continue
            text = re.sub(r"\s+", " ", tf.read_text("utf-8"))
            fetched.append(f"{url} -> {len(text)} chars")
            tn = fold(text)
            for n in list(misses):
                p = tn.find(fold(n))
                if p >= 0:
                    misses.discard(n)
                    snippets[n] = text[max(0, p - 140): p + 160]
                    found_in.append(url)
            for n in c.get("any_needles", []):
                p = tn.find(fold(n))
                if p >= 0 and n not in snippets:
                    snippets[n] = text[max(0, p - 140): p + 160]
        any_ok = (not c.get("any_needles")) or any(n in snippets for n in c["any_needles"])
        reachable = any("chars" in f for f in fetched)
        if not reachable:
            status = "source_unreachable"
        elif not misses and any_ok:
            status = "figures_found"
        elif len(misses) < len(c.get("needles", [])) or (c.get("any_needles") and any_ok):
            status = "partially_found"
        else:
            status = "figures_not_found"
        rows.append({"check_id": c["check_id"], "report_ids": ";".join(c["report_ids"]), "claim": c["claim"],
                     "status": status, "missing_needles": ";".join(sorted(misses)),
                     "snippets": json.dumps(snippets, ensure_ascii=False)[:3000], "fetched": " | ".join(fetched),
                     "note": c.get("note", "")})
    with open(out / "claim_checks.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    tally = defaultdict(int)
    for r in rows:
        tally[r["status"]] += 1
    print(f"checks={len(rows)}", dict(tally))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["extract", "dedupe", "dois", "urls", "claims", "all"])
    ap.add_argument("--src", default=str(DEFAULT_SRC))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--checks")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args(argv)
    if a.cmd in ("extract", "all"):
        cmd_extract(a)
    if a.cmd in ("dedupe", "all"):
        cmd_dedupe(a)
    if a.cmd in ("dois", "all"):
        cmd_dois(a)
    if a.cmd in ("urls", "all"):
        cmd_urls(a)
    if a.cmd == "claims":
        cmd_claims(a)


if __name__ == "__main__":
    sys.exit(main())
