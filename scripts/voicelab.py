r"""Local expressive TTS (Qwen3-TTS, Apache-2.0) for scripts/dialogue.py. Runs in .venv-voicelab (CUDA torch).

  .venv-voicelab\Scripts\python scripts\voicelab.py qwen jobs.json --refs assets\voices [--mode design|clone]

jobs.json: [{text, out, design, direction, speaker, language}]
  design  each line is made from the character's description plus the line's (direction): the most expressive
  clone   each character's reference clip (assets/voices/<SPEAKER>.wav, designed once from its description and
          reused) is cloned for every line: the most consistent voice, less control over delivery

Original voices only: references are designed from text descriptions, never recorded from real people.
Seeds are fixed per line, so re-running a job reproduces the same take. Writes <out>.json beside each wav
with generation time; prints peak VRAM.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import soundfile as sf
import torch

ROOT = Path(__file__).resolve().parent.parent

DESIGN = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
BASE = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"


def load(name):
    from qwen_tts import Qwen3TTSModel
    return Qwen3TTSModel.from_pretrained(name, device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa")


class Embedder:
    """Speaker fingerprints from the Base model's speaker encoder, run on the CPU (only Base has one, and both 1.7B
    models together don't fit 8 GB of VRAM). Cosine similarity of two fingerprints = how alike two voices are."""

    def __init__(self):
        from qwen_tts import Qwen3TTSModel
        base = Qwen3TTSModel.from_pretrained(BASE, device_map="cpu", dtype=torch.bfloat16)
        self.encoder = base.model.speaker_encoder.float().eval()
        del base

    @torch.inference_mode()
    def __call__(self, wav, sr):
        import librosa
        import numpy as np
        from qwen_tts.core.models.modeling_qwen3_tts import mel_spectrogram
        wav = np.asarray(wav, dtype=np.float32)
        if wav.ndim > 1:
            wav = wav.mean(axis=1)
        if sr != 24000:
            wav = librosa.resample(y=wav, orig_sr=sr, target_sr=24000)
        mels = mel_spectrogram(torch.from_numpy(wav).unsqueeze(0), n_fft=1024, num_mels=128, sampling_rate=24000,
                               hop_size=256, win_size=1024, fmin=0, fmax=12000).transpose(1, 2)
        e = self.encoder(mels.float())[0]
        return (e / e.norm()).flatten()

    def file(self, path):
        wav, sr = sf.read(str(path))
        return self(wav, sr)


def center(vecs):
    """Remove what every voice shares (the set's mean), so differences between voices dominate the score."""
    mean = torch.stack(vecs).mean(0)
    return [(v - mean) / (v - mean).norm() for v in vecs]


def similarity(paths):
    emb = Embedder()
    vecs = center([emb.file(p) for p in paths])
    names = [Path(p).parent.parent.name[-6:] + "/" + Path(p).stem for p in paths]
    for n, a in zip(names, vecs):
        print(f"{n[:28]:28}", " ".join(f"{float(a @ b):5.2f}" for b in vecs))


def instruct(job):
    d = job["design"]
    return f"{d} Delivery for this line: {job['direction']}." if job.get("direction") else d


def cast(a):
    """Design each character's fixed reference voice: `--candidates` takes per character from its description reading
    its sample line, fingerprinted; the take most distinct from the other characters becomes
    assets/voices/<NAME>.wav (+ .txt). All takes stay in assets/voices/candidates/ so the owner can swap one by ear
    (copy it over <NAME>.wav). Existing references are kept unless --redo names them."""
    import shutil
    chars = json.loads((ROOT / "config" / "cast.json").read_text(encoding="utf-8"))["characters"]
    refs, cand_dir = Path(a.refs), Path(a.refs) / "candidates"
    cand_dir.mkdir(parents=True, exist_ok=True)
    todo = [n for n, c in chars.items() if c.get("qwen", {}).get("sample")
            and (n in (a.redo or []) or not (refs / f"{n}.wav").exists())]
    design = load(DESIGN)
    takes = {}
    for n in todo:
        q = chars[n]["qwen"]
        for k in range(a.candidates):
            torch.manual_seed(a.seed + 101 * k)
            s = time.time()
            wavs, sr = design.generate_voice_design(text=q["sample"], instruct=q["design"], language="English")
            path = cand_dir / f"{n}_{k + 1}.wav"
            sf.write(path, wavs[0], sr)
            takes.setdefault(n, []).append(path)
            print(f"{path.name} {len(wavs[0]) / sr:.1f}s in {time.time() - s:.0f}s", flush=True)
    del design
    torch.cuda.empty_cache()
    # fingerprint every take of every character (existing references too, so new ones are judged against them)
    emb = Embedder()
    pool = {n: takes.get(n) or [refs / f"{n}.wav"] for n in chars if takes.get(n) or (refs / f"{n}.wav").exists()}
    vecs = {p: emb.file(p) for paths in pool.values() for p in paths}
    centred = dict(zip(vecs, center(list(vecs.values()))))
    report = {}
    for n in todo:
        def closest_other(p):
            return max(float(centred[p] @ centred[q]) for m, qs in pool.items() if m != n for q in qs)
        scores = {p.name: round(closest_other(p), 3) for p in pool[n]}
        best = min(pool[n], key=closest_other)
        shutil.copyfile(best, refs / f"{n}.wav")
        (refs / f"{n}.txt").write_text(chars[n]["qwen"]["sample"], encoding="utf-8")
        report[n] = {"chosen": best.name, "closest_other_character": scores}
        print(f"{n}: chose {best.name} (similarity to the nearest other character: {scores[best.name]:+.2f})")
    (refs / "cast-report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")


