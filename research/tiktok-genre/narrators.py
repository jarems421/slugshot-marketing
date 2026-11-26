"""Six narrator takes of one original In My World passage via Gemini TTS (spend guard + ledger in gemini_tts)."""
import json, os, shutil, sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\runni\slugshot marketing\scripts")
import gemini_tts
OUT = Path(r"C:\Users\runni\slugshot marketing\out\voices\narrator-test-2026-11-26")
TEXT = ("In my world, every slug picks its partner on the day it hatches. Some pick fire. Some pick water. "
        "You see, the whole town lines up at sunrise, and the slugs choose. Not you. The slugs. "
        "My best friend got picked in four seconds. My neighbour got picked before breakfast. "
        "And me? I waited until noon. Until one slug finally rolled over, opened one eye... "
        "and fell back asleep on my shoe. And that was the day he picked me.")
PACE = ("Fast-paced, continuous storytime narration at about 205 words per minute: keep sentences flowing with only "
        "short pauses between them, and one brief pause just before the final line.")
TAKES = [
    ("M1_Puck_fast", "Puck", "Energetic, charismatic young male storyteller, punchy emphasis, smiling. " + PACE),
    ("M2_Algieba_deep-dry", "Algieba", "Low, smooth male storyteller with a dry, deadpan, understated delivery and a hint of a smile; calm but never slow, never shouting. " + PACE),
    ("M3_Orus_low-calm", "Orus", "Deep, relaxed, confident male storyteller; calm and grounded, quietly amused, like telling a friend a story. " + PACE),
    ("F1_Sulafat_warm", "Sulafat", "Warm, calm young female storyteller, gently amused, close to the microphone; relaxed but quick. " + PACE),
    ("F2_Aoede_playful", "Aoede", "Bright, playful young female storyteller, teasing and lightly sarcastic, a grin you can hear. " + PACE),
    ("F3_Kore_dry", "Kore", "Low, smooth, confident young female storyteller with a dry, deadpan delivery; unbothered, quietly funny. " + PACE),
]
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "script.txt").write_text(TEXT + "\n", encoding="utf-8")
for name, voice, style in TAKES:
    secs = gemini_tts.speak(TEXT, voice, style, OUT / f"{name}.wav")
    print(f"{name}: {secs:.1f} s, {len(TEXT.split()) / secs * 60:.0f} words/min overall", flush=True)
json.dump([{"file": f"{n}.wav", "voice": v, "style": s} for n, v, s in TAKES], open(OUT / "takes.json", "w"), indent=1)
print(f"month spend so far ${gemini_tts.month_spend():.4f}")
