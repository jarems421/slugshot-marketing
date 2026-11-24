--!nonstrict
-- SlugshotScene: runs a declarative scene spec (roblox-native/scenes/**/*.json, validated by
-- tools/scene.py and built into the marketing place) as a Reel take. Client side.
--
--   local Scene = require(ReplicatedStorage.SlugshotMarketing.Scene)
--   local manifest = Scene.run("smoke_orbit")   -- yields until the take ends; returns the manifest
--
-- Every take builds its set and actors in setup and destroys them in cleanup, so takes start
-- from the same state (reset). Reel restores the camera and UI.
local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Root = ReplicatedStorage:WaitForChild("SlugshotMarketing")
local Reel = require(Root:WaitForChild("Reel"))
local Actors = require(script.Actors)
local Cameras = require(script.Cameras)
local Canon = require(script.Canon)

local Scene = {}

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
	local module = Root.Scenes:FindFirstChild(id)
	assert(module, `no scene {id}; built scenes: {table.concat(Scene.list(), ", ")}`)
	return decode(module)
end

local library = decode(Root:WaitForChild("Library"))

local function v3(t: { number }): Vector3
	return Vector3.new(t[1], t[2] or 0, t[3] or 0)
end

local function now(): number
	return DateTime.now().UnixTimestampMillis
end

-- A set gives the origin that marks are relative to.
local function buildSet(set: any, parent: Instance): (CFrame, () -> ())
	if set.kind == "cyc" then
		-- Default far from the game world: the copied place has large art (e.g. the hub storm) up high.
		local cyc = Reel.Cyc.build(parent, CFrame.new(v3(set.at or { 4000, 1500, 4000 })), { radius = set.radius })
		return cyc.top, cyc.destroy
	elseif set.kind == "place" then
		-- An existing location in the place: origin is a world position (and yaw in degrees).
		return CFrame.new(v3(set.origin)) * CFrame.Angles(0, math.rad(set.yaw or 0), 0), function() end
	end
	error(`unknown set kind {set.kind}`)
end

