"""Run clockworks/tiktok-scraper with a hard charge cap; save receipt + items under data/local."""
import json, sys, time
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import apify, research_common as rc
ACTOR = "clockworks~tiktok-scraper"
BASIS = ("Owner-asserted TikTok permission (owner message 2026-11-26) covering Apify Actors on this key for "
         "public posts: metadata, captions, transcripts, permitted downloads. Original email not seen by Claude.")
def run(label, payload, cap):
    dest = rc.DATA / "creative" / "tiktok-genre" / rc.new_run_id("apify-" + label)
    dest.mkdir(parents=True)
    r = apify.req(f"acts/{ACTOR}/runs", params={"maxTotalChargeUsd": cap, "timeout": 900, "waitForFinish": 30}, payload=payload)["data"]
    print("run", r["id"], "->", dest, flush=True)
    while r["status"] not in {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}:
        time.sleep(5)
        r = apify.req(f"actor-runs/{r['id']}", params={"waitForFinish": 30})["data"]
    items, off = [], 0
    while True:
        page = apify.req(f"datasets/{r['defaultDatasetId']}/items", params={"offset": off, "limit": 500})
        items += page; off += len(page)
        if len(page) < 500: break
    receipt = {k: r.get(k) for k in ("id", "status", "startedAt", "finishedAt", "defaultDatasetId", "defaultKeyValueStoreId", "chargedEventCounts", "usageTotalUsd")}
    receipt.update(actor=ACTOR.replace("~", "/"), input=payload, charge_cap_usd=cap, permission_basis=BASIS, items=len(items))
    (dest / "run.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    (dest / "items.json").write_text(json.dumps(items, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(r["status"], len(items), "items | $", r.get("usageTotalUsd"), r.get("chargedEventCounts"))
    return dest, items
if __name__ == "__main__":
    label, cap, payload = sys.argv[1], float(sys.argv[2]), json.loads(open(sys.argv[3], encoding="utf-8").read())
    run(label, payload, cap)
