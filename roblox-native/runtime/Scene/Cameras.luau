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
	whip_pan = function(s, ctx)
		local a, b = ctx.frame(s.from).Position, ctx.frame(s.to).Position
		local at = (a + b) / 2 + Vector3.new(0, s.height or 3, 0) + (b - a).Unit:Cross(Vector3.yAxis) * (s.distance or 10)
		return ctx.Shot.whip({ at = at, from = ctx.target(s.from), to = ctx.target(s.to), duration = s.duration, fov = s.fov or 50 })
	end,
}

function Cameras.build(shotSpec: any, ctx: any)
	local preset = Cameras.presets[shotSpec.preset]
	assert(preset, `unknown camera preset {shotSpec.preset}`)
	-- Built lazily, when the shot first plays, so fixed framings use where actors are at that cut
	-- (an actor may have moved since the take started). After that the shot is a pure function of t.
	local inner
	return {
		duration = shotSpec.duration,
		pose = function(t: number)
			if not inner then
				inner = preset(shotSpec, ctx)
				if shotSpec.shake then
					inner = ctx.Shot.shake(inner, { amplitude = shotSpec.shake, seed = ctx.seed })
				end
			end
			return inner.pose(t)
		end,
	}
end

return Cameras
