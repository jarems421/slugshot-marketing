"""Roblox public experience stats for a small watchlist (EXPERIMENTAL: legacy, unstable source).

  games             snapshot every experience in config/research/roblox_experiences.csv (max 20):
                    current players, visits, favourites, up/down votes, created/updated times
  universe PLACE_ID print the universe ID for a place ID (the number in a roblox.com/games/<id> URL)
  report            export the snapshots -> exports/share/research/

Source: games.roblox.com/v1/games and /v1/games/votes, Roblox "legacy" web APIs, unauthenticated.
Roblox says legacy APIs "can incorporate breaking changes without notice" and aren't recommended for
production (create.roblox.com/docs/cloud/legacy). So: small watchlist, at most one run per
`min_minutes_between_runs`, every row labelled source_stability=legacy_unstable, stop if it breaks.
`playing` is Roblox's current-player figure; for multi-place experiences it may cover only some places
(older DevForum report), so read it as an approximate concurrent count, not unique players.
This never touches the Slugshot game repository, Studio or Open Cloud keys.
"""
import argparse
import csv
import json
import sys
from datetime import timedelta
from pathlib import Path

import research_common as rc

GAMES = "https://games.roblox.com/v1/games"
VOTES = "https://games.roblox.com/v1/games/votes"
PLACE = "https://apis.roblox.com/universes/v1/places/{}/universe"
FIELDS = ["universe_id", "label", "root_place_id", "name", "creator_name", "creator_type", "playing", "visits",
          "favorited_count", "up_votes", "down_votes", "max_players", "genre", "created_utc", "updated_utc",
          "observed_at_utc", "source_stability", "run_id"]
COLUMNS = [
    ("universe_id", "Roblox", "experience (universe) ID"),
    ("label", "config", "our label from the watchlist"),
    ("root_place_id", "Roblox", "start place ID (roblox.com/games/<id>)"),
    ("name", "Roblox", "experience name at observation"),
    ("creator_name", "Roblox", "owner user or group"),
    ("creator_type", "Roblox", "User or Group"),
    ("playing", "Roblox", "current players at observation (approximate; may not cover every place)"),
    ("visits", "Roblox", "lifetime visits at observation"),
    ("favorited_count", "Roblox", "lifetime favourites at observation"),
    ("up_votes", "Roblox", "thumbs up at observation"),
    ("down_votes", "Roblox", "thumbs down at observation"),
    ("max_players", "Roblox", "server size"),
    ("genre", "Roblox", "genre label"),
    ("created_utc", "Roblox", "when the experience was created"),
    ("updated_utc", "Roblox", "last update time"),
    ("observed_at_utc", "local", "when the snapshot was taken"),
    ("source_stability", "local", "legacy_unstable: Roblox may change or remove this API without notice"),
]


def store_dir(a):
    d = Path(a.data_dir) if a.data_dir else rc.DATA / ("dryrun" if a.dry_run else "") / "roblox"
    d.mkdir(parents=True, exist_ok=True)
    return d


def watchlist(path=None):
    with Path(path or rc.CONFIG / "roblox_experiences.csv").open(newline="", encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if r.get("universe_id", "").strip().isdigit()]


def get(run, url, params, fixture, dry):
    try:
        data = json.loads(rc.fixture(fixture) if dry else rc.http(url, params)[0])
        run.ok += 1
        return data
    except rc.HttpError:
        run.failed += 1
        raise


