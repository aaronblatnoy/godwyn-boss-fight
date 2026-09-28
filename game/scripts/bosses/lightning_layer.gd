class_name LightningLayer
extends Node


signal threshold_crossed()
signal marker_created(attack_id: String, marker_data: Dictionary)
signal strike_activated(attack_id: String, hitbox: Hitbox)
signal strike_deactivated(attack_id: String)
signal shrinking_circle_radius_changed(radius: float)
signal dragons_charge_stage_entered(stage: String)

const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")

# These five moves can begin between melee cycles. Mid-melee strikes are an
# overlay, and the slam AoE is reachable only through overhead_slam.
const IDLE_LIGHTNING_ATTACK_IDS: Array[String] = [
	"lightning_placidusax_call",
	"lightning_targeted_strikes_standalone",
	"lightning_horizontal_sweep",
	"lightning_shrinking_circle",
	"lightning_dragons_charge",
]
const ALL_LIGHTNING_ATTACK_IDS: Array[String] = [
	"lightning_placidusax_call",
	"lightning_targeted_strikes_standalone",
	"lightning_targeted_strikes_mid_melee",
	"lightning_horizontal_sweep",
	"lightning_shrinking_circle",
	"lightning_dragons_charge",
	"lightning_slam_aoe",
]
# SPEC.txt lines 405-412's mid-band (4-10m) table is the standing
# approximation for SPEC 7B's "any initiator" follow-ups because Section 7B
# supplies no separate literal weighted set for lightning continuations.
const MELEE_INITIATOR_IDS: Array[String] = [
	"x_combo",
	"jump_lunge",
	"dragons_memory",
	"the_pause",
	"sacred_cleave",
]


# ResourceLoader caches .tres instances. A per-fight library prevents the
# overhead-slam exit and dynamic lightning follow-ups from leaking to another
# boss instance while staying on AttackLibrary's public interface.
class FightAttackLibrary:
	extends AttackLibrary

	var attacks: Dictionary = {}

	func seed_from(source: AttackLibrary) -> void:
		attacks.clear()
		for source_attack: AttackData in source.get_all_attacks():
			attacks[source_attack.id] = source_attack.duplicate(true) as AttackData

	func load_default_attacks() -> void:
		# seed_from() is authoritative for this per-fight library.
		pass

	func get_attack(attack_id: String) -> AttackData:
		return attacks.get(attack_id) as AttackData

	func get_all_attacks() -> Array[AttackData]:
		var result: Array[AttackData] = []
		for attack: Variant in attacks.values():
			result.append(attack as AttackData)
		return result


@export var boss: BossBase
@export var player_target: Node3D

var _tunables: Tunables
var _rng := RandomNumberGenerator.new()
var _initialized := false
var _unlocked := false
var _threshold_tell_time_remaining := 0.0
var _last_hp_ratio := 0.0
var _merge_deferred_pending := false
var _overhead_exit_added := false
var _dragons_charge_used := false
var _mid_melee_used_this_cycle := false
var _stationary_time := 0.0
var _last_player_position := Vector3.ZERO
var _markers: Array[Dictionary] = []
var _next_marker_id := 0
var _shrinking_circle_hitboxes: Array[Hitbox] = []
var _shrinking_circle_center := Vector3.ZERO
var _shrinking_circle_elapsed := 0.0
var _shrinking_circle_active := false
var _horizontal_sweep_hitboxes: Array[Hitbox] = []
var _horizontal_sweep_line_offsets: Array[float] = []
var _horizontal_sweep_axis := Vector3.RIGHT
var _horizontal_sweep_line_axis := Vector3.FORWARD
var _horizontal_sweep_start_center := Vector3.ZERO
var _horizontal_sweep_end_center := Vector3.ZERO
var _horizontal_sweep_elapsed := 0.0
var _horizontal_sweep_active := false
var _dragons_charge_step_back_active := false
var _dragons_charge_step_back_elapsed := 0.0
var _dragons_charge_step_back_start := Vector3.ZERO
var _dragons_charge_step_back_target := Vector3.ZERO


func _ready() -> void:
	_tunables = TUNABLES_SCRIPT.new()
	_rng.randomize()
	if boss == null:
		boss = get_parent() as BossBase
	if boss == null:
		push_error("LightningLayer requires a BossBase reference or BossBase parent")
		set_process(false)
		set_physics_process(false)
		return
	if boss.attack_library == null or boss.boss_stats == null:
		call_deferred("_finish_initialization")
	else:
		_finish_initialization()


