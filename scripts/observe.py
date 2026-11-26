"""Public observations: import what people (or ChatGPT/TinyFish/vidIQ) saw on public pages, with provenance.

  template [--kind K]   copy a ready-to-fill template into data/local/research/observations/inbox/
                        (K = general, creative_center, post, vidiq)
  check FILE...         validate only; nothing is written
  import FILE...        validate and store (whole file refused if any row has an error, unless --skip-bad)
  report                export the store -> exports/share/research/public_observations_*.csv
  list                  items with repeat observations

Input: CSV, TSV, or a Markdown table pasted from ChatGPT (.md/.txt). Column names are forgiving
("Views", "View count", "Link", "Hashtag", "Observed" all work; see docs/research-data.md). Anything the
file doesn't say can come from options: --platform, --source, --observed-at, --region, --period, --category.
Defaults are only ever applied to metadata you pass explicitly; numbers are never invented.

Rules: blank / "-" / "n/a" stay blank (never 0). "24.5K" is stored as shown and as 24500 with
value_rounded=true. Ranks are P2, interpretations (hook, format, notes from a tool) are P4, counts take the
source's provenance (P1 platform page or Creative Center, P3 vidIQ or other third-party tools).
Duplicates (same item, metric, source and observation time) are skipped; the same item observed at a new
time is a repeat observation and is kept.
"""
import argparse
import csv
import io
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import research_common as rc

TEMPLATES = rc.ROOT / "data" / "templates"
STORE_FIELDS = ["obs_key", "import_id", "platform", "entity_type", "content_key", "content_id", "url", "creator_handle",
                "creator_name", "title_or_name", "published_at_utc", "observed_at_utc", "observed_precision", "source",
                "collected_via", "provenance", "region", "region_evidence", "period", "category", "metric",
                "value_display", "value_numeric", "value_rounded", "metric_definition", "content_language",
                "language_evidence", "sample_role", "concept_id", "meme_id", "sound_id", "format_id", "genre_id",
                "notes", "source_url", "oembed_checked", "imported_at_utc"]
METRICS = ["rank", "rank_change", "views", "likes", "comments", "shares", "saves", "posts", "followers", "plays",
           "videos_using_sound", "breakout_multiple", "views_per_hour", "engagement_rate"]
P4_FIELDS = ["hook", "format_description", "interpretation", "audience_note"]
ALIASES = {
    "link": "url", "post_url": "url", "video_url": "url", "reel_url": "url", "source_link": "source_url",
    "page_url": "source_url", "creative_center_url": "source_url",
    "id": "content_id", "video_id": "content_id", "post_id": "content_id",
    "creator": "creator_name", "account": "creator_handle", "handle": "creator_handle", "username": "creator_handle",
    "author": "creator_name", "channel": "creator_name",
    "title": "title_or_name", "name": "title_or_name", "hashtag": "title_or_name", "sound": "title_or_name",
    "keyword": "title_or_name", "caption": "title_or_name", "track": "title_or_name",
    "published": "published_at", "posted": "published_at", "post_date": "published_at", "date_posted": "published_at",
    "published_at_utc": "published_at", "upload_date": "published_at",
    "observed": "observed_at_utc", "observed_at": "observed_at_utc", "observation_date": "observed_at_utc",
    "checked": "observed_at_utc", "date_observed": "observed_at_utc", "observed_utc": "observed_at_utc",
    "view_count": "views", "plays_count": "plays", "play_count": "plays", "reported_views": "views",
    "public_views": "views", "provider_reported_views": "views",
    "like_count": "likes", "comment_count": "comments", "share_count": "shares", "save_count": "saves",
    "post_count": "posts", "videos": "posts", "follower_count": "followers", "subscribers": "followers",
    "breakout": "breakout_multiple", "outlier_multiple": "breakout_multiple", "vph": "views_per_hour",
    "position": "rank", "ranking": "rank", "change": "rank_change",
    "country": "region", "market": "region", "time_period": "period", "window": "period",
    "industry": "category", "type": "entity_type", "kind": "entity_type",
    "language": "content_language", "lang": "content_language",
    "formula": "format_description", "format": "format_description", "opening_hook": "hook",
    "concept": "concept_id", "meme": "meme_id", "sound_id_": "sound_id", "genre": "genre_id",
    "ordinary": "sample_role", "role": "sample_role", "via": "collected_via", "tool": "collected_via",
    "platform_name": "platform", "app": "platform", "note": "notes", "comment": "notes",
}
SOURCES = {  # source -> (collected_via default, provenance of counts)
    "creative_center": ("tiktok_creative_center", "P1"),
    "creator_search_insights": ("tiktok_creator_search_insights", "P2"),
    "platform_page": ("manual_browser", "P1"),
    "manual": ("manual_browser", "P1"),
    "tinyfish": ("tinyfish_via_chatgpt", "P1"),
    "vidiq": ("vidiq_via_chatgpt", "P3"),
    "ttanon": ("third_party_mirror", "P3"),
    "wieldr": ("third_party_tracker", "P3"),
    "other_tool": ("third_party_tool", "P3"),
}
PLATFORMS = {"tiktok", "instagram", "youtube", "twitch", "roblox", "x", "reddit", "other"}
ENTITIES = {"post", "hashtag", "sound", "creator", "keyword", "search_term", "game", "trend"}
ROLES = {"featured", "ordinary", "failed", "unknown", ""}
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MONTHS.update({"ene": 1, "abr": 4, "ago": 8, "dic": 12})


