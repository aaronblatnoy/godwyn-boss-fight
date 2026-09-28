class_name GodwynP1AI
extends Node


# Phase 6 player-attack wiring calls report_player_attack() when attack input
# fires. During The Pause this schedules Godwyn's SPEC 0.12s counter; outside
# The Pause the method is intentionally a safe no-op.

const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")

@export var boss: BossBase
@export var player_target: Node3D

var _tunables: Tunables
var _rng := RandomNumberGenerator.new()
var _pause_cooldown_elapsed: float = 0.0
var _pause_in_progress := false
var _pause_was_countered := false
var _counter_pending := false
var _counter_time_remaining: float = 0.0
var _jump_lunge_bonus_for_next_pick := false
var _last_angle_to_player: float = 0.0
var _circle_direction: float = 1.0
var _memory_fragment_time_remaining: float = 0.0
var _memory_fragment_latches: Dictionary = {}
var _memory_fragment_trigger_count := 0
var _last_hp_ratio: float = 0.0
var _idle_transition_pending := false


func _ready() -> void:
	_tunables = TUNABLES_SCRIPT.new()
	_rng.randomize()
	if boss == null:
		boss = get_parent() as BossBase
	if boss == null:
		push_error("GodwynP1AI requires a BossBase reference or BossBase parent")
		set_process(false)
		set_physics_process(false)
		return
	# The Phase 4 resource is preloaded and shared. AI weights must remain local
	# to this boss instance so another boss cannot observe distance-band changes.
	boss.moveset_tree = boss.moveset_tree.duplicate(true) as MovesetTree
	_pause_cooldown_elapsed = _tunables.boss_pause_cooldown
	_last_hp_ratio = float(boss.get_hp()) / float(boss.get_max_hp())
	for threshold: float in _memory_fragment_thresholds():
		_memory_fragment_latches[threshold] = false
	if not boss.attack_started.is_connected(_on_attack_started):
		boss.attack_started.connect(_on_attack_started)
	if not boss.hp_changed.is_connected(_on_boss_hp_changed):
		boss.hp_changed.connect(_on_boss_hp_changed)
	if not boss.state_changed.is_connected(_on_boss_state_changed):
		boss.state_changed.connect(_on_boss_state_changed)
	_refresh_runtime_initiators()


func _process(delta: float) -> void:
	if boss == null:
		return
	_apply_pending_idle_transition_multiplier()
	_memory_fragment_time_remaining = maxf(
		_memory_fragment_time_remaining - delta,
		0.0
	)
	_pause_cooldown_elapsed = minf(
		_pause_cooldown_elapsed + delta,
		_tunables.boss_pause_cooldown
	)
	_update_completed_pause()
	_update_pause_counter(delta)


func _physics_process(delta: float) -> void:
	if boss == null or player_target == null:
		return
	_last_angle_to_player = _angle_to_player()
	if not is_zero_approx(_last_angle_to_player):
		_circle_direction = signf(_last_angle_to_player)
	_face_player()
	_refresh_runtime_initiators()
	if boss.current_state == BossBase.State.IDLE:
		_pursue_player(delta)


func is_memory_fragment_active() -> bool:
	return _memory_fragment_time_remaining > 0.0


func get_memory_fragment_trigger_count() -> int:
	return _memory_fragment_trigger_count


func report_player_attack() -> void:
	if boss == null or _counter_pending:
		return
	var current_attack := boss.get_current_attack()
	if current_attack == null or current_attack.id != "the_pause":
		return
	_counter_pending = true
	_counter_time_remaining = _tunables.boss_pause_counter_delay


func build_weight_table(distance_to_player: float) -> Array[Dictionary]:
	var table: Array[Dictionary] = []
	if distance_to_player < _tunables.boss_perception_close_range:
		# Radiant Sequence has no distinct Phase 4 geometry. Keep its literal
		# SPEC weight auditable here, but funnel it into the available x_combo
		# resource until the Phase 4 resource gap is resolved by that phase.
		# The six values below are the literal close-band weights in SPEC.txt line 407.
		table = [
			_entry("Sovereign's Sequence", "x_combo", 45.0),
			_entry("The Tide", "horizontal_sweep", 25.0),
			_entry("Radiant Sequence", "x_combo", 20.0),
			_entry("Dash Chain", "jump_lunge", 0.0),
			_entry("Dragon's Memory", "dragons_memory", 0.0),
			_entry("The Pause", "the_pause", 10.0),
		]
	elif distance_to_player <= _tunables.boss_perception_mid_range:
		# Sacred Cleave -> horizontal_sweep is an unresolved plan gap: Phase 4
		# authored no separate geometry, so the architect should confirm this map.
		# The six values below are the literal mid-band weights in SPEC.txt lines 409-410.
		table = [
			_entry("Sovereign's Sequence", "x_combo", 25.0),
			_entry("Sacred Cleave", "horizontal_sweep", 15.0),
			_entry("Radiant Sequence", "x_combo", 0.0),
			_entry("Dash Chain", "jump_lunge", 35.0),
			_entry("Dragon's Memory", "dragons_memory", 20.0),
			_entry("The Pause", "the_pause", 5.0),
		]
	else:
		# The six values below are the literal far-band weights in SPEC.txt line 411.
		table = [
			_entry("Sovereign's Sequence", "x_combo", 0.0),
			_entry("The Tide", "horizontal_sweep", 0.0),
			_entry("Radiant Sequence", "x_combo", 0.0),
			_entry("Dash Chain", "jump_lunge", 55.0),
			_entry("Dragon's Memory", "dragons_memory", 30.0),
			_entry("The Pause", "the_pause", 15.0),
		]
	return table


