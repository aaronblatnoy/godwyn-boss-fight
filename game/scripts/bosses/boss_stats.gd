class_name BossStats
extends Node


signal hp_changed(new_hp: int, max_hp: int)
signal died()

const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")

var max_hp: int
var hp: int
var combat_target: Node
var knockback_velocity := Vector3.ZERO
var _died_emitted := false


func _init() -> void:
	var tunables: Tunables = TUNABLES_SCRIPT.new()
	max_hp = tunables.boss_max_hp
	hp = max_hp


func take_damage(amount: int, _damage_type) -> void:
	if amount <= 0 or hp <= 0:
		return
	var old_hp := hp
	hp = clampi(hp - amount, 0, max_hp)
	hp_changed.emit(hp, max_hp)
	if old_hp > 0 and hp == 0 and not _died_emitted:
		_died_emitted = true
		died.emit()


func take_poise_damage(amount: float) -> void:
	if combat_target != null and combat_target.has_method("take_poise_damage"):
		combat_target.call("take_poise_damage", amount)


func apply_knockback(impulse: Vector3) -> void:
	knockback_velocity += impulse