func _finish_initialization() -> void:
	if _initialized or boss == null:
		return
	if boss.attack_library == null or boss.boss_stats == null:
		push_error("LightningLayer requires BossBase._ready() to finish first")
		set_process(false)
		set_physics_process(false)
		return
	var fight_library := FightAttackLibrary.new()
	fight_library.seed_from(boss.attack_library)
	boss.attack_library = fight_library
	# Rebuild the generated animation library from the per-fight copies. The
	# lightning resources have no authored clip and use world-space Timers.
	boss.attack_library.build_runtime_animations(boss.animation_player)
	_strip_overhead_slam_exit()
	_last_hp_ratio = float(boss.get_hp()) / float(boss.get_max_hp())
	_last_player_position = (
		player_target.global_position if player_target != null else Vector3.ZERO
	)
	if not boss.hp_changed.is_connected(_on_boss_hp_changed):
		boss.hp_changed.connect(_on_boss_hp_changed)
	if not boss.attack_started.is_connected(_on_attack_started):
		boss.attack_started.connect(_on_attack_started)
	if not boss.state_changed.is_connected(_on_boss_state_changed):
		boss.state_changed.connect(_on_boss_state_changed)
	_initialized = true
	if _last_hp_ratio <= _tunables.lightning_unlock_hp_percent:
		_unlock_lightning()


func _process(delta: float) -> void:
	_threshold_tell_time_remaining = maxf(
		_threshold_tell_time_remaining - delta,
		0.0
	)
	_update_shrinking_circle(delta)
	_update_horizontal_sweep(delta)
	_update_dragons_charge_step_back(delta)


func _physics_process(delta: float) -> void:
	if not _initialized or not _unlocked:
		return
	# GodwynP1AI replaces the whole pool in its own physics callback. Deferring
	# this merge puts it after every sibling physics callback regardless of node
	# order. The merge first removes stale lightning IDs, so repeated calls are
	# idempotent and never reorder the AI's melee entries.
	if not _merge_deferred_pending:
		_merge_deferred_pending = true
		call_deferred("_run_deferred_merge")
	_update_mid_melee_stationary_trigger(delta)


func is_unlocked() -> bool:
	return _unlocked


func is_threshold_tell_active() -> bool:
	return _threshold_tell_time_remaining > 0.0


func has_dragons_charge_been_used() -> bool:
	return _dragons_charge_used


func get_active_markers() -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for marker: Dictionary in _markers:
		result.append(marker.duplicate(true))
	return result


func get_shrinking_circle_radius() -> float:
	return _calculate_shrinking_circle_radius(_shrinking_circle_elapsed)


func get_horizontal_sweep_line_offsets() -> Array[float]:
	return _horizontal_sweep_line_offsets.duplicate()


func merge_runtime_initiators() -> void:
	if not _initialized or not _unlocked or boss.moveset_tree == null:
		return
	var merged: Array[Dictionary] = []
	for entry: Dictionary in boss.moveset_tree.initiators:
		var attack_id := str(entry.get("attack_id", ""))
		if attack_id not in ALL_LIGHTNING_ATTACK_IDS:
			merged.append(entry)
	# SPEC 7B does not assign lightning selection percentages. A unit weight is
	# a neutral data-layer placeholder, not a claimed probability; the existing
	# SPEC-authored melee weights and their order remain untouched.
	for attack_id: String in IDLE_LIGHTNING_ATTACK_IDS:
		if attack_id == "lightning_dragons_charge" and _dragons_charge_used:
			continue
		merged.append({
			"attack_id": attack_id,
			"weight": 1.0,
			"continue_probability": 1.0,
		})
	boss.moveset_tree.initiators = merged


func _run_deferred_merge() -> void:
	_merge_deferred_pending = false
	merge_runtime_initiators()


func _on_boss_hp_changed(new_hp: int, maximum_hp: int) -> void:
	if maximum_hp <= 0:
		return
	var hp_ratio := float(new_hp) / float(maximum_hp)
	if (
		not _unlocked
		and _last_hp_ratio > _tunables.lightning_unlock_hp_percent
		and hp_ratio <= _tunables.lightning_unlock_hp_percent
	):
		_unlock_lightning()
	_last_hp_ratio = hp_ratio


