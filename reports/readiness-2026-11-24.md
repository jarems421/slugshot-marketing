# Readiness report: Claude Code production environment

Date: 2026-11-24. Final refinement phase: creative editing intelligence and operational readiness. No new software was installed in this phase: everything was built on Remotion, FFmpeg, Whisper and Kokoro, which were already in place. The game repo was not modified, and no dashboard, Gemini configuration or AI agents were added.

## What changed in this phase

| Item | Result |
|---|---|
| Creative editing skill | `.claude/skills/slugshot-video-editing/`: a router plus six references (script-to-edit, pacing/cuts/zooms, captions/hierarchy, audio design, format playbooks, review and approval). Built on the research PDF; every rule labelled A (official), B (research), C (creator practice), D (our hypothesis) or S (Slugshot result, none yet). It complements the Remotion skill and doesn't repeat its API documentation. |
| Skill in use | Reviewed a real multi-scene render. It caught three problems the technical QC passed: duplicate captions, a muted-viewer gap and a double CTA. Fixed in V02, with two new rules added to the skill ([record](skill-review-2026-11-24.md)). |
| Multi-scene assembly | `ss assemble` + Remotion `Story` composition: video (MP4/MOV, MKV auto-remuxed), PNG/JPG stills, text cards, recorded WAV or approved script -> Kokoro, voice tidy, ducked music, timed SFX, captions with emphasis words, punch-ins, push-ins, fade-ins, per-scene labels, and scenes timed to the script's blocks from Whisper word timings. |
| Template refactor | Shared parts (`remotion/parts.tsx`) for both compositions; emphasis words; captions hidden on cards; label positions. |
| Gemini hand-off | `ss candidates`: Gemini CSV -> padded review clips with burned-in source timecode + `index.csv` for the human check. |
| Review aid | `ss sheet`: frame sheets that Claude and people can scan. |
| YouTube data | Reports now go to `data/local/reports/` with an internal-only banner. Nothing from the API reaches `exports/share/`; `ss export` no longer points to it. |
| Docs | [COMMANDS.md](../docs/COMMANDS.md) (every command: inputs, outputs, limits), [flow-and-gemini.md](../docs/flow-and-gemini.md), [INVENTORY.md](../docs/INVENTORY.md) readiness table, README and CLAUDE.md updated. |

## Production-readiness test (external asset types)

| Asset type | How it entered | Result |
|---|---|---|
| Gameplay recording (OBS-style MKV) | `ss import` -> `media/raw/...RAW.mkv` -> assemble (auto-remux) | rendered with trim, crop and punch-in |
| Externally generated MP4 (9:16 Flow stand-in with audio) | `media/flow/` -> assemble scene with "AI-generated scene" label and fade-in | rendered |
| PNG still | `media/flow/` -> image scene with push-in | rendered |
| WAV narration | Kokoro from the script (recorded WAV takes the `narration` key) -> tidy -> mix | rendered, -14 LUFS |
| Approved script | `jobs/scripts/sample-story.md` with [SCENE] blocks -> voice + scene timing | scene starts matched spoken lines |
| Gemini timestamps | sample CSV -> `ss candidates` | 2 clips + index; bad row skipped |

Stand-ins are clearly test material (Blender preview strip, generated gradient clip). The pipeline is proven; the content still needs real footage.

## Test results

`ss smoke`: **13/13 PASS** ([report](smoke-test.md)): tools, glossary, Whisper, Kokoro round trip, audio, FFmpeg render, Remotion render, multi-scene assembly, Gemini candidates, MakeMyClip, YouTube dry run, YouTube data kept internal, YouTube live call.

## Final audit

**Fully tested:** every `ss` command in [COMMANDS.md](../docs/COMMANDS.md); technical QC; MakeMyClip confinement; YouTube collection within policy limits; YouTube reports kept internal.

**Needs human creative approval every time:**
- whether an edit is funny, exciting or clear to a stranger;
- AI voice quality;
- music and SFX feel;
- which variant to post;
- the phone review;
- platform disclosures and audio rights at upload.

The skill makes Claude's reviews specific and honest about this limit. It doesn't replace the person.

**Depends on future footage or channel:**
- real gameplay through the whole chain;
- Gemini analysis of a real session;
- Flow clips made from approved reference stills;
- licensed music and SFX;
- own-channel retention and watch time (needs the channel);
- Roblox share-link acquisition (needs the published game);
- turning D rules into S rules (needs posting results).

**Still waiting on you:**
1. Regenerate and restrict the YouTube key, then `.\ss smoke`.
2. First OBS session; then `ss candidates` on Gemini's CSV and `ss assemble`.
3. Listen to the Kokoro samples and decide on the voice.
4. Licensed music/SFX into `assets/` with `LICENSES.csv` rows.
5. Optionally ask YouTube API support whether sharing public API stats with AI tools for internal analysis is allowed; until then, sharing stays disabled.

## Known limitations

- No crossfades between scenes (cuts and fade-from-black only). Add them if the skill's playbooks start calling for them.
- Scene timing from script blocks is proportional to word counts; adjust by hand when a beat must land on an exact word.
- The glossary misses large garbles; the low-confidence list flags them.
- Template fonts are system fonts (Arial Black). Brand fonts need a font file and the Remotion font setup.
