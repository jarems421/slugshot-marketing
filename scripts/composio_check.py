"""Composio (docs.composio.dev) checks for the marketing toolkit: read-only by design.

  status            key present (never shown), API reachable, connected accounts and auth configs
  test              run one free, no-auth, read-only tool end to end (Hacker News item 1; 1 of the
                    Hobby plan's monthly tool calls)
  audit             refresh the toolkit audit for the integrations we care about (GET only) ->
                    data/local/composio/toolkit_audit.csv

REST v3 with the project key (COMPOSIO_API_KEY in the git-ignored .env, sent as x-api-key). Standard
library only: no SDK, CLI or plugin is installed (docs/composio.md explains why). This script never
executes tools that write, post or publish, and never creates connections: connecting an account is
an owner OAuth step. Hobby is hard-capped with no card on file, so it cannot bill.
"""
import argparse
import csv
import json
import sys

import research_common as rc

API = "https://backend.composio.dev/api/v3"
AUDIT = ["tiktok", "instagram", "youtube", "googledrive", "googlesheets", "google_analytics", "google_search_console",
         "facebook", "reddit", "twitch", "vidiq_mcp", "youtube_transcript", "metricool_mcp", "tiktok_ads", "roblox"]


def key():
    k = rc.env_value("COMPOSIO_API_KEY")
    if not k:
        rc.die("COMPOSIO_API_KEY isn't set in .env (see .env.example)")
    return k


def call(path, params=None, body=None):
    headers = {"x-api-key": key(), "accept": "application/json"}
    if body is not None:
        headers["content-type"] = "application/json"
        body = json.dumps(body).encode()
    raw, _ = rc.http(API + path, params=params, headers=headers, data=body, timeout=60)
    return json.loads(raw.decode("utf-8"))


def pages(path, params):
    items, cursor = [], None
    while True:
        b = call(path, {**params, **({"cursor": cursor} if cursor else {})})
        items += b.get("items", [])
        cursor = b.get("next_cursor")
        if not cursor or not b.get("items"):
            return items


def cmd_status(a):
    print("COMPOSIO_API_KEY: present (not shown)" if key() else "")
    call("/toolkits", {"limit": 1})
    print("API: reachable, key accepted")
    accounts = pages("/connected_accounts", {"limit": 100})
    print(f"Connected accounts: {len(accounts)}")
    for c in accounts:
        print(f"  {(c.get('toolkit') or {}).get('slug', '?'):20} status={c.get('status')} created={c.get('created_at', '')[:10]}")
    configs = pages("/auth_configs", {"limit": 100})
    print(f"Auth configs: {len(configs)}" + "".join(f"\n  {(c.get('toolkit') or {}).get('slug', '?')}" for c in configs))


def cmd_test(a):
    r = call("/tools/execute/HACKERNEWS_GET_ITEM_WITH_ID", body={"arguments": {"item_id": "1", "max_depth": 0},
                                                                   "user_id": "slugshot-marketing"})
    d = (r.get("data") or {}).get("response_data") or {}
    ok = r.get("successful") and d.get("id") == 1
    print(f"{'PASS' if ok else 'FAIL'} read-only tool execution (HACKERNEWS_GET_ITEM_WITH_ID 1): "
          f"author={d.get('author')} created={d.get('created_at', '')[:10]}" + ("" if ok else f" error={r.get('error')}"))
    sys.exit(0 if ok else 1)


def cmd_audit(a):
    toolkits = {t["slug"]: t for t in pages("/toolkits", {"limit": 500})}
    rows = []
    for slug in AUDIT:
        t = toolkits.get(slug)
        if not t:
            rows.append({"toolkit": slug, "in_catalog": "no"})
            continue
        tools = pages("/tools", {"toolkit_slug": slug, "limit": 200})
        ro = [x for x in tools if "readOnlyHint" in (x.get("tags") or [])]
        rows.append({"toolkit": slug, "in_catalog": "yes", "name": t["name"], "auth_schemes": "|".join(t["auth_schemes"]),
                     "composio_managed_auth": "|".join(t["composio_managed_auth_schemes"]) or "none (own credentials needed)",
                     "tools": len(tools), "read_only_tools": len(ro),
                     "read_only_tool_slugs": "|".join(x["slug"] for x in ro), "observed_at_utc": rc.iso(rc.now())})
    dest = rc.ROOT / "data" / "local" / "composio" / "toolkit_audit.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    fields = ["toolkit", "in_catalog", "name", "auth_schemes", "composio_managed_auth", "tools", "read_only_tools",
              "read_only_tool_slugs", "observed_at_utc"]
    with dest.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['toolkit']:22} managed={r.get('composio_managed_auth', '-'):24} tools={r.get('tools', '-')} "
              f"read-only={r.get('read_only_tools', '-')}")
    print(f"{len(toolkits)} toolkits in the catalog -> {dest}")


def main():
    sys.stdout.reconfigure(errors="replace")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("status", "test", "audit"):
        sub.add_parser(name)
    a = p.parse_args()
    try:
        {"status": cmd_status, "test": cmd_test, "audit": cmd_audit}[a.cmd](a)
    except rc.HttpError as e:
        rc.die(f"Composio API error {e}")


if __name__ == "__main__":
    main()