def store_paths(a):
    d = Path(a.data_dir) if a.data_dir else rc.DATA / ("dryrun" if a.dry_run else "") / "observations"
    d.mkdir(parents=True, exist_ok=True)
    return d, d / "public_observations.csv"


# ---------- reading tables ----------

def norm_header(h):
    h = re.sub(r"\(.*?\)", "", h.strip().lower())
    h = re.sub(r"[^a-z0-9]+", "_", h).strip("_")
    return ALIASES.get(h, h)


def read_table(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    lines = [l for l in text.splitlines()]
    if Path(path).suffix.lower() in (".md", ".txt", ".markdown") or sum(l.strip().startswith("|") for l in lines) >= 2:
        rows = []
        for l in lines:
            s = l.strip()
            if not s.startswith("|"):
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            rows.append(cells)
        if not rows:
            raise ValueError("no Markdown table found")
        head, body = rows[0], rows[1:]
    else:
        dialect = "excel-tab" if lines and lines[0].count("\t") > lines[0].count(",") else "excel"
        rows = [r for r in csv.reader(io.StringIO(text), dialect=dialect) if any(c.strip() for c in r)]
        if not rows:
            raise ValueError("empty file")
        head, body = rows[0], rows[1:]
    head = [norm_header(h) for h in head]
    return head, [dict(zip(head, [strip_md(c) for c in r] + [""] * (len(head) - len(r)))) for r in body]


def strip_md(cell):
    """ChatGPT tables wrap links as [text](url) and use **bold**; keep the URL, drop the markup."""
    m = re.fullmatch(r"\[(.*?)\]\((https?://[^)\s]+)\)", cell.strip())
    if m:
        return m.group(2)
    return re.sub(r"\*\*(.*?)\*\*", r"\1", cell).strip()


# ---------- parsing values ----------

def parse_when(s, date_order):
    """Returns (utc datetime, precision) or raises ValueError. Never guesses an ambiguous date."""
    s = s.strip()
    if not s:
        return None, ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return rc.parse_time(s), "day"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:?\d{2})?", s):
        t = s.replace(" ", "T")
        if not re.search(r"(Z|[+-]\d{2}:?\d{2})$", t):
            raise ValueError(f"'{s}' has no time zone; add Z for UTC")
        return rc.parse_time(t), "second"
    m = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*\.?\s+(\d{4})", s) or None
    if m:
        return datetime(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1)), tzinfo=timezone.utc), "day"
    m = re.fullmatch(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})", s)
    if m:
        return datetime(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2)), tzinfo=timezone.utc), "day"
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        x, y, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if not date_order:
            if x > 12:
                date_order = "dmy"
            elif y > 12:
                date_order = "mdy"
            else:
                raise ValueError(f"'{s}' is ambiguous (day/month?); pass --date-order dmy or mdy, or use YYYY-MM-DD")
        d, mo = (x, y) if date_order == "dmy" else (y, x)
        return datetime(yr, mo, d, tzinfo=timezone.utc), "day"
    if re.search(r"\b(ago|hace)\b", s.lower()):
        raise ValueError(f"'{s}' is relative; give the actual date")
    raise ValueError(f"unrecognised date '{s}' (use YYYY-MM-DD or ISO time with Z)")


def parse_metric(name, raw):
    """Returns (display, numeric, rounded) or raises ValueError."""
    s = (raw or "").strip()
    if s.lower() in rc.MISSING:
        return "", "", ""
    if name == "rank_change":
        if s.upper() in ("NEW", "NUEVO"):
            return s, "", "false"
        if re.fullmatch(r"[+-]?\d+", s):
            return s, str(int(s)), "false"
        raise ValueError(f"rank_change '{s}' should be +N, -N, 0 or NEW")
    if name in ("breakout_multiple",):
        m = re.fullmatch(r"([\d.]+)\s*[x×]?", s.lower())
        if m:
            return s, m.group(1), "false"
        raise ValueError(f"{name} '{s}' should look like 5.2x")
    if name == "engagement_rate":
        m = re.fullmatch(r"([\d.]+)\s*%?", s)
        if m:
            return s, m.group(1), "false"
        raise ValueError(f"engagement_rate '{s}' should look like 4.5%")
    if name == "rank":
        s2 = s.lstrip("#")
        if re.fullmatch(r"\d+", s2):
            return s, s2, "false"
        raise ValueError(f"rank '{s}' is not a whole number")
    if name == "views_per_hour":
        n, r = rc.parse_count(s)
        if n is None and re.fullmatch(r"\d+\.\d+", s):
            return s, s, "false"
    n, r = rc.parse_count(s)
    if n is None:
        raise ValueError(f"{name} '{s}' is not a number (examples: 1200, 1,200, 24.5K, 3.6M)")
    return s, str(n), str(r).lower()


