"""Owner-authorised OAuth through the local loopback (http://127.0.0.1:<port>/oauth/callback), with PKCE.

Google (YouTube): Desktop-app OAuth client; Google accepts any loopback port for that client type.
TikTok: Login Kit; the redirect URI must be registered exactly in the TikTok developer portal. TikTok's
desktop PKCE uses a hex-encoded SHA-256 challenge (verify against TikTok's current docs at first use).
Instagram: no OAuth here; the owner pastes the long-lived token the Meta app dashboard generates.
Tokens go to the DPAPI vault; nothing is logged.
purpose="publish" adds the upload scopes (YouTube youtube.upload; TikTok video.upload, video.publish) on top of
the analytics ones, so one connection serves both. The granted scopes are stored with the token.
Reconnecting asks again for every scope the stored token already holds, so an analytics reconnect never drops
upload permission (TikTok replaces the token's scopes; Google also merges them via include_granted_scopes).
A callback that would bind a different account than the one already recorded, or an account already connected
in another slot (e.g. the EN TikTok in the ES slot), is refused and nothing is stored.
"""
import base64
import hashlib
import os
import time
import urllib.parse

from . import connectors as C
from . import vault
from .store import settings

_pending = {}  # state -> {provider, account_id, verifier, created}


def redirect_uri():
    return f"http://127.0.0.1:{settings()['port']}/oauth/callback"


def _verifier():
    return base64.urlsafe_b64encode(os.urandom(48)).rstrip(b"=").decode()


def _held(provider, account_id):
    """Scopes the stored token already has (so a reconnect asks for them again)."""
    t = vault.get(f"oauth_{provider}_{account_id}") or {}
    return [x for x in (t.get("scope") or "").replace(",", " ").split() if x]


def _scopes(base, extra, held):
    return list(dict.fromkeys(base + extra + held))


def _other_slots(provider, account_id):
    from .store import Store
    return [a for a in Store().accounts() if a["platform"] == provider and a["account_id"] != account_id]


def start(provider, account_id, purpose="analytics"):
    from .publish import UPLOAD_SCOPES
    state = base64.urlsafe_b64encode(os.urandom(18)).rstrip(b"=").decode()
    verifier = _verifier()
    _pending[state] = {"provider": provider, "account_id": account_id, "verifier": verifier, "created": time.time(),
                      "purpose": purpose}
    extra = UPLOAD_SCOPES.get(provider, []) if purpose == "publish" else []
    if provider == "youtube":
        cid = vault.secret("YOUTUBE_OAUTH_CLIENT_ID")
        if not cid:
            raise ValueError("Add the Google OAuth client (YOUTUBE_OAUTH_CLIENT_ID / _SECRET) first")
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
            "client_id": cid, "redirect_uri": redirect_uri(), "response_type": "code",
            "scope": " ".join(_scopes(C.YouTubeAnalytics.scopes, extra, _held("youtube", account_id))), "access_type": "offline", "prompt": "consent select_account",
            "include_granted_scopes": "true",
            "code_challenge": challenge, "code_challenge_method": "S256", "state": state})
    if provider == "tiktok":
        key = vault.secret("TIKTOK_CLIENT_KEY")
        if not key:
            raise ValueError("Add the TikTok app (TIKTOK_CLIENT_KEY / _SECRET) first")
        challenge = hashlib.sha256(verifier.encode()).hexdigest()
        return "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode({
            "client_key": key, "redirect_uri": redirect_uri(), "response_type": "code",
            "scope": ",".join(_scopes(C.TikTok.scopes, extra, _held("tiktok", account_id))), "state": state, "code_challenge": challenge,
            "code_challenge_method": "S256"})
    raise ValueError("unknown provider")


