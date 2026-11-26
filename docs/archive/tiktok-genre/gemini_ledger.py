"""Repost scan, IMW-GEMINI-VERIFY ledger, and a blind recode packet for Gemini's interpretive codes."""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(project_root / "scripts"), str(project_root / "research" / "tiktok-genre")]
import research_common as rc

import csv, json, random, re, difflib, shutil
from pathlib import Path
ROOT = rc.ROOT
EXP = ROOT / "exports/share/research/tiktok-in-my-world-2026-11-26"
G = ROOT / "data/local/research/gemini"
pool = {r["id"]: r for r in csv.DictReader(open(ROOT / "data/local/research/creative/tiktok-genre/pool.csv", encoding="utf-8"))}
rows = {r["id"]: r for r in csv.DictReader(open(EXP / "ALL-POSTS.csv", encoding="utf-8-sig"))}
T = lambda i: " ".join(t for _, t in json.loads(pool[i]["transcript"])).lower()
tiered = [r for r in rows.values() if r["tier"]]

# 1. copies: a tiered post whose opening 800 chars match an EARLIER post anywhere in the 631 at >= 0.90
texts = {i: T(i)[:800] for i in pool if pool[i]["transcript"] != "[]"}
copies = {"TOP": [], "MID": [], "FLOP": []}
for r in tiered:
    i, t0 = r["id"], texts.get(r["id"], "")
    for j, tj in texts.items():
        if j == i or rows[j]["posted_at_utc"] >= r["posted_at_utc"] or not tj:
            continue
        sm = difflib.SequenceMatcher(None, t0, tj)
        if sm.real_quick_ratio() > 0.9 and sm.quick_ratio() > 0.9 and sm.ratio() >= 0.90:
            copies[r["tier"]].append((r["creator"], int(r["views"]), rows[j]["creator"], int(rows[j]["views"])))
            break
# compilation halves (a post copied from inside a longer earlier compilation) are caught by a substring test
for r in tiered:
    i = r["id"]
    if any(c[0] == r["creator"] and c[1] == int(r["views"]) for c in copies[r["tier"]]):
        continue
    head = texts.get(i, "")[:300]
    for j in texts:
        if j != i and rows[j]["posted_at_utc"] < r["posted_at_utc"] and len(head) > 200 and head[40:240] in T(j):
            copies[r["tier"]].append((r["creator"], int(r["views"]), rows[j]["creator"], int(rows[j]["views"])))
            break
print({t: len(v) for t, v in copies.items()})
for t, v in copies.items():
    for c in v: print(f"  {t}: @{c[0]} {c[1]:,} copies earlier @{c[2]} {c[3]:,}")

# 2. ledger
src = "exports/share/research/tiktok-in-my-world-2026-11-26/ALL-POSTS.csv"
ev = [
 {"evidence_id": "E1", "description": "Our 631-post TikTok bank (Apify clockworks, 26 Nov 2026), tiers TOP/MID/FLOP-50; public counts at one snapshot", "source_family": "tiktok", "actual_role": "third_party_estimate", "provenance": "P3", "access_status": "full", "metric_definition": "approximate", "sample_role": "retrieved", "observed_at": "2026-11-26", "locator": {"file": src, "note": "recomputed by docs/archive/tiktok-genre/verify_gemini.py"}},
 {"evidence_id": "E2", "description": "TikTok ASR subtitles / local Whisper transcripts for the same posts", "source_family": "tiktok", "actual_role": "observed_result", "provenance": "P3", "access_status": "full", "metric_definition": "approximate", "sample_role": "retrieved", "observed_at": "2026-11-26", "locator": {"file": "data/local/research/creative/tiktok-genre/pool.csv", "column": "transcript"}},
 {"evidence_id": "E3", "description": "Gemini Deep Research report and coded CSV (owner-supplied, 26 Nov 2026); coding done with tier labels visible", "source_family": "qualitative_review", "actual_role": "qualitative_coding", "provenance": "P4", "access_status": "full", "metric_definition": "unknown", "sample_role": "unknown", "observed_at": "2026-11-26", "locator": {"note": "Gemini-In-My-World-Empirical-Creative-Research.pdf + Gemini-IMW-Coded-Dataset.csv, supplied in chat; save to data/local/research/gemini/"}},
]
def claim(cid, text, level, status, strength, refs, values=None, rivals=None, test="", findings=None, note=""):
    return {"claim_id": cid, "decision_id": "IMW-GEMINI-VERIFY", "claim_text": text, "level": level, "support_status": status, "strength": strength,
            "evidence_refs": refs, "values": values or {}, "rival_hypotheses": rivals or [], "next_discriminating_test": test, "findings": findings or [],
            "scope": "TikTok In My World / In This Town Roblox posts, 150 tiered (>=5 d, Roblox-tagged, English speech), one snapshot 26 Nov 2026",
            "review": {"ai_reviewed": True, "reviewer": "claude", "notes": note or "Re-read against recomputed values from E1/E2."}}