func _unlock_lightning() -> void:
	if _unlocked:
		return
	_unlocked = true
	_threshold_tell_time_remaining = _tunables.lightning_threshold_tell_duration
	_add_overhead_slam_exit()
	threshold_crossed.emit()


func _add_overhead_slam_exit() -> void:
	if _overhead_exit_added:
		return
	var overhead := boss.attack_library.get_attack("overhead_slam")
	if overhead == null:
		push_error("LightningLayer could not resolve overhead_slam")
		return
	for option: Dictionary in overhead.exit_options:
		if str(option.get("attack_id", "")) == "lightning_slam_aoe":
			_overhead_exit_added = true
			return
	# Preserve the existing flow-into-X edge's authored placeholder weight and
	# continuation rather than introducing a new branching probability.
	var template: Dictionary = (
		overhead.exit_options.front() if not overhead.exit_options.is_empty() else {}
	)
	overhead.exit_options.append({
		"attack_id": "lightning_slam_aoe",
		"weight": float(template.get("weight", 1.0)),
		"continue_probability": float(template.get("continue_probability", 1.0)),
	})
	_overhead_exit_added = true


func _strip_overhead_slam_exit() -> void:
	var overhead := boss.attack_library.get_attack("overhead_slam")
	if overhead == null:
		push_error("LightningLayer could not resolve overhead_slam")
		return
	var retained: Array[Dictionary] = []
	for option: Dictionary in overhead.exit_options:
		if str(option.get("attack_id", "")) != "lightning_slam_aoe":
			retained.append(option)
	overhead.exit_options = retained
	_overhead_exit_added = false


func _on_attack_started(attack_id: String) -> void:
	if attack_id not in ALL_LIGHTNING_ATTACK_IDS:
		return
	if not _unlocked:
		return
	var attack := boss.attack_library.get_attack(attack_id)
	_configure_melee_followups(attack)
	match attack_id:
		"lightning_placidusax_call":
			_start_placidusax_call()
		"lightning_targeted_strikes_standalone":
			_start_targeted_strikes(attack)
		"lightning_horizontal_sweep":
			_start_horizontal_sweep()
		"lightning_shrinking_circle":
			_start_shrinking_circle()
		"lightning_dragons_charge":
			_start_dragons_charge()
		"lightning_slam_aoe":
			_start_slam_aoe()


func _on_boss_state_changed(
	_old_state: BossBase.State,
	new_state: BossBase.State
) -> void:
	if new_state == BossBase.State.IDLE:
		# A chain can contain many attack_started signals. Reset only at the
		# cycle boundary so the mid-melee overlay cannot fire once per cut.
		_mid_melee_used_this_cycle = false
		_stationary_time = 0.0
		if player_target != null:
			_last_player_position = player_target.global_position


func _configure_melee_followups(attack: AttackData) -> void:
	if attack == null:
		return
	match attack.id:
		"lightning_targeted_strikes_standalone":
			attack.exit_options = _copy_melee_entries(["jump_lunge"])
		"lightning_horizontal_sweep":
			attack.exit_options = _copy_melee_entries(["x_combo", "jump_lunge"])
		"lightning_placidusax_call", "lightning_shrinking_circle", "lightning_dragons_charge", "lightning_slam_aoe":
			attack.exit_options = _copy_melee_entries(MELEE_INITIATOR_IDS)


func _copy_melee_entries(allowed_ids: Array[String]) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for entry: Dictionary in boss.moveset_tree.initiators:
		var attack_id := str(entry.get("attack_id", ""))
		if attack_id in allowed_ids:
			result.append(entry.duplicate(true))
	if result.is_empty():
		# This fallback is only reachable before the AI has built its first pool.
		for attack_id: String in allowed_ids:
			result.append({
				"attack_id": attack_id,
				"weight": 1.0,
				"continue_probability": 1.0,
			})
	return result


func _start_placidusax_call() -> void:
	# SPEC requires a deliberate multi-strike pattern but supplies neither its
	# authored point count nor offsets. The two combatant anchors are the minimum
	# non-random greybox pattern implied by "multiple"; authored layout remains
	# a flagged data gap rather than a fabricated distance.
	var positions: Array[Vector3] = [boss.global_position]
	if player_target != null:
		positions.append(player_target.global_position)
	for index: int in positions.size():
		_schedule(
			float(index) * _tunables.lightning_pattern_strike_interval,
			_create_placidusax_marker.bind(positions[index])
		)


