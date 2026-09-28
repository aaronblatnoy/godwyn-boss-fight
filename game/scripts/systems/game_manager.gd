class_name GameManager
extends Node3D


signal victory_reached

const VOID_SCENE := preload("res://scenes/environments/void.tscn")
const PLAYER_SCENE := preload("res://scenes/player/player.tscn")
const PLAYER_CAMERA_SCENE := preload("res://scenes/player/player_camera.tscn")
const HUD_SCENE := preload("res://scenes/ui/hud.tscn")
const BOSS_HEALTHBAR_SCENE := preload("res://scenes/ui/boss_healthbar.tscn")
const DEATH_SCREEN_SCENE := preload("res://scenes/ui/death_screen.tscn")
const BOSS_BASE_SCRIPT := preload("res://scripts/bosses/boss_base.gd")
const GODWYN_P1_AI_SCRIPT := preload("res://scripts/bosses/godwyn_p1_ai.gd")
const GODWYN_PHASE1_SCENE := preload("res://scenes/bosses/godwyn_phase1.tscn")
const VERTICAL_SLICE_INITIATORS: Array[String] = [
	"x_combo",
	"jump_lunge",
	"the_pause",
	"dragons_memory",
]

var arena: Node3D
var player: PlayerController
var player_camera: PlayerCamera
var boss: BossBase
var boss_ai: GodwynP1AI
var hud: CombatHud
var boss_healthbar: BossHealthbar
var death_screen: DeathScreen
var ui_layer: CanvasLayer

var _victory_emitted := false


func _ready() -> void:
	await _assemble_vertical_slice()
	print("boot ok")


func _process(_delta: float) -> void:
	if boss_ai == null:
		return
	if Input.is_action_just_pressed("light_attack") or Input.is_action_just_pressed("heavy_attack"):
		boss_ai.report_player_attack()


func _assemble_vertical_slice() -> void:
	arena = VOID_SCENE.instantiate() as Node3D
	arena.name = "Void"
	add_child(arena)

	var player_spawn := arena.get_node("PlayerSpawn") as Marker3D
	var boss_spawn := arena.get_node("BossSpawn") as Marker3D

	player = PLAYER_SCENE.instantiate() as PlayerController
	player.name = "Player"
	add_child(player)
	player.global_position = player_spawn.global_position
	if not player.is_node_ready():
		await player.ready

	player_camera = PLAYER_CAMERA_SCENE.instantiate() as PlayerCamera
	player_camera.name = "PlayerCamera"
	add_child(player_camera)
	if not player_camera.is_node_ready():
		await player_camera.ready
	player_camera.set_follow_target(player)

	boss = GODWYN_PHASE1_SCENE.instantiate() as BossBase
	boss.name = "Godwyn"
	_add_boss_lockon_marker(boss)
	add_child(boss)
	boss.global_position = boss_spawn.global_position
	if not boss.is_node_ready():
		await boss.ready

	# BossBase must finish its runtime-child and AttackLibrary setup before the AI
	# enters the tree; GodwynP1AI consumes both from its own _ready().
	boss_ai = GODWYN_P1_AI_SCRIPT.new() as GodwynP1AI
	boss_ai.name = "GodwynP1AI"
	boss_ai.boss = boss
	boss_ai.player_target = player
	boss_ai.initiator_subset = VERTICAL_SLICE_INITIATORS.duplicate()
	boss.add_child(boss_ai)

	ui_layer = CanvasLayer.new()
	ui_layer.name = "UI"
	add_child(ui_layer)

	hud = HUD_SCENE.instantiate() as CombatHud
	hud.name = "HUD"
	ui_layer.add_child(hud)
	hud.bind_player_stats(player.stats)
	hud.bind_flask(player.flask)

	boss_healthbar = BOSS_HEALTHBAR_SCENE.instantiate() as BossHealthbar
	boss_healthbar.name = "BossHealthbar"
	ui_layer.add_child(boss_healthbar)
	boss_healthbar.bind_boss_stats(boss.boss_stats)
	boss_healthbar.start_intro()

	death_screen = DEATH_SCREEN_SCENE.instantiate() as DeathScreen
	death_screen.name = "DeathScreen"
	ui_layer.add_child(death_screen)
	death_screen.bind_player_stats(player.stats)
	death_screen.restart_requested.connect(_on_restart_requested)

	boss.boss_stats.died.connect(_on_boss_died)


func _add_boss_lockon_marker(target_boss: BossBase) -> void:
	var marker := Area3D.new()
	marker.name = "LockOnMarker"
	marker.collision_layer = 0
	marker.set_collision_layer_value(9, true)
	marker.collision_mask = 0
	marker.monitoring = false
	marker.monitorable = true
	marker.set_meta(&"lockon_owner", target_boss)

	var marker_shape := CollisionShape3D.new()
	marker_shape.name = "CollisionShape3D"
	marker_shape.position.y = BossBase.BOSS_HEIGHT * 0.5
	var capsule := CapsuleShape3D.new()
	capsule.height = BossBase.BOSS_HEIGHT
	capsule.radius = BossBase.BOSS_CAPSULE_RADIUS
	marker_shape.shape = capsule
	marker.add_child(marker_shape)
	target_boss.add_child(marker)


func _on_boss_died() -> void:
	if _victory_emitted:
		return
	_victory_emitted = true
	victory_reached.emit()


func _on_restart_requested() -> void:
	get_tree().call_deferred("reload_current_scene")