URL_RULES = [  # (platform, entity, regex, id group)
    ("tiktok", "post", r"tiktok\.com/@([^/?#]+)/(?:video|photo)/(\d+)", 2),
    ("tiktok", "sound", r"tiktok\.com/music/[^?#]*?-?(\d{6,})", 1),
    ("tiktok", "hashtag", r"tiktok\.com/tag/([^/?#]+)", 1),
    ("tiktok", "creator", r"tiktok\.com/@([^/?#]+)/?(?:\?.*)?$", 1),
    ("instagram", "post", r"instagram\.com/(?:[^/]+/)?(?:reel|reels|p|tv)/([A-Za-z0-9_-]+)", 1),
    ("instagram", "hashtag", r"instagram\.com/explore/tags/([^/?#]+)", 1),
    ("youtube", "post", r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})", 1),
    ("twitch", "post", r"(?:clips\.twitch\.tv/|twitch\.tv/[^/]+/clip/)([A-Za-z0-9_-]+)", 1),
    ("roblox", "game", r"roblox\.com/games/(\d+)", 1),
]


def from_url(url):
    for platform, entity, rx, g in URL_RULES:
        m = re.search(rx, url)
        if m:
            handle = m.group(1) if platform == "tiktok" and entity in ("post", "creator") else ""
            return platform, entity, m.group(g), handle
    if "creativecenter" in url.replace("/", "").lower() or "ads.tiktok.com/creative" in url:
        return "tiktok", "", "", ""
    return "", "", "", ""


# ---------- validation ----------

