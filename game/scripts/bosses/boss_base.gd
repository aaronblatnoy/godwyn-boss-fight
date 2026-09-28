class_name BossBase
extends Node3D


signal state_changed(old_state: State, new_state: State)
signal attack_started(attack_id: String)
signal attack_window_opened(attack_id: String)
signal attack_window_closed(attack_id: String)
signal hp_changed(new_hp: int, max_hp: int)

enum State {
	IDLE,
	TELEGRAPH,
	ACTIVE,
	RECOVERY,
	STUNNED,
	BACK_TO_PLAYER,
	AIRBORNE,
	EXTENDED,
	MEMORY_FRAG,
}

const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")
const DEFAULT_MOVESET := preload("res://resources/moveset/godwyn_p1.tres")
const BOSS_HEIGHT := 3.2 # SPEC.txt line 351 / 1408: Godwyn and the placeholder capsule are 3.2m tall.
const BOSS_CAPSULE_RADIUS := 0.6 # PLACEHOLDER -- SPEC defines height but not boss capsule radius; migrate to tunables.gd later.
const MAX_CHAIN_ATTACKS := 6 # SPEC.txt lines 366-368: the same opener can extend through six hits.

@export var moveset_tree: MovesetTree = DEFAULT_MOVESET
@export var auto_select_attacks: bool = true

var current_state: State = State.IDLE
var state_timer: float = 0.0
var current_poise: float = 0.0
var attack_library: AttackLibrary
var boss_hitbox: Hitbox
var boss_hurtbox: Hurtbox
var boss_stats: BossStats
var hit_resolver: HitResolver
var hitstop: Hitstop
var animation_player: AnimationPlayer

var _tunables: Tunables
var _rng := RandomNumberGenerator.new()
var _current_attack: AttackData
var _did_overshoot := false
var _last_hitbox_monitoring := false
var _attack_token := 0
var _chain_attack_count := 0


func _ready() -> void:
	_tunables = TUNABLES_SCRIPT.new()
	_rng.randomize()
	current_poise = _tunables.boss_poise
	_ensure_runtime_children()
	attack_library = AttackLibrary.new()
	attack_library.load_default_attacks()
	attack_library.build_runtime_animations(animation_player)
	boss_hitbox.deactivate()
	_last_hitbox_monitoring = false
	_enter_idle_with_cooldown()


func _process(delta: float) -> void:
	_emit_window_edge_signals()
	match current_state:
		State.IDLE:
			state_timer = maxf(state_timer - delta, 0.0)
			if state_timer <= 0.0 and auto_select_attacks:
				_run_tree_attack("IDLE")
		State.TELEGRAPH:
			state_timer = maxf(state_timer - delta, 0.0)
			if state_timer <= 0.0:
				_begin_active()
		State.ACTIVE:
			if not animation_player.is_playing():
				_begin_recovery()
		State.RECOVERY:
			state_timer = maxf(state_timer - delta, 0.0)
			if state_timer <= 0.0:
				_finish_attack()
		State.STUNNED:
			state_timer = maxf(state_timer - delta, 0.0)
			if state_timer <= 0.0:
				current_poise = _tunables.boss_poise
				_enter_idle_with_cooldown()
		State.MEMORY_FRAG:
			# Phase 5 owns entering, timing, and exiting the Memory Fragment buff state.
			pass


func run_attack(attack: AttackData) -> void:
	if attack == null or current_state == State.STUNNED:
		return
	_attack_token += 1
	_chain_attack_count += 1
	_current_attack = attack
	_did_overshoot = false
	boss_hitbox.damage = attack.damage
	boss_hitbox.poise_damage = attack.poise_damage
	boss_hitbox.damage_type = attack.damage_type
	boss_hitbox.deactivate()
	attack_library.ensure_runtime_animation(animation_player, attack)
	_set_state(State.TELEGRAPH)
	state_timer = maxf(attack.telegraph_time, 0.0)
	attack_started.emit(attack.id)


func report_overshoot() -> void:
	if _current_attack != null and _current_attack.overshoot_possible:
		_did_overshoot = true


func take_poise_damage(amount: float) -> void:
	if current_state == State.STUNNED or amount <= 0.0:
		return
	current_poise -= amount
	if current_poise <= 0.0:
		_interrupt_to_stunned()


func get_current_attack() -> AttackData:
	return _current_attack


func get_hp() -> int:
	return boss_stats.hp if boss_stats != null else 0


func get_max_hp() -> int:
	return boss_stats.max_hp if boss_stats != null else 0


func state_name() -> String:
	return State.keys()[current_state]


func _begin_active() -> void:
	if _current_attack == null:
		_enter_idle_with_cooldown()
		return
	_set_state(State.ACTIVE)
	animation_player.play(attack_library.animation_name(_current_attack))


func _begin_recovery() -> void:
	boss_hitbox.deactivate()
	_set_state(State.RECOVERY)
	state_timer = maxf(_current_attack.recovery_time, 0.0) if _current_attack != null else 0.0


