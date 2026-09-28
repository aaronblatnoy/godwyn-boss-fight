extends SceneTree


const ATTACK_DATA_SCRIPT := preload("res://scripts/bosses/attack_data.gd")
const BOSS_BASE_SCRIPT := preload("res://scripts/bosses/boss_base.gd")
const TEST_SCENE := preload("res://scenes/_tests/player_combat.tscn")
const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")
const FRAME_CAP := 900 # TEST HARNESS VALUE -- deterministic wait guard.
const SETTLE_FRAMES := 5 # TEST HARNESS VALUE -- physics stabilization only.
const BOSS_POSITION := Vector3(0.0, 0.0, -1.0) # TEST HARNESS VALUE -- overlap placement only.
const BOSS_ATTACK_DAMAGE := 37 # TEST HARNESS VALUE -- bidirectional integration proof only.
const BOSS_WINDOW_RADIUS := 2.0 # TEST HARNESS VALUE -- overlap geometry only.
const BOSS_SHORT_WINDOW_END := 0.08 # TEST HARNESS VALUE -- fits wholly inside the roll i-frame window.
const BOSS_HIT_WINDOW_END := 0.2 # TEST HARNESS VALUE -- outside-i-frame overlap proof.
const HALF_STAGGER_RATIO := 0.5 # TEST HARNESS VALUE -- midpoint duration probe.
const FLASK_CANCEL_MARGIN := 0.04 # TEST HARNESS VALUE -- keeps the probe inside [0.3s, 0.6s).

var _original_max_fps: int
var _original_time_scale: float
var _scene: Node
var _player: PlayerController
var _stats: PlayerStats
var _combat: PlayerCombat
var _flask: Flask
var _weapon_hitbox: Hitbox
var _hurtbox: Hurtbox
var _boss: BossBase
var _tunables: Tunables
var _flask_signal_count: int = 0
var _poise_break_count: int = 0
var _poise_break_stagger_timer: float = 0.0
var _player_to_boss_hitstop_duration: float = 0.0
var _boss_to_player_hitstop_duration: float = 0.0


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	_original_max_fps = Engine.max_fps
	_original_time_scale = Engine.time_scale
	Engine.max_fps = 120
	Engine.time_scale = 1.0
	_tunables = TUNABLES_SCRIPT.new()
	_scene = TEST_SCENE.instantiate()
	root.add_child(_scene)
	_player = _scene.get_node("Player") as PlayerController
	_stats = _player.get_node("Stats") as PlayerStats
	_combat = _player.get_node("Combat") as PlayerCombat
	_flask = _player.get_node("Flask") as Flask
	_weapon_hitbox = _player.get_node("HandSocket/WeaponHitbox") as Hitbox
	_hurtbox = _player.get_node("Hurtbox") as Hurtbox
	_boss = BOSS_BASE_SCRIPT.new() as BossBase
	_boss.name = "Boss"
	_boss.auto_select_attacks = false
	_boss.position = BOSS_POSITION
	_scene.add_child(_boss)
	await _wait_physics_frames(SETTLE_FRAMES)
	_boss.hit_resolver.hit_landed.connect(_on_player_to_boss_hit_landed)
	_player.hit_resolver.hit_landed.connect(_on_boss_to_player_hit_landed)
	_boss.poise_broken.connect(_on_boss_poise_broken)

	if not _player.is_on_floor():
		_fail("player did not settle on the test floor")
		return
	if _hurtbox.hit_resolver == null or _player.hitstop == null or _boss.hitstop == null:
		_fail("production bidirectional HitResolver/Hitstop wiring is incomplete")
		return
	if not _test_normalized_attack_windows():
		return
	if not await _test_light_attack():
		return
	if not await _test_heavy_attack():
		return
	if not await _test_light_combo():
		return
	if not await _test_stamina_gate():
		return
	if not await _test_real_poise_stagger():
		return
	if not _test_poise_regen_after_delay():
		return
	if not await _test_boss_damage_and_roll_iframes():
		return
	if not await _test_flask():
		return

	_cleanup_inputs()
	_scene.queue_free()
	Engine.time_scale = _original_time_scale
	Engine.max_fps = _original_max_fps
	print("PASS test_player_combat")
	quit(0)


