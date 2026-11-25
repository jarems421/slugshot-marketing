"""Publishing to our own accounts: drafts, checks, owner approval, official-API uploads, manual fallback.

Nothing leaves this machine until the owner approves a job in the dashboard by typing the account handle.
Approval binds the exact file (SHA-256) and the exact text and options; any later change voids it.
Claude prepares drafts and packages (`ss publish`), and never approves.

Routes (official docs checked 2026-11-25; docs/dashboard/publishing.md has the quotes and limits):
| platform  | route   | API                                                   | scope / permission               |
|-----------|---------|-------------------------------------------------------|----------------------------------|
| youtube   | api     | Data API v3 videos.insert, resumable                  | youtube.upload                   |
| tiktok    | inbox   | Content Posting API, upload to inbox (owner finishes) | video.upload                     |
| tiktok    | direct  | Content Posting API, Direct Post                      | video.publish (+ creator_info)   |
| tiktok    | buffer  | Buffer createPost (Buffer's audited TikTok app)       | BUFFER_API_KEY; public video URL |
| instagram | buffer  | Buffer createPost, type reel                          | BUFFER_API_KEY; public video URL |
| instagram | api     | Instagram Login, REELS container from a public URL    | instagram_business_content_publish |
| any       | manual  | package (text files + checklist); owner posts by hand | none                             |

Two separate settings (publishing.* in config/dashboard/settings.json):
- public_posting: whether a job may be anything other than private (YouTube private, TikTok SELF_ONLY).
- reveal_lock: the game's identity stays hidden, whatever the visibility. Text naming the game
  (publishing.reveal_terms) blocks any post that others can see, and the owner confirms at approval that the
  video itself doesn't reveal it. Only the owner turns it off.
TikTok Direct Post stays SELF_ONLY on a private account until TikTok audits the app (tiktok_app_audited);
the inbox route lets the owner choose the visibility in the app. Manual packages are always allowed.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import connectors as C
from . import hosting
from . import vault
from .store import DATA, ROOT, now_iso, settings

PLATFORMS = ("youtube", "tiktok", "instagram")
ROUTES = {"youtube": ("api", "manual"), "tiktok": ("buffer", "inbox", "direct", "manual"), "instagram": ("buffer", "api", "manual")}
UPLOAD_SCOPES = {"youtube": ["https://www.googleapis.com/auth/youtube.upload"], "tiktok": ["video.upload", "video.publish"]}
VIDEO_EXT = {".mp4", ".mov", ".webm"}
STATES = ("draft", "approved", "uploading", "processing", "sent_to_inbox", "in_buffer_drafts", "done", "failed", "manual_pending")
PACKAGES = DATA / "publish"
TIKTOK_MUSIC = "By posting, you agree to TikTok's Music Usage Confirmation."
TIKTOK_BRANDED = "By posting, you agree to TikTok's Branded Content Policy and Music Usage Confirmation."
YT_CHUNK = 32 * 256 * 1024            # 8 MiB; YouTube chunks must be multiples of 256 KiB
TT_CHUNK = 10_000_000                # TikTok: 5-64 MB per chunk, last chunk may carry the remainder (<=128 MB)

# Platform limits used by the checks (from the official pages; see docs/dashboard/publishing.md).
LIMITS = {
    "youtube": {"title": 100, "description": 5000, "tags_total": 500, "max_bytes": 256 * 1024 ** 3},
    "tiktok": {"caption": 2200, "max_bytes": 4 * 1024 ** 3, "max_s": 600, "min_side": 360, "max_side": 4096, "fps": (23, 60)},
    "instagram": {"caption": 2200, "hashtags": 30, "max_bytes": 300 * 1024 ** 2, "min_s": 3, "max_s": 900, "fps": (23, 60),
                  "max_width": 1920},
}
GAME_TRUTH_BLOCK = [re.compile(r"floppy[^.!?\n]{0,40}\b(does nothing|useless|zero damage|no damage|0 damage)", re.I),
                    re.compile(r"floppy[^.!?\n]{0,40}\b(transform|evolve|ability|abilities)", re.I)]


REVEAL_TERMS = [r"slug\s*shot", r"roblox\.com/(?:games|share)", r"ro\.blox\.com"]


def cfg():
    p = settings().get("publishing", {})
    return {"reveal_lock": p.get("reveal_lock", True), "public_posting": p.get("public_posting", False),
            "reveal_terms": p.get("reveal_terms", REVEAL_TERMS), "tiktok_app_audited": p.get("tiktok_app_audited", False),
            "youtube_category_id": p.get("youtube_category_id", "20"), "roots": p.get("allowed_roots", ["exports", "media"])}


def visibility(j):
    """'private' (only the account sees it), 'in_app' (TikTok inbox: the owner picks in the app) or 'visible'."""
    f, platform, route = j["fields"], j["platform"], j["route"]
    if platform == "youtube":
        return "private" if f.get("privacy", "private") == "private" else "visible"
    if route == "buffer":
        return "in_app" if f.get("buffer_draft") else "visible"  # Buffer posts follow the account's own privacy
    if platform == "tiktok":
        if route == "inbox":
            return "in_app"
        if route == "direct":
            return "private" if f.get("privacy") == "SELF_ONLY" else "visible"
    return "visible"


# ------------------------------------------------------------------ files
def resolve_video(path):
    """Only video files inside the workspace's exports/ or media/ folders."""
    p = Path(path)
    p = (p if p.is_absolute() else ROOT / p).resolve()
    roots = [(ROOT / r).resolve() for r in cfg()["roots"]]
    if not any(p == r or r in p.parents for r in roots):
        raise ValueError("video must be inside exports/ or media/")
    if p.suffix.lower() not in VIDEO_EXT:
        raise ValueError("video must be .mp4, .mov or .webm")
    if not p.is_file():
        raise ValueError(f"no such file: {rel(p)}")
    return p


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _tool(name):
    found = shutil.which(name)
    if found:
        return found
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet"
    for p in [base / "Links" / f"{name}.exe", *base.glob(f"Packages/Gyan.FFmpeg*/*/bin/{name}.exe")]:
        if p.exists():
            return str(p)
    return None


def probe(path):
    """ffprobe facts about the file, or {} if ffprobe isn't available."""
    exe = _tool("ffprobe")
    if not exe:
        return {}
    try:
        out = subprocess.run([exe, "-v", "error", "-show_entries",
                              "format=duration,size:stream=codec_type,codec_name,width,height,avg_frame_rate,sample_rate",
                              "-of", "json", str(path)], capture_output=True, text=True, timeout=60, check=True).stdout
        j = json.loads(out)
    except (subprocess.SubprocessError, ValueError, OSError):
        return {}
    v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in j.get("streams", []) if s.get("codec_type") == "audio"), {})
    fps = None
    if v.get("avg_frame_rate") and "/" in v["avg_frame_rate"]:
        num, den = v["avg_frame_rate"].split("/")
        fps = round(float(num) / float(den), 2) if float(den) else None
    fmt = j.get("format", {})
    return {"duration_s": float(fmt["duration"]) if fmt.get("duration") else None, "bytes": int(fmt.get("size") or 0),
            "width": v.get("width"), "height": v.get("height"), "fps": fps, "video_codec": v.get("codec_name"),
            "audio_codec": a.get("codec_name"), "audio_hz": int(a["sample_rate"]) if a.get("sample_rate") else None}


