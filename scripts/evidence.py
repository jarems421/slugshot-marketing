"""Slugshot evidence ledger: machine-checkable claims, evidence and support, shared by Claude and ChatGPT.

  new LEDGER_ID [--question Q]     start a ledger in data/local/research/evidence/<id>.json from the template
  validate LEDGER [--bundle DIR]   structural + evidence checks (references resolve, numbers match the rows, blanks
                                   not read as 0, quotes are exact, causal/lifecycle/audience wording vs. evidence,
                                   strength vs. independence and replication); --fix-summary rewrites the counts
  card LEDGER                      human-readable claim cards + decision memo skeleton (Markdown)
  export-evidenceguard LEDGER      the same audit in EvidenceGuard V0.1 format (research/upstream/evidenceguard)

Model (docs/research-evidence.md): claims carry an inference level O/D/P/I/C/R, a support status
(supported / partially_supported / unsupported / indeterminate, from EvidenceGuard), a verbal strength
(exploratory / suggestive / supported_descriptive / convergent / experimental) and six dimensions. There is
deliberately no numeric confidence score. The validator is deterministic; semantic review of wording and
interpretation is done by Claude/ChatGPT and recorded in each claim's `review` block.
"""
import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import research_common as rc

LEDGER_DIR = rc.DATA / "evidence"
VERSION = "slugshot-evidence-1.0"
LEVELS = {"O": "observation", "D": "derived statistic", "P": "descriptive pattern", "I": "interpretation",
          "C": "causal claim", "R": "recommendation"}
STATUSES = ["supported", "partially_supported", "unsupported", "indeterminate"]
STRENGTHS = ["exploratory", "suggestive", "supported_descriptive", "convergent", "experimental"]
DIMENSIONS = ["directness", "coverage", "temporal", "independence", "robustness", "counterevidence"]
DIM_VALUES = {"strong", "adequate", "weak", "none", "unknown"}
ROLES = {  # EvidenceGuard actual_role values + Slugshot-specific roles
    "observed_result", "estimate", "forecast", "target", "definition", "requirement", "expert_opinion",
    "contextual_background", "method_or_design", "other",
    "platform_metric", "third_party_estimate", "normalised_index", "qualitative_coding", "experiment_result",
    "literature_finding", "search_record"}
ACCESS = {"full", "partial", "metadata_only", "inaccessible"}
# Families = data-generating processes. Two pieces of evidence from one family are not independent confirmations.
FAMILIES = {"youtube", "tiktok", "instagram", "twitch", "roblox", "google_search", "wikimedia", "news",
            "literature", "owned_experiment", "qualitative_review", "community_reference", "other"}
FINDING_TYPES = {"unsupported_factual_claim", "partial_support", "citation_role_mismatch", "stale_or_insufficient_source",
                 "causal_overclaim", "numeric_inconsistency", "unclear_population_or_timeframe"}
# Causal vocabulary: K-Dense hypothesis-generation lint_causal_claims.py (MIT) + Slugshot additions.
CAUSAL_RE = re.compile(
    r"\b(?:causes?|caused|causal\s+(?:effect|impact)|effect\s+of|leads?\s+to|results?\s+in|increases?|reduces?|"
    r"prevents?|improves?|worsens?|drives?|mediates?|produces?|proves?|guarantees?|boosts?|because\s+of|"
    r"thanks\s+to|will\s+go\s+viral|makes?\s+\w+\s+(?:go\s+)?viral|is\s+why)\b", re.IGNORECASE)
LIFECYCLE_RE = re.compile(r"\b(?:emerging|accelerat\w*|rising|growing|grows|declin\w*|dying|saturat\w*|peak\w*|"
                          r"trending\s+(?:up|down)|losing\s+steam|taking\s+off|blowing\s+up)\b", re.IGNORECASE)
AUDIENCE_RE = re.compile(r"\b(?:audiences?|viewers?|fans?|players?|fandom|demographic\w*|mexican|spaniards?|"
                         r"argentin\w+|colombian\w*|chilean\w*|latin\s+american\w*|people\s+in)\b", re.IGNORECASE)
