"""FIXTURE ONLY: back-fills daily snapshots for the demo database (`ss dash demo`) and tests.

The connector fixtures give one snapshot per sync. Real accounts build history one sync a day; this writes the same
shape for the last DAYS days so the demo shows trends: each video's lifetime counters grow towards today's fixture
value, follower counts climb (with a dip, so losses show), and nothing is written to the live database.
"""
import math
from datetime import date, datetime, timedelta, timezone

DAYS = 21


def backfill(store, days=DAYS):
    today = datetime.now(timezone.utc).date()
    rows = []
    ups = store.q("SELECT upload_id, account_id, platform, published_at_utc FROM uploads")
    for u in ups:
        pub = date.fromisoformat((u["published_at_utc"] or today.isoformat())[:10])
        latest = store.q("""SELECT metric, source, value, observed_at_utc FROM observations o WHERE entity_id=? AND period_type='lifetime'
                            AND status='value' AND observed_at_utc=(SELECT MAX(observed_at_utc) FROM observations o2
                            WHERE o2.entity_id=o.entity_id AND o2.metric=o.metric AND o2.source=o.source)""", (u["upload_id"],))
        for r in latest:
            if r["metric"] in ("avg_view_duration_s", "avg_view_pct", "completion_rate"):
                continue
            for back in range(1, days + 1):
                d = today - timedelta(days=back)
                if d < pub:
                    break
                age, now_age = (d - pub).days + 1, (today - pub).days + 1
                share = (1 - math.exp(-age / 4)) / (1 - math.exp(-now_age / 4))  # fast start, then a long tail
                rows.append(_obs(u["platform"], u["account_id"], "upload", u["upload_id"], r["metric"], round(r["value"] * share),
                                 "lifetime", "", d.isoformat(), r["source"], d))
    for a in store.q("SELECT account_id, platform FROM accounts WHERE platform IN ('youtube','tiktok','instagram')"):
        cur = store.q("""SELECT value, source FROM observations WHERE account_id=? AND metric='followers' AND period_type='point'
                         AND status='value' ORDER BY observed_at_utc DESC LIMIT 1""", (a["account_id"],))
        if not cur:
            continue
        v, src = cur[0]["value"], cur[0]["source"]
        for back in range(1, days + 1):
            d = today - timedelta(days=back)
            v = max(0, round(v - (v * 0.018) + (12 if back in (6, 7) else 0)))  # mostly growth, a small loss a week ago
            rows.append(_obs(a["platform"], a["account_id"], "account", a["account_id"], "followers", v, "point",
                             d.isoformat(), d.isoformat(), src, d))
    return store.put_obs(rows)


def _obs(platform, account, etype, eid, metric, value, ptype, pstart, pend, source, d):
    at = datetime(d.year, d.month, d.day, 9, tzinfo=timezone.utc).isoformat()
    return {"platform": platform, "account_id": account, "entity_type": etype, "entity_id": eid, "metric": metric,
            "value": float(value), "period_type": ptype, "period_start": pstart, "period_end": pend, "observed_at_utc": at,
            "source": source, "run_id": "fixture-history", "note": "FIXTURE history"}