def finish(params):
    """Handle the callback. Returns a short, secret-free message for the page."""
    state = params.get("state", "")
    p = _pending.pop(state, None)
    if not p or time.time() - p["created"] > 900:
        return False, "This sign-in link expired or wasn't started here. Start again from Settings."
    if params.get("error"):
        return False, f"Sign-in was cancelled ({params.get('error')})."
    code = params.get("code", "")
    ctx = C.Ctx()
    try:
        if p["provider"] == "youtube":
            r = ctx.call("", "https://oauth2.googleapis.com/token", data={
                "code": code, "client_id": vault.secret("YOUTUBE_OAUTH_CLIENT_ID"),
                "client_secret": vault.secret("YOUTUBE_OAUTH_CLIENT_SECRET"), "redirect_uri": redirect_uri(),
                "grant_type": "authorization_code", "code_verifier": p["verifier"]})
            if not r.get("refresh_token"):
                return False, "Google returned no refresh token. Remove the app's access in your Google account and connect again."
            bad = _youtube_identity_problem(ctx, r["access_token"], p["account_id"])
            if bad:
                return False, bad
            vault.put(f"oauth_youtube_{p['account_id']}", {"refresh_token": r["refresh_token"], "access_token": r["access_token"],
                                                            "expires_at": time.time() + int(r.get("expires_in", 3600)),
                                                            "scope": r.get("scope", "")})
        else:
            r = ctx.call("", "https://open.tiktokapis.com/v2/oauth/token/", data={
                "client_key": vault.secret("TIKTOK_CLIENT_KEY"), "client_secret": vault.secret("TIKTOK_CLIENT_SECRET"),
                "code": code, "grant_type": "authorization_code", "redirect_uri": redirect_uri(), "code_verifier": p["verifier"]})
            bad = _tiktok_identity_problem(r.get("open_id", ""), p["account_id"])
            if bad:
                return False, bad
            granted = set((r.get("scope") or "").split(","))
            from .publish import UPLOAD_SCOPES
            wanted = C.TikTok.scopes + (UPLOAD_SCOPES["tiktok"] if p.get("purpose") == "publish" else [])
            missing = set(wanted) - granted
            vault.put(f"oauth_tiktok_{p['account_id']}", {"access_token": r["access_token"], "refresh_token": r["refresh_token"],
                                                           "expires_at": time.time() + int(r.get("expires_in", 86400)),
                                                           "open_id": r.get("open_id", ""), "scope": r.get("scope", ""),
                                                           **({"refresh_expires_at": time.time() + int(r["refresh_expires_in"])}
                                                              if r.get("refresh_expires_in") else {})})
            if missing:
                return True, f"Connected, but these permissions were not granted: {', '.join(sorted(missing))}."
    except C.rc.HttpError as e:
        return False, f"The provider refused the sign-in (HTTP {e.status}: {e.reason})."
    return True, "Connected. You can close this tab."


def _youtube_identity_problem(ctx, access_token, account_id):
    """'' if the signed-in channel may be stored under account_id, else a message for the page."""
    from .store import Store
    acct = Store().account(account_id) or {}
    items = ctx.call("", "https://www.googleapis.com/youtube/v3/channels", {"part": "id,snippet", "mine": "true"},
                     {"Authorization": f"Bearer {access_token}"}).get("items") or []
    if not items:
        return "That Google account has no YouTube channel. Connect again and pick the channel."
    cid, url = items[0]["id"], items[0]["snippet"].get("customUrl", "")
    if acct.get("external_id") and acct["external_id"] != cid:
        return f"You signed in as {url or cid}, but {acct.get('label', account_id)} is a different channel. Connect again and pick the right one."
    if not acct.get("external_id") and acct.get("handle") and url and not C.same_handle(url, acct["handle"]):
        return f"You signed in as {url}, but {acct.get('label', account_id)} is @{acct['handle'].lstrip('@')}. Connect again and pick the right channel."
    for o in _other_slots("youtube", account_id):
        if o.get("external_id") == cid:
            return f"{url or cid} is already connected as {o['label']}. Connect again and pick the other channel."
    return ""


def _tiktok_identity_problem(open_id, account_id):
    from .store import Store
    acct = Store().account(account_id) or {}
    if open_id and acct.get("external_id") and acct["external_id"] != open_id:
        return f"That TikTok account isn't {acct.get('label', account_id)}. Sign out of TikTok in the browser, then connect again."
    for o in _other_slots("tiktok", account_id):
        t = vault.get(f"oauth_tiktok_{o['account_id']}") or {}
        if open_id and open_id in (o.get("external_id"), t.get("open_id")):
            return f"That TikTok account is already connected as {o['label']}. Sign out of TikTok in the browser, then connect again."
    return ""
