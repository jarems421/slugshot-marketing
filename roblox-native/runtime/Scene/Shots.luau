--!nonstrict
-- Slug shots for human actors (owner, 2026-11-26: a shot should be "the slug actually shooting and transforming ... a
-- special moment", not a generic gunshot). A `shoot` beat with `slug` launches that species from the actor's blaster
-- muzzle at `target` and plays the game's own transformation presentation (PlayerScripts.Combat.SlugTransformation:
-- twirl in a glow, swap to <Slug>Transformed, grow in, then a hit that turns it back). Floppy never transforms
-- (docs/game-truth.md): he flies as himself and tumbles.
--
-- The game's module keeps a little state per shot (the swap, its ending clock). To stay a function of scene time, a
-- shot is rebuilt and replayed in 1/480 s steps from its launch whenever time runs backwards (a still, a patch pass).
-- Steps that fine keep the twirl and transformation smooth in slow motion (a 1/30 s step showed each pose for
-- several frames at a quarter speed).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shots = {}
local FilmTime = require(ReplicatedStorage:WaitForChild("SlugshotMarketing"):WaitForChild("FilmTime"))

local STEP = 1 / 480
local SPEED = 42 -- studs per second of flight (the game's shots are faster; staged shots are slowed to read)

local transformation = nil
local function module()
	if transformation == nil then
		local combat = Players.LocalPlayer:WaitForChild("PlayerScripts"):WaitForChild("Combat", 20)
		local m = combat and combat:FindFirstChild("SlugTransformation")
		transformation = if m then require(m) else false
		if transformation then
			transformation.timeScale = 1 -- staged steps are already in scene time
		end
	end
	return transformation or nil
end

local function client(name: string): any?
	local combat = Players.LocalPlayer.PlayerScripts:FindFirstChild("Combat")
	local m = combat and combat:FindFirstChild(name)
	local ok, v = pcall(function()
		return require(m)
	end)
	return if ok then v else nil
end

local recoveryModule = nil
local function recovery(): any
	recoveryModule = recoveryModule or client("FloppyRecovery")
	return recoveryModule
end

local function styleGlow(species: string): Color3
	local styles = client("TransformationStyles")
	local ok, s = pcall(function()
		return styles.of(species).glow
	end)
	return if ok and typeof(s) == "Color3" then s else Color3.fromRGB(255, 226, 150)
end

-- The game's landing (SlugVisuals.land): ImpactFx's contact sweep and chips in the slug's style, the transformed form's
-- "hit" ending, then FloppyRecovery: the base slug falls, wriggles, hops and burrows into the floor (owner,
-- 2026-11-26: "the same impact mechanics ... the same digging mechanics", not a re-creation).
local function contactCue(s: any, at: Vector3, normal: Vector3)
	local fx, styles = client("ImpactFx"), client("TransformationStyles")
	if not (fx and styles) then
		return
	end
	local style = styles.of(s.species)
	local impact = style.impact or styles.DefaultImpact
	fx.contact(at, normal, s.way * s.speed, impact.burst, style.glow, impact.debris, nil)
end

local function slugSize(species: string): number
	local ok, size = pcall(function()
		return require(ReplicatedStorage:WaitForChild("Combat")).Slugs[species].Size
	end)
	return if ok and type(size) == "number" then size else 1
end

-- A shot's plan: launch time, path and flight time. `muzzle(t)` gives the blaster muzzle's world position.
function Shots.plan(b: any, muzzleAt: (number) -> Vector3, where: any): any
	local from = muzzleAt(b.time)
	local to = where(b.target, b.time)
	local length = (to - from).Magnitude
	return {
		t = b.time, species = b.slug, from = from, to = to, way = (to - from).Unit,
		flight = math.max(length / (b.speed or SPEED), 0.25), arc = b.arc or 0.06 * length, speed = b.speed or SPEED,
		glow = styleGlow(b.slug), live = nil,
	}
end

local function pathAt(s: any, u: number): CFrame
	local p = s.from:Lerp(s.to, u) + Vector3.new(0, s.arc * 4 * u * (1 - u), 0)
	local q = s.from:Lerp(s.to, math.min(u + 0.02, 1)) + Vector3.new(0, s.arc * 4 * (u + 0.02) * (1 - u - 0.02), 0)
	return CFrame.lookAt(p, if (q - p).Magnitude > 1e-3 then q else p + s.way)
end

local function build(s: any, parent: Instance)
	local assets = ReplicatedStorage:WaitForChild("CombatAssets")
	local template = assets:FindFirstChild(s.species .. "Flight")
	assert(template, `shoot: no CombatAssets.{s.species}Flight`)
	local base = template:Clone()
	for _, d in base:GetDescendants() do
		if d:IsA("BasePart") then
			d.Anchored, d.CanCollide, d.CanTouch, d.CanQuery = true, false, false, false
		elseif d:IsA("LuaSourceContainer") then
			d:Destroy()
		end
	end
	base:PivotTo(CFrame.new(s.from))
	base.Parent = parent
	local params = RaycastParams.new()
	params.FilterType = Enum.RaycastFilterType.Exclude
	params.FilterDescendantsInstances = { parent, workspace.CurrentCamera }
	local live = { base = base, clock = -1, state = nil, params = params, landed = false, ending = false, recovery = nil,
		gone = false }
	FilmTime.reseed(math.floor(s.t * 1000) % 100003 + 1) -- the same chips and dirt in every pass
	local T = module()
	if T and s.species ~= "Floppy" then
		local launch = { id = 0, slugId = s.species, origin = s.from, velocity = s.way * (s.speed or SPEED), route = nil }
		live.state = T.new(s.species, base, launch, params, parent)
	end
	-- the slug's own colour lights the muzzle as it leaves (no generic muzzle flash)
	local glowPart = Instance.new("Part")
	glowPart.Anchored, glowPart.CanCollide, glowPart.CanQuery, glowPart.CanTouch = true, false, false, false
	glowPart.Transparency, glowPart.Size, glowPart.CFrame = 1, Vector3.one * 0.1, CFrame.new(s.from)
	local light = Instance.new("PointLight")
	light.Color, light.Range, light.Shadows, light.Brightness = s.glow, 9, false, 0
	light.Parent = glowPart
	glowPart.Parent = parent
	live.light = light
	s.live = live
end

local function destroy(s: any)
	local live = s.live
	s.lastLive = nil
	if not live then
		return
	end
	if live.state and not live.state.ended then
		module().destroy(live.state)
	end
	live.base:Destroy()
	live.light.Parent:Destroy()
	s.live = nil
end

-- One step of the shot at tau seconds after launch (called in order, every STEP).
local function advance(s: any, tau: number)
	local live = s.live
	workspace:SetAttribute("FilmNow", s.t + tau) -- the game's effects started in this step are born now (FilmTime)
	local T = module()
	live.light.Brightness = 2.5 * math.max(0, 1 - tau / 0.25)
	local filmScale = workspace:GetAttribute("FilmTimeScale") or 1
	if tau <= s.flight then
		local frame = pathAt(s, tau / s.flight)
		if live.state then
			if live.state.form.Parent then
				live.state.form:SetAttribute("TimeScale", filmScale)
			end
			T.step(live.state, tau, frame)
		else
			-- Floppy (or a slug without a form): flies as himself, tumbling end over end
			live.base:PivotTo(frame * CFrame.Angles(-tau * 14, 0, 0))
		end
		return
	end
	if live.gone then
		return
	end
	local now = s.t + tau
	if not live.landed then
		live.landed = true
		local hit = workspace:Raycast(s.to - s.way * 1.5 + Vector3.yAxis * 0.5, s.way * 3 - Vector3.yAxis * 1.5, live.params)
		live.normal = if hit then hit.Normal else Vector3.yAxis
		local at = if hit then hit.Position else s.to
		live.ground = at.Y
		contactCue(s, at, live.normal)
		if live.state and live.state.swapped then
			local bounce = T.bounce(live.state, at, live.normal, s.way * s.speed, live.params)
			if T.endWith(live.state, "hit", T.contact(live.state, at, s.way * s.speed), bounce) then
				live.ending = true
				return
			end
		end
		if live.state then
			T.finish(live.state, at, live.normal)
		end
		live.recovery = recovery().new(live.base, slugSize(s.species), at, live.normal, s.way * s.speed, live.params, nil,
			now)
	end
	if live.ending then
		local done, position, recoil = T.stepEnd(live.state, STEP)
		if done then
			live.ending = false
			live.recovery = recovery().new(live.base, slugSize(s.species), position, Vector3.zero, recoil or Vector3.zero,
				live.params, nil, now, recoil ~= nil)
		end
		return
	end
	if live.recovery and recovery().step(live.recovery, now) then
		live.gone = true
		live.base.Parent = nil
	end
end

-- Pose every shot of one actor at t. Shots are rebuilt and replayed when time runs backwards.
function Shots.pose(list: { any }, t: number, parent: Instance)
	for _, s in list do
		local tau = t - s.t
		if tau < 0 or tau > s.flight + 3 then
			destroy(s)
			continue
		end
		if s.live and tau < s.live.clock - 1e-6 then
			destroy(s)
		end
		if not s.live then
			build(s, parent)
		end
		local live = s.live
		local next = if live.clock < 0 then 0 else live.clock + STEP
		while next <= tau + 1e-6 do
			advance(s, next)
			live.clock = next
			next += STEP
		end
		-- The forms' particles run on real time: in a film take (and its slow motion) they follow scene time.
		local scale = workspace:GetAttribute("FilmTimeScale")
		if scale then
			for _, root in { live.base, live.state and live.state.form } do
				for _, e in if root then root:GetDescendants() else {} do
					if e:IsA("ParticleEmitter") then
						if e:GetAttribute("SS_TimeScale") == nil then
							e:SetAttribute("SS_TimeScale", e.TimeScale)
						end
						e.TimeScale = e:GetAttribute("SS_TimeScale") * scale
					end
				end
			end
		end
	end
end

-- When the slug's twirl ends and its form takes over (the game's Transformation.Spin), seconds after launch; nil for
-- Floppy, who never transforms.
function Shots.spin(s: any): number?
	if s.species == "Floppy" then
		return nil
	end
	local ok, spin = pcall(function()
		return require(ReplicatedStorage:WaitForChild("Combat")).Slugs[s.species].Transformation.Spin
	end)
	return if ok and type(spin) == "number" then spin else nil