func _test_light_attack() -> bool:
	_reset_boss()
	_player_to_boss_hitstop_duration = 0.0
	_stats.stamina = _tunables.player_max_stamina
	var stamina_before := _stats.stamina
	var hp_before := _boss.get_hp()
	var poise_before := _boss.current_poise
	await _tap_action(&"light_attack")
	if _combat.state != PlayerCombat.State.LIGHT_ATTACK:
		_fail("light input did not enter LIGHT_ATTACK")
		return false
	if not is_equal_approx(_stats.stamina, stamina_before - _tunables.stamina_cost_light_attack):
		_fail("light attack did not spend its configured stamina up front")
		return false
	if _weapon_hitbox.monitoring:
		_fail("light weapon hitbox opened before light_attack_active_start")
		return false
	var expected_start_t := _tunables.light_attack_active_start / (_tunables.light_attack_active_end + _tunables.light_attack_recovery)
	if _combat.get_attack_t() >= expected_start_t:
		_fail("light attack test did not begin before its normalized active window")
		return false
	if not await _wait_until(func() -> bool: return _weapon_hitbox.monitoring):
		_fail("light weapon hitbox never opened")
		return false
	if not await _wait_until(func() -> bool: return _boss.get_hp() < hp_before):
		_fail("light attack did not damage the real boss")
		return false
	if _boss.get_hp() != hp_before - _tunables.light_attack_damage:
		_fail("light damage did not match tunables.light_attack_damage")
		return false
	if not is_equal_approx(_boss.current_poise, poise_before - _tunables.light_attack_poise_damage):
		_fail("light poise damage did not match tunables.light_attack_poise_damage")
		return false
	if not is_equal_approx(Engine.time_scale, _tunables.hitstop_time_scale):
		_fail("player-on-boss light hit did not start hitstop")
		return false
	if not is_equal_approx(_player_to_boss_hitstop_duration, _tunables.light_attack_hitstop):
		_fail("light attack did not propagate light_attack_hitstop through HitResolver")
		return false
	if not await _wait_for_time_scale_one() or not await _wait_for_free():
		_fail("light attack or its hitstop did not finish")
		return false
	return true


func _test_heavy_attack() -> bool:
	_reset_boss()
	_player_to_boss_hitstop_duration = 0.0
	_stats.stamina = _tunables.player_max_stamina
	var stamina_before := _stats.stamina
	var hp_before := _boss.get_hp()
	var poise_before := _boss.current_poise
	await _tap_action(&"heavy_attack")
	if _combat.state != PlayerCombat.State.HEAVY_ATTACK:
		_fail("heavy input did not enter HEAVY_ATTACK")
		return false
	if not is_equal_approx(_stats.stamina, stamina_before - _tunables.stamina_cost_heavy_attack):
		_fail("heavy attack did not spend its configured stamina up front")
		return false
	if not await _wait_until(func() -> bool: return _combat.attack_elapsed >= _tunables.heavy_attack_telegraph):
		_fail("heavy attack never completed its telegraph")
		return false
	if _weapon_hitbox.monitoring or _boss.get_hp() != hp_before:
		_fail("heavy telegraph did not keep the weapon hitbox closed")
		return false
	if not await _wait_until(func() -> bool: return _weapon_hitbox.monitoring):
		_fail("heavy weapon hitbox never opened after telegraph")
		return false
	if not await _wait_until(func() -> bool: return _boss.get_hp() < hp_before):
		_fail("heavy attack did not damage the real boss")
		return false
	if _boss.get_hp() != hp_before - _tunables.heavy_attack_damage:
		_fail("heavy damage did not match tunables.heavy_attack_damage")
		return false
	var expected_poise := _tunables.light_attack_poise_damage * _tunables.heavy_attack_poise_damage_multiplier
	if not is_equal_approx(_boss.current_poise, poise_before - expected_poise):
		_fail("heavy poise damage did not apply the configured multiplier")
		return false
	if not is_equal_approx(Engine.time_scale, _tunables.hitstop_time_scale):
		_fail("player-on-boss heavy hit did not start hitstop")
		return false
	if not is_equal_approx(_player_to_boss_hitstop_duration, _tunables.heavy_attack_hitstop):
		_fail("heavy attack did not propagate heavy_attack_hitstop through HitResolver")
		return false
	if not await _wait_for_time_scale_one() or not await _wait_for_free():
		_fail("heavy attack or its hitstop did not finish")
		return false
	return true