def build(a, path):
    head, rows = read_table(path)
    unknown = [h for h in head if h and h not in set(STORE_FIELDS) | set(METRICS) | set(P4_FIELDS) |
               {"published_at", "platform", "notes", "metric_definitions_verified", "ordinary_example"}]
    out, errors, warnings = [], [], []
    if unknown:
        warnings.append(f"ignored columns: {', '.join(unknown)} (see docs/research-data.md for names)")
    import_id = f"obs-{rc.sha256(path)[:12]}"
    for n, r in enumerate(rows, 2):
        err = []
        # "—", "n/a", "unknown" etc. mean blank in every column, not just in metrics.
        g = lambda k: "" if (r.get(k) or "").strip().lower() in rc.MISSING else (r.get(k) or "").strip()
        url = g("url")
        source = (g("source") or a.source or "").lower().replace(" ", "_")
        if not source:
            err.append("no source (column 'source' or --source: creative_center, platform_page, tinyfish, vidiq, ...)")
        via_default, count_prov = SOURCES.get(source, ("", ""))
        prov = (g("provenance") or a.provenance or count_prov).upper()
        if prov and prov not in rc.PROVENANCE:
            err.append(f"provenance '{prov}' must be P1, P2, P3 or P4")
        if source and not prov:
            err.append(f"source '{source}' has no default provenance; pass --provenance P1/P2/P3")
        u_platform, u_entity, u_id, u_handle = from_url(url) if url else ("", "", "", "")
        if url and not re.match(r"https?://", url):
            err.append(f"url '{url[:60]}' must start with http(s)://")
        platform = (g("platform") or a.platform or u_platform).lower()
        if platform not in PLATFORMS:
            err.append(f"platform '{platform}' unknown (one of {', '.join(sorted(PLATFORMS))})" if platform else
                       "platform unknown: add a platform column, --platform, or a recognisable URL")
        if u_platform and platform and u_platform != platform:
            err.append(f"url points to {u_platform} but platform says {platform}")
        title = g("title_or_name")
        entity = (g("entity_type") or a.entity_type or u_entity or ("hashtag" if title.startswith("#") else "")).lower()
        if entity not in ENTITIES:
            err.append(f"entity_type '{entity}' unknown (one of {', '.join(sorted(ENTITIES))})" if entity else
                       "entity_type unknown: add entity_type (post, hashtag, sound, creator, keyword...) or --entity-type")
        cid = g("content_id") or u_id
        if g("content_id") and u_id and g("content_id") != u_id:
            err.append(f"content_id {g('content_id')} doesn't match the ID in the URL ({u_id})")
        if entity == "hashtag":
            name = (title or cid).lstrip("#").strip().lower()
            key = f"{platform}:hashtag:{name}" if name else ""
            title = title or ("#" + name if name else "")
        elif entity in ("keyword", "search_term", "trend"):
            key = f"{platform}:{entity}:{title.lower()}" if title else ""
        elif entity == "creator":
            h = (g("creator_handle") or u_handle or cid).lstrip("@").lower()
            key = f"{platform}:creator:{h}" if h else ""
        else:
            key = f"{platform}:{entity}:{cid}" if cid else (f"{platform}:{entity}:name:{title.lower()}" if title and entity == "sound" else "")
        if not key:
            err.append("can't identify the item: give a URL, content_id, or name/hashtag")
        try:
            obs, precision = parse_when(g("observed_at_utc") or a.observed_at or "", a.date_order)
            if not obs:
                err.append("no observation date (column 'observed_at_utc' or --observed-at)")
            elif obs > rc.now():
                err.append(f"observation date {rc.iso(obs)} is in the future")
        except ValueError as e:
            obs, precision = None, ""
            err.append(f"observed: {e}")
        try:
            pub, _ = parse_when(g("published_at"), a.date_order)
            if pub and obs and pub > obs and precision != "day":
                err.append("published after it was observed")
        except ValueError as e:
            pub = None
            err.append(f"published: {e}")
        role = (g("sample_role") or a.sample_role or "").lower()
        if role in ("yes", "true", "y"):
            role = "ordinary"
        if role not in ROLES:
            err.append(f"sample_role '{role}' should be featured, ordinary, failed or unknown")
        base = {"import_id": import_id, "platform": platform, "entity_type": entity, "content_key": key,
                "content_id": cid, "url": url, "creator_handle": (g("creator_handle") or u_handle).lstrip("@"),
                "creator_name": g("creator_name"), "title_or_name": title, "published_at_utc": rc.iso(pub),
                "observed_at_utc": rc.iso(obs), "observed_precision": precision, "source": source,
                "collected_via": g("collected_via") or a.collected_via or via_default,
                "region": (g("region") or a.region or "").upper(),
                "region_evidence": g("region_evidence") or a.region_evidence or ("source_filter" if (g("region") or a.region) else ""),
                "period": g("period") or a.period or "", "category": g("category") or a.category or "",
                "content_language": g("content_language"), "language_evidence": g("language_evidence"),
                "sample_role": role, "concept_id": g("concept_id"), "meme_id": g("meme_id"), "sound_id": g("sound_id"),
                "format_id": g("format_id"), "genre_id": g("genre_id"), "notes": g("notes"),
                "source_url": g("source_url") or a.source_url or "", "oembed_checked": "",
                "imported_at_utc": rc.iso(rc.now())}
        verified = {m.strip() for m in g("metric_definitions_verified").split("|") if m.strip()}
        rowset = []
        for m in METRICS:
            try:
                disp, numv, rounded = parse_metric(m, g(m))
            except ValueError as e:
                err.append(str(e))
                continue
            if disp == "":
                continue
            rowset.append({**base, "metric": m, "value_display": disp, "value_numeric": numv, "value_rounded": rounded,
                           "provenance": "P2" if m in ("rank", "rank_change") else ("P3" if m in ("breakout_multiple",) and prov == "P1" else prov),
                           "metric_definition": "verified" if m in verified else "unknown"})
        for f in P4_FIELDS:
            if g(f):
                rowset.append({**base, "metric": f, "value_display": g(f), "value_numeric": "", "value_rounded": "",
                               "provenance": "P4", "metric_definition": "interpretation"})
        if not rowset:
            rowset.append({**base, "metric": "_seen", "value_display": "", "value_numeric": "", "value_rounded": "",
                           "provenance": prov, "metric_definition": "item observed; no metrics recorded"})
        if err:
            errors.append(f"row {n}: " + "; ".join(err))
        else:
            out += rowset
    for r in out:
        # Scope matters: the same hashtag's views in US/7 days and MX/30 days are different observations.
        r["obs_key"] = "|".join((r["content_key"], r["metric"], r["source"], r["observed_at_utc"], r["region"],
                                 r["period"].lower(), r["category"].lower()))
    return out, errors, warnings


def oembed(rows, dry):
    """TikTok's public oEmbed endpoint: confirms the post resolves and returns author/title. No statistics."""
    seen = {}
    for r in rows:
        if r["platform"] != "tiktok" or r["entity_type"] != "post" or not r["url"]:
            continue
        if r["url"] not in seen:
            try:
                body = rc.fixture("tiktok_oembed.json") if dry else rc.http("https://www.tiktok.com/oembed", {"url": r["url"]})[0]
                seen[r["url"]] = json.loads(body)
            except rc.HttpError as e:
                seen[r["url"]] = {"_error": f"{e.status}"}
        d = seen[r["url"]]
        if "_error" in d:
            r["oembed_checked"] = f"failed ({d['_error']})"
            continue
        # Live test 2026-11-24: TikTok's oEmbed returned only embed HTML and embed_product_id (no author,
        # title or stats), so its real use is confirming the post exists and the ID matches.
        pid = str(d.get("embed_product_id", ""))
        if pid and r["content_id"] and pid != r["content_id"]:
            r["oembed_checked"] = f"id mismatch (oEmbed {pid})"
            continue
        r["oembed_checked"] = "true"
        r["creator_handle"] = r["creator_handle"] or d.get("author_unique_id", "")
        r["creator_name"] = r["creator_name"] or d.get("author_name", "")
        r["title_or_name"] = r["title_or_name"] or d.get("title", "")[:200]
        if r["creator_handle"] and d.get("author_unique_id") and r["creator_handle"].lower() != d["author_unique_id"].lower():
            r["notes"] = (r["notes"] + " | " if r["notes"] else "") + f"oEmbed author is @{d['author_unique_id']}"


