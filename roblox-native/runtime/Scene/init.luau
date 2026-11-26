--!nonstrict
-- SlugshotScene: runs a declarative scene spec (roblox-native/scenes/**/*.json, validated by tools/scene.py
-- and built into the marketing place). Client side, during a playtest.
--
-- One engine: Scene.prepare builds the set and actors and returns frame(t), which poses every actor and the
-- camera as a pure function of scene time. Three drivers use it:
--   Scene.run(id, opts)    real-time preview (opts.speed, default 1); returns the take manifest
--   Scene.film(id, opts)   frame-stepped filming: scene frame i is held for opts.hold rendered frames and
--                          stamped with its index, so a recording that drops frames can be resampled to
--                          exact 30 fps (tools/take.py film). opts.portrait (default true) rolls the camera
--                          for native-resolution vertical video.
--   Scene.still(id, t)     poses everything at t and leaves the camera there (for a screenshot)
-- Every take builds its set and actors and destroys them afterwards (the reset).
local CollectionService = game:GetService("CollectionService")
local HttpService = game:GetService("HttpService")
local Lighting = game:GetService("Lighting")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local RunService = game:GetService("RunService")

local Root = ReplicatedStorage:WaitForChild("SlugshotMarketing")
local Reel = require(Root:WaitForChild("Reel"))
local Actors = require(script.Actors)
local Cameras = require(script.Cameras)
local Canon = require(script.Canon)
local Humans = require(script.Humans)
local FilmTime = require(Root:WaitForChild("FilmTime"))

local Scene = {}
Scene.FPS = 30

-- Slow motion (owner, 2026-11-26: the slug shot had "no emphasis ... not slowed down"). `slowmo` segments in a spec
-- ({from, until, rate, ramp}, scene seconds) play scene time at `rate`, easing in and out over `ramp`. The scene stays
-- written in scene time; the video's time is out(t) = t + the extra seconds the segments before t add, and frames
-- are filmed at out-times mapped back to scene time. Segments sit in dialogue gaps (tools/scene.py checks), so the
-- edit only adds silence there (take.py warp).
local function buildWarp(segments: { any }?, duration: number): any
	local list = {}
	for _, s in segments or {} do
		local a, b, rate = s.from, s["until"], s.rate
		local ramp = math.min(s.ramp or 0.08, (b - a) / 2)
		local function rateAt(t: number): number
			if t <= a or t >= b then
				return 1
			end
			local e = if t < a + ramp then Actors.smooth((t - a) / ramp)
				elseif t > b - ramp then Actors.smooth((b - t) / ramp)
				else 1
			return 1 - (1 - rate) * e
		end
		local n, h = 2000, (b - a) / 2000
		local cum = table.create(n + 1, 0)
		for i = 1, n do
			cum[i + 1] = cum[i] + (1 / rateAt(a + (i - 0.5) * h) - 1) * h
		end
		table.insert(list, { from = a, ["until"] = b, rate = rate, ramp = ramp, rateAt = rateAt, cum = cum, h = h, n = n,
			extra = cum[n + 1] })
	end
	table.sort(list, function(x, y)
		return x.from < y.from
	end)
	local total = 0
	for _, s in list do
		total += s.extra
	end
	local function outAt(t: number): number
		local out = t
		for _, s in list do
			if t >= s["until"] then
				out += s.extra
			elseif t > s.from then
				local x = (t - s.from) / s.h
				local i = math.floor(x)
				out += s.cum[i + 1] + (s.cum[math.min(i + 2, s.n + 1)] - s.cum[i + 1]) * (x - i)
			end
		end
		return out
	end
	local function sceneAt(out: number): number
		if total == 0 then
			return out
		end
		local lo, hi = math.max(0, out - total), out
		for _ = 1, 48 do
			local mid = (lo + hi) / 2
			if outAt(mid) < out then
				lo = mid
			else
				hi = mid
			end
		end
		return (lo + hi) / 2
	end
	local function rateAt(t: number): number
		for _, s in list do
			if t > s.from and t < s["until"] then
				return s.rateAt(t)
			end
		end
		return 1
	end
	return { segments = list, outAt = outAt, sceneAt = sceneAt, rateAt = rateAt, duration = outAt(duration) }
end

local function decode(module: Instance): any
	return HttpService:JSONDecode(require(module :: ModuleScript))
end

function Scene.list(): { string }
	local out = {}
	for _, m in Root.Scenes:GetChildren() do
		table.insert(out, m.Name)
	end
	table.sort(out)
	return out
end

