--!strict
-- Temporary locations (owner, 2026-11-27): quick, reusable sets outside the lobby (a bedroom, a classroom, a wild
-- cavern, a market) in the Slugshot look, so videos can go anywhere. Each lives in roblox-native/library/locations
-- as data and is built here at play time, once, under workspace.SS_Locations: plain boxes for floors and walls,
-- props made with Studio's mesh generator (by asset id), pieces cloned from the game's own hub art (already inked),
-- and lights. Nothing is saved into the place, so a rebuild never loses them and git holds the whole set.
--
-- Ink: the hub draws its outlines as ink shells; boxes and generated props get one charcoal Highlight per group
-- (floor, walls, props) instead of one each, because Roblox renders at most 31 Highlights and every actor uses one.
local AssetService = game:GetService("AssetService")

local Locations = {}

local INK = Color3.fromRGB(14, 14, 18) -- the hub's ink (HubMotion)

local function rgb(c: { number }?, default: Color3): Color3
	return if c then Color3.fromRGB(c[1], c[2], c[3]) else default
end

local function place(origin: CFrame, at: { number }): CFrame
	return origin * CFrame.new(at[1], at[2] or 0, at[3] or 0) * CFrame.Angles(0, math.rad(at[4] or 0), 0)
end

local function inked(group: Model, width: number?)
	local h = Instance.new("Highlight")
	h.FillTransparency = 1
	h.OutlineColor = INK
	h.OutlineTransparency = 0
	h.DepthMode = Enum.HighlightDepthMode.Occluded
	h.Adornee = group
	h.Parent = group
end

-- The first model of that name anywhere in the hub's art (the game builds it in about two minutes).
local function kit(name: string, index: number?): Instance?
	local art = workspace:FindFirstChild("HubArt")
	if not art then
		return nil
	end
	local n = 0
	for _, d in art:GetDescendants() do
		if d.Name == name and (d:IsA("Model") or d:IsA("BasePart")) then
			n += 1
			if n >= (index or 1) then
				return d
			end
		end
	end
	return nil
end

local meshCache: { [string]: MeshPart } = {}
local function mesh(id: string): MeshPart?
	if meshCache[id] == nil then
		local ok, part = pcall(function()
			return AssetService:CreateMeshPartAsync(id)
		end)
		if not ok then
			warn(`Locations: mesh {id} failed to load: {part}`)
			return nil
		end
		meshCache[id] = part :: MeshPart
	end
	return meshCache[id]:Clone()
end

function Locations.origin(loc: any): CFrame
	local o = loc.origin
	return CFrame.new(o[1], o[2] or 0, o[3] or 0)
end

-- Builds (or returns the already built) location; same pieces in the same places every time.
function Locations.ensure(loc: any): Model
	local root = workspace:FindFirstChild("SS_Locations") or Instance.new("Folder")
	root.Name = "SS_Locations"
	root.Parent = workspace
	local existing = root:FindFirstChild(loc.name)
	if existing then
		return existing :: Model
	end
	local model = Instance.new("Model")
	model.Name = loc.name
	local groups: { [string]: Model } = {}
	local function group(name: string): Model
		if not groups[name] then
			local g = Instance.new("Model")
			g.Name = name
			g.Parent = model
			groups[name] = g
			if name ~= "kit" and name ~= "lights" then
				inked(g)
			end
		end
		return groups[name]
	end
	local origin = Locations.origin(loc)
	for i, p in loc.pieces do
		local cf = place(origin, p.at or { 0, 0, 0 })
		if p.box then
			local part = Instance.new("Part")
			part.Name = p.name or `box{i}`
			part.Anchored = true
			part.Size = Vector3.new(p.box[1], p.box[2], p.box[3])
			part.CFrame = cf
			part.Color = rgb(p.color, Color3.fromRGB(120, 110, 140))
			part.Material = (Enum.Material :: any)[p.material or "SmoothPlastic"]
			part.CanCollide = p.solid ~= false
			part.CanQuery = p.solid ~= false
			part.CastShadow = p.shadow ~= false
			if p.glow then
				part.Material = Enum.Material.Neon
				local l = Instance.new("SurfaceLight")
				l.Face = (Enum.NormalId :: any)[p.glow.face or "Front"]
				l.Color = part.Color
				l.Range = p.glow.range or 16
				l.Brightness = p.glow.brightness or 1.5
				l.Shadows = false
				l.Parent = part
			end
			part.Parent = group(p.group or "props")
		elseif p.mesh then
			local part = mesh(p.mesh)
			if part then
				part.Name = p.name or `prop{i}`
				part.TextureID = p.tex or ""
				part.Anchored = true
				part.CanCollide = p.solid == true
				part.CanQuery = p.solid == true
				local base = part.Size
				part.Size = if p.size then Vector3.new(p.size[1], p.size[2], p.size[3]) else base * (p.scale or 1)
				-- sit on the floor: `at` is where the prop's base touches the ground
				part.CFrame = cf * CFrame.new(0, part.Size.Y / 2, 0)
				part.Parent = group(p.group or "props")
			end
		elseif p.kit then
			local source = kit(p.kit, p.index)
			if source then
				local copy = source:Clone()
				for _, d in copy:GetDescendants() do
					if d:IsA("Script") or d:IsA("LocalScript") or d:IsA("ModuleScript") then
						d:Destroy()
					elseif d:IsA("BasePart") then
						d.Anchored = true
					end
				end
				if copy:IsA("Model") then
					if p.scale and p.scale ~= 1 then
						copy:ScaleTo(copy:GetScale() * p.scale)
					end
					-- keep the piece's own tilt, turn it by `at`'s yaw, then lift it so its lowest point sits at `at`
					local pivot = copy:GetPivot()
					copy:PivotTo(cf * (pivot - pivot.Position))
					local box, size = copy:GetBoundingBox()
					copy:PivotTo(copy:GetPivot() + Vector3.new(0, cf.Y - (box.Position.Y - size.Y / 2), 0))
				else
					(copy :: BasePart).CFrame = cf
				end
				copy.Parent = group("kit")
			else
				warn(`Locations: no hub piece {p.kit} (is the hub built?)`)
			end
		elseif p.light then
			local holder = Instance.new("Part")
			holder.Name = `light{i}`
			holder.Anchored, holder.CanCollide, holder.CanQuery, holder.CanTouch = true, false, false, false
			holder.Transparency = 1
			holder.Size = Vector3.one * 0.2
			holder.CFrame = cf
			local l = Instance.new("PointLight")
			l.Color = rgb(p.color, Color3.fromRGB(255, 214, 160))
			l.Range = p.range or 20
			l.Brightness = p.brightness or 1.2
			l.Shadows = p.shadows == true
			l.Parent = holder
			holder.Parent = group("lights")
		end
	end
	model.Parent = root
	return model
end

return Locations