NEGATED_RE = re.compile(r"\b(?:unknown|cannot|can't|not\s+(?:yet\s+)?(?:established|known|shown|clear|determined)|"
                        r"insufficient|no\s+evidence|whether|undetermined|unclear)\b", re.IGNORECASE)
TREND_LEVEL_RE = re.compile(r"\b(?:trend|meme|format|sound|genre|hashtag|concept|joke|style)s?\b", re.IGNORECASE)
GENERAL_RE = re.compile(r"\b(?:typical\w*|ordinary|most|usually|in\s+general|generally|common(?:ly)?|always|everyone)\b",
                        re.IGNORECASE)
NUM_RE = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*([KkMmBb%])?(?![\w])")
RETRIEVAL_ONLY_SCOPE = {"region_param", "relevance_language_param", "language_edition", "search_geo", "source_filter"}


def ledger_path(arg):
    p = Path(arg)
    if p.suffix != ".json":
        p = LEDGER_DIR / f"{arg}.json"
    return p


def template(ledger_id, question=""):
    now = rc.iso(rc.now())
    return {
        "ledger_version": VERSION, "ledger_id": ledger_id, "created_at": now, "updated_at": now,
        "decision": {"decision_id": ledger_id, "question": question, "decision_threshold": "", "owner_decision": ""},
        "contract": {"primary_question": question, "construct": "", "not_evidence": [], "markets": [], "languages": [],
                     "platforms": [], "time_window": "", "hypotheses": [], "rival_hypotheses": [],
                     "negative_controls": [], "sampling_plan": "", "stop_rule": ""},
        "evidence": [], "claims": [], "decision_memo": {}, "summary": {}, "limitations": []}


def num(s):
    """'71.6M' -> 71600000.0; '24,500' -> 24500.0; '12%' -> 12.0; None if not a number."""
    if s is None:
        return None
    m = NUM_RE.fullmatch(str(s).strip())
    if not m:
        n, _ = rc.parse_count(s)
        return float(n) if n is not None else None
    v = float(m.group(1).replace(",", ""))
    return v * {"k": 1e3, "m": 1e6, "b": 1e9}.get((m.group(2) or "").lower(), 1)


def close(a, b, rel=0.05):
    return a is not None and b is not None and (a == b or abs(a - b) <= rel * max(abs(a), abs(b)))


class Report:
    def __init__(self):
        self.errors, self.warnings, self.review = [], [], []

    def e(self, where, msg):
        self.errors.append(f"{where}: {msg}")

    def w(self, where, msg):
        self.warnings.append(f"{where}: {msg}")

    def r(self, where, msg):
        self.review.append(f"{where}: {msg}")


def resolve_file(locator, bundle, ledger_file):
    """Find a cited file: inside the bundle first (exact, then the newest re-export of the same kind), then locally."""
    f = locator.get("file") or locator.get("source_path")
    if not f:
        return None
    kind = re.sub(r"_\d{8}T\d{4}Z(?=\.\w+$)", "", Path(f).name)
    bases = ([("bundle", Path(bundle))] if bundle else []) + [("local", b) for b in (ledger_file.parent, rc.ROOT, rc.SHARE, rc.DATA)]
    for where, base in bases:
        if (base / f).exists():
            return base / f
        if where == "bundle":
            exact = list(base.rglob(Path(f).name))
            if exact:
                return exact[0]
            if kind != Path(f).name:  # a re-export renames files (<kind>_<UTC time>.csv)
                stem, suffix = kind.rsplit(".", 1)
                cands = sorted(base.rglob(f"{stem}_*.{suffix}"))
                if cands:
                    locator["_resolved_to"] = cands[-1].name
                    return cands[-1]
    return None