func _test_light_combo() -> bool:
	_reset_boss()
	_boss.current_poise = 10000.0 # TEST HARNESS VALUE -- isolate combo damage from stagger.
	_stats.stamina = _tunables.player_max_stamina
	var hp_before := _boss.get_hp()
	if not await _queue_three_hit_combo():
		return false
	if _combat.state != PlayerCombat.State.LIGHT_ATTACK or _combat.get_light_combo_count() != _tunables.light_attack_combo_max_hits:
		_fail("buffered chain returned to FREE before the third light began")
		return false
	if not await _wait_for_free():
		_fail("three-hit light chain did not finish")
		return false
	if _boss.get_hp() != hp_before - _tunables.light_attack_damage * _tunables.light_attack_combo_max_hits:
		_fail("buffered light chain did not deal exactly three damage instances")
		return false
	return true


func _test_stamina_gate() -> bool:
	_stats.stamina = _tunables.stamina_cost_light_attack - 1.0
	var stamina_before := _stats.stamina
	await _tap_action(&"light_attack")
	if _combat.state != PlayerCombat.State.FREE or not is_equal_approx(_stats.stamina, stamina_before):
		_fail("light attack was not blocked cleanly below its stamina cost")
		return false
	return true


func _test_real_poise_stagger() -> bool:
	_reset_boss()
	_poise_break_count = 0
	_poise_break_stagger_timer = 0.0
	_stats.stamina = _tunables.player_max_stamina
	if not await _queue_three_hit_combo() or not await _wait_for_free():
		_fail("first poise-pressure combo did not finish")
		return false
	if _boss.current_state == BossBase.State.STUNNED:
		_fail("boss staggered before enough configured light poise damage accrued")
		return false
	_stats.stamina = _tunables.player_max_stamina
	if not await _queue_three_hit_combo():
		return false
	if not await _wait_until(func() -> bool: return _boss.current_state == BossBase.State.STUNNED):
		_fail("real player Hitbox path did not poise-break the boss into STUNNED")
		return false
	if _poise_break_count != 1:
		_fail("real poise break did not emit exactly one poise_broken signal")
		return false
	if not is_equal_approx(_poise_break_stagger_timer, _tunables.boss_stagger_duration):
		_fail("real poise break did not initialize the full boss_stagger_duration")
		return false
	await create_timer(_tunables.boss_stagger_duration * HALF_STAGGER_RATIO).timeout
	if _boss.current_state != BossBase.State.STUNNED:
		_fail("real-hit STUNNED state ended before boss_stagger_duration")
		return false
	var punish_hp_before := _boss.get_hp()
	if not await _wait_for_free():
		_fail("player did not recover in time to use the real stagger punish window")
		return false
	_stats.stamina = _tunables.player_max_stamina
	await _tap_action(&"light_attack")
	if not await _wait_until(func() -> bool: return _boss.get_hp() < punish_hp_before):
		_fail("follow-up player hit did not land during the real stagger punish window")
		return false
	if _boss.current_state != BossBase.State.STUNNED:
		_fail("boss left STUNNED before the real punish hit landed")
		return false
	if not await _wait_until(func() -> bool: return _boss.current_state == BossBase.State.IDLE):
		_fail("real-hit STUNNED state did not return to IDLE")
		return false
	if not is_equal_approx(_boss.current_poise, float(_tunables.boss_poise)):
		_fail("boss poise did not reset after stagger exit")
		return false
	if not await _wait_for_free():
		_fail("player did not finish the poise-breaking combo")
		return false
	return true


func _test_poise_regen_after_delay() -> bool:
	_reset_boss()
	_boss.take_poise_damage(_tunables.light_attack_poise_damage)
	var damaged_poise := _boss.current_poise
	_boss._process(_tunables.boss_poise_regen_delay * 0.5)
	if not is_equal_approx(_boss.current_poise, damaged_poise):
		_fail("boss poise regenerated before boss_poise_regen_delay")
		return false
	var regen_step := 0.25 # TEST HARNESS VALUE -- direct deterministic regen step.
	_boss._process(_tunables.boss_poise_regen_delay * 0.5 + regen_step)
	var expected_poise := damaged_poise + _tunables.boss_poise_regen_rate * regen_step
	if not is_equal_approx(_boss.current_poise, expected_poise):
		_fail("boss poise did not regenerate at boss_poise_regen_rate after the delay")
		return false
	_boss._process(float(_tunables.boss_poise))
	if not is_equal_approx(_boss.current_poise, float(_tunables.boss_poise)):
		_fail("boss poise regeneration did not clamp to boss_poise")
		return false
	return true


