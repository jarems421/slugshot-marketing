# Sets: where scenes can be filmed (scouted 2026-11-26 in the marketing place)

The world is built at play time (HubArt about 2 min, Training about 3.5 min); in Edit mode the workspace is empty, so scout in a playtest. Marks are relative to a spec's `set.origin`, so one spec can span sets: write marks as (set origin - spec origin) + local position, and move actors between sets with an instant `move_to` (`duration: 0.02`) exactly on a cut.

| Set | World origin | Floor | Look | Good for |
|---|---|---|---|---|
| **Hub plaza** (spawn island) | (19, 0, 20) | y 0 (hub-rock.Top) | The best-looking set: glowing mushrooms, portals, lava arches, waterfalls, bridges | social scenes, setup, endings. Clear duel lane along -Z from (17, 0, 16) to (21, 0, -4); the west side (x 10-14) is open for fire lanes, the east has rope posts |
| **Training arena** (floating island) | (6000, 0, 0) | y 0 (TrainingSolids.Footing), about 300 x 300 open | Dark purple stone and mist against a black void (the game's own arena light), cover blocks, grey R6 training dummies, target boards, a green portal | duels, practice, montage. Actors read well at medium and wide (checked); keep marks clear of the dummies |
| **Cinder Rift** (1v1 PvP greybox) | (-6000, ~0, 0) | indoor under a roof at y 60 | Grey-box walls, orange lava, unlit | not yet: it reads as unfinished |

**Living sets (2026-11-27).**
- **Hub plaza** (spec coords, origin (19, 0, 20)): the floor is cut by diagonal cracks and pits, now mapped (`python roblox-native/tools/floormap.py show hub_plaza`). The widest clean patch for heroes is around (-12, -19) (x -22..-4, z -24..-14); the big open crowd area is north-west (x -40..-22, z -46..-30). Face the heroes so the camera looks north-west across the crowd; east of x 0 the background is the cave wall and pillars. The pilot's Floppy and Raf marks stood on cracks.
- **Slug Grove**: origin (120, 0, 10) frames the pond. `residents` brings back the game's 14 residents at their real spots; the pond trio (Rammstone, Aquabeek, Floppy) sits around (-5.2, 0, -3.1), with the waterfall behind from the south-west (orbit angles about 205-250, radius 9, height 3.2). Visitors fit in [-14, -10, 8, 14]. Tall flora in the foreground blocks wider orbits.

**Temporary locations (2026-11-27).** Quick reusable sets outside the lobby, in the Slugshot look, so videos can go anywhere (owner: "one-shotted", not production quality, but our identity). Use `"set": {"kind": "location", "location": "<name>"}`; the location's origin, named marks and lighting come with it.

| Location | Origin | Inside | Named marks |
|---|---|---|---|
| `bedroom` | (0, 0, 9000) | 26 x 20 room, panelled and beamed: bed, desk + lamp, wardrobe, bookshelf, slug terrarium, beanbag, slug plush, backpack, plant, wall shelf, the game's blaster on the wall, crystals in a corner, glowing window | center, by_bed, at_desk, by_window, door; seat_bed, seat_beanbag; look_terrarium, look_window, look_poster, look_blaster |
| `classroom` | (400, 0, 9000) | 34 x 26 room: chalkboard, teacher's desk + globe, nine student desks in staggered rows, bookshelves, backpacks, windows, crystals | teacher, front, aisle, back_row, door, seat_l1/c1/r1, seat_r1c1..seat_r3c3; look_board, look_window |
| `wild_cavern` | (800, 0, 9000) | 70 x 70 cave walled with turned stones in four shades: mossy ground, giant glowing mushrooms, flowers, crystal clusters, boulders, lantern posts | clearing, boulder_side, path, tree_shade, crystals; look_boulder, look_crystals |
| `market` | (1200, 0, 9000) | 60 x 50 cave plaza: striped stall (shopkeeper behind the counter), shelf of creature jars, crates, barrels, a stool, a sign board, paper lanterns, the town's mushroom shop | shopkeeper, customer, browse, street; seat_stool; look_jars, look_sign |

**Handcrafted, not assembled (owner, 2026-11-27).** The four files are written by `python roblox-native/tools/make_locations.py`; edit that script, not the JSON. It nudges and turns furniture a little (seeded), staggers rows, adds clutter and story props, panels and beams interiors, builds cave walls from varied turned stones, grows crystals in a corner, hangs the game's blaster where it fits (a `clone` piece: any model in the place by dotted path, e.g. `StarterPack.Blaster`) and lights with motivated pools (lamps, windows, lanterns: warm inside, teal outside).
- `seat_*` marks: the mark sits on the seat, facing out. Use the `sit` gesture (`human_moves.sit`, mask `legs`, `duration` = how long they sit). A mark's yaw 0 faces actors toward -z; 180 toward +z.
- `look_*` marks: things to look at (`look` / `face` / `point` with the mark as target), so characters look at objects, not empty space.
- Generated props are in `roblox-native/library/props.json` (22, from Studio's `generate_mesh` in Edit mode; it fails in play mode).
- Still review for "assembled" looks: identical props side by side, perfect grids, bare walls, flat lighting.

- Data: `roblox-native/library/locations/<name>.json` (boxes, `kit` pieces cloned from the hub's own inked art by name, generated props by mesh/texture id, lights); built at play time by `runtime/Scene/Locations.luau`, once, under `workspace.SS_Locations`.
- A new location: copy one of these files and change it. Props: Studio's `generate_mesh` (owner-approved; prompt "stylized chunky shapes, bold flat colours, hand-painted toon style"), then record the `rbxassetid` mesh and texture. Generated props come in smaller than asked and sometimes tilted (the chalkboard): check a still and use boxes where a shape is simple.
- Ink: one charcoal Highlight per group (floor, walls, trim, props); kit pieces bring their own ink shells. Roblox renders at most 31 Highlights and every actor uses one, so don't give props their own.
- Hub kit names: mushroom-3/5/12/13 (trees), hub-flora-bell/star/lantern, crystals-1/5/10, hub-lantern-post, hub-gun-shop (the mushroom shop). `index` picks the nth copy.
- Aim wides at a person, not a floor mark (the camera looks at the mark's height). Orbit angle 0 is in front of the target.

Each video uses at least two sets (directing.md section 8). Before using a new spot, put a test actor there and look at a still: floors have cracks and props that swallow feet.