def check_evidence(ev, R, bundle, ledger_file, now):
    eid = ev.get("evidence_id", "?")
    where = f"evidence {eid}"
    for k in ("evidence_id", "source_family", "actual_role", "provenance", "locator"):
        if not ev.get(k):
            R.e(where, f"missing '{k}'")
    if ev.get("source_family") and ev["source_family"] not in FAMILIES:
        R.e(where, f"source_family '{ev['source_family']}' unknown ({', '.join(sorted(FAMILIES))})")
    if ev.get("actual_role") and ev["actual_role"] not in ROLES:
        R.e(where, f"actual_role '{ev['actual_role']}' unknown")
    if ev.get("provenance") and ev["provenance"] not in rc.PROVENANCE:
        R.e(where, f"provenance '{ev['provenance']}' must be P1-P4")
    if ev.get("access_status") and ev["access_status"] not in ACCESS:
        R.e(where, f"access_status '{ev['access_status']}' unknown")
    if ev.get("provenance") == "P3" and ev.get("actual_role") == "platform_metric":
        R.e(where, "a third-party (P3) figure is labelled platform_metric; use third_party_estimate")
    if ev.get("expires_at") and rc.parse_time(ev["expires_at"]) <= now:
        R.w(where, f"expired {ev['expires_at']}: refresh the observation or drop its numbers (provider retention)")
    loc = ev.get("locator") or {}
    path = resolve_file(loc, bundle, ledger_file) if (loc.get("file") or loc.get("source_path")) else None
    if loc.pop("_resolved_to", None):
        R.r(where, f"cited file {loc.get('file')} not present; checked against the newer export {path.name}")
    if (loc.get("file") or loc.get("source_path")) and path is None:
        R.w(where, f"file '{loc.get('file') or loc.get('source_path')}' not found (pass --bundle DIR to check rows)")
    if loc.get("quote"):
        if path and path.suffix.lower() in (".txt", ".md", ".html", ".csv", ".json"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if loc["quote"] not in text:
                R.e(where, "quote is not an exact passage of the cited source text")
        elif not path:
            R.r(where, "quote could not be checked against a local copy of the source; verify the passage")
    if path and path.suffix.lower() == ".csv" and loc.get("where"):
        with path.open(newline="", encoding="utf-8-sig") as f:
            rows = [r for r in csv.DictReader(f) if all(str(r.get(k, "")) == str(v) for k, v in loc["where"].items())]
        if not rows:
            R.e(where, f"no row in {path.name} matches {loc['where']}")
        elif loc.get("column"):
            cells = [r.get(loc["column"]) for r in rows]
            if any(c is None for c in cells):
                R.e(where, f"column '{loc['column']}' not in {path.name}")
            elif "value" in loc:
                stated = str(loc["value"]).strip()
                if stated in ("0", "0.0") and all(c == "" for c in cells):
                    R.e(where, "the cited cell is blank (unknown) but the evidence states 0: missing is not zero")
                elif not any(c == stated or close(num(c), num(stated), 0.0005) for c in cells if c != ""):
                    R.e(where, f"stated value {stated!r} doesn't match {loc['column']} in the row ({cells[:3]})")
            ev["_cells"] = cells
    return path


def scope_key(ev):
    return json.dumps({k: v for k, v in sorted((ev.get("scope") or {}).items())}, sort_keys=True)


def check_claim(c, evid, R, levels_seen):
    cid = c.get("claim_id", "?")
    where = f"claim {cid}"
    for k in ("claim_id", "claim_text", "level", "support_status", "strength"):
        if not c.get(k):
            R.e(where, f"missing '{k}'")
    level, text = c.get("level"), c.get("claim_text", "")
    if level and level not in LEVELS:
        R.e(where, f"level '{level}' must be one of O/D/P/I/C/R")
    if c.get("support_status") and c["support_status"] not in STATUSES:
        R.e(where, f"support_status '{c['support_status']}' must be one of {STATUSES}")
    if c.get("strength") and c["strength"] not in STRENGTHS:
        R.e(where, f"strength '{c['strength']}' must be one of {STRENGTHS}")
    for d, v in (c.get("dimensions") or {}).items():
        if d not in DIMENSIONS or (v.get("rating") if isinstance(v, dict) else v) not in DIM_VALUES:
            R.e(where, f"dimension '{d}' needs rating in {sorted(DIM_VALUES)}")
    refs = c.get("evidence_refs", [])
    counter = c.get("counterevidence_refs", [])
    for ref in refs + counter:
        if ref not in evid and ref not in levels_seen:
            R.e(where, f"reference '{ref}' is neither an evidence_id nor an earlier claim_id")
    support = [evid[r] for r in refs if r in evid]
    status = c.get("support_status")
    if status in ("supported", "partially_supported") and not refs:
        R.e(where, f"{status} needs at least one evidence or claim reference")
    if status == "unsupported" and not refs and not counter:
        R.e(where, "unsupported needs the evidence that fails to justify it, contradicting evidence (counterevidence_refs) "
                   "or a search_record showing nothing was found; if we simply can't tell, use indeterminate")
    if status in ("unsupported", "indeterminate"):
        # An audit record of a claim we do NOT accept: its overclaiming wording is the point, not an error.
        if CAUSAL_RE.search(text) or LIFECYCLE_RE.search(text) or AUDIENCE_RE.search(text) or GENERAL_RE.search(text):
            R.r(where, f"{status} record of an overclaim; keep it out of findings and decision memos")
        return
    if status == "indeterminate" and not (c.get("missingness") or c.get("limitations")):
        R.w(where, "indeterminate: say what is missing (missingness) so the next test is clear")
    hedged = bool(NEGATED_RE.search(text))
    if hedged and (CAUSAL_RE.search(text) or LIFECYCLE_RE.search(text) or AUDIENCE_RE.search(text)):
        R.r(where, "negated/uncertain wording around causal, trend or audience terms: confirm the claim really says we don't know")
    # Causal wording.
    if level != "C" and CAUSAL_RE.search(text) and not hedged:
        R.e(where, f"causal wording ('{CAUSAL_RE.search(text).group(0)}') in a level-{level} claim: rephrase as an "
                   "association/observation, or make it a level-C claim with a causal basis")
    if level == "C":
        if not any(e.get("source_family") == "owned_experiment" or e.get("actual_role") == "experiment_result" for e in support) \
                and not c.get("causal_basis"):
            R.e(where, "level-C claim without an experiment or an explicit causal_basis (design + assumptions)")
        if c.get("strength") != "experimental" and status == "supported":
            R.w(where, "a supported causal claim normally has experimental strength")
    # Lifecycle / trend direction needs repeated comparable observations.
    if LIFECYCLE_RE.search(text) and level in ("P", "I", "D") and not hedged:
        groups = {}
        for e in support:
            if e.get("actual_role") in ("platform_metric", "normalised_index", "observed_result", "third_party_estimate"):
                g = groups.setdefault((e.get("item", ""), scope_key(e), e.get("metric", "")), set())
                g.add(e.get("observed_at", ""))
                if int(e.get("series_points") or 0) >= 2:  # one evidence item holding a dated series
                    g.update({f"series-{i}" for i in range(int(e["series_points"]))})
        if not any(len({t for t in ts if t}) >= 2 for ts in groups.values()):
            R.e(where, f"'{LIFECYCLE_RE.search(text).group(0)}' needs at least two comparable observations (same item, "
                       "metric and scope, different times); one snapshot is lifecycle 'unknown'")
        elif TREND_LEVEL_RE.search(text) and len({k[0] for k in groups}) == 1 and not any(
                e.get("item_type") in ("hashtag", "sound", "keyword", "search_term") for e in support):
            R.e(where, "one item's trajectory (a single video/clip/post) is not evidence about a whole "
                       f"{TREND_LEVEL_RE.search(text).group(0)}; use repeated comparable items or a trend-level measure")
    # Retrieval/edition parameters are not audience evidence.
    if AUDIENCE_RE.search(text) and level in ("P", "I", "D", "O") and support and not hedged:
        scopes = [set((e.get("scope") or {}).keys()) for e in support]
        if all(s and s <= RETRIEVAL_ONLY_SCOPE for s in scopes) or all(e.get("source_family") == "wikimedia" for e in support):
            R.e(where, f"'{AUDIENCE_RE.search(text).group(0)}': the evidence only shows retrieval/edition/filter scope "
                       "(region_param, language edition, tool filter), not audience geography, fandom size or demand")
    # Featured examples cannot speak for ordinary content.
    if GENERAL_RE.search(text) and support and all(e.get("sample_role") == "featured" for e in support):
        R.e(where, f"'{GENERAL_RE.search(text).group(0)}' generalises from featured examples only; add ordinary/failed "
                   "examples or narrow the claim")
    # Strength vs evidence.
    fams = {e.get("source_family") for e in support if e.get("source_family")}
    strength = c.get("strength")
    if strength == "convergent" and len(fams) < 2:
        R.e(where, f"convergent needs at least two independent source families (has {sorted(fams) or 'none'})")
    if strength == "experimental" and "owned_experiment" not in fams:
        R.e(where, "experimental strength needs owned_experiment evidence")
    if strength == "supported_descriptive":
        times = {e.get("observed_at") for e in support if e.get("observed_at")}
        if len(times) < 2:
            R.e(where, "supported_descriptive needs repeated observations (two or more observation times)")
        if not counter and (c.get("dimensions") or {}).get("counterevidence", {}).get("rating", "unknown") in ("unknown", "none"):
            R.w(where, "supported_descriptive without counterevidence having been sought")
    if len(support) >= 2 and len(fams) == 1 and strength in ("convergent",):
        R.e(where, "several items from one source family are one lineage, not independent confirmations")
    if len(support) >= 2 and len(fams) == 1:
        R.r(where, f"all {len(support)} supporting items come from one family ({next(iter(fams))}); "
                   "treat them as one lineage when judging independence")
    if any(e.get("provenance") == "P3" for e in support) and status == "supported" and level in ("O", "D") \
            and not any(e.get("provenance") in ("P1", "P2") for e in support):
        R.w(where, "supported only by third-party (P3) figures; label it as the tool's report, not a platform fact")
    if any(e.get("metric_definition") == "unknown" for e in support) and level in ("D", "P") and status == "supported":
        R.w(where, "uses a metric whose definition is unknown; keep the claim to what was displayed")
    # Numbers in the claim should be traceable.
    nums = [num(m.group(0).rstrip(",")) for m in NUM_RE.finditer(text)
            if not re.fullmatch(r"(19|20)\d\d", m.group(1).rstrip(","))]  # years aren't measurements
    nums = [n for n in nums if n is not None and n not in range(0, 32)]  # skip small counts like '7 days'
    known = [num(e.get("locator", {}).get("value")) for e in support] + \
            [num(x) for e in support for x in (e.get("_cells") or [])] + [num(v) for v in (c.get("values") or {}).values()]
    for n in nums:
        if not any(close(n, k, 0.06) for k in known if k is not None) and str(int(n) if n == int(n) else n) not in json.dumps(c.get("analysis_spec", "")):
            R.w(where, f"number {n:g} in the claim isn't traceable to a cited value or analysis_spec")
    if counter and status == "supported" and strength in ("supported_descriptive", "convergent"):
        R.r(where, "counterevidence is recorded but the claim is fully supported at high strength; check whether it "
                   "should be partially_supported or narrowed")
    if level == "R" and not c.get("next_discriminating_test") and not c.get("experiment"):
        R.w(where, "recommendation without the cheapest test / experiment that would check it")
    if level in ("P", "I") and not c.get("rival_hypotheses"):
        R.r(where, "no rival explanations recorded; name at least one for patterns and interpretations")
    R.r(where, "semantic review: does the wording stay within scope, period and population of the evidence?") \
        if not (c.get("review") or {}).get("ai_reviewed") else None


def validate(ledger, ledger_file, bundle=None):
    R = Report()
    now = rc.now()
    if ledger.get("ledger_version") != VERSION:
        R.e("ledger", f"ledger_version must be '{VERSION}'")
    for k in ("ledger_id", "decision", "evidence", "claims"):
        if k not in ledger:
            R.e("ledger", f"missing '{k}'")
    evid = {}
    for ev in ledger.get("evidence", []):
        if ev.get("evidence_id") in evid:
            R.e(f"evidence {ev.get('evidence_id')}", "duplicate evidence_id")
        evid[ev.get("evidence_id")] = ev
        check_evidence(ev, R, bundle, ledger_file, now)
    seen = set()
    for c in ledger.get("claims", []):
        if c.get("claim_id") in seen:
            R.e(f"claim {c.get('claim_id')}", "duplicate claim_id")
        check_claim(c, evid, R, seen)
        seen.add(c.get("claim_id"))
        for f in c.get("findings", []):
            if f.get("type") not in FINDING_TYPES:
                R.e(f"claim {c.get('claim_id')}", f"finding type '{f.get('type')}' unknown")
    for ev in evid.values():
        ev.pop("_cells", None)
    return R


def summary(ledger):
    cl = ledger.get("claims", [])
    count = lambda key, vals: {v: sum(1 for c in cl if c.get(key) == v) for v in vals}
    return {"total_claims": len(cl), "by_status": count("support_status", STATUSES),
            "by_strength": count("strength", STRENGTHS), "by_level": count("level", LEVELS),
            "evidence_items": len(ledger.get("evidence", [])),
            "source_families": sorted({e.get("source_family") for e in ledger.get("evidence", []) if e.get("source_family")}),
            "findings": sum(len(c.get("findings", [])) for c in cl)}


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"No ledger at {path}")
    except json.JSONDecodeError as e:
        sys.exit(f"{path} is not valid JSON: {e}")


