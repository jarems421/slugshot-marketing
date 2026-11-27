"""Portable campaign snapshot for the owner, ChatGPT, Claude and Gemini.

`ss dash export [--detail overview|detailed] [--local]`:
- default (safe to share): exports/share/dashboard/slugshot_snapshot_<UTC>/, sharing rules from
  config/dashboard/settings.json applied, local media paths removed, then every file is scanned for
  credential values and the export is deleted if any appears.
- --local: data/local/dashboard/exports/ (private; everything, still no credentials).
Files are individually readable (Markdown + CSV + JSON), no ZIP. Platforms stay in separate files.
"""
import csv
import io
import json
import shutil
from datetime import datetime, timezone

from . import sync, vault, views
from .store import DATA, ROOT, is_fixture_db, metric_defs, now_iso, settings

SHARE_DIR = ROOT / "exports" / "share" / "dashboard"
LOCAL_DIR = DATA / "exports"
SOURCE_RULE = {"youtube_analytics": "youtube_analytics", "instagram": "instagram", "tiktok": "tiktok",
               "roblox_analytics": "roblox_analytics", "roblox_public": "roblox_public"}


def allowed(source, rules, platform=None):
    """Buffer carries TikTok and Instagram data, so its rows also need their platform's rule."""
    key = "manual" if source.startswith("manual") else SOURCE_RULE.get(source, source)
    if source == "buffer" and platform and not rules.get(platform, False):
        return False
    return bool(rules.get(key, False))


def _csv(rows, cols):
    buf = io.StringIO()
    w = csv.DictWriter(buf, cols, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in cols})
    return buf.getvalue()


def fmt(v):
    if v is None:
        return "no data"
    return f"{v:,.0f}" if abs(v) >= 100 or float(v).is_integer() else f"{v:,.3g}"


