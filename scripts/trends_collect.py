"""Google Trends, two credential-free official routes (no pytrends, no private endpoints).

  rss [--geo GB,MX]     Trending Now RSS (trends.google.com/trending/rss?geo=XX, the feed behind the
                        Trending Now page's Export > RSS): trending searches, approximate traffic, start time,
                        linked news. ALL searches in that country, not gaming-specific.
  import FILE...        validate and store CSVs downloaded by hand from trends.google.com/explore:
                        interest over time, interest by region/subregion, related queries/topics (top + rising)
  imports               list what has been imported
  report                export both stores -> exports/share/research/

Normalisation: every Explore download is scaled 0-100 against the highest point among ITS OWN terms,
geo, window, category and search type. Values from two downloads are not on the same scale and must not be
compared directly; each row carries `import_id` and `normalisation_scope` so they stay apart.
"<1" is kept as written (value_numeric blank, value_kind less_than_one). "Breakout" and "+250%" in related
queries are growth labels, not 0-100 values (value_kind breakout / percent_increase).
--dry-run reads tests/fixtures/research/trends_rss_<GEO>.xml and writes to data/local/research/dryrun/.
"""
import argparse
import csv
import io
import re
import sys
import xml.etree.ElementTree as ET
from datetime import timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

import research_common as rc

RSS = "https://trends.google.com/trending/rss"
HT = "{https://trends.google.com/trending/rss}"
RSS_FIELDS = ["geo", "position", "term", "approx_traffic", "approx_traffic_lower_bound", "trend_started_at_utc",
              "news_titles", "news_urls", "news_sources", "observed_at_utc", "run_id", "expires_at_utc"]
IMPORT_FIELDS = ["import_id", "source_file", "sha256", "export_type", "terms", "geo", "geo_label", "subregion",
                 "window", "window_source", "category", "search_type", "normalisation_scope", "downloaded_at_utc",
                 "downloaded_at_source", "imported_at_utc", "rows", "warnings"]
VALUE_FIELDS = ["import_id", "export_type", "term", "geo", "geo_label", "window", "category", "search_type", "period",
                "region_name", "section", "query", "value_raw", "value_numeric", "value_kind", "downloaded_at_utc"]
RSS_COLUMNS = [
    ("geo", "request", "country code the feed was requested for (search geography)"),
    ("position", "Google", "order in the feed at observation (1 = first listed); not an official rank"),
    ("term", "Google", "trending search term"),
    ("approx_traffic", "Google", "Google's approximate search volume band, as shown (e.g. 500+)"),
    ("approx_traffic_lower_bound", "derived", "the number in approx_traffic (a lower bound, not a count)"),
    ("trend_started_at_utc", "Google", "when Google says the trend started (pubDate), UTC"),
    ("news_titles", "Google", "linked news headlines, | separated"),
    ("news_urls", "Google", "linked news URLs, | separated"),
    ("news_sources", "Google", "news outlets, | separated"),
    ("observed_at_utc", "local", "when the feed was read"),
]
VALUE_COLUMNS = [
    ("import_id", "local", "one Explore download; values are only comparable within the same import_id"),
    ("export_type", "local", "interest_over_time / interest_by_region / related_queries / related_topics"),
    ("term", "Google", "search term or topic as written in the file header"),
    ("geo", "import", "country/subregion code given at import (blank if not given)"),
    ("geo_label", "Google", "geography as written in the file header, e.g. Mexico"),
    ("window", "import/Google", "time range of the download"),
    ("category", "Google/import", "Trends category of the download"),
    ("search_type", "import", "web / youtube / images / news / froogle, as given at import (blank if not given)"),
    ("period", "Google", "date or week start (interest over time)"),
    ("region_name", "Google", "region/subregion/city (interest by region)"),
    ("section", "Google", "top or rising (related queries/topics)"),
    ("query", "Google", "related query or topic"),
    ("value_raw", "Google", "the value exactly as in the file"),
    ("value_numeric", "derived", "the number when value_raw is a plain 0-100 index or a percentage; else blank"),
    ("value_kind", "derived", "index_0_100 / less_than_one / percent_increase / breakout / missing"),
    ("downloaded_at_utc", "import", "when the CSV was downloaded (given, or the file's modified time)"),
]
DATE_HEADS = {"day", "week", "month", "time", "date", "día", "semana", "mes", "fecha", "hora"}
REGION_HEADS = {"region", "country", "subregion", "city", "metro", "dma", "región", "país", "ciudad", "subregión"}


