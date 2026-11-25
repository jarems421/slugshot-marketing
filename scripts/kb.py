"""Slugshot knowledge banks (Stage 4.7): private local JSONL, validated, filterable, exportable.

Banks live in data/local/research/knowledge/ (git-ignored; override with SLUGSHOT_KB_DIR):
  curated/*.jsonl     hand-reviewed entries (mechanisms, principles, funnel, characters, hypotheses, decisions, ...)
  generated/*.jsonl   rebuilt by `kb migrate` from an audit folder (inventory, works, claims, culture cards)
  sentiment/*.jsonl   coded audience-opinion samples written by `ss sentiment join`
  views/, INDEX.md    Markdown rendered by `kb render` (never edited by hand)

Evidence stays in the evidence ledgers (data/local/research/evidence/); entries point to ledger claims.
No numeric confidence and no composite scores anywhere.

  ss kb validate                       schema, references, game truth, expiry, duplicates, policy
  ss kb find [TEXT] [--bank B --objective O --format F --lang L --character C --stage S --evidence E --status S --due]
  ss kb show ID                         one entry with its resolved links and ledger claims
  ss kb due                             entries past review_by (stale) or expiring within 14 days
  ss kb brief "CONCEPT TEXT" [--character floppy --format SKIT --lang es]   relevant entries for a concept
  ss kb stats
  ss kb render                          INDEX.md + views/<bank>.md
  ss kb export [--out DIR]              AI-readable snapshot to exports/share/knowledge/<stamp>/ (policy-gated)
  ss kb migrate --audit DIR             (re)generate generated/*.jsonl from a research audit folder
  ss kb new BANK                        print a blank entry for that bank
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "kb-1.0"
LEDGER_DIR = ROOT / "data" / "local" / "research" / "evidence"
GAME_TRUTH = ROOT / "docs" / "game-truth.md"
SHARE = ROOT / "exports" / "share" / "knowledge"

BANKS = {  # bank -> id prefix
    "inventory": "INV", "sources": "WRK", "claims": "CLM", "amendments": "AMD", "mechanisms": "MECH", "hooks": "HOOK",
    "narrative": "NARR", "humour": "HUM", "characters": "CHAR", "culture": "CULT", "sentiment": "SENT",
    "opportunities": "OPP", "audiovisual": "AV", "funnel": "FUN", "hypotheses": "HYP", "decisions": "DEC"}
PREFIX_BANK = {v: k for k, v in BANKS.items()}
KINDS = {"source", "inventory_item", "claim", "amendment", "mechanism", "principle", "fact", "card", "observation",
         "opportunity", "hypothesis", "decision", "definition"}
EVIDENCE_LABELS = {"established", "adjacent", "verified_platform", "owned_result", "application", "untested",
                   "owner_hypothesis", "inventory", "observed"}
EVIDENCE_BACKED = {"established", "adjacent", "verified_platform", "owned_result"}
REVIEW = ["draft", "reviewed", "approved", "retired"]
SUPPORT = {"supported", "partially_supported", "unsupported", "indeterminate"}
STRENGTH = {"exploratory", "suggestive", "supported_descriptive", "convergent", "experimental"}
SHELF = {"evergreen": None, "platform_90d": 90, "cultural_30d": 30, "cultural_14d": 14, "cultural_7d": 7,
         "sentiment_30d": 30, "custom": None}
LINK_TYPES = {"supports", "conflicts_with", "moderates", "mediates", "applies", "tested_by", "supersedes", "derived_from",
              "amends", "alias_of", "refines"}
OBJECTIVES = {"reach", "viewer_experience", "brand_memory", "interest", "acquisition", "activation", "retention",
              "monetisation", "production_efficiency", "safety"}
STAGES = {"Discovery", "Engagement", "Interest", "Acquisition", "Activation", "Retention", "Monetisation"}
JOURNEY = {"stop", "understand", "care", "remember", "want", "find", "stay"}
FORMATS = {"PVP", "PROMO", "CHOICE", "WORLD", "SKIT", "AISCENE", "TEST"}
LANGS = {"en", "es", "mixed", "unknown"}
GT_LABELS = {"OK", "CAPTURE", "FICTION", "NO", "AVOID"}
EXTERNAL_REF = re.compile(r"^(EXP|CON)-[A-Z0-9-]+$|^S46\d-[A-Z]+\d+[a-z]?$|^https?://")
CAUSAL = re.compile(r"\b(causes?|caused|drives?|boosts?|proves?|because of|leads to|guarantees?)\b", re.I)
SENT_SOURCES = {"youtube_api", "youtube_own_api", "instagram_own_api", "manual_paste", "manual_notes"}


def kb_dir() -> Path:
    return Path(os.environ.get("SLUGSHOT_KB_DIR") or ROOT / "data" / "local" / "research" / "knowledge")


def today() -> date:
    return datetime.now(timezone.utc).date()


def parse_day(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ load
def load(base: Path | None = None):
    base = base or kb_dir()
    entries, origin = [], {}
    for sub in ("curated", "generated", "sentiment"):
        for p in sorted((base / sub).glob("*.jsonl")) if (base / sub).exists() else []:
            for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip() or line.lstrip().startswith("//"):
                    continue
                try:
                    e = json.loads(line)
                except ValueError as ex:
                    entries.append({"id": f"__BAD__{p.name}:{n}", "_error": f"{p.name}:{n}: invalid JSON ({ex})"})
                    continue
                e["_file"] = f"{sub}/{p.name}:{n}"
                entries.append(e)
    return entries


def ledgers():
    out = {}
    for p in sorted(LEDGER_DIR.glob("*.json")) if LEDGER_DIR.exists() else []:
        if p.name.endswith(".evidenceguard.json"):
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for c in d.get("claims", []):
            out[f"{d.get('ledger_id', p.stem)}:{c.get('claim_id')}"] = c
    return out


def game_truth_rows():
    """{claim text: label} from the table in docs/game-truth.md."""
    rows = {}
    if not GAME_TRUTH.exists():
        return rows
    for line in GAME_TRUTH.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[1] and not set(cells[1]) <= set("-: ") and cells[0] != "Claim":
            rows[cells[0]] = cells[1].split()[0].strip(",").upper()
    return rows


def status_of(e, ref_day=None):
    """fresh / due (within 14 days) / stale (past review_by) / evergreen."""
    ref_day = ref_day or today()
    rb = parse_day(e.get("review_by"))
    if not rb:
        return "evergreen" if e.get("shelf_life") == "evergreen" else "undated"
    if rb < ref_day:
        return "stale"
    return "due" if (rb - ref_day).days <= 14 else "fresh"


# ------------------------------------------------------------------ validate
def validate(entries, ledger_claims=None, gt=None, ref_day=None):
    ledger_claims = ledgers() if ledger_claims is None else ledger_claims
    gt = game_truth_rows() if gt is None else gt
    errs, warns = [], []
    ids = Counter(e.get("id") for e in entries)
    known = set(ids)
    aliases = {a for e in entries for a in e.get("report_aliases", [])}
    for e in entries:
        w = e.get("id", "?")
        E = lambda m: errs.append(f"{w}: {m}")  # noqa: E731
        W = lambda m: warns.append(f"{w}: {m}")  # noqa: E731
        if "_error" in e:
            errs.append(e["_error"])
            continue
        if ids[w] > 1:
            E(f"duplicate id ({ids[w]} entries)")
        for f in ("id", "bank", "kind", "title", "evidence_label", "review_status", "shelf_life"):
            if not e.get(f):
                E(f"missing {f}")
        if e.get("schema_version") != SCHEMA_VERSION:
            E(f"schema_version must be {SCHEMA_VERSION}")
        pre = w.split("-")[0]
        if e.get("bank") not in BANKS:
            E(f"unknown bank {e.get('bank')}")
        elif PREFIX_BANK.get(pre) != e.get("bank"):
            E(f"id prefix {pre} does not belong to bank {e.get('bank')} (expects {BANKS[e['bank']]}-)")
        if not re.fullmatch(r"[A-Z]+-[A-Za-z0-9.-]+", w):
            E("id must look like PREFIX-NAME")
        if e.get("kind") and e["kind"] not in KINDS:
            E(f"kind {e['kind']} unknown")
        if e.get("evidence_label") and e["evidence_label"] not in EVIDENCE_LABELS:
            E(f"evidence_label {e['evidence_label']} unknown")
        if e.get("review_status") and e["review_status"] not in REVIEW:
            E(f"review_status {e['review_status']} unknown")
        if e.get("review_status") == "approved" and not any(h.get("by") == "owner" for h in e.get("history", [])):
            E("approved needs an owner entry in history")
        if e.get("shelf_life") and e["shelf_life"] not in SHELF:
            E(f"shelf_life {e['shelf_life']} unknown")
        for f in ("observed_at", "review_by"):
            if e.get(f) and not parse_day(e[f]):
                E(f"{f} is not an ISO date")
        if e.get("shelf_life") and e["shelf_life"] != "evergreen":
            if not e.get("observed_at"):
                E("expiring entry needs observed_at")
            if not e.get("review_by"):
                E("expiring entry needs review_by")
        if e.get("support_status") and e["support_status"] not in SUPPORT:
            E(f"support_status {e['support_status']} unknown")
        if e.get("strength") and e["strength"] not in STRENGTH:
            E(f"strength {e['strength']} unknown")
        if e.get("strength") == "experimental" and e.get("evidence_label") != "owned_result":
            E("experimental strength is reserved for our own controlled tests")
        if e.get("evidence_label") in EVIDENCE_BACKED and e.get("kind") not in ("source", "inventory_item"):
            if not (e.get("claim_refs") or e.get("evidence_refs") or e.get("source_refs")):
                E("evidence-backed entry needs claim_refs, evidence_refs or source_refs")
            if not e.get("support_status"):
                E("evidence-backed entry needs support_status")
        for cr in e.get("claim_refs", []):
            if cr not in ledger_claims:
                E(f"claim_ref {cr} not found in any ledger")
        for sr in e.get("source_refs", []):
            if sr not in known:
                E(f"source_ref {sr} not found")
        for er in e.get("evidence_refs", []):
            if er not in known and er not in aliases and not EXTERNAL_REF.match(er):
                E(f"evidence_ref {er} not found")
        tags = e.get("tags") or {}
        for key, allowed in (("objective", OBJECTIVES), ("funnel_stage", STAGES), ("journey", JOURNEY),
                             ("format", FORMATS), ("language", LANGS)):
            bad = [x for x in tags.get(key, []) if x not in allowed]
            if bad:
                E(f"tags.{key} has unknown values {bad}")
        for m in tags.get("mechanism", []):
            if m not in known:
                E(f"tags.mechanism {m} not found")
        needs_gt = e.get("bank") == "characters" or bool(tags.get("character"))
        if needs_gt and e.get("kind") not in ("inventory_item", "claim", "observation"):
            if not e.get("game_truth"):
                E("character/game entry needs game_truth refs to docs/game-truth.md")
        for g in e.get("game_truth", []):
            row, label = g.get("row", ""), g.get("label", "")
            if label not in GT_LABELS:
                E(f"game_truth label {label} unknown")
            elif row not in gt:
                E(f"game_truth row not in docs/game-truth.md: {row[:70]}")
            elif gt[row] != label:
                E(f"game_truth label {label} != sheet label {gt[row]} for: {row[:60]}")
        if e.get("bank") == "hypotheses":
            for f in ("scope", "design", "comparator"):
                if not e.get(f):
                    E(f"hypothesis needs {f}")
        for l in e.get("links", []):
            if l.get("type") not in LINK_TYPES:
                E(f"link type {l.get('type')} unknown")
            to = l.get("to", "")
            if to not in known and to not in aliases and not EXTERNAL_REF.match(to):
                E(f"link target {to} not found")
        for f in ("experiment_refs", "concept_refs"):
            for x in e.get(f, []):
                if not EXTERNAL_REF.match(x):
                    E(f"{f} {x} must be a dashboard EXP-/CON- id")
        if e.get("bank") in ("sentiment",):
            pol = e.get("policy") or {}
            if pol.get("source") not in SENT_SOURCES:
                E(f"sentiment policy.source must be one of {sorted(SENT_SOURCES)}")
            if pol.get("contains_comment_text"):
                exp = parse_day(pol.get("text_expires_at"))
                if not exp:
                    E("sentiment entry with comment text needs policy.text_expires_at")
                elif exp < (ref_day or today()):
                    E("comment text past its expiry: run `ss sentiment prune`")
            if pol.get("cross_channel_aggregate") and pol.get("source") == "youtube_api" and not pol.get("derived_metrics_accepted"):
                E("cross-channel YouTube aggregation requires the derived-metrics amendment")
            for k in ("username", "author", "handle", "author_channel_id"):
                if k in json.dumps(e.get("items", [])):
                    E(f"sentiment items must not carry {k}")
        if e.get("kind") in ("principle", "mechanism", "fact") and CAUSAL.search(e.get("statement", "")) \
                and e.get("evidence_label") != "owned_result" and not e.get("causal_basis"):
            W("causal wording without causal_basis; restate as an association or add causal_basis")
        st = status_of(e, ref_day)
        if st == "stale" and e.get("review_status") != "retired":
            W(f"stale: review_by {e.get('review_by')} has passed")
    return errs, warns


# ------------------------------------------------------------------ query
def text_of(e):
    return " ".join(str(e.get(k, "")) for k in ("id", "title", "statement", "boundaries", "transfer_assumption",
                                                 "original_text")) + " " + " ".join(e.get("report_aliases", []))


def matches(e, q=None, bank=None, objective=None, fmt=None, lang=None, character=None, stage=None, evidence=None,
            status=None, mechanism=None, journey=None, due=False, include_inventory=False, ref_day=None):
    if bank and e.get("bank") != bank:
        return False
    if not bank and not include_inventory and e.get("bank") in ("inventory",):
        return False
    t = e.get("tags") or {}
    for want, key in ((objective, "objective"), (fmt, "format"), (lang, "language"), (character, "character"),
                      (stage, "funnel_stage"), (mechanism, "mechanism"), (journey, "journey")):
        if want and want not in t.get(key, []):
            return False
    if evidence and e.get("evidence_label") != evidence and e.get("support_status") != evidence:
        return False
    if status and e.get("review_status") != status:
        return False
    if due and status_of(e, ref_day) not in ("due", "stale"):
        return False
    if q:
        hay = text_of(e).lower()
        if not all(w in hay for w in q.lower().split()):
            return False
    return True


def find(entries, **f):
    return [e for e in entries if not e.get("_error") and matches(e, **f)]


def public(e):
    return {k: v for k, v in e.items() if not k.startswith("_")}


def resolve(entries, e):
    """Entry plus resolved links, ledger claims and inbound references."""
    by = {x.get("id"): x for x in entries}
    lc = ledgers()
    out = public(e)
    out["status_freshness"] = status_of(e)
    out["claims_resolved"] = [{"ref": r, **{k: lc[r].get(k) for k in ("claim_text", "level", "support_status", "strength")}}
                              for r in e.get("claim_refs", []) if r in lc]
    out["links_resolved"] = [{"type": l.get("type"), "to": l.get("to"), "title": by.get(l.get("to"), {}).get("title", ""),
                              "note": l.get("note", "")} for l in e.get("links", [])]
    inbound = []
    for x in entries:
        refs = [l.get("to") for l in x.get("links", [])] + x.get("evidence_refs", []) + x.get("source_refs", []) + \
               (x.get("tags") or {}).get("mechanism", [])
        if e.get("id") in refs and x.get("id") != e.get("id"):
            inbound.append({"id": x["id"], "bank": x.get("bank"), "title": x.get("title")})
    out["inbound"] = inbound[:60]
    return out


def brief(entries, text, character=None, fmt=None, lang=None):
    words = {w for w in re.findall(r"[a-záéíóúñü]{4,}", text.lower())}
    scored = []
    for e in entries:
        if e.get("_error") or e.get("bank") in ("inventory", "sources", "claims", "amendments") or e.get("review_status") == "retired":
            continue
        t = e.get("tags") or {}
        hits = len(words & {w for w in re.findall(r"[a-záéíóúñü]{4,}", text_of(e).lower())})
        tag_hit = (character and character in t.get("character", [])) or (fmt and fmt in t.get("format", [])) or \
                  (lang and lang in t.get("language", []))
        if hits or tag_hit or e.get("bank") == "characters" and character:
            scored.append((bool(tag_hit), hits, e))
    scored.sort(key=lambda x: (not x[0], -x[1], x[2]["id"]))   # ordering only; nothing is shown as a score
    groups = defaultdict(list)
    for _, _, e in scored[:40]:
        groups[e["bank"]].append(e)
    return groups


# ------------------------------------------------------------------ render & export
def render(entries, base: Path | None = None):
    base = base or kb_dir()
    (base / "views").mkdir(parents=True, exist_ok=True)
    by_bank = defaultdict(list)
    for e in entries:
        if not e.get("_error"):
            by_bank[e["bank"]].append(e)
    idx = ["# Knowledge banks", "", f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC by `ss kb render` from the JSONL banks. "
           "Do not edit; edit the JSONL and re-render.", "",
           "| Bank | Entries | Reviewed | Due or stale | View |", "|---|---|---|---|---|"]
    for bank in BANKS:
        rows = by_bank.get(bank, [])
        if not rows:
            continue
        rev = sum(1 for e in rows if e.get("review_status") in ("reviewed", "approved"))
        due = sum(1 for e in rows if status_of(e) in ("due", "stale"))
        idx.append(f"| {bank} | {len(rows)} | {rev} | {due} | [views/{bank}.md](views/{bank}.md) |")
        md = [f"# {bank}", "", f"{len(rows)} entries. Evidence label, review status and freshness are separate; no scores.", ""]
        for e in sorted(rows, key=lambda x: x["id"]):
            md.append(f"## {e['id']}: {e.get('title', '')}")
            md.append(f"`{e.get('evidence_label')}` · `{e.get('review_status')}` · {status_of(e)}"
                      + (f" · support `{e['support_status']}`" if e.get("support_status") else "")
                      + (f" · strength `{e['strength']}`" if e.get("strength") else ""))
            if e.get("statement"):
                md += ["", e["statement"]]
            for k, label in (("boundaries", "Boundaries"), ("transfer_assumption", "Transfer assumption")):
                if e.get(k):
                    md += ["", f"*{label}:* {e[k]}"]
            if e.get("report_aliases"):
                md += ["", "Report IDs: " + ", ".join(e["report_aliases"][:30])]
            md.append("")
        (base / "views" / f"{bank}.md").write_text("\n".join(md), encoding="utf-8")
    (base / "INDEX.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    return base / "INDEX.md"


def exportable(e):
    """Safe-export gate: no comment text, no local-only entries, no unreviewed inventory dumps."""
    pol = e.get("policy") or {}
    if pol.get("export") == "local_only" or pol.get("contains_comment_text"):
        return False
    return e.get("bank") != "inventory"


def export(entries, out: Path | None = None):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    out = out or SHARE / stamp
    out.mkdir(parents=True, exist_ok=True)
    keep = [public(e) for e in entries if not e.get("_error") and exportable(e)]
    for e in keep:
        if e.get("bank") == "sentiment":
            e.pop("items", None)          # summaries only; never per-comment rows
    (out / "knowledge.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in keep) + "\n", encoding="utf-8")
    c = Counter(e["bank"] for e in keep)
    stale = [e["id"] for e in keep if status_of(e) == "stale"]
    md = ["# Slugshot knowledge snapshot", "", f"Exported {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC by `ss kb export`. "
          "Internal analysis only; do not publish.", "",
          "Fields: `evidence_label` (established / adjacent / verified_platform / owned_result / application / untested / "
          "owner_hypothesis), `review_status` (draft / reviewed / approved), `support_status` and `strength` (v1.1 words). "
          "Review status is not evidence. No numeric scores exist.", "",
          "| Bank | Entries |", "|---|---|"] + [f"| {b} | {n} |" for b, n in sorted(c.items())] + [
          "", f"Stale entries ({len(stale)}): {', '.join(stale[:40]) or 'none'}", "",
          "Excluded by policy: comment text, per-comment sentiment rows, local-only entries, the raw report inventory."]
    (out / "SNAPSHOT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return out, len(keep)


# ------------------------------------------------------------------ migrate (audit -> generated banks)
def _w(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def migrate(audit: Path, base: Path | None = None, reviews: Path | None = None):
    """Rebuild generated banks from an audit folder (scripts/research_audit*.py outputs). The audit itself is never
    modified. Hand-written claim reviews and source amendments come from curated/claim_reviews.json."""
    base = base or kb_dir()
    inv = json.loads((audit / "inventory.json").read_text(encoding="utf-8"))
    reg = json.loads((audit / "source_register.json").read_text(encoding="utf-8"))
    rd = lambda n: list(csv.DictReader(open(audit / n, encoding="utf-8")))  # noqa: E731
    dois = {r["doi"]: r for r in rd("doi_verification.csv")}
    ev_ver = {r["evidence_id"]: r for r in rd("evidence_verification.csv")}
    cl_ver = {r["claim_id"]: r for r in rd("claim_verification_register.csv")}
    checks = rd("claim_checks.csv")
    reviews = reviews or (base / "curated" / "claim_reviews.json")
    rv = json.loads(reviews.read_text(encoding="utf-8")) if reviews.exists() else {}
    doi_fix = rv.get("doi_corrections", {})
    lineage = rv.get("lineage", {})
    src_amend = rv.get("source_amendments", {})
    observed = rv.get("audit_date", "2026-11-25")
    cluster_of = {m: s["source_id"] for s in reg["sources"] for m in s["member_ids"]}
    fam_of_cluster = {s["source_id"]: s["family"] for s in reg["sources"]}
    items = inv["items"]

    # works: one per DOI, plus one per evidence entry with no DOI; many-to-many with evidence entries
    works, ev_works = {}, defaultdict(list)
    for it in (i for i in items if i["type"] == "evidence"):
        ds = [doi_fix.get(d, d) for d in it["dois"]]
        keys = [("doi", d) for d in ds] or [("ev", it["id"])]
        for k in keys:
            wid = "WRK-" + (re.sub(r"[^A-Za-z0-9]+", "-", k[1]).strip("-").upper()[:60] if k[0] == "doi" else it["id"])
            w = works.setdefault(wid, {"_dois": set(), "_ev": set(), "_urls": set(), "_label": it["source_line"]})
            if k[0] == "doi":
                w["_dois"].add(k[1])
            w["_ev"].add(it["id"])
            w["_urls"].update(it["urls"][:4])
            ev_works[it["id"]].append(wid)
    wrows = []
    for wid, w in sorted(works.items()):
        d = sorted(w["_dois"])
        rec = dois.get(d[0]) or {} if d else {}
        as_cited = [k for k, v in doi_fix.items() if v in d]
        if not rec and as_cited:
            rec = dois.get(as_cited[0]) or {}
        evs = sorted(w["_ev"])
        cl = sorted({cluster_of.get(x, "") for x in evs} - {""})
        if d:
            bib = "corrected_doi" if as_cited else (rec.get("verdict") or "unchecked")
        else:
            outs = {ev_ver.get(x, {}).get("url_outcomes", "") for x in evs}
            bib = "url_loads" if any("ok" in o for o in outs) else ("no_locator" if outs <= {""} else "url_problem")
        am = src_amend.get(wid) or (src_amend.get(d[0]) if d else None) or {}
        wrows.append({"schema_version": SCHEMA_VERSION, "id": wid, "bank": "sources", "kind": "source",
                      "title": (rec.get("record_title") or w["_label"])[:160], "statement": "",
                      "evidence_label": "inventory", "review_status": "draft", "shelf_life": "evergreen",
                      "doi": d[0] if d else "", "doi_as_cited": as_cited, "record_authors": rec.get("record_authors", ""),
                      "record_year": rec.get("record_year", ""), "urls": sorted(w["_urls"])[:6],
                      "family_id": fam_of_cluster.get(cl[0], "") if cl else "",
                      "lineage_id": lineage.get(wid) or (lineage.get(d[0]) if d else None) or wid, "cluster_ids": cl, "evidence_ids": evs,
                      "report_aliases": evs, "bibliographic_status": am.get("bibliographic_status", bib),
                      "access": am.get("access", ""), "amendment_refs": am.get("amendments", []),
                      "history": [{"date": observed, "by": "claude", "note": "migrated from Stage 4.6 audit"}]})
    _w(base / "generated" / "sources.jsonl", wrows)

    # claims: separate verification fields; support only from contextual review
    figs = defaultdict(list)
    for c in checks:
        for rid in c["report_ids"].split(";"):
            figs[rid].append(c)
    creviews = rv.get("claims", {})
    crow = []
    for it in (i for i in items if i["type"] == "claim"):
        v, r = cl_ver.get(it["id"], {}), creviews.get(it["id"], {})
        refs = v.get("evidence_refs", "").split(";") if v.get("evidence_refs") else []
        fig = [f"{c['check_id']}:{c['status']}" for x in [it["id"], *refs] for c in figs.get(x, [])]
        flags = [f for f in v.get("flags", "").split(";") if f]
        self_strength = (it.get("strength") or "").split(" ")[0]
        audit_strength = r.get("audit_strength") or ("suggestive" if self_strength == "convergent" and
                                                     "convergent_with_<2_sources" in flags else "")
        crow.append({"schema_version": SCHEMA_VERSION, "id": "CLM-" + it["id"], "bank": "claims", "kind": "claim",
                     "title": it.get("claim_text", "")[:110], "statement": r.get("bounded_revision", ""),
                     "original_text": it.get("claim_text", ""), "evidence_label": r.get("evidence_label", "inventory"),
                     "review_status": "reviewed" if r else "draft", "shelf_life": "evergreen",
                     "report_aliases": [it["id"]], "report_level": it.get("level", ""),
                     "report_self_support": it.get("support_status", ""), "report_self_strength": it.get("strength", ""),
                     "evidence_refs": [x for x in refs if x],
                     "bibliographic_verification": v.get("audit_status", ""),
                     "figure_presence": sorted(set(fig)), "contextual_verification": r.get("contextual", "not_reviewed"),
                     "design": r.get("design", ""), "directness": r.get("directness", ""),
                     "support_status": r.get("support", "indeterminate"),
                     **({"strength": audit_strength} if audit_strength else {}),
                     "transfer_assumption": r.get("transfer") or ("Adjacent-domain causal design; any effect on Slugshot short-form content is an "
                                                                    "untested transfer hypothesis." if "causal_from_adjacent_domain(transfer_hypothesis)" in flags else ""), "access": r.get("access", ""),
                     "audit_flags": flags, "reviewer": r.get("reviewer", ""), "reviewed_at": r.get("reviewed_at", ""),
                     "claim_refs": r.get("claim_refs", []),
                     "history": [{"date": observed, "by": "claude", "note": "migrated; support is indeterminate unless reviewed in context"}]})
    _w(base / "generated" / "claims.jsonl", crow)

    # culture cards from the reports (perishable)
    cards = []
    for it in (i for i in items if i["type"] == "culture_card"):
        cells = [c for c in it.get("cells", []) if c]
        title = re.sub(r"\s+", " ", cells[1] if len(cells) > 1 else it["source_line"])[:120]
        days = 7 if re.search(r"7 days|7.10 days", it["text"]) else 30
        cards.append({"schema_version": SCHEMA_VERSION, "id": "CULT-" + it["id"], "bank": "culture", "kind": "card",
                      "title": title, "statement": "", "original_text": re.sub(r"\s+", " ", it["text"])[:1500],
                      "evidence_label": "inventory", "review_status": "draft", "shelf_life": "custom",
                      "observed_at": "2026-11-25", "review_by": str(date(2026, 11, 25) + timedelta(days=days)),
                      "report_aliases": [it["id"]],
                      "dimensions": {k: {"rating": "unknown", "note": "single report snapshot; not re-observed"}
                                     for k in ("popularity", "velocity", "persistence", "saturation", "sentiment", "fatigue", "slugshot_fit")},
                      "history": [{"date": observed, "by": "claude", "note": "migrated from report; refresh before use"}]})
    _w(base / "generated" / "culture.jsonl", cards)

    # full inventory, nothing dropped
    irow = []
    for it in items:
        irow.append({"schema_version": SCHEMA_VERSION, "id": "INV-" + it["id"], "bank": "inventory", "kind": "inventory_item",
                     "title": re.sub(r"\s+", " ", (it.get("claim_text") or it["source_line"] or it["id"]))[:140],
                     "statement": "", "original_text": it["text"], "evidence_label": "inventory", "review_status": "draft",
                     "shelf_life": "evergreen", "report_aliases": [it["id"]], "item_type": it["type"],
                     "report": it["report"], "locator": f"{it['report']} lines {it['first_line']}-{it['block_end_line']}",
                     "report_refs": it["refs"], "works": ev_works.get(it["id"], []),
                     "verification": {"evidence": ev_ver.get(it["id"], {}).get("status", ""),
                                      "claim": cl_ver.get(it["id"], {}).get("audit_status", "")}})
    _w(base / "generated" / "inventory.jsonl", irow)
    return {"sources": len(wrows), "claims": len(crow), "culture": len(cards), "inventory": len(irow)}


# ------------------------------------------------------------------ CLI
TEMPLATE = {"schema_version": SCHEMA_VERSION, "id": "", "bank": "", "kind": "principle", "title": "", "statement": "",
            "evidence_label": "untested", "review_status": "draft", "shelf_life": "evergreen", "observed_at": "",
            "review_by": "", "support_status": "", "claim_refs": [], "report_aliases": [], "boundaries": "", "rivals": [],
            "transfer_assumption": "", "tags": {"objective": [], "funnel_stage": [], "journey": [], "mechanism": [],
                                                "format": [], "codes": [], "character": [], "language": [], "market": []},
            "game_truth": [], "links": [], "history": []}


def _print_rows(rows):
    for e in rows:
        t = e.get("tags") or {}
        bits = [e.get("evidence_label", ""), e.get("review_status", ""), status_of(e)]
        if e.get("support_status"):
            bits.append(e["support_status"])
        print(f"{e['id']:<34} {e.get('title', '')[:70]:<70}  [{' · '.join(bits)}]"
              + (f"  {','.join(t.get('format', []))}" if t.get("format") else ""))


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="ss kb", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    f = sub.add_parser("find")
    f.add_argument("text", nargs="*")
    for k in ("bank", "objective", "format", "lang", "character", "stage", "evidence", "status", "mechanism", "journey"):
        f.add_argument("--" + k)
    f.add_argument("--due", action="store_true")
    f.add_argument("--all", action="store_true", help="include the raw report inventory")
    f.add_argument("--json", action="store_true")
    s = sub.add_parser("show")
    s.add_argument("id")
    sub.add_parser("due")
    sub.add_parser("stats")
    b = sub.add_parser("brief")
    b.add_argument("text")
    b.add_argument("--character")
    b.add_argument("--format")
    b.add_argument("--lang")
    sub.add_parser("render")
    x = sub.add_parser("export")
    x.add_argument("--out")
    m = sub.add_parser("migrate")
    m.add_argument("--audit", required=True)
    n = sub.add_parser("new")
    n.add_argument("bank", choices=sorted(BANKS))
    a = ap.parse_args(argv)

    if a.cmd == "migrate":
        print(json.dumps(migrate(Path(a.audit)), indent=1))
        return 0
    if a.cmd == "new":
        t = dict(TEMPLATE, bank=a.bank, id=BANKS[a.bank] + "-NEW")
        print(json.dumps(t, ensure_ascii=False))
        return 0
    entries = load()
    if a.cmd == "validate":
        errs, warns = validate(entries)
        print(f"{len(entries)} entries in {kb_dir()}: {'VALID' if not errs else 'INVALID'} - {len(errs)} errors, {len(warns)} warnings")
        for e in errs[:80]:
            print("  ERROR ", e)
        for w in warns[:40]:
            print("  WARN  ", w)
        return 1 if errs else 0
    if a.cmd == "find":
        rows = find(entries, q=" ".join(a.text) or None, bank=a.bank, objective=a.objective, fmt=a.format, lang=a.lang,
                    character=a.character, stage=a.stage, evidence=a.evidence, status=a.status, mechanism=a.mechanism,
                    journey=a.journey, due=a.due, include_inventory=a.all)
        if a.json:
            print(json.dumps([public(e) for e in rows], ensure_ascii=False, indent=1))
        else:
            _print_rows(rows)
            print(f"{len(rows)} entries")
        return 0
    if a.cmd == "show":
        e = next((x for x in entries if x.get("id") == a.id or a.id in x.get("report_aliases", [])), None)
        if not e:
            print(f"{a.id} not found")
            return 1
        print(json.dumps(resolve(entries, e), ensure_ascii=False, indent=1))
        return 0
    if a.cmd == "due":
        rows = [e for e in entries if not e.get("_error") and status_of(e) in ("due", "stale") and e.get("review_status") != "retired"]
        _print_rows(sorted(rows, key=lambda e: e.get("review_by", "")))
        print(f"{len(rows)} entries due or stale")
        return 0
    if a.cmd == "stats":
        c = Counter((e.get("bank"), e.get("review_status")) for e in entries if not e.get("_error"))
        for bank in BANKS:
            row = {s: c.get((bank, s), 0) for s in REVIEW}
            if sum(row.values()):
                print(f"{bank:<14} " + "  ".join(f"{k} {v}" for k, v in row.items() if v))
        return 0
    if a.cmd == "brief":
        g = brief(entries, a.text, a.character, a.format, a.lang)
        print(f"# Brief inputs for: {a.text}\n")
        for bank, rows in g.items():
            print(f"## {bank}")
            for e in rows:
                print(f"- **{e['id']}** {e.get('title')} [{e.get('evidence_label')}, {status_of(e)}]"
                      + (f"\n  {e['statement']}" if e.get("statement") else ""))
            print()
        return 0
    if a.cmd == "render":
        print(render(entries))
        return 0
    if a.cmd == "export":
        errs, _ = validate(entries)
        if errs:
            print(f"Refusing to export: {len(errs)} validation errors (run `ss kb validate`).")
            return 1
        out, n = export(entries, Path(a.out) if a.out else None)
        print(f"{n} entries -> {out}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