func pick_weighted_initiator(
	distance_to_player: float,
	pick_rng: RandomNumberGenerator,
	exclude_pause: bool = false
) -> String:
	var table := build_weight_table(distance_to_player)
	if exclude_pause:
		_set_weight(table, "the_pause", 0.0)
	return _pick_from_table(table, pick_rng)


func _refresh_runtime_initiators() -> void:
	if player_target == null:
		return
	var table := build_weight_table(_distance_to_player())
	if _pause_cooldown_elapsed < _tunables.boss_pause_cooldown:
		_set_weight(table, "the_pause", 0.0)
	if _jump_lunge_bonus_for_next_pick:
		var jump_weight := _weight_for(table, "jump_lunge")
		_set_weight(
			table,
			"jump_lunge",
			jump_weight * (1.0 + _tunables.boss_pause_wait_jump_lunge_bonus)
		)
	# Keep the bonus on every perception refresh until BossBase consumes one
	# initiator. attack_started then clears it, so it affects exactly one pick.
	boss.moveset_tree.initiators = table


func _on_attack_started(attack_id: String) -> void:
	# BossBase assigns the AttackData's unbuffed damage immediately before this
	# signal, so multiplying here cannot accumulate across attacks.
	if is_memory_fragment_active():
		boss.boss_hitbox.damage = roundi(
			float(boss.boss_hitbox.damage)
			* _tunables.boss_memory_fragment_damage_multiplier
		)
	if attack_id == "the_pause":
		_pause_cooldown_elapsed = 0.0
		_pause_in_progress = true
		_pause_was_countered = false
		_counter_pending = false
		var pause_attack := boss.attack_library.get_attack("the_pause")
		if pause_attack != null:
			pause_attack.recovery_time = _rng.randf_range(
				_tunables.boss_pause_duration_min,
				_tunables.boss_pause_duration_max
			)
		return
	if _jump_lunge_bonus_for_next_pick:
		_jump_lunge_bonus_for_next_pick = false


func _update_completed_pause() -> void:
	if not _pause_in_progress:
		return
	var current_attack := boss.get_current_attack()
	if current_attack != null and current_attack.id == "the_pause":
		return
	if not _pause_was_countered:
		_jump_lunge_bonus_for_next_pick = true
	_pause_in_progress = false
	_pause_was_countered = false
	_counter_pending = false


func _update_pause_counter(delta: float) -> void:
	if not _counter_pending:
		return
	var current_attack := boss.get_current_attack()
	if current_attack == null or current_attack.id != "the_pause":
		_counter_pending = false
		return
	_counter_time_remaining = maxf(_counter_time_remaining - delta, 0.0)
	if _counter_time_remaining > 0.0:
		return
	_counter_pending = false
	_pause_was_countered = true
	_step_offline()
	var attack_id := pick_weighted_initiator(_distance_to_player(), _rng, true)
	var counter_attack := boss.attack_library.get_attack(attack_id)
	if counter_attack != null:
		# SPEC.txt lines 622-625 mandate an immediate counter with no telegraph.
		# run_attack() copies telegraph_time synchronously into state_timer, so
		# restore the shared AttackData immediately to preserve its normal use.
		var authored_telegraph := counter_attack.telegraph_time
		counter_attack.telegraph_time = 0.0
		boss.run_attack(counter_attack)
		counter_attack.telegraph_time = authored_telegraph


func _pursue_player(delta: float) -> void:
	var offset := player_target.global_position - boss.global_position
	offset.y = 0.0
	var distance := offset.length()
	if distance > 0.0:
		var toward_player := offset / distance
		var tangent := Vector3(-toward_player.z, 0.0, toward_player.x) * _circle_direction
		var speed_multiplier := (
			_tunables.boss_memory_fragment_move_speed_multiplier
			if is_memory_fragment_active()
			else 1.0
		)
		var closing_step := minf(
			_tunables.boss_pursuit_speed * speed_multiplier * delta,
			distance
		)
		boss.global_position += toward_player * closing_step
		boss.global_position += (
			tangent * _tunables.boss_circle_speed * speed_multiplier * delta
		)
	_clamp_boss_to_arena()
	_face_player()


