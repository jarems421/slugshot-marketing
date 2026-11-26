--!nonstrict
-- Slug shots for human actors (owner, 2026-11-26: a shot should be "the slug actually shooting and transforming ... a
-- special moment", not a generic gunshot). A `shoot` beat with `slug` launches that species from the actor's blaster
-- muzzle at `target` and plays the game's own transformation presentation (PlayerScripts.Combat.SlugTransformation:
-- twirl in a glow, swap to <Slug>Transformed, grow in, then a hit that turns it back). Floppy never transforms
-- (docs/game-truth.md): he flies as himself and tumbles.
--
-- The game's module keeps a little state per shot (the swap, its ending clock). To stay a function of scene time, a
-- shot is rebuilt and replayed in 1/30 s steps from its launch whenever time runs backwards (a still, a patch pass).
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Shots = {}

local STEP = 1 / 30
local SPEED = 42 -- studs per second of flight (the game's shots are faster; staged shots are slowed to read)
local END_POP = 0.3

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

local function styleGlow(species: string): Color3
	local combat = Players.LocalPlayer.PlayerScripts:FindFirstChild("Combat")
	local styles = combat and combat:FindFirstChild("TransformationStyles")
	local ok, s = pcall(function()
		return require(styles).of(species).glow
	end)
	return if ok and typeof(s) == "Color3" then s else Color3.fromRGB(255, 226, 150)
end

-- A shot's plan: launch time, path and flight time. `muzzle(t)` gives the blaster muzzle's world position.
function Shots.plan(b: any, muzzleAt: (number) -> Vector3, where: any): any
	local from = muzzleAt(b.time)
	local to = where(b.target, b.time)
	local length = (to - from).Magnitude
	return {
		t = b.time, species = b.slug, from = from, to = to, way = (to - from).Unit,
		flight = math.max(length / (b.speed or SPEED), 0.25), arc = b.arc or 0.06 * length,
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
	local live = { base = base, clock = -1, state = nil, ended = false, popped = nil, baseScale = base:GetScale() }
	local T = module()
	if T and s.species ~= "Floppy" then
		local params = RaycastParams.new()
		params.FilterType = Enum.RaycastFilterType.Exclude
		params.FilterDescendantsInstances = { parent }
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
	if live.state and not live.ended then
		if not live.state.ending then
			local contact = T.contact(live.state, s.to, s.way)
			if not T.endWith(live.state, "hit", contact, -s.way * 0.8 + Vector3.yAxis * 0.5) then
				live.ended = true
			end
		end
		if live.state.ending and not live.ended then
			local done = T.stepEnd(live.state, STEP)
			if done then
				live.ended = true
				T.finish(live.state, s.to, s.way)
			end
		end
	elseif not live.state then
		live.ended = true
	end
	if live.ended then
		live.popped = live.popped or tau
		local k = math.clamp(1 - (tau - live.popped) / END_POP, 0.001, 1)
		live.base:ScaleTo(live.baseScale * k)
		live.base:PivotTo(CFrame.new(s.to - s.way * 0.6 + Vector3.new(0, 0.4 * (1 - k), 0)))
		if k <= 0.001 then
			live.base.Parent = nil
		end
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
	end
end

-- Where the slug is at t on its way (a camera follows it); before launch, at the muzzle facing the target.
function Shots.frameAt(s: any, t: number): CFrame
	return pathAt(s, math.clamp((t - s.t) / s.flight, 0, 1))
end

function Shots.clear(list: { any })
	for _, s in list do
		destroy(s)
	end
end

return Shots
