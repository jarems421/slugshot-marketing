--!strict
-- Game-truth rules checked again at run time (tools/scene.py checks them before a spec is built in).
-- Keep in step with docs/game-truth.md and tools/scene.py.
local Canon = {}

Canon.MODES = { authentic_gameplay = true, staged_gameplay = true, staged_fiction = true, hybrid_bridge = true }

-- Actions that would show a slug transforming or using an ability. Floppy never does either.
Canon.TRANSFORM_ACTIONS = { transform = true, ability = true, ability_q = true, ability_e = true }
Canon.NEVER_TRANSFORMS = { floppy = true }

function Canon.check(spec: any): (boolean, string?)
	local truth = spec.truth
	if typeof(truth) ~= "table" or not Canon.MODES[truth.mode] then
		return false, "truth.mode must be authentic_gameplay, staged_gameplay, staged_fiction or hybrid_bridge"
	end
	if truth.mode == "authentic_gameplay" then
		return false, "authentic gameplay is captured from real play, not staged by the scene runner"
	end
	local identities: { [string]: string } = {}
	for name, actor in spec.actors or {} do
		identities[name] = actor.identity or (actor.species and string.lower(actor.species))
	end
	for _, beat in spec.timeline or {} do
		local identity = beat.actor and identities[beat.actor]
		if identity and Canon.NEVER_TRANSFORMS[identity] and Canon.TRANSFORM_ACTIONS[beat.action or ""] then
			return false, `{identity} never transforms or uses abilities (beat at {beat.time}s)`
		end
		if beat.animation and identity and Canon.NEVER_TRANSFORMS[identity] then
			local anim = string.lower(beat.animation)
			if string.find(anim, "transform") or string.find(anim, "ability") then
				return false, `{identity} cannot play {beat.animation}`
			end
		end
	end
	return true, nil
end

return Canon
