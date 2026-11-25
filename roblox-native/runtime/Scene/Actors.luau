--!nonstrict
-- Actors for staged scenes. Everything an actor does is a pure function of scene time t, so a take can be
-- previewed in real time, filmed frame by frame, or posed at any single moment for a still, and every
-- route shows the same picture. Client side; everything spawned is local to the filming client.
--
-- Kinds:
--   slug            a real slug rig from ReplicatedStorage.CombatAssets (species), performed by the game's own
--                   SlugIdle (breathing, idle, facial acting) and, for Floppy, FloppyFace (lids, eyes, mouth)
--   clone           a copy of any Model in the place (asset = dotted path); a puppet
--   standin_humanoid / standin_slug   part-built stand-ins, technical tests only
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Actors = {}

local TAU = 2 * math.pi

-- Species -> the model in CombatAssets. Icon models are in the pose SlugIdle is written for (+Y up, -Z face).
local SPECIES = {
	Floppy = "FloppyFlight",
	Inferno = "InfernoIcon",
	Aquabeek = "AquabeekIcon",
	Rammstone = "RammstoneIcon",
	Tormato = "TormatoIcon",
	BoonDoc = "BoonDocIcon",
	Phosphoro = "PhosphoroIcon",
}
Actors.SPECIES = SPECIES

-- The game's FloppyFace/FloppyIdle LocalScripts drive any model named "Floppy"/"FloppyFlight" on real time. In a
-- staged take they fought this runner and raced ahead of held film frames (owner, 2026-11-25: Floppy's face
-- "glitching around"), so actors never take those names: Floppy's face is driven here (Actors.floppyFace, ported
-- from FloppyFace with the same constants) as a pure function of scene time.

local function smooth(u: number): number
	u = math.clamp(u, 0, 1)
	return u * u * u * (u * (u * 6 - 15) + 10)
end
Actors.smooth = smooth

local function part(model: Model, name: string, size: Vector3, offset: CFrame, color: Color3, shape: Enum.PartType?)
	local p = Instance.new("Part")
	p.Name = name
	p.Size = size
	p.CFrame = offset
	p.Color = color
	p.Material = Enum.Material.SmoothPlastic
	p.Anchored = true
	p.CanCollide = false
	if shape then
		p.Shape = shape
	end
	p.Parent = model
	return p
end

local function standinHumanoid(): Model
	local m = Instance.new("Model")
	local root = part(m, "Root", Vector3.new(2, 2, 1), CFrame.new(0, 3, 0), Color3.fromRGB(80, 120, 200))
	part(m, "Head", Vector3.new(1.2, 1.2, 1.2), CFrame.new(0, 4.6, 0), Color3.fromRGB(240, 200, 160))
	part(m, "Nose", Vector3.new(0.3, 0.3, 0.4), CFrame.new(0, 4.6, -0.7), Color3.fromRGB(220, 160, 120))
	part(m, "LegL", Vector3.new(0.9, 2, 1), CFrame.new(-0.5, 1, 0), Color3.fromRGB(50, 50, 60))
	part(m, "LegR", Vector3.new(0.9, 2, 1), CFrame.new(0.5, 1, 0), Color3.fromRGB(50, 50, 60))
	m.PrimaryPart = root
	return m
end

local function standinSlug(): Model
	local m = Instance.new("Model")
	local body = part(m, "Body", Vector3.new(1.6, 1.2, 2.2), CFrame.new(0, 0.6, 0), Color3.fromRGB(235, 220, 170), Enum.PartType.Ball)
	part(m, "EyeL", Vector3.new(0.25, 0.25, 0.25), CFrame.new(-0.3, 0.9, -0.9), Color3.new(0, 0, 0), Enum.PartType.Ball)
	part(m, "EyeR", Vector3.new(0.25, 0.25, 0.25), CFrame.new(0.3, 0.9, -0.9), Color3.new(0, 0, 0), Enum.PartType.Ball)
	m.PrimaryPart = body
	return m
end

local function findPath(path: string): Instance?
	local node: Instance? = game
	for segment in string.gmatch(path, "[^%.]+") do
		if node == nil then
			return nil
		end
		node = if segment == "game" then node else node:FindFirstChild(segment)
	end
	return node