def dedupe(new, existing):
    have = {r["obs_key"]: r for r in existing}
    keep, dup, conflict = [], 0, []
    for r in new:
        old = have.get(r["obs_key"])
        if old is None:
            have[r["obs_key"]] = r
            keep.append(r)
        elif old["value_display"] == r["value_display"]:
            dup += 1
        else:
            conflict.append(f"{r['content_key']} {r['metric']} at {r['observed_at_utc']}: stored '{old['value_display']}' "
                            f"vs new '{r['value_display']}'")
    return keep, dup, conflict


def cmd_check(a, imp=False):
    d, store = store_paths(a)
    existing = rc.read_rows(store)
    total_new, bad = [], False
    for f in a.files:
        try:
            rows, errors, warnings = build(a, f)
        except (ValueError, OSError) as e:
            print(f"{f}: REJECTED - {e}")
            bad = True
            continue
        if a.oembed:
            oembed(rows, a.dry_run)
        keep, dup, conflict = dedupe(rows, existing + total_new)
        items = {r["content_key"] for r in keep}
        repeats = {r["content_key"] for r in keep} & {r["content_key"] for r in existing}
        print(f"{f}: {len(keep)} new values for {len(items)} items; {dup} duplicates skipped; "
              f"{len(repeats)} items are repeat observations; {len(errors)} rows with errors")
        for w in warnings:
            print("  WARN", w)
        for e in errors + [f"conflict: {c}" for c in conflict]:
            print("  ERROR", e)
        if (errors or conflict) and not a.skip_bad:
            bad = True
            if imp:
                print("  Nothing imported from this file. Fix the rows above, or use --skip-bad to import the valid rows.")
            continue
        total_new += keep
    if imp and total_new:
        rc.append_rows(store, STORE_FIELDS, total_new)
        run = rc.Run("observations", "import", {"files": a.files, "source": a.source}, a.dry_run, a.data_dir)
        run.rows, run.ok = len(total_new), len(a.files)
        run.finish("ok" if not bad else "partial")
        print(f"Imported {len(total_new)} values -> {store}")
    elif not imp:
        print("Check only: nothing written." if not bad else "Check only: fix the errors above before importing.")
    if bad:
        sys.exit(1)


# Creative Center: a person reads each page. The helpers process copied text.

CC_HASHTAG = "https://ads.tiktok.com/creative/creativeCenter/trends/hashtag?region={region}&period={period}"
CC_LABELS = {"posts": "posts", "post": "posts", "publicaciones": "posts", "videos": "posts", "vídeos": "posts",
             "views": "views", "view": "views", "visualizaciones": "views", "vistas": "views", "reproducciones": "views"}
NUM = r"(\d[\d.,]*\s*[KMBkmb]?)"


def cmd_cc_links(a):
    """Print (and optionally open) the Creative Center hashtag page for each market and period, plus a session file."""
    import webbrowser
    regions = [r.strip().upper() for r in (a.regions or ",".join(rc.settings()["trends"]["geos"])).split(",") if r.strip()]
    periods = [p.strip() for p in a.periods.split(",") if p.strip()]
    d, _ = store_paths(a)
    inbox = d / "inbox"
    inbox.mkdir(exist_ok=True)
    plan = inbox / f"creative_center_session_{rc.now():%Y%m%d_%H%M}.csv"
    with plan.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["region", "period", "url", "paste_file", "then_run"])
        for r in regions:
            for p in periods:
                url = CC_HASHTAG.format(region=r, period=p)
                paste = inbox / f"cc_{r}_{p}d_{rc.now():%Y%m%d}.txt"
                w.writerow([r, p, url, paste.name,
                            f'.\\ss observe cc-paste "{paste}" --region {r} --period {p}' + (f' --category "{a.category}"' if a.category else "")])
                print(f"{r} {p:>3} days  {url}")
                if a.open:
                    webbrowser.open(url)
    print(f"\nSession list -> {plan}\nFor each page: set the industry filter (e.g. Games) if you want it, scroll so the rows load, "
          "press Ctrl+A then Ctrl+C, paste into the paste_file named in the list, then run its then_run command.")


