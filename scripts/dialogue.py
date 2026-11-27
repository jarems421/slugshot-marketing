r"""Character dialogue: a cast script -> one performance per line -> one timing manifest.

  .\ss dialogue jobs\dialogue\floppy-seven.txt [--engine kokoro|qwen] [--only 3] [--out out\dialogue\ID]

Script (UTF-8 text):
  # comments
  RAMMSTONE (smug, slow): So. You're the starter slug.
  [beat 0.8]                 silence before the next line (a held pause, never trimmed)
  FLOPPY (flat): Yep.
  [overlap 0.25]             the next line starts 0.25 s before this one ends (an interruption)
  NAME may be any key in config/cast.json. (direction) goes to engines that take delivery instructions.
  Default gap between lines is 0.25 s.

Writes to out/dialogue/<id>/:
  lines/NN_NAME.wav     each line as performed (Gemini: TTS edge padding trimmed; cast tempo applied, pitch kept)
  dialogue.wav          the lines placed on one timeline (48 kHz mono, about -16 LUFS)
  dialogue.json         THE timing source: per line speaker, actor, start/end, script words with measured
                        times, a 30 fps mouth envelope, and deviations between script and performance
  dialogue.srt / dialogue.words.json   captions in the approved script's words (Remotion format, + speaker)
  timing.md             a readable table for review

Captions use the approved script's words; Whisper only supplies their timing and flags lines where the
performance differs from the script (dropped, added or changed words). Nothing is force-matched.
`--only N` re-performs one line and keeps the others (revision without redoing everything).
Gemini, one take, full run: consecutive lines with the same speaker and identical (direction), with no [overlap]
between them, share one request (100 a day on Tier 1) and are cut back into per-line files at the measured pauses;
a read that doesn't match the script falls back to one request per line.
"""
import argparse
import difflib
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np

import glossary

ROOT = Path(__file__).resolve().parent.parent
CAST = json.loads((ROOT / "config" / "cast.json").read_text(encoding="utf-8"))["characters"]
PY_TTS = ROOT / ".venv-tts" / "Scripts" / "python.exe"
PY_LAB = ROOT / ".venv-voicelab" / "Scripts" / "python.exe"
RATE = 48000
FPS = 30
LINE = re.compile(r"^\s*([A-Z][A-Z0-9_ ]*?)\s*(?:\(([^)]*)\))?\s*:\s*(.+)$")
DIRECTIVE = re.compile(r"^\s*\[(beat|overlap)\s+([0-9.]+)\s*\]\s*$", re.I)


def parse(path):
    lines, gap = [], None
    for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        d = DIRECTIVE.match(raw)
        if d:
            gap = float(d.group(2)) * (-1 if d.group(1).lower() == "overlap" else 1)
            continue
        m = LINE.match(raw)
        if not m:
            raise SystemExit(f"can't read script line: {raw!r} (expected NAME (direction): text)")
        name = m.group(1).strip()
        if name not in CAST:
            raise SystemExit(f"{name} is not in config/cast.json")
        if lines:
            lines[-1]["gap_after"] = 0.25 if gap is None else gap
        lines.append({"speaker": name, "direction": (m.group(2) or "").strip(), "text": m.group(3).strip()})
        gap = None
    if not lines:
        raise SystemExit("no dialogue lines found")
    lines[-1]["gap_after"] = 0.0 if gap is None else gap
    return lines


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, args)], check=True)