func _create_placidusax_marker(position: Vector3) -> void:
	var marker_id := _register_marker(
		"lightning_placidusax_call",
		position,
		_tunables.lightning_pattern_marker_warning
	)
	_schedule(
		_tunables.lightning_pattern_marker_warning,
		_activate_ground_strike.bind(
			"lightning_placidusax_call",
			position,
			marker_id
		)
	)


func _start_targeted_strikes(attack: AttackData) -> void:
	var strike_count := _rng.randi_range(
		_tunables.lightning_targeted_strike_count_min,
		_tunables.lightning_targeted_strike_count_max
	)
	# The final pulse occurs after count-1 intervals. BossBase can then take the
	# jump-lunge follow-up while the world-space strike sequence stays exact.
	attack.recovery_time = (
		float(strike_count - 1) * _tunables.lightning_targeted_strike_interval
	)
	for index: int in strike_count:
		_schedule(
			float(index) * _tunables.lightning_targeted_strike_interval,
			_pulse_targeted_strike.bind("lightning_targeted_strikes_standalone")
		)


func _pulse_targeted_strike(attack_id: String) -> void:
	if player_target == null:
		return
	var position := player_target.global_position
	# SPEC gives the interval between standalone pulses but no marker lead time.
	# The placeholder small-AoE radius lives in the attack resource.
	var marker_id := _register_marker(attack_id, position, 0.0)
	_activate_ground_strike(attack_id, position, marker_id)


func _start_horizontal_sweep() -> void:
	var marker_center := Vector3.ZERO
	_horizontal_sweep_axis = boss.global_transform.basis.x
	_horizontal_sweep_axis.y = 0.0
	if _horizontal_sweep_axis.is_zero_approx():
		_horizontal_sweep_axis = Vector3.RIGHT
	_horizontal_sweep_axis = _horizontal_sweep_axis.normalized()
	_horizontal_sweep_line_axis = boss.global_transform.basis.z
	_horizontal_sweep_line_axis.y = 0.0
	if _horizontal_sweep_line_axis.is_zero_approx():
		_horizontal_sweep_line_axis = Vector3.FORWARD
	_horizontal_sweep_line_axis = _horizontal_sweep_line_axis.normalized()
	var marker_id := _register_marker(
		"lightning_horizontal_sweep",
		marker_center,
		_tunables.lightning_horizontal_sweep_tell,
		_tunables.arena_boundary_radius
	)
	_schedule(
		_tunables.lightning_horizontal_sweep_tell,
		_begin_horizontal_sweep.bind(marker_id)
	)


func _begin_horizontal_sweep(marker_id: int = -1) -> void:
	if marker_id != -1:
		_remove_marker(marker_id)
	_horizontal_sweep_elapsed = 0.0
	_horizontal_sweep_line_offsets.clear()
	var spacing := (
		_tunables.lightning_horizontal_sweep_line_thickness
		+ _tunables.lightning_horizontal_sweep_gap_width
	)
	var formation_half_span := (
		float(_tunables.lightning_horizontal_sweep_line_count - 1)
		* spacing
		/ 2.0
	)
	for index: int in _tunables.lightning_horizontal_sweep_line_count:
		_horizontal_sweep_line_offsets.append(
			(float(index) - float(_tunables.lightning_horizontal_sweep_line_count - 1) / 2.0)
			* spacing
		)
	_horizontal_sweep_start_center = (
		boss.global_position
		- _horizontal_sweep_axis
		* (_tunables.arena_boundary_radius + formation_half_span)
	)
	_horizontal_sweep_end_center = (
		boss.global_position
		+ _horizontal_sweep_axis
		* (_tunables.arena_boundary_radius + formation_half_span)
	)
	_horizontal_sweep_active = true
	_horizontal_sweep_hitboxes.clear()
	var half_thickness := _tunables.lightning_horizontal_sweep_line_thickness / 2.0
	for index: int in _horizontal_sweep_line_offsets.size():
		var position := (
			_horizontal_sweep_start_center
			+ _horizontal_sweep_axis * _horizontal_sweep_line_offsets[index]
		)
		var hitbox := _create_hitbox(
			"lightning_horizontal_sweep",
			position,
			{
				"extents": Vector3(
					half_thickness,
					half_thickness,
					_tunables.arena_boundary_radius
				)
			}
		)
		if is_instance_valid(hitbox):
			hitbox.look_at(position + _horizontal_sweep_line_axis, Vector3.UP)
			_horizontal_sweep_hitboxes.append(hitbox)


