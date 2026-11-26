-- Marketing place only (added by roblox-native/tools/make_marketing_place.py): the server half of human actors
-- (Scene/Humans.luau). Players:CreateHumanoidModelFromDescription and InsertService run on the server only, so the
-- filming client asks here, through ReplicatedStorage.SlugshotMarketing.Cast, for:
--   "rig", key, look      an R6 character from free Roblox-owned clothing and hair (catalog IDs), stored as
--                         ReplicatedStorage.SlugshotMarketingRigs[key]
--   "emote", catalogId    a free Roblox emote's KeyframeSequence, stored as SlugshotMarketingRigs["emote_<id>"]
-- Nothing is published, bought or uploaded; the place never saves these.
local InsertService = game:GetService("InsertService")
local KeyframeSequenceProvider = game:GetService("KeyframeSequenceProvider")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local remote = ReplicatedStorage:WaitForChild("SlugshotMarketing"):WaitForChild("Cast") :: RemoteFunction
local store = Instance.new("Folder")
store.Name = "SlugshotMarketingRigs"
store.Parent = ReplicatedStorage

local function color(c: { number }?, default: Color3): Color3
	return if c then Color3.fromRGB(c[1], c[2], c[3]) else default
end

local ACCESSORIES = { hair = "HairAccessory", hat = "HatAccessory", face = "FaceAccessory", neck = "NeckAccessory",
	back = "BackAccessory", front = "FrontAccessory", shoulder = "ShouldersAccessory", waist = "WaistAccessory" }

local function rig(key: string, look: any): string
	local d = Instance.new("HumanoidDescription")
	local skin = color(look.skin, Color3.fromRGB(234, 184, 146))
	local colors = look.colors or {}
	for _, part in { "Head", "Torso", "LeftArm", "RightArm", "LeftLeg", "RightLeg" } do
		(d :: any)[part .. "Color"] = color(colors[part], skin)
	end
	d.Shirt = look.shirt or 0
	d.Pants = look.pants or 0
	d.GraphicTShirt = look.tshirt or 0
	for field, property in ACCESSORIES do
		if look[field] then
			(d :: any)[property] = table.concat(look[field], ",")
		end
	end
	local model = Players:CreateHumanoidModelFromDescription(d, Enum.HumanoidRigType.R6)
	local old = store:FindFirstChild(key)
	if old then
		old:Destroy()
	end
	model.Name = key
	model.Parent = store
	return key
end

local function emote(id: number): string
	local key = `emote_{math.floor(id)}`
	if store:FindFirstChild(key) then
		return key
	end
	local asset = InsertService:LoadAsset(id)
	local ks = asset:FindFirstChildWhichIsA("KeyframeSequence", true)
	if not ks then
		local animation = asset:FindFirstChildWhichIsA("Animation", true)
		assert(animation, `catalog item {id} holds no animation`)
		ks = KeyframeSequenceProvider:GetKeyframeSequenceAsync(animation.AnimationId)
	end
	ks.Name = key
	ks.Parent = store
	asset:Destroy()
	return key
end

remote.OnServerInvoke = function(_player: Player, op: string, a: any, b: any)
	if op == "rig" and type(a) == "string" and type(b) == "table" then
		return rig(a, b)
	elseif op == "emote" and type(a) == "number" then
		return emote(a)
	end
	error(`SlugshotMarketing.Cast: bad request {op}`)
end
