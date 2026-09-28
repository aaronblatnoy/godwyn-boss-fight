extends SceneTree


const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")
const TEST_SCENE := preload("res://scenes/_tests/combat_core.tscn")
const FRAME_CAP := 300
const TEST_KNOCKBACK := 2.0 # TEST HARNESS VALUE -- not a SPEC number; real values come from AttackData in a later phase.
const TEST_CAPSULE_RADIUS := 0.5 # TEST HARNESS VALUE -- not a SPEC number.
const TEST_CAPSULE_HEIGHT := 2.0 # TEST HARNESS VALUE -- not a SPEC number.
const TEST_BOSS_START_POSITION := Vector3(0.0, 0.0, -0.5) # TEST HARNESS VALUE -- not a SPEC number.
const TEST_PLAYER_REST_POSITION := Vector3(0.0, 0.0, 1.0) # TEST HARNESS VALUE -- not a SPEC number.
const TEST_PLAYER_SWING_POSITION := Vector3.ZERO # TEST HARNESS VALUE -- not a SPEC number.
const TEST_SEPARATED_POSITION := Vector3(0.0, 0.0, -3.0) # TEST HARNESS VALUE -- not a SPEC number.
const SETTLE_FRAMES := 3 # TEST HARNESS VALUE -- not a gameplay timing.


class DummyStats extends Node:
	var hp: int
	var poise: float
	var velocity: Vector3 = Vector3.ZERO


var _original_max_fps: int


func _initialize() -> void:
	call_deferred("_run")


