class_name AttackLibrary
extends Resource


const ATTACK_DIRECTORY := "res://resources/attacks"
const ACTIVE_CLIP_DURATION := 1.0 # PLACEHOLDER -- SPEC has no per-move numeric value; pending real animation authoring (Phase 6/9)
const DEFAULT_LIBRARY := &"godwyn_runtime"

var _attacks: Dictionary = {}


func load_default_attacks() -> void:
	_attacks.clear()
	var directory := DirAccess.open(ATTACK_DIRECTORY)
	if directory == null:
		push_error("AttackLibrary could not open %s" % ATTACK_DIRECTORY)
		return
	var file_names := directory.get_files()
	file_names.sort()
	for file_name: String in file_names:
		if not file_name.ends_with(".tres"):
			continue
		var attack := ResourceLoader.load("%s/%s" % [ATTACK_DIRECTORY, file_name]) as AttackData
		if attack == null or attack.id.is_empty():
			push_error("AttackLibrary rejected invalid attack resource %s" % file_name)
			continue
		_attacks[attack.id] = attack


func get_attack(attack_id: String) -> AttackData:
	if _attacks.is_empty():
		load_default_attacks()
	return _attacks.get(attack_id) as AttackData


func get_all_attacks() -> Array[AttackData]:
	if _attacks.is_empty():
		load_default_attacks()
	var result: Array[AttackData] = []
	for attack: Variant in _attacks.values():
		result.append(attack as AttackData)
	return result


func build_runtime_animations(animation_player: AnimationPlayer) -> void:
	if _attacks.is_empty():
		load_default_attacks()
	animation_player.callback_mode_method = AnimationMixer.ANIMATION_CALLBACK_MODE_METHOD_IMMEDIATE
	if animation_player.has_animation_library(DEFAULT_LIBRARY):
		animation_player.remove_animation_library(DEFAULT_LIBRARY)
	var library := AnimationLibrary.new()
	animation_player.add_animation_library(DEFAULT_LIBRARY, library)
	for attack: AttackData in get_all_attacks():
		_add_attack_animation(library, attack)


func ensure_runtime_animation(animation_player: AnimationPlayer, attack: AttackData) -> void:
	if attack == null or attack.animation_clip.is_empty():
		return
	var library: AnimationLibrary
	if animation_player.has_animation_library(DEFAULT_LIBRARY):
		library = animation_player.get_animation_library(DEFAULT_LIBRARY)
	else:
		library = AnimationLibrary.new()
		animation_player.add_animation_library(DEFAULT_LIBRARY, library)
	if library.has_animation(attack.animation_clip):
		library.remove_animation(attack.animation_clip)
	_add_attack_animation(library, attack)


func animation_name(attack: AttackData) -> StringName:
	if attack.animation_clip.is_empty():
		return &""
	return StringName("%s/%s" % [DEFAULT_LIBRARY, attack.animation_clip])


func _add_attack_animation(library: AnimationLibrary, attack: AttackData) -> void:
	if attack == null or attack.animation_clip.is_empty():
		return
	var animation := Animation.new()
	animation.length = ACTIVE_CLIP_DURATION
	animation.loop_mode = Animation.LOOP_NONE
	var track := animation.add_track(Animation.TYPE_METHOD)
	animation.track_set_path(track, NodePath("BossHitbox"))
	for window: Dictionary in attack.active_windows:
		if not attack.is_valid_window(window):
			push_error("Attack %s has invalid normalized active window" % attack.id)
			continue
		animation.track_insert_key(track, float(window.start_t) * ACTIVE_CLIP_DURATION, {
			"method": &"activate_window",
			"args": [window],
		})
		animation.track_insert_key(track, float(window.end_t) * ACTIVE_CLIP_DURATION, {
			"method": &"deactivate",
			"args": [],
		})
	library.add_animation(attack.animation_clip, animation)
