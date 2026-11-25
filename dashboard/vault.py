"""Local credential vault: Windows DPAPI-encrypted files in data/local/dashboard/vault/ (git-ignored).

DPAPI ties each file to this Windows user account, so a copied file is useless elsewhere. Values are
never logged, printed, returned by the HTTP API or written to exports. Lookup order for a name:
vault first, then the environment / .env (the toolkit's existing convention).
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import research_common as rc  # noqa: E402

from .store import DATA  # noqa: E402

VAULT = Path(os.environ.get("SLUGSHOT_DASH_VAULT") or DATA / "vault")  # default; root() re-reads the environment


def root():
    """Resolved per call, so a test (or the demo) that sets SLUGSHOT_DASH_VAULT after import still gets its own vault."""
    return Path(os.environ.get("SLUGSHOT_DASH_VAULT") or DATA / "vault")
NAME = re.compile(r"[A-Za-z0-9_.-]{1,80}")


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob(data):
    buf = ctypes.create_string_buffer(data, len(data))
    return _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf


def _dpapi(data, protect):
    if os.name != "nt":
        raise RuntimeError("the credential vault needs Windows (DPAPI)")
    crypt = ctypes.windll.crypt32
    src, _keep = _blob(data)
    out = _Blob()
    fn = crypt.CryptProtectData if protect else crypt.CryptUnprotectData
    ok = fn(ctypes.byref(src), None, None, None, None, 0x1, ctypes.byref(out))  # 0x1 = UI_FORBIDDEN
    if not ok:
        raise RuntimeError("DPAPI call failed")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def _path(name):
    if not NAME.fullmatch(name):
        raise ValueError("bad credential name")
    return root() / f"{name}.dpapi"


def put(name, value):
    root().mkdir(parents=True, exist_ok=True)
    data = json.dumps(value).encode()
    _path(name).write_bytes(_dpapi(data, True))


def get(name, default=None):
    p = _path(name)
    if p.exists():
        try:
            return json.loads(_dpapi(p.read_bytes(), False))
        except Exception:
            return default
    return default


def delete(name):
    p = _path(name)
    if p.exists():
        p.unlink()


def has(name):
    return _path(name).exists()


def secret(name):
    """A plain secret string (API key, app secret): vault, then .env/environment."""
    v = get(name)
    return v if isinstance(v, str) and v else rc.env_value(name)


def all_secret_values():
    """Every stored secret string, for the export leak check. Never print the result."""
    vals = []
    if root().exists():
        for p in root().glob("*.dpapi"):
            v = get(p.stem)
            if isinstance(v, str):
                vals.append(v)
            elif isinstance(v, dict):
                vals += [x for x in v.values() if isinstance(x, str) and len(x) > 12]
    for n in SECRET_NAMES:
        v = rc.env_value(n)
        if v:
            vals.append(v)
    return [v for v in vals if len(v) > 8]


SECRET_NAMES = ["YOUTUBE_API_KEY", "YOUTUBE_OAUTH_CLIENT_ID", "YOUTUBE_OAUTH_CLIENT_SECRET", "INSTAGRAM_APP_SECRET",
                "TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "ROBLOX_ANALYTICS_API_KEY", "TWITCH_CLIENT_ID",
                "TWITCH_CLIENT_SECRET", "COMPOSIO_API_KEY", "BUFFER_API_KEY", "CLOUDINARY_API_KEY", "CLOUDINARY_API_SECRET"]