func _run() -> void:
	_original_max_fps = Engine.max_fps
	# Test harness pacing only: gives unscaled timers deterministic frame progress.
	Engine.max_fps = 120
	Engine.time_scale = 1.0

	var scene := TEST_SCENE.instantiate()
	_configure_test_geometry(scene)
	root.add_child(scene)
	var tunables: Resource = TUNABLES_SCRIPT.new()
	var resolver := scene.get_node("HitResolver") as HitResolver
	var hitstop := scene.get_node("Hitstop") as Hitstop
	var player_dummy := scene.get_node("PlayerDummy") as Node3D
	var boss_dummy := scene.get_node("BossDummy") as Node3D
	var player_hitbox := scene.get_node("PlayerDummy/Hitbox") as Hitbox
	var player_hurtbox := scene.get_node("PlayerDummy/Hurtbox") as Hurtbox
	var boss_hitbox := scene.get_node("BossDummy/Hitbox") as Hitbox
	var boss_hurtbox := scene.get_node("BossDummy/Hurtbox") as Hurtbox
	var player_stats := DummyStats.new()
	var boss_stats := DummyStats.new()
	player_stats.hp = tunables.player_max_hp
	player_stats.poise = tunables.boss_poise
	boss_stats.hp = tunables.boss_max_hp
	boss_stats.poise = tunables.boss_poise
	scene.add_child(player_stats)
	scene.add_child(boss_stats)
	player_hurtbox.stats_target = player_stats
	boss_hurtbox.stats_target = boss_stats
	player_hurtbox.hit_resolver = resolver
	boss_hurtbox.hit_resolver = resolver
	hitstop.bind_resolver(resolver)

	player_hitbox.damage = tunables.light_attack_damage
	player_hitbox.poise_damage = tunables.light_attack_poise_damage
	player_hitbox.hitstop_duration = tunables.light_attack_hitstop
	player_hitbox.knockback = TEST_KNOCKBACK
	player_hitbox.damage_type = DamageTypes.Type.PHYSICAL
	boss_hitbox.damage = tunables.light_attack_damage
	boss_hitbox.poise_damage = tunables.light_attack_poise_damage
	boss_hitbox.hitstop_duration = tunables.light_attack_hitstop
	boss_hitbox.knockback = TEST_KNOCKBACK
	boss_hitbox.damage_type = DamageTypes.Type.PHYSICAL

	# Genuine swing: begin separated, activate, translate into the target, then
	# return to rest. Detection is exclusively engine overlap/poll driven.
	await _wait_physics_frames(SETTLE_FRAMES)
	var boss_hp_before_swing: int = boss_stats.hp
	var boss_poise_before_swing: float = boss_stats.poise
	player_hitbox.activate()
	player_dummy.position = TEST_PLAYER_SWING_POSITION
	if not await _wait_until(func() -> bool: return boss_stats.hp == boss_hp_before_swing - tunables.light_attack_damage):
		_fail("genuine capsule swing did not apply damage within frame cap")
		return
	player_hitbox.deactivate()
	player_dummy.position = TEST_PLAYER_REST_POSITION
	await _wait_physics_frames(SETTLE_FRAMES)
	if boss_stats.hp != boss_hp_before_swing - tunables.light_attack_damage:
		_fail("swing damage expected %d, got %d" % [tunables.light_attack_damage, boss_hp_before_swing - boss_stats.hp])
		return
	if not is_equal_approx(boss_stats.poise, boss_poise_before_swing - tunables.light_attack_poise_damage):
		_fail("poise damage expected %s, got %s" % [tunables.light_attack_poise_damage, boss_poise_before_swing - boss_stats.poise])
		return
	if boss_stats.velocity.is_zero_approx() or boss_stats.velocity.z >= 0.0:
		_fail("knockback was not applied along hitbox-to-hurtbox direction")
		return
	if not await _wait_until(func() -> bool: return is_equal_approx(Engine.time_scale, 1.0)):
		_fail("swing hitstop did not restore before the next sub-test")
		return

	# Regression: two activations at one fixed overlap. The second activation is
	# immediate, with no transform change between deactivate() and activate().
	player_dummy.position = TEST_PLAYER_SWING_POSITION
	await _wait_physics_frames(SETTLE_FRAMES)
	var stationary_hp_before: int = boss_stats.hp
	player_hitbox.activate()
	if not await _wait_until(func() -> bool: return boss_stats.hp == stationary_hp_before - tunables.light_attack_damage):
		_fail("first stationary activation did not hit")
		return
	await _wait_physics_frames(SETTLE_FRAMES)
	if boss_stats.hp != stationary_hp_before - tunables.light_attack_damage:
		_fail("same activation resolved more than one hit")
		return
	player_hitbox.deactivate()
	player_hitbox.activate()
	if not await _wait_until(func() -> bool: return boss_stats.hp == stationary_hp_before - tunables.light_attack_damage * 2):
		_fail("fixed-overlap reactivation did not deal the second hit")
		return
	player_hitbox.deactivate()
	if boss_stats.hp != stationary_hp_before - tunables.light_attack_damage * 2:
		_fail("fixed-overlap reactivation did not deal exactly one hit per activation")
		return
	if not await _wait_until(func() -> bool: return is_equal_approx(Engine.time_scale, 1.0)):
		_fail("stationary-hit hitstop did not restore before the next sub-test")
		return

	boss_dummy.position = TEST_SEPARATED_POSITION
	await _wait_physics_frames(SETTLE_FRAMES)
	var same_faction_hp := player_stats.hp
	player_hitbox.activate()
	await _wait_physics_frames(SETTLE_FRAMES)
	player_hitbox.deactivate()
	if player_stats.hp != same_faction_hp:
		_fail("same-faction hit registered damage")
		return

	boss_dummy.position = TEST_BOSS_START_POSITION
	player_dummy.position = TEST_PLAYER_SWING_POSITION
	await _wait_physics_frames(SETTLE_FRAMES)
	var iframe_hp := boss_stats.hp
	boss_hurtbox.monitoring = false
	await _wait_physics_frames(SETTLE_FRAMES)
	player_hitbox.activate()
	await _wait_physics_frames(SETTLE_FRAMES)
	player_hitbox.deactivate()
	if boss_stats.hp != iframe_hp:
		_fail("disabled hurtbox registered damage during simulated i-frames")
		return
	boss_hurtbox.monitoring = true
	await _wait_physics_frames(SETTLE_FRAMES)

	# Both hits below are engine-detected and their unscaled restore windows
	# overlap, exercising the reentrant hitstop counter.
	var hitstop_boss_hp: int = boss_stats.hp
	player_hitbox.activate()
	if not await _wait_until(func() -> bool: return boss_stats.hp == hitstop_boss_hp - tunables.light_attack_damage):
		_fail("first hitstop overlap did not land")
		return
	player_hitbox.deactivate()
	if not is_equal_approx(Engine.time_scale, tunables.hitstop_time_scale):
		_fail("hitstop did not set Engine.time_scale to %s" % tunables.hitstop_time_scale)
		return

	var hitstop_player_hp: int = player_stats.hp
	boss_hitbox.activate()
	if not await _wait_until(func() -> bool: return player_stats.hp == hitstop_player_hp - tunables.light_attack_damage):
		_fail("second overlapping hitstop hit did not land")
		return
	boss_hitbox.deactivate()
	if not is_equal_approx(Engine.time_scale, tunables.hitstop_time_scale):
		_fail("overlapping hitstop restored Engine.time_scale early")
		return
	if not await _wait_until(func() -> bool: return is_equal_approx(Engine.time_scale, 1.0)):
		_fail("overlapping hitstops did not restore Engine.time_scale within frame cap")
		return
	if not is_equal_approx(Engine.time_scale, 1.0):
		_fail("final Engine.time_scale sanity check failed")
		return

	scene.queue_free()
	Engine.max_fps = _original_max_fps
	print("PASS test_combat_core")
	quit(0)


func _configure_test_geometry(scene: Node) -> void:
	for path: NodePath in [
		NodePath("PlayerDummy/Hitbox/CollisionShape3D"),
		NodePath("PlayerDummy/Hurtbox/CollisionShape3D"),
		NodePath("BossDummy/Hitbox/CollisionShape3D"),
		NodePath("BossDummy/Hurtbox/CollisionShape3D"),
	]:
		var collision_shape := scene.get_node(path) as CollisionShape3D
		var capsule := collision_shape.shape as CapsuleShape3D
		capsule.radius = TEST_CAPSULE_RADIUS
		capsule.height = TEST_CAPSULE_HEIGHT
	(scene.get_node("PlayerDummy") as Node3D).position = TEST_PLAYER_REST_POSITION
	(scene.get_node("BossDummy") as Node3D).position = TEST_BOSS_START_POSITION


func _wait_physics_frames(frame_count: int) -> void:
	for _frame: int in frame_count:
		await physics_frame


func _wait_until(predicate: Callable) -> bool:
	for _frame: int in FRAME_CAP:
		if predicate.call():
			return true
		await process_frame
	return predicate.call()


func _fail(reason: String) -> void:
	Engine.time_scale = 1.0
	if not is_equal_approx(Engine.time_scale, 1.0):
		reason += "; cleanup could not restore Engine.time_scale to 1.0"
	Engine.max_fps = _original_max_fps
	print("FAIL test_combat_core: %s" % reason)
	quit(1)
