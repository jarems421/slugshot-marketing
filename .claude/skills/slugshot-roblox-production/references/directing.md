# Directing scenes: shots, acting and timing

Craft rules for turning a script into a scene spec. Evidence labels as in slugshot-video-editing:
- **C**: established film/animation craft;
- **D**: our hypothesis;
- **S**: a Slugshot result.

"Observed" notes come from the 2026-11-25 benchmark (`docs/production-quality.md`).

## 1. Start from the beat table, not the camera

For every line, write down three things:
- who the audience should watch;
- what that character feels;
- what changes.

Each answer picks a shot and an acting beat. If a shot or beat has no answer, cut it. (C)

## 2. Vertical framing (9:16)

- **Side-on two-shots don't fit.** Observed: two slugs 3 studs apart framed from the side left one clipped and one out of frame. Establish with **depth staging**: one actor near the lens (over the shoulder), the other further back. (S)
- Close-ups:
  - `close_up` `size` 1.0-1.2 (the frame is about that many slug heights tall) for reactions and punchlines;
  - 1.3-1.5 for ordinary lines;
  - 0.95 for the final beat. Observed: 1.5 read loose at phone size. (S)
- Eyes sit in the upper-middle; the lower third stays clear for captions (`captionTop` about 0.7). (A: platform safe areas)
- Nothing important in the top 12% or the bottom 20% (platform UI).
- Foreground intrusion: if another actor's body clips the frame edge at the start of a push, swing `side` further away (observed fix: -18° to -38°).

## 3. Screen direction and eyelines

- Keep the camera on one side of the line between two talking characters (the 180° rule). (C)
- With our presets, for a line along X with the camera on +Z:
  - the left actor's `close_up` uses negative `side`, the right actor's uses positive;
  - `over_shoulder` uses `shoulder` 1.
  - Check one still per shot before filming.
- Angle the camera 20-30° off a face so the eyeline reads toward the other character. Look straight into the lens only for a deliberate fourth-wall beat (Floppy's payoff smile). (C)
- Listeners look at the speaker automatically. Override with `look` when a character should look away (avoidance, deadpan, to camera).

## 4. Acting vocabulary that reads on slugs

Slugs have no arms, so acting lives in head, body, eyes and timing:
- **Notice / smug**: `react` 1. Each species answers in character: Rammstone lifts his chin, Aquabeek gives a half-lidded tilt, Tormato bounces, Boon Doc nods.
- **Leaning in to threaten**: `lean` 1. **Thrown back**: `lean` -0.6 with `react` 0.
- **Anger** (Rammstone): `angry` 0.5-0.8, eased over 0.5 s or more. Let it build after the line, not during it.
- **Floppy's deadpan**: `squint` 0.4-0.6 (heavy lids), no smile, slow blinks. His payoff is `look` to a lens mark, then `smile` 1 eased 0.5 s after the line ends.
- **Entrances**: two small hops plus `move_to`, a heavy landing sound on each. A small slug hops lower (`height` 0.2-0.3).
- **Ease times**: 0.3-0.5 s for expressions. Faster reads as a twitch; slower reads as unmotivated. (D)

## 4b. Character truths (game catalog first, handbook archetypes as colour; `config/cast.json`)

- **Floppy:**
  - drowsy, slow, a little out of it, unbothered, with stubborn dignity;
  - his "wins" are attitude, timing or someone else's mistake, never power;
  - asleep = `squint` 2, groggy = 0.8-1, awake-ish = 0.4.
- **Rammstone:** loud swagger that cracks. Lean in to threaten, `angry` to shout, thrown back (`lean` -0.6) when rattled.
- **Aquabeek:** cool and dry. Half-lidded `react`; she looks away or to camera when unimpressed.
- **Tormato:** can't stay still. Frequent small hops; spinning eyes come from his idle.
- **Boon Doc:** gentle, fussy carer. `react` for his nod; quiet reactions.
- **Phosphoro:** curious. Small hops toward whatever's new; looks at things, not people.
- **Inferno:** playful flame with a temper. Excited `react` and a hop when he's the topic.
- **Background slugs** are actors too: give each a `phase` (so they don't breathe in sync), `auto_look: false`, and a beat or two of life. The game's own grove residents are hidden during takes because they run on real time.

## 5. Comic timing

- Silence is a beat. Script it (`[beat 1.1]`) and **hold on the listener's face** during it, not the speaker's. (C)
- The cut lands on the reaction, not before it: anchor `until` to `Ln.end+0.3` to `+0.55` so the silence plays on screen.
- Build-up is elaborate; the payoff is humble and quick. A long push-in ending on a small smile beats a whip pan. (C)
- Don't cover a punchline with music swells or whooshes. The SFX tells the punchline; it doesn't replace the pause.

## 6. Look (see slugshot-video-editing/references/visual-direction.md)

- Shoot real sets: the lobby's glowing portals, mushroom canopy and inked rock read as our world straight away.
- Depth of field is off while filming: it blurs small subjects and drops anti-aliasing.
- Characters always carry the charcoal ink outline (the runner adds it).
- Light per scene with `look.lighting` only when a beat calls for it (a dramatic lore beat), and restore it afterwards (the runner does).

## 7. Before filming: checklist

1. Stills at the first frame of each shot and at each punchline.
2. Nothing clipped at the frame edge; eyes upper-middle; eyelines correct.
3. Truth label set; canon clean; no game name visible on any prop while the reveal lock is on.
