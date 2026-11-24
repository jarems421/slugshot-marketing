--!nonstrict
-- Actors for staged scenes: spawning (stand-ins or copies of models already in the place) and the
-- actions a timeline can ask for. Client side; everything spawned is local to the filming client.
local RunService = game:GetService("RunService")

local Actors = {}

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

-- Stand-ins are plain parts: no network, no assets. Only for technical tests.
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

-- kind: "standin_humanoid" | "standin_slug" | "clone" (asset = dotted path to a Model in the place)
function Actors.spawn(name: string, def: any, at: CFrame, parent: Instance): Model
	local model: Model
	if def.kind == "standin_humanoid" then
		model = standinHumanoid()
	elseif def.kind == "standin_slug" then
		model = standinSlug()
	elseif def.kind == "clone" then
		local source = findPath(def.asset)
		assert(source and source:IsA("Model"), `actor {name}: no Model at {def.asset}`)
		model = (source :: Model):Clone()
	else
		error(`actor {name}: unknown kind {def.kind}`)
	end
	model.Name = `SS_actor_{name}`
	for _, d in model:GetDescendants() do
		if d:IsA("BasePart") then
			d.Anchored = true -- staged actors are puppets, not physics
		elseif d:IsA("Script") or d:IsA("LocalScript") then
			d.Enabled = false -- copied game behaviour must not run inside a staged scene
		end
	end
	model:PivotTo(at)
	model.Parent = parent
	return model
end

-- Smoothly move a model's pivot from its current CFrame to `goal` over `duration`.
local function glide(model: Model, goal: CFrame, duration: number, arc: number?)
	local start = model:GetPivot()
	local t = 0
	while t < duration do
		t += RunService.RenderStepped:Wait()
		local k = math.min(t / duration, 1)
		local eased = k * k * (3 - 2 * k)
		local lift = if arc then math.sin(math.pi * k) * arc else 0
		model:PivotTo(start:Lerp(goal, eased) + Vector3.new(0, lift, 0))
	end
	model:PivotTo(goal)
end

local function animator(model: Model): Animator?
	local host = model:FindFirstChildWhichIsA("Humanoid", true) or model:FindFirstChildWhichIsA("AnimationController", true)
	if not host then
		return nil
	end
	local a = host:FindFirstChildOfClass("Animator")
	if not a then
		a = Instance.new("Animator")
		a.Parent = host
	end
	return a
end

-- One timeline action. `ctx` gives access to other actors, marks and libraries.
function Actors.act(model: Model, beat: any, ctx: any)
	local action = beat.action
	if action == "move_to" then
		local mark = ctx.mark(beat.mark)
		glide(model, CFrame.new(mark.Position) * (model:GetPivot() - model:GetPivot().Position), beat.duration or 1)
	elseif action == "face" then
		local target = ctx.position(beat.target)
		local here = model:GetPivot().Position
		local flat = Vector3.new(target.X, here.Y, target.Z)
		glide(model, CFrame.lookAt(here, flat), beat.duration or 0.25)
	elseif action == "hop" then
		local here = model:GetPivot()
		glide(model, here, beat.duration or 0.45, beat.height or 1.5)
	elseif action == "animate" then
		local entry = ctx.library.animations[beat.animation]
		assert(entry, `unknown animation {beat.animation}`)
		local a = animator(model)
		if not a then
			warn(`[SlugshotScene] {model.Name} has no Humanoid/AnimationController; skipped {beat.animation}`)
			return
		end
		local anim = Instance.new("Animation")
		anim.AnimationId = entry.id
		local track = a:LoadAnimation(anim)
		for marker, cue in entry.markers or {} do
			track:GetMarkerReachedSignal(marker):Connect(function()
				ctx.cue(cue, model)
			end)
		end
		track:Play(beat.fade or 0.1, 1, beat.speed or 1)
	else
		error(`unknown action {action}`)
	end
end

return Actors
