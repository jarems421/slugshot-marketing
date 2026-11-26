# Sets: where scenes can be filmed (scouted 2026-11-26 in the marketing place)

The world is built at play time (HubArt about 2 min, Training about 3.5 min); in Edit mode the workspace is empty, so scout in a playtest. Marks are relative to a spec's `set.origin`, so one spec can span sets: write marks as (set origin - spec origin) + local position, and move actors between sets with an instant `move_to` (`duration: 0.02`) exactly on a cut.

| Set | World origin | Floor | Look | Good for |
|---|---|---|---|---|
| **Hub plaza** (spawn island) | (19, 0, 20) | y 0 (hub-rock.Top) | The best-looking set: glowing mushrooms, portals, lava arches, waterfalls, bridges | social scenes, setup, endings. Clear duel lane along -Z from (17, 0, 16) to (21, 0, -4); the west side (x 10-14) is open for fire lanes, the east has rope posts |
| **Training arena** (floating island) | (6000, 0, 0) | y 0 (TrainingSolids.Footing), about 300 x 300 open | Dark purple stone and mist against a black void (the game's own arena light), cover blocks, grey R6 training dummies, target boards, a green portal | duels, practice, montage. Actors read well at medium and wide (checked); keep marks clear of the dummies |
| **Cinder Rift** (1v1 PvP greybox) | (-6000, ~0, 0) | indoor under a roof at y 60 | Grey-box walls, orange lava, unlit | not yet: it reads as unfinished |

Each video uses at least two sets (directing.md section 8). Before using a new spot, put a test actor there and look at a still: floors have cracks and props that swallow feet.
