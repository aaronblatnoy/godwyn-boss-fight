class_name MovesetTree
extends Resource

@export var initiators: Array[Dictionary] = []
@export var state_exits: Dictionary = {}


func get_exits_for_state(state_name: String) -> Array:
	var options: Array = initiators if state_name == "IDLE" else state_exits.get(state_name, [])
	var attack_ids: Array = []
	for option: Variant in options:
		if option is Dictionary:
			var attack_id: String = str((option as Dictionary).get("attack_id", ""))
			if not attack_id.is_empty():
				attack_ids.append(attack_id)
	return attack_ids


func pick_next_attack(state_name: String, rng: RandomNumberGenerator) -> String:
	var options: Array = initiators if state_name == "IDLE" else state_exits.get(state_name, [])
	return pick_weighted_option(options, rng)


func pick_attack_followup(attack: AttackData, rng: RandomNumberGenerator) -> String:
	if attack == null:
		return ""
	return pick_weighted_option(attack.exit_options, rng)


func pick_weighted_option(options: Array, rng: RandomNumberGenerator) -> String:
	var total_weight := 0.0
	for option: Variant in options:
		if option is Dictionary:
			total_weight += maxf(float((option as Dictionary).get("weight", 0.0)), 0.0)
	if total_weight <= 0.0:
		return ""
	var roll := rng.randf_range(0.0, total_weight)
	for option: Variant in options:
		if not option is Dictionary:
			continue
		var entry := option as Dictionary
		roll -= maxf(float(entry.get("weight", 0.0)), 0.0)
		if roll <= 0.0:
			return _roll_continuation(entry, rng)
	return _roll_continuation(options.back() as Dictionary, rng)


func _roll_continuation(entry: Dictionary, rng: RandomNumberGenerator) -> String:
	var continue_probability := clampf(float(entry.get("continue_probability", 1.0)), 0.0, 1.0)
	if rng.randf() > continue_probability:
		return ""
	return str(entry.get("attack_id", ""))


func resolve_post_attack_state(attack: AttackData, did_overshoot: bool) -> String:
	if attack == null:
		return "IDLE"
	if did_overshoot and attack.overshoot_possible:
		return "BACK_TO_PLAYER"
	return attack.enters_state
