class_name AttackData
extends Resource


@export var id: String = ""
@export var initiator: bool = false
@export var telegraph_time: float = 0.0
@export var active_windows: Array[Dictionary] = []
@export var recovery_time: float = 0.0
@export var damage: int = 0
@export var poise_damage: float = 0.0
@export var damage_type: DamageTypes.Type = DamageTypes.Type.PHYSICAL
@export var animation_clip: String = ""
@export var enters_state: String = ""
@export var exit_options: Array[Dictionary] = []
@export var overshoot_possible: bool = false
@export var camera_pull: float = 0.0
@export var cut_vocabulary: String = ""


func is_valid_window(window: Dictionary) -> bool:
	var start_t: float = float(window.get("start_t", -1.0))
	var end_t: float = float(window.get("end_t", -1.0))
	return start_t >= 0.0 and end_t <= 1.0 and start_t < end_t
