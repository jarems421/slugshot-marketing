r"""Gemini TTS for `ss dialogue --engine gemini` (standard library only; REST `v1beta/interactions`).

Each character speaks in a fixed prebuilt voice (config/cast.json `gemini.voice`); the script's (direction) and the
character's base style go in the turn's `speech_metadata.style`, never in the spoken text. Inline tags such as
<laugh>, <sigh>, <gasp>, <short pause> may be written in a line and are spoken as sounds.

Key: GEMINI_API_KEY in .env (never printed). Spending guard (config/voice-budget.json):
  project_billing false  the key's Google project has no billing: free tier only (rate-limited; we back off and wait)
  project_billing true   every call's estimated cost is logged in data/local/spend/gemini_tts.jsonl and a call
                         that would take this month past monthly_cap_usd is refused
Audio is billed at about 25 tokens per second of speech (pricing page, 2026-11-25).
"""
import base64
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from research_common import env_value

ROOT = Path(__file__).resolve().parent.parent
BUDGET = ROOT / "config" / "voice-budget.json"
LEDGER = ROOT / "data" / "local" / "spend" / "gemini_tts.jsonl"
URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


def budget():
    return json.loads(BUDGET.read_text(encoding="utf-8"))["gemini_tts"]


def month_spend():
    if not LEDGER.exists():
        return 0.0
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return sum(r["usd"] for r in map(json.loads, LEDGER.read_text(encoding="utf-8").splitlines())
               if r["at"].startswith(month))


def estimate(text, seconds, b):
    """Rough cost: text tokens about chars/4; audio tokens 25 per second."""
    return len(text) / 4 / 1e6 * b["usd_per_m_input"] + seconds * 25 / 1e6 * b["usd_per_m_audio"]


def speak(text, voice, style, out, language="en"):
    """One line to `out` (WAV, 24 kHz mono 16-bit). Returns seconds of audio."""
    key = env_value("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is not set in .env (add it there or in the dashboard's Settings vault)")
    b = budget()
    if b["project_billing"]:
        guess = estimate(text, max(1.0, len(text) / 14), b)  # about 14 characters per second of speech
        if month_spend() + guess > b["monthly_cap_usd"]:
            raise SystemExit(f"Gemini TTS: this call would pass the ${b['monthly_cap_usd']:.2f} monthly cap "
                             f"(spent about ${month_spend():.2f}); raise it in config/voice-budget.json only with the owner's approval")
    content = {"type": "text", "text": text}
    if style:
        content["annotations"] = [{"type": "speech_metadata", "style": style}]
    body = {"model": b["model"], "input": [{"type": "user_input", "content": [content]}],
            "response_format": {"type": "audio"}, "generation_config": {"speech_config": [{"voice": voice}]}}
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST",
                                 headers={"x-goog-api-key": key, "Content-Type": "application/json"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:400]
            if e.code in (429, 500, 503) and attempt < 5:
                wait = 20 * (attempt + 1)
                print(f"Gemini TTS {e.code}; waiting {wait}s (free-tier rate limits are tight)", flush=True)
                time.sleep(wait)
                continue
            raise SystemExit(f"Gemini TTS failed ({e.code}): {msg}")
    audio = _find_audio(data)
    if not audio:
        raise SystemExit(f"Gemini TTS: no audio in the response (keys: {sorted(data)[:8]})")
    raw = base64.b64decode(audio)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if raw[:4] != b"RIFF":  # headerless L16: wrap it
        import wave
        with wave.open(str(out), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(raw)
    else:
        out.write_bytes(raw)
    seconds = (len(raw) - (44 if raw[:4] == b"RIFF" else 0)) / 48000
    if b["project_billing"]:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": b["model"],
                                "seconds": round(seconds, 2), "usd": round(estimate(text, seconds, b), 5)}) + "\n")
    return seconds


def _find_audio(data):
    """The audio's base64: steps[].content[] (type audio) in the REST response; output_audio.data in the SDK shape."""
    if isinstance(data.get("output_audio"), dict) and data["output_audio"].get("data"):
        return data["output_audio"]["data"]
    for step in data.get("steps", []) or data.get("outputs", []):
        for c in step.get("content", []) if isinstance(step, dict) else []:
            if c.get("type") == "audio" and c.get("data"):
                return c["data"]
    return None


def style_for(g, direction=""):
    """A line's style: the line's (direction), the character's style, then the shared storytime delivery
    (cast.json gemini_delivery; owner, 2026-11-25: voices should be more engaging)."""
    shared = json.loads((ROOT / "config" / "cast.json").read_text(encoding="utf-8")).get("gemini_delivery", "")
    if g.get("shared_delivery") is False:  # a character whose own style reads better alone (the narrator)
        shared = ""
    return ". ".join(x for x in (direction, g.get("style", ""), shared) if x)


def audition(only=None):
    """Each character's sample line in each candidate voice: out/voices/gemini/<NAME>_<voice>.wav (only: names;
    naming characters re-records their files, e.g. after a style change)."""
    cast = json.loads((ROOT / "config" / "cast.json").read_text(encoding="utf-8"))["characters"]
    out = ROOT / "out" / "voices" / "gemini"
    for name, c in cast.items():
        g, q = c.get("gemini"), c.get("qwen", {})
        if not g or not q.get("sample") or (only and name not in only):
            continue
        for v in g.get("candidates", [g["voice"]]):
            path = out / f"{name}_{v}.wav"
            if only or not path.exists():
                print(f"{path.name}: {speak(q['sample'], v, style_for(g), path):.1f}s", flush=True)


if __name__ == "__main__":
    if sys.argv[1:2] == ["audition"]:
        audition([n.upper() for n in sys.argv[2:]] or None)
    else:
        print(__doc__)
