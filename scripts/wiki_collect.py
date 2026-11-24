"""Wikipedia page views (Wikimedia Analytics API): a free, dated, historical cultural-interest signal.

  resolve          look up each title in config/research/wiki_entities.csv: canonical title, page ID,
                   Wikidata ID, whether it is a redirect, and the title in the other language edition
  pull             daily or monthly page views for every entity (canonical article AND the listed title
                   when it is a redirect, kept as separate rows; --all-redirects adds every known redirect).
                   Each title is fetched once; every request is logged ok / no_data / failed (wiki_coverage.csv)
  report           export the stored series -> exports/share/research/ (open data, shareable)

What this is and isn't:
- A language EDITION is not a country: es.wikipedia readers include Spain and all of Latin America.
- Views of a redirect title (e.g. es "Bajoterra" -> "Slugterra") are counted under the redirect title,
  separately from the canonical article. Both are stored, labelled `title_role`; don't read one alone.
- agent=user excludes known bots and spiders (Wikimedia's own classification), not all automated traffic.
- It measures reading interest in an encyclopedia article, not game demand or social engagement.
Data: daily from July 2015. Wikimedia asks for a descriptive User-Agent (set `contact` in settings.json).
--dry-run reads tests/fixtures/research/ and writes to data/local/research/dryrun/wikimedia/.
"""
import argparse
import csv
import json
import sys
import time
import urllib.parse
from datetime import timedelta
from pathlib import Path

import research_common as rc

PV = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/{access}/{agent}/{article}/{gran}/{start}/{end}"
ACTION = "https://{project}.org/w/api.php"
RESOLVED_FIELDS = ["entity_id", "project", "language_edition", "requested_title", "canonical_title", "is_redirect",
                   "page_id", "wikidata_id", "other_edition_title", "known_redirects", "known_redirect_count", "kind",
                   "resolved_at_utc", "run_id", "note"]
COVERAGE_FIELDS = ["entity_id", "project", "article_title", "title_role", "canonical_title", "wikidata_id", "granularity",
                   "window_start", "window_end", "status", "http_status", "points_returned", "observed_at_utc", "run_id"]
PV_FIELDS = ["entity_id", "project", "language_edition", "article_title", "title_role", "canonical_title", "page_id",
             "wikidata_id", "granularity", "period_start", "views", "agent", "access", "observed_at_utc", "run_id"]
COLUMNS = [
    ("entity_id", "config", "our label for the thing being tracked (same ID across editions)"),
    ("project", "Wikimedia", "wiki edition, e.g. en.wikipedia, es.wikipedia"),
    ("language_edition", "Wikimedia", "language of the wiki edition (NOT a country)"),
    ("article_title", "Wikimedia", "the exact title whose views are counted"),
    ("title_role", "local", "canonical = the article itself; redirect = an alias title that forwards to it"),
    ("canonical_title", "Wikimedia", "the article the title belongs to"),
    ("page_id", "Wikimedia", "page ID of the canonical article"),
    ("wikidata_id", "Wikidata", "Q-ID shared by the same topic across editions"),
    ("granularity", "request", "daily or monthly"),
    ("period_start", "Wikimedia", "first day of the period (UTC)"),
    ("views", "Wikimedia", "page views in the period"),
    ("agent", "request", "user = excludes known bots/spiders"),
    ("access", "request", "all-access, desktop, mobile-app or mobile-web"),
    ("observed_at_utc", "local", "when the collector read it"),
]
COVERAGE_COLUMNS = [
    ("entity_id", "config", "our label for the topic"),
    ("project", "Wikimedia", "wiki edition"),
    ("article_title", "Wikimedia", "title requested"),
    ("title_role", "local", "canonical or redirect"),
    ("canonical_title", "Wikimedia", "article the title belongs to"),
    ("wikidata_id", "Wikidata", "topic ID shared across editions"),
    ("granularity", "request", "daily or monthly"),
    ("window_start", "request", "first period requested (YYYYMMDD)"),
    ("window_end", "request", "last period requested (YYYYMMDD)"),
    ("status", "local", "ok = returned data; no_data = Wikimedia had no views for this title in the whole window (404); "
                        "failed = request failed, so every date in the window is UNKNOWN; resolve_failed = the title lookup "
                        "failed, nothing requested (UNKNOWN); not_found = no such article on that wiki"),
    ("http_status", "Wikimedia", "HTTP status of the request"),
    ("points_returned", "Wikimedia", "how many dated rows came back"),
    ("observed_at_utc", "local", "when the request was made"),
]