end

local slugIdleModule = nil
local function slugIdle()
	if not slugIdleModule then
		local combat = Players.LocalPlayer:WaitForChild("PlayerScripts"):WaitForChild("Combat", 20)
		local module = combat and combat:WaitForChild("SlugIdle", 10)
		assert(module, "SlugIdle not found in PlayerScripts.Combat (is this the marketing place, in play mode?)")
		slugIdleModule = require(module)
	end
	return slugIdleModule
end

-- Spawns the model only; where it stands and what it does come from its tracks (Actors.compile).
function Actors.spawn(name: string, def: any, parent: Instance): any
	local model: Model
	local kind = def.kind
	if kind == "standin_humanoid" then
		model = standinHumanoid()
	elseif kind == "standin_slug" then
		model = standinSlug()
	elseif kind == "clone" or kind == "slug" then
		local path = if kind == "slug"
			then `ReplicatedStorage.CombatAssets.{SPECIES[def.species] or error(`unknown species {def.species}`)}`
			else def.asset
		local source = findPath(path)
		assert(source and source:IsA("Model"), `actor {name}: no Model at {path}`)
		model = (source :: Model):Clone()
	else
		error(`actor {name}: unknown kind {kind}`)
	end
	model.Name = `SS_actor_{name}`
	model:SetAttribute("SlugshotActor", name)
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then
			d.Anchored = true -- staged actors are puppets, not physics
			d.CanCollide, d.CanTouch = false, false
		elseif d:IsA("Script") or d:IsA("LocalScript") then
			d.Enabled = false -- copied game behaviour must not run inside a staged scene
		end
	end
	if def.scale and model.ScaleTo then
		model:ScaleTo(model:GetScale() * def.scale)
	end
	local box, size = model:GetBoundingBox()
	-- How far the pivot sits above the model's lowest point, so every kind stands on its mark's ground.
	local lift = model:GetPivot().Position.Y - (box.Position.Y - size.Y / 2)
	if kind == "slug" then
		-- Slug imports carry an invisible RootPart block reaching about 1.4 studs below the body (owner, 2026-11-25:
		-- "all the slugs are floating"). The authored floor is the `root` bone (the body's lowest point, measured
		-- for every species), and height is the visible meshes' height, for grounding and framing alike.
		local root = model:FindFirstChild("root", true)
		local top, bottom = -math.huge, math.huge
		for _, p in model:GetDescendants() do
			if p:IsA("MeshPart") then
				top = math.max(top, p.Position.Y + p.Size.Y / 2)
				bottom = math.min(bottom, p.Position.Y - p.Size.Y / 2)
			elseif p:IsA("BasePart") and p.Name == "RootPart" then
				p.Transparency = 1
			end
		end
		local floor = if root and root:IsA("Bone") then root.WorldPosition.Y else bottom
		lift = model:GetPivot().Position.Y - floor
		if top > floor then
			size = Vector3.new(size.X, top - floor, size.Z)
		end
		for _, p in model:GetDescendants() do
			if p:IsA("BasePart") and string.sub(p.Name, -9) == "MouthLine" then
				p.Transparency = 0.15 -- the game's resting tooth division (InfernoMotion)
			end
		end
	end
	model.Parent = parent
	local actor = {
		name = name, def = def, model = model, height = size.Y, size = size, lift = lift,
		species = def.species, idle = nil, bones = {}, all = {},
	}
	if kind == "slug" then
		actor.idle = slugIdle().new(model, def.species)
		-- Every copy of every bone (Roblox can make one skeleton per skinned mesh), with its rest frame in the
		-- model's pivot space, so overlays move all copies together in the model's own axes.
		local pivot = model:GetPivot()
		for _, b in model:GetDescendants() do
			if b:IsA("Bone") then
				actor.bones[b.Name] = actor.bones[b.Name] or {}
				table.insert(actor.bones[b.Name], { bone = b, rest = pivot:ToObjectSpace(b.WorldCFrame) })
				table.insert(actor.all, b)
			end
		end
		if def.species == "Floppy" then
			actor.face = Actors.floppyFaceSetup(actor)
		end
	end
	if kind == "slug" then
		-- Character lighting for close-ups: an actor's own horns, spikes and lids cast coarse shadow-map blocks
		-- onto its face, so actors don't self-shadow; a soft, shadowless fill lifts faces out of the world's
		-- hard shadows (def.fill = 0 turns it off, or sets its brightness).
		for _, d in model:GetDescendants() do
			if d:IsA("BasePart") then
				d.CastShadow = false
			end
		end
		local brightness = if def.fill ~= nil then def.fill else 0.7
		if brightness > 0 and model.PrimaryPart then
			-- in front of the face (pivot -Z) at head height, riding with the model as it moves
			local at = Instance.new("Attachment")
			at.Name = "SS_fill"
			at.Parent = model.PrimaryPart
			at.WorldPosition = model:GetPivot() * Vector3.new(0, size.Y * 0.15, -(size.Z * 0.5 + size.Y * 0.7))
			local fill = Instance.new("PointLight")
			fill.Shadows = false
			fill.Brightness = brightness
			fill.Range = math.max(size.Y * 2.2, 5)
			fill.Color = Color3.fromRGB(255, 244, 232)
			fill.Parent = at
		end
	end
	if def.outline ~= false and kind ~= "standin_humanoid" and kind ~= "standin_slug" then
		-- Characters are always inked (Living Comic-Book Fantasy, "Inked Cavern"): charcoal, not pure black.
		local h = Instance.new("Highlight")
		h.FillTransparency = 1
		h.OutlineColor = Color3.fromRGB(24, 22, 28)
		h.OutlineTransparency = 0
		h.DepthMode = Enum.HighlightDepthMode.Occluded
		h.Parent = model
	end
	return actor