func _test_boss_damage_and_roll_iframes() -> bool:
	_stats.hp = _tunables.player_max_hp
	_boss_to_player_hitstop_duration = 0.0
	var hp_before := _stats.hp
	var attack := _make_boss_attack("player_damage", BOSS_HIT_WINDOW_END)
	_boss.run_attack(attack)
	_boss.boss_hitbox.hitstop_duration = _tunables.light_attack_hitstop
	if not await _wait_until(func() -> bool: return _stats.hp < hp_before):
		_fail("real boss AttackData/Hitbox did not damage the production player Hurtbox")
		return false
	if _stats.hp != hp_before - BOSS_ATTACK_DAMAGE:
		_fail("boss-to-player damage did not apply exactly once")
		return false
	if not is_equal_approx(Engine.time_scale, _tunables.hitstop_time_scale):
		_fail("boss-on-player hit did not start hitstop")
		return false
	if not is_equal_approx(_boss_to_player_hitstop_duration, _tunables.light_attack_hitstop):
		_fail("boss-on-player hit did not propagate its authored duration through HitResolver")
		return false
	if not await _wait_for_time_scale_one():
		_fail("boss-on-player hitstop did not restore")
		return false

	_stats.stamina = _tunables.player_max_stamina
	if not await _start_roll():
		_fail("could not start the real-boss i-frame proof roll")
		return false
	var inside_t := (_tunables.roll_iframe_start_t + _tunables.roll_iframe_end_t) * 0.5
	if not await _wait_for_roll_t(inside_t) or _hurtbox.monitoring:
		_fail("player did not reach the disabled-Hurtbox i-frame window")
		return false
	hp_before = _stats.hp
	_boss.global_position = _player.global_position
	_boss.run_attack(_make_boss_attack("iframe_attack", BOSS_SHORT_WINDOW_END))
	_boss.boss_hitbox.hitstop_duration = _tunables.light_attack_hitstop
	if not await _wait_until(func() -> bool: return _boss.boss_hitbox.monitoring):
		_fail("real boss i-frame attack never opened its Hitbox")
		return false
	if not await _wait_until(func() -> bool: return not _boss.boss_hitbox.monitoring):
		_fail("real boss i-frame attack never closed its Hitbox")
		return false
	if _stats.hp != hp_before:
		_fail("real boss attack damaged the player inside roll i-frames")
		return false
	if not await _wait_for_free():
		_fail("i-frame proof roll did not finish")
		return false

	_stats.stamina = _tunables.player_max_stamina
	if not await _start_roll():
		_fail("could not start the outside-i-frame proof roll")
		return false
	var outside_t := (_tunables.roll_iframe_end_t + 1.0) * 0.5
	if not await _wait_for_roll_t(outside_t) or not _hurtbox.monitoring:
		_fail("player did not become vulnerable while the roll was still active")
		return false
	hp_before = _stats.hp
	_boss.global_position = _player.global_position
	_boss.run_attack(_make_boss_attack("outside_iframe_attack", BOSS_HIT_WINDOW_END))
	_boss.boss_hitbox.hitstop_duration = _tunables.light_attack_hitstop
	if not await _wait_until(func() -> bool: return _stats.hp < hp_before):
		_fail("real boss attack did not damage the player outside roll i-frames")
		return false
	if _stats.hp != hp_before - BOSS_ATTACK_DAMAGE:
		_fail("outside-i-frame boss attack did not apply exactly once")
		return false
	if not await _wait_for_time_scale_one() or not await _wait_for_free():
		_fail("outside-i-frame roll or hitstop did not finish")
		return false
	return true