# ------------------------------------------------------------------ jobs
def _load(row):
    if not row:
        return None
    j = dict(row)
    for k, d in (("fields", {}), ("approval", None), ("result", {}), ("log", [])):
        try:
            j[k] = json.loads(j[k]) if j[k] else d
        except ValueError:
            j[k] = d
    return j


def job(store, job_id):
    r = store.q("SELECT * FROM publish_jobs WHERE job_id=?", (job_id,))
    return _load(r[0]) if r else None


def jobs(store, state=None):
    sql, args = "SELECT * FROM publish_jobs", ()
    if state:
        sql, args = sql + " WHERE state=?", (state,)
    return [_load(r) for r in store.q(sql + " ORDER BY updated_at_utc DESC", args)]


def default_fields(store, platform, asset):
    concept = store.q("SELECT * FROM concepts WHERE concept_id=?", (asset["concept_id"],))[0]
    hook = concept.get("hook_text") or concept.get("title") or ""
    synthetic = bool(asset.get("fiction_label"))
    if platform == "youtube":
        return {"title": hook[:100], "description": "", "tags": [], "privacy": "private", "made_for_kids": None,
                "synthetic_media": synthetic, "language": asset.get("language", "")}
    if platform == "tiktok":
        # TikTok's UX rules: no default privacy, interactions off, commercial toggle off.
        return {"caption": hook, "privacy": "", "allow_comment": False, "allow_duet": False, "allow_stitch": False,
                "commercial": False, "your_brand": False, "branded_content": False, "is_aigc": synthetic, "cover_ms": 1000,
                "video_url": "", "buffer_draft": False}
    return {"caption": hook, "share_to_feed": True, "video_url": "", "cover_ms": 0, "is_aigc": synthetic, "buffer_draft": False}