end

-- Where the slug is at t on its way (a camera follows it); before launch, at the muzzle facing the target.
-- After the hit the game throws the form back off the surface and the base slug falls, wriggles and burrows wherever
-- it lands, so a camera following the shot follows the slug itself from then on (owner, 2026-11-26: the V-test shot
-- stared at empty floor), easing over from the path's end.
local function liveAt(s: any): Vector3?
	local live = s.live
	if not live or live.gone then
		return nil
	end
	local form = live.state and live.state.form
	for _, m in { form, live.base } do
		if m and m.Parent then
			-- the body itself: a model's pivot can sit well away from where its mesh draws
			local body, size = nil, 0
			for _, d in m:GetDescendants() do
				if d:IsA("BasePart") and d.Transparency < 1 and d.Size.Magnitude > size then
					body, size = d, d.Size.Magnitude
				end
			end
			local p = if body then body.Position else m:GetPivot().Position
			if p.Y > -1000 then -- parked models sit far below the world
				-- a burrowing slug goes into the floor; the camera stays above it, on the dirt
				return if live.ground then Vector3.new(p.X, math.max(p.Y, live.ground + 0.3), p.Z) else p
			end
		end
	end
	return nil
end

function Shots.frameAt(s: any, t: number): CFrame
	local tau = t - s.t
	local frame = pathAt(s, math.clamp(tau / s.flight, 0, 1))
	if tau <= s.flight or not s.live or math.abs(s.live.clock - tau) > 0.05 then
		return frame
	end
	local p = liveAt(s)
	if p then
		s.lastLive = p
	end
	p = p or s.lastLive
	if not p then
		return frame
	end
	local u = math.clamp((tau - s.flight) / 0.3, 0, 1)
	u = u * u * (3 - 2 * u)
	return frame.Rotation + frame.Position:Lerp(p, u)
end

function Shots.clear(list: { any })
	for _, s in list do
		destroy(s)
	end
end

return Shots