func _finish_attack() -> void:
	if _current_attack == null:
		_enter_idle_with_cooldown()
		return
	var finished_attack := _current_attack
	var overshot := _did_overshoot
	var next_state_name := moveset_tree.resolve_post_attack_state(finished_attack, overshot)
	_current_attack = null
	_did_overshoot = false
	if _chain_attack_count >= MAX_CHAIN_ATTACKS:
		_enter_idle_with_cooldown()
		return
	if not auto_select_attacks:
		if next_state_name.is_empty() or next_state_name == "IDLE":
			_enter_idle_with_cooldown()
		else:
			_set_state(_state_from_name(next_state_name))
		return
	var followup_id := ""
	if overshot:
		followup_id = moveset_tree.pick_next_attack("BACK_TO_PLAYER", _rng)
	elif not finished_attack.exit_options.is_empty():
		# An empty result here is a failed continue_probability roll, not a
		# request to fall through to the state's generic exits.
		followup_id = moveset_tree.pick_attack_followup(finished_attack, _rng)
	elif not next_state_name.is_empty() and next_state_name != "IDLE":
		followup_id = moveset_tree.pick_next_attack(next_state_name, _rng)
	if followup_id.is_empty():
		_enter_idle_with_cooldown()
		return
	var attack := attack_library.get_attack(followup_id)
	if attack == null:
		push_error("Moveset state %s resolved missing attack_id %s" % [next_state_name, followup_id])
		_enter_idle_with_cooldown()
		return
	run_attack(attack)


func _run_tree_attack(from_state: String) -> void:
	var attack_id := moveset_tree.pick_next_attack(from_state, _rng)
	if attack_id.is_empty():
		_enter_idle_with_cooldown()
		return
	var attack := attack_library.get_attack(attack_id)
	if attack == null:
		push_error("Moveset state %s has no resolvable attack" % from_state)
		auto_select_attacks = false
		return
	if from_state == "IDLE":
		_chain_attack_count = 0
	run_attack(attack)


func _interrupt_to_stunned() -> void:
	_attack_token += 1
	animation_player.stop()
	boss_hitbox.deactivate()
	_current_attack = null
	_did_overshoot = false
	_set_state(State.STUNNED)
	state_timer = _tunables.boss_stagger_duration


func _enter_idle_with_cooldown() -> void:
	boss_hitbox.deactivate()
	_chain_attack_count = 0
	_set_state(State.IDLE)
	state_timer = _rng.randf_range(
		_tunables.boss_global_cooldown_min,
		_tunables.boss_global_cooldown_max
	)


func _set_state(next_state: State) -> void:
	if current_state == next_state:
		return
	var old_state := current_state
	current_state = next_state
	state_changed.emit(old_state, next_state)


func _emit_window_edge_signals() -> void:
	if boss_hitbox == null or boss_hitbox.monitoring == _last_hitbox_monitoring:
		return
	_last_hitbox_monitoring = boss_hitbox.monitoring
	var attack_id := _current_attack.id if _current_attack != null else ""
	if _last_hitbox_monitoring:
		attack_window_opened.emit(attack_id)
	else:
		attack_window_closed.emit(attack_id)


func _state_from_name(value: String) -> State:
	var index := State.keys().find(value)
	if index < 0:
		push_error("Unknown boss state %s" % value)
		return State.IDLE
	return index as State


func _ensure_runtime_children() -> void:
	boss_stats = get_node_or_null("BossStats") as BossStats
	if boss_stats == null:
		boss_stats = BossStats.new()
		boss_stats.name = "BossStats"
		add_child(boss_stats)
	boss_stats.combat_target = self
	if not boss_stats.hp_changed.is_connected(_on_boss_hp_changed):
		boss_stats.hp_changed.connect(_on_boss_hp_changed)
	hit_resolver = get_node_or_null("HitResolver") as HitResolver
	if hit_resolver == null:
		hit_resolver = HitResolver.new()
		hit_resolver.name = "HitResolver"
		add_child(hit_resolver)
	hitstop = get_node_or_null("Hitstop") as Hitstop
	if hitstop == null:
		hitstop = Hitstop.new()
		hitstop.name = "Hitstop"
		add_child(hitstop)
	hitstop.bind_resolver(hit_resolver)
	boss_hitbox = get_node_or_null("BossHitbox") as Hitbox
	if boss_hitbox == null:
		boss_hitbox = Hitbox.new()
		boss_hitbox.name = "BossHitbox"
		boss_hitbox.owner_faction = "boss"
		add_child(boss_hitbox)
	boss_hitbox.owner_faction = "boss"
	_ensure_capsule_shape(boss_hitbox)
	boss_hurtbox = get_node_or_null("BossHurtbox") as Hurtbox
	if boss_hurtbox == null:
		boss_hurtbox = Hurtbox.new()
		boss_hurtbox.name = "BossHurtbox"
		boss_hurtbox.faction = "boss"
		add_child(boss_hurtbox)
	boss_hurtbox.faction = "boss"
	boss_hurtbox.stats_target = boss_stats
	boss_hurtbox.hit_resolver = hit_resolver
	_ensure_capsule_shape(boss_hurtbox)
	animation_player = get_node_or_null("AnimationPlayer") as AnimationPlayer
	if animation_player == null:
		animation_player = AnimationPlayer.new()
		animation_player.name = "AnimationPlayer"
		add_child(animation_player)


func _ensure_capsule_shape(area: Area3D) -> void:
	var collision_shape := area.get_node_or_null("CollisionShape3D") as CollisionShape3D
	if collision_shape == null:
		collision_shape = CollisionShape3D.new()
		collision_shape.name = "CollisionShape3D"
		area.add_child(collision_shape)
	if collision_shape.shape == null:
		var capsule := CapsuleShape3D.new()
		capsule.height = BOSS_HEIGHT
		capsule.radius = BOSS_CAPSULE_RADIUS
		collision_shape.shape = capsule


func _on_boss_hp_changed(new_hp: int, maximum_hp: int) -> void:
	hp_changed.emit(new_hp, maximum_hp)