def create(store, asset_id, account_id, video, route=None, fields=None, experiment_id="", variant_id=""):
    asset = store.q("SELECT * FROM assets WHERE asset_id=?", (asset_id,))
    if not asset:
        raise ValueError(f"unknown version {asset_id}; register it on the Content page first")
    acct = store.account(account_id)
    if not acct or not acct.get("active", 1):
        raise ValueError(f"unknown or inactive account {account_id}")
    platform = acct["platform"]
    if platform not in PLATFORMS:
        raise ValueError(f"{platform} accounts can't publish videos")
    route = route or ROUTES[platform][0]
    if route not in ROUTES[platform]:
        raise ValueError(f"{platform} routes: {', '.join(ROUTES[platform])}")
    if experiment_id:
        ex = [e for e in store.experiments() if e["experiment_id"] == experiment_id]
        if not ex:
            raise ValueError(f"unknown experiment {experiment_id}")
        if variant_id and variant_id not in [v["variant_id"] for v in ex[0]["variants"]]:
            raise ValueError(f"{experiment_id} has no variant {variant_id}")
    p = resolve_video(video)
    f = default_fields(store, platform, asset[0])
    f.update(fields or {})
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    n = len(store.q("SELECT 1 FROM publish_jobs WHERE job_id LIKE ?", (f"PUB-{stamp}-{account_id}%",)))
    jid = f"PUB-{stamp}-{account_id}" + (f"-{n + 1}" if n else "")
    t = now_iso()
    store.x("""INSERT INTO publish_jobs(job_id, asset_id, account_id, platform, route, video_path, fields, experiment_id,
               variant_id, state, created_at_utc, updated_at_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (jid, asset_id, account_id, platform, route, rel(p), json.dumps(f), experiment_id, variant_id,
             "manual_pending" if route == "manual" else "draft", t, t))
    return jid


def update(store, job_id, fields=None, route=None, video=None):
    j = job(store, job_id)
    if not j:
        raise ValueError("unknown job")
    if j["state"] not in ("draft", "manual_pending", "failed"):
        raise ValueError(f"a {j['state']} job can't be edited")
    f = {**j["fields"], **(fields or {})}
    route = route or j["route"]
    if route not in ROUTES[j["platform"]]:
        raise ValueError(f"{j['platform']} routes: {', '.join(ROUTES[j['platform']])}")
    vp = rel(resolve_video(video)) if video else j["video_path"]
    state = "manual_pending" if route == "manual" else "draft"
    store.x("""UPDATE publish_jobs SET fields=?, route=?, video_path=?, state=?, approval='', updated_at_utc=?
               WHERE job_id=?""", (json.dumps(f), route, vp, state, now_iso(), job_id))
    _log(store, job_id, "edited; any earlier approval is void")
    return job(store, job_id)


def delete(store, job_id):
    j = job(store, job_id)
    if j and j["state"] in ("uploading", "processing"):
        raise ValueError("an upload is in progress")
    store.x("DELETE FROM publish_jobs WHERE job_id=?", (job_id,))
    _release(store, j)


def _log(store, job_id, msg):
    j = job(store, job_id)
    log = (j or {}).get("log", [])[-40:] + [{"at": now_iso(), "msg": msg}]
    store.x("UPDATE publish_jobs SET log=?, updated_at_utc=? WHERE job_id=?", (json.dumps(log), now_iso(), job_id))


def _set(store, job_id, **kw):
    for k in ("result", "approval"):
        if k in kw and not isinstance(kw[k], str):
            kw[k] = json.dumps(kw[k])
    cols = ", ".join(f"{k}=?" for k in kw)
    store.x(f"UPDATE publish_jobs SET {cols}, updated_at_utc=? WHERE job_id=?", (*kw.values(), now_iso(), job_id))


# ------------------------------------------------------------------ checks
def _text(j):
    f = j["fields"]
    return " ".join(str(f.get(k) or "") for k in ("title", "description", "caption")) + " " + " ".join(f.get("tags") or [])


def credential(store, account, route=None):
    """(state, message). 'ready' means an upload-capable credential is in the vault."""
    a = account["account_id"]
    if os.environ.get("SLUGSHOT_DASH_FIXTURE"):
        return "ready", "fixture"
    if route == "buffer":
        return ("ready", "") if vault.secret("BUFFER_API_KEY") else ("not connected", "Add BUFFER_API_KEY (Settings).")
    if account["platform"] == "youtube":
        t = vault.get(f"oauth_youtube_{a}")
        if not t:
            return "not connected", "Connect this channel for uploads (Publish → Accounts)."
        if UPLOAD_SCOPES["youtube"][0] not in (t.get("scope") or ""):
            return "needs upload permission", "Connected for analytics only; connect again for uploads."
        return "ready", ""
    if account["platform"] == "tiktok":
        t = vault.get(f"oauth_tiktok_{a}")
        if not t:
            return "not connected", "Connect this account for uploads (Publish → Accounts)."
        return "ready", ",".join(sorted(set((t.get("scope") or "").split(",")) & set(UPLOAD_SCOPES["tiktok"])))
    if account["platform"] == "instagram":
        return ("ready", "") if vault.has(f"token_instagram_{a}") else ("not connected", "Add a token that includes instagram_business_content_publish.")
    return "unsupported", ""


def check(store, j, creator=None):
    """Errors block approval; warnings are shown beside the approve box."""
    errors, warnings = [], []
    c = cfg()
    lock = c["reveal_lock"]
    f, platform, route = j["fields"], j["platform"], j["route"]
    try:
        p = resolve_video(j["video_path"])
    except ValueError as e:
        return {"errors": [str(e)], "warnings": [], "probe": {}, "reveal_lock": lock, "public_posting": c["public_posting"],
                "tiktok_app_audited": c["tiktok_app_audited"], "visibility": visibility(j), "needs_reveal_ok": bool(lock)}
    info = probe(p) or {"bytes": p.stat().st_size}
    size = info.get("bytes") or p.stat().st_size
    lim = LIMITS[platform]
    if size > lim["max_bytes"]:
        errors.append(f"file is {size / 1e6:.0f} MB; {platform} allows {lim['max_bytes'] / 1e6:.0f} MB")
    dur, w, hgt, fps = info.get("duration_s"), info.get("width"), info.get("height"), info.get("fps")
    if not info.get("width"):
        warnings.append("ffprobe unavailable: duration, size and codec not checked")
    elif hgt and w and w > hgt:
        warnings.append(f"{w}x{hgt} is landscape; Shorts, TikTok and Reels expect vertical (1080x1920)")
    if platform == "youtube":
        if not (f.get("title") or "").strip():
            errors.append("YouTube needs a title")
        if len(f.get("title") or "") > lim["title"]:
            errors.append(f"title is {len(f['title'])} characters; YouTube allows {lim['title']}")
        if re.search(r"[<>]", (f.get("title") or "") + (f.get("description") or "")):
            errors.append("YouTube titles and descriptions can't contain < or >")
        if len(f.get("description") or "") > lim["description"]:
            errors.append(f"description is over {lim['description']} characters")
        if sum(len(t) + 1 for t in f.get("tags") or []) > lim["tags_total"]:
            errors.append("tags exceed 500 characters in total")
        if f.get("made_for_kids") not in (True, False):
            errors.append("choose whether this video is made for kids (YouTube requires the declaration)")
        if f.get("privacy") not in ("private", "unlisted", "public"):
            errors.append("choose a YouTube visibility")
        if dur and dur > 180:
            warnings.append(f"{dur:.0f} s: longer than 3 minutes, so YouTube won't treat it as a Short")
    else:
        cap = f.get("caption") or ""
        if len(cap.encode("utf-16-le")) // 2 > lim["caption"]:
            errors.append(f"caption is over {lim['caption']} characters")
        if platform == "instagram" and len(re.findall(r"(?<!\w)#\w", cap)) > lim["hashtags"]:
            errors.append("Instagram allows 30 hashtags")
        if dur and lim.get("max_s") and dur > lim["max_s"]:
            errors.append(f"{dur:.0f} s is longer than {platform} allows through the API ({lim['max_s']} s)")
        if dur and lim.get("min_s") and dur < lim["min_s"]:
            errors.append(f"Reels must be at least {lim['min_s']} s")
        if fps and lim.get("fps") and not lim["fps"][0] - 0.5 <= fps <= lim["fps"][1] + 0.5:
            errors.append(f"{fps} fps; {platform} needs 23-60 fps")
        if platform == "tiktok" and w and hgt and (min(w, hgt) < lim["min_side"] or max(w, hgt) > lim["max_side"]):
            errors.append("TikTok needs 360-4096 px per side")
        if platform == "instagram" and w and w > lim["max_width"]:
            errors.append("Reels allow at most 1920 px width")
        if platform == "instagram" and info.get("audio_hz") and info["audio_hz"] > 48000:
            errors.append("Reels audio must be at most 48 kHz")
    if platform == "tiktok" and route == "direct":
        if not f.get("privacy"):
            errors.append("choose who can view this TikTok (there is no default)")
        elif creator and f["privacy"] not in creator.get("privacy_level_options", []):
            errors.append("that privacy option isn't offered for this account")
        if not c["tiktok_app_audited"]:
            if f.get("privacy") and f["privacy"] != "SELF_ONLY":
                errors.append("TikTok hasn't audited our app yet, so Direct Post can only be 'Only me'; use Upload to inbox to post publicly")
            if creator and "PUBLIC_TO_EVERYONE" in creator.get("privacy_level_options", []):
                errors.append("this TikTok account is public, and until TikTok audits our app Direct Post only works on private accounts; use Upload to inbox")
        if f.get("commercial") and not (f.get("your_brand") or f.get("branded_content")):
            errors.append("commercial content is on: choose 'Your brand' and/or 'Branded content'")
        if f.get("branded_content") and f.get("privacy") == "SELF_ONLY":
            errors.append("TikTok: branded content can't be private")
        if creator and dur and creator.get("max_video_post_duration_sec") and dur > creator["max_video_post_duration_sec"]:
            errors.append(f"this account can post at most {creator['max_video_post_duration_sec']} s")
    if route == "buffer":
        if f.get("video_url") and not re.match(r"https://", f["video_url"]):
            errors.append("the video link must start with https://")
        elif not f.get("video_url") and not hosting.ready():
            errors.append("Buffer needs the video online: add the Cloudinary credentials, or paste an https link you control")
        elif not f.get("video_url"):
            cap = hosting.cfg()["max_file_mb"] * 1024 ** 2
            if size > cap:
                errors.append(f"file is {size / 1e6:.0f} MB; hosting takes at most {cap / 1e6:.0f} MB on the free plan (compress it locally)")
            else:
                warnings.append("at approval the file is put on Cloudinary behind a private signed link for Buffer, "
                                "and deleted once every Buffer post of it has finished")
    if platform == "instagram" and route == "api":
        if not re.match(r"https://", f.get("video_url") or ""):
            errors.append("Instagram Login can only fetch the video from a public https URL (no local upload)")
    text = _text(j)
    for rx in GAME_TRUTH_BLOCK:
        if rx.search(text):
            errors.append("game truth: Floppy deals light damage (7) and never transforms or has abilities (docs/game-truth.md)")
            break
    vis = visibility(j)
    if vis == "visible" and not c["public_posting"] and route != "manual":
        errors.append("public posting is off (publishing.public_posting): keep it private, or the owner turns it on")
    elif vis == "in_app" and not c["public_posting"]:
        warnings.append("public posting is off: choose 'Only me' when you finish this post in TikTok")
    hits = sorted({m.group(0) for rx in c["reveal_terms"] for m in re.finditer(rx, text, re.I)})
    if lock and hits:
        if vis == "private":
            warnings.append(f"names the game ({', '.join(hits)}): fine while private; remove it before this goes public")
        else:
            errors.append(f"reveal lock: the text names the game ({', '.join(hits)}); remove it, or keep the post private")
    needs_reveal_ok = bool(lock and vis != "private")
    if needs_reveal_ok:
        warnings.append("reveal lock: others may see this post. When you approve you'll confirm the video itself doesn't show "
                        "the game's name, logo, place link or anything else that identifies it")
    asset = store.q("SELECT fiction_label FROM assets WHERE asset_id=?", (j["asset_id"],))
    if asset and asset[0]["fiction_label"]:
        flag = {"youtube": "synthetic_media", "tiktok": "is_aigc"}.get(platform)
        if flag and not f.get(flag):
            warnings.append(f"this version carries the label '{asset[0]['fiction_label']}'; consider the platform's AI/altered-content flag")
    if route != "manual":
        st, msg = credential(store, store.account(j["account_id"]), route)
        if st != "ready":
            errors.append(f"{st}: {msg}")
    qc = p.with_suffix(".qc.json")
    if qc.exists():
        try:
            overall = json.loads(qc.read_text(encoding="utf-8")).get("overall", "")
            if overall and overall.upper() != "PASS":
                warnings.append(f"technical QC result: {overall}")
        except ValueError:
            pass
    return {"errors": errors, "warnings": warnings, "probe": info, "reveal_lock": lock, "public_posting": c["public_posting"],
            "tiktok_app_audited": c["tiktok_app_audited"], "visibility": vis, "needs_reveal_ok": needs_reveal_ok}


def fingerprint(j, file_hash):
    core = {k: j[k] for k in ("asset_id", "account_id", "platform", "route", "video_path", "experiment_id", "variant_id")}
    return hashlib.sha256(json.dumps({**core, "fields": j["fields"], "file": file_hash}, sort_keys=True).encode()).hexdigest()


def handle_matches(account, typed):
    want = (account.get("handle") or "").strip().lstrip("@").lower()
    return bool(want) and typed.strip().lstrip("@").lower() == want


# ------------------------------------------------------------------ approval and run
_running = set()
_run_lock = threading.Lock()


def approve(store, job_id, typed, consent=False, reveal_ok=False):
    """Owner-only (dashboard UI). Binds the file and metadata, then starts the upload in the background."""
    j = job(store, job_id)
    if not j:
        raise ValueError("unknown job")
    if j["route"] == "manual":
        raise ValueError("manual jobs need no approval: post them by hand, then mark them posted")
    if j["state"] not in ("draft", "failed"):
        raise ValueError(f"a {j['state']} job can't be approved")
    acct = store.account(j["account_id"])
    if not handle_matches(acct, typed):
        raise ValueError("type the account handle exactly to approve (it's shown above the box)")
    if j["platform"] == "tiktok" and not consent:
        raise ValueError("tick the TikTok declaration first")
    creator = tiktok_creator_info(store, acct) if j["route"] == "direct" else None
    res = check(store, j, creator)
    if res["errors"]:
        raise ValueError("fix these first: " + "; ".join(res["errors"]))
    if res["needs_reveal_ok"] and not reveal_ok:
        raise ValueError("tick the reveal-lock confirmation first: the video mustn't show or name the game")
    fh = sha256(resolve_video(j["video_path"]))
    for o in jobs(store):
        if o["job_id"] != job_id and o["account_id"] == j["account_id"] and (o.get("approval") or {}).get("file_sha256") == fh \
                and o["state"] in ("approved", "uploading", "processing", "sent_to_inbox", "in_buffer_drafts", "done"):
            raise ValueError(f"this exact file is already {o['state'].replace('_', ' ')} for this account ({o['job_id']}); "
                             "delete that job first if you really want it twice")
    appr = {"by": "owner (dashboard)", "at": now_iso(), "typed_handle": acct["handle"], "file_sha256": fh,
            "fingerprint": fingerprint(j, fh), "reveal_lock": res["reveal_lock"], "public_posting": res["public_posting"],
            "visibility": res["visibility"], "reveal_confirmed": bool(res["needs_reveal_ok"] and reveal_ok),
            "declaration": (TIKTOK_BRANDED if j["fields"].get("branded_content") else TIKTOK_MUSIC) if j["platform"] == "tiktok" else ""}
    _set(store, job_id, state="approved", approval=appr)
    _log(store, job_id, "approved by the owner")
    start(store, job_id)
    return job(store, job_id)


def start(store, job_id, background=True):
    with _run_lock:
        if job_id in _running:
            return False
        _running.add(job_id)
    if background:
        threading.Thread(target=_run_safe, args=(store, job_id), daemon=True).start()
    else:
        _run_safe(store, job_id)
    return True


def _run_safe(store, job_id):
    try:
        run(store, job_id)
    except Exception as e:  # recorded on the job; never includes tokens
        if (job(store, job_id) or {}).get("state") != "draft":
            _set(store, job_id, state="failed")
        _log(store, job_id, f"failed: {type(e).__name__}: {str(e)[:300]}")
    finally:
        with _run_lock:
            _running.discard(job_id)


def run(store, job_id, transport=None):
    j = job(store, job_id)
    appr = j.get("approval") or {}
    if j["state"] not in ("approved", "failed") or not appr:
        raise RuntimeError("not approved")
    p = resolve_video(j["video_path"])
    fh = sha256(p)
    if fh != appr.get("file_sha256") or fingerprint(j, fh) != appr.get("fingerprint"):
        _set(store, job_id, state="draft", approval="")
        raise RuntimeError("the file or text changed after approval; approve again")
    now = cfg()
    if now["reveal_lock"] != appr.get("reveal_lock"):
        raise RuntimeError("reveal lock changed since approval; approve again")
    if visibility(j) == "visible" and not now["public_posting"]:
        raise RuntimeError("public posting was turned off after approval; approve again")
    tx = transport or _transport()
    acct = store.account(j["account_id"])
    if j["route"] == "buffer":
        _set(store, job_id, state="uploading")
        url = j["fields"].get("video_url")
        if not url and not j["result"].get("buffer_post_id"):
            row = hosting.host(store, fh, p, tx, log=lambda m: _log(store, job_id, m))
            url = hosting.signed_url(row)  # handed to Buffer only; never logged or stored
        out = buffer_publish(store, job(store, job_id), acct, tx, url)
        finish(store, job_id, out, tx)
        return job(store, job_id)
    if j["platform"] in ("youtube", "tiktok"):
        verify_identity(store, acct, tx)
    _set(store, job_id, state="uploading")
    _log(store, job_id, f"uploading {p.stat().st_size / 1e6:.1f} MB to {j['platform']} ({j['route']})")
    if j["platform"] == "youtube":
        out = youtube_upload(store, j, acct, p, tx)
    elif j["platform"] == "tiktok":
        out = tiktok_upload(store, j, acct, p, tx)
    else:
        out = instagram_publish(store, j, acct, tx)
    finish(store, job_id, out)
    return job(store, job_id)


def finish(store, job_id, out, tx=None):
    """out: {state, platform_video_id?, url?, ...}. Records the upload against the version and experiment."""
    j = job(store, job_id)
    result = {**j["result"], **out}
    upload_id = j["upload_id"]
    if out.get("platform_video_id"):
        upload_id = store.save_upload({"platform": j["platform"], "platform_video_id": out["platform_video_id"],
                                       "asset_id": j["asset_id"], "account_id": j["account_id"], "url": out.get("url", ""),
                                       "title": j["fields"].get("title") or (j["fields"].get("caption") or "")[:120],
                                       "published_at_utc": out.get("published_at_utc") or now_iso(),
                                       "duration_s": (probe(resolve_video(j["video_path"])) or {}).get("duration_s"),
                                       "source": out.get("source", f"publish:{j['route']}")})
        link_experiment(store, j)
    _set(store, job_id, state=out["state"], result=result, upload_id=upload_id or "")
    _log(store, job_id, {"done": f"done: {out.get('url') or out.get('platform_video_id')}",
                         "sent_to_inbox": "sent to the TikTok inbox: open TikTok and finish the post there",
                         "in_buffer_drafts": "saved as a Buffer draft: open Buffer to post it",
                         "processing": "uploaded; the platform is still processing"}.get(out["state"], out["state"]))
    _release(store, job(store, job_id), tx)


def _release(store, j, tx=None):
    """After a Buffer job ends (or is deleted): delete the hosted copy if no other job still needs it."""
    sha = ((j or {}).get("approval") or {}).get("file_sha256")
    if not (j and j["route"] == "buffer" and sha and not j["fields"].get("video_url")):
        return
    try:
        if hosting.release(store, sha, tx or _transport()):
            _log(store, j["job_id"], "hosted copy deleted from Cloudinary (no other post needs it)")
    except Exception as e:  # cleanup retries later; the post itself is unaffected
        _log(store, j["job_id"], f"couldn't delete the hosted copy yet ({str(e)[:120]}); the daily cleanup retries")


def link_experiment(store, j):
    if not (j["experiment_id"] and j["variant_id"]):
        return
    r = store.q("SELECT asset_ids FROM variants WHERE experiment_id=? AND variant_id=?", (j["experiment_id"], j["variant_id"]))
    if r:
        ids = json.loads(r[0]["asset_ids"] or "[]")
        if j["asset_id"] not in ids:
            store.x("UPDATE variants SET asset_ids=? WHERE experiment_id=? AND variant_id=?",
                    (json.dumps(ids + [j["asset_id"]]), j["experiment_id"], j["variant_id"]))


VIDEO_ID = {"youtube": [r"youtu\.be/([\w-]{11})", r"[?&]v=([\w-]{11})", r"/shorts/([\w-]{11})", r"^([\w-]{11})$"],
            "tiktok": [r"/video/(\d{8,})", r"^(\d{8,})$"],
            "instagram": [r"/(?:reel|reels|p)/([\w-]+)", r"^([\w-]{6,})$"]}


def mark_posted(store, job_id, url_or_id, posted_at=""):
    """Manual fallback (or a TikTok inbox draft the owner finished): record the post and link it."""
    j = job(store, job_id)
    if not j:
        raise ValueError("unknown job")
    s = url_or_id.strip()
    vid = next((m.group(1) for rx in VIDEO_ID[j["platform"]] for m in [re.search(rx, s)] if m), None)
    if not vid:
        raise ValueError(f"that doesn't look like a {j['platform']} video link or ID")
    url = s if s.startswith("http") else {"youtube": f"https://www.youtube.com/watch?v={vid}",
                                          "tiktok": "", "instagram": f"https://www.instagram.com/reel/{vid}/"}[j["platform"]]
    finish(store, job_id, {"state": "done", "platform_video_id": vid, "url": url, "published_at_utc": posted_at or now_iso(),
                           "source": "publish:manual" if j["route"] == "manual" else f"publish:{j['route']}"})
    return job(store, job_id)


def package(store, job_id):
    """Manual fallback: the platform text as files plus a checklist, in data/local/publish/<job>/ (git-ignored)."""
    j = job(store, job_id)
    if not j:
        raise ValueError("unknown job")
    acct = store.account(j["account_id"])
    d = PACKAGES / job_id
    d.mkdir(parents=True, exist_ok=True)
    f = j["fields"]
    files = {}
    if j["platform"] == "youtube":
        files = {"title.txt": f.get("title", ""), "description.txt": f.get("description", ""), "tags.txt": ", ".join(f.get("tags") or [])}
    else:
        files = {"caption.txt": f.get("caption", "")}
    for name, text in files.items():
        (d / name).write_text(text, encoding="utf-8")
    res = check(store, {**j, "route": "manual"})
    steps = {
        "youtube": ["Open https://studio.youtube.com and switch to the right channel (top-right avatar).",
                    "Create → Upload videos → choose the file below.",
                    "Paste title.txt, description.txt and tags.txt (Show more → Tags).",
                    f"Audience: {'made for kids' if f.get('made_for_kids') else 'not made for kids' if f.get('made_for_kids') is False else 'choose'}; "
                    f"altered or synthetic content: {'yes' if f.get('synthetic_media') else 'no'}.",
                    f"Visibility: {f.get('privacy') or 'private'}" + (" (reveal lock: keep it private)" if res["reveal_lock"] else ""),
                    "Copy the video link and paste it into Publish → this job → Mark as posted."],
        "tiktok": ["Open TikTok Studio (https://www.tiktok.com/tiktokstudio/upload) signed in as the account below, or use the app.",
                   "Upload the file below and paste caption.txt.",
                   f"AI-generated content label: {'on' if f.get('is_aigc') else 'off'}; comments/duet/stitch as you choose.",
                   "Who can view: " + ("Only me (reveal lock)" if res["reveal_lock"] else "your choice"),
                   "Copy the video link and paste it into Publish → this job → Mark as posted."],
        "instagram": ["Open the Instagram app (or instagram.com → Create) signed in as the account below.",
                      "Create → Reel → choose the file below; paste caption.txt.",
                      "Instagram has no private posts: with the reveal lock on, keep this as a draft and don't share it.",
                      "After posting, copy the reel link and paste it into Publish → this job → Mark as posted."],
    }[j["platform"]]
    md = [f"# Manual post: {job_id}", "",
          f"- Account: {acct['label']} (@{(acct.get('handle') or '').lstrip('@')})",
          f"- Video file: `{j['video_path']}`", f"- Version: {j['asset_id']}",
          f"- Experiment: {j['experiment_id'] or 'none'} {j['variant_id']}".rstrip(), "", "## Steps", ""]
    md += [f"{i}. {s}" for i, s in enumerate(steps, 1)]
    if res["errors"] or res["warnings"]:
        md += ["", "## Checks", ""] + [f"- ERROR: {e}" for e in res["errors"] if "not connected" not in e] + [f"- note: {w}" for w in res["warnings"]]
    (d / "CHECKLIST.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    if j["state"] == "draft":
        _set(store, job_id, state="manual_pending")
    _log(store, job_id, f"manual package written to {rel(d)}")
    return {"folder": rel(d), "files": sorted(list(files) + ["CHECKLIST.md"])}


# ------------------------------------------------------------------ HTTP
class Transport:
    """Plain urllib with retries. Returns (status, headers, body_bytes). Errors never include URLs or tokens."""

    def request(self, method, url, headers=None, data=None, timeout=120):
        req = urllib.request.Request(url, data=data, headers={"User-Agent": "SlugshotDashboard/1.0 (owner's own accounts)", **(headers or {})},
                                     method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
        except urllib.error.HTTPError as e:
            return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, e.read()[:4000]
        except urllib.error.URLError as e:
            return 0, {}, json.dumps({"error": f"network error: {e.reason}"}).encode()

    def json(self, method, url, body=None, headers=None, form=None):
        h = dict(headers or {})
        data = None
        if body is not None:
            data, h["Content-Type"] = json.dumps(body).encode(), "application/json; charset=UTF-8"
        elif form is not None:
            data, h["Content-Type"] = urllib.parse.urlencode(form).encode(), "application/x-www-form-urlencoded"
        delay = 2
        for attempt in range(4):
            st, hd, raw = self.request(method, url, h, data)
            if st in (0, 429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(delay)
                delay *= 2
                continue
            try:
                j = json.loads(raw or b"{}")
            except ValueError:
                j = {}
            return st, hd, j
        return st, hd, {}


def _err(platform, st, j):
    e = j.get("error", j)
    if isinstance(e, dict):
        msg = e.get("message") or e.get("code") or ""
        code = e.get("code", "")
        if platform == "tiktok" and code and code != "ok":
            msg = f"{code}: {e.get('message', '')}"
    else:
        msg = str(e)
    return RuntimeError(f"{platform} refused (HTTP {st}): {str(msg)[:240]}")


def _token(platform, acct):
    ctx = C.Ctx(fixture=bool(os.environ.get("SLUGSHOT_DASH_FIXTURE")))
    con = {"youtube": "youtube_analytics", "tiktok": "tiktok", "instagram": "instagram"}[platform]
    return C.CONNECTORS[con].token(acct, ctx)


def youtube_upload(store, j, acct, p, tx):
    f = j["fields"]
    size = p.stat().st_size
    h = {"Authorization": f"Bearer {_token('youtube', acct)}"}
    session = j["result"].get("session_uri")
    if not session:
        body = {"snippet": {"title": f["title"], "description": f.get("description", ""), "tags": f.get("tags") or [],
                            "categoryId": cfg()["youtube_category_id"]},
                "status": {"privacyStatus": f["privacy"], "selfDeclaredMadeForKids": bool(f["made_for_kids"]),
                           "containsSyntheticMedia": bool(f.get("synthetic_media"))}}
        if f.get("language"):
            body["snippet"]["defaultLanguage"] = body["snippet"]["defaultAudioLanguage"] = f["language"]
        st, hd, r = tx.json("POST", "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                            body, {**h, "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/*"})
        if st != 200 or not hd.get("location"):
            raise _err("youtube", st, r)
        session = hd["location"]
        _set(store, j["job_id"], result={**j["result"], "session_uri": session})
    offset = 0
    st, hd, _ = tx.request("PUT", session, {**h, "Content-Length": "0", "Content-Range": f"bytes */{size}"})
    if st in (200, 201):
        offset = size
    elif st == 308 and hd.get("range"):
        offset = int(hd["range"].split("-")[1]) + 1
    elif st == 404:
        _set(store, j["job_id"], result={k: v for k, v in j["result"].items() if k != "session_uri"})
        raise RuntimeError("the YouTube upload session expired; retry to start a new one")
    raw = b""
    with open(p, "rb") as fh:
        while offset < size:
            fh.seek(offset)
            chunk = fh.read(YT_CHUNK)
            end = offset + len(chunk) - 1
            for attempt in range(5):
                st, hd, raw = tx.request("PUT", session, {**h, "Content-Length": str(len(chunk)), "Content-Type": "video/*",
                                                          "Content-Range": f"bytes {offset}-{end}/{size}"}, chunk, timeout=600)
                if st in (0, 500, 502, 503, 504):
                    time.sleep(2 ** attempt)
                    continue
                break
            if st == 308:
                offset = int(hd["range"].split("-")[1]) + 1 if hd.get("range") else offset
            elif st in (200, 201):
                offset = size
            else:
                raise _err("youtube", st, json.loads(raw or b"{}") if raw[:1] == b"{" else {})
    if not raw:  # resumed an upload that had already finished: fetch the result
        raise RuntimeError("upload finished earlier but the response was lost; check YouTube Studio, then mark as posted")
    v = json.loads(raw)
    vid = v["id"]
    return {"state": "done", "platform_video_id": vid, "url": f"https://www.youtube.com/watch?v={vid}",
            "privacy": v.get("status", {}).get("privacyStatus", f["privacy"]), "published_at_utc": now_iso(),
            "upload_status": v.get("status", {}).get("uploadStatus", "")}


TT = "https://open.tiktokapis.com/v2"


def verify_identity(store, acct, tx):
    """Before anything is sent: the stored token must still belong to this account (a reconnect could swap it)."""
    want = acct.get("handle") or ""
    if acct["platform"] == "youtube":
        st, _, r = tx.json("GET", "https://www.googleapis.com/youtube/v3/channels?part=id,snippet&mine=true",
                           headers={"Authorization": f"Bearer {_token('youtube', acct)}"})
        if st != 200:
            raise _err("youtube", st, r)
        c = (r.get("items") or [{}])[0]
        got_id, got = c.get("id", ""), (c.get("snippet") or {}).get("customUrl", "")
        if (acct.get("external_id") and got_id != acct["external_id"]) or (want and got and not C.same_handle(got, want)):
            raise RuntimeError(f"the connected channel is {got or got_id or 'unknown'}, not @{want.lstrip('@')}; reconnect the right channel")
    else:
        got = (tiktok_creator_info(store, acct, tx) or {}).get("creator_username", "")
        if want and not C.same_handle(got, want):
            raise RuntimeError(f"the connected TikTok account is @{got or 'unknown'}, not @{want.lstrip('@')}; reconnect the right account")


def tiktok_creator_info(store, acct, tx=None):
    if acct["platform"] != "tiktok":
        return None
    tx = tx or _transport()
    st, _, r = tx.json("POST", f"{TT}/post/publish/creator_info/query/", {}, {"Authorization": f"Bearer {_token('tiktok', acct)}"})
    if st != 200 or (r.get("error") or {}).get("code", "ok") != "ok":
        raise _err("tiktok", st, r)
    return r.get("data", {})


def tiktok_chunks(size):
    """(chunk_size, total_chunk_count) by TikTok's rules: under 5 MB (or under one chunk) goes whole; the
    count is size // chunk_size and the last chunk takes the remainder."""
    if size <= TT_CHUNK:
        return size, 1
    return TT_CHUNK, size // TT_CHUNK


def tiktok_upload(store, j, acct, p, tx):
    f = j["fields"]
    size = p.stat().st_size
    chunk, count = tiktok_chunks(size)
    h = {"Authorization": f"Bearer {_token('tiktok', acct)}"}
    src = {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk, "total_chunk_count": count}
    if j["route"] == "direct":
        body = {"post_info": {"title": f.get("caption", ""), "privacy_level": f["privacy"],
                              "disable_comment": not f.get("allow_comment"), "disable_duet": not f.get("allow_duet"),
                              "disable_stitch": not f.get("allow_stitch"), "video_cover_timestamp_ms": int(f.get("cover_ms") or 0),
                              "brand_content_toggle": bool(f.get("commercial") and f.get("branded_content")),
                              "brand_organic_toggle": bool(f.get("commercial") and f.get("your_brand")),
                              "is_aigc": bool(f.get("is_aigc"))}, "source_info": src}
        url = f"{TT}/post/publish/video/init/"
    else:
        body, url = {"source_info": src}, f"{TT}/post/publish/inbox/video/init/"
    st, _, r = tx.json("POST", url, body, h)
    if st != 200 or (r.get("error") or {}).get("code", "ok") != "ok":
        raise _err("tiktok", st, r)
    publish_id, upload_url = r["data"]["publish_id"], r["data"]["upload_url"]
    _set(store, j["job_id"], result={**j["result"], "publish_id": publish_id})
    ctype = {".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm"}[p.suffix.lower()]
    with open(p, "rb") as fh:
        for i in range(count):
            start_b = i * chunk
            n = size - start_b if i == count - 1 else chunk
            data = fh.read(n)
            for attempt in range(4):
                st, _, raw = tx.request("PUT", upload_url, {"Content-Type": ctype, "Content-Length": str(n),
                                                            "Content-Range": f"bytes {start_b}-{start_b + n - 1}/{size}"}, data, timeout=600)
                if st >= 500 or st == 0:
                    time.sleep(2 ** attempt)
                    continue
                break
            if st not in (200, 201, 206):
                raise RuntimeError(f"tiktok chunk {i + 1}/{count} refused (HTTP {st})" + (": the upload link expired (1 hour)" if st == 403 else ""))
    _set(store, j["job_id"], state="processing")
    return tiktok_poll(store, j, acct, publish_id, tx)


def tiktok_poll(store, j, acct, publish_id, tx, tries=40, wait=6):
    h = {"Authorization": f"Bearer {_token('tiktok', acct)}"}
    status = ""
    for _ in range(tries):
        st, _, r = tx.json("POST", f"{TT}/post/publish/status/fetch/", {"publish_id": publish_id}, h)
        if st != 200:
            raise _err("tiktok", st, r)
        d = r.get("data", {})
        status = d.get("status", "")
        if status == "FAILED":
            raise RuntimeError(f"TikTok processing failed: {d.get('fail_reason', 'no reason given')}")
        if status == "SEND_TO_USER_INBOX":
            return {"state": "sent_to_inbox", "publish_id": publish_id, "tiktok_status": status}
        ids = d.get("publicaly_available_post_id") or d.get("publicly_available_post_id") or []
        if status == "PUBLISH_COMPLETE":
            if ids:
                vid = str(ids[0])
                return {"state": "done", "platform_video_id": vid, "publish_id": publish_id, "tiktok_status": status,
                        "url": f"https://www.tiktok.com/@{(acct.get('handle') or '').lstrip('@')}/video/{vid}"}
            # Private (SELF_ONLY) posts have no public ID: the owner pastes the link later.
            return {"state": "processing", "publish_id": publish_id, "tiktok_status": status,
                    "note": "posted as private; TikTok gives no public ID, so mark it posted with the link from the app"}
        time.sleep(wait)
    return {"state": "processing", "publish_id": publish_id, "tiktok_status": status or "unknown"}


def instagram_publish(store, j, acct, tx):
    f = j["fields"]
    tok = _token("instagram", acct)
    base = C.CONNECTORS["instagram"].base()
    me = acct.get("external_id") or "me"
    if me == "me":
        st, _, r = tx.json("GET", f"{base}/me?fields=user_id&access_token={urllib.parse.quote(tok)}")
        if st != 200:
            raise _err("instagram", st, r)
        me = r.get("user_id") or r.get("id")
    form = {"media_type": "REELS", "video_url": f["video_url"], "caption": f.get("caption", ""),
            "share_to_feed": "true" if f.get("share_to_feed", True) else "false", "access_token": tok}
    if f.get("cover_ms"):
        form["thumb_offset"] = str(int(f["cover_ms"]))
    st, _, r = tx.json("POST", f"{base}/{me}/media", form=form)
    if st != 200 or not r.get("id"):
        raise _err("instagram", st, r)
    container = r["id"]
    _set(store, j["job_id"], state="processing", result={**j["result"], "container_id": container})
    for _ in range(6):  # Meta: check once a minute, for no more than 5 minutes
        st, _, r = tx.json("GET", f"{base}/{container}?fields=status_code&access_token={urllib.parse.quote(tok)}")
        code = r.get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram couldn't process the video ({code})")
        time.sleep(0 if isinstance(tx, FixtureTransport) else 60)
    else:
        return {"state": "processing", "container_id": container, "note": "still processing after 5 minutes; retry later"}
    st, _, r = tx.json("POST", f"{base}/{me}/media_publish", form={"creation_id": container, "access_token": tok})
    if st != 200 or not r.get("id"):
        raise _err("instagram", st, r)
    mid = r["id"]
    st, _, m = tx.json("GET", f"{base}/{mid}?fields=permalink,timestamp&access_token={urllib.parse.quote(tok)}")
    return {"state": "done", "platform_video_id": mid, "url": m.get("permalink", ""), "published_at_utc": m.get("timestamp") or now_iso()}


BUFFER_CREATE = """mutation($i: CreatePostInput!) { createPost(input: $i) { __typename
  ... on PostActionSuccess { post { id status } } ... on MutationError { message } } }"""
BUFFER_POST = "query($i: PostInput!) { post(input: $i) { id status externalLink sentAt error { message } } }"


def _buffer(tx, query, variables, store=None):
    q = (store.pref("buffer_quota") if store is not None else None) or {}
    if q.get("remaining") is not None and q["remaining"] < 10 and not isinstance(tx, FixtureTransport):
        raise RuntimeError(f"only {q['remaining']} Buffer API requests left in this 30-day window; wait for it to reset")
    st, hd, r = tx.json("POST", C.BUFFER, {"query": query, "variables": variables},
                        {"Authorization": f"Bearer {'FIXTURE' if isinstance(tx, FixtureTransport) else vault.secret('BUFFER_API_KEY')}"})
    C.buffer_quota(store, hd)
    if st != 200 or r.get("errors"):
        msg = "; ".join(e.get("message", "") for e in r.get("errors") or []) or (r.get("error") or {}).get("message", "")
        raise RuntimeError(f"buffer refused (HTTP {st}): {msg[:240]}")
    return r.get("data") or {}


def buffer_publish(store, j, acct, tx, url=None, tries=30, wait=10):
    """Owner-approved post through Buffer: re-check the live channel, create the post (or a Buffer draft), wait for it.
    A retry never creates a second post: once Buffer has given a post ID, only that post is followed."""
    f = j["fields"]
    pid = j["result"].get("buffer_post_id")
    if pid:
        _log(store, j["job_id"], "following the Buffer post created earlier (no second post)")
        return _buffer_wait(store, j, acct, tx, pid, tries, wait)
    con = C.CONNECTORS["buffer"]
    cached = store.pref(f"buffer_channel_{acct['account_id']}") or {}
    org = cached.get("organization_id")
    if not org:
        orgs = _buffer(tx, "query { account { organizations { id } } }", {}, store).get("account", {}).get("organizations") or []
        org = orgs[0]["id"] if orgs else ""
    chans = _buffer(tx, """query($o: OrganizationId!) { channels(input: {organizationId: $o}) { id name service isLocked isDisconnected } }""",
                    {"o": org}, store).get("channels") or []
    ch = next((c for c in chans if c["service"] == acct["platform"] and C.same_handle(c["name"], acct.get("handle"))), None)
    if not ch or (cached.get("id") and cached["id"] != ch["id"]):
        raise RuntimeError(f"no Buffer channel for {acct['platform']} @{(acct.get('handle') or '').lstrip('@')}; check Buffer's connected channels")
    if ch.get("isDisconnected") or ch.get("isLocked"):
        raise RuntimeError(f"the Buffer channel @{ch['name']} is disconnected or locked; reconnect it in Buffer")
    video = {"url": url or f["video_url"], **({"metadata": {"thumbnailOffset": int(f["cover_ms"])}} if f.get("cover_ms") else {})}
    meta = ({"tiktok": {"isAiGenerated": bool(f.get("is_aigc"))}} if acct["platform"] == "tiktok" else
            {"instagram": {"type": "reel", "shouldShareToFeed": f.get("share_to_feed", True) is not False, "isAiGenerated": bool(f.get("is_aigc"))}})
    draft = bool(f.get("buffer_draft"))
    inp = {"channelId": ch["id"], "text": f.get("caption", ""), "assets": [{"video": video}], "metadata": meta,
           "schedulingType": "automatic", "mode": "addToQueue" if draft else "shareNow", "needsApproval": False,
           "source": "slugshot-dashboard", **({"saveToDraft": True} if draft else {})}
    r = _buffer(tx, BUFFER_CREATE, {"i": inp}, store).get("createPost") or {}
    if r.get("__typename") != "PostActionSuccess":
        raise RuntimeError(f"Buffer didn't create the post ({r.get('__typename', 'no answer')}): {r.get('message', '')[:240]}")
    pid = r["post"]["id"]
    _set(store, j["job_id"], result={**j["result"], "buffer_post_id": pid})
    if draft:
        return {"state": "in_buffer_drafts", "buffer_post_id": pid}
    return _buffer_wait(store, j, acct, tx, pid, tries, wait)


def _buffer_wait(store, j, acct, tx, pid, tries, wait):
    _set(store, j["job_id"], state="processing")
    status = ""
    for _ in range(tries):
        p = _buffer(tx, BUFFER_POST, {"i": {"id": pid}}, store).get("post") or {}
        status = p.get("status", "")
        if status == "error":
            raise RuntimeError(f"Buffer couldn't post it: {((p.get('error') or {}).get('message') or 'no reason given')[:240]}")
        if status == "sent":
            vid = next((m.group(1) for rx in VIDEO_ID[acct["platform"]] for m in [re.search(rx, p.get("externalLink") or "")] if m), None)
            if vid:
                return {"state": "done", "platform_video_id": vid, "url": p["externalLink"], "buffer_post_id": pid,
                        "published_at_utc": p.get("sentAt") or now_iso(), "source": "publish:buffer"}
            return {"state": "processing", "buffer_post_id": pid, "note": "Buffer sent it but gave no link yet; mark it posted with the link"}
        time.sleep(0 if isinstance(tx, FixtureTransport) else wait)
    return {"state": "processing", "buffer_post_id": pid, "buffer_status": status or "unknown",
            "note": "still sending in Buffer; mark it posted with the link once it's live"}


def _transport():
    return FixtureTransport() if os.environ.get("SLUGSHOT_DASH_FIXTURE") else Transport()


class FixtureTransport:
    """Offline stand-in for tests and `ss dash demo`: answers like the APIs do and records every call."""

    def __init__(self, inbox_status="SEND_TO_USER_INBOX", identity=None, credit_pct=1.6):
        self.credit_pct = credit_pct
        self.identity = identity or {"youtube": "@ronin_jt", "tiktok": ".roni_jt"}
        self.calls = []
        self.inbox_status = inbox_status
        self.received = 0

    def request(self, method, url, headers=None, data=None, timeout=0):
        self.calls.append((method, url.split("?")[0], dict(headers or {}), len(data or b"")))
        h = headers or {}
        if "upload/youtube" in url and method == "POST":
            return 200, {"location": "https://fixture.invalid/yt-session"}, b"{}"
        if url.startswith("https://fixture.invalid/yt-session"):
            total = int(h["Content-Range"].split("/")[1])
            if h.get("Content-Length") == "0":
                return (308, {"range": f"bytes=0-{self.received - 1}"} if self.received else {}, b"")
            self.received = int(h["Content-Range"].split(" ")[1].split("-")[1].split("/")[0]) + 1
            if self.received >= total:
                return 201, {}, json.dumps({"id": "FXyt0000001", "status": {"privacyStatus": "private", "uploadStatus": "uploaded"}}).encode()
            return 308, {"range": f"bytes=0-{self.received - 1}"}, b""
        if "api.cloudinary.com" in url and url.endswith("/video/upload"):
            self.hosted_uploads = getattr(self, "hosted_uploads", 0) + 1
            pid = re.search(rb'name="public_id"\r\n\r\n([^\r]+)', data or b"").group(1).decode()
            size = len(data.split(b"video/mp4\r\n\r\n", 1)[1].rsplit(b"\r\n--", 1)[0])
            return 200, {}, json.dumps({"public_id": pid, "version": 1700000000, "format": "mp4", "type": "authenticated",
                                        "bytes": size, "resource_type": "video"}).encode()
        if url.startswith("https://res.cloudinary.com/"):
            return 206, {}, b"\x00"
        if url.startswith("https://fixture.invalid/tt-upload"):
            last = int(h["Content-Range"].split("-")[1].split("/")[0])
            return (201 if last + 1 == int(h["Content-Range"].split("/")[1]) else 206), {}, b""
        return 404, {}, b"{}"

    def json(self, method, url, body=None, headers=None, form=None):
        self.calls.append((method, url.split("?")[0], body if body is not None else {k: v for k, v in (form or {}).items() if k != "access_token"}, 0))
        if "upload/youtube" in url:
            st, hd, _ = self.request(method, url, headers)
            return st, hd, {}
        if "api.cloudinary.com" in url and url.endswith("/usage"):
            return 200, {}, {"plan": "Free", "last_updated": "2026-11-25", "credits": {"usage": 0.4, "limit": 25, "used_percent": self.credit_pct},
                             "storage": {"usage": 1000}, "bandwidth": {"usage": 0}, "transformations": {"usage": 2},
                             "media_limits": {"video_max_size_bytes": 104857600}}
        if "api.cloudinary.com" in url and url.endswith("/video/destroy"):
            self.destroyed = getattr(self, "destroyed", []) + [(form or {}).get("public_id")]
            return 200, {}, {"result": "ok"}
        if url == C.BUFFER:
            q = (body or {}).get("query", "")
            if "organizations" in q:
                return 200, {}, {"data": {"account": {"organizations": [{"id": "org-fixture"}]}}}
            if "channels(" in q:
                return 200, {}, {"data": {"channels": [
                    {"id": "ch-tt-en", "name": self.identity["tiktok"], "service": "tiktok", "isLocked": False, "isDisconnected": False},
                    {"id": "ch-ig-en", "name": "1roni_jt", "service": "instagram", "isLocked": False, "isDisconnected": False}]}}
            if "createPost" in q:
                self.last_channel = body["variables"]["i"]["channelId"]
                return 200, {}, {"data": {"createPost": {"__typename": "PostActionSuccess", "post": {"id": "bufpost-1", "status": "sending"}}}}
            if "post(" in q:
                link = ("https://www.instagram.com/reel/FXreel002/" if getattr(self, "last_channel", "") == "ch-ig-en"
                        else "https://www.tiktok.com/@.roni_jt/video/7400000000000000001")
                return 200, {}, {"data": {"post": {"id": "bufpost-1", "status": "sent", "sentAt": now_iso(), "externalLink": link}}}
        if "youtube/v3/channels" in url:
            return 200, {}, {"items": [{"id": "UCfixture", "snippet": {"customUrl": self.identity["youtube"]}}]}
        ok = {"error": {"code": "ok"}}
        if url.endswith("/creator_info/query/"):
            return 200, {}, {**ok, "data": {"creator_nickname": "Roni (fixture)", "creator_username": self.identity["tiktok"],
                                            "privacy_level_options": ["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"],
                                            "comment_disabled": False, "duet_disabled": True, "stitch_disabled": False,
                                            "max_video_post_duration_sec": 600}}
        if url.endswith("/video/init/"):
            return 200, {}, {**ok, "data": {"publish_id": "v_pub_fixture_1", "upload_url": "https://fixture.invalid/tt-upload"}}
        if url.endswith("/status/fetch/"):
            d = {"status": self.inbox_status}
            if self.inbox_status == "PUBLISH_COMPLETE":
                d["publicaly_available_post_id"] = [7000000000000000001]
            return 200, {}, {**ok, "data": d}
        if url.endswith("/media"):
            return 200, {}, {"id": "17900000000000001"}
        if url.endswith("/media_publish"):
            return 200, {}, {"id": "17800000000000001"}
        if "/me" in url:
            return 200, {}, {"user_id": "17841400000000001"}
        if "1790000" in url:
            return 200, {}, {"status_code": "FINISHED"}
        if "1780000" in url:
            return 200, {}, {"permalink": "https://www.instagram.com/reel/FIXTURE/", "timestamp": now_iso()}
        return 404, {}, {}


def accounts_view(store):
    out = []
    for a in store.accounts():
        if a["platform"] not in PLATFORMS:
            continue
        st, msg = credential(store, a)
        buf = "buffer" in ROUTES[a["platform"]] and credential(store, a, "buffer")[0] == "ready"
        if st != "ready" and buf:
            st, msg = "ready", "via Buffer"  # e.g. Instagram: its own API is deferred, Buffer posts for it
        out.append({**a, "routes": list(ROUTES[a["platform"]]), "credential": st, "credential_note": msg, "buffer": buf})
    return out
