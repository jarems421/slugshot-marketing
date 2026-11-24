# Production tool research (2026-11-24)

Goal: find existing, free and maintained tools for the gaps in the Claude Code side, without duplicating what's already installed or adding subscriptions. Hardware: Windows 11, RTX 3070 (8 GB), Python 3.13, Node 24.

| Need | Chosen | Licence | Runs on | Status | Considered and not used |
|---|---|---|---|---|---|
| AI narration | **Kokoro-82M** via `kokoro-onnx` 0.6.1 | code MIT, weights Apache-2.0 | CPU, about real time | Installed in `.venv-tts`, tested (5 voices; Whisper round trip correct) | **Chatterbox** (Resemble AI, MIT, more expressive with an "exaggeration" control, watermarks output with PerTh): needs CUDA PyTorch (~3 GB); next step if Kokoro sounds flat. **XTTS-v2**: Coqui Public Model Licence is non-commercial, rejected. **F5-TTS**: code MIT but published weights reported non-commercial, rejected. **edge-tts**: unofficial use of a Microsoft service, rejected. **Windows SAPI**: robotic; used only for test narration |
| Voice clean-up, pause trimming, speed | **FFmpeg filters** (`highpass`, `afftdn`, `silenceremove`, `atempo`, `acompressor`, `loudnorm`) in `scripts/audio.py` | LGPL/GPL | CPU | Built and tested (12.7 s to 10.4 s, keeps 150 ms breaths) | **auto-editor**: duplicates MakeMyClip's silence removal. **DeepFilterNet**: stronger denoise, add only if mic recordings are noisy |
| Music ducking and SFX placement | **FFmpeg `sidechaincompress` + `adelay`** in `scripts/audio.py mix` | as above | CPU | Built and tested (music 13 dB lower under speech) | DAW or Kdenlive keyframes for hand-tuned mixes |
| Silence and retake removal on footage | **MakeMyClip** (already installed) `timeline silence` | MIT | CPU | Available | auto-editor (redundant) |
| Animated word-level captions | **Remotion `@remotion/captions`** (already installed) with Whisper word timings | Remotion licence | CPU | Built and tested (word highlight in the accent colour) | MakeMyClip captions (needs whisper.cpp, a second transcription engine); FFmpeg ASS (kept for plain phrase captions) |
| Editing-specific agent skill | **Remotion official skill** `remotion-best-practices` (copied from `remotion-dev/skills` at 89c8afa after review) | Remotion repo | n/a | Installed in `.claude/skills/` | **MakeMyClip skill**: runs an unpinned `npx -y` copy of a CLI that ignores its workspace limit; the MCP server is used instead. Community copies of Remotion skills on skills.sh: use the official one |
| Agent-driven timeline editing | **MakeMyClip MCP** (`.mcp.json`) | MIT | CPU | Configured; confinement tested | n/a |
| Batch rendering of variants | **Remotion CLI** driven by `scripts/batch.py` (one job file, many hooks/formats) | Remotion Free License | CPU, about 30 s per 13 s video | Built and tested (3 variants in 97 s) | Remotion Lambda (paid cloud), `@remotion/renderer` API (not needed at this volume) |
| Automated video/audio QC | **FFmpeg detection filters** (`blackdetect`, `freezedetect`, `silencedetect`, `ebur128`) + ffprobe in `scripts/qc.py` | as above | CPU | Built and tested on good and broken files | **QCTools** (BAVC, GPL): GUI for archive digitisation, more than needed. **eko/qc**: unverified maintenance. **VMAF**: needs a reference video, not relevant |
| Presets and assets | `config/formats.json` (7 formats), `config/glossary.json`, `assets/` + `assets/LICENSES.csv` | n/a | n/a | Built | Digital asset managers: unnecessary for one person |
| Long-session shot splitting (optional) | **PySceneDetect** (BSD-3) could cut a 30-minute OBS session into shots before Gemini screening | BSD-3 | CPU | Not installed (Gemini does the screening) | n/a |

## Licence notes that affect use

- **Remotion**: Free License for individuals and companies of up to 3 employees. Renders pass `--license-key=free-license` as Remotion's own skill instructs. A bigger company needs a paid Remotion licence.
- **Kokoro voices**: Apache-2.0 weights allow commercial use. Platforms may still require an AI-voice label (TikTok and Meta for realistic synthetic content). The research PDF recommends a human voice where it's better.
- **Chatterbox**, if added later, watermarks every file. That's fine, and useful for provenance.
- **Music and SFX**: none are bundled. Record each file you add in `assets/LICENSES.csv`. For trending sounds, use each platform's own library in its app (TikTok's Commercial Music Library for business accounts).

## Sources

- Kokoro / kokoro-onnx: https://pypi.org/project/kokoro-onnx/ , https://github.com/thewh1teagle/kokoro-onnx
- Chatterbox: https://resemble.ai/chatterbox , https://huggingface.co/ResembleAI/chatterbox
- Open TTS licence overview: https://pinggy.io/blog/best_open_source_self_hosted_text_to_speech_models/ , https://www.siliconflow.com/articles/best-open-source-text-to-speech-models
- Remotion agent skills: https://www.remotion.dev/docs/ai/skills , https://github.com/remotion-dev/skills
- auto-editor: https://github.com/wyattblue/auto-editor
- QC tools: https://github.com/bavc/qctools , https://pkg.go.dev/github.com/eko/qc
