class_name PlayerCombat
extends Node


const TunablesScript := preload("res://scripts/systems/tunables.gd")

enum State {
	FREE,
	SPRINT,
	ROLL,
	LIGHT_ATTACK,
	HEAVY_ATTACK,
	FLASK,
	DEAD,
}

const MAX_LIGHT_COMBO_HITS := 3 # SPEC.txt Section 3: light attacks chain for 2-3 hits.

var tunables := TunablesScript.new()
var state: State = State.FREE
var roll_elapsed: float = 0.0
var attack_elapsed: float = 0.0
var flask_elapsed: float = 0.0

var _light_combo_count: int = 0
var _light_attack_buffered: bool = false


func get_roll_t() -> float:
	# frame->t: t = frame / assumed_clip_length_frames, where
	# assumed_clip_length_frames = roll_iframe_start_frame / roll_iframe_start_t
	# = roll_iframe_end_frame / roll_iframe_end_t once a real clip length is known.
	# Until Phase 9 imports the real rig/animation, the normalized boundaries come
	# directly from SPEC's authoritative seconds rather than an arbitrary frame count.
	return clampf(roll_elapsed / tunables.roll_duration, 0.0, 1.0)


func is_roll_invulnerable_at(roll_t: float) -> bool:
	return roll_t >= tunables.roll_iframe_start_t and roll_t < tunables.roll_iframe_end_t


func try_start_roll(stats: PlayerStats, stamina_cost: float) -> bool:
	if state != State.FREE and state != State.SPRINT:
		return false
	if not stats.spend_stamina(stamina_cost):
		return false
	state = State.ROLL
	roll_elapsed = 0.0
	return true


func try_start_light_attack(stats: PlayerStats) -> bool:
	if state == State.LIGHT_ATTACK:
		return buffer_light_attack()
	if state != State.FREE and state != State.SPRINT:
		return false
	if not stats.spend_stamina(tunables.stamina_cost_light_attack):
		return false
	state = State.LIGHT_ATTACK
	attack_elapsed = 0.0
	_light_combo_count = 1
	_light_attack_buffered = false
	return true


func buffer_light_attack() -> bool:
	if state != State.LIGHT_ATTACK:
		return false
	if attack_elapsed < tunables.light_attack_active_end or attack_elapsed >= _light_attack_duration():
		return false
	if _light_combo_count >= MAX_LIGHT_COMBO_HITS:
		return false
	_light_attack_buffered = true
	return true


func try_start_heavy_attack(stats: PlayerStats) -> bool:
	if state != State.FREE and state != State.SPRINT:
		return false
	if not stats.spend_stamina(tunables.stamina_cost_heavy_attack):
		return false
	state = State.HEAVY_ATTACK
	attack_elapsed = 0.0
	_reset_light_chain()
	return true


func advance_attack(delta: float, stats: PlayerStats) -> void:
	if not is_attacking():
		return
	attack_elapsed += delta
	if state == State.LIGHT_ATTACK and attack_elapsed >= _light_attack_duration():
		if _light_attack_buffered and _light_combo_count < MAX_LIGHT_COMBO_HITS:
			_light_attack_buffered = false
			if stats.spend_stamina(tunables.stamina_cost_light_attack):
				_light_combo_count += 1
				attack_elapsed = 0.0
				return
		_finish_attack()
	elif state == State.HEAVY_ATTACK and attack_elapsed >= _heavy_attack_duration():
		_finish_attack()


func is_attacking() -> bool:
	return state == State.LIGHT_ATTACK or state == State.HEAVY_ATTACK


func is_attack_hitbox_open() -> bool:
	# These SPEC values are literal seconds, unlike AttackData's normalized boss
	# windows. They are the greybox fallback required by invariant I2. When real
	# player clips arrive, AnimationPlayer call tracks should replace this polling
	# while preserving the same open/close contract.
	if state == State.LIGHT_ATTACK:
		return attack_elapsed >= tunables.light_attack_active_start and attack_elapsed < tunables.light_attack_active_end
	if state == State.HEAVY_ATTACK:
		var active_elapsed := attack_elapsed - tunables.heavy_attack_telegraph
		return active_elapsed >= tunables.heavy_attack_active_start and active_elapsed < tunables.heavy_attack_active_end
	return false


func get_attack_damage() -> int:
	if state == State.LIGHT_ATTACK:
		return tunables.light_attack_damage
	if state == State.HEAVY_ATTACK:
		return tunables.heavy_attack_damage
	return 0


func get_attack_poise_damage() -> float:
	if state == State.LIGHT_ATTACK:
		return tunables.light_attack_poise_damage
	if state == State.HEAVY_ATTACK:
		return tunables.light_attack_poise_damage * tunables.heavy_attack_poise_damage_multiplier
	return 0.0


func get_attack_hitstop_duration() -> float:
	if state == State.LIGHT_ATTACK:
		return tunables.light_attack_hitstop
	if state == State.HEAVY_ATTACK:
		return tunables.heavy_attack_hitstop
	return 0.0


func get_light_combo_count() -> int:
	return _light_combo_count


func try_start_flask(flask: Flask) -> bool:
	if state != State.FREE and state != State.SPRINT:
		return false
	if not flask.begin_drink():
		return false
	state = State.FLASK
	flask_elapsed = 0.0
	_reset_light_chain()
	return true


func is_flask_roll_cancelable() -> bool:
	return state == State.FLASK and flask_elapsed >= tunables.flask_roll_cancel_time and flask_elapsed < tunables.flask_animation_duration


func try_cancel_flask_into_roll(stats: PlayerStats, flask: Flask, stamina_cost: float) -> bool:
	if not is_flask_roll_cancelable():
		return false
	if not stats.spend_stamina(stamina_cost):
		return false
	flask.cancel_drink()
	state = State.ROLL
	roll_elapsed = 0.0
	flask_elapsed = 0.0
	return true


func advance_flask(delta: float, flask: Flask, stats: PlayerStats) -> void:
	if state != State.FLASK:
		return
	flask_elapsed += delta
	if flask_elapsed >= tunables.flask_animation_duration:
		flask.complete_drink(stats)
		flask_elapsed = 0.0
		state = State.FREE


func set_sprinting(enabled: bool) -> void:
	if state != State.FREE and state != State.SPRINT:
		return
	state = State.SPRINT if enabled else State.FREE


func finish_roll() -> void:
	if state == State.ROLL:
		state = State.FREE


func enter_dead() -> void:
	state = State.DEAD
	roll_elapsed = 0.0
	attack_elapsed = 0.0
	flask_elapsed = 0.0
	_reset_light_chain()


func _light_attack_duration() -> float:
	return tunables.light_attack_active_end + tunables.light_attack_recovery


func _heavy_attack_duration() -> float:
	return tunables.heavy_attack_telegraph + tunables.heavy_attack_active_end + tunables.heavy_attack_recovery


func _finish_attack() -> void:
	state = State.FREE
	attack_elapsed = 0.0
	_reset_light_chain()


func _reset_light_chain() -> void:
	_light_combo_count = 0
	_light_attack_buffered = false