class Wiki:
    def __init__(self, a):
        self.dry = a.dry_run
        self.dir = Path(a.data_dir) if a.data_dir else rc.DATA / ("dryrun" if a.dry_run else "") / "wikimedia"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.resolved = self.dir / "wiki_resolved.csv"
        self.pageviews = self.dir / "wiki_pageviews.csv"
        self.coverage = self.dir / "wiki_coverage.csv"

    def get(self, run, url, params=None, fixture=None):
        if not self.dry:
            # Wikimedia rate-limits bursts (429 seen live 2026-11-24 at ~60 quick requests): pace and back off.
            for attempt in range(4):
                time.sleep(0.2)
                try:
                    data = json.loads(rc.http(url, params)[0])
                    run.ok += 1
                    return data
                except rc.HttpError as e:
                    if e.status not in (429, 503) or attempt == 3:
                        run.failed += 1
                        raise
                    time.sleep(2 ** (attempt + 1))
        try:
            data = json.loads(rc.fixture(fixture))
            if self.dry and "_error" in data:  # fixtures can simulate a 404 or a failure
                raise rc.HttpError(data["_error"]["code"], data["_error"]["reason"])
            run.ok += 1
            return data
        except (rc.HttpError, FileNotFoundError):
            run.failed += 1
            raise


def entities(path=None):
    with Path(path or rc.CONFIG / "wiki_entities.csv").open(newline="", encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if r.get("title", "").strip()]


def other_lang(project):
    return "es" if project.startswith("en.") else "en"


def resolve_one(w, run, e):
    project, title = e["project"].strip(), e["title"].strip()
    params = {"action": "query", "titles": title, "redirects": 1, "prop": "pageprops|langlinks|redirects",
              "lllang": other_lang(project), "rdlimit": "max", "rdnamespace": 0, "format": "json", "formatversion": 2}
    data = w.get(run, ACTION.format(project=project), params, fixture=f"wiki_query_{project.split('.')[0]}_{slug(title)}.json")
    q = data.get("query", {})
    page = (q.get("pages") or [{}])[0]
    redirected = bool(q.get("redirects"))
    missing = page.get("missing", False)
    return {"entity_id": e["entity_id"], "project": project, "language_edition": project.split(".")[0],
            "requested_title": title, "canonical_title": "" if missing else page.get("title", ""),
            "is_redirect": str(redirected).lower(), "page_id": page.get("pageid", ""),
            "wikidata_id": page.get("pageprops", {}).get("wikibase_item", ""),
            "other_edition_title": (page.get("langlinks") or [{}])[0].get("title", ""),
            "known_redirects": "|".join(x["title"] for x in page.get("redirects", [])[:200]),
            "known_redirect_count": len(page.get("redirects", [])), "kind": e.get("kind", ""),
            "resolved_at_utc": rc.iso(rc.now()), "run_id": run.id,
            "note": "title not found on this wiki" if missing else ""}


def slug(t):
    return "".join(c if c.isalnum() else "_" for c in t)


def cmd_resolve(a, w):
    run = rc.Run("wikimedia", "resolve", {"entities": a.entities or "default"}, a.dry_run, a.data_dir)
    rows = []
    for e in entities(a.entities):
        try:
            r = resolve_one(w, run, e)
        except (rc.HttpError, FileNotFoundError) as ex:
            # Keep the entry, marked, so the next pull retries it and the coverage log shows it as unknown.
            code = getattr(ex, "status", 0)
            print(f"  {e['project']} {e['title']}: lookup FAILED ({code}); will retry on the next pull")
            rows.append({**dict.fromkeys(RESOLVED_FIELDS, ""), "entity_id": e["entity_id"], "project": e["project"].strip(),
                         "language_edition": e["project"].split(".")[0], "requested_title": e["title"].strip(),
                         "kind": e.get("kind", ""), "resolved_at_utc": rc.iso(rc.now()), "run_id": run.id,
                         "note": f"resolve failed ({code})"})
            continue
        rows.append(r)
        arrow = f" -> {r['canonical_title']}" if r["is_redirect"] == "true" else ""
        other = f" ({other_lang(r['project'])}: {r['other_edition_title']})" if r["other_edition_title"] else ""
        print(f"  {r['project']} {r['requested_title']}{arrow} [{r['wikidata_id'] or 'no Wikidata ID'}]{other} {r['note']}")
    rc.write_rows(w.resolved, RESOLVED_FIELDS, rows)
    run.rows = len(rows)
    run.finish("ok" if not run.failed else "partial")
    print(f"{len(rows)} titles -> {w.resolved}")
    return rows