func _update_horizontal_sweep(delta: float) -> void:
	if not _horizontal_sweep_active:
		return
	_horizontal_sweep_elapsed += delta
	var progress := clampf(
		_horizontal_sweep_elapsed / _tunables.lightning_horizontal_sweep_duration,
		0.0,
		1.0
	)
	var formation_center := _horizontal_sweep_start_center.lerp(
		_horizontal_sweep_end_center,
		progress
	)
	for index: int in _horizontal_sweep_hitboxes.size():
		var hitbox := _horizontal_sweep_hitboxes[index]
		if is_instance_valid(hitbox):
			hitbox.global_position = (
				formation_center
				+ _horizontal_sweep_axis * _horizontal_sweep_line_offsets[index]
			)
	if progress >= 1.0:
		_horizontal_sweep_active = false
		for hitbox: Hitbox in _horizontal_sweep_hitboxes:
			_deactivate_strike("lightning_horizontal_sweep", hitbox)
		_horizontal_sweep_hitboxes.clear()


func _start_shrinking_circle() -> void:
	var center := _combat_midpoint()
	var marker_id := _register_marker(
		"lightning_shrinking_circle",
		center,
		_tunables.lightning_shrinking_circle_warning,
		_tunables.lightning_shrinking_circle_start_radius
	)
	_schedule(
		_tunables.lightning_shrinking_circle_warning,
		_begin_shrinking_circle.bind(center, marker_id)
	)


func _begin_shrinking_circle(center: Vector3, marker_id: int = -1) -> void:
	if marker_id != -1:
		_remove_marker(marker_id)
	_shrinking_circle_elapsed = 0.0
	_shrinking_circle_active = true
	_shrinking_circle_center = center
	_shrinking_circle_hitboxes.clear()
	var radius := _tunables.lightning_shrinking_circle_start_radius
	var segment_count := _tunables.lightning_shrinking_circle_ring_segment_count
	var half_thickness := _tunables.lightning_shrinking_circle_ring_thickness / 2.0
	var half_chord := TAU * radius / float(segment_count) / 2.0
	for index: int in segment_count:
		var angle := float(index) * TAU / float(segment_count)
		var radial := Vector3(cos(angle), 0.0, sin(angle))
		var tangent := Vector3(-sin(angle), 0.0, cos(angle))
		var position := center + radial * radius
		var hitbox := _create_hitbox(
			"lightning_shrinking_circle",
			position,
			{"extents": Vector3(half_thickness, half_thickness, half_chord)}
		)
		if is_instance_valid(hitbox):
			hitbox.look_at(position + tangent, Vector3.UP)
			_shrinking_circle_hitboxes.append(hitbox)


func _update_shrinking_circle(delta: float) -> void:
	if not _shrinking_circle_active:
		return
	_shrinking_circle_elapsed += delta
	var radius := _calculate_shrinking_circle_radius(_shrinking_circle_elapsed)
	var segment_count := _shrinking_circle_hitboxes.size()
	var half_thickness := _tunables.lightning_shrinking_circle_ring_thickness / 2.0
	var half_chord := TAU * radius / float(segment_count) / 2.0
	for index: int in segment_count:
		var angle := float(index) * TAU / float(segment_count)
		var radial := Vector3(cos(angle), 0.0, sin(angle))
		var tangent := Vector3(-sin(angle), 0.0, cos(angle))
		var hitbox := _shrinking_circle_hitboxes[index]
		if is_instance_valid(hitbox):
			hitbox.global_position = _shrinking_circle_center + radial * radius
			hitbox.look_at(hitbox.global_position + tangent, Vector3.UP)
			hitbox.configure_window({
				"extents": Vector3(half_thickness, half_thickness, half_chord)
			})
	shrinking_circle_radius_changed.emit(radius)
	var lifetime := (
		_tunables.lightning_shrinking_circle_contraction_duration
		+ _tunables.lightning_shrinking_circle_hold
	)
	if _shrinking_circle_elapsed >= lifetime:
		_shrinking_circle_active = false
		for hitbox: Hitbox in _shrinking_circle_hitboxes:
			_deactivate_strike("lightning_shrinking_circle", hitbox)
		_shrinking_circle_hitboxes.clear()