def cmd_games(a):
    cfg = rc.settings()["roblox"]
    items = watchlist(a.list)
    if not items:
        sys.exit("No experiences: add universe IDs to config/research/roblox_experiences.csv")
    if len(items) > cfg["max_experiences"]:
        sys.exit(f"Watchlist has {len(items)} experiences; the limit is {cfg['max_experiences']} (settings.json).")
    d = store_dir(a)
    snaps = d / "roblox_experiences.csv"
    last = max((r["observed_at_utc"] for r in rc.read_rows(snaps)), default="")
    if last and not a.dry_run and not a.force:
        mins = (rc.now() - rc.parse_time(last)).total_seconds() / 60
        if mins < cfg["min_minutes_between_runs"]:
            sys.exit(f"Last snapshot was {mins:.0f} min ago; wait until {cfg['min_minutes_between_runs']} min "
                     "(keeps load on this legacy API low).")
    ids = [r["universe_id"].strip() for r in items]
    labels = {r["universe_id"].strip(): r.get("label", "") for r in items}
    run = rc.Run("roblox", "games", {"universe_ids": ids}, a.dry_run, a.data_dir)
    try:
        games = get(run, GAMES, {"universeIds": ",".join(ids)}, "roblox_games.json", a.dry_run).get("data", [])
    except rc.HttpError as e:
        run.finish("failed", f"{e.status} {e.reason}")
        sys.exit(f"Roblox games API failed ({e.status} {e.reason}). It is a legacy API and may have changed; "
                 "nothing was stored.")
    try:
        votes = {str(v["id"]): v for v in get(run, VOTES, {"universeIds": ",".join(ids)}, "roblox_votes.json", a.dry_run).get("data", [])}
    except rc.HttpError as e:
        print(f"Votes unavailable ({e.status}); vote columns left blank.")
        votes = {}
    observed = rc.iso(rc.now())
    rows = []
    for g in games:
        uid = str(g.get("id", ""))
        v = votes.get(uid, {})
        cr = g.get("creator") or {}
        rows.append({"universe_id": uid, "label": labels.get(uid, ""), "root_place_id": g.get("rootPlaceId", ""),
                     "name": g.get("name", ""), "creator_name": cr.get("name", ""), "creator_type": cr.get("type", ""),
                     "playing": g.get("playing", ""), "visits": g.get("visits", ""),
                     "favorited_count": g.get("favoritedCount", ""), "up_votes": v.get("upVotes", ""),
                     "down_votes": v.get("downVotes", ""), "max_players": g.get("maxPlayers", ""),
                     "genre": g.get("genre", ""), "created_utc": g.get("created", ""), "updated_utc": g.get("updated", ""),
                     "observed_at_utc": observed, "source_stability": "legacy_unstable", "run_id": run.id})
    missing = set(ids) - {r["universe_id"] for r in rows}
    rc.append_rows(snaps, FIELDS, rows)
    run.rows = len(rows)
    run.finish("ok" if not missing else "partial", f"not returned: {','.join(sorted(missing))}" if missing else "")
    for r in rows:
        print(f"  {r['name'][:40]:40} playing {r['playing'] or '?':>8}  visits {r['visits'] or '?'}")
    if missing:
        print(f"Not returned (wrong ID or removed): {', '.join(sorted(missing))}")
    print(f"{len(rows)} snapshots -> {snaps} [run {run.id}]")


def cmd_universe(a):
    run = rc.Run("roblox", "universe", {"place_id": a.place_id}, a.dry_run, a.data_dir)
    data = get(run, PLACE.format(int(a.place_id)), None, "roblox_universe.json", a.dry_run)
    run.finish()
    print(f"place {a.place_id} -> universe {data.get('universeId', '?')} (add it to config/research/roblox_experiences.csv)")


def cmd_report(a):
    d = store_dir(a)
    rows = rc.read_rows(d / "roblox_experiences.csv")
    dest = rc.export("roblox", "roblox_experiences", rows, COLUMNS, notes=[
        "Experimental legacy source: numbers can change meaning or vanish without notice.",
        "playing is a point-in-time concurrent figure; visits/favourites/votes are lifetime totals at observation.",
        "Player counts are context for a game's momentum, not evidence that any video caused a change."],
        provenance="P1", retention_rule="no stated provider limit (legacy public endpoint)", expires_at=None,
        share=True, dry_run=a.dry_run, out_dir=(d / "reports") if a.data_dir else None)
    print(f"{len(rows)} rows -> {dest}")


def main():
    sys.stdout.reconfigure(errors="replace")  # titles contain emoji the Windows console can't encode
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--data-dir", help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("games")
    g.add_argument("--list", help="watchlist CSV (default config/research/roblox_experiences.csv)")
    g.add_argument("--force", action="store_true", help="ignore the minimum gap between runs")
    u = sub.add_parser("universe")
    u.add_argument("place_id")
    sub.add_parser("report")
    a = ap.parse_args()
    {"games": cmd_games, "universe": cmd_universe, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    main()