def parse_cc_text(text):
    """Turn text copied from a Creative Center hashtag list into rows. Tolerant of one-value-per-line and
    'value label' layouts, English or Spanish labels. Anything not recognised is left blank, never guessed."""
    lines = [l.strip() for l in text.replace(" ", " ").splitlines()]
    lines = [l for l in lines if l]
    rows, cur, last_int = [], None, None
    for i, l in enumerate(lines):
        m = re.fullmatch(r"#\s*([^\s#]+)", l)
        if m:
            if cur:
                rows.append(cur)
            cur = {"title_or_name": "#" + m.group(1), "rank": last_int or "", "posts": "", "views": "", "unparsed": []}
            last_int = None
            continue
        nxt = lines[i + 1].lower() if i + 1 < len(lines) else ""
        if re.fullmatch(r"\d{1,3}", l) and nxt not in CC_LABELS:
            last_int = l  # a bare small integer not followed by a label is the next row's rank
            continue
        if cur is None:
            continue
        m = re.fullmatch(NUM + r"\s+([A-Za-zÁÉÍÓÚáéíóú]+)", l)
        if m and m.group(2).lower() in CC_LABELS:
            cur[CC_LABELS[m.group(2).lower()]] = cur[CC_LABELS[m.group(2).lower()]] or m.group(1).replace(" ", "")
            continue
        if l.lower() in CC_LABELS and i > 0 and re.fullmatch(NUM, lines[i - 1]):
            cur[CC_LABELS[l.lower()]] = cur[CC_LABELS[l.lower()]] or lines[i - 1].replace(" ", "")
            continue
        if not re.fullmatch(NUM, l):
            cur["unparsed"].append(l)
    if cur:
        rows.append(cur)
    return rows