class Trends:
    def __init__(self, a):
        self.dry = a.dry_run
        self.dir = Path(a.data_dir) if a.data_dir else rc.DATA / ("dryrun" if a.dry_run else "") / "google_trends"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.rss = self.dir / "trending_now.csv"
        self.imports = self.dir / "explore_imports.csv"
        self.values = self.dir / "explore_values.csv"


def cmd_rss(a, t):
    geos = [g.strip().upper() for g in (a.geo.split(",") if a.geo else rc.settings()["trends"]["geos"]) if g.strip()]
    run = rc.Run("google_trends", "rss", {"geos": geos}, a.dry_run, a.data_dir)
    observed = rc.now()
    keep_days = rc.settings()["trends"]["rss_retention_days"]
    rows = []
    for geo in geos:
        try:
            body = rc.fixture(f"trends_rss_{geo}.xml") if a.dry_run else rc.http(RSS, {"geo": geo})[0]
            run.ok += 1
        except (rc.HttpError, FileNotFoundError) as e:
            run.failed += 1
            print(f"  {geo}: FAILED ({e})")
            continue
        items = ET.fromstring(body).findall("./channel/item")
        for n, it in enumerate(items, 1):
            news = it.findall(f"{HT}news_item")
            pub = it.findtext("pubDate")
            traffic = it.findtext(f"{HT}approx_traffic") or ""
            lb = re.sub(r"[^\d]", "", traffic)
            rows.append({"geo": geo, "position": n, "term": (it.findtext("title") or "").strip(), "approx_traffic": traffic,
                         "approx_traffic_lower_bound": lb,
                         "trend_started_at_utc": rc.iso(parsedate_to_datetime(pub)) if pub else "",
                         "news_titles": "|".join((x.findtext(f"{HT}news_item_title") or "").strip() for x in news),
                         "news_urls": "|".join((x.findtext(f"{HT}news_item_url") or "").strip() for x in news),
                         "news_sources": "|".join((x.findtext(f"{HT}news_item_source") or "").strip() for x in news),
                         "observed_at_utc": rc.iso(observed), "run_id": run.id,
                         "expires_at_utc": rc.iso(observed + timedelta(days=keep_days))})
        print(f"  {geo}: {len(items)} trending searches")
    rc.prune_file(t.rss, RSS_FIELDS)
    rc.append_rows(t.rss, RSS_FIELDS, rows)
    run.rows = len(rows)
    run.finish("ok" if not run.failed else "partial")
    print(f"{len(rows)} rows -> {t.rss} [run {run.id}]")


# ---------- Explore CSV import ----------

def value_kind(raw):
    s = raw.strip()
    if s == "":
        return "", "missing"
    if s.startswith("<"):
        return "", "less_than_one"
    if s.lower() in ("breakout", "aumento puntual", "fuerte aumento"):
        return "", "breakout"
    m = re.fullmatch(r"\+?([\d,.]+)\s*%", s)
    if m:
        return m.group(1).replace(",", ""), "percent_increase"
    if re.fullmatch(r"\d{1,3}", s):
        return s, "index_0_100"
    return "", "unrecognised"


def split_header(cell):
    """'Roblox: (Mexico)' -> ('Roblox', 'Mexico'); 'Roblox: (24/11/2025 - 24/11/2026)' -> ('Roblox', that window)."""
    m = re.fullmatch(r"(.*?):\s*\((.*)\)\s*", cell)
    return (m.group(1).strip(), m.group(2).strip()) if m else (cell.strip(), "")