cl = [
 claim("C1", "Gemini's median engagement rates by tier match our recomputation to within 0.01 points: likes 10.18/4.98/3.75%, shares 0.70/0.28/0.14%, saves 0.82/0.65/0.51%, comments 0.05/0.08/0.13% (TOP/MID/FLOP).", "D", "supported", "suggestive", ["E1", "E3"],
       {"like": [10.18, 4.98, 3.75], "share": [0.70, 0.28, 0.14], "save": [0.82, 0.65, 0.51], "comment": [0.05, 0.08, 0.13]}, ["Rates are partly mechanical: tiers are defined by views and counts are rounded at high values"]),
 claim("C2", "Median non-zero followers are 34,300/13,100/2,931 and median views per follower 40.8x/4.5x/1.0x (TOP/MID/FLOP); Spearman followers vs views is 0.59 (n=147; Gemini 0.603).", "D", "supported", "suggestive", ["E1", "E3"],
       {"followers": [34300, 13100, 2931], "spearman": 0.592}, ["Account size explains much of the tier split; creative effects must be judged within creator or per follower"]),
 claim("C3", "TOP skews younger than MID and FLOP: 30% of TOP vs 8% of MID and 14% of FLOP were 5-7 days old, and TOP leans on search while FLOP leans on creator back catalogues.", "D", "supported", "suggestive", ["E1", "E3"],
       {"age_5_7d_pct": [30, 8, 14]}, ["Sampling route, not script quality, separates some tiers"], "Re-snapshot the same posts at +7 and +21 days"),
 claim("C4", "Narration pace does not separate tiers: median words per minute of runtime is 218/221/231 and median duration 109/120/114 s.", "D", "supported", "suggestive", ["E2"], {"wpm": [218, 221, 231], "duration_s": [109, 120, 114]}),
 claim("C5", "The rule opening is near universal: 45/46/46 of 50 speak an 'in this/my town/world' line in the first 10 s, so it is an entry requirement, not a differentiator.", "D", "supported", "suggestive", ["E2"], {"rule_in_10s": [45, 46, 46]}),
 claim("C6", "Gemini's OTHER-A counts and cited view figures match our data: 48 under-5-day posts have >=500k views and 37 have >=1M; cited examples (A-156 2.0M, A-266 26.8M, A-150 8.2M, A-152 6.2M, A-267 6.7M, A-271 4.1M) are correct.", "O", "supported", "suggestive", ["E1"], {"ge500k": 48, "ge1m": 37}),
 claim("C7", f"Copies of earlier posts sit mostly in the lower tiers: TOP {len(copies['TOP'])}, MID {len(copies['MID'])}, FLOP {len(copies['FLOP'])} of 50 open with text >=90% identical to an earlier post in the 631 (or to part of an earlier compilation).", "D", "supported", "suggestive", ["E2"],
       {"copies": {t: len(v) for t, v in copies.items()}}, ["Only copies of posts inside our 631 are detectable; copies of outside posts are missed", "Copying accounts may also be small or new"], "Compare each copy's views with its original within the same follower band"),
 claim("C8", "FLOP-49 is the volcano story taken from the second half of @in.this.world.stories' compilation TOP-32 (94% text match), confirming Gemini's matched-script pair.", "O", "supported", "suggestive", ["E2"], {"similarity": 0.94}),
 claim("C9", "Gemini's description of FLOP-45 as a late copycat of TOP-01 is wrong on timing: FLOP-45 (posted 18 Nov) predates TOP-01 (20 Nov); it copies an 'everybody goes out partying except me' template whose original is not in our data.", "O", "partially_supported", "suggestive", ["E1", "E2", "E3"],
       findings=[{"finding_id": "F9", "type": "unclear_population_or_timeframe", "severity": "warning", "explanation": "Order of posting contradicts 'late copycat'", "remediation": "Treat FLOP-45 as a template copy, origin unknown"}]),
 claim("C10", "Spoken 'subscribe' appears in 0/1/6 tier transcripts (Gemini: 0/0/6; MID-18 also says it), so the YouTube-carryover pattern is concentrated in FLOP but not exclusive to it.", "D", "partially_supported", "suggestive", ["E2", "E3"], {"subscribe": [0, 1, 6]},
       findings=[{"finding_id": "F10", "type": "numeric_inconsistency", "severity": "info", "explanation": "MID-18 (68.2k) says 'Subscribe if you enjoy my content'", "remediation": "Use 0/1/6"}]),
 claim("C11", "Captions that state the premise are more common in TOP: 43/34/32 of 50 by our word-count rule vs Gemini's 42/30/27; the direction holds but the TOP-FLOP gap is about 22 points, not 30.", "D", "partially_supported", "suggestive", ["E1", "E3"], {"ours": [43, 34, 32], "gemini": [42, 30, 27]},
       ["Large accounts write better captions and get more reach"], "Owned 2x2 test: explicit vs vague caption on matched scripts"),
 claim("C12", "Gemini's interpretive differentiators (novelty, humour mechanism, abstract fantasy and power-rank premises, flat endings, AI-style prose) cannot be confirmed from countable proxies and were coded with tier labels visible; e.g. power-rank vocabulary appears in only 2/1/3 transcripts vs Gemini's 2/6/11 power-rank codes.", "P", "indeterminate", "exploratory", ["E2", "E3"],
       {"power_rank_vocab": [2, 1, 3], "gemini_power_rank": [2, 6, 11]}, ["Hindsight halo: a coder who knows a post flopped rates it less novel and less funny"], "Blind recode of the 150 transcripts (shuffled, no tiers or metrics) by a fresh Gemini chat; owner spot-checks 20"),
 claim("C13", "Gemini's six formulas and interaction cells (for example 3/4, 2/3 and 5/6 posts quoted as 75%, 66.7% and 83% TOP) are post-hoc groupings from dozens of tests on 150 posts and should be used as script hypotheses, not validated rules.", "I", "indeterminate", "exploratory", ["E3"],
       ["Some cells may be real patterns; sample is too small to tell"], "Pre-register 2-3 formulas, post matched scripts, compare 24 h/48 h/7 d within one account"),
]
ledger = json.load(open(ROOT / "data/local/research/evidence/IMW-GEMINI-VERIFY.json", encoding="utf-8"))
ledger["contract"].update({
    "construct": "Accuracy of a third-party AI report against the data it was given",
    "not_evidence": ["Gemini's percentages or p-values on its own codes", "View counts as proof of script quality"],
    "platforms": ["tiktok"], "languages": ["en"], "time_window": "posts up to 26 Nov 2026, one snapshot",
    "hypotheses": ["Gemini's objective numbers are correct", "Gemini's interpretive differentiators survive blind recoding"],
    "rival_hypotheses": ["Account size, post age and search route explain tier gaps", "Hindsight halo inflates interpretive codes"],
    "negative_controls": ["Pace and rule opening should not separate tiers"],
    "sampling_plan": "All 150 tiered posts plus the 481 others for copy detection", "stop_rule": "Objective checks complete; interpretive claims wait for blind recode"})