def cmd_new(a):
    p = ledger_path(a.ledger_id)
    if p.exists():
        sys.exit(f"{p} already exists")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(template(a.ledger_id, a.question or ""), indent=1, ensure_ascii=False), encoding="utf-8")
    print(p)


def cmd_validate(a):
    p = ledger_path(a.ledger)
    ledger = load(p)
    R = validate(ledger, p, a.bundle)
    s = summary(ledger)
    if a.fix_summary:
        ledger["summary"] = s
        ledger["updated_at"] = rc.iso(rc.now())
        p.write_text(json.dumps(ledger, indent=1, ensure_ascii=False), encoding="utf-8")
    elif ledger.get("summary") and ledger["summary"] != s:
        R.w("summary", "stored summary doesn't reconcile with the claims; run with --fix-summary")
    out = {"ledger": str(p), "valid": not R.errors, "errors": R.errors, "warnings": R.warnings,
           "needs_ai_review": R.review, "summary": s, "checked_at": rc.iso(rc.now())}
    if a.json:
        print(json.dumps(out, indent=1, ensure_ascii=False))
    else:
        print(f"{p.name}: {'VALID' if not R.errors else 'INVALID'} - {len(R.errors)} errors, {len(R.warnings)} warnings, "
              f"{len(R.review)} items for AI review; {s['total_claims']} claims, {s['evidence_items']} evidence items")
        for label, items in (("ERROR", R.errors), ("WARN", R.warnings), ("REVIEW", R.review)):
            for i in items:
                print(f"  {label:6} {i}")
    sys.exit(1 if R.errors else 0)


