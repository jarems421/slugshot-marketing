--!nonstrict
-- Named camera presets -> Reel shots. A shot entry in a spec:
--   { preset = "orbit_reveal", target = "floppy", duration = 2, ...preset options }
-- Positions are read when the take's shots are built (after actors spawn); targets follow actors.
local Cameras = {}

local function ease(u: number): number
	u = math.clamp(u, 0, 1)
	return u * u * (3 - 2 * u)
end

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
	-- `look` (the target's own axes, like `offset`) aims off the target, e.g. between two people walking together.
	follow = function(s, ctx)
		local o, l = s.offset or { 0, 3, 8 }, s.look or { 0, 0, 0 }
		return ctx.Shot.follow({ target = ctx.target(s.target), offset = Vector3.new(o[1], o[2], o[3]),
			aim = Vector3.new(l[1], l[2], l[3]), duration = s.duration, fov = s.fov or 55 })
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
	-- A slug shot as its own moment (owner, 2026-11-26): from beside the shooter's muzzle, the camera rides along with
	-- the flying slug (`target` = the shooter, `shot` = which of their slug shots), a little behind and to one side,
	-- looking ahead of it, so its twirl, glow and transformation fill the frame.
	slug_shot = function(s, ctx)
		local side, back, up = s.side or 2.2, s.back or 3.2, s.height or 0.8
		return {
			duration = s.duration,
			pose = function(lt)
				local cf = ctx.slug(s.target, s.shot or 1, ctx.start + lt) or ctx.frame(s.target)
				local at = cf.Position + cf.RightVector * side - cf.LookVector * back + Vector3.new(0, up, 0)
				return CFrame.lookAt(at, cf.Position + cf.LookVector * (s.lead or 1.5)), s.fov or 55, nil
			end,
		}
	end,
	-- The slug-shot cutscene camera (owner, 2026-11-26: the ride-along was "too zoomed in" with "no emphasis"). Frames
	-- the shooter's `shot` (`target` = the shooter) wide enough to read the twirl, the transformation and the world:
	--   mode "orbit": circles the slug in flight through `sweep` {from, to} degrees (0 = its right side, 90 = ahead),
	--                 `distance` and `height` in studs, aiming `lead` studs ahead; pair with clock "output" and a
	--                 slowmo segment for a bullet-time sweep.
	--   mode "pan":   locked off beside the path, `along` (0 muzzle .. 1 target), `distance` to its `side` (1 right,
	--                 -1 left), and turns to follow the slug.
	--   mode "ride":  the default single-shot cutscene. Rides beside the slug at `angle` degrees (0 = its right side,
	--                 90 = ahead), `near` studs away while it twirls, easing out to `distance` from `zoom_at` seconds
	--                 after launch (default: 0.7 of the slug's twirl, as the glow hides the swap) over `zoom_for`, then
	--                 holds through the game's impact and burrow. Split screen is for duels only (owner, 2026-11-26).
	slug_cam = function(s, ctx)
		local k = s.shot or 1
		local function slugAt(lt)
			return ctx.slug(s.target, k, ctx.start + lt) or ctx.frame(s.target)
		end
		local first = slugAt(0)
		local way = Vector3.new(first.LookVector.X, 0, first.LookVector.Z).Unit
		local right = way:Cross(Vector3.yAxis)
		local fov, dist, up = s.fov or 40, s.distance or 7, s.height or 1
		local fixed = nil
		if s.mode == "pan" then
			local path = ctx.slug(s.target, k, math.huge)
			local from, to = first.Position, if path then path.Position else first.Position + way * 10
			fixed = from:Lerp(to, s.along or 0.3) + right * dist * (s.side or 1) + Vector3.new(0, up, 0)
		end
		return {
			duration = s.duration,
			pose = function(lt)
				local cf = slugAt(lt)
				local p = cf.Position
				if fixed then
					return CFrame.lookAt(fixed, p + way * (s.lead or 0)), fov, nil
				end
				if s.mode == "ride" then
					-- One unbroken angle beside the slug (owner, 2026-11-26: no angle changes mid-shot): close while it
					-- twirls, easing out as the glow hides the swap so the transformed form fits, then wide through the
					-- hit and the burrow (the path stops at the target, so the camera settles there).
					local plan, spin = ctx.shotPlan(s.target, k)
					local tau = ctx.start + lt - (if plan then plan.t else ctx.start)
					local zoomAt = s.zoom_at or (if spin then spin * 0.7 else math.huge)
					local u = ease((tau - zoomAt) / (s.zoom_for or 0.35))
					-- Wide enough for the transformed form in a 9:16 frame (its length across the narrow width), unless
					-- `distance` says otherwise; after the hit it eases in to `land` so the fall and burrow read.
					local far = s.distance
					if not far then
						local size = 0
						local live = plan and plan.live
						local form = live and live.state and live.state.form
						if form and form.Parent then
							local _, ext = form:GetBoundingBox()
							size = math.max(ext.X, ext.Z)
						end
						local half = math.atan(math.tan(math.rad(fov) / 2) * 9 / 16)
						far = math.max(7, size * 0.75 / math.tan(half) + 1)
						s._far = math.max(s._far or 0, far)
						far = s._far
					end
					local d = (s.near or 2.4) + (far - (s.near or 2.4)) * u
					local lead = (s.lead or 0) * u
					if plan and tau > plan.flight then
						-- after the hit the slug bounces back and burrows where it lands: look at it, not ahead of it
						lead *= 1 - ease((tau - plan.flight) / 0.25)
						local k = ease((tau - plan.flight - 0.4) / 0.6)
						d += ((s.land or 4) - d) * k
					end
					local angle = math.rad(s.angle or 35)
					local dir = right * math.cos(angle) + way * math.sin(angle)
					local at = p + dir * d + Vector3.new(0, up * (0.35 + 0.65 * u), 0)
					return CFrame.lookAt(at, p + way * lead), fov, nil
				end
				local u = if s.duration > 0 then ease(lt / s.duration) else 0
				local sweep = s.sweep or { 20, 70 }
				local angle = math.rad(sweep[1] + (sweep[2] - sweep[1]) * u)
				local dir = right * math.cos(angle) + way * math.sin(angle)
				local at = p + dir * dist + Vector3.new(0, up, 0)
				return CFrame.lookAt(at, p + way * (s.lead or 0.8)), fov, nil
			end,
		}
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
-- A `split` shot (owner, 2026-11-26: "your screen gets split in half ... then your screen comes together") holds two
-- views of the same moment. A take films view 1; a second pass with layer "b" films view 2, and take.py split
-- composites them, top and bottom, behind a slanted divider that opens and closes. Each view is any shot entry.
function Cameras.build(shotSpec: any, ctx: any, start: number)
	if shotSpec.preset == "split" then
		local view = table.clone(shotSpec.views[if ctx.layer == "b" then 2 else 1])
		view.duration = shotSpec.duration
		view.clock = view.clock or shotSpec.clock
		return Cameras.build(view, ctx, start)
	end
	local preset = Cameras.presets[shotSpec.preset]
	assert(preset, `unknown camera preset {shotSpec.preset}`)
	local inner
	return {
		duration = shotSpec.duration,
		start = start,
		clock = shotSpec.clock, -- "output": moves at the video's pace through slow motion
		-- what the shot looks at: the camera keeps a clear line to it (init.luau `unblock`); rides and splits have none
		subject = if shotSpec.preset == "slug_cam" or shotSpec.preset == "slug_shot" then nil
			else shotSpec.target or (shotSpec.targets and shotSpec.targets[1]),
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