func _test_flask() -> bool:
	_stats.hp = _tunables.player_max_hp - _tunables.flask_heal - 20 # TEST HARNESS VALUE -- verifies unclamped healing.
	var hp_before := _stats.hp
	var charges_before := _flask.charges
	_flask_signal_count = 0
	_flask.flask_changed.connect(_on_flask_changed)
	await _tap_action(&"use_flask")
	if _combat.state != PlayerCombat.State.FLASK or _flask.charges != charges_before - 1:
		_fail("flask did not consume one charge immediately on drink start")
		return false
	if _flask_signal_count != 1:
		_fail("flask_changed did not fire for the consumed charge")
		return false
	if not await _wait_for_free():
		_fail("undisturbed flask drink did not finish")
		return false
	if _stats.hp != mini(hp_before + _tunables.flask_heal, _tunables.player_max_hp):
		_fail("completed flask did not heal tunables.flask_heal")
		return false
	if _flask.charges != charges_before - 1:
		_fail("completed flask unexpectedly refunded its charge")
		return false

	_stats.hp = _tunables.player_max_hp - _tunables.flask_heal - 20
	_stats.stamina = _tunables.player_max_stamina
	hp_before = _stats.hp
	charges_before = _flask.charges
	await _tap_action(&"use_flask")
	if _flask.charges != charges_before - 1:
		_fail("cancel-test flask did not consume its charge immediately")
		return false
	var stamina_before := _stats.stamina
	await _tap_action(&"roll")
	if _combat.state != PlayerCombat.State.FLASK or not is_equal_approx(_stats.stamina, stamina_before):
		_fail("flask allowed a roll cancel before flask_roll_cancel_time")
		return false
	if not await _wait_until(func() -> bool: return _combat.flask_elapsed >= _tunables.flask_roll_cancel_time + FLASK_CANCEL_MARGIN):
		_fail("flask never reached its roll-cancel window")
		return false
	stamina_before = _stats.stamina
	await _tap_action(&"roll")
	if _combat.state != PlayerCombat.State.ROLL:
		_fail("eligible flask roll-cancel did not enter a real ROLL")
		return false
	if not is_equal_approx(_stats.stamina, stamina_before - _tunables.stamina_cost_roll):
		_fail("flask-cancel roll did not spend normal roll stamina")
		return false
	if _stats.hp != hp_before:
		_fail("cancelled flask applied healing before its placeholder heal frame")
		return false
	if _flask.charges != charges_before - 1:
		_fail("cancelled flask refunded its consumed charge")
		return false
	if not await _wait_for_free():
		_fail("flask-cancel roll did not finish normally")
		return false

	while _flask.charges > 0:
		if not _flask.begin_drink():
			_fail("remaining flask charge could not be consumed")
			return false
		_flask.cancel_drink()
	if _flask.begin_drink():
		_fail("empty flask started another drink")
		return false
	await process_frame
	if _flask.charges != 0:
		_fail("flask charges refilled during the active attempt")
		return false
	var restarted_flask := Flask.new()
	root.add_child(restarted_flask)
	await process_frame
	if restarted_flask.charges != _tunables.flask_count:
		_fail("fresh attempt Flask did not initialize with flask_count charges")
		restarted_flask.queue_free()
		return false
	restarted_flask.queue_free()
	return true


func _test_normalized_attack_windows() -> bool:
	var light_duration := _tunables.light_attack_active_end + _tunables.light_attack_recovery
	_combat.state = PlayerCombat.State.LIGHT_ATTACK
	_combat.attack_elapsed = _tunables.light_attack_active_start
	var light_start_t := _tunables.light_attack_active_start / light_duration
	if not is_equal_approx(_combat.get_attack_t(), light_start_t) or not _combat.is_attack_hitbox_open():
		_fail("light normalized active-start boundary did not open the hitbox")
		return false
	_combat.attack_elapsed = _tunables.light_attack_active_end
	var light_end_t := _tunables.light_attack_active_end / light_duration
	if not is_equal_approx(_combat.get_attack_t(), light_end_t) or _combat.is_attack_hitbox_open():
		_fail("light normalized active-end boundary did not close the hitbox")
		return false

	var heavy_duration := (
		_tunables.heavy_attack_telegraph
		+ _tunables.heavy_attack_active_end
		+ _tunables.heavy_attack_recovery
	)
	var heavy_active_start := _tunables.heavy_attack_telegraph + _tunables.heavy_attack_active_start
	var heavy_active_end := _tunables.heavy_attack_telegraph + _tunables.heavy_attack_active_end
	_combat.state = PlayerCombat.State.HEAVY_ATTACK
	_combat.attack_elapsed = heavy_active_start
	if not is_equal_approx(_combat.get_attack_t(), heavy_active_start / heavy_duration) or not _combat.is_attack_hitbox_open():
		_fail("heavy normalized active-start boundary did not open after its telegraph")
		return false
	_combat.attack_elapsed = heavy_active_end
	if not is_equal_approx(_combat.get_attack_t(), heavy_active_end / heavy_duration) or _combat.is_attack_hitbox_open():
		_fail("heavy normalized active-end boundary did not close the hitbox")
		return false

	_combat.state = PlayerCombat.State.FREE
	_combat.attack_elapsed = 0.0
	return true