def read_pcm(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(RATE), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def liveliness(path):
    """How animated a read is: its pitch range in semitones (10th to 90th percentile of voiced frames) plus how much
    its loudness moves (dB spread), half weighted. Flat reads score low."""
    import wave
    with wave.open(str(path)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float) / 32768
    n, hop = int(0.04 * sr), int(0.01 * sr)
    f0, db = [], []
    lo, hi = int(sr / 400), int(sr / 70)
    for s in range(0, len(x) - n, hop):
        seg = x[s:s + n] - x[s:s + n].mean()
        rms = np.sqrt((seg ** 2).mean())
        if rms < 0.02:
            continue
        db.append(20 * np.log10(rms))
        ac = np.correlate(seg, seg, "full")[n - 1:]
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.5 * ac[0]:
            f0.append(sr / k)
    if len(f0) < 5:
        return 0.0
    semis = 12 * np.log2(np.percentile(f0, 90) / np.percentile(f0, 10))
    return float(semis + 0.5 * (np.percentile(db, 90) - np.percentile(db, 10)))


def gemini_groups(lines):
    """Runs of consecutive lines one Gemini request can perform: same speaker, identical (direction), no
    [overlap] between them. Keeps every line's direction exact while saving requests (100 a day on Tier 1)."""
    groups = []
    for i, ln in enumerate(lines):
        prev = lines[i - 1] if i else None
        if (prev and groups and prev["speaker"] == ln["speaker"] and prev["direction"] == ln["direction"]
                and prev["gap_after"] >= 0):
            groups[-1].append(i)
        else:
            groups.append([i])
    return groups


def split_points(words, counts):
    """Cut times between the lines of one performed passage: the middle of the pause after each line's last
    word. `words` are the passage's aligned script words; None when a boundary has no audible pause."""
    cuts, k = [], 0
    for n in counts[:-1]:
        k += n
        end, start = words[k - 1]["end"], words[k]["start"]
        if start - end < 0.04:
            return None
        cuts.append(round((end + start) / 2, 3))
    return cuts


def perform_passage(group, lines, voice, style, work):
    """One request for several lines, cut back into per-line raw files at the pauses Whisper measures.
    False (nothing kept) when the read doesn't match the script, so the caller performs line by line."""
    import gemini_tts
    raw = work / "lines" / f"passage_{group[0] + 1:02}-{group[-1] + 1:02}.raw.wav"
    text = " ".join(lines[i]["text"] for i in group)
    seconds = gemini_tts.speak(glossary.tts_text(text), voice, style, raw)
    heard = transcribe([raw], [text], "small.en")[0]
    words, dev = align(text, heard, 0.0)
    cuts = None if dev else split_points(words, [len(lines[i]["text"].split()) for i in group])
    if cuts is None:
        print(f"lines {group[0] + 1}-{group[-1] + 1}: passage read didn't split cleanly ({'; '.join(dev) or 'no pause'}); "
              f"performing line by line", flush=True)
        raw.unlink(missing_ok=True)
        return False
    edges = [0.0, *cuts, seconds]
    for i, a, b in zip(group, edges, edges[1:]):
        ffmpeg("-i", raw, "-ss", f"{a:.3f}", "-to", f"{b:.3f}", lines[i]["_raw"])
    raw.unlink()
    print(f"lines {group[0] + 1}-{group[-1] + 1} ({lines[group[0]]['speaker']}, {voice}): one request, {seconds:.1f}s", flush=True)
    return True



def line_filters(pitch=0, tempo=1.0, trim=False):
    """FFmpeg filters for one performed line.
    trim: cut the TTS's own padding at the line's edges to 40 ms before and 80 ms after the voice (Gemini adds about
      0.3-0.5 s; 31 lines of it added about 20 s of dead air to pilot 01). Scripted pauses are [beat]s and gaps
      between lines, so nothing acted is removed.
    tempo: a character's pace (cast.json <engine>.tempo), pitch-preserving. The narrator's bright genre direction read
      at about 150 wpm against the genre's ~210 (owner, 2026-11-26).
    Then an even level per line without squashing delivery: a gentle peak-safe loudness match."""
    chain = []
    if trim:
        chain += ["silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.04", "areverse",
                  "silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.08", "areverse"]
    if pitch:
        chain.append(f"rubberband=pitch={2 ** (pitch / 12):.5f}:formant=preserved")
    if tempo and abs(tempo - 1.0) > 1e-3:
        chain.append(f"rubberband=tempo={tempo:.4f}:pitchq=quality:formant=preserved")
    return chain + ["highpass=f=70", "loudnorm=I=-17:TP=-2:LRA=15", f"aresample={RATE}"]

def perform(lines, engine, work, only, mode="design", takes=1):
    """Synthesise each line to lines/NN_NAME.wav (48 kHz mono, pitch applied, levelled but not compressed).
    Gemini, one take, full run: consecutive same-speaker, same-direction lines share one request."""
    jobs = []
    done = set()
    if engine == "gemini" and takes == 1 and not only:
        import gemini_tts
        (work / "lines").mkdir(parents=True, exist_ok=True)
        for group in (g for g in gemini_groups(lines) if len(g) > 1):
            first = lines[group[0]]
            g = CAST[first["speaker"]].get("gemini") or {}
            if not g.get("voice"):
                raise SystemExit(f"{first['speaker']} has no gemini.voice in config/cast.json")
            for i in group:
                lines[i]["file"] = work / "lines" / f"{i + 1:02}_{lines[i]['speaker']}.wav"
                lines[i]["_raw"] = work / "lines" / f"{i + 1:02}_{lines[i]['speaker']}.raw.wav"
                lines[i]["_pitch"] = g.get("pitch", 0)  # a character's fixed lift (cast.json gemini.pitch)
            if perform_passage(group, lines, g["voice"], gemini_tts.style_for(g, first["direction"]), work):
                done.update(i + 1 for i in group)
            else:
                for i in group:
                    del lines[i]["_raw"]
    for i, ln in enumerate(lines, 1):
        ln["file"] = work / "lines" / f"{i:02}_{ln['speaker']}.wav"
        if i in done or (only and i not in only and ln["file"].exists()):
            continue
        c = CAST[ln["speaker"]]
        raw = work / "lines" / f"{i:02}_{ln['speaker']}.raw.wav"
        if engine == "gemini":
            import gemini_tts
            g = c.get("gemini") or {}
            if not g.get("voice"):
                raise SystemExit(f"{ln['speaker']} has no gemini.voice in config/cast.json")
            style = gemini_tts.style_for(g, ln["direction"])
            ln["_raw"], ln["_pitch"] = raw, g.get("pitch", 0)
            if takes == 1:
                seconds = gemini_tts.speak(glossary.tts_text(ln["text"]), g["voice"], style, raw)
                print(f"line {i} ({ln['speaker']}, {g['voice']}): {seconds:.1f}s", flush=True)
                continue
            # Several takes, the liveliest kept (owner, 2026-11-25: voices "not engaging"): a TTS read varies a lot
            # from take to take, and a flat one sinks the line.
            got = []
            for k in range(takes):
                path = raw.with_name(f"{raw.stem}.t{k}.wav")
                secs = gemini_tts.speak(glossary.tts_text(ln["text"]), g["voice"], style, path)
                got.append((path, secs, liveliness(path)))
            mid = sorted(s for _, s, _ in got)[len(got) // 2]
            sane = [t for t in got if 0.6 * mid <= t[1] <= 1.6 * mid]  # a ramble or a repeated line runs long
            best = max(sane, key=lambda t: t[2])
            shutil.copyfile(best[0], raw)
            print(f"line {i} ({ln['speaker']}, {g['voice']}): {best[1]:.1f}s, take {got.index(best) + 1}/{takes} "
                  f"(liveliness {', '.join(f'{t[2]:.1f}' for t in got)})", flush=True)
            continue
        if engine == "kokoro":
            k = c.get("kokoro") or {"voice": "am_michael", "speed": 1.0}
            jobs.append({"text": ln["text"], "out": str(raw), "voice": k["voice"], "speed": k.get("speed", 1.0),
                         **({"blend": k["blend"]} if k.get("blend") else {})})
        else:
            q = c["qwen"]
            jobs.append({"text": glossary.tts_text(ln["text"]), "out": str(raw), "design": q["design"],
                         "direction": ln["direction"], "speaker": ln["speaker"], "language": "English"})
        ln["_raw"], ln["_pitch"] = raw, c.get(engine, {}).get("pitch", 0)
    if jobs:
        (work / "lines").mkdir(parents=True, exist_ok=True)
        batch = work / "tts_jobs.json"
        batch.write_text(json.dumps(jobs, indent=1), encoding="utf-8")
        if engine == "kokoro":
            cmd = [PY_TTS, ROOT / "scripts" / "voice.py", "--batch", batch]
        else:
            cmd = [PY_LAB, ROOT / "scripts" / "voicelab.py", "qwen", batch, "--refs", ROOT / "assets" / "voices", "--mode", mode]
        r = subprocess.run(list(map(str, cmd)), cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"{engine} failed:\n{(r.stderr or r.stdout)[-1500:]}")
    for ln in lines:
        if "_raw" not in ln:
            continue
        g = CAST[ln["speaker"]].get(engine) or {}
        chain = line_filters(ln["_pitch"], g.get("tempo", 1.0), trim=engine == "gemini")
        ffmpeg("-i", ln["_raw"], "-af", ",".join(chain), "-ac", "1", ln["file"])
        ln["_raw"].unlink(missing_ok=True)


def mouth_envelope(pcm):
    """0..1 openness per 1/30 s: RMS in a 40 ms window, normalised to the line's loud speech, with a fast
    attack and a slower release so the mouth doesn't chatter."""
    hop = RATE // FPS
    frames = int(np.ceil(len(pcm) / hop))
    win = int(RATE * 0.04)
    padded = np.pad(pcm, (win // 2, win))
    rms = np.array([np.sqrt(np.mean(padded[i * hop:i * hop + win] ** 2)) for i in range(frames)])
    loud = np.percentile(rms[rms > 0], 90) if np.any(rms > 0) else 1
    x = np.clip((rms / max(loud, 1e-6) - 0.12) / 0.88, 0, 1)
    out, v = [], 0.0
    for target in x:
        v += (target - v) * (0.75 if target > v else 0.35)
        out.append(round(float(v), 3))
    return out


NUMBERS = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven",
           "8": "eight", "9": "nine", "10": "ten", "100": "hundred"}


def norm(w):
    w = re.sub(r"[^a-z0-9']", "", w.lower())
    return NUMBERS.get(w, w)


def align(script_text, whisper_words, offset):
    """Script words with times from Whisper, matched by sequence alignment. Script words Whisper missed get
    times interpolated between neighbours and are flagged; words Whisper heard that aren't in the script are
    reported as deviations (and not captioned)."""
    script = script_text.split()
    heard = [w for w in whisper_words if norm(w["word"])]
    sm = difflib.SequenceMatcher(a=[norm(w) for w in script], b=[norm(w["word"]) for w in heard], autojunk=False)
    times = [None] * len(script)
    deviations = []
    for tag, a0, a1, b0, b1 in sm.get_opcodes():
        if tag == "equal":
            for k in range(a1 - a0):
                times[a0 + k] = (heard[b0 + k]["start"], heard[b0 + k]["end"])
        elif tag == "replace" and a1 - a0 == b1 - b0:
            for k in range(a1 - a0):  # same count: likely mis-recognition of the same word, keep the timing
                times[a0 + k] = (heard[b0 + k]["start"], heard[b0 + k]["end"])
            deviations.append(f"heard '{' '.join(w['word'].strip() for w in heard[b0:b1])}' for '{' '.join(script[a0:a1])}'")
        else:
            if a1 > a0:
                deviations.append(f"not heard: '{' '.join(script[a0:a1])}'")
            if b1 > b0:
                deviations.append(f"extra: '{' '.join(w['word'].strip() for w in heard[b0:b1])}'")
    known = [i for i, t in enumerate(times) if t]
    for i, t in enumerate(times):
        if t:
            continue
        before = max([k for k in known if k < i], default=None)
        after = min([k for k in known if k > i], default=None)
        lo = times[before][1] if before is not None else (heard[0]["start"] if heard else 0)
        hi = times[after][0] if after is not None else (heard[-1]["end"] if heard else lo + 0.3)
        times[i] = (lo, max(hi, lo + 0.05))
    return [{"text": w, "start": round(offset + s, 3), "end": round(offset + e, 3)} for w, (s, e) in zip(script, times)], deviations


def transcribe(files, texts, model_name):
    """Per line. The prompt is the line's own approved text: on clips this short, a general term list leaks
    into the output as invented words. Words Whisper is unsure of (p < 0.15) are dropped as likely inventions."""
    import whisper
    model = whisper.load_model(model_name, device="cpu")
    out = []
    for f, text in zip(files, texts):
        r = model.transcribe(str(f), word_timestamps=True, fp16=False, initial_prompt=text,
                             condition_on_previous_text=False, hallucination_silence_threshold=0.3)
        words = [w for seg in r["segments"] for w in seg.get("words", [])
                 if w.get("probability", 1) >= 0.15 and seg.get("no_speech_prob", 0) < 0.8]
        words, _ = glossary.fix_words(words)
        out.append(words)
    return out


def srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def caption_groups(words):
    """One caption per line when it has six words or fewer (a punchline stays whole); longer lines split into
    balanced groups, preferring breaks after punctuation. Never mixes speakers (called per line)."""
    pages = 1 if len(words) <= 6 else -(-len(words) // 5)
    size = -(-len(words) // pages)
    group = []
    for i, w in enumerate(words):
        group.append(w)
        left = len(words) - i - 1
        punct = w["text"][-1:] in ".,!?;:…"
        if left > 0 and len(group) >= size - (1 if punct else 0) and left >= 2:
            yield group
            group = []
    if group:
        yield group


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script")
    ap.add_argument("--engine", choices=["kokoro", "qwen", "gemini"], default="gemini",
                    help="gemini: fixed prebuilt voice per character + per-line style (needs GEMINI_API_KEY; config/voice-budget.json)")
    ap.add_argument("--mode", choices=["design", "clone"], default="clone",
                    help="qwen: clone (default) = each character's fixed reference voice from `ss cast`; design = a fresh "
                         "voice per line from the description (measured: the voice drifts between lines; tests only)")
    ap.add_argument("--only", type=int, nargs="*", help="re-perform only these line numbers (1-based)")
    ap.add_argument("--out", help="output folder (default out/dialogue/<script name>)")
    ap.add_argument("--whisper", default="small.en", help="checker model; small.en caught pronunciation faults base.en missed")
    ap.add_argument("--takes", type=int, default=1, help="Gemini takes per line; use 3 for a performance audition")
    a = ap.parse_args()
    if a.takes < 1:
        ap.error("--takes must be at least 1")
    script = Path(a.script)
    work = (Path(a.out) if a.out else ROOT / "out" / "dialogue" / script.stem).resolve()
    if not a.only and work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    lines = parse(script)
    perform(lines, a.engine, work, set(a.only or []), a.mode, a.takes)

    # Place lines on one timeline. Gaps are kept exactly: silence is part of the performance.
    t = 0.0
    pcms = []
    for ln in lines:
        pcm = read_pcm(ln["file"])
        pcms.append(pcm)
        ln["start"] = round(max(t, 0.0), 3)
        ln["end"] = round(ln["start"] + len(pcm) / RATE, 3)
        t = ln["end"] + ln["gap_after"]
    total = max(ln["end"] for ln in lines) + 0.3
    mix = np.zeros(int(total * RATE) + 1, dtype=np.float32)
    for ln, pcm in zip(lines, pcms):
        i = int(ln["start"] * RATE)
        mix[i:i + len(pcm)] += pcm
    peak = float(np.max(np.abs(mix))) or 1.0
    if peak > 0.98:
        mix *= 0.98 / peak
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "1",
                    "-i", "-", "-c:a", "pcm_s24le", str(work / "dialogue.wav")], input=mix.tobytes(), check=True)

    heard = transcribe([ln["file"] for ln in lines], [ln["text"] for ln in lines], a.whisper)
    manifest_lines, all_words, flagged = [], [], 0
    for i, (ln, pcm, h) in enumerate(zip(lines, pcms, heard), 1):
        words, dev = align(ln["text"], h, ln["start"])
        flagged += bool(dev)
        for w in words:
            all_words.append({**w, "speaker": ln["speaker"]})
        manifest_lines.append({
            "n": i, "speaker": ln["speaker"], "actor": CAST[ln["speaker"]].get("actor"), "text": ln["text"],
            "direction": ln["direction"], "start": ln["start"], "end": ln["end"], "gap_after": ln["gap_after"],
            "file": str(ln["file"].relative_to(ROOT)).replace("\\", "/"), "words": words,
            "mouth": mouth_envelope(pcm), "deviations": dev,
        })
    manifest = {"id": script.stem, "script": str(script).replace("\\", "/"), "engine": a.engine,
                "mode": a.mode if a.engine == "qwen" else None, "fps": FPS,
                "duration": round(total, 3), "audio": str((work / "dialogue.wav").relative_to(ROOT)).replace("\\", "/"),
                "lines": manifest_lines}
    (work / "dialogue.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")

    srt, caps = [], []
    for ml in manifest_lines:
        colour = CAST[ml["speaker"]].get("caption", "#ffffff")
        for g in caption_groups(ml["words"]):
            srt.append(f"{len(srt) + 1}\n{srt_time(g[0]['start'])} --> {srt_time(g[-1]['end'])}\n{' '.join(w['text'] for w in g)}\n")
        for k, w in enumerate(ml["words"]):
            caps.append({"text": (" " if caps else "") + w["text"], "startMs": round(w["start"] * 1000),
                         "endMs": round(w["end"] * 1000), "timestampMs": round((w["start"] + w["end"]) * 500),
                         "confidence": 1, "speaker": ml["speaker"], "color": colour, "lineStart": k == 0})
    (work / "dialogue.srt").write_text("\n".join(srt), encoding="utf-8")
    (work / "dialogue.words.json").write_text(json.dumps(caps, indent=1), encoding="utf-8")

    rows = ["| # | speaker | start | end | gap after | text | deviations |", "|---|---|---|---|---|---|---|"]
    for ml in manifest_lines:
        rows.append(f"| {ml['n']} | {ml['speaker']} | {ml['start']:.2f} | {ml['end']:.2f} | {ml['gap_after']:+.2f} | "
                    f"{ml['text']} | {'; '.join(ml['deviations']) or '-'} |")
    (work / "timing.md").write_text(f"# {script.stem} ({a.engine}, {total:.2f}s)\n\n" + "\n".join(rows) + "\n",
                                    encoding="utf-8")
    print(f"{work / 'dialogue.json'}: {len(lines)} lines, {total:.2f}s, engine {a.engine}")
    for ml in manifest_lines:
        if ml["deviations"]:
            print(f"  line {ml['n']} ({ml['speaker']}): " + "; ".join(ml["deviations"]))
    if flagged:
        print(f"{flagged} line(s) differ from the script: listen, then re-perform with --only N or accept.")


if __name__ == "__main__":
    main()
