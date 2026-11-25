--!nonstrict
-- Named camera presets -> Reel shots. A shot entry in a spec:
--   { preset = "orbit_reveal", target = "floppy", duration = 2, ...preset options }
-- Positions are read when the take's shots are built (after actors spawn); targets follow actors.
local Cameras = {}

local function behind(pos: Vector3, facing: Vector3, distance: number, height: number): Vector3
	local flat = Vector3.new(facing.X, 0, facing.Z)
	flat = if flat.Magnitude > 1e-3 then flat.Unit else Vector3.new(0, 0, -1)
	return pos + flat * distance + Vector3.new(0, height, 0)
end

-- ctx: { Shot, Curve, target(name) -> () -> CFrame?, frame(name) -> CFrame, center(names) -> Vector3 }
Cameras.presets = {
	-- Wide, fixed: the whole set or both actors.
	static_wide = function(s, ctx)
		local c = ctx.center(s.targets or { s.target })
		local f = ctx.frame((s.targets or { s.target })[1])
		local at = behind(c, f.LookVector, s.distance or 16, s.height or 6)
		return ctx.Shot.still({ at = CFrame.lookAt(at, c + Vector3.new(0, s.aim or 1.5, 0)), duration = s.duration, fov = s.fov or 50 })
	end,
	-- Two actors framed together, from the side of their line.
	two_shot = function(s, ctx)
		local a, b = ctx.frame(s.targets[1]).Position, ctx.frame(s.targets[2]).Position
		local mid = (a + b) / 2
		local side = (b - a).Unit:Cross(Vector3.yAxis)
		local at = mid + side * (s.distance or ((b - a).Magnitude * 0.9 + 4)) + Vector3.new(0, s.height or 2.5, 0)
		return ctx.Shot.still({ at = CFrame.lookAt(at, mid + Vector3.new(0, s.aim or 1.5, 0)), duration = s.duration, fov = s.fov or 45 })
	end,
	orbit_reveal = function(s, ctx)
		return ctx.Shot.orbit({ target = ctx.target(s.target), radius = s.radius or 8, height = s.height or 2.2,
			from = s.from or -40, to = s.to or 40, duration = s.duration, fov = s.fov or 50 })
	end,
	dolly_in = function(s, ctx)
		local f = ctx.frame(s.target)
		local aim = f.Position + Vector3.new(0, s.aim or 1, 0)
		local from = behind(f.Position, f.LookVector, s.from_distance or 14, s.height or 2.5)
		local to = behind(f.Position, f.LookVector, s.to_distance or 6, s.height or 2.5)
		return ctx.Shot.dolly({ from = CFrame.lookAt(from, aim), to = CFrame.lookAt(to, aim), duration = s.duration,
			fov = s.fov or 50, ease = ctx.Curve.rise(0, 1) })
	end,
	-- Low, close, looking up: makes a small slug look big.
	slug_low_angle = function(s, ctx)
		local f = ctx.frame(s.target)
		local at = behind(f.Position, f.LookVector, s.distance or 5, s.height or 0.4)
		return ctx.Shot.still({ at = CFrame.lookAt(at, f.Position + Vector3.new(0, s.aim or 1.2, 0)), duration = s.duration, fov = s.fov or 60 })
	end,
	reaction_closeup = function(s, ctx)
		local f = ctx.frame(s.target)
		local head = f.Position + Vector3.new(0, s.aim or 4.5, 0)
		local at = behind(head, f.LookVector, s.distance or 4, 0.2)
		return ctx.Shot.still({ at = CFrame.lookAt(at, head), duration = s.duration, fov = s.fov or 40 })
	end,
	follow = function(s, ctx)
		local o = s.offset or { 0, 3, 8 }
		return ctx.Shot.follow({ target = ctx.target(s.target), offset = Vector3.new(o[1], o[2], o[3]), duration = s.duration, fov = s.fov or 55 })
	end,
	-- Fast punch-in: same framing, field of view snaps narrower early in the shot.
	snap_zoom = function(s, ctx)
		local f = ctx.frame(s.target)
		local aim = f.Position + Vector3.new(0, s.aim or 1.5, 0)
		local at = behind(f.Position, f.LookVector, s.distance or 10, s.height or 3)
		local snap = math.clamp((s.snap or 0.15) / s.duration, 0.01, 1)
		return ctx.Shot.still({ at = CFrame.lookAt(at, aim), duration = s.duration, fov = ctx.Curve.ease(s.fov or 55, s.fov_end or 30, snap) })
	end,
	-- Size-aware framings for creatures of any size. `size` is the frame height in actor heights (1.2 = a tight
	-- close-up of a slug, 2.5 = a medium shot). `side` swings the camera off the actor's face axis (degrees,
	-- positive to the actor's left) so eyelines read; `eye` is the camera height as a fraction of actor height.
	close_up = function(s, ctx)
		local f, h = ctx.frame(s.target), ctx.height(s.target)
		local head = ctx.head(s.target)
		local fov = s.fov or 30
		local dist = (s.size or 1.3) * h / (2 * math.tan(math.rad(fov) / 2))
		local dir = (f * CFrame.Angles(0, math.rad(s.side or 18), 0)).LookVector
		local at = head + dir * dist + Vector3.new(0, (s.eye or 0) * h, 0)
		local aim = head - Vector3.new(0, (s.headroom or 0.12) * h, 0)
		return ctx.Shot.still({ at = CFrame.lookAt(at, aim), duration = s.duration, fov = fov })
	end,
	-- A slow push from `from_size` to `size`: the camera tells you who matters ("this is Floppy").
	push_in = function(s, ctx)
		local f, h = ctx.frame(s.target), ctx.height(s.target)
		local head = ctx.head(s.target)
		local fov = s.fov or 32
		local k = h / (2 * math.tan(math.rad(fov) / 2))
		local dir = (f * CFrame.Angles(0, math.rad(s.side or 10), 0)).LookVector
		local lift = Vector3.new(0, (s.eye or 0.05) * h, 0)
		local aim = head - Vector3.new(0, (s.headroom or 0.15) * h, 0)
		local from = head + dir * (s.from_size or 3) * k + lift
		local to = head + dir * (s.size or 1.4) * k + lift
		return ctx.Shot.dolly({ from = CFrame.lookAt(from, aim), to = CFrame.lookAt(to, aim), duration = s.duration,
			fov = fov, ease = ctx.Curve.rise(0, 1) })
	end,
	-- Shot/reverse-shot: over `from`'s shoulder onto `target`'s face. `shoulder` picks the side (1 right, -1 left).
	over_shoulder = function(s, ctx)
		local a, b = ctx.frame(s.from).Position, ctx.head(s.target)
		local ha = ctx.height(s.from)
		local flat = Vector3.new(b.X - a.X, 0, b.Z - a.Z).Unit
		local right = flat:Cross(Vector3.yAxis)
		local at = a - flat * (s.back or 1.1) * ha + right * (s.shoulder or 1) * (s.offset or 0.55) * ha
			+ Vector3.new(0, (s.eye or 0.85) * ha, 0)
		return ctx.Shot.still({ at = CFrame.lookAt(at, b - Vector3.new(0, 0.1 * ctx.height(s.target), 0)),
			duration = s.duration, fov = s.fov or 34 })
	end,
	whip_pan = function(s, ctx)
		local a, b = ctx.frame(s.from).Position, ctx.frame(s.to).Position
		local at = (a + b) / 2 + Vector3.new(0, s.height or 3, 0) + (b - a).Unit:Cross(Vector3.yAxis) * (s.distance or 10)
		return ctx.Shot.whip({ at = at, from = ctx.target(s.from), to = ctx.target(s.to), duration = s.duration, fov = s.fov or 50 })
	end,
}