ledger["evidence"], ledger["claims"] = ev, cl
ledger["decision_memo"] = {
    "recommend": "Use Gemini's report as a strong hypothesis bank. Its numbers are accurate; its creative judgements are unblinded and should guide scripts as hypotheses tested on our own posts.",
    "supported_findings": ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"],
    "uncertain_but_useful": ["C11", "C12", "C13"],
    "counterevidence": ["C9", "C10"],
    "unknown": ["Whether novelty, humour or ending type separate tiers once the coder cannot see outcomes", "Retention, visuals and sound (not in transcripts)"],
    "creative_hypothesis": "If an original rule with a dry comic edge and a premise-stating caption drives shares, then a Slugshot In My World short built that way should beat a straight-earnest version on share rate within our own account.",
    "cheapest_test": "Blind recode (free, a fresh Gemini chat with the packet), then two matched Slugshot scripts posted a few days apart."}
ledger["limitations"] = ["One snapshot; tiers partly reflect account size and age", "Transcripts are ASR and carry no visuals or sound", "Copy detection only sees posts inside our 631", "Gemini CSV not yet saved locally for row-level agreement"]
json.dump(ledger, open(ROOT / "data/local/research/evidence/IMW-GEMINI-VERIFY.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)

# 3. blind recode packet
random.seed(26)
items = tiered[:]; random.shuffle(items)
key, packet = {}, []
for n, r in enumerate(items, 1):
    bid = f"B-{n:03d}"; key[bid] = {"id": r["id"], "tier": r["tier"]}
    packet.append(f"## {bid} · {r['duration_s']} s\n\nCaption: {re.sub(r'@\\S+', '@creator', r['caption']).strip()}\n\nTranscript:\n" + "\n".join(f"[{s // 60:02d}:{s % 60:02d}] {t}" for s, t in json.loads(pool[r['id']]['transcript'])) + "\n")
D = G / "blind-recode"; D.mkdir(parents=True, exist_ok=True)
json.dump(key, open(D / "KEY-do-not-share.json", "w"), indent=0)
instr = """# Blind recode: In My World transcripts (150)

You are coding 150 short TikTok story transcripts. You do NOT know how any of them performed. Do not guess performance, and do not look anything up. Code only from the caption and transcript. Each item: ID, length in seconds, caption, transcript (automatic speech recognition, may contain errors).

For every item output one CSV row with these columns, using exactly these values:

- `blind_id`
- `novelty` 1-5: how fresh the world rule is compared with common genre tropes (1 = stock superpower/rank premise, 5 = a rule you have not seen before)
- `humor_mech`: none_serious | absurd_slapstick_world_gags | dry_deadpan_understatement | meme_brainrot_cultural_ref | edgy_taboo_innuendo
- `grounding`: high_everyday_relatability | high_primal_fear | high_absurd_comedy | generic_fantasy_abstract
- `power_rank`: 1 if the premise is about power levels, ranks or levelling up, else 0
- `escalation`: escalating_threat_crisis | countdown_ticking_clock | mystery_clue_chain | comedic_rule_of_three | flat_linear_or_rushed
- `ending`: resolved_ironic_button | cliffhanger_unresolved | resolved_sequel_stinger | 4th_wall_infects_viewer | flat_abrupt_incomplete
- `voice_style`: punchy_staccato_conversational | literary_atmospheric_fable | generic_ai_expository | meme_slang_chaotic
- `twist`: recontextualization_revelation | chilling_horror_cliffhanger | ironic_comedic_reversal | hidden_power_underdog_only | none_or_cut_before_twist
- `evidence`: a short exact quote that justified the humour and ending codes

Return a single CSV with a header row and 150 rows, nothing else.
"""
(D / "INSTRUCTIONS.md").write_text(instr, encoding="utf-8")
(D / "BLIND-PACKET.md").write_text("# Blind packet: 150 transcripts\n\n" + "\n".join(packet), encoding="utf-8")
dl = Path.home() / "Downloads" / "tiktok-in-my-world-2026-11-26" / "gemini-verification"; dl.mkdir(parents=True, exist_ok=True)
for f in ("INSTRUCTIONS.md", "BLIND-PACKET.md"): shutil.copy(D / f, dl / f)
print("packet", len(packet), "->", dl)
