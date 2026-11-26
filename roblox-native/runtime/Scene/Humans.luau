--!nonstrict
-- Human actors: blocky R6 characters, the rig the game's players use (../slugshot docs/decisions/0008-r6-rig.md),
-- performed as a pure function of scene time like every other actor.
--
-- Look: the marketing server builds each rig from a HumanoidDescription (CastServer; free Roblox-owned clothing and
-- hair by catalog ID, from library.json `humans` or the actor's own `look`). The face is ours: inked eyes, brows and
-- a mouth built from parts, so it blinks, glances, raises its brows and talks (a drawn decal can't change per frame
-- here: EditableImage doesn't render in this place).
--
-- Motion is composed in the game's R15 pose terms (joint names and axes of ../slugshot OriginalClips) and folded
-- onto R6 the way the game's Presentation does it (chord, toR6, ported below). Moves come from library.json
-- `human_moves`:
--   { "clip": "Run" }                 the game's own clips (ReplicatedStorage.MovementExperiment.Clips)
--   { "animation": 507770239 }        a Roblox-owned animation (KeyframeSequence, sampled at scene time)
--   { "catalog": 3576968026 }         a free Roblox emote, fetched by the server from its catalog item
--   { "keys": [{ "t": 0, "joints": { "RightShoulder": [x, y, z] } }] }   an authored pose, degrees
-- Every part is anchored and placed by our own forward kinematics (no physics, no AnimationTracks), so held film
-- frames, patches and stills agree exactly.
local KeyframeSequenceProvider = game:GetService("KeyframeSequenceProvider")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local StarterPack = game:GetService("StarterPack")
local TweenService = game:GetService("TweenService")

local Humans = {}
local Shots = require(script.Parent.Shots)

local IDENTITY = CFrame.identity
local FPS = 30
local INK = Color3.fromRGB(24, 22, 28)
local DOWN = Vector3.new(0, -1, 0)

local A, library -- the Actors module (shared helpers) and library.json, from Humans.bind

function Humans.bind(actors: any, lib: any)
	A, library = actors, lib
end

local function remote(): RemoteFunction
	return ReplicatedStorage:WaitForChild("SlugshotMarketing"):WaitForChild("Cast")
end

local function store(): Instance
	return ReplicatedStorage:WaitForChild("SlugshotMarketingRigs", 20)
end

-- Clips ---------------------------------------------------------------------------------------------------

local Clips, gameClips = nil, nil
local function clipsModule()
	if not Clips then
		Clips = require(ReplicatedStorage:WaitForChild("MovementExperiment"):WaitForChild("Clips"))
		gameClips = Clips.load()
	end
	return Clips, gameClips
end

local PART_JOINT = {
	LowerTorso = "Root", UpperTorso = "Waist", Head = "Neck",
	LeftUpperArm = "LeftShoulder", LeftLowerArm = "LeftElbow", LeftHand = "LeftWrist",
	RightUpperArm = "RightShoulder", RightLowerArm = "RightElbow", RightHand = "RightWrist",
	LeftUpperLeg = "LeftHip", LeftLowerLeg = "LeftKnee", LeftFoot = "LeftAnkle",
	RightUpperLeg = "RightHip", RightLowerLeg = "RightKnee", RightFoot = "RightAnkle",
}
-- Roblox's R15 animations move the root in studs; clips keep it in hip units (about 2 studs on R15).
local R15_UNIT = 2

local function poseEase(style: Enum.PoseEasingStyle, direction: Enum.PoseEasingDirection, u: number): number
	if style == Enum.PoseEasingStyle.Constant then
		return 0
	elseif style == Enum.PoseEasingStyle.Linear then
		return u
	end
	local v2 = style == Enum.PoseEasingStyle.CubicV2
	local dir = direction.Name
	-- The legacy pose styles name In and Out the other way round from TweenService (CubicV2 fixed that).
	if not v2 and dir ~= "InOut" then
		dir = if dir == "In" then "Out" else "In"
	end
	return TweenService:GetValue(u, Enum.EasingStyle[if v2 then "Cubic" else style.Name], Enum.EasingDirection[dir])
end

local function trackAt(keys: { any }, t: number): CFrame
	if t <= keys[1].t then
		return keys[1].cf
	end
	for i = 1, #keys - 1 do
		local a, b = keys[i], keys[i + 1]
		if t < b.t then
			return a.cf:Lerp(b.cf, poseEase(a.style, a.dir, (t - a.t) / math.max(b.t - a.t, 1e-6)))
		end
	end
	return keys[#keys].cf
end

local function clip(name: string, joints: any, frames: number, loop: boolean): any
	return {
		name = name, fps = FPS, frames = frames, duration = (if loop then frames else frames - 1) / FPS, loop = loop,
		speed = 0, direction = Vector3.new(0, 0, -1), events = {}, joints = joints,
	}
end

-- A KeyframeSequence baked to the game's clip layout at 30 fps (pose names are R15 part names).
local function bakeSequence(name: string, ks: KeyframeSequence, entry: any): any
	local tracks, last = {}, 0
	local function walk(pose: Instance, time: number)
		for _, child in (pose :: any):GetSubPoses() do
			if child:IsA("Pose") then
				local joint = PART_JOINT[child.Name]
				if joint and child.Weight > 0 then
					tracks[joint] = tracks[joint] or {}
					table.insert(tracks[joint], { t = time, cf = child.CFrame, style = child.EasingStyle, dir = child.EasingDirection })
				end
				walk(child, time)
			end
		end
	end
	for _, kf in ks:GetKeyframes() do
		last = math.max(last, kf.Time)
		for _, top in (kf :: Keyframe):GetPoses() do
			if top:IsA("Pose") then
				walk(top, kf.Time)
			end
		end
	end
	local loop = if entry.loop ~= nil then entry.loop else ks.Loop
	local frames = math.max(1, math.floor(last * FPS + 0.5)) + (if loop then 0 else 1)
	local joints = {}
	for joint, keys in tracks do
		table.sort(keys, function(x, y)
			return x.t < y.t
		end)
		local list = table.create(frames)
		for f = 0, frames - 1 do
			local cf = trackAt(keys, f / FPS)
			list[f + 1] = if joint == "Root" then CFrame.new(cf.Position / R15_UNIT) * cf.Rotation else cf
		end
		joints[joint] = list
	end
	return clip(name, joints, frames, loop)
end

-- An authored pose: keys of joint angles in degrees (CFrame.Angles X, Y, Z, as in the game's OriginalClips); Root may
-- add a translation in hip units ([x, y, z, px, py, pz]). Each joint eases from one key that names it to the next;
-- an empty first key at t = 0 starts every joint from rest.
local function bakeKeys(name: string, entry: any): any
	local keys = entry.keys
	local loop = entry.loop == true
	local frames = math.max(1, math.floor(keys[#keys].t * FPS + 0.5)) + (if loop then 0 else 1)
	local tracks = {}
	for _, k in keys do
		for j, v in k.joints do
			tracks[j] = tracks[j] or {}
			table.insert(tracks[j], { t = k.t, cf = CFrame.new(v[4] or 0, v[5] or 0, v[6] or 0)
				* CFrame.Angles(math.rad(v[1]), math.rad(v[2] or 0), math.rad(v[3] or 0)) })
		end
	end
	if keys[1].t == 0 and next(keys[1].joints) == nil then
		for _, list in tracks do
			table.insert(list, 1, { t = 0, cf = IDENTITY })
		end
	end
	local joints = {}
	for j, list in tracks do
		joints[j] = table.create(frames)
		for f = 0, frames - 1 do
			local t = f / FPS
			local cf = list[#list].cf
			if t <= list[1].t then
				cf = list[1].cf
			else
				for i = 1, #list - 1 do
					if t < list[i + 1].t then
						cf = list[i].cf:Lerp(list[i + 1].cf, A.smooth((t - list[i].t) / (list[i + 1].t - list[i].t)))
						break
					end
				end
			end
			joints[j][f + 1] = cf
		end
	end
	return clip(name, joints, frames, loop)
end

local moves = {}
-- A move from library.json human_moves: { clip, entry, natural } (natural: studs per second of travel the move
-- covers at its own rate, for locomotion, at actor scale 1).
function Humans.move(name: string): any
	if moves[name] then
		return moves[name]
	end
	local entry = (library.human_moves or {})[name]
	assert(entry, `human move {name} is not in library.json human_moves`)
	local c
	if entry.clip then
		local _, lib = clipsModule()
		c = lib[entry.clip]
		assert(c, `human move {name}: the game has no clip {entry.clip}`)
	elseif entry.keys then
		c = bakeKeys(name, entry)
	else
		local ks
		if entry.catalog then
			local key = remote():InvokeServer("emote", entry.catalog)
			ks = store():WaitForChild(key, 20)
		else
			ks = KeyframeSequenceProvider:GetKeyframeSequenceAsync(`rbxassetid://{entry.animation}`)
		end
		assert(ks and ks:IsA("KeyframeSequence"), `human move {name}: no animation`)
		c = bakeSequence(name, ks, entry)
	end
	moves[name] = { clip = c, entry = entry, natural = entry.speed or (c.speed * 2) }
	return moves[name]
end

-- R6 -------------------------------------------------------------------------------------------------------
-- Ported from the game's Presentation (chord, toR6): clips stay in R15 terms; each two-segment limb becomes one
-- block aimed from its root to its end, and the single R6 torso takes Root then Waist.

local function chord(upper: CFrame?, lower: CFrame?): CFrame
	local u = (upper or IDENTITY).Rotation
	if not lower then
		return u
	end
	local along = u:VectorToWorldSpace(DOWN)
	local target = along + (u * lower.Rotation):VectorToWorldSpace(DOWN)
	if target.Magnitude < 1e-6 then
		return u
	end
	target = target.Unit
	local axis = along:Cross(target)
	if axis.Magnitude < 1e-9 then
		return u
	end
	return CFrame.fromAxisAngle(axis.Unit, math.acos(math.clamp(along:Dot(target), -1, 1))) * u
end

local FOLD = {
	{ "LeftShoulder", "LeftElbow", "LeftWrist" }, { "RightShoulder", "RightElbow", "RightWrist" },
	{ "LeftHip", "LeftKnee", "LeftAnkle" }, { "RightHip", "RightKnee", "RightAnkle" },
}

local function about(rotation: CFrame, point: Vector3): CFrame
	return CFrame.new(point) * rotation * CFrame.new(-point)
end

local function toR6(pose: any, scale: number): any
	local root = pose.Root or IDENTITY
	local waist = (pose.Waist or IDENTITY).Rotation
	local unwaist = waist:Inverse()
	return {
		RootJoint = CFrame.new(root.Position) * about(root.Rotation, Vector3.new(0, -1, 0) * scale)
			* about(waist, Vector3.new(0, -0.6, 0) * scale),
		Neck = pose.Neck or IDENTITY,
		["Left Shoulder"] = pose.LeftShoulder or IDENTITY,
		["Right Shoulder"] = pose.RightShoulder or IDENTITY,
		["Left Hip"] = unwaist * (pose.LeftHip or IDENTITY).Rotation,
		["Right Hip"] = unwaist * (pose.RightHip or IDENTITY).Rotation,
	}
end

local MASKS = {
	upper = { Waist = true, Neck = true, LeftShoulder = true, LeftElbow = true, LeftWrist = true, RightShoulder = true,
		RightElbow = true, RightWrist = true },
	arms = { LeftShoulder = true, LeftElbow = true, LeftWrist = true, RightShoulder = true, RightElbow = true, RightWrist = true },
	right_arm = { RightShoulder = true, RightElbow = true, RightWrist = true },
	left_arm = { LeftShoulder = true, LeftElbow = true, LeftWrist = true },
	head = { Neck = true },
}
Humans.MASKS = MASKS

-- Gaits: the move each plays, its default travel speed (studs/s) and how long it takes to get up to speed.
local GAITS = {
	walk = { move = "walk", speed = 5.5, ramp = 0.4 },
	run = { move = "run", speed = 16, ramp = 0.5 },
	sprint = { move = "sprint", speed = 22, ramp = 0.6 },
	back = { move = "walk", speed = 3.5, ramp = 0.35, back = true },
}
Humans.GAITS = GAITS

-- Spawn --------------------------------------------------------------------------------------------------

-- The face, in head space (an R6 head is a rounded cylinder about 0.62 studs in radius at scale 1).
local FACE_R = 0.62
local function facePart(parent: Instance, name: string, shape: Enum.PartType?): BasePart
	local p = Instance.new("Part")
	p.Name = name
	p.Shape = shape or Enum.PartType.Block
	p.Color = INK
	p.Material = Enum.Material.SmoothPlastic
	p.Anchored, p.CanCollide, p.CanTouch, p.CanQuery, p.CastShadow = true, false, false, false, false
	p.Size = Vector3.one * 0.1
	p.Parent = parent
	return p
end

-- Painted face (owner, 2026-11-26: "actual facial features", the classic painted Roblox face of top videos): three
-- decal layers from our face kit (tools/faces.py; IDs in library.face_assets), swapped per frame in faceDecals.
local function makeDecalFace(head: BasePart, style: string): any?
	local kit = library.face_assets
	if not (kit and kit[style] and kit.mouths) then
		return nil
	end
	local face = { kit = kit, style = style, layers = {} }
	for z, layer in { "mouth", "eyes", "brows", "blush" } do
		local d = Instance.new("Decal")
		d.Name = `SS_face_{layer}`
		d.Face = Enum.NormalId.Front
		d.ZIndex = z
		d.Texture = ""
		d.Parent = head
		face.layers[layer] = d
	end
	return face
end

local function makeFace(model: Model, head: BasePart, style: string?): any
	local decal = head:FindFirstChild("face")
	if decal and decal:IsA("Decal") then
		decal.Transparency = 1
	end
	local painted = makeDecalFace(head, style or "boy")
	if painted then
		return painted
	end
	local folder = Instance.new("Model")
	folder.Name = "SS_face"
	folder.Parent = model
	local face = { eyes = {}, brows = {}, mouth = {} }
	for _, s in { -1, 1 } do
		table.insert(face.eyes, { side = s, part = facePart(folder, "Eye", Enum.PartType.Ball) })
		table.insert(face.brows, { side = s, part = facePart(folder, "Brow") })
		table.insert(face.mouth, { side = s, part = facePart(folder, "Mouth", Enum.PartType.Ball) })
	end
	return face
end

-- The game's blaster (StarterPack.Blaster), copied into the actor and carried in the right hand as an R6 tool is.
local GRIP = CFrame.new(0, -1, 0) * CFrame.Angles(-math.pi / 2, 0, 0)
local function makeBlaster(model: Model, loaded: string?): any?
	local tool = StarterPack:FindFirstChild("Blaster")
	if not (tool and tool:IsA("Tool")) then
		warn("[SlugshotScene] StarterPack.Blaster not found; human actor has no blaster")
		return nil
	end
	local copy = tool:Clone()
	local handle = copy:FindFirstChild("Handle") :: BasePart
	local gun = Instance.new("Model")
	gun.Name = "SS_blaster"
	local parts, tip, tipY = {}, -math.huge, {}
	for _, d in copy:GetDescendants() do
		if d:IsA("LuaSourceContainer") then
			d:Destroy()
		elseif d:IsA("JointInstance") or d:IsA("WeldConstraint") then
			d.Enabled = false
		end
	end
	for _, d in copy:GetDescendants() do
		if d:IsA("BasePart") then
			d.Anchored, d.CanCollide, d.CanTouch, d.CanQuery, d.CastShadow = true, false, false, false, false
			local rel = handle.CFrame:ToObjectSpace(d.CFrame)
			-- The chamber holds a model of every slug (Floppy, InfernoLoaded, ...); only the loaded one shows.
			local slug = d:FindFirstAncestorOfClass("Model")
			while slug and slug.Parent ~= copy do
				slug = slug:FindFirstAncestorOfClass("Model")
			end
			local hidden = slug ~= nil and not (loaded and string.sub(slug.Name, 1, #loaded) == loaded)
			table.insert(parts, { part = d, rel = rel, transparency = if hidden then 1 else d.Transparency })
			if not d:FindFirstAncestorOfClass("Model") then -- the gun body, not the slugs shown in its chamber
				local reach = rel.Z + math.abs(rel:VectorToWorldSpace(Vector3.zAxis * d.Size.Z / 2).Z)
				if reach > tip then
					tip = reach
				end
				table.insert(tipY, { reach, rel.Y })
			end
		end
	end
	for _, c in copy:GetChildren() do
		c.Parent = gun
	end
	copy:Destroy()
	gun.Parent = model
	-- This blaster's barrel runs along the handle's +Z, the opposite of Roblox's tool convention (owner, 2026-11-26:
	-- held with the standard grip it pointed back "inside of their arm"). The hold turns it about the grip point
	-- (GRIP_FLIP below); the flash sits just past the barrel tip, at the barrel's height.
	local sum, n = 0, 0
	for _, e in tipY do
		if e[1] > tip - 0.35 then
			sum, n = sum + e[2], n + 1
		end
	end
	local muzzle = CFrame.new(0, if n > 0 then sum / n else 0, tip + 0.15)
	local flash = facePart(gun, "SS_flash", Enum.PartType.Ball)
	flash.Color = Color3.fromRGB(255, 226, 120)
	flash.Material = Enum.Material.Neon
	flash.Size = Vector3.one * 0.55
	flash.Transparency = 1
	local light = Instance.new("PointLight")
	light.Color, light.Range, light.Brightness, light.Shadows, light.Enabled = flash.Color, 10, 3, false, false
	light.Parent = flash
	return { model = gun, parts = parts, grip = tool.Grip, muzzle = muzzle, flash = flash, light = light, shown = nil }
end

function Humans.spawn(name: string, def: any, parent: Instance): any
	local look = def.look or (library.humans or {})[def.human or ""]
	assert(look, `actor {name}: a human needs 'human' (a library.json humans entry) or its own 'look'`)
	local key = remote():InvokeServer("rig", `SS_{name}`, look)
	local source = store():WaitForChild(key, 20)
	assert(source, `actor {name}: the marketing server built no rig (is this the marketing place, in play mode?)`)
	local model = (source :: Model):Clone()
	model.Name = `SS_actor_{name}`
	model:SetAttribute("SlugshotActor", name)
	for _, d in model:GetDescendants() do
		if d:IsA("LuaSourceContainer") then
			d:Destroy()
		end
	end
	local humanoid = model:FindFirstChildOfClass("Humanoid")
	if humanoid then
		humanoid.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
		humanoid.HealthDisplayType = Enum.HumanoidHealthDisplayType.AlwaysOff
		humanoid.RequiresNeck, humanoid.BreakJointsOnDeath, humanoid.EvaluateStateMachine = false, false, false
	end
	local scale = def.scale or 1
	if scale ~= 1 then
		model:ScaleTo(scale)
	end
	local hrp = model:FindFirstChild("HumanoidRootPart") :: BasePart
	local head = model:FindFirstChild("Head") :: BasePart
	local leg = model:FindFirstChild("Left Leg") :: BasePart
	assert(hrp and head and leg, `actor {name}: not an R6 rig`)
	model.PrimaryPart = hrp -- the built rig pivots on its head; follow shots track the steady root instead

	-- Forward kinematics order: every joint and weld, walked out from the root part.
	local edges = {}
	for _, j in model:GetDescendants() do
		if j:IsA("JointInstance") and j.Part0 and j.Part1 then
			edges[j.Part0] = edges[j.Part0] or {}
			edges[j.Part1] = edges[j.Part1] or {}
			table.insert(edges[j.Part0], { to = j.Part1, j = j, forward = true })
			table.insert(edges[j.Part1], { to = j.Part0, j = j, forward = false })
		end
	end
	local order, seen, queue = {}, { [hrp] = true }, { hrp }
	while #queue > 0 do
		local p = table.remove(queue, 1)
		for _, e in edges[p] or {} do
			if not seen[e.to] then
				seen[e.to] = true
				table.insert(queue, e.to)
				local j = e.j
				table.insert(order, {
					parent = p, part = e.to, forward = e.forward, c0 = j.C0, c1 = j.C1,
					joint = if e.forward and j:IsA("Motor6D") then j.Name else nil,
					frames = { j.C0.Rotation:Inverse(), j.C1.Rotation },
				})
			end
		end
	end
	for _, d in model:GetDescendants() do
		if d:IsA("JointInstance") then
			d.Enabled = false
		elseif d:IsA("BasePart") then
			d.Anchored, d.CanCollide, d.CanTouch, d.CanQuery = true, false, false, false
			-- body parts ground the character with their shadow; the head and hair don't block its own face
			d.CastShadow = d ~= head and not d:FindFirstAncestorOfClass("Accessory")
		end
	end
	hrp.Transparency = 1

	local face = makeFace(model, head, look.face_style)
	local blaster = if def.blaster ~= nil then makeBlaster(model, def.loaded) else nil
	-- Character lighting, as for slugs: a soft shadowless fill in front of the face (def.fill: brightness, 0 = off).
	local fill = if def.fill ~= nil then def.fill else 0.35
	if fill > 0 then
		local at = Instance.new("Attachment")
		at.Name = "SS_fill"
		at.Position = Vector3.new(0, 1.7, -2.6) * scale
		at.Parent = hrp
		local light = Instance.new("PointLight")
		light.Shadows, light.Brightness, light.Range = false, fill, 7.5 * scale
		light.Color = Color3.fromRGB(255, 244, 232)
		light.Parent = at
	end
	if def.outline ~= false then
		local h = Instance.new("Highlight")
		h.FillTransparency = 1
		h.OutlineColor = INK
		h.OutlineTransparency = 0
		h.DepthMode = Enum.HighlightDepthMode.Occluded
		h.Parent = model
	end
	model.Parent = parent

	local unit = leg.Size.Y -- R6 hip unit: the leg's length
	local stand = unit + hrp.Size.Y / 2
	local height = stand + hrp.Size.Y / 2 + head.Size.Y
	return {
		name = name, def = def, model = model, human = true, scale = scale, unit = unit, stand = stand,
		height = height, eye = height - head.Size.Y * 0.45, size = Vector3.new(2, height, 1) * Vector3.new(scale, 1, scale),
		lift = 0, species = nil, bones = {}, all = {},
		rig = { hrp = hrp, head = head, order = order, torso = model:FindFirstChild("Torso"),
			arms = { right = model:FindFirstChild("Right Arm"), left = model:FindFirstChild("Left Arm") },
			legs = { leg, model:FindFirstChild("Right Leg") } },
		face = face, blaster = blaster,
	}
end

-- Tracks -------------------------------------------------------------------------------------------------

-- Travel along one move at tau seconds in: an even acceleration up to cruising speed, then down to a stop.
local function profile(m: any, tau: number): (number, number)
	tau = math.clamp(tau, 0, m.d)
	local r, v = m.r, m.v
	if r <= 0 then
		return m.len * tau / m.d, if tau < m.d then v else 0
	elseif tau < r then
		return 0.5 * v * tau * tau / r, v * tau / r
	elseif tau < m.d - r then
		return 0.5 * v * r + v * (tau - r), v
	end
	local left = m.d - tau
	return m.len - 0.5 * v * left * left / r, v * left / r
end

local function blinkSchedule(actor: any): { number }
	local tr = actor.tracks
	local times = table.clone(tr.blinks)
	local seed = #actor.name * 1.71
	local at = 0.9 + (seed % 1.7)
	while at < 180 do
		table.insert(times, at)
		at += 2.4 + ((at * 5.31 + seed) % 2.2)
	end
	-- people blink as they turn to look at someone
	for _, e in tr.looks do
		if e.explicit then
			table.insert(times, e.t + 0.02)
		end
	end
	return times
end

local function positionAt(moves: { any }, home: Vector3, t: number): Vector3
	local pos = home
	for _, m in moves do
		if t < m.t then
			break
		end
		local s = profile(m, t - m.t)
		pos = if m.len > 1e-3 then m.from:Lerp(m.to, s / m.len) else m.to
	end
	return pos
end

-- Runs after Actors.compile (which gives looks, faces, expression channels and speech) for human-only tracks.
function Humans.compile(actor: any, beats: { any }, place: (string, any) -> CFrame)
	local tr = actor.tracks
	local list = {}
	for _, b in beats do
		if b.actor == actor.name and b.action == "move_to" then
			table.insert(list, b)
		end
	end
	table.sort(list, function(x, y)
		return x.time < y.time
	end)
	tr.moves = {}
	local travelled = 0
	for _, b in list do
		local gait = GAITS[b.gait or "walk"]
		assert(gait, `{actor.name}: unknown gait {b.gait}`)
		local from = positionAt(tr.moves, tr.home.Position, b.time)
		local to = place(b.mark, actor).Position
		local len = Vector3.new(to.X - from.X, 0, to.Z - from.Z).Magnitude
		local speed = (b.speed or gait.speed) * actor.scale
		local d = b.duration or (len / speed + gait.ramp)
		local r = math.min(gait.ramp, d / 2)
		table.insert(tr.moves, {
			t = b.time, d = d, r = r, v = if d - r > 1e-3 then len / (d - r) else 0, len = len, from = from, to = to,
			s0 = travelled, gait = b.gait or "walk", turn = b.turn ~= false and not gait.back,
		})
		travelled += len
	end
	tr.gestures, tr.aims, tr.shots, tr.holds, tr.gear, tr.slugShots = {}, {}, {}, {}, {}, {}
	for _, b in beats do
		if b.actor ~= actor.name then
			continue
		end
		local a = b.action
		if a == "gesture" then
			local m = Humans.move(b.move)
			local speed = b.speed or m.entry.rate or 1
			local d = b.duration or (m.clip.duration / speed)
			table.insert(tr.gestures, {
				t = b.time, d = d, clip = m.clip, speed = speed, from = b.from or 0, weight = b.weight or m.entry.weight or 1,
				mask = MASKS[b.mask or m.entry.mask or "full"], fade = b.fade or m.entry.fade or 0.25,
			})
		elseif a == "aim" or a == "point" then
			table.insert(tr.aims, { t = b.time, d = b.duration or 2, target = b.target, hand = b.hand or "right",
				two = a == "aim" and b.two_hands ~= false, fade = b.fade or 0.25 })
		elseif a == "shoot" then
			table.insert(tr.shots, b.time)
			if b.slug then
				table.insert(tr.slugShots, b) -- planned at first pose, when the muzzle can be placed (Shots.luau)
			end
		elseif a == "hold" then
			table.insert(tr.holds, { t = b.time, d = b.duration, item = b.item, hand = b.hand or "right", fade = b.ease or 0.35 })
		elseif a == "equip" or a == "holster" then
			table.insert(tr.gear, { t = b.time, on = a == "equip" })
		end
	end
	for _, l in { tr.gestures, tr.aims, tr.holds, tr.gear } do
		table.sort(l, function(x, y)
			return x.t < y.t
		end)
	end
	table.sort(tr.shots)
	tr.blinkTimes = blinkSchedule(actor)
	-- load every move now, not mid-take
	Humans.move("stand")
	for _, g in GAITS do
		Humans.move(g.move)
	end
end

-- Where the actor stands at t, plus the unwrapped yaw and travel state the pose needs. Pure.
local function stateAt(actor: any, t: number, where: any): (CFrame, number, number, number, string, number)
	local tr = actor.tracks
	local pos = tr.home.Position
	local yaw = select(2, tr.home:ToEulerAnglesYXZ())
	local s, v, gait, vmax = 0, 0, "walk", 0
	for _, m in tr.moves do
		if t < m.t then
			break
		end
		local sm, vm = profile(m, t - m.t)
		if m.turn and m.len > 0.2 then
			yaw += A.shortest(yaw, A.yawTo(m.from, m.to)) * A.smooth((t - m.t) / math.min(0.35, m.d))
		end
		pos = if m.len > 1e-3 then m.from:Lerp(m.to, sm / m.len) else m.to
		s, gait = m.s0 + sm, m.gait
		if t - m.t < m.d then
			v, vmax = vm, m.v
		end
	end
	for _, f in tr.faces do
		if t < f.t then
			break
		end
		yaw += A.shortest(yaw, A.yawTo(pos, where(f.target, f.t))) * A.smooth((t - f.t) / f.d)
	end
	return CFrame.new(pos) * CFrame.Angles(0, yaw, 0), yaw, s, v, gait, vmax
end

function Humans.frameAt(actor: any, t: number, where: any): CFrame
	return (stateAt(actor, t, where))
end

-- Head angles toward a target in the actor's own frame (a person turns further than a slug).
local function angles(actor: any, frame: CFrame, target: string?, t: number, where: any): (number, number)
	if not target or target == "none" then
		return 0, 0
	end
	local d = frame:VectorToObjectSpace(where(target, t) - (frame * CFrame.new(0, actor.eye, 0)).Position)
	return math.clamp(math.atan2(-d.X, -d.Z), -1.3, 1.3), math.clamp(math.atan2(d.Y, Vector2.new(d.X, d.Z).Magnitude), -0.6, 0.6)
end

local function looking(actor: any, frame: CFrame, t: number, where: any, quick: boolean): (number, number)
	local cur, prev = nil, nil
	for _, e in actor.tracks.looks do
		if t < e.t then
			break
		end
		prev, cur = cur, e
	end
	if not cur then
		return 0, 0
	end
	local y1, p1 = angles(actor, frame, prev and prev.target, t, where)
	local y2, p2 = angles(actor, frame, cur.target, t, where)
	local k = A.smooth((t - cur.t) / (if quick then 0.12 else cur.ease))
	return y1 + (y2 - y1) * k, p1 + (p2 - p1) * k
end

local function envelope(t: number, start: number, d: number, fade: number): number
	if t < start or t > start + d + fade then
		return 0
	end
	return math.min(A.smooth((t - start) / fade), 1 - A.smooth((t - start - d) / fade))
end

local function blinkAt(actor: any, t: number): number
	local out = 0
	for _, b in actor.tracks.blinkTimes do
		local u = (t - b) / 0.17
		if u >= 0 and u < 1 then
			out = math.max(out, if u < 0.35 then u / 0.35 elseif u < 0.55 then 1 else (1 - u) / 0.45)
		end
	end
	return out
end

-- Recoil of each shot: a sharp kick, then a quick settle (radians of shoulder lift).
local function recoil(tr: any, t: number): number
	local k = 0
	for _, s in tr.shots do
		local u = t - s
		if u >= 0 and u < 0.6 then
			k += 0.32 * (if u < 0.04 then u / 0.04 else math.exp(-(u - 0.04) / 0.09))
		end
	end
	return k
end

-- The rotation that turns a hanging arm (rest: pointing down) to point along `dir` (torso space).
local function pointArm(dir: Vector3): CFrame
	dir = dir.Unit
	local axis = DOWN:Cross(dir)
	if axis.Magnitude < 1e-6 then
		return if dir.Y < 0 then IDENTITY else CFrame.Angles(math.pi, 0, 0)
	end
	return CFrame.fromAxisAngle(axis.Unit, math.acos(math.clamp(DOWN:Dot(dir), -1, 1)))
end

local function fk(actor: any, root: CFrame, r6: any): { [BasePart]: CFrame }
	local cf = { [actor.rig.hrp] = root }
	for _, l in actor.rig.order do
		local p = cf[l.parent]
		if l.forward then
			local tr = if l.joint then l.frames[1] * (r6[l.joint] or IDENTITY) * l.frames[2] else IDENTITY
			cf[l.part] = p * l.c0 * tr * l.c1:Inverse()
		else
			cf[l.part] = p * l.c1 * l.c0:Inverse()
		end
	end
	return cf
end

local CORNERS = {
	Vector3.new(0.5, -0.5, 0.5), Vector3.new(-0.5, -0.5, 0.5), Vector3.new(0.5, -0.5, -0.5), Vector3.new(-0.5, -0.5, -0.5),
}

local function shoulderAt(actor: any, torso: CFrame, side: number): Vector3
	return torso * (Vector3.new(1.5 * side, 0.5, 0) * actor.scale)
end

-- Everything the actor's body does at t: part CFrames (forward kinematics) and the face state. Cached per t, so a
-- held slug asking for the hand and the actor's own pose share one solve.
function Humans.solve(actor: any, t: number, where: any): any
	if actor._solved and actor._solved.t == t then
		return actor._solved
	end
	actor._busy = true
	local C = clipsModule()
	local tr = actor.tracks
	local frame, yaw, s, v, gait, vmax = stateAt(actor, t, where)
	local scale = actor.scale

	-- Locomotion: the gait's cycle advances with distance travelled (feet don't slide), blended up from standing
	-- with speed; turning on the spot shuffles the feet.
	local stand = Humans.move("stand")
	local g = GAITS[gait]
	local walk = Humans.move(g.move)
	local natural = walk.natural * scale
	local w = if vmax > 0 then A.smooth(v / (vmax * 0.6)) else 0
	local gaitTime = s / natural * (if g.back then -1 else 1)
	local _, y0 = stateAt(actor, t - 0.05, where)
	local _, y1 = stateAt(actor, t + 0.05, where)
	local step = math.clamp(math.abs(y1 - y0) / 0.1 / 3, 0, 0.6) * (1 - w)
	local walkMove = Humans.move("walk")
	local pose = C.blend({
		C.sample(stand.clip, t + (actor.def.phase or 0)),
		C.sample(walk.clip, gaitTime),
		C.sample(walkMove.clip, math.abs(yaw) * 0.45 * scale / (walkMove.natural * scale)),
	}, { math.max(0, 1 - w - step), w, step })

	-- Gestures, each over its body mask, eased in and out.
	for _, ge in tr.gestures do
		local e = envelope(t, ge.t, ge.d, ge.fade) * ge.weight
		if e > 1e-3 then
			local sample = C.sample(ge.clip, (t - ge.t) * ge.speed + ge.from)
			for joint, value in sample do
				if not ge.mask or ge.mask[joint] then
					pose[joint] = (pose[joint] or IDENTITY):Lerp(value, e)
				end
			end
		end
	end

	-- Expression and speech: lean, chin, the nod that follows phrases.
	local ch = tr.ch
	local open, nod = A.speech(tr, t)
	local lean = A.channel(ch.lean, t, 0)
	pose.Waist = CFrame.Angles(-lean * 0.3, 0, 0) * (pose.Waist or IDENTITY)
	pose.Neck = CFrame.Angles(A.channel(ch.look_up, t, 0) * 0.35 - nod * 0.14, 0, 0) * (pose.Neck or IDENTITY)

	-- Eyeline: the eyes get there first, then the head, with the chest following a little.
	local headYaw, headPitch = looking(actor, frame, t, where, false)
	local eyeYaw, eyePitch = looking(actor, frame, t, where, true)
	pose.Waist = CFrame.Angles(0, headYaw * 0.3, 0) * pose.Waist
	pose.Neck = CFrame.Angles(0, headYaw * 0.7, 0) * CFrame.Angles(headPitch * 0.8, 0, 0) * pose.Neck

	-- Fold onto R6 (rotation-only limbs), root translation from hip units to studs.
	for _, limb in FOLD do
		pose[limb[1]] = chord(pose[limb[1]], pose[limb[2]])
		pose[limb[2]], pose[limb[3]] = nil, nil
	end
	local root = pose.Root or IDENTITY
	pose.Root = CFrame.new(root.Position * actor.unit) * root.Rotation
	local r6 = toR6(pose, scale)
	local rootCF = frame * CFrame.new(0, actor.stand, 0)
	local parts = fk(actor, rootCF, r6)
	-- Feet push out of the floor and never pull the body down (the game's GroundContact.PullDown = false): block
	-- legs lift clear in the stride, as in classic Roblox walks.
	local low = math.huge
	for _, leg in actor.rig.legs do
		for _, c in CORNERS do
			low = math.min(low, (parts[leg] * (leg.Size * c)).Y)
		end
	end
	if low < frame.Position.Y then
		rootCF += Vector3.new(0, frame.Position.Y - low, 0)
		parts = fk(actor, rootCF, r6)
	end
	local torso = parts[actor.rig.torso]

	-- Arms that point at something: aiming (two-handed, with recoil), pointing, and holding a slug out in front.
	local kick = recoil(tr, t)
	local function arm(side: number, point: Vector3, weight: number, extra: CFrame?)
		local name = if side > 0 then "Right Shoulder" else "Left Shoulder"
		local r = pointArm(torso:VectorToObjectSpace(point - shoulderAt(actor, torso, side)))
		if extra then
			r = extra * r
		end
		r6[name] = (r6[name] or IDENTITY):Lerp(r, weight)
	end
	local function tip(side: number): Vector3
		local name = if side > 0 then "Right Shoulder" else "Left Shoulder"
		return shoulderAt(actor, torso, side) + torso:VectorToWorldSpace((r6[name] or IDENTITY) * DOWN) * 2 * scale
	end
	local moved = false
	for _, h in tr.holds do
		local e = envelope(t, h.t, h.d, h.fade)
		if e > 1e-3 then
			-- One hand held out, palm up, a little below level so the slug sits on top of it. (Two-handed holds left the
			-- slug floating between the hands, owner 2026-11-26; a slug sits on one hand or a shoulder instead.) A
			-- shoulder perch leaves the arms free.
			if h.hand ~= "shoulder" then
				moved = true
				local side = if h.hand == "left" then -1 else 1
				arm(side, torso * (Vector3.new(0.95 * side, -0.55, -2.0) * scale), e)
			end
		end
	end
	for _, a in tr.aims do
		local e = envelope(t, a.t, a.d, a.fade)
		if e > 1e-3 then
			moved = true
			local target = where(a.target, t)
			local side = if a.hand == "left" then -1 else 1
			arm(side, target, e, if a.two then CFrame.Angles(kick, 0, 0) else nil)
			if a.two then
				-- the support hand meets the gun just ahead of the trigger hand
				local hand = tip(side)
				arm(-side, hand + (target - hand).Unit * 0.35 * scale, e)
			end
		end
	end
	if moved then
		parts = fk(actor, rootCF, r6)
		torso = parts[actor.rig.torso]
	end

	local face = {
		blink = blinkAt(actor, t), react = A.channel(ch.react, t, 0), smile = A.channel(ch.smile, t, 0),
		angry = A.channel(ch.angry, t, 0), squint = A.channel(ch.squint, t, 0), smirk = A.channel(ch.smirk, t, 0),
		open = math.clamp(open + A.channel(ch.open, t, 0), 0, 1),
		gazeX = math.clamp((eyeYaw - headYaw) / 0.45, -1, 1), gazeY = math.clamp((eyePitch - headPitch) / 0.35, -1, 1),
	}
	actor._solved = { t = t, parts = parts, face = face, frame = frame, r6 = r6 }
	actor._busy = false
	return actor._solved
end

-- The face on the head's curved front: eyes (blink, squint, wide, glance), brows (raised, knitted) and a two-piece
-- mouth (talks with the speech envelope; its halves tilt up into a smile or down into a frown).
local function surface(x: number): number
	return -math.sqrt(FACE_R * FACE_R - x * x)
end

local function onFace(head: CFrame, k: number, x: number, y: number, depth: number, roll: number): CFrame
	return head * CFrame.new(Vector3.new(x, y, surface(x) + depth) * k) * CFrame.Angles(0, -math.asin(x / FACE_R), roll)
end

-- Which painted layers show at this moment. Thresholds, not blends: painted faces switch, as in Roblox videos.
local function faceDecals(face: any, f: any)
	local kit = face.kit
	local style = kit[face.style]
	local react, angry, smile, squint = f.react, f.angry, f.smile, math.clamp(f.squint, 0, 1)
	local eyes = if f.blink > 0.5 then "closed"
		elseif react > 0.6 then "wide"
		elseif smile > 0.85 and f.open < 0.15 then "happy"
		elseif squint > 0.35 or f.smirk > 0.5 then "half"
		elseif f.gazeX > 0.45 then "left"
		elseif f.gazeX < -0.45 then "right"
		else "open"
	local brows = if angry > 0.4 then "angry"
		elseif react > 0.4 then "raised"
		elseif squint > 0.3 and smile <= 0.2 then "skeptic"
		elseif smile < -0.4 then "sad"
		else "neutral"
	local mouth
	if f.open > 0.5 then
		mouth = if smile > 0.3 then "talk_smile" else "talk_wide"
	elseif f.open > 0.18 then
		mouth = if smile > 0.5 then "talk_smile" else "talk_small"
	elseif react > 0.6 then
		mouth = "o"
	elseif angry > 0.4 or smile < -0.3 then
		mouth = "frown"
	elseif f.smirk > 0.5 then
		mouth = "smirk"
	elseif smile > 0.75 then
		mouth = "grin"
	elseif smile > 0.3 then
		mouth = "smile"
	elseif squint > 0.3 then
		mouth = "flat"
	else
		mouth = "neutral"
	end
	local want = { eyes = style.eyes[eyes], brows = style.brows[brows], mouth = kit.mouths[mouth],
		blush = if face.style == "girl" and smile > 0.75 then kit.mouths.blush else "" }
	for layer, id in want do
		local d = face.layers[layer]
		if d.Texture ~= (id or "") then
			d.Texture = id or ""
		end
	end
end

local function faceFrames(actor: any, head: CFrame, f: any, list: { BasePart }, cfs: { CFrame })
	if actor.face.kit then
		faceDecals(actor.face, f)
		return
	end
	local k = actor.scale
	local react, angry = math.clamp(f.react, 0, 1), math.clamp(f.angry, 0, 1)
	local gx, gy = -f.gazeX * 0.035, f.gazeY * 0.025
	for _, e in actor.face.eyes do
		local x = 0.19 * e.side + gx
		local h = 0.2 * (1 + 0.18 * react) * (1 - 0.4 * math.clamp(f.squint, 0, 1)) * (1 - 0.9 * f.blink)
		e.part.Size = Vector3.new(0.12 * (1 + 0.1 * react), math.max(h, 0.018), 0.08) * k
		table.insert(list, e.part)
		table.insert(cfs, onFace(head, k, x, 0.07 + gy, 0.015, 0))
	end
	for _, b in actor.face.brows do
		b.part.Size = Vector3.new(0.2, 0.045, 0.04) * k
		table.insert(list, b.part)
		table.insert(cfs, onFace(head, k, 0.2 * b.side, 0.27 + 0.06 * react - 0.035 * angry, 0, b.side * (-0.1 - 0.45 * angry + 0.12 * react)))
	end
	local open = f.open
	for _, m in actor.face.mouth do
		-- the halves close up into one oval as the mouth opens
		m.part.Size = Vector3.new(0.15 + 0.02 * open, 0.045 + 0.13 * open, 0.06) * k
		table.insert(list, m.part)
		table.insert(cfs, onFace(head, k, (0.06 - 0.04 * open) * m.side, -0.2 - 0.025 * open, 0.01,
			m.side * math.clamp(f.smile, -1, 1) * 0.42 * (1 - 0.6 * open)))
	end
end

local GRIP_ANGLE = CFrame.Angles(-math.pi / 2, 0, 0)
local GRIP_FLIP = CFrame.Angles(0, math.pi, 0) -- see makeBlaster: the barrel faces the handle's +Z

local function gunHandle(actor: any, st: any): CFrame
	local grip = actor.blaster.grip
	return st.parts[actor.rig.arms.right] * CFrame.new(0, -actor.scale, 0) * GRIP_ANGLE * grip:Inverse()
		* CFrame.new(grip.Position) * GRIP_FLIP * CFrame.new(-grip.Position)
end

-- The blaster muzzle in the world at t (where a slug shot leaves from).
function Humans.muzzleAt(actor: any, t: number, where: any): Vector3
	local st = Humans.solve(actor, t, where)
	actor._solved = nil -- a look-ahead: don't keep it as the current pose
	return (gunHandle(actor, st) * actor.blaster.muzzle).Position
end

local function plans(actor: any, where: any): { any }
	local tr = actor.tracks
	if not tr.shotPlans then
		tr.shotPlans = {}
		for _, b in tr.slugShots do
			table.insert(tr.shotPlans, Shots.plan(b, function(at)
				return Humans.muzzleAt(actor, at, where)
			end, where))
		end
	end
	return tr.shotPlans
end

-- The n-th slug shot's flying slug at t (for the slug_shot camera), or nil.
-- The n-th slug shot's plan (launch time t, flight, species, from, to) and its twirl length (Shots.spin).
function Humans.shotPlan(actor: any, n: number, where: any): (any?, number?)
	local list = if actor.human and actor.blaster then plans(actor, where) else {}
	return list[n], if list[n] then Shots.spin(list[n]) else nil
end

function Humans.shotFrame(actor: any, n: number, t: number, where: any): CFrame?
	local list = if actor.human and actor.blaster then plans(actor, where) else {}
	return if list[n] then Shots.frameAt(list[n], t) else nil
end

function Humans.pose(actor: any, t: number, where: any)
	local st = Humans.solve(actor, t, where)
	local list, cfs = {}, {}
	for p, cf in st.parts do
		table.insert(list, p)
		table.insert(cfs, cf)
	end
	faceFrames(actor, st.parts[actor.rig.head], st.face, list, cfs)
	local gun = actor.blaster
	if gun then
		local on = actor.def.blaster == true
		for _, g in actor.tracks.gear do
			if t >= g.t then
				on = g.on
			end
		end
		if gun.shown ~= on then
			for _, p in gun.parts do
				p.part.Transparency = if on then p.transparency else 1
			end
			gun.shown = on
		end
		local handle = gunHandle(actor, st)
		for _, p in gun.parts do
			table.insert(list, p.part)
			table.insert(cfs, handle * p.rel)
		end
		-- No generic muzzle flash (owner, 2026-11-26): a shot is the slug itself leaving the blaster (Shots.luau).
		gun.flash.Transparency = 1
		gun.light.Enabled = false
	end
	workspace:BulkMoveTo(list, cfs, Enum.BulkMoveMode.FireCFrameChanged)
	local tr = actor.tracks
	if #tr.slugShots > 0 then
		Shots.pose(plans(actor, where), t, actor.model.Parent)
	end
end

-- Where a held slug sits at t: on top of the holding hand(s), facing its holder (or `facing = "out"`). A ground
-- frame, like Actors.frameAt's.
local function carryFrame(holder: any, t: number, where: any, hand: string, facing: string?): CFrame
	local k = holder.scale
	if holder._busy then
		-- asked while the holder is itself being solved (it is looking at what it holds): the hold pose's hand spot
		local f = stateAt(holder, t, where)
		return f * CFrame.new(0.9 * k, 2.6 * k, -1.9 * k) * CFrame.Angles(0, if facing == "out" then 0 else math.pi, 0)
	end
	local st = Humans.solve(holder, t, where)
	local p
	if hand == "shoulder" or hand == "shoulder_left" then
		-- on top of the shoulder, over the arm's top face
		local side = if hand == "shoulder_left" then -1 else 1
		p = st.parts[holder.rig.torso] * (Vector3.new(1.5 * side, 1.0, 0) * k)
	else
		-- the highest point of the hand end's surface: the slug's sole rests there, whatever the arm's angle
		local arm = st.parts[if hand == "left" then holder.rig.arms.left else holder.rig.arms.right]
		p = arm * (Vector3.new(0, -0.75, -0.5) * k)
		for _, c in { Vector3.new(0, -0.75, 0.5), Vector3.new(0.5, -0.75, 0), Vector3.new(-0.5, -0.75, 0) } do
			local q = arm * (c * k)
			if q.Y > p.Y then
				p = q
			end
		end
	end
	local yaw = select(2, st.frame:ToEulerAnglesYXZ()) + (if facing == "out" then 0 else math.pi)
	return CFrame.new(p) * CFrame.Angles(0, yaw, 0)
end

-- A slug actor's ground frame, carried while a human holds it (eased up into the hands and back down).
function Humans.carry(item: any, t: number, where: any, base: CFrame): CFrame
	for _, h in item.tracks.held do
		local holder = item.cast and item.cast[h.holder]
		local e = if holder then envelope(t, h.t, h.d, h.ease) else 0
		if e > 1e-3 then
			base = base:Lerp(carryFrame(holder, t, where, h.hand, h.facing), e)
		end
	end
	return base
end

return Humans