func _calculate_shrinking_circle_radius(elapsed: float) -> float:
	if elapsed >= _tunables.lightning_shrinking_circle_contraction_duration:
		return _tunables.lightning_shrinking_circle_end_radius
	# SPEC marks both speed and duration approximate; use the authored speed and
	# clamp to the authored end radius, then hold the exact end radius at expiry.
	return maxf(
		_tunables.lightning_shrinking_circle_end_radius,
		_tunables.lightning_shrinking_circle_start_radius
		- _tunables.lightning_shrinking_circle_contraction_speed * elapsed
	)


func _start_dragons_charge() -> void:
	if _dragons_charge_used:
		return
	_dragons_charge_used = true
	merge_runtime_initiators()
	if player_target == null:
		return
	# Hold TELEGRAPH through the shove and emergence so GodwynP1AI's IDLE-only
	# pursuit cannot contend with the scripted step-back. ACTIVE begins with the
	# corridor, after which the zero-recovery attack can immediately flow onward.
	boss.state_timer = (
		_tunables.lightning_dragons_charge_step_back_duration
		+ _tunables.lightning_dragons_charge_emergence_duration
	)
	dragons_charge_stage_entered.emit("shove")
	var shove := Hitbox.new()
	shove.name = "LightningHitbox_lightning_dragons_charge_shove"
	shove.damage = 0
	shove.poise_damage = 0.0
	shove.owner_faction = "boss"
	shove.knockback = _tunables.lightning_dragons_charge_shove_knockback
	add_child(shove)
	shove.global_position = player_target.global_position
	shove.activate_window({"radius": _tunables.lightning_dragons_charge_shove_radius})
	strike_activated.emit("lightning_dragons_charge_shove", shove)
	call_deferred(
		"_deactivate_strike",
		"lightning_dragons_charge_shove",
		shove
	)

	var away_from_player := boss.global_position - player_target.global_position
	away_from_player.y = 0.0
	if away_from_player.is_zero_approx():
		away_from_player = boss.global_transform.basis.z
	away_from_player = away_from_player.normalized()
	_dragons_charge_step_back_start = boss.global_position
	_dragons_charge_step_back_target = (
		_dragons_charge_step_back_start
		+ away_from_player * _tunables.lightning_dragons_charge_step_back_distance
	)
	_dragons_charge_step_back_elapsed = 0.0
	_dragons_charge_step_back_active = true
	_schedule(
		_tunables.lightning_dragons_charge_step_back_duration,
		_begin_dragons_charge_emergence
	)


func _update_dragons_charge_step_back(delta: float) -> void:
	if not _dragons_charge_step_back_active:
		return
	_dragons_charge_step_back_elapsed += delta
	var progress := clampf(
		_dragons_charge_step_back_elapsed
		/ _tunables.lightning_dragons_charge_step_back_duration,
		0.0,
		1.0
	)
	boss.global_position = _dragons_charge_step_back_start.lerp(
		_dragons_charge_step_back_target,
		progress
	)
	if progress >= 1.0:
		_dragons_charge_step_back_active = false


func _begin_dragons_charge_emergence() -> void:
	dragons_charge_stage_entered.emit("emergence")
	_schedule(
		_tunables.lightning_dragons_charge_emergence_duration,
		_begin_dragons_charge_corridor
	)


func _begin_dragons_charge_corridor() -> void:
	if player_target == null:
		return
	dragons_charge_stage_entered.emit("charge")
	var direction := player_target.global_position - boss.global_position
	direction.y = 0.0
	if direction.is_zero_approx():
		direction = -boss.global_transform.basis.z
	direction = direction.normalized()
	var line_length := _tunables.arena_boundary_radius * 2.0
	var center := boss.global_position + direction * _tunables.arena_boundary_radius
	var half_width := _tunables.lightning_dragons_charge_fire_line_width / 2.0
	var hitbox := _create_hitbox(
		"lightning_dragons_charge",
		center,
		{"extents": Vector3(half_width, half_width, line_length / 2.0)}
	)
	if is_instance_valid(hitbox):
		hitbox.look_at(center + direction, Vector3.UP)
		_schedule(
			_tunables.lightning_dragons_charge_duration,
			_deactivate_strike.bind("lightning_dragons_charge", hitbox)
		)


func _start_slam_aoe() -> void:
	var position := boss.global_position
	var marker_id := _register_marker(
		"lightning_slam_aoe",
		position,
		0.0,
		_tunables.lightning_slam_aoe_radius
	)
	_activate_ground_strike("lightning_slam_aoe", position, marker_id)