function Scene.load(id: string): any
	-- Rehearsal: a spec validated by tools/scene.py (`scene.py json ID`) and handed to the playtest through
	-- _G.SlugshotSceneSpecs[id] replaces the built one until the place is rebuilt.
	local rehearsal = _G.SlugshotSceneSpecs and _G.SlugshotSceneSpecs[id]
	if rehearsal then
		return HttpService:JSONDecode(rehearsal)
	end
	local module = Root.Scenes:FindFirstChild(id)
	assert(module, `no scene {id}; built scenes: {table.concat(Scene.list(), ", ")}`)
	return decode(module)
end

local library = decode(Root:WaitForChild("Library"))
Actors.humans = Humans
Humans.bind(Actors, library)

local function v3(t: { number }): Vector3
	return Vector3.new(t[1], t[2] or 0, t[3] or 0)
end

local function now(): number
	return DateTime.now().UnixTimestampMillis
end

local function buildSet(set: any, parent: Instance): (CFrame, () -> ())
	if set.kind == "cyc" then
		local cyc = Reel.Cyc.build(parent, CFrame.new(v3(set.at or { 4000, 1500, 4000 })), { radius = set.radius })
		return cyc.top, cyc.destroy
	elseif set.kind == "place" then
		return CFrame.new(v3(set.origin)) * CFrame.Angles(0, math.rad(set.yaw or 0), 0), function() end
	end
	error(`unknown set kind {set.kind}`)
end

-- Film look: depth of field off (it blurs small subjects near the lens and turns off anti-aliasing), optional
-- per-scene light tweaks; everything restored afterwards.
local function applyLook(look: any?): () -> ()
	local undo = {}
	for _, root in { Lighting, workspace.CurrentCamera } do
		for _, e in root:GetDescendants() do
			if e:IsA("DepthOfFieldEffect") or e:IsA("BlurEffect") then
				table.insert(undo, { e, "Enabled", e.Enabled })
				e.Enabled = false
			end
		end
	end
	-- Close-ups sit far inside Roblox's shadow-map resolution: shadow edges on small faces render as hard pixel
	-- blocks (owner, 2026-11-25: "rectangular and blocky ... so stiff"). Soften them for the take.
	table.insert(undo, { Lighting, "ShadowSoftness", Lighting.ShadowSoftness })
	Lighting.ShadowSoftness = look and look.shadow_softness or 1
	-- Lamps and crystals keep their shadows (owner, 2026-11-25: "I still want the shadows"). The flashing first
	-- blamed on them came from the hub's clock running apart from scene time (see FilmClock); look.local_shadows =
	-- false still turns them off for a scene that needs it.
	if look and look.local_shadows == false then
		for _, e in workspace:GetDescendants() do
			if (e:IsA("PointLight") or e:IsA("SpotLight") or e:IsA("SurfaceLight")) and e.Shadows then
				table.insert(undo, { e, "Shadows", true })
				e.Shadows = false
			end
		end
	end
	if look then
		for key, value in look.lighting or {} do
			table.insert(undo, { Lighting, key, Lighting[key] })
			Lighting[key] = if type(value) == "table" then Color3.fromRGB(value[1], value[2], value[3]) else value
		end
	end
	return function()
		for i = #undo, 1, -1 do
			local u = undo[i]
			u[1][u[2]] = u[3]
		end
	end
end