end

-- Tracks ------------------------------------------------------------------------------------------------
-- Everything below is a pure function of scene time t: a still at any t, a preview and a filmed take agree, and
-- nothing depends on how often frames are drawn (owner, 2026-11-25: choppy, jittering slugs in the first takes).

-- A channel is a list of {t, value, ease} keys, sorted; its value at t eases from the previous key's value
-- to each key's value over that key's `ease` seconds starting at its time.
local function channel(keys: { any }, t: number, default: number): number
	local v = default
	for _, k in keys do
		if t < k.t then
			break
		end
		local from = v
		local u = if k.ease <= 0 then 1 else smooth((t - k.t) / k.ease)
		v = from + (k.value - from) * u
	end
	return v
end

local function yawTo(from: Vector3, to: Vector3): number
	local d = to - from
	return math.atan2(-d.X, -d.Z)
end

local function shortest(a: number, b: number): number
	return ((b - a + math.pi) % TAU) - math.pi
end

-- Zero-phase smoothing (forward then backward exponential): no lag, no frame-to-frame popping.
local function smoothSeries(xs: { number }, k: number): { number }
	local out, v = table.create(#xs, 0), xs[1] or 0
	for i, x in xs do
		v += (x - v) * k
		out[i] = v
	end
	v = out[#out] or 0
	for i = #out, 1, -1 do
		v += (out[i] - v) * k
		out[i] = v
	end
	return out
end

-- Hop: an eased anticipation squash, a parabolic arc, and a landing squash that settles with a damped wobble.
-- Continuous at every phase boundary. Returns lift (fraction of hop height), press (SlugIdle squash) and wobble.
local WIND, LAND = 0.16, 0.5
local function hopShape(u: number, d: number): (number, number, number)
	if u < -WIND or u > d + LAND then
		return 0, 0, 0
	elseif u < 0 then
		return 0, 0.55 * smooth((u + WIND) / WIND), 0
	elseif u < d then
		local k = u / d
		return 4 * k * (1 - k), 0.55 * (1 - smooth(k / 0.3)), 0
	end
	local k = (u - d) / LAND
	local settle = math.exp(-4.5 * k)
	return 0, 0.7 * smooth(k / 0.08) * (1 - k) ^ 2, math.sin(TAU * 1.4 * k) * settle * (1 - k)
end

-- The eyeline at t: explicit `look` beats hold until the next explicit look ("auto" hands back to the dialogue);
-- otherwise the actor looks at whoever speaks (from just before each line). Returns the current and previous
-- target and how far the turn between them has eased.
local function lookEvents(actor: any, beats: { any }, dialogue: any?): { any }
	local events = {}
	for _, b in beats do
		if b.actor == actor.name and b.action == "look" then
			table.insert(events, { t = b.time, target = b.target, ease = b.ease or 0.35, explicit = true })
		end
	end
	if dialogue and actor.def.auto_look ~= false then
		for _, line in dialogue.lines do
			if line.actor and line.actor ~= actor.name then
				table.insert(events, { t = math.max(0, line.start - 0.15), target = line.actor, ease = 0.35 })
			end
		end
	end
	table.sort(events, function(a, b)
		return a.t < b.t
	end)
	local kept, locked = {}, false
	for _, e in events do
		if e.explicit then
			locked = e.target ~= "auto"
			if e.target ~= "auto" then
				table.insert(kept, e)
			end
		elseif not locked then
			table.insert(kept, e)
		end
	end
	return kept
end

-- Turns a spec's timeline into per-actor tracks. `place(markName)` gives a mark's world CFrame on the ground
-- for this actor.
function Actors.compile(actor: any, beats: { any }, place: (string, any) -> CFrame, dialogue: any?)
	local tr = {
		moves = {}, faces = {}, hops = {},
		ch = { smile = {}, angry = {}, react = {}, look_up = {}, squint = {}, open = {}, lean = {} },
		blinks = {}, lines = {},
	}
	tr.home = place(actor.def.mark, actor)
	for _, b in beats do
		if b.actor ~= actor.name then
			continue
		end
		local a = b.action
		if a == "move_to" then
			table.insert(tr.moves, { t = b.time, d = b.duration or 1, to = place(b.mark, actor).Position, turn = b.turn ~= false })
		elseif a == "face" then
			table.insert(tr.faces, { t = b.time, d = b.duration or 0.35, target = b.target })
		elseif a == "hop" then
			table.insert(tr.hops, { t = b.time, d = b.duration or 0.45, h = b.height or 0.3 })
		elseif a == "express" then
			for key, value in b.set or {} do
				assert(tr.ch[key], `express: unknown channel {key}`)
				table.insert(tr.ch[key], { t = b.time, value = value, ease = b.ease or 0.35 })
			end
		elseif a == "blink" then
			table.insert(tr.blinks, b.time)
		end
	end
	if dialogue then
		for _, line in dialogue.lines do
			if line.actor == actor.name then
				-- Mouth: lightly smoothed loudness. Nod: a slow version, so the head follows phrases, not syllables.
				table.insert(tr.lines, { start = line.start, finish = line["end"],
					open = smoothSeries(line.mouth, 0.5), nod = smoothSeries(line.mouth, 0.12) })
			end
		end
	end
	tr.looks = lookEvents(actor, beats, dialogue)
	for _, list in { tr.moves, tr.faces, tr.hops } do
		table.sort(list, function(x, y)
			return x.t < y.t
		end)
	end
	for _, keys in tr.ch do
		table.sort(keys, function(x, y)
			return x.t < y.t
		end)
	end
	actor.tracks = tr
end

-- Where the actor stands at t (ground position and facing), from its moves, turns and hops. Pure.
function Actors.frameAt(actor: any, t: number, where: (string, number) -> Vector3): CFrame
	local tr = actor.tracks
	local pos = tr.home.Position
	local yaw = select(2, tr.home:ToEulerAnglesYXZ())
	for _, m in tr.moves do
		if t < m.t then
			break
		end
		local u = smooth((t - m.t) / m.d)
		if m.turn and (m.to - pos).Magnitude > 0.2 then
			yaw += shortest(yaw, yawTo(pos, m.to)) * smooth((t - m.t) / math.min(0.3, m.d))
		end
		pos = pos:Lerp(m.to, u)
	end
	for _, f in tr.faces do
		if t < f.t then
			break
		end
		yaw += shortest(yaw, yawTo(pos, where(f.target, f.t))) * smooth((t - f.t) / f.d)
	end
	local lift = 0
	for _, h in tr.hops do
		lift += hopShape(t - h.t, h.d) * h.h * actor.height
	end
	return CFrame.new(pos + Vector3.new(0, lift, 0)) * CFrame.Angles(0, yaw, 0)
end

local function sample(series: { number }, start: number, t: number): number
	local x = (t - start) * 30
	local i = math.floor(x) + 1
	local a, b = series[i] or 0, series[i + 1] or 0
	return a + (b - a) * (x - (i - 1))
end

local function speech(tr: any, t: number): (number, number)
	local open, nod = 0, 0
	for _, line in tr.lines do
		if t >= line.start - 0.05 and t <= line.finish + 0.4 then
			open = math.max(open, sample(line.open, line.start, t))
			nod = math.max(nod, sample(line.nod, line.start, t))
		end
	end
	return open, nod
end

-- Who, if anyone, is speaking at t (kept for callers; eyelines now come from each actor's look events).
function Actors.speakerAt(dialogue: any?, t: number): string?
	if not dialogue then
		return nil
	end
	local best = nil
	for _, line in dialogue.lines do
		if line.actor and t >= line.start - 0.15 and t <= line["end"] + 0.25 then
			best = line.actor
		end
	end
	return best
end

-- Floppy's slow lids: scheduled at fixed times (no randomness), sinking a little over halfway, never shut.
local function blinkAt(actor: any, t: number): number
	local tr = actor.tracks
	if not tr.blinkTimes then
		local times = table.clone(tr.blinks)
		local seed = #actor.name * 1.37
		local at = 1.1 + (seed % 1.3)
		while at < 180 do
			table.insert(times, at)
			at += 2.8 + ((at * 7.13 + seed) % 2.6)
		end
		tr.blinkTimes = times
	end
	local out = 0
	for _, b in tr.blinkTimes do
		local u = (t - b) / 0.55
		if u >= 0 and u < 1 then
			local k = if u < 0.4 then u / 0.4 elseif u < 0.5 then 1 else 1 - (u - 0.5) / 0.5
			out = math.max(out, 0.55 * (0.5 - 0.5 * math.cos(k * math.pi)))
		end
	end
	return out
end

-- Head angles toward a target, in the actor's own frame, clamped to what a neck can do.
local function aim(actor: any, frame: CFrame, target: string?, t: number, where: any): (number, number)
	if not target or target == "none" then
		return 0, 0
	end
	local at = where(target, t)
	local head = (frame * CFrame.new(0, actor.height * 0.72, 0)).Position
	local d = frame:VectorToObjectSpace(at - head)
	return math.clamp(math.atan2(-d.X, -d.Z), -0.6, 0.6),
		math.clamp(math.atan2(d.Y, Vector2.new(d.X, d.Z).Magnitude), -0.35, 0.35)
end

local function lookAt(actor: any, frame: CFrame, t: number, where: any): (number, number)
	local events = actor.tracks.looks
	local cur, prev = nil, nil
	for _, e in events do
		if t < e.t then
			break
		end
		prev, cur = cur, e
	end
	if not cur then
		return 0, 0
	end
	local y1, p1 = aim(actor, frame, prev and prev.target, t, where)
	local y2, p2 = aim(actor, frame, cur.target, t, where)
	local k = smooth((t - cur.t) / cur.ease)
	return y1 + (y2 - y1) * k, p1 + (p2 - p1) * k
end

-- Overlays, applied to every copy of a bone in the model's pivot axes, after SlugIdle has posed it.
local function rotate(actor: any, name: string, axis: Vector3, angle: number)
	for _, c in actor.bones[name] or {} do
		c.bone.Transform = c.bone.Transform * CFrame.fromAxisAngle(c.rest:VectorToObjectSpace(axis), angle)
	end
end

-- Lower-lip gains from the game's SlugIdle MOUTH_GAIN (how far each painted mouth may open).
local LIP_GAIN = { Aquabeek = 0.5, Rammstone = 0.4, Tormato = 0.5, BoonDoc = 0.4 }

local function offset(actor: any, name: string, v: Vector3)
	for _, c in actor.bones[name] or {} do
		c.bone.Transform = CFrame.new(c.rest:VectorToObjectSpace(v)) * c.bone.Transform
	end
end

-- Floppy's face, ported from the game's FloppyFace (../slugshot experiments/creatures/floppy/client) with its
-- constants, but driven by scene time instead of its own clock.
local FACE = {
	EYE_SPACING = 0.74, GAZE_SIDE = 0.018, GAZE_UP = 0.008, GAZE_BACK = 0.03,
	CLOSED_DEPTH = { [1] = 0.172, [-1] = 0.112 }, CLOSED_TURN = math.atan(0.29),
	LID = 0.03, TILT = math.rad(16), -- Tuning: faceLid, faceTilt
	EXPRESSIONS = {
		{ low = 0.065, high = 0.025, wide = 0.015, jaw = 0.008, lid = -0.004 }, -- content and drowsy
		{ low = 0.10, high = 0.04, wide = 0.025, jaw = 0.018, lid = -0.02 }, -- lazy smile
		{ low = 0.075, high = 0.03, wide = 0.018, jaw = 0.012, lid = 0.004 }, -- sleepy grin
	},
}

function Actors.floppyFaceSetup(actor: any): any?
	local b = actor.bones
	local first = function(n)
		return b[n] and b[n][1] and b[n][1].bone
	end
	local eyeL, eyeR, root, head = first("eye_L"), first("eye_R"), first("root"), first("head")
	if not (eyeL and eyeR and root and head) then
		return nil
	end
	local sideways = (eyeR.WorldPosition - eyeL.WorldPosition).Unit
	local rough = (head.WorldPosition - root.WorldPosition).Unit
	local up = (rough - sideways * rough:Dot(sideways)).Unit
	local front = sideways:Cross(up)
	local face = { scale = (eyeR.WorldPosition - eyeL.WorldPosition).Magnitude / FACE.EYE_SPACING }
	for group, names in { gaze = { "gaze_L", "gaze_R" }, lids = { "lid_L", "lid_R" }, left = { "mouth_L" },
		right = { "mouth_R" }, lip = { "mouth_low" } } do
		face[group] = {}
		for _, n in names do
			for _, c in b[n] or {} do
				local f = c.bone.WorldCFrame
				table.insert(face[group], { bone = c.bone, side = f:VectorToObjectSpace(sideways), up = f:VectorToObjectSpace(up),
					front = f:VectorToObjectSpace(front), sign = if string.sub(n, -2) == "_L" then 1 else -1 })
			end
		end
	end
	return face
end

local function floppyFace(face: any, t: number, smile: number, squint: number, blink: number, lookX: number,
	lookY: number, talk: number)
	local E = FACE.EXPRESSIONS
	local a, bb, k = E[1], if smile >= 0 then E[2] else E[3], math.clamp(math.abs(smile), 0, 1)
	local function mix(key)
		return a[key] + (bb[key] - a[key]) * k
	end
	local low, high, wide, lid = mix("low"), mix("high"), mix("wide"), mix("lid")
	local mouthing = 0.5 + 0.5 * math.sin(t * 2.3) * math.sin(t * 5.7)
	local lift = 0.006 * math.sin(t * 1.7)
	local jaw = mix("jaw") + 0.008 * mouthing * (1 - talk) + 0.016 * talk -- game range; deeper bent the drool (owner, 2026-11-25)
	-- Sleepiness closes the lids along their designed closing path (as a slow blink held part-way): translating them
	-- further down stretched the lid skin into the eye corners (owner, 2026-11-25: lids "connected to the sides").
	-- Floppy's rest lids already read as tired; squint adds at most a third of a blink so the spirals always show
	-- (owner, 2026-11-25: "way too squinty ... still look tired"). Negative squint lifts the lids above rest.
	local rest = (FACE.LID + lid) * (1 + math.clamp(squint, -1, 0))
	local close = math.max(blink, math.clamp(squint * 0.18, 0, 0.35))
	blink = close
	local droop = FACE.TILT * math.clamp(1 + lid / 0.09, 0, 1)
	droop += (FACE.CLOSED_TURN - droop) * blink
	local s = face.scale
	for _, it in face.gaze do
		it.bone.Transform = CFrame.new((it.side * lookX * FACE.GAZE_SIDE + it.up * lookY * FACE.GAZE_UP
			- it.front * FACE.GAZE_BACK * math.max(math.abs(lookX), math.abs(lookY))) * s)
	end
	for _, it in face.lids do
		local l = rest + (FACE.CLOSED_DEPTH[it.sign] - rest) * blink
		it.bone.Transform = CFrame.new((it.up * -l + it.front * math.max(l, 0) * 0.15) * s)
			* CFrame.fromAxisAngle(it.front, droop * it.sign)
	end
	for _, it in face.left do
		it.bone.Transform = CFrame.new((it.up * (low + lift) - it.side * wide) * s)
	end
	for _, it in face.right do
		it.bone.Transform = CFrame.new((it.up * (high + lift) + it.side * wide) * s)
	end
	for _, it in face.lip do
		it.bone.Transform = CFrame.new(it.up * -jaw * s)
	end
end

-- Pose the actor at t. `where(name, t)` resolves look targets.
function Actors.pose(actor: any, t: number, where: (string, number) -> Vector3, _speaker: string?)
	local tr = actor.tracks
	local frame = Actors.frameAt(actor, t, where)
	if actor.def.kind ~= "slug" then
		actor.model:PivotTo(frame * CFrame.new(0, actor.lift, 0))
		return
	end
	-- Eyelines turn the whole body most of the way; the head bone only adds a little. Head bones are weighted into
	-- the cheeks, and a large head twist puffed them out (owner, 2026-11-25: Aquabeek's cheeks on a turn).
	local yaw, pitch = lookAt(actor, frame, t, where)
	local base = frame * CFrame.Angles(0, yaw * 0.75, 0) * CFrame.new(0, actor.lift, 0)
	actor.model:PivotTo(base)
	-- Start every frame from the rest pose, so no overlay can build up from one frame to the next.
	for _, b in actor.all do
		b.Transform = CFrame.identity
	end

	local open, nod = speech(tr, t)
	local press, wobble = 0, 0
	for _, h in tr.hops do
		local _, p, w = hopShape(t - h.t, h.d)
		press += p
		wobble += w
	end
	local ch = tr.ch
	local smile = channel(ch.smile, t, 0)
	local idle = actor.idle
	if idle then
		idle.react = math.clamp(channel(ch.react, t, 0) + math.max(smile, 0) * 0.6, 0, 1)
		idle.angry = channel(ch.angry, t, 0)
		idle.lookUp = channel(ch.look_up, t, 0)
		idle.press = press
		idle.wobble = wobble
		slugIdle().pose(idle, t + (actor.def.phase or 0))
	end

	local lean = channel(ch.lean, t, 0)
	local talkNod = nod * 0.05
	rotate(actor, "head", Vector3.yAxis, math.clamp(yaw * 0.25, -0.12, 0.12))
	rotate(actor, "head", Vector3.xAxis, math.clamp(pitch * 0.5, -0.15, 0.15) - talkNod)
	local body = if actor.bones.body_upper then "body_upper" else "body"
	rotate(actor, body, Vector3.xAxis, -lean * 0.15 - nod * 0.02)

	local mouth = math.clamp(open + channel(ch.open, t, 0), 0, 1)
	if actor.face then
		floppyFace(actor.face, t, smile, channel(ch.squint, t, 0), blinkAt(actor, t),
			math.clamp(-yaw / 0.6, -1, 1), math.clamp(pitch / 0.35, -0.45, 0.6), mouth)
	else
		-- Talking only drops the lower lip, within each slug's painted-mouth range (the game's SlugIdle MOUTH_GAIN
		-- lip, about twice its idle mouthing). Larger drops, a forward push and pinched corners smeared the painted
		-- mouth (owner, 2026-11-25: Aquabeek's "mouth movements look very weird").
		local u = idle and idle.unit or 1
		local lip = LIP_GAIN[actor.def.species] or 0.5
		offset(actor, "mouth_low", Vector3.new(0, -0.018 * lip * mouth * u, 0))
	end
end

return Actors