func _step_offline() -> void:
	if player_target == null:
		return
	var toward_player := player_target.global_position - boss.global_position
	toward_player.y = 0.0
	if toward_player.length_squared() > 0.0:
		toward_player = toward_player.normalized()
		var tangent := Vector3(-toward_player.z, 0.0, toward_player.x)
		boss.global_position += (
			tangent * _circle_direction * _tunables.boss_pause_counter_step_distance
		)
	_clamp_boss_to_arena()
	_face_player()


func _clamp_boss_to_arena() -> void:
	var clamped_position := boss.global_position
	var arena_offset := Vector2(clamped_position.x, clamped_position.z)
	if arena_offset.length() > _tunables.arena_boundary_radius:
		arena_offset = arena_offset.normalized() * _tunables.arena_boundary_radius
		clamped_position.x = arena_offset.x
		clamped_position.z = arena_offset.y
		boss.global_position = clamped_position


func _face_player() -> void:
	var flat_target := player_target.global_position
	flat_target.y = boss.global_position.y
	if flat_target.distance_squared_to(boss.global_position) > 0.0:
		boss.look_at(flat_target, Vector3.UP)


func _distance_to_player() -> float:
	if player_target == null or boss == null:
		return 0.0
	var offset := player_target.global_position - boss.global_position
	return Vector2(offset.x, offset.z).length()


func _angle_to_player() -> float:
	if player_target == null or boss == null:
		return 0.0
	var forward_3d := -boss.global_transform.basis.z
	var forward := Vector2(forward_3d.x, forward_3d.z).normalized()
	var offset := player_target.global_position - boss.global_position
	var toward_player := Vector2(offset.x, offset.z).normalized()
	if forward.is_zero_approx() or toward_player.is_zero_approx():
		return 0.0
	return forward.angle_to(toward_player)


func _on_boss_hp_changed(new_hp: int, maximum_hp: int) -> void:
	if maximum_hp <= 0:
		return
	var hp_ratio := float(new_hp) / float(maximum_hp)
	for threshold: float in _memory_fragment_thresholds():
		if (
			_last_hp_ratio > threshold
			and hp_ratio <= threshold
			and not bool(_memory_fragment_latches.get(threshold, false))
		):
			_memory_fragment_latches[threshold] = true
			_memory_fragment_trigger_count += 1
			# A new threshold crossing refreshes the SPEC 10-second mechanical
			# buff even if another fragment is already active.
			_memory_fragment_time_remaining = _tunables.boss_memory_fragment_duration
	_last_hp_ratio = hp_ratio


func _on_boss_state_changed(_old_state: BossBase.State, new_state: BossBase.State) -> void:
	if new_state == BossBase.State.IDLE and is_memory_fragment_active():
		# BossBase emits state_changed before assigning its new random IDLE
		# cooldown. Defer the multiplication until this AI's next process step,
		# after BossBase has populated its already-public state_timer field.
		_idle_transition_pending = true


func _apply_pending_idle_transition_multiplier() -> void:
	if not _idle_transition_pending:
		return
	_idle_transition_pending = false
	if boss.current_state == BossBase.State.IDLE and is_memory_fragment_active():
		# SPEC's "transition time between cycles" is the global-cooldown IDLE
		# timer. This uses only BossBase's existing public state_timer surface.
		boss.state_timer *= _tunables.boss_memory_fragment_transition_time_multiplier


func _memory_fragment_thresholds() -> Array[float]:
	return [
		_tunables.boss_memory_fragment_threshold_75,
		_tunables.boss_memory_fragment_threshold_50,
		_tunables.boss_memory_fragment_threshold_25,
	]


func _entry(spec_name: String, attack_id: String, weight: float) -> Dictionary:
	return {
		"spec_name": spec_name,
		"attack_id": attack_id,
		"weight": weight,
		"continue_probability": 1.0,
	}


func _pick_from_table(table: Array[Dictionary], pick_rng: RandomNumberGenerator) -> String:
	var total_weight := 0.0
	for entry: Dictionary in table:
		total_weight += maxf(float(entry.get("weight", 0.0)), 0.0)
	if total_weight <= 0.0:
		return ""
	var roll := pick_rng.randf_range(0.0, total_weight)
	for entry: Dictionary in table:
		roll -= maxf(float(entry.get("weight", 0.0)), 0.0)
		if roll <= 0.0:
			return str(entry.get("attack_id", ""))
	return str(table.back().get("attack_id", ""))


func _set_weight(table: Array[Dictionary], attack_id: String, weight: float) -> void:
	for index: int in table.size():
		if str(table[index].get("attack_id", "")) == attack_id:
			var entry := table[index]
			entry["weight"] = weight
			table[index] = entry


func _weight_for(table: Array[Dictionary], attack_id: String) -> float:
	var total := 0.0
	for entry: Dictionary in table:
		if str(entry.get("attack_id", "")) == attack_id:
			total += float(entry.get("weight", 0.0))
	return total