def cmd_card(a):
    p = ledger_path(a.ledger)
    L = load(p)
    evid = {e["evidence_id"]: e for e in L.get("evidence", [])}
    out = [f"# Evidence ledger {L.get('ledger_id')}", "", f"Decision: {L.get('decision', {}).get('question', '')}", ""]
    for c in L.get("claims", []):
        fams = sorted({evid[r].get("source_family", "?") for r in c.get("evidence_refs", []) if r in evid})
        out += [f"## {c.get('claim_id')} [{c.get('level')}: {LEVELS.get(c.get('level'), '?')}]", "",
                f"**Claim:** {c.get('claim_text')}", "",
                f"Status: **{c.get('support_status')}** - Strength: **{c.get('strength')}** - Source families: {', '.join(fams) or 'none'}", ""]
        dims = c.get("dimensions") or {}
        if dims:
            out += ["| dimension | rating | note |", "|---|---|---|"] + [
                f"| {d} | {(dims[d] or {}).get('rating', '')} | {(dims[d] or {}).get('note', '')} |" for d in DIMENSIONS if d in dims] + [""]
        out += ["Evidence:"] + [f"- {r}: {evid[r].get('description', evid[r].get('locator', {}))}" for r in c.get("evidence_refs", []) if r in evid]
        if c.get("counterevidence_refs"):
            out += ["", "Against:"] + [f"- {r}: {evid.get(r, {}).get('description', r)}" for r in c["counterevidence_refs"]]
        for label, key in (("Rival explanations", "rival_hypotheses"), ("Missing", "missingness")):
            v = c.get(key)
            if v:
                out += ["", f"{label}:"] + [f"- {x}" for x in (v if isinstance(v, list) else [v])]
        if c.get("next_discriminating_test"):
            out += ["", f"Next test: {c['next_discriminating_test']}"]
        out.append("")
    m = L.get("decision_memo") or {}
    if m:
        out += ["# Decision memo", ""] + [f"**{k.replace('_', ' ').title()}:** {v if isinstance(v, str) else ', '.join(map(str, v))}"
                                          for k, v in m.items()]
    dest = p.with_suffix(".md")
    dest.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(dest)