def parse_explore(text):
    """Returns (export_type, meta, rows) where rows are dicts with term/period/region_name/section/query/value_raw."""
    lines = text.lstrip("﻿").splitlines()
    meta = {}
    body = []
    for line in lines:
        m = re.match(r"\s*(Category|Categoría)\s*:\s*(.*)", line)
        if m and not body:
            meta["category"] = m.group(2).strip()
            continue
        body.append(line)
    rows_in = [r for r in csv.reader(io.StringIO("\n".join(body)))]
    rows_in = [r for r in rows_in if any(c.strip() for c in r)]
    if not rows_in:
        raise ValueError("no data rows found")
    sections = {"TOP", "RISING", "PRINCIPALES", "EN AUMENTO"}
    if any(len(r) == 1 and r[0].strip().upper() in sections for r in rows_in):
        out, section = [], None
        kind = "related_queries"
        for r in rows_in:
            cell = r[0].strip()
            if len(r) == 1 and cell.upper() in sections:
                section = "top" if cell.upper() in ("TOP", "PRINCIPALES") else "rising"
                continue
            if cell.lower() in ("query", "topic", "consulta", "tema"):
                kind = "related_topics" if cell.lower() in ("topic", "tema") else kind
                meta.setdefault("terms", [split_header(c)[0] for c in r[1:]])
                continue
            if section and len(r) >= 2:
                out.append({"section": section, "query": cell, "value_raw": r[1].strip(),
                            "term": (meta.get("terms") or [""])[0]})
        return kind, meta, out
    head = rows_in[0]
    first = head[0].strip().lower()
    series = [split_header(c) for c in head[1:]]
    meta["terms"] = [s[0] for s in series]
    labels = {s[1] for s in series if s[1]}
    if first in DATE_HEADS:
        kind = "interest_over_time"
        meta["geo_label"] = "; ".join(sorted(labels))
    elif first in REGION_HEADS:
        kind = "interest_by_region"
        meta["window_from_header"] = "; ".join(sorted(labels))
        meta["region_level"] = first
    else:
        raise ValueError(f"unrecognised first column '{head[0]}' (expected a date or region column)")
    out = []
    for n, r in enumerate(rows_in[1:], 2):
        if len(r) != len(head):
            raise ValueError(f"data row {n} has {len(r)} cells, header has {len(head)}")
        if kind == "interest_over_time" and not re.match(r"\d{4}-\d{2}(-\d{2})?", r[0].strip()):
            raise ValueError(f"data row {n}: '{r[0]}' is not a date")
        for (term, _), raw in zip(series, r[1:]):
            out.append({"term": term, "value_raw": raw.strip(),
                        ("period" if kind == "interest_over_time" else "region_name"): r[0].strip()})
    if kind == "interest_over_time" and out:
        periods = sorted({x["period"] for x in out})
        meta["window_from_rows"] = f"{periods[0]} to {periods[-1]}"
    return kind, meta, out


def cmd_import(a, t):
    done = {r["sha256"] for r in rc.read_rows(t.imports)}
    run = rc.Run("google_trends", "import", {"files": a.files, "geo": a.geo, "window": a.window}, a.dry_run, a.data_dir)
    total = 0
    for f in a.files:
        p = Path(f)
        if not p.exists():
            print(f"  {f}: not found")
            run.failed += 1
            continue
        digest = rc.sha256(p)
        if digest in done:
            print(f"  {p.name}: already imported (same file contents); skipped")
            continue
        try:
            kind, meta, rows = parse_explore(p.read_text(encoding="utf-8-sig"))
        except (ValueError, UnicodeDecodeError) as e:
            print(f"  {p.name}: REJECTED - {e}")
            run.failed += 1
            continue
        warnings = []
        window = a.window or meta.get("window_from_header") or meta.get("window_from_rows", "")
        window_source = "given" if a.window else ("file header" if meta.get("window_from_header") else
                                                  ("derived from first/last row" if window else ""))
        if not a.window and kind.startswith("related"):
            warnings.append("window not in file; pass --window")
        if not a.geo:
            warnings.append("geo code not given (geo_label from the header is kept)" if meta.get("geo_label") else
                            "geo not given and not in the file; pass --geo")
        if not a.search_type:
            warnings.append("search type not given (web, youtube, images, news, froogle); left blank")
        if a.downloaded_at:
            dl, dl_src = rc.iso(rc.parse_time(a.downloaded_at)), "given"
        else:
            from datetime import datetime, timezone
            dl, dl_src = rc.iso(datetime.fromtimestamp(p.stat().st_mtime, timezone.utc)), "file modified time"
            warnings.append("download time taken from the file's modified time; pass --downloaded-at if that's wrong")
        category = a.category or meta.get("category", "")
        terms = a.terms or "|".join(meta.get("terms", []))
        import_id = f"gt-{digest[:12]}"
        scope = (f"0-100 relative to the highest point across [{terms}] in {a.geo or meta.get('geo_label') or 'unknown geo'}, "
                 f"{window or 'unknown window'}, {category or 'unknown category'}, {a.search_type or 'unknown search type'}"
                 if kind in ("interest_over_time", "interest_by_region") else
                 "related queries/topics: top = relative 0-100 within this list; rising = growth label or %")
        vals = []
        for r in rows:
            num, vk = value_kind(r["value_raw"])
            vals.append({"import_id": import_id, "export_type": kind, "term": r.get("term", ""), "geo": a.geo or "",
                         "geo_label": meta.get("geo_label", ""), "window": window, "category": category,
                         "search_type": a.search_type or "", "period": r.get("period", ""),
                         "region_name": r.get("region_name", ""), "section": r.get("section", ""),
                         "query": r.get("query", ""), "value_raw": r["value_raw"], "value_numeric": num,
                         "value_kind": vk, "downloaded_at_utc": dl})
        bad = sum(1 for v in vals if v["value_kind"] == "unrecognised")
        if bad:
            warnings.append(f"{bad} values not recognised (kept raw)")
        rc.append_rows(t.values, VALUE_FIELDS, vals)
        rc.append_rows(t.imports, IMPORT_FIELDS, [{
            "import_id": import_id, "source_file": p.name, "sha256": digest, "export_type": kind, "terms": terms,
            "geo": a.geo or "", "geo_label": meta.get("geo_label", ""), "subregion": a.subregion or "",
            "window": window, "window_source": window_source, "category": category, "search_type": a.search_type or "",
            "normalisation_scope": scope, "downloaded_at_utc": dl, "downloaded_at_source": dl_src,
            "imported_at_utc": rc.iso(rc.now()), "rows": len(vals), "warnings": "; ".join(warnings)}])
        done.add(digest)
        total += len(vals)
        run.ok += 1
        print(f"  {p.name}: {kind}, {len(vals)} values, terms [{terms}] -> {import_id}")
        for w in warnings:
            print(f"    WARN {w}")
    run.rows = total
    run.finish("ok" if not run.failed else "partial")
    print(f"{total} values stored -> {t.values}")
    if run.failed:
        sys.exit(1)