function Scene.prepare(id: string, options: any?): any
	local opts = options or {}
	local spec = Scene.load(id)
	local ok, why = Canon.check(spec)
	assert(ok, `scene {id} rejected by canon check: {why}`)
	local dialogue = spec._dialogue

	local stage = Instance.new("Folder")
	stage.Name = `SS_scene_{spec.id}`
	stage.Parent = workspace
	local origin, destroySet = buildSet(spec.set, stage)

	local exclude = RaycastParams.new()
	exclude.FilterType = Enum.RaycastFilterType.Exclude
	local character = Players.LocalPlayer.Character
	exclude.FilterDescendantsInstances = { stage, character }

	local function mark(name: string): CFrame
		local m = spec.marks[name]
		assert(m, `unknown mark {name}`)
		return origin * CFrame.new(m[1], m[2] or 0, m[3] or 0) * CFrame.Angles(0, math.rad(m[4] or 0), 0)
	end
	-- Marks for actors sit on whatever ground is below them (sets keep marks relative; the floor decides height).
	local grounded = {}
	local function place(name: string, actor: any): CFrame
		local cf = mark(name)
		if spec.set.kind ~= "place" or (actor and actor.def.ground == false) then
			return cf
		end
		if not grounded[name] then
			local hit = workspace:Raycast(cf.Position + Vector3.new(0, 12, 0), Vector3.new(0, -40, 0), exclude)
			grounded[name] = if hit then hit.Position.Y else cf.Position.Y
		end
		return CFrame.new(cf.X, grounded[name], cf.Z) * cf.Rotation
	end

	local actors = {}
	for name, def in spec.actors or {} do
		actors[name] = Actors.spawn(name, def, stage)
	end
	for _, a in actors do
		a.cast = actors -- a held slug finds its holder
	end
	local where -- name, t -> Vector3 (an actor's head, or a mark)
	local function frameAt(name: string, t: number): CFrame
		local a = actors[name]
		return if a then Actors.frameAt(a, t, where) else mark(name)
	end
	local function headAt(name: string, t: number): Vector3
		local a = actors[name]
		if not a then
			return mark(name).Position
		end
		return (frameAt(name, t) * CFrame.new(0, a.eye or a.height * 0.72, 0)).Position
	end
	where = function(name: string, t: number): Vector3
		return headAt(name, t)
	end
	-- Initial facing: `face` on the actor def turns it toward an actor or mark on its first frame.
	for name, def in spec.actors or {} do
		Actors.compile(actors[name], spec.timeline or {}, place, dialogue)
		if def.face then
			local here = actors[name].tracks.home.Position
			local there = if spec.marks[def.face] then mark(def.face).Position else place(spec.actors[def.face].mark, actors[def.face]).Position
			local d = there - here
			actors[name].tracks.home = CFrame.new(here) * CFrame.Angles(0, math.atan2(-d.X, -d.Z), 0)
		end
	end

	local function ctxAt(start: number)
		return {
			Shot = Reel.Shot, Curve = Reel.Curve, seed = opts.seed or 1, start = start,
			-- a human's k-th slug shot in flight at scene time tt (the slug_shot camera)
			slug = function(n, k, tt)
				local a = actors[n]
				return if a and a.human then Humans.shotFrame(a, k or 1, tt, where) else nil
			end,
			shotPlan = function(n, k)
				local a = actors[n]
				if a and a.human then
					return Humans.shotPlan(a, k or 1, where)
				end
				return nil, nil
			end,
			frame = function(n) return frameAt(n, start) end,
			head = function(n) return headAt(n, start) end,
			height = function(n) return actors[n] and actors[n].height or 5 end,
			position = function(n) return frameAt(n, start).Position end,
			center = function(names)
				local sum = Vector3.zero
				for _, n in names do
					sum += frameAt(n, start).Position
				end
				return sum / #names
			end,
			target = function(n)
				return function(): CFrame?
					local a = actors[n]
					return if a and a.model.Parent then a.model:GetPivot() else nil
				end
			end,
		}
	end
	-- layer "b" films the second view of every split shot (a second pass; take.py split composites the two)
	local ctx = { Shot = Reel.Shot, Curve = Reel.Curve, seed = opts.seed or 1, at = ctxAt, layer = opts.layer or "a" }

	local shots, total = {}, 0
	for _, s in spec.shots do
		table.insert(shots, Cameras.build(s, ctx, total))
		total += s.duration
	end
	local warp = buildWarp(spec.slowmo, total)

	-- Impact accents (spec `fx`, scene seconds): a "flash" brightens the whole image and fades (a ColorCorrection,
	-- so it is lit like the world, not a white card); a "shake" jolts the camera and settles. Both are pure in t.
	local grade = Instance.new("ColorCorrectionEffect")
	grade.Name = "SS_fx"
	grade.Parent = Lighting
	local function accents(t: number, cf: CFrame): CFrame
		local bright, contrast, tint = 0, 0, Color3.new(1, 1, 1)
		for i, f in spec.fx or {} do
			local u = (t - f.at) / (f.duration or 0.3)
			if u < 0 or u >= 1 then
				continue
			end
			local k = (1 - u) ^ 2
			if f.type == "flash" then
				bright += (f.strength or 0.45) * k
				contrast += 0.25 * k
				local c = f.tint or { 255, 236, 205 }
				tint = Color3.new(1, 1, 1):Lerp(Color3.fromRGB(c[1], c[2], c[3]), k)
			elseif f.type == "shake" then
				local a, w = (f.amplitude or 0.25) * k, (f.rate or 22) * (t - f.at)
				cf = cf * CFrame.new(a * math.noise(w, i, 0.5), a * math.noise(w, i, 7.5), 0)
					* CFrame.Angles(0, 0, a * 0.12 * math.noise(w, i, 13.5))
			end
		end
		grade.Brightness, grade.Contrast, grade.TintColor = bright, contrast, tint
		return cf
	end

	local events = {}
	for _, b in spec.timeline or {} do
		if b.cue or b.marker then
			table.insert(events, b)
		end
	end
	table.sort(events, function(a, b)
		return a.time < b.time
	end)

	local portrait = opts.portrait
	local camera = workspace.CurrentCamera
	local lock = nil
	-- The hub's look-only motion (drifting islands and their sun shadows, lamp pulses, lava) follows scene time
	-- through workspace.FilmClock (a marketing patch to the game's HubMotion), so every pass and patch of a take
	-- agrees. world.clock picks where in their cycle the take happens.
	local worldClock = spec.world and spec.world.clock or 60
	local lastT = -math.huge
	local function frame(t: number): (CFrame, number, number)
		workspace:SetAttribute("FilmClock", worldClock + t)
		-- The game's effect modules run on this (FilmTime); going back in time drops what was born later.
		if t < lastT then
			FilmTime.rewind(t)
		end
		lastT = t
		workspace:SetAttribute("FilmNow", t)
		local speaker = Actors.speakerAt(dialogue, t)
		for _, a in actors do
			Actors.pose(a, t, where, speaker)
		end
		local index, shot = #shots, shots[#shots]
		for i, s in shots do
			if t < s.start + s.duration then
				index, shot = i, s
				break
			end
		end
		local lt = math.clamp(t - shot.start, 0, shot.duration)
		if shot.clock == "output" and shot.duration > 0 then
			-- a camera that keeps moving at the video's pace through slow motion (bullet-time orbits)
			local a, b = warp.outAt(shot.start), warp.outAt(shot.start + shot.duration)
			lt = math.clamp((warp.outAt(t) - a) / math.max(b - a, 1e-6), 0, 1) * shot.duration
		end
		local cf, fov = shot.pose(lt)
		cf = accents(t, cf)
		workspace:SetAttribute("FilmNow", t)
		FilmTime.step(t)
		fov = fov or 50
		local plain = cf
		if portrait then
			cf, fov = Cameras.portrait(cf, fov)
		end
		-- Roblox draws detail around Camera.Focus: left at the player, distant set pieces and small actors
		-- drop to low detail or vanish. Focus goes on what the shot looks at.
		lock = { cf = cf, fov = fov, focus = CFrame.new(plain.Position + plain.LookVector * 8) }
		camera.CameraType = Enum.CameraType.Scriptable
		camera.CFrame, camera.FieldOfView, camera.Focus = lock.cf, lock.fov, lock.focus
		return plain, fov, index
	end
	-- Re-applied after every other render step, so no game camera script can move the shot mid-frame.
	RunService:BindToRenderStep("SlugshotSceneCamera", Enum.RenderPriority.Last.Value + 50, function()
		if lock then
			camera.CameraType = Enum.CameraType.Scriptable
			camera.CFrame, camera.FieldOfView, camera.Focus = lock.cf, lock.fov, lock.focus
		end
	end)

	-- Cues fire once as the clock passes them; the VFX burst is the runner's placeholder (real effects come
	-- from the game or the edit). Sounds here are for preview only: the edit owns the final mix.
	local fired = 0
	local function cues(t: number, manifest: any)
		while fired < #events and events[fired + 1].time <= t do
			fired += 1
			local b = events[fired]
			if b.marker then
				table.insert(manifest.cues, { type = "marker", name = b.marker, elapsed = b.time, at = now() })
			else
				local c = b.cue
				table.insert(manifest.cues, { type = c.type, name = c.name or c.effect or c.sound, elapsed = b.time, at = now() })
				local host = c.actor and actors[c.actor] and actors[c.actor].model
				if c.type == "vfx" and host then
					local p = Instance.new("Part")
					p.Anchored, p.CanCollide, p.Transparency, p.Size = true, false, 1, Vector3.one * 0.2
					p.CFrame = host:GetPivot()
					p.Parent = stage
					local emitter = Instance.new("ParticleEmitter")
					emitter.Rate = 0
					emitter.Speed = NumberRange.new(c.speed or 8)
					emitter.Lifetime = NumberRange.new(0.4, 0.8)
					emitter.Color = ColorSequence.new(Color3.fromRGB(255, 210, 63))
					emitter.TimeScale = manifest.time_scale or 1
					emitter.Parent = p
					emitter:Emit(c.count or 24)
				elseif c.type == "sound" and not manifest.silent then
					local s = library.sounds[c.sound]
					if s then
						local snd = Instance.new("Sound")
						snd.SoundId, snd.Volume, snd.Parent = s.id, c.volume or s.volume or 0.6, stage
						snd:Play()
					end
				end
			end
		end
	end

	-- The lobby's grove residents are animated by the game on real time: in a held film frame they race ahead
	-- (owner, 2026-11-25: background slugs "jumping really fast"). They leave the world for the take; a scene
	-- that wants background life places its own slug actors, which follow scene time. `world.grove = "keep"`
	-- keeps them (real-time previews only).
	local grove = workspace:FindFirstChild("HubArt") and workspace.HubArt:FindFirstChild("GroveSlugs")
	local groveParent = grove and grove.Parent
	if grove and not (spec.world and spec.world.grove == "keep") then
		grove.Parent = nil
	end
	local restoreLook = applyLook(spec.look)
	local restoreUi = Reel.Stage.clear({ keep = { "SS_FrameStamp" } })
	-- The filming client's avatar must stay in the world (the lobby's client presentation, lighting included,
	-- follows it), so it is parked under the set, invisible and casting no shadow. Under, not beside: the game's
	-- client draws the blaster holster on the avatar's back outside the character model, and its ink showed as
	-- black blobs behind the slugs (owner, 2026-11-25: "black circles" in the opener).
	local hidden = {}
	local parkedAt = character and character:GetPivot()
	if character then
		local root = character:FindFirstChild("HumanoidRootPart") :: BasePart?
		for _, d in character:GetDescendants() do
			if d:IsA("BasePart") then
				table.insert(hidden, { d, d.Transparency, d.CastShadow })
				d.Transparency, d.CastShadow = 1, false
			elseif d:IsA("Decal") then
				table.insert(hidden, { d, d.Transparency })
				d.Transparency = 1
			end
		end
		if root then
			table.insert(hidden, { root, root.Transparency, root.CastShadow, root.Anchored })
			root.Anchored = true
		end
		character:PivotTo(origin * CFrame.new(0, -40, 0))
	end
	local function destroy()
		RunService:UnbindFromRenderStep("SlugshotSceneCamera")
		workspace:SetAttribute("FilmClock", nil)
		workspace:SetAttribute("FilmTimeScale", nil)
		workspace:SetAttribute("FilmNow", nil)
		FilmTime.clear()
		if grove and groveParent and grove.Parent == nil then
			grove.Parent = groveParent
		end
		restoreUi()
		restoreLook()
		for _, h in hidden do
			h[1].Transparency = h[2]
			if h[3] ~= nil then
				h[1].CastShadow = h[3]
			end
			if h[4] ~= nil then
				h[1].Anchored = h[4]
			end
		end
		if character and parkedAt then
			character:PivotTo(parkedAt)
		end
		destroySet()
		grade:Destroy()
		stage:Destroy()
		camera.CameraType = Enum.CameraType.Custom
		camera.FieldOfView = 70
	end

	return {
		spec = spec, duration = total, frame = frame, cues = cues, destroy = destroy, shots = shots,
		dialogue = dialogue, actors = actors, warp = warp,
	}
