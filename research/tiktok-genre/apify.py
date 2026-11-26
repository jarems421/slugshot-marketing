import json, sys
sys.path.insert(0, r"C:\Users\runni\slugshot marketing\scripts")
import research_common as rc
API = "https://api.apify.com/v2/"
def req(path, params=None, payload=None):
    tok = rc.env_value("APIFY_TOKEN")
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    body, _ = rc.http(API + path, params=params, headers=h, data=json.dumps(payload).encode() if payload is not None else None)
    return json.loads(body)
if __name__ == "__main__":
    b = req("acts/clockworks~tiktok-scraper/builds/default")["data"]
    s = b.get("inputSchema") or b.get("actorDefinition", {}).get("input")
    s = json.loads(s) if isinstance(s, str) else s
    for k, v in s["properties"].items():
        print(k, "|", v.get("type"), "|", str(v.get("default", v.get("prefill", "")))[:60], "|", (v.get("description") or "")[:160].replace("\n", " "))