def build(store, detail="overview", share=True, filters=None):
    f = dict(filters or {})
    rules = settings()["sharing"] if share else {k: True for k in settings()["sharing"]}
    start, end = views.window(f)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = (SHARE_DIR if share else LOCAL_DIR) / f"slugshot_snapshot_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    files, excluded = {}, []

    defs = metric_defs()
    files["metric_definitions.csv"] = (_csv(defs["metrics"], ["id", "label", "kind", "unit", "stage", "platforms", "definition"]),
                                       "all", len(defs["metrics"]))
    health = sync.health(store)
    files["sources.csv"] = (_csv(health, ["connector", "platform", "account_id", "language", "credential", "freshness",
                                          "last_success_utc", "last_status", "last_message"]), "all", len(health))
    accounts = store.accounts()
    files["accounts.csv"] = (_csv(accounts, ["account_id", "platform", "language", "label", "handle"]), "all", len(accounts))

    content = views.content(store, f)["uploads"]
    metric_cols = ["views", "likes", "comments", "shares", "saves", "watch_time_minutes", "avg_view_duration_s",
                   "avg_view_pct", "completion_rate", "reach", "profile_visits", "link_new_players"]
    for p in ("youtube", "tiktok", "instagram"):
        rows = []
        for u in content:
            if u["platform"] != p:
                continue
            lat = views.latest_upload_metrics(store, u["upload_id"])
            srcs = {v["source"] for v in lat.values()}
            if srcs and not any(allowed(s, rules, p) for s in srcs):
                excluded.append(f"{p} upload metrics from {', '.join(sorted(srcs))} (sharing rule)")
                continue
            row = {k: u.get(k) for k in ("upload_id", "asset_id", "concept_id", "concept_title", "format", "hook_type", "slug",
                                         "language", "account_id", "url", "published_at_utc", "observed_at", "production_minutes")}
            row["edit_file"] = u.get("edit_file") if rules.get("local_media_paths") else ""
            for m in metric_cols:
                v = lat.get(m)
                row[m] = v["value"] if v and v["status"] == "value" and allowed(v["source"], rules, p) else ("unavailable" if v and v["status"] == "unavailable" else None)
            rows.append(row)
        if rows:
            files[f"content_{p}.csv"] = (_csv(rows, list(rows[0])), p, len(rows))

    ov = views.overview(store, f)
    gm = views.game(store, f)
    exps = views.experiments(store)
    for e in exps:
        for v in e["variants"]:
            for u in v["uploads"]:
                if not rules.get("local_media_paths"):
                    u.pop("edit_file", None)
    files["experiments.json"] = (json.dumps(exps, indent=1, ensure_ascii=False), "all", len(exps))
    files["experiments.csv"] = (_csv(exps, ["experiment_id", "title", "status", "hypothesis", "one_change", "primary_metric",
                                            "window_hours", "stop_rule", "threshold", "results", "limitations", "decision",
                                            "next_action", "source"]), "all", len(exps))

    if detail == "detailed":
        obs = store.q("""SELECT platform, account_id, entity_type, entity_id, metric, value, status, period_type, period_start,
                         period_end, breakdown_dim, breakdown_value, observed_at_utc, source, provenance, run_id, note
                         FROM observations WHERE (period_start='' OR period_start BETWEEN ? AND ?) ORDER BY platform, metric, period_start""",
                      (start, end))
        for p in ("youtube", "tiktok", "instagram", "roblox"):
            rows = [o for o in obs if o["platform"] == p and allowed(o["source"], rules, p)]
            dropped = [o for o in obs if o["platform"] == p and not allowed(o["source"], rules, p)]
            if dropped:
                excluded.append(f"{len(dropped)} {p} observations (sharing rule)")
            if rows:
                files[f"observations_{p}.csv"] = (_csv(rows, list(rows[0])), p, len(rows))

    research = views.research(store)
    if rules.get("research_evidence"):
        claims = [{"ledger_id": l["ledger_id"], "claim_id": c["id"], "level": c["level"], "level_label": c["level_label"],
                   "support": c["support"], "strength": c["strength"], "claim": c["text"]}
                  for l in research["ledgers"] if not l["example"] for c in l["claims"]]
        files["research_findings.csv"] = (_csv(claims, ["ledger_id", "claim_id", "level", "level_label", "support", "strength", "claim"]),
                                          "research", len(claims))
        # Knowledge banks through the same gate as `ss kb export`: no comment text, no per-comment rows, no raw inventory.
        kb = views._kb()
        kb_entries = [e for e in kb.load() if not e.get("_error") and kb.exportable(e)]
        if kb_entries:
            rows = []
            for e in kb_entries:
                e = kb.public(e)
                if e.get("bank") == "sentiment":
                    e.pop("items", None)
                rows.append(json.dumps(e, ensure_ascii=False))
            files["knowledge.jsonl"] = ("\n".join(rows) + "\n", "research", len(rows))
            excluded.append("comment text and the raw report inventory (knowledge-bank export policy)")

    # Markdown summary (always last, so it can list the files)
    md = []
    fixture = is_fixture_db()
    md.append(f"# Slugshot campaign snapshot ({detail})\n")
    if fixture:
        md.append("> **FIXTURE DATA. Not real performance.** Generated from test fixtures to show the format.\n")
    md.append(f"Generated {now_iso()} UTC. Window {start} to {end}. Filters: platform={f.get('platform') or 'all'}, "
              f"language={f.get('language') or 'all'}. Mode: {'safe to share' if share else 'local (private)'}.\n")
    md.append("## How to read this\n")
    md.append("- Platforms are never added together: each platform defines a view differently, and one person can follow several accounts.\n"
              "- 'period' values are counts inside the window; 'lifetime' values are cumulative totals at the latest observation.\n"
              "- Funnel stages are separate populations. No conversion rate between stages is given or implied.\n"
              "- Blank or 'no data' means not collected or not provided; 0 means the platform reported zero; 'unavailable' means the provider does not offer that metric through the route we use.\n"
              "- Player numbers (Roblox) are not attributable to videos unless they came through a tracked share link.\n")
    md.append("## Sources and freshness\n")
    md.append("| Source | Account | Status | Last success (UTC) |\n|---|---|---|---|")
    for h in health:
        md.append(f"| {h['label']} | {h['account_label']} | {h['freshness']}{' (' + h['credential'] + ')' if h['credential'] != 'ready' else ''} | {h['last_success_utc'] or '-'} |")
    md.append("\n## Social accounts\n")
    if not ov["platforms"]:
        md.append("No social data yet.\n")
    for p in ov["platforms"]:
        md.append(f"- **{p['platform']}**: views {fmt(p['views'])} ({p['views_basis'] or 'none'}); followers {fmt(p['followers'])}"
                  f"; followers gained {fmt(p['followers_gained'])}; watch time {fmt(p['watch_time_minutes'])} min")
    md.append("\n## Game (Roblox)\n")
    for s in gm["stages"]:
        vals = "; ".join(f"{m['label']} {v['platform']}: {fmt(v['value'])}{' (' + v['basis'] + ')' if v['basis'] else ''}"
                         for m in s["metrics"] for v in m["values"])
        md.append(f"- **{s['label']}** ({s['measures']}): {vals or 'no data'}")
    md.append(f"\n{gm['activation_note']}\n")
    md.append("## Experiments\n")
    for e in exps:
        md.append(f"### {e['experiment_id']}: {e['title']} ({e['status']})\n")
        md.append(f"- Hypothesis: {e['hypothesis']}\n- One change: {e['one_change']}\n- Primary metric: {e['primary_metric']} at {e['window_hours']} h"
                  f"\n- Variants: " + "; ".join(f"{v['variant_id']} {v['role']} '{v['label']}' ({len(v['uploads'])} uploads)" for v in e["variants"]) +
                  f"\n- Results: {e['results'] or 'none recorded'}\n- Decision: {e['decision'] or 'none yet'}\n- Next action: {e['next_action'] or '-'}\n- Limitations: {e['limitations'] or '-'}\n")
    md.append("## Research\n")
    md.append("Collection status: " + ", ".join(f"{c['provider']} {c['status']} {c['at'][:10]}" for c in research["collection"]) + "\n")
    if rules.get("research_evidence"):
        md.append("Findings are in research_findings.csv with their evidence level (O observation, D derived, P pattern, "
                  "I interpretation, C causal, R recommendation), support status and verbal strength. No numeric confidence.\n")
        if "knowledge.jsonl" in files:
            md.append("Knowledge banks are in knowledge.jsonl, one entry per line: `evidence_label` (what kind of evidence), "
                      "`review_status` (draft/reviewed/approved; review is not evidence), `support_status`/`strength` (v1.1 words), "
                      "`review_by` (re-check perishable entries before use). Hypothesis families link to experiments by EXP- ID.\n")
    md.append("## Missing data and limitations\n")
    gaps = [h for h in health if h["freshness"] in ("not connected", "never synced", "stale")]
    for h in gaps:
        md.append(f"- {h['label']} / {h['account_label']}: {h['freshness']} ({h['credential']})")
    md.append("- TikTok Display API gives lifetime counts only (no watch time, completion or retention); those need TikTok Studio imports.")
    md.append("- Instagram follower_count needs 100+ followers; some metrics are rejected per media type and recorded as unavailable.")
    md.append("- Activation (onboarding) has no data source until in-game events are approved and added.")
    for x in excluded:
        md.append(f"- Excluded: {x}")
    md.append("\n## Files\n")
    md.append("| File | Scope | Rows |\n|---|---|---|")
    for name, (_, scope, n) in files.items():
        md.append(f"| {name} | {scope} | {n} |")
    files = {"README.md": ("\n".join(md) + "\n", "all", None), **files}

    secrets = vault.all_secret_values()
    for name, (text, *_rest) in files.items():
        if any(s in text for s in secrets):
            shutil.rmtree(out, ignore_errors=True)
            raise RuntimeError(f"Export stopped: {name} contained a credential value. Nothing was written.")
        (out / name).write_text(text, encoding="utf-8", newline="")
    folder = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    return {"folder": str(folder).replace("\\", "/"), "files": list(files), "excluded": excluded,
            "fixture": fixture}