def fetch_plan(resolved, all_redirects):
    """One entry per (project, title), so an alias listed twice (or listed under two entities) is fetched and
    stored once. Returns (plan, warnings)."""
    plan, warnings = {}, []

    def add(r, title, role):
        k = (r["project"], title)
        if k in plan:
            if plan[k]["entity_id"] != r["entity_id"]:
                warnings.append(f"{r['project']} '{title}' is listed under entities {plan[k]['entity_id']} and "
                                f"{r['entity_id']}; counted once, under {plan[k]['entity_id']}")
            return
        plan[k] = {**r, "article_title": title, "title_role": role}

    for r in resolved:
        if not r["canonical_title"]:
            continue
        add(r, r["canonical_title"], "canonical")
        if r["is_redirect"] == "true":
            add(r, r["requested_title"], "redirect")
        if all_redirects:
            for title in filter(None, (r.get("known_redirects") or "").split("|")):
                add(r, title, "redirect")
    return plan, warnings


def cmd_pull(a, w):
    resolved = rc.read_rows(w.resolved)
    listed = {(e["project"].strip(), e["title"].strip()) for e in entities(a.entities)}
    have = {(r["project"], r["requested_title"]) for r in resolved}
    if (not resolved or a.refresh_titles or (a.all_redirects and "known_redirects" not in resolved[0])
            or listed != have or any(r.get("note", "").startswith("resolve failed") for r in resolved)):
        resolved = cmd_resolve(a, w)  # also re-runs when the entity list changed or a lookup failed last time
    gran = a.granularity
    end = rc.parse_time(a.end) if a.end else rc.now() - timedelta(days=1)
    start = rc.parse_time(a.start) if a.start else end - timedelta(days=a.days)
    fmt = "%Y%m%d" if gran == "daily" else "%Y%m01"
    params = {"granularity": gran, "start": start.strftime(fmt), "end": end.strftime("%Y%m%d"),
              "agent": a.agent, "access": a.access, "all_redirects": a.all_redirects}
    run = rc.Run("wikimedia", "pull", params, a.dry_run, a.data_dir)
    observed, new, coverage = rc.iso(rc.now()), [], []
    plan, warnings = fetch_plan(resolved, a.all_redirects)
    for msg in dict.fromkeys(warnings):
        print("  WARN", msg)
    for r in resolved:  # titles that never reached the page-view step are logged too, never silently dropped
        if not r.get("canonical_title"):
            status = "resolve_failed" if r.get("note", "").startswith("resolve failed") else "not_found"
            coverage.append({"entity_id": r["entity_id"], "project": r["project"], "article_title": r["requested_title"],
                             "title_role": "unknown", "canonical_title": "", "wikidata_id": "", "granularity": gran,
                             "window_start": params["start"], "window_end": params["end"], "status": status,
                             "http_status": "", "points_returned": 0, "observed_at_utc": observed, "run_id": run.id})
            print(f"  {r['project']} {r['requested_title']}: {status} (no page views requested)")
    for (project, title), r in plan.items():
        role = r["title_role"]
        url = PV.format(project=project, access=a.access, agent=a.agent, gran=gran, start=params["start"],
                        end=params["end"], article=urllib.parse.quote(title.replace(" ", "_"), safe=""))
        cov = {"entity_id": r["entity_id"], "project": project, "article_title": title, "title_role": role,
               "canonical_title": r["canonical_title"], "wikidata_id": r["wikidata_id"], "granularity": gran,
               "window_start": params["start"], "window_end": params["end"], "observed_at_utc": observed, "run_id": run.id}
        try:
            data = w.get(run, url, fixture=f"wiki_pageviews_{r['language_edition']}_{slug(title)}.json")
        except (rc.HttpError, FileNotFoundError) as ex:
            # 404 = Wikimedia has no views for this title in the whole window; anything else = unknown.
            code = getattr(ex, "status", 0)
            status = "no_data" if code == 404 else "failed"
            coverage.append({**cov, "status": status, "http_status": code, "points_returned": 0})
            print(f"  {project} {title}: {'no views in window' if status == 'no_data' else 'FAILED'} ({code})")
            continue
        items = data.get("items", [])
        coverage.append({**cov, "status": "ok", "http_status": 200, "points_returned": len(items)})
        for it in items:
            new.append({"entity_id": r["entity_id"], "project": project, "language_edition": r["language_edition"],
                        "article_title": title, "title_role": role, "canonical_title": r["canonical_title"],
                        "page_id": r["page_id"], "wikidata_id": r["wikidata_id"], "granularity": gran,
                        "period_start": f"{it['timestamp'][:4]}-{it['timestamp'][4:6]}-{it['timestamp'][6:8]}",
                        "views": it.get("views", ""), "agent": a.agent, "access": a.access,
                        "observed_at_utc": observed, "run_id": run.id})
        print(f"  {project} {title} ({role}): {len(items)} {gran} points")
    # Same article + period + filters: keep the newest reading (Wikimedia occasionally backfills).
    key = lambda x: (x["project"], x["article_title"], x["granularity"], x["period_start"], x["agent"], x["access"])
    merged = {key(x): x for x in rc.read_rows(w.pageviews)}
    merged.update({key(x): x for x in new})
    rows = sorted(merged.values(), key=lambda x: (x["entity_id"], x["project"], x["article_title"], x["granularity"], x["period_start"]))
    rc.write_rows(w.pageviews, PV_FIELDS, rows)
    rc.append_rows(w.coverage, COVERAGE_FIELDS, coverage)
    run.rows = len(new)
    run.finish("ok" if not run.failed else "partial")
    print(f"{len(new)} points read, {len(rows)} stored -> {w.pageviews}; request log -> {w.coverage} [run {run.id}]")