def cmd_export_eg(a):
    """Map to EvidenceGuard V0.1 (research/upstream/evidenceguard/claim_evidence.schema.json)."""
    p = ledger_path(a.ledger)
    L = load(p)
    evid = {e["evidence_id"]: e for e in L.get("evidence", [])}
    ctype = {"O": "factual", "D": "numeric", "P": "comparative", "I": "other", "C": "causal", "R": "other"}
    eg_role = lambda r: r if r in {"observed_result", "estimate", "forecast", "target", "definition", "requirement",
                                   "expert_opinion", "contextual_background", "method_or_design"} else \
        {"platform_metric": "observed_result", "third_party_estimate": "estimate", "normalised_index": "observed_result",
         "experiment_result": "observed_result", "literature_finding": "observed_result"}.get(r, "other")
    claims = []
    for c in L.get("claims", []):
        claims.append({"claim_id": c["claim_id"], "claim_text": c["claim_text"], "location": f"ledger {L['ledger_id']}",
                       "claim_type": ctype.get(c.get("level"), "other"), "support_status": c.get("support_status"),
                       "evidence": [{"evidence_id": r, "source_label": evid[r].get("description") or evid[r].get("source_family"),
                                     "locator": json.dumps(evid[r].get("locator", {}), ensure_ascii=False),
                                     "actual_role": eg_role(evid[r].get("actual_role")),
                                     "access_status": evid[r].get("access_status", "full")} for r in c.get("evidence_refs", []) if r in evid],
                       "findings": [{k: f[k] for k in ("finding_id", "type", "severity", "explanation", "evidence_basis", "remediation") if k in f}
                                    for f in c.get("findings", [])]})
    by_type = {}
    for c in claims:
        for f in c["findings"]:
            by_type[f["type"]] = by_type.get(f["type"], 0) + 1
    out = {"audit_version": "0.1",
           "audit_scope": {"target_name": L["ledger_id"], "audit_date": datetime.now(timezone.utc).date().isoformat(),
                           "evidence_boundary": "evidence items listed in the Slugshot ledger"},
           "claims": claims,
           "summary": {"total_claims": len(claims), **{s: sum(1 for c in claims if c["support_status"] == s) for s in STATUSES},
                       "total_findings": sum(by_type.values()), "findings_by_type": by_type},
           "limitations": L.get("limitations", []), "escalations": []}
    dest = p.with_name(p.stem + ".evidenceguard.json")
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(dest)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("ledger_id")
    n.add_argument("--question")
    v = sub.add_parser("validate")
    v.add_argument("ledger", help="ledger id (data/local/research/evidence/<id>.json) or a path")
    v.add_argument("--bundle", help="folder (or extracted bundle) holding the cited CSV/text files")
    v.add_argument("--fix-summary", action="store_true")
    v.add_argument("--json", action="store_true")
    c = sub.add_parser("card")
    c.add_argument("ledger")
    e = sub.add_parser("export-evidenceguard")
    e.add_argument("ledger")
    a = ap.parse_args()
    {"new": cmd_new, "validate": cmd_validate, "card": cmd_card, "export-evidenceguard": cmd_export_eg}[a.cmd](a)


if __name__ == "__main__":
    main()
