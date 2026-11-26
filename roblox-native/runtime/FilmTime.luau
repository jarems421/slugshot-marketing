--!nonstrict
-- Film time for the game's own effect modules (marketing place only). make_marketing_place.py patches the game's
-- ImpactFx, FloppyRecovery and SlugTransformation so their clock, Debris lifetimes, tweens and randomness come from here
-- (owner, 2026-11-26: reuse the game's impact and burrow instead of re-creating them). Outside a take everything passes
-- straight through to os.clock, Debris, TweenService and Random; during a take (workspace.FilmNow set by Scene) it all
-- follows scene time, so effects play at film speed, slow down in slow motion, and replay identically in a patch pass.
local Debris = game:GetService("Debris")
local RunService = game:GetService("RunService")
local TweenService = game:GetService("TweenService")

local FilmTime = {}

local function film(): number?
	return workspace:GetAttribute("FilmNow")
end

function FilmTime.now(): number
	return film() or os.clock()
end

-- Things created during a take, with the scene time they were born at: Scene clears the ones born after a time it
-- rewinds to, and lifetimes run out on scene time.
local items = {} -- { obj, born, dies }
local tweens = {} -- { obj, born, delay, time, style, direction, from, to }

function FilmTime.addItem(obj: Instance, life: number)
	local t = film()
	if not t then
		Debris:AddItem(obj, life)
		return
	end
	table.insert(items, { obj = obj, born = t, dies = t + life })
end

local function lerp(a: any, b: any, k: number): any
	local kind = typeof(a)
	if kind == "number" then
		return a + (b - a) * k
	elseif kind == "boolean" then
		return if k >= 1 then b else a
	end
	return a:Lerp(b, k)
end

local Tween = {}
Tween.__index = Tween
function Tween:Play()
	local t = film()
	local from = {}
	for key in self.props do
		from[key] = self.obj[key]
	end
	table.insert(tweens, { obj = self.obj, born = t, info = self.info, from = from, to = self.props })
end
function Tween:Cancel() end
function Tween:Pause() end

function FilmTime.create(obj: Instance, info: TweenInfo, props: any): any
	if not film() then
		return TweenService:Create(obj, info, props)
	end
	return setmetatable({ obj = obj, info = info, props = props }, Tween)
end

-- One seeded generator during a take (Scene reseeds it per shot, so every pass draws the same numbers).
local rng = Random.new(1)
function FilmTime.reseed(seed: number)
	rng = Random.new(seed)
end
local real = Random.new()
FilmTime.random = setmetatable({}, {
	__index = function(_, method)
		return function(_, ...)
			local r = if film() then rng else real
			return (r :: any)[method](r, ...)
		end
	end,
})

-- Everything born after t goes (a still or patch rewinding).
function FilmTime.rewind(t: number)
	for i = #items, 1, -1 do
		if items[i].born > t + 1e-6 then
			if items[i].obj then
				items[i].obj:Destroy()
			end
			table.remove(items, i)
		end
	end
	for i = #tweens, 1, -1 do
		if tweens[i].born > t + 1e-6 then
			table.remove(tweens, i)
		end
	end
end

function FilmTime.clear()
	for _, it in items do
		if it.obj then
			it.obj:Destroy()
		end
	end
	table.clear(items)
	table.clear(tweens)
end

-- Applies lifetimes and tweens at scene time t (Scene calls this each frame; also run every render as a fallback).
function FilmTime.step(t: number?)
	t = t or film()
	if not t then
		return
	end
	for i = #items, 1, -1 do
		local it = items[i]
		if t >= it.dies then
			if it.obj then
				it.obj:Destroy()
			end
			table.remove(items, i)
		end
	end
	for i = #tweens, 1, -1 do
		local tw = tweens[i]
		if not tw.obj.Parent then
			table.remove(tweens, i)
			continue
		end
		local info = tw.info
		local u = math.clamp((t - tw.born - info.DelayTime) / math.max(info.Time, 1e-6), 0, 1)
		local k = TweenService:GetValue(u, info.EasingStyle, info.EasingDirection)
		for key, goal in tw.to do
			tw.obj[key] = lerp(tw.from[key], goal, k)
		end
	end
end

RunService.RenderStepped:Connect(function()
	FilmTime.step()
end)

return FilmTime