def cmd_report(a, w):
    rows = rc.read_rows(w.pageviews)
    dest = rc.export("wikimedia", "wikimedia_pageviews", rows, COLUMNS, notes=[
        "A language edition is not a country; es.wikipedia mixes Spain and Latin America.",
        "Redirect-title rows (title_role=redirect) are separate from the canonical article; read them together.",
        "Page views measure interest in an encyclopedia article, not game demand or social-media engagement.",
        "Each title appears once per date (aliases listed twice are fetched once), so rows can be summed without double counting.",
        "Topic total for one edition and date = sum of views over rows with the same entity_id, project and period_start "
        "(canonical + listed redirects). Use wikidata_id to line up the same topic across editions; never add editions together "
        "as if they were one country.",
        "A date missing inside a window whose coverage status is ok = no views recorded (Wikimedia omits zero days). A date in a "
        "window with status failed = unknown. A views value of 0 returned by Wikimedia stays 0. See the wikimedia_coverage export."],
        provenance="P1", retention_rule="open data (Wikimedia); no provider storage limit", expires_at=None,
        share=True, dry_run=a.dry_run, out_dir=(w.dir / "reports") if a.data_dir else None)
    print(f"{len(rows)} rows -> {dest}")
    cov = rc.read_rows(w.coverage)
    dest = rc.export("wikimedia", "wikimedia_coverage", cov, COVERAGE_COLUMNS, notes=[
        "One row per page-view request: which title and window was asked for and whether it succeeded.",
        "Use it to tell 'no views recorded' (status ok, date absent; or status no_data) from 'unknown' (status failed)."],
        provenance="P1", retention_rule="open data (Wikimedia); no provider storage limit", expires_at=None,
        share=True, dry_run=a.dry_run, out_dir=(w.dir / "reports") if a.data_dir else None)
    print(f"{len(cov)} request-log rows -> {dest}")


def main():
    sys.stdout.reconfigure(errors="replace")  # titles contain emoji the Windows console can't encode
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--data-dir", help=argparse.SUPPRESS)
    ap.add_argument("--entities", help="entity CSV (default config/research/wiki_entities.csv)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("resolve")
    p = sub.add_parser("pull")
    p.add_argument("--granularity", choices=["daily", "monthly"], default="daily")
    p.add_argument("--days", type=int, default=90, help="window length when --start isn't given (default 90)")
    p.add_argument("--start", help="YYYY-MM-DD (data exists from 2015-07-01)")
    p.add_argument("--end", help="YYYY-MM-DD (default yesterday)")
    p.add_argument("--agent", choices=["user", "all-agents", "automated", "spider"], default=rc.settings()["wikimedia"]["default_agent"])
    p.add_argument("--access", choices=["all-access", "desktop", "mobile-app", "mobile-web"], default="all-access")
    p.add_argument("--refresh-titles", action="store_true", help="re-resolve titles first")
    p.add_argument("--all-redirects", action="store_true",
                   help="also pull every redirect that points to each canonical article (fuller topic totals; more requests)")
    sub.add_parser("report")
    a = ap.parse_args()
    w = Wiki(a)
    try:
        {"resolve": cmd_resolve, "pull": cmd_pull, "report": cmd_report}[a.cmd](a, w)
    except rc.HttpError as e:
        sys.exit(f"Wikimedia error: {e.status} {e.reason}")


if __name__ == "__main__":
    main()
