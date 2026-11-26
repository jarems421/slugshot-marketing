"""Inspect the default Clockworks TikTok Actor input schema."""

import argparse
import json
from urllib.parse import urlsplit

from genre_common import rc

from creative_references import apify_request

DEFAULT_ACTOR = "clockworks~tiktok-scraper"


def req(path, params=None, payload=None):
    """Send a request using the shared Apify client."""
    token = rc.env_value("APIFY_TOKEN")
    if not token:
        raise ValueError("Set APIFY_TOKEN in .env or the environment.")
    return apify_request(path, token, params=params, payload=payload)


def download(url, *, timeout=30):
    """Fetch an Actor result without sharing a credential with media CDNs."""
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Actor media links must be HTTPS.")
    headers = {}
    if parsed.hostname.casefold() == "api.apify.com":
        token = rc.env_value("APIFY_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    body, _ = rc.http(url, timeout=timeout, unredirected_headers=headers)
    return body


def main(argv=None):
    """Print the Actor's input field names, types and defaults."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    try:
        build = req(f"acts/{DEFAULT_ACTOR}/builds/default")["data"]
        schema = build.get("inputSchema") or build.get("actorDefinition", {}).get(
            "input"
        )
        if isinstance(schema, str):
            schema = json.loads(schema)
        for key, field in schema["properties"].items():
            default = str(field.get("default", field.get("prefill", "")))[:60]
            description = (field.get("description") or "")[:160].replace("\n", " ")
            print(rc.redact(f"{key} | {field.get('type')} | {default} | {description}"))
    except (rc.HttpError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, rc.redact(f"Error: {error}\n"))


if __name__ == "__main__":
    main()
