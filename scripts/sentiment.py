"""Audience sentiment and opportunity samples (Stage 4.7). Codebook: config/research/codebooks/slugshot-sentiment.json.

A *sample* is one read of comments about one target (a format, sound, meme, creator, our own post), with its
selection method, date, language as observed and denominators. Comment text lives only in a packet file that
expires (30 days); the knowledge bank keeps the coded summary. No usernames, no inferred demographics, no scores.

  ss sentiment packet --youtube --ids V1,V2 --target "In This Town / Huss format" --selection "..." [--name N]
        codes YouTube API comments already fetched by `ss yt comments` (needs the derived-metrics amendment flag)
  ss sentiment packet --paste FILE --platform tiktok|instagram|reddit|devforum|youtube_web|other --locator URL
        --target "..." --selection "..." [--name N]
        comments a person copied from a public page (one per line, or blank-line separated); handles are stripped
  ss sentiment join PACKET ANNOTATIONS [--notes "owner/Claude paraphrase"]
        validates the coding and writes the coded sample to the knowledge bank (sentiment/samples.jsonl)
  ss sentiment list
  ss sentiment prune [--dry-run]       delete expired comment text and expired summaries
  ss sentiment status                  current policy gates
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import kb  # noqa: E402

CODEBOOK = ROOT / "config" / "research" / "codebooks" / "slugshot-sentiment.json"
SETTINGS = ROOT / "config" / "research" / "settings.json"
YT_COMMENTS = ROOT / "data" / "local" / "research" / "youtube" / "youtube_comments.csv"
PLATFORMS = {"tiktok", "instagram", "reddit", "devforum", "youtube_web", "other"}


def work_dir() -> Path:
    d = kb.kb_dir().parent / "sentiment"
    (d / "packets").mkdir(parents=True, exist_ok=True)
    return d


def policy():
    return json.loads(SETTINGS.read_text(encoding="utf-8")).get("sentiment", {})


def codebook():
    return json.loads(CODEBOOK.read_text(encoding="utf-8"))


def now():
    return datetime.now(timezone.utc).replace(microsecond=0)


HANDLE = re.compile(r"(?<![\w.])@[\w.\-]{2,}")
LEAD_NAME = re.compile(r"^\s*[\w.\- ]{2,30}\s*[:·•]\s+")


def scrub(text: str) -> str:
    """Remove handles and a leading 'name:' so no identifiers are stored."""
    return HANDLE.sub("@user", LEAD_NAME.sub("", text)).strip()


def cmd_status(a):
    p = policy()
    print(json.dumps({k: v for k, v in p.items() if not k.startswith("_")}, indent=1))
    return 0


def write_packet(name, meta, items):
    cb = codebook()
    wd = work_dir()
    path = wd / "packets" / f"{name}.jsonl"
    lines = [json.dumps({"_packet": meta}, ensure_ascii=False)] + [json.dumps(i, ensure_ascii=False) for i in items]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ann = wd / "packets" / f"{name}.annotations.jsonl"
    codes = [c["code"] for c in cb["codes"]]
    tmpl = {"key": "<key>", "codebook_version": cb["version"], "codes": {c: "absent" for c in codes},
            "stance": "unclear", "target": ["unclear"], "irony": "literal", "language": "unknown",
            "fatigue_intensity": None, "play_intent_subtype": None, "ai_authenticity_mode": None, "coder": "claude", "note": ""}
    instr = [f"# Sentiment coding packet {name}", "", f"Codebook **{cb['version']}**, unit: {cb['unit']}.",
             f"Target: {meta['target']}. Source: {meta['source']}. Selection: {meta['selection']}.",
             f"Comment text expires {meta['text_expires_at']}; delete copies by then.", "", "Rules:"] + \
            [f"- {r}" for r in cb["rules"]] + ["", "Codes (mark every code for every item: " + ", ".join(cb["states"]) + "):"] + \
            [f"- `{c['code']}`: {c['definition']} {c.get('boundary', '')}" for c in cb["codes"]] + ["", "Item fields:"] + \
            [f"- `{k}`: {', '.join(v['values'])}. {v.get('about', '')}" for k, v in cb["item_fields"].items()] + \
            ["", f"Write one JSON line per item to `{ann.name}`, for example:", "", "```json", json.dumps(tmpl, ensure_ascii=False), "```"]
    (wd / "packets" / f"{name}.md").write_text("\n".join(instr) + "\n", encoding="utf-8")
    return path


def cmd_packet(a):
    p = policy()
    t = now()
    name = a.name or f"{t:%Y%m%d-%H%M}-" + re.sub(r"[^a-z0-9]+", "-", a.target.lower()).strip("-")[:30]
    text_exp = (t + timedelta(days=int(p.get("comment_text_retention_days", 30)))).date().isoformat()
    if a.youtube:
        if not p.get("youtube_api_derived_metrics_accepted"):
            print("Refused: YouTube API comments can't be sentiment-coded until the derived-metrics amendment is accepted "
                  "(config/research/settings.json sentiment.youtube_api_derived_metrics_accepted). See docs/audience-sentiment.md.")
            return 2
        if not YT_COMMENTS.exists():
            print(f"No stored comments: run `ss yt comments --ids ...` first ({YT_COMMENTS}).")
            return 1
        ids = {x.strip() for x in a.ids.split(",") if x.strip()}
        with open(YT_COMMENTS, encoding="utf-8") as fh:
            rows = [r for r in csv.DictReader(fh) if r["video_id"] in ids]
        if not rows:
            print("No stored comments for those video IDs.")
            return 1
        items = [{"key": f"{r['video_id']}:{r['comment_id']}", "unit": r["video_id"], "text": scrub(r["text"]),
                  "observed_at_utc": r.get("observed_at_utc", ""), "order_param": r.get("order_param", "")} for r in rows]
        oldest = min((r.get("observed_at_utc") or t.isoformat())[:10] for r in rows)
        text_exp = min(text_exp, (date.fromisoformat(oldest) + timedelta(days=30)).isoformat())
        meta = {"source": "youtube_api", "platform": "youtube", "target": a.target, "selection": a.selection,
                "locator": ",".join(sorted(ids)), "observed_at": oldest, "text_expires_at": text_exp,
                "derived_metrics_accepted": True, "units": sorted(ids)}
    else:
        if not p.get("manual_sources_enabled", True):
            print("Refused: manual sources disabled in settings.")
            return 2
        if a.platform not in PLATFORMS:
            print(f"--platform must be one of {sorted(PLATFORMS)}")
            return 1
        raw = Path(a.paste).read_text(encoding="utf-8")
        chunks = [c for c in re.split(r"\n\s*\n", raw)] if "\n\n" in raw.strip() else raw.splitlines()
        texts = [scrub(c) for c in chunks if scrub(c)]
        unit = a.locator or a.platform
        items = [{"key": f"m{n:03d}", "unit": unit, "text": tx, "observed_at_utc": t.isoformat()} for n, tx in enumerate(texts, 1)]
        text_exp = (t + timedelta(days=int(p.get("manual_text_retention_days", 30)))).date().isoformat()
        meta = {"source": "manual_paste", "platform": a.platform, "target": a.target, "selection": a.selection,
                "locator": a.locator or "", "observed_at": t.date().isoformat(), "text_expires_at": text_exp, "units": [unit]}
    meta.update({"name": name, "n_items": len(items), "codebook_version": codebook()["version"]})
    path = write_packet(name, meta, items)
    print(f"{len(items)} items -> {path}\nInstructions: {path.with_suffix('.md')}\nAnnotations go in {path.with_name(name + '.annotations.jsonl')}")
    return 0


def read_packet(path: Path):
    lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return lines[0]["_packet"], lines[1:]


def check_annotations(items, anns, cb):
    codes = [c["code"] for c in cb["codes"]]
    fields = cb["item_fields"]
    keys = {i["key"] for i in items}
    errs = []
    seen = set()
    for n, an in enumerate(anns, 1):
        w = f"annotation {n} ({an.get('key')})"
        if an.get("key") not in keys:
            errs.append(f"{w}: key not in packet")
        if an.get("key") in seen:
            errs.append(f"{w}: duplicate key")
        seen.add(an.get("key"))
        if an.get("codebook_version") != cb["version"]:
            errs.append(f"{w}: codebook_version must be {cb['version']}")
        c = an.get("codes") or {}
        for code in codes:
            if c.get(code) not in cb["states"]:
                errs.append(f"{w}: {code} must be one of {cb['states']}")
        for extra in set(c) - set(codes):
            errs.append(f"{w}: unknown code {extra}")
        for f in ("stance", "irony", "language"):
            if an.get(f) not in fields[f]["values"]:
                errs.append(f"{w}: {f} must be one of {fields[f]['values']}")
        tg = an.get("target") or []
        if not tg or any(x not in fields["target"]["values"] for x in tg):
            errs.append(f"{w}: target must be a non-empty list from {fields['target']['values']}")
        for code, f in (("FATIGUE", "fatigue_intensity"), ("PLAY_INTENT", "play_intent_subtype"), ("AUTHENTICITY_AI", "ai_authenticity_mode")):
            if c.get(code) == "present" and an.get(f) not in fields[f]["values"]:
                errs.append(f"{w}: {code} present needs {f} in {fields[f]['values']}")
        if "text" in an or "quote" in an:
            errs.append(f"{w}: annotations must not copy comment text")
    missing = keys - seen
    return errs, missing


def cmd_join(a):
    cb = codebook()
    meta, items = read_packet(Path(a.packet))
    anns = [json.loads(l) for l in Path(a.annotations).read_text(encoding="utf-8").splitlines() if l.strip()]
    errs, missing = check_annotations(items, anns, cb)
    if errs:
        print(f"INVALID: {len(errs)} problems")
        for e in errs[:40]:
            print("  ", e)
        return 1
    unit_of = {i["key"]: i["unit"] for i in items}
    per_unit = defaultdict(lambda: {"n_items": 0, "n_coded": 0, "codes": defaultdict(Counter), "stance": Counter(),
                                    "play_intent_subtype": Counter(), "fatigue_intensity": Counter(), "irony": Counter(),
                                    "language": Counter()})
    for i in items:
        per_unit[i["unit"]]["n_items"] += 1
    for an in anns:
        u = per_unit[unit_of[an["key"]]]
        u["n_coded"] += 1
        for code, st in an["codes"].items():
            u["codes"][code][st] += 1
        for f in ("stance", "irony", "language"):
            u[f][an[f]] += 1
        for f in ("play_intent_subtype", "fatigue_intensity"):
            if an.get(f):
                u[f][an[f]] += 1
    units = {k: {"n_items": v["n_items"], "n_coded": v["n_coded"],
                 "codes": {c: dict(s) for c, s in v["codes"].items()},
                 **{f: dict(v[f]) for f in ("stance", "irony", "language", "play_intent_subtype", "fatigue_intensity")}}
             for k, v in per_unit.items()}
    p = policy()
    yt = meta["source"] == "youtube_api"
    months = int(p.get("derived_retention_months", 36)) if yt else 0
    obs = date.fromisoformat(meta["observed_at"])
    retain = (obs + timedelta(days=30 * months)).isoformat() if yt else \
        (obs + timedelta(days=int(p.get("manual_summary_retention_days", 365)))).isoformat()
    sid = "SENT-" + re.sub(r"[^A-Za-z0-9-]+", "-", meta["name"]).upper()
    entry = {"schema_version": kb.SCHEMA_VERSION, "id": sid, "bank": "sentiment", "kind": "observation",
             "title": f"{meta['target']} · {meta['platform']} · {meta['observed_at']}",
             "statement": a.notes or "", "evidence_label": "observed", "review_status": "draft",
             "shelf_life": "custom", "observed_at": meta["observed_at"],
             "review_by": (obs + timedelta(days=14)).isoformat(),
             "target": meta["target"], "selection": meta["selection"], "platform": meta["platform"],
             "locator": meta["locator"], "codebook_version": cb["version"],
             "denominators": {"items": len(items), "coded": len(anns), "uncoded": len(missing)},
             "units": units,
             "policy": {"source": meta["source"], "contains_comment_text": False,
                        "derived_metrics_accepted": bool(meta.get("derived_metrics_accepted")),
                        "cross_channel_aggregate": False, "retention_until": retain,
                        "packet_text_expires_at": meta["text_expires_at"], "export": "summary_only"},
             "caveats": ["Commenters are self-selected; counts describe this read only, not the audience or the trend.",
                         "One snapshot: no lifecycle or prevalence claim.",
                         "Coded by " + ", ".join(sorted({an.get('coder', '?') for an in anns})) + "; ambiguous items stay uncertain."],
             "tags": {"language": sorted({l for u in units.values() for l in u["language"] if l in kb.LANGS})},
             "history": [{"date": now().date().isoformat(), "by": "claude", "note": f"joined {len(anns)} annotations"}]}
    out = kb.kb_dir() / "sentiment" / "samples.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    old = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()] if out.exists() else []
    old = [o for o in old if o.get("id") != sid] + [entry]
    out.write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in old) + "\n", encoding="utf-8")
    print(f"{sid}: {len(anns)} coded of {len(items)} ({len(missing)} uncoded) across {len(units)} unit(s) -> {out}")
    if yt:
        print("Per-video counts only; no cross-channel totals are computed.")
    return 0


def cmd_list(a):
    out = kb.kb_dir() / "sentiment" / "samples.jsonl"
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines() if l.strip()] if out.exists() else []
    for r in rows:
        print(f"{r['id']:<44} {r['title'][:60]:<60} coded {r['denominators']['coded']}/{r['denominators']['items']}  {kb.status_of(r)}")
    print(f"{len(rows)} samples; packets in {work_dir() / 'packets'}")
    return 0


def cmd_prune(a, today=None):
    today = today or now().date()
    removed = []
    for pk in sorted((work_dir() / "packets").glob("*.jsonl")):
        if pk.name.endswith(".annotations.jsonl"):
            continue
        meta, _ = read_packet(pk)
        if date.fromisoformat(meta["text_expires_at"]) < today:
            for f in (pk, pk.with_suffix(".md"), pk.with_name(pk.stem + ".annotations.jsonl")):
                if f.exists():
                    removed.append(f)
    out = kb.kb_dir() / "sentiment" / "samples.jsonl"
    keep, dropped = [], []
    if out.exists():
        for l in out.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            r = json.loads(l)
            (dropped if date.fromisoformat(r["policy"]["retention_until"]) < today else keep).append(r)
    for f in removed:
        print(("would delete " if a.dry_run else "deleted ") + str(f))
        if not a.dry_run:
            f.unlink()
    if dropped:
        print(("would drop " if a.dry_run else "dropped ") + ", ".join(r["id"] for r in dropped))
        if not a.dry_run:
            out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in keep) + ("\n" if keep else ""), encoding="utf-8")
    print(f"{len(removed)} expired text files, {len(dropped)} expired summaries")
    return 0


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="ss sentiment", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    p = sub.add_parser("packet")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--youtube", action="store_true")
    src.add_argument("--paste")
    p.add_argument("--ids", default="")
    p.add_argument("--platform", default="other")
    p.add_argument("--locator", default="")
    p.add_argument("--target", required=True)
    p.add_argument("--selection", required=True, help="how the items were picked, e.g. 'relevance order, 3 ordinary + 2 featured videos'")
    p.add_argument("--name")
    j = sub.add_parser("join")
    j.add_argument("packet")
    j.add_argument("annotations")
    j.add_argument("--notes", default="")
    sub.add_parser("list")
    pr = sub.add_parser("prune")
    pr.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    return {"status": cmd_status, "packet": cmd_packet, "join": cmd_join, "list": cmd_list, "prune": cmd_prune}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
