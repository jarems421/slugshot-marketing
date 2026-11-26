# TikTok genre bank: working scripts (26 Nov 2026)

These scripts built the "In My World / In This Town" transcript bank and the narrator voice tests. They're kept so the next data pull can reuse them. They aren't `ss` commands: run them with `.venv\Scripts\python.exe` from the repo root, or with `.venv-voicelab` for `voices.py`/`gender.py`. They read `APIFY_TOKEN` and `GEMINI_API_KEY` from `.env` and never print them. Whisper needs FFmpeg on PATH: the WinGet FFmpeg folder, which `ss.ps1` resolves for you.

| Script | What it does |
|---|---|
| `apify.py`, `run.py` | Run `clockworks/tiktok-scraper` with a hard charge cap (min $0.50). Receipt and items go to `data/local/research/creative/tiktok-genre/apify-<label>-<run>/`. Usage: `run.py <label> <cap_usd> <payload.json>` |
| `inputs/*.json` | The payloads used: search and hashtag pool, creator back catalogues (`newestPostDate` for older posts), TOP downloads |
| `process.py` | Merges all runs, keeps in-format posts, fetches TikTok subtitle tracks, falls back to local Whisper output, and writes `pool.csv` |
| `whisper_run.py`, `savetop.py` | Transcribe or save downloaded videos (`media/research/tiktok-genre/`, ignored) |
| `build.py` | TOP/MID/FLOP-50 tiers (5+ days old, Roblox-tagged, English speech, at most 4 per creator), OTHER-A…F files, `ALL-POSTS.csv`, and a copy to Downloads |
| `speed.py`, `measure.py` | Narration pace (words a minute), gaps and pitch |
| `voices.py`, `gender.py` | Voice measurements and fingerprints. Gender by fingerprint failed on TikTok audio because music masks it |
| `narrators.py`, `instory.py` | Gemini narrator takes, and the In My World sample voiced with each narrator |

Results: `exports/share/research/tiktok-in-my-world-2026-11-26/`, with a copy in the owner's Downloads folder. Pace finding: `docs/production-quality.md`. Permission basis (owner-asserted TikTok approval for Apify Actors): `data/local/research/creative/tiktok-genre/README.md`.

Costs on 26 Nov: Apify about $4.40 of the $5 monthly Free credit (cycle ends 25 Dec). Each result costs about $0.0037; TikTok's subtitle tracks are free; video downloads cost $0.0013 each.