end

local function newManifest(spec: any, take: string, mode: string): any
	return {
		scene = spec.id, take = take, truth = spec.truth, format = spec.format, mode = mode,
		dialogue = spec._dialogue and spec._dialogue.id or nil,
		marks = {}, cues = {}, camera = {}, started_ms = now(),
	}
end

local function sample(manifest: any, t: number, cf: CFrame)
	table.insert(manifest.camera, { t = t, elapsed = t, pos = { cf.X, cf.Y, cf.Z }, look = { cf.LookVector.X, cf.LookVector.Y, cf.LookVector.Z } })
end

-- Real-time preview: wall clock x speed. Frame drops skip time but never change what any moment looks like.
function Scene.run(id: string, options: any?): any
	local opts = options or {}
	local st = Scene.prepare(id, { portrait = opts.portrait, seed = opts.seed, layer = opts.layer })
	local takeName = opts.take or `{st.spec.id}_{os.date("!%Y%m%dT%H%M%S")}`
	local manifest = newManifest(st.spec, takeName, "realtime")
	manifest.silent = opts.silent
	local speed = opts.speed or 1
	local ok, err = pcall(function()
		local t0 = os.clock()
		local lastShot, nextSample = 0, 0
		table.insert(manifest.marks, { kind = "start", shot = 1, elapsed = 0, at = now() })
		while true do
			local out = (os.clock() - t0) * speed
			if out >= st.warp.duration then
				break
			end
			local t = st.warp.sceneAt(out)
			local cf, _, shot = st.frame(t)
			if shot ~= lastShot and lastShot ~= 0 then
				table.insert(manifest.marks, { kind = "cut", shot = shot, elapsed = st.shots[shot].start, at = now() })
			end
			lastShot = shot
			st.cues(t, manifest)
			if t >= nextSample then
				sample(manifest, nextSample, select(1, st.frame(nextSample)))
				nextSample += st.spec.capture and st.spec.capture.sample or 0.5
			end
			RunService.RenderStepped:Wait()
		end
		table.insert(manifest.marks, { kind = "end", shot = #st.shots, elapsed = st.duration, at = now() })
	end)
	st.destroy()
	manifest.ended_ms = now()
	manifest.completed = ok
	manifest.error = if ok then nil else tostring(err)
	return manifest
end

-- Frame index stamp: `bits` squares down the left edge of the viewport (white = 1), outside the portrait crop.
local STAMP = { x = 6, y = 40, size = 22, gap = 6, bits = 13 }

local function mountStamp(): (ScreenGui, { Frame })
	local gui = Instance.new("ScreenGui")
	gui.Name = "SS_FrameStamp"
	gui.IgnoreGuiInset = true
	gui.DisplayOrder = 1000
	local squares = {}
	for i = 1, STAMP.bits + 2 do
		local f = Instance.new("Frame")
		f.BorderSizePixel = 0
		f.Size = UDim2.fromOffset(STAMP.size, STAMP.size)
		f.Position = UDim2.fromOffset(STAMP.x, STAMP.y + (i - 1) * (STAMP.size + STAMP.gap))
		f.Parent = gui
		squares[i] = f
	end
	-- the first two squares are references: always white, then always black
	squares[1].BackgroundColor3 = Color3.new(1, 1, 1)
	squares[2].BackgroundColor3 = Color3.new(0, 0, 0)
	-- Calibration: a full-viewport magenta card at the start of a take, so a recording of the whole Studio window
	-- (tools/rec.py) can be cropped to exactly the viewport.
	local card = Instance.new("Frame")
	card.Name = "Calibration"
	card.BorderSizePixel = 0
	card.Size = UDim2.fromScale(1, 1)
	card.BackgroundColor3 = Color3.fromRGB(255, 0, 255)
	card.ZIndex = 0
	card.Visible = false
	card.Parent = gui
	gui.Parent = Players.LocalPlayer:WaitForChild("PlayerGui")
	return gui, squares
end

local function stamp(squares: { Frame }, index: number)
	for b = 0, STAMP.bits - 1 do
		local on = bit32.band(bit32.rshift(index, b), 1) == 1
		squares[b + 3].BackgroundColor3 = if on then Color3.new(1, 1, 1) else Color3.new(0, 0, 0)
	end
end

-- Frame-stepped filming. Holds scene frame i (t = i/30) for `hold` rendered frames, stamped with i. A pre-roll
-- of frame 0 and a post-roll of the last frame give the recorder room to start and stop. Particle emitters in
-- the world are slowed to match, so ambient motion keeps its real speed in the finished video.
function Scene.film(id: string, options: any?): any
	local opts = options or {}
	local hold = opts.hold or 4
	-- Resolution guard (owner rule: native-resolution masters). The rolled 9:16 frame is the viewport's height wide
	-- and 16/9 of it tall; a viewport under 1000 px high (Studio not maximised) would mean upscaled footage.
	local vp = workspace.CurrentCamera.ViewportSize
	assert(opts.allow_small or (vp.Y >= 1000 and vp.X >= vp.Y * 16 / 9),
		`viewport {math.floor(vp.X)}x{math.floor(vp.Y)} is too small for native 1080x1920: maximise the Studio window`)
	-- Studio's Automatic graphics quality drops lamps, glows and sparkles when the frame rate dips, so passes of
	-- one take lit the slugs differently and the decoded video flickered between them (owner, 2026-11-25:
	-- shadows "jittering, cut"). Takes render at the top quality level and restore the owner's setting after.
	-- (Settable when the take is started from Studio MCP; a game script can't, and then this is a no-op.)
	-- The frame-rate manager and distance-based mesh detail also change what is drawn while a take renders slowly:
	-- frames came out softer at random, worst on close-ups (owner, 2026-11-26: "randomly everything goes blurry").
	local quality, frm, meshDetail = nil, nil, nil
	pcall(function()
		quality = settings().Rendering.QualityLevel
		settings().Rendering.QualityLevel = Enum.QualityLevel.Level21
		frm = settings().Rendering.FrameRateManager
		settings().Rendering.FrameRateManager = Enum.FramerateManagerMode.Off
		meshDetail = settings().Rendering.MeshPartDetailLevel
		settings().Rendering.MeshPartDetailLevel = Enum.MeshPartDetailLevel.Level04
	end)
	local st = Scene.prepare(id, { portrait = opts.portrait ~= false, seed = opts.seed, layer = opts.layer })
	local takeName = opts.take or `{st.spec.id}_{os.date("!%Y%m%dT%H%M%S")}`
	local manifest = newManifest(st.spec, takeName, "film")
	manifest.quality = if quality then "Level21" else "unlocked"
	manifest.silent = true
	local warp = st.warp
	local frames = math.ceil(warp.duration * Scene.FPS)
	local gui, squares = mountStamp()
	local camera = workspace.CurrentCamera

	-- measure the render rate during the pre-roll to slow the world's particles to scene time
	local slowed = {}
	local portalSwirls = {}
	-- A chunk or patch pass films frames first..last; earlier frames are posed instantly (not filmed) so any
	-- eased state reaches frame `first` exactly as in a full pass.
	local first = math.clamp(opts.first or 0, 0, frames - 1)
	local last = math.clamp(opts.last or frames - 1, first, frames - 1)
	manifest.first, manifest.last = first, last
	local ok, err = pcall(function()
		-- The portal surface pulses on FilmClock. Its extra swirl layers are emitted on real time,
		-- so their bloom disagrees between a full take and a patch at the same scene frame.
		for _, swirl in CollectionService:GetTagged("HubPortalSwirl") do
			if swirl:IsA("ParticleEmitter") and swirl.Parent then
				portalSwirls[swirl] = swirl.Enabled
				swirl.Enabled = false
				swirl:Clear()
				local startup = swirl.Parent:FindFirstChild(swirl.Name .. "Start")
				if startup and startup:IsA("ParticleEmitter") then
					startup:Clear()
				end
			end
		end
		-- Warm-up: a take started soon after play began filmed the cavern while its textures were still loading,
		-- so the background brightened over the first seconds and frames mixed from a later pass flashed between
		-- dark and light (owner, 2026-11-26). Load what the take shows, then look through every shot once so the
		-- renderer has it all resident before frame `first` is filmed. (frame(t) is pure; no cues fire here.)
		local warm = os.clock()
		-- The lobby's solid art (cavern walls, roof, rocks) is built by the game's HubArt over about two minutes after
		-- play starts; it marks the end with workspace.HubSolidParts. Takes started earlier filmed walls appearing
		-- mid-shot, seen as dark-to-light flashes (owner, 2026-11-26). Wait for it (at most 4 minutes).
		while workspace:GetAttribute("HubSolidParts") == nil and workspace:FindFirstChild("HubArt")
			and os.clock() - warm < 240 do
			task.wait(0.5)
		end
		manifest.hub_built = workspace:GetAttribute("HubSolidParts") ~= nil
		pcall(function()
			game:GetService("ContentProvider"):PreloadAsync({ workspace })
		end)
		for _, s in st.shots do
			for _, k in { 0, 0.5, 0.95 } do
				st.frame(s.start + s.duration * k)
				for _ = 1, 10 do
					RunService.RenderStepped:Wait()
				end
			end
		end
		while game:GetService("ContentProvider").RequestQueueSize > 0 and os.clock() - warm < 30 do
			RunService.RenderStepped:Wait()
		end
		manifest.warmup_s = math.floor((os.clock() - warm) * 10) / 10
		for i = 0, first do
			st.frame(warp.sceneAt(i / Scene.FPS))
			st.cues(warp.sceneAt(i / Scene.FPS), manifest)
		end
		local card = gui:FindFirstChild("Calibration")
		if card then
			card.Visible = true
			task.wait(0.6)
			card.Visible = false
		end
		stamp(squares, first)
		local c0, n = os.clock(), 0
		while os.clock() - c0 < (opts.preroll or 2) do
			RunService.RenderStepped:Wait()
			n += 1
		end
		local fps = n / (os.clock() - c0)
		local scale = math.clamp(fps / (Scene.FPS * hold), 0.05, 1)
		manifest.render_fps, manifest.time_scale = fps, scale
		-- Real-time motion scripts that honour a TimeScale attribute (the game's transformed slug forms) slow to match.
		workspace:SetAttribute("FilmTimeScale", scale)
		for _, e in workspace:GetDescendants() do
			if e:IsA("ParticleEmitter") then
				table.insert(slowed, { e, e.TimeScale })
				e.TimeScale = e.TimeScale * scale
			end
		end
		-- In slow motion the world's real-time motion slows by the same rate.
		local rate = 1
		local function slowTo(r: number)
			if r ~= rate then
				rate = r
				workspace:SetAttribute("FilmTimeScale", scale * r)
				for _, s in slowed do
					if s[1].Parent then
						s[1].TimeScale = s[2] * scale * r
					end
				end
			end
		end
		table.insert(manifest.marks, { kind = "start", shot = 1, elapsed = 0, at = now() })
		local lastShot = 1
		for i = first, last do
			local t = warp.sceneAt(i / Scene.FPS)
			slowTo(warp.rateAt(t))
			local cf, _, shot = st.frame(t)
			st.cues(t, manifest)
			stamp(squares, i)
			if shot ~= lastShot then
				table.insert(manifest.marks, { kind = "cut", shot = shot, elapsed = st.shots[shot].start, at = now() })
				lastShot = shot
				-- A new view's textures stream in over a few frames: clothing showed blocky for the first frames after
				-- a cut (owner, 2026-11-26: "randomly everything goes blurry ... maybe when there's a cut"). Render it
				-- unstamped (the decoder skips unstamped frames) until they have loaded.
				squares[1].BackgroundColor3 = Color3.new(0, 0, 0)
				for _ = 1, opts.settle or 24 do
					RunService.RenderStepped:Wait()
				end
				squares[1].BackgroundColor3 = Color3.new(1, 1, 1)
			end
			if i % 15 == 0 then
				sample(manifest, t, cf)
			end
			for _ = 1, hold do
				RunService.RenderStepped:Wait()
			end
		end
		table.insert(manifest.marks, { kind = "end", shot = #st.shots, elapsed = st.duration, at = now() })
		task.wait(opts.postroll or 1)
	end)
	for _, s in slowed do
		if s[1].Parent then
			s[1].TimeScale = s[2]
		end
	end
	for swirl, enabled in portalSwirls do
		if swirl.Parent then
			swirl.Enabled = enabled
		end
	end
	manifest.viewport = { camera.ViewportSize.X, camera.ViewportSize.Y }
	manifest.stamp = STAMP
	manifest.frames, manifest.fps, manifest.hold, manifest.portrait = frames, Scene.FPS, hold, opts.portrait ~= false
	manifest.layer = opts.layer
	-- Video time: the slow segments (take.py warp adds their extra seconds of silence to the dialogue) and the
	-- split shots' frame ranges (take.py split composites the "b" pass into them).
	manifest.duration_out = warp.duration
	manifest.warp = {}
	for _, w in warp.segments do
		table.insert(manifest.warp, { from = w.from, ["until"] = w["until"], rate = w.rate, ramp = w.ramp, extra = w.extra,
			out_from = warp.outAt(w.from) })
	end
	manifest.splits = {}
	for i, s in st.spec.shots do
		if s.preset == "split" then
			local sh = st.shots[i]
			table.insert(manifest.splits, { shot = i, first = math.floor(warp.outAt(sh.start) * Scene.FPS + 0.5),
				last = math.floor(warp.outAt(sh.start + sh.duration) * Scene.FPS + 0.5) - 1,
				open = s.open or 0.3, close = s.close or 0.3, slant = s.slant or 0.05, divider = s.divider })
		end
	end
	gui:Destroy()
	st.destroy()
	if quality then
		pcall(function()
			settings().Rendering.QualityLevel = quality
			settings().Rendering.FrameRateManager = frm
			settings().Rendering.MeshPartDetailLevel = meshDetail
		end)
	end
	manifest.ended_ms = now()
	manifest.completed = ok
	manifest.error = if ok then nil else tostring(err)
	return manifest
end

-- Pose at t (frames 0..t are run in order so eased state matches a filmed take) and leave the scene standing
-- until Scene.clear(); returns the camera CFrame for a screenshot.
local standing = nil
function Scene.still(id: string, t: number, options: any?): string
	Scene.clear()
	local opts = options or {}
	standing = Scene.prepare(id, { portrait = opts.portrait, seed = opts.seed, layer = opts.layer })
	local cf, fov
	for i = 0, math.floor(t * Scene.FPS) do
		cf, fov = standing.frame(i / Scene.FPS)
	end
	cf, fov = standing.frame(t)
	local look = cf.Position + cf.LookVector * 10
	return HttpService:JSONEncode({ t = t, fov = fov, pos = { cf.X, cf.Y, cf.Z }, look = { look.X, look.Y, look.Z } })
end

function Scene.clear()
	if standing then
		standing.destroy()
		standing = nil
	end
end

-- Non-blocking start for tools that can't wait (Studio MCP): the result lands in _G.SlugshotTake.
function Scene.start(mode: string, id: string, options: any?)
	_G.SlugshotTake = { running = true }
	task.spawn(function()
		local m = if mode == "film" then Scene.film(id, options) else Scene.run(id, options)
		_G.SlugshotTake = { running = false, json = HttpService:JSONEncode(m) }
	end)
end

function Scene.runJson(id: string, options: any?): string
	return HttpService:JSONEncode(Scene.run(id, options))
end

function Scene.filmJson(id: string, options: any?): string
	return HttpService:JSONEncode(Scene.film(id, options))
end

return Scene
