"""Run a TikTok Actor with a hard charge cap. Save its receipt and dataset."""

import argparse
import math
import os
import re
import time
from pathlib import Path

from apify import DEFAULT_ACTOR, req
from genre_common import DATA_DIR, rc, read_json, write_json

BASIS = "Apify use approved for this toolkit's TikTok collection."
TERMINAL = {"SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"}
RECEIPT_FIELDS = (
    "id",
    "status",
    "startedAt",
    "finishedAt",
    "defaultDatasetId",
    "defaultKeyValueStoreId",
    "chargedEventCounts",
    "usageTotalUsd",
)


def dataset_items(dataset_id):
    """Read a completed Actor dataset in page order."""
    items = []
    page_size = 500
    while True:
        page = req(
            f"datasets/{dataset_id}/items",
            params={"offset": len(items), "limit": page_size},
        )
        items.extend(page)
        if len(page) < page_size:
            return items


def run(label, payload, cap, *, data_dir=DATA_DIR):
    """Start a capped run and record its provenance and resulting items."""
    if not re.fullmatch(r"[\w-]+", label):
        raise ValueError(
            "Use letters, numbers, underscores or hyphens in the run label."
        )
    if not math.isfinite(cap) or cap <= 0:
        raise ValueError("Supply a positive charge cap in USD.")
    actor = os.environ.get("APIFY_ACTOR", DEFAULT_ACTOR)
    dest = data_dir / rc.new_run_id(f"apify-{label}")
    dest.mkdir(parents=True)
    result = req(
        f"acts/{actor}/runs",
        params={"maxTotalChargeUsd": cap, "timeout": 900, "waitForFinish": 30},
        payload=payload,
    )["data"]
    print(rc.redact(f"run {result['id']} -> {dest}"), flush=True)
    while result["status"] not in TERMINAL:
        time.sleep(5)
        result = req(f"actor-runs/{result['id']}", params={"waitForFinish": 30})["data"]
    items = dataset_items(result["defaultDatasetId"])
    receipt = {key: result.get(key) for key in RECEIPT_FIELDS}
    receipt.update(
        actor=actor.replace("~", "/"),
        input=payload,
        charge_cap_usd=cap,
        permission_basis=BASIS,
        items=len(items),
    )
    write_json(dest / "run.json", receipt, indent=2)
    write_json(dest / "items.json", items)
    print(
        rc.redact(
            f"{result['status']} {len(items)} items | USD {result.get('usageTotalUsd')} {result.get('chargedEventCounts')}"
        )
    )
    return dest, items


def main(argv=None):
    """Parse the Actor input and cap, then run collection."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label")
    parser.add_argument("cap_usd", type=float)
    parser.add_argument("payload", type=Path)
    args = parser.parse_args(argv)
    try:
        run(args.label, read_json(args.payload), args.cap_usd)
    except (rc.HttpError, OSError, ValueError, KeyError) as error:
        parser.exit(1, rc.redact(f"Error: {error}\n"))


if __name__ == "__main__":
    main()