func _queue_three_hit_combo() -> bool:
	await _tap_action(&"light_attack")
	if _combat.state != PlayerCombat.State.LIGHT_ATTACK:
		_fail("combo opener did not start")
		return false
	if not await _wait_until(func() -> bool: return _combat.attack_elapsed >= _tunables.light_attack_active_end):
		_fail("combo opener never reached recovery")
		return false
	await _tap_action(&"light_attack")
	if not await _wait_until(func() -> bool: return _combat.get_light_combo_count() == 2):
		_fail("first buffered light was not consumed into hit two")
		return false
	if _combat.state != PlayerCombat.State.LIGHT_ATTACK:
		_fail("light combo returned to FREE between hits one and two")
		return false
	if not await _wait_until(func() -> bool: return _combat.attack_elapsed >= _tunables.light_attack_active_end):
		_fail("second combo hit never reached recovery")
		return false
	await _tap_action(&"light_attack")
	if not await _wait_until(func() -> bool: return _combat.get_light_combo_count() == _tunables.light_attack_combo_max_hits):
		_fail("second buffered light was not consumed into hit three")
		return false
	if not await _wait_until(func() -> bool: return _combat.attack_elapsed >= _tunables.light_attack_active_end):
		_fail("third combo hit never reached recovery")
		return false
	await _tap_action(&"light_attack")
	if _combat.get_light_combo_count() != _tunables.light_attack_combo_max_hits:
		_fail("light combo accepted a hit beyond light_attack_combo_max_hits")
		return false
	return true


func _make_boss_attack(attack_id: String, window_end: float) -> AttackData:
	var attack := ATTACK_DATA_SCRIPT.new() as AttackData
	attack.id = attack_id
	attack.telegraph_time = 0.0
	attack.active_windows = [{
		"start_t": 0.0,
		"end_t": window_end,
		"radius": BOSS_WINDOW_RADIUS,
		"position": Vector3(0.0, 1.0, 0.0),
	}]
	attack.recovery_time = 0.0
	attack.damage = BOSS_ATTACK_DAMAGE
	attack.poise_damage = 0.0
	attack.animation_clip = attack_id
	attack.enters_state = "IDLE"
	return attack


func _reset_boss() -> void:
	_boss.boss_stats.hp = _tunables.boss_max_hp
	_boss.current_poise = _tunables.boss_poise
	_boss.boss_hitbox.deactivate()


func _on_flask_changed(_charges: int, _maximum: int) -> void:
	_flask_signal_count += 1


func _on_boss_poise_broken() -> void:
	_poise_break_count += 1
	_poise_break_stagger_timer = _boss.state_timer


func _on_player_to_boss_hit_landed(_owner: Variant, _victim: Variant, _amount: Variant, _poise: Variant) -> void:
	_player_to_boss_hitstop_duration = _boss.hit_resolver.last_hitstop_duration


func _on_boss_to_player_hit_landed(_owner: Variant, _victim: Variant, _amount: Variant, _poise: Variant) -> void:
	_boss_to_player_hitstop_duration = _player.hit_resolver.last_hitstop_duration


func _tap_action(action: StringName) -> void:
	Input.action_press(action)
	await physics_frame
	await process_frame
	Input.action_release(action)
	await process_frame


func _start_roll() -> bool:
	await _tap_action(&"roll")
	return _combat.state == PlayerCombat.State.ROLL


func _wait_for_roll_t(target_t: float) -> bool:
	return await _wait_until(
		func() -> bool:
			return _combat.state == PlayerCombat.State.ROLL and _combat.get_roll_t() >= target_t
	)


func _wait_for_free() -> bool:
	return await _wait_until(func() -> bool: return _combat.state == PlayerCombat.State.FREE)


func _wait_for_time_scale_one() -> bool:
	return await _wait_until(func() -> bool: return is_equal_approx(Engine.time_scale, 1.0))


func _wait_until(predicate: Callable) -> bool:
	for _frame: int in FRAME_CAP:
		if predicate.call():
			return true
		await physics_frame
	return predicate.call()


func _wait_physics_frames(frame_count: int) -> void:
	for _frame: int in frame_count:
		await physics_frame


func _cleanup_inputs() -> void:
	for action: StringName in [&"move_fwd", &"move_back", &"move_left", &"move_right", &"sprint", &"roll", &"light_attack", &"heavy_attack", &"use_flask"]:
		Input.action_release(action)


func _fail(reason: String) -> void:
	_cleanup_inputs()
	Engine.time_scale = _original_time_scale
	Engine.max_fps = _original_max_fps
	print("FAIL test_player_combat: %s" % reason)
	quit(1)