func _update_mid_melee_stationary_trigger(delta: float) -> void:
	if player_target == null or _mid_melee_used_this_cycle:
		return
	var current_attack := boss.get_current_attack()
	if current_attack == null or current_attack.id in ALL_LIGHTNING_ATTACK_IDS:
		_stationary_time = 0.0
		_last_player_position = player_target.global_position
		return
	if player_target.global_position.is_equal_approx(_last_player_position):
		_stationary_time += delta
	else:
		_stationary_time = 0.0
		_last_player_position = player_target.global_position
	if _stationary_time >= _tunables.lightning_stationary_trigger_time:
		_mid_melee_used_this_cycle = true
		_stationary_time = 0.0
		_start_mid_melee_bolt()


func _start_mid_melee_bolt() -> void:
	if player_target == null:
		return
	var position := player_target.global_position
	var marker_id := _register_marker(
		"lightning_targeted_strikes_mid_melee",
		position,
		_tunables.lightning_mid_melee_warning
	)
	_schedule(
		_tunables.lightning_mid_melee_warning,
		_activate_ground_strike.bind(
			"lightning_targeted_strikes_mid_melee",
			position,
			marker_id
		)
	)


func _activate_ground_strike(
	attack_id: String,
	position: Vector3,
	marker_id: int = -1
) -> void:
	if marker_id != -1:
		_remove_marker(marker_id)
	var attack := boss.attack_library.get_attack(attack_id)
	var window: Dictionary = {}
	if attack != null and not attack.active_windows.is_empty():
		window = attack.active_windows.front().duplicate(true)
	window.erase("position")
	var hitbox := _create_hitbox(attack_id, position, window)
	# Lightning impacts are instantaneous. Keeping the Area active through the
	# next deferred flush gives physics one overlap window without inventing a
	# duration absent from SPEC 7B.
	call_deferred("_deactivate_strike", attack_id, hitbox)


func _create_hitbox(
	attack_id: String,
	position: Vector3,
	window: Dictionary
) -> Hitbox:
	var attack := boss.attack_library.get_attack(attack_id)
	if attack == null:
		push_error("LightningLayer could not resolve %s" % attack_id)
		return null
	var hitbox := Hitbox.new()
	hitbox.name = "LightningHitbox_%s" % attack_id
	hitbox.owner_faction = "boss"
	hitbox.damage = attack.damage
	hitbox.poise_damage = attack.poise_damage
	hitbox.damage_type = attack.damage_type
	add_child(hitbox)
	hitbox.global_position = position
	if window.has("radius") or window.has("extents"):
		hitbox.activate_window(window)
	else:
		# Defensive fallback for malformed future AttackData. Authored lightning
		# strikes must supply radius or extents so their Areas have real geometry.
		hitbox.activate()
	strike_activated.emit(attack_id, hitbox)
	return hitbox


func _deactivate_strike(attack_id: String, hitbox: Hitbox) -> void:
	if not is_instance_valid(hitbox):
		return
	hitbox.deactivate()
	strike_deactivated.emit(attack_id)
	hitbox.queue_free()


func _register_marker(
	attack_id: String,
	position: Vector3,
	lead_time: float,
	radius: float = -1.0
) -> int:
	var marker_id := _next_marker_id
	_next_marker_id += 1
	var marker := {
		"marker_id": marker_id,
		"attack_id": attack_id,
		"position": position,
		"lead_time": lead_time,
	}
	if radius >= 0.0:
		marker["radius"] = radius
	_markers.append(marker)
	marker_created.emit(attack_id, marker.duplicate(true))
	return marker_id


func _remove_marker(marker_id: int) -> void:
	var retained: Array[Dictionary] = []
	for marker: Dictionary in _markers:
		if int(marker.get("marker_id", -1)) != marker_id:
			retained.append(marker)
	_markers = retained


func _combat_midpoint() -> Vector3:
	if player_target == null:
		return boss.global_position
	return (boss.global_position + player_target.global_position) / 2.0


func _schedule(delay: float, callback: Callable) -> void:
	if delay <= 0.0:
		callback.call()
		return
	var timer := Timer.new()
	timer.one_shot = true
	timer.wait_time = delay
	timer.process_callback = Timer.TIMER_PROCESS_PHYSICS
	add_child(timer)
	timer.timeout.connect(func() -> void:
		callback.call()
		timer.queue_free()
	)
	timer.start()