def cmd_cc_paste(a):
    p = Path(a.file)
    rows = parse_cc_text(p.read_text(encoding="utf-8-sig"))
    if not rows:
        sys.exit("No hashtags found. Copy the hashtag list page (rows starting with #) and paste the text unchanged.")
    from datetime import datetime as _dt, timezone as _tz
    if a.observed_at:
        observed, how = a.observed_at, "given"
    else:
        observed, how = rc.iso(_dt.fromtimestamp(p.stat().st_mtime, _tz.utc)), "paste file's modified time"
    url = CC_HASHTAG.format(region=a.region.upper(), period=a.period)
    out = p.with_suffix(".csv")
    head = ["platform", "entity_type", "title_or_name", "rank", "posts", "views", "region", "region_evidence", "period",
            "category", "observed_at_utc", "source", "collected_via", "source_url", "notes"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(head)
        for r in rows:
            note = ("unparsed text: " + " / ".join(r["unparsed"][:4])) if r["unparsed"] else ""
            w.writerow(["tiktok", "hashtag", r["title_or_name"], r["rank"], r["posts"], r["views"], a.region.upper(),
                        "source_filter", f"{a.period} days", a.category or "", observed, "creative_center",
                        "manual_copy_paste", url, note])
    print(f"{len(rows)} hashtags parsed from {p.name} (observed_at: {how}). Preview:")
    print(f"  {'rank':>4}  {'hashtag':32} {'posts':>8} {'views':>9}")
    for r in rows[:15]:
        print(f"  {r['rank'] or '-':>4}  {r['title_or_name'][:32]:32} {r['posts'] or '-':>8} {r['views'] or '-':>9}")
    if len(rows) > 15:
        print(f"  ... {len(rows) - 15} more")
    blanks = sum(1 for r in rows if not (r["posts"] and r["views"]))
    if blanks:
        print(f"  WARN {blanks} rows are missing posts or views: they stay blank. Check them against the page.")
    print(f"Wrote {out}. Compare the preview with the page, then: .\\ss observe import \"{out}\"")
    if a.import_now:
        a.files, a.source = [str(out)], None
        for k in ("provenance", "platform", "entity_type", "region_evidence", "collected_via", "source_url", "sample_role"):
            setattr(a, k, None)
        a.date_order, a.oembed, a.skip_bad = None, False, False
        cmd_check(a, imp=True)


def read_clipboard(tk_root):
    try:
        return tk_root.clipboard_get()
    except Exception:  # empty or non-text clipboard
        return ""


def cmd_cc_session(a):
    """Guided Creative Center session: open each market/period page in the owner's browser, wait for the owner to
    copy the page (Ctrl+A, Ctrl+C), then parse, save and import it and open the next page. The owner's browser does
    all access; this only reads clipboard text that parses as a hashtag list (anything else is ignored, not stored)."""
    import hashlib
    import time
    import tkinter
    import webbrowser
    regions = [r.strip().upper() for r in (a.regions or ",".join(rc.settings()["trends"]["geos"])).split(",") if r.strip()]
    periods = [p.strip() for p in a.periods.split(",") if p.strip()]
    d, _ = store_paths(a)
    inbox = d / "inbox"
    inbox.mkdir(exist_ok=True)
    root = tkinter.Tk()
    root.withdraw()
    seen = hashlib.sha256(read_clipboard(root).encode()).hexdigest()
    results = []
    pages = [(r, p) for r in regions for p in periods]
    print(f"Creative Center session: {len(pages)} pages. On each page that opens: "
          + (f"select the '{a.category}' industry, " if a.category else "") +
          "scroll once so the rows load, press Ctrl+A then Ctrl+C. Ctrl+C here to stop.")
    for n, (region, period) in enumerate(pages, 1):
        url = CC_HASHTAG.format(region=region, period=period)
        print(f"\n[{n}/{len(pages)}] {region}, {period} days: {url}")
        if not a.no_open:
            webbrowser.open(url)
        deadline, got = time.time() + a.timeout, None
        while time.time() < deadline:
            root.update()
            text = read_clipboard(root)
            h = hashlib.sha256(text.encode()).hexdigest()
            if h != seen:
                seen = h
                rows = parse_cc_text(text)
                if len(rows) >= 2:
                    got = (text, rows)
                    break
                print("  clipboard changed but doesn't look like a hashtag list; still waiting")
            time.sleep(0.7)
        if not got:
            print("  no copy received; skipped")
            results.append((region, period, "skipped", 0))
            continue
        stamp = f"{rc.now():%Y%m%d_%H%M%S}"
        paste = inbox / f"cc_{region}_{period}d_{stamp}.txt"
        paste.write_text(got[0], encoding="utf-8")
        sub = argparse.Namespace(**{**vars(a), "file": str(paste), "region": region, "period": period,
                                    "observed_at": rc.iso(rc.now()), "import_now": True})
        try:
            cmd_cc_paste(sub)
            results.append((region, period, "imported", len(got[1])))
        except SystemExit as e:
            results.append((region, period, f"import refused ({e.code})", len(got[1])))
    root.destroy()
    print("\nSession summary:")
    for region, period, status, n in results:
        print(f"  {region} {period:>3} days: {status} ({n} hashtags)")


def cmd_template(a):
    d, _ = store_paths(a)
    inbox = d / "inbox"
    inbox.mkdir(exist_ok=True)
    src = TEMPLATES / ("public_observations_template.csv" if a.kind == "general" else f"examples/observations_{a.kind}.csv")
    dst = inbox / f"{a.kind}_{rc.now():%Y%m%d_%H%M}.csv"
    shutil.copyfile(src, dst)
    print(f"{dst}\nFill it in (leave unknown cells blank), then: .\\ss observe import \"{dst}\"")


def cmd_report(a):
    d, store = store_paths(a)
    rows = rc.read_rows(store)
    cols = [(f, "import" if f not in ("obs_key", "content_key", "import_id", "imported_at_utc") else "local",
             DICT.get(f, "")) for f in STORE_FIELDS]
    dest = rc.export("observations", "public_observations", rows, cols, notes=[
        "One row per item x metric x observation. Repeat observations of the same item share content_key.",
        "value_display is exactly what was seen; value_numeric is its number; value_rounded=true means it was "
        "shown abbreviated (24.5K) so the true value could be up to the next rounding step.",
        "provenance: P1 platform's own displayed count, P2 rank/index, P3 third-party tool figure, P4 interpretation.",
        "metric_definition=unknown means nobody has confirmed what the platform counts in that number.",
        "sample_role tells featured examples (picked because they did well) from ordinary/failed ones.",
        "Language and region columns say only what the source or a person recorded; region from a filter is not audience geography."],
        provenance="mixed (see provenance column)", retention_rule="manual public observations; refresh counts before reuse",
        expires_at=None, share=True, dry_run=a.dry_run, out_dir=(d / "reports") if a.data_dir else None)
    print(f"{len(rows)} rows -> {dest}")


def cmd_list(a):
    _, store = store_paths(a)
    by = {}
    for r in rc.read_rows(store):
        by.setdefault(r["content_key"], set()).add(r["observed_at_utc"])
    for k, times in sorted(by.items(), key=lambda kv: -len(kv[1])):
        print(f"{len(times):3} observations  {k}")


DICT = {
    "obs_key": "dedupe key: content_key | metric | source | observed_at_utc | region | period | category",
    "import_id": "which imported file the row came from", "platform": "tiktok / instagram / youtube / ...",
    "entity_type": "post / hashtag / sound / creator / keyword / search_term / game / trend",
    "content_key": "stable item key across observations (platform:type:id or name)",
    "content_id": "platform ID (from the URL when possible)", "url": "canonical public URL of the item",
    "creator_handle": "@handle without @", "creator_name": "display name as seen",
    "title_or_name": "title, caption, hashtag, sound or keyword", "published_at_utc": "when the item was posted, UTC",
    "observed_at_utc": "when the value was seen, UTC", "observed_precision": "second or day",
    "source": "where the value came from (creative_center, platform_page, tinyfish, vidiq, ...)",
    "collected_via": "who/what read it", "provenance": "P1/P2/P3/P4 (see notes)",
    "region": "region filter or market shown by the source", "region_evidence": "what the region means (source_filter = a tool's region setting)",
    "period": "time window the source used (e.g. 7 days)", "category": "category/industry filter used",
    "metric": "rank, views, likes, posts, ... or hook/format_description (P4), or _seen",
    "value_display": "exactly as shown", "value_numeric": "number parsed from value_display",
    "value_rounded": "true if shown abbreviated (K/M/B)", "metric_definition": "verified / unknown / interpretation",
    "content_language": "language as recorded", "language_evidence": "how the language was decided",
    "sample_role": "featured / ordinary / failed / unknown", "concept_id": "ChatGPT's concept ID",
    "meme_id": "specific joke/meme ID", "sound_id": "audio ID", "format_id": "story/edit structure ID",
    "genre_id": "broad genre ID", "notes": "free text", "source_url": "page the value was read on (e.g. Creative Center URL)",
    "oembed_checked": "TikTok oEmbed confirmed the URL (true) or failed", "imported_at_utc": "when it was imported",
}


def main():
    sys.stdout.reconfigure(errors="replace")  # titles contain emoji the Windows console can't encode
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--data-dir", help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("template")
    t.add_argument("--kind", choices=["general", "creative_center", "post", "vidiq"], default="general")
    for name in ("check", "import"):
        p = sub.add_parser(name)
        p.add_argument("files", nargs="+")
        p.add_argument("--source", help="creative_center, creator_search_insights, platform_page, manual, tinyfish, vidiq, ttanon, wieldr, other_tool")
        p.add_argument("--provenance", choices=["P1", "P2", "P3", "P4"], help="override the source's default")
        p.add_argument("--platform")
        p.add_argument("--entity-type")
        p.add_argument("--observed-at", help="observation date/time for rows that don't have one (YYYY-MM-DD or ISO with Z)")
        p.add_argument("--date-order", choices=["dmy", "mdy"], help="how to read 03/04/2026-style dates")
        p.add_argument("--region", help="e.g. US, MX (the source's region filter)")
        p.add_argument("--region-evidence", help="default source_filter when --region is given")
        p.add_argument("--period", help="e.g. 7 days")
        p.add_argument("--category", help="e.g. Games")
        p.add_argument("--collected-via")
        p.add_argument("--source-url", help="page the values were read on")
        p.add_argument("--sample-role", choices=["featured", "ordinary", "failed", "unknown"])
        p.add_argument("--oembed", action="store_true", help="check TikTok post URLs with TikTok's oEmbed (fills handle/title)")
        p.add_argument("--skip-bad", action="store_true", help="import valid rows even if some rows have errors")
    sub.add_parser("report")
    sub.add_parser("list")
    cl = sub.add_parser("cc-links", help="Creative Center hashtag pages for each market and period (+ a session list)")
    cl.add_argument("--regions", help="e.g. US,GB,MX,ES,AR,CO,CL (default: settings.json trends.geos)")
    cl.add_argument("--periods", default="7,30", help="days: 7, 30 or 120 (default 7,30)")
    cl.add_argument("--category", help="industry you will select on the page, e.g. Games (recorded only)")
    cl.add_argument("--open", action="store_true", help="open each page in your default browser")
    cp = sub.add_parser("cc-paste", help="turn text copied from a Creative Center hashtag page into a checked CSV")
    cp.add_argument("file", help="a .txt with the page text pasted unchanged")
    cp.add_argument("--region", required=True)
    cp.add_argument("--period", required=True, help="days shown on the page (7, 30, 120)")
    cp.add_argument("--category", help="industry filter that was selected, e.g. Games")
    cp.add_argument("--observed-at", help="when you copied it (default: the paste file's modified time)")
    cp.add_argument("--import", dest="import_now", action="store_true", help="import straight away after the preview")
    cs = sub.add_parser("cc-session", help="guided session: opens each page, waits for your Ctrl+A/Ctrl+C, imports, next")
    cs.add_argument("--regions", help="default: settings.json trends.geos")
    cs.add_argument("--periods", default="7", help="days: 7, 30 or 120 (default 7)")
    cs.add_argument("--category", help="industry to select on each page, e.g. Games (recorded with the rows)")
    cs.add_argument("--timeout", type=int, default=240, help="seconds to wait per page before skipping it")
    cs.add_argument("--no-open", action="store_true", help="don't open pages (you navigate yourself)")
    a = ap.parse_args()
    if a.cmd == "cc-session":
        cmd_cc_session(a)
    elif a.cmd == "cc-links":
        cmd_cc_links(a)
    elif a.cmd == "cc-paste":
        cmd_cc_paste(a)
    elif a.cmd == "template":
        cmd_template(a)
    elif a.cmd == "check":
        cmd_check(a)
    elif a.cmd == "import":
        cmd_check(a, imp=True)
    elif a.cmd == "report":
        cmd_report(a)
    else:
        cmd_list(a)


if __name__ == "__main__":
    main()
