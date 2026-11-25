"""Claim-level verification register and unresolved-evidence queue (Stage 4.6 audit).

Joins the outputs of scripts/research_audit.py (inventory, source register, DOI, URL and
figure checks) and applies the Slugshot evidence rules (docs/research-evidence.md):
  - "convergent" needs at least two independent source families;
  - a level-C claim needs a credible causal design, and transfer to Slugshot is separate;
  - causal wording in a non-causal claim is an overclaim.
Each claim's figures and sources are audited; whether the claim is true is a separate question.

  python scripts/research_audit_register.py [--out DIR]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "local" / "research" / "stage-4.6"
CAUSAL = re.compile(r"\b(causes?|caused|drives?|driving|boosts?|proves?|because of|leads? to|increases?|reduces?|"
                    r"raises?|lowers?|lifts?|degrades?|impairs?|erodes?|triggers?)\b", re.I)
CONSEQUENTIAL = re.compile(r"roblox|rfy|recommend|share link|retention|d1|d7|acquisition|conversion|attribution|"
                           r"engaged view|skip rate|stayed to watch|coppa|ftc|ofcom|under-1[36]|teen account|made for kids|"
                           r"age-check|policy|disclos|brand recall|vampire|wishlist|player", re.I)


def load(out):
    inv = json.loads((out / "inventory.json").read_text("utf-8"))
    reg = json.loads((out / "source_register.json").read_text("utf-8"))
    dois = {r["doi"]: r for r in csv.DictReader(open(out / "doi_verification.csv", encoding="utf-8"))}
    urls = {r["norm"]: r for r in csv.DictReader(open(out / "url_checks.csv", encoding="utf-8"))}
    checks = list(csv.DictReader(open(out / "claim_checks.csv", encoding="utf-8")))
    return inv, reg, dois, urls, checks


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    out = Path(a.out)
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from research_audit import norm_url

    inv, reg, dois, urls, checks = load(out)
    items = {i["id"]: i for i in inv["items"]}
    src_of = {m: s for s in reg["sources"] for m in s["member_ids"]}
    checks_by_id = defaultdict(list)
    for c in checks:
        for rid in c["report_ids"].split(";"):
            checks_by_id[rid].append(c)
    cited_by = defaultdict(set)
    for i in inv["items"]:
        for r in i["refs"]:
            cited_by[r].add(i["id"])

    # ---- evidence-level verification
    ev_rows = []
    for e in (i for i in inv["items"] if i["type"] == "evidence"):
        dv = [dois[d]["verdict"] for d in e["dois"] if d in dois]
        uo = [urls[norm_url(u)]["outcome"] for u in e["urls"] if norm_url(u) in urls]
        fc = [c["status"] for c in checks_by_id.get(e["id"], [])]
        if "figures_found" in fc:
            status = "figures_verified"
        elif "partially_found" in fc:
            status = "figures_partially_verified"
        elif "figures_not_found" in fc:
            status = "figures_not_found"
        elif any(v.startswith("match") for v in dv) or "ok" in uo:
            status = "source_exists_figures_unchecked"
        elif dv or uo:
            status = "source_problem"
        else:
            status = "no_locator"
        if any(v in ("does_not_resolve",) or v.startswith("mismatch") for v in dv):
            status += "+bibliographic_issue"
        ev_rows.append({"evidence_id": e["id"], "report": e["report"], "source_id": src_of.get(e["id"], {}).get("source_id", ""),
                        "family": src_of.get(e["id"], {}).get("family", ""), "status": status,
                        "doi_verdicts": ";".join(dv), "url_outcomes": ";".join(uo),
                        "figure_checks": ";".join(f"{c['check_id']}:{c['status']}" for c in checks_by_id.get(e["id"], [])),
                        "cited_by_n": len(cited_by[e["id"]]), "source_line": e["source_line"][:180]})
    ev_status = {r["evidence_id"]: r for r in ev_rows}

    # ---- claim-level register
    rows = []
    for c in (i for i in inv["items"] if i["type"] == "claim"):
        ev_refs = [r for r in c["refs"] if items.get(r, {}).get("type") == "evidence"]
        srcs = sorted({src_of[r]["source_id"] for r in ev_refs if r in src_of})
        fams = sorted({src_of[r]["family"] for r in ev_refs if r in src_of})
        st = [ev_status[r]["status"] for r in ev_refs if r in ev_status]
        own = checks_by_id.get(c["id"], [])
        strength = (c.get("strength") or "").split(" ")[0]
        level = (c.get("level") or "")[:1]
        flags = []
        if strength == "convergent" and len(srcs) < 2:
            flags.append("convergent_with_<2_sources")
        elif strength == "convergent" and len(fams) < 2:
            flags.append("convergent_single_family_type(review)")
        if strength == "experimental":
            flags.append("experimental_reserved_for_owned_tests")
        if level == "C" and re.search(r"adjacent", c["text"], re.I):
            flags.append("causal_from_adjacent_domain(transfer_hypothesis)")
        if level not in ("C", "R") and CAUSAL.search(c.get("claim_text", "")) and c.get("support_status", "").split(" ")[0] != "unsupported":
            flags.append("causal_wording_in_non_causal_claim")
        if any("bibliographic_issue" in s for s in st):
            flags.append("cited_bibliographic_issue")
        if any(s.startswith(("figures_not_found", "source_problem")) for s in st) or any(x["status"] in ("figures_not_found", "source_unreachable") for x in own):
            flags.append("cited_figure_or_source_not_found")
        if not ev_refs:
            flags.append("no_evidence_refs_parsed")
        if any(s.startswith("figures_verified") for s in st) or any(x["status"] == "figures_found" for x in own):
            audit = "key_figures_verified"
        elif any(s.startswith("figures_partially") for s in st) or any(x["status"] == "partially_found" for x in own):
            audit = "partially_verified"
        elif st and all(s.startswith(("source_exists", "figures")) for s in st):
            audit = "bibliographic_only"
        elif st:
            audit = "mixed_or_problem"
        else:
            audit = "unverified"
        if "cited_figure_or_source_not_found" in flags:
            audit = "problem_found" if audit != "key_figures_verified" else "verified_with_problem"
        consequential = bool(CONSEQUENTIAL.search(c.get("claim_text", ""))) or len(cited_by[c["id"]]) >= 3
        rows.append({"claim_id": c["id"], "report": c["report"], "level": c.get("level", ""), "self_support": c.get("support_status", ""),
                     "self_strength": c.get("strength", ""), "audit_status": audit, "flags": ";".join(flags),
                     "n_evidence": len(ev_refs), "n_distinct_sources": len(srcs), "families": ";".join(fams),
                     "evidence_refs": ";".join(ev_refs), "used_by_n": len(cited_by[c["id"]]),
                     "used_by": ";".join(sorted(cited_by[c["id"]]))[:300], "consequential": consequential,
                     "claim_text": c.get("claim_text", "")[:600], "source_line": c["first_line"]})

    # ---- unresolved queue (prioritised; no composite score: ordered by explicit tiers)
    queue = []
    for r in rows:
        tier = None
        if r["audit_status"] in ("problem_found", "verified_with_problem"):
            tier = 1
        elif r["consequential"] and r["audit_status"] in ("bibliographic_only", "unverified", "mixed_or_problem"):
            tier = 2
        elif "convergent_with_<2_sources" in r["flags"] or "causal_wording_in_non_causal_claim" in r["flags"]:
            tier = 3
        elif r["audit_status"] in ("bibliographic_only", "unverified"):
            tier = 4
        if tier:
            queue.append({"tier": tier, "kind": "claim", "id": r["claim_id"], "report": r["report"],
                          "why": f"{r['audit_status']}; {r['flags']}".strip("; "), "used_by_n": r["used_by_n"],
                          "text": r["claim_text"][:240]})
    for e in ev_rows:
        if "bibliographic_issue" in e["status"] or e["status"].startswith(("figures_not_found", "source_problem")):
            queue.append({"tier": 1, "kind": "evidence", "id": e["evidence_id"], "report": e["report"],
                          "why": e["status"] + (f"; DOI {e['doi_verdicts']}" if e["doi_verdicts"] else ""),
                          "used_by_n": e["cited_by_n"], "text": e["source_line"]})
    queue.sort(key=lambda q: (q["tier"], -q["used_by_n"], q["id"]))

    for name, data in (("evidence_verification.csv", ev_rows), ("claim_verification_register.csv", rows), ("unresolved_queue.csv", queue)):
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)
    (out / "claim_verification_register.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), "utf-8")
    print("evidence:", dict(Counter(r["status"] for r in ev_rows)))
    print("claims:", dict(Counter(r["audit_status"] for r in rows)))
    fl = Counter(f for r in rows for f in r["flags"].split(";") if f)
    print("claim flags:", dict(fl))
    print("queue tiers:", dict(Counter(q["tier"] for q in queue)), "total", len(queue))


if __name__ == "__main__":
    main()