-- `ctx.at(start)` returns a context whose frame/head/position read actors as they stand at the shot's start,
-- so fixed framings use where actors are at that cut, and a still posed mid-shot frames it the same way as
-- the filmed take. After that the shot is a pure function of its local time.
function Cameras.build(shotSpec: any, ctx: any, start: number)
	local preset = Cameras.presets[shotSpec.preset]
	assert(preset, `unknown camera preset {shotSpec.preset}`)
	local inner
	return {
		duration = shotSpec.duration,
		start = start,
		pose = function(t: number)
			if not inner then
				inner = preset(shotSpec, ctx.at(start))
				if shotSpec.shake then
					inner = ctx.Shot.shake(inner, { amplitude = shotSpec.shake, seed = ctx.seed })
				end
			end
			return inner.pose(t)
		end,
	}
end

-- Vertical video from a landscape viewport: roll the camera a quarter turn so the 9:16 frame lies along the
-- viewport's long side (native pixels instead of an upscaled centre crop), and convert the spec's FOV (the
-- 9:16 frame's vertical FOV) to Roblox's FieldOfView (the viewport's vertical, i.e. the portrait's horizontal).
function Cameras.portrait(cf: CFrame, fov: number): (CFrame, number)
	local h = 2 * math.deg(math.atan(math.tan(math.rad(fov) / 2) * 9 / 16))
	return cf * CFrame.Angles(0, 0, math.rad(90)), h
end

return Cameras
