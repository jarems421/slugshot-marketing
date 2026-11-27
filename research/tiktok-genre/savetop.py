"""Save permitted media copies from an existing Actor dataset."""

import argparse
from pathlib import Path

from apify import download
from genre_common import DATA_DIR, MEDIA_DIR, rc, read_json


def main(argv=None):
    """Download the first permitted media URL per post."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dataset",
        nargs="?",
        type=Path,
        help="Actor items.json (defaults to the first apify-top run)",
    )
    parser.add_argument("--output-dir", type=Path, default=MEDIA_DIR / "top")
    args = parser.parse_args(argv)
    dataset = args.dataset or next(
        iter(sorted(DATA_DIR.glob("apify-top*/items.json"))), None
    )
    if dataset is None:
        parser.exit(1, "No apify-top dataset found. Supply an Actor items.json file.\n")
    items = read_json(dataset)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for item in items:
        url = (item.get("mediaUrls") or [None])[0]
        if not url:
            print(f"{item.get('id', 'unknown')}: no media URL")
            continue
        try:
            body = download(url, timeout=120)
        except (rc.HttpError, ValueError) as error:
            parser.exit(1, rc.redact(f"Error: {error}\n"))
        path = args.output_dir / f"{item['id']}.mp4"
        path.write_bytes(body)
        print(f"saved {path.name}")


if __name__ == "__main__":
    main()
