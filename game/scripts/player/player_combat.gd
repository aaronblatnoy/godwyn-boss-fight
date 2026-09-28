class_name PlayerCombat
extends Node


const TunablesScript := preload("res://scripts/systems/tunables.gd")

enum State {
	FREE,
	SPRINT,
	ROLL,
	DEAD,
}

var tunables := TunablesScript.new()
var state: State = State.FREE
var roll_elapsed: float = 0.0


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


func set_sprinting(enabled: bool) -> void:
	if state == State.DEAD or state == State.ROLL:
		return
	state = State.SPRINT if enabled else State.FREE


func finish_roll() -> void:
	if state == State.ROLL:
		state = State.FREE


func enter_dead() -> void:
	state = State.DEAD
	roll_elapsed = 0.0