function Scene.run(id: string, options: any?): any
	local opts = options or {}
	local spec = Scene.load(id)
	local ok, why = Canon.check(spec)
	assert(ok, `scene {id} rejected by canon check: {why}`)

	local takeName = opts.take or `{spec.id}_{os.date("!%Y%m%dT%H%M%S")}`
	local manifest = {
		scene = spec.id, take = takeName, truth = spec.truth, format = spec.format,
		marks = {}, cues = {}, camera = {}, started_ms = now(),
	}
	local actors: { [string]: Model } = {}
	local origin = CFrame.identity
	local seed = opts.seed or 1

	local function mark(name: string): CFrame
		local m = spec.marks[name]
		assert(m, `unknown mark {name}`)
		return origin * CFrame.new(m[1], m[2] or 0, m[3] or 0) * CFrame.Angles(0, math.rad(m[4] or 0), 0)
	end
	local function frameOf(name: string): CFrame
		if actors[name] then
			return actors[name]:GetPivot()
		end
		return mark(name)
	end
	local function position(name: string): Vector3
		return frameOf(name).Position
	end
	local function cue(c: any, at: Model?)
		local entry = { type = c.type, name = c.name or c.effect or c.sound, elapsed = 0, at = now() }
		if c.type == "vfx" then
			local host = at or (c.actor and actors[c.actor])
			if host and host.PrimaryPart then
				local emitter = Instance.new("ParticleEmitter")
				emitter.Rate = 0
				emitter.Speed = NumberRange.new(c.speed or 8)
				emitter.Lifetime = NumberRange.new(0.4, 0.8)
				emitter.Color = ColorSequence.new(Color3.fromRGB(255, 210, 63))
				emitter.Parent = host.PrimaryPart
				emitter:Emit(c.count or 24)
				task.delay(1.5, function()
					emitter:Destroy()
				end)
			end
		elseif c.type == "sound" then
			local s = library.sounds[c.sound]
			assert(s, `unknown sound {c.sound}`)
			local snd = Instance.new("Sound")
			snd.SoundId = s.id
			snd.Volume = c.volume or s.volume or 0.6
			snd.Parent = workspace
			snd:Play()
			task.delay(10, function()
				snd:Destroy()
			end)
		end
		table.insert(manifest.cues, entry)
	end

	local ctx = {
		Shot = Reel.Shot, Curve = Reel.Curve, seed = seed, library = library,
		mark = mark, position = position, frame = frameOf, cue = cue,
		target = function(name: string)
			return function(): CFrame?
				local a = actors[name]
				return if a and a.Parent then a:GetPivot() + Vector3.new(0, 1, 0) else nil
			end
		end,
		center = function(names: { string }): Vector3
			local sum = Vector3.zero
			for _, n in names do
				sum += position(n)
			end
			return sum / #names
		end,
	}

	local beats = {}
	for _, b in spec.timeline or {} do
		table.insert(beats, { time = b.time, run = function(take)
			if b.cue then
				cue(b.cue, b.actor and actors[b.actor])
				manifest.cues[#manifest.cues].elapsed = take.elapsed()
			elseif b.marker then
				table.insert(manifest.cues, { type = "marker", name = b.marker, elapsed = take.elapsed(), at = now() })
				print(`[SlugshotScene] marker {b.marker} take={takeName} elapsed={string.format("%.3f", take.elapsed())} at={now()}`)
			else
				Actors.act(actors[b.actor], b, ctx)
			end
		end })
	end
	-- Camera samples for repeatability checks (two takes of the same scene should match).
	local total = 0
	for _, s in spec.shots do
		total += s.duration
	end
	local step = spec.capture and spec.capture.sample or 0.5
	for t = 0, total - 1e-3, step do
		table.insert(beats, { time = t, run = function(take)
			local cf = workspace.CurrentCamera.CFrame
			table.insert(manifest.camera, { t = t, elapsed = take.elapsed(), pos = { cf.X, cf.Y, cf.Z }, look = { cf.LookVector.X, cf.LookVector.Y, cf.LookVector.Z } })
		end })
	end

	Reel.register({
		name = `scene/{spec.id}`,
		note = spec.note,
		haze = spec.set.kind ~= "cyc",
		setup = function()
			local stage = Instance.new("Folder")
			stage.Name = `SS_scene_{spec.id}`
			stage.Parent = workspace
			local destroySet
			origin, destroySet = buildSet(spec.set, stage)
			for name, def in spec.actors or {} do
				actors[name] = Actors.spawn(name, def, mark(def.mark), stage)
			end
			for name, def in spec.actors or {} do
				if def.face then
					local here = actors[name]:GetPivot().Position
					local there = position(def.face)
					actors[name]:PivotTo(CFrame.lookAt(here, Vector3.new(there.X, here.Y, there.Z)))
				end
			end
			return function() -- reset: everything the take made goes away
				table.clear(actors)
				destroySet()
				stage:Destroy()
			end
		end,
		shots = function()
			local shots = {}
			for _, s in spec.shots do
				table.insert(shots, Cameras.build(s, ctx))
			end
			return shots
		end,
		at = beats,
	})

	local done = false
	Reel.play(`scene/{spec.id}`, {
		seed = seed,
		onMark = function(m)
			table.insert(manifest.marks, { kind = m.kind, shot = m.shot, elapsed = m.elapsed, at = m.at, detail = m.detail })
			Reel.Take.printMark(m)
			if m.kind == "end" or m.kind == "stop" or m.kind == "fail" then
				done = true
			end
		end,
	})
	local deadline = os.clock() + total + 15
	while not done and os.clock() < deadline do
		task.wait(0.1)
	end
	manifest.ended_ms = now()
	manifest.completed = done and manifest.marks[#manifest.marks].kind == "end"
	return manifest
end

-- JSON string version for tools that read results as text (Studio MCP execute_luau).
function Scene.runJson(id: string, options: any?): string
	return HttpService:JSONEncode(Scene.run(id, options))
end

return Scene
