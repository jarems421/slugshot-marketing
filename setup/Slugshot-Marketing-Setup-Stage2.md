> **Setup note, 2026-11-24.** Kept for reference; the README is current. This workspace (`slugshot marketing`) is the tools workspace, not `%USERPROFILE%\Slugshot-Marketing-Tools`. Python 3.13 was already installed, so the venv is `.venv` on 3.13 (openai-whisper 20250625 supports it) rather than `whisper-env` on 3.11. Remotion was set up as a small hand-written composition in `remotion/` instead of the `create-video --tiktok` template, because that template brings its own whisper.cpp transcription (a second pipeline). MakeMyClip was reviewed and pinned locally at 0.5.2 instead of run through `npx -y`.

# Slugshot marketing tools — stage 2 (Windows)

Run the accompanying CMD file first, review all installer prompts, and open a **new Command Prompt** afterwards. No API key is required. These commands have been prepared but not executed on your computer.

## 1. Verify prerequisites

```bat
ffmpeg -version
py -3.11 --version
node --version
npm --version
git --version
```

MakeMyClip requires Node 24 or later; update Node if necessary. If any command fails, resolve the relevant installation before proceeding.

## 2. Install Whisper in an isolated environment

```bat
cd /d "%USERPROFILE%\Slugshot-Marketing-Tools"
py -3.11 -m venv whisper-env
whisper-env\Scripts\python.exe -m pip install --upgrade pip
whisper-env\Scripts\python.exe -m pip install openai-whisper
whisper-env\Scripts\whisper.exe --help
```

Test with an actual narration file:

```bat
whisper-env\Scripts\whisper.exe "C:\path\to\narration.mp3" --model base.en --output_format srt --device cpu --fp16 False
```

The model is downloaded on first use. This is a CPU baseline, not a GPU-optimized installation.
Source: https://github.com/openai/whisper

## 3. Create the Remotion project

From the tools workspace:

```bat
cd /d "%USERPROFILE%\Slugshot-Marketing-Tools"
npx create-video@latest --tiktok
```

When prompted, use `slugshot-video-templates` as the project name. Review the prompts and choose npm. Skip extra agent skills for now if offered. Follow the scaffolder's printed instructions to open the project and run `npm run dev`. Check licensing at https://www.remotion.dev/docs/license/pricing (free for eligible individuals and teams up to three people).
Source: https://www.remotion.dev/templates/tiktok

## 4. Evaluate MakeMyClip (third-party, not yet audited)

```bat
cd /d "%USERPROFILE%\Slugshot-Marketing-Tools"
git clone https://github.com/MakeMyClip/editor.git makemyclip-source
```

Review the README, licence, package.json, dependency and install scripts before executing this package. This is a relatively new third-party tool; do not grant it access to your game repository, secrets, or entire home directory. Once reviewed and approved, the documented npm entry point is `npx @makemyclip/editor`; use the project's current instructions to configure the CLI and optionally its MCP server in local Codex. Keep the MCP workspace scoped to a dedicated marketing footage directory. Do not connect it to the web chat by pasting credentials.
Source: https://github.com/MakeMyClip/editor

## 5. Optional manual editor

DaVinci Resolve Free: https://www.blackmagicdesign.com/uk/products/davinciresolve — choose the free version, not Studio. Its vendor download flow may request registration. It overlaps with Kdenlive, so install only if you want it.

## 6. First smoke test

- Record a 20-second Roblox clip with OBS.
- Open and export it in Kdenlive, using a vertical project.
- Transcribe a short voiceover with Whisper and inspect the SRT.
- Open the Remotion template in Studio and render a sample.
- Test MakeMyClip only after reviewing the repository, using disposable footage.

None of these steps requires an additional paid subscription for the intended eligible usage. Local disk space, model downloads and dependencies still apply.