def main():
    torch.set_grad_enabled(False)
    if len(sys.argv) > 1 and sys.argv[1] == "similarity":
        return similarity(sys.argv[2:])
    if len(sys.argv) > 1 and sys.argv[1] == "cast":
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--refs", default=str(ROOT / "assets" / "voices"))
        ap.add_argument("--candidates", type=int, default=3)
        ap.add_argument("--redo", nargs="*")
        ap.add_argument("--seed", type=int, default=7)
        return cast(ap.parse_args())
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("engine", choices=["qwen"])
    ap.add_argument("jobs")
    ap.add_argument("--refs", default="assets/voices")
    ap.add_argument("--mode", choices=["design", "clone"], default="clone")
    ap.add_argument("--takes", type=int, default=2, help="clone: takes per line; the one closest to the reference wins")
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    jobs = json.loads(Path(a.jobs).read_text(encoding="utf-8-sig"))
    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    refs = {}
    if a.mode == "clone":
        for job in jobs:
            ref = Path(a.refs) / f"{job['speaker']}.wav"
            if not ref.exists():
                raise SystemExit(f"no reference voice for {job['speaker']}: run `ss cast` first")
            refs[job["speaker"]] = ref
        model = load(BASE)
        prompts = {sp: model.create_voice_clone_prompt(ref_audio=str(r), ref_text=r.with_suffix(".txt").read_text(encoding="utf-8"))
                   for sp, r in refs.items()}
        target = {sp: model.model.extract_speaker_embedding(*_load24(r)).flatten().float() for sp, r in refs.items()}
    else:
        design = load(DESIGN)
    print(f"loaded model in {time.time() - t0:.1f}s", flush=True)

    for i, job in enumerate(jobs):
        s = time.time()
        if a.mode == "design":
            torch.manual_seed(a.seed + i)
            wavs, sr = design.generate_voice_design(text=job["text"], instruct=instruct(job), language=job["language"])
            best, sim = wavs[0], None
        else:
            best, sim = None, -2.0
            for k in range(a.takes):
                torch.manual_seed(a.seed + i * 17 + k)
                wavs, sr = model.generate_voice_clone(text=job["text"], language=job["language"], voice_clone_prompt=prompts[job["speaker"]])
                import librosa
                w24 = librosa.resample(y=wavs[0].astype("float32"), orig_sr=sr, target_sr=24000) if sr != 24000 else wavs[0].astype("float32")
                e = model.model.extract_speaker_embedding(w24, 24000).flatten().float()
                score = float(torch.nn.functional.cosine_similarity(e, target[job["speaker"]], dim=0))
                if score > sim:
                    best, sim = wavs[0], score
        out = Path(job["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        sf.write(out, best, sr)
        took = time.time() - s
        out.with_suffix(".json").write_text(json.dumps({"seconds": round(took, 2), "audio": round(len(best) / sr, 2), "mode": a.mode,
                                                        "reference_similarity": None if sim is None else round(sim, 3)}), encoding="utf-8")
        print(f"{out.name} {len(best) / sr:.2f}s audio in {took:.1f}s" + ("" if sim is None else f", voice match {sim:.3f}"), flush=True)
    print(f"peak VRAM {torch.cuda.max_memory_allocated() / 2**30:.2f} GiB, total {time.time() - t0:.1f}s")


def _load24(path):
    import librosa
    wav, sr = sf.read(str(path))
    wav = wav.mean(axis=1) if wav.ndim > 1 else wav
    if sr != 24000:
        wav = librosa.resample(y=wav.astype("float32"), orig_sr=sr, target_sr=24000)
    return wav.astype("float32"), 24000


if __name__ == "__main__":
    sys.exit(main())