def cmd_imports(a, t):
    for r in rc.read_rows(t.imports):
        print(f"{r['import_id']}  {r['export_type']:20} {r['terms'][:40]:40} {r['geo'] or r['geo_label']:10} {r['window'][:28]:28} {r['rows']} rows")


def cmd_report(a, t):
    out = (t.dir / "reports") if a.data_dir else None
    rc.prune_file(t.rss, RSS_FIELDS)
    rows = rc.read_rows(t.rss)
    # The export expires with its oldest row (local 90-day rule), so copies follow the same retention as the store.
    exp = [rc.parse_time(r["expires_at_utc"]) for r in rows if r.get("expires_at_utc")]
    d1 = rc.export("google_trends", "google_trending_now", rows, RSS_COLUMNS, notes=[
        "Trending Now covers ALL searches in a country (news, sport, TV), not gaming demand.",
        "approx_traffic is Google's rounded band; the lower bound is not a count.",
        "geo is where people searched; it says nothing about language or Roblox audience."],
        provenance="P2", retention_rule=f"local choice: {rc.settings()['trends']['rss_retention_days']} days (no stated provider limit)",
        expires_at=min(exp) if exp else None, share=True, dry_run=a.dry_run, out_dir=out)
    vals = rc.read_rows(t.values)
    if not vals:
        print(f"{len(rows)} Trending Now rows -> {d1}\nNo Explore imports yet; nothing else exported.")
        return
    d2 = rc.export("google_trends", "google_trends_explore", vals, VALUE_COLUMNS, notes=[
        "Each import_id is its own 0-100 scale. Never compare values across import_id as if absolute.",
        "'<1' stays as written; Breakout and +N% are growth labels for rising queries, not index values.",
        "Search interest is relative, not a count of searches."],
        provenance="P2", retention_rule="manual downloads (Google Terms of Service); no stated storage limit",
        expires_at=None, share=True, dry_run=a.dry_run, out_dir=out)
    print(f"{len(rows)} Trending Now rows -> {d1}\n{len(vals)} Explore values -> {d2}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--data-dir", help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("rss")
    r.add_argument("--geo", help="comma-separated country codes (default: settings.json trends.geos)")
    i = sub.add_parser("import")
    i.add_argument("files", nargs="+")
    i.add_argument("--geo", help="geo code used in Explore, e.g. MX or MX-JAL")
    i.add_argument("--subregion", help="subregion level shown, e.g. states / cities")
    i.add_argument("--window", help="time range used, e.g. 'past 12 months' or '2025-11-24 2026-11-24'")
    i.add_argument("--category", help="Trends category (default: the file's 'Category:' line)")
    i.add_argument("--search-type", choices=["web", "youtube", "images", "news", "froogle"])
    i.add_argument("--terms", help="override the term list (| separated)")
    i.add_argument("--downloaded-at", help="when you downloaded it (ISO time); default: file modified time")
    sub.add_parser("imports")
    sub.add_parser("report")
    a = ap.parse_args()
    {"rss": cmd_rss, "import": cmd_import, "imports": cmd_imports, "report": cmd_report}[a.cmd](a, Trends(a))


if __name__ == "__main__":
    main()
