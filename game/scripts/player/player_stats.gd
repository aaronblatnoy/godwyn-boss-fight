class_name PlayerStats
extends Node


signal hp_changed(new_hp: int, max_hp: int)
signal stamina_changed(new_stamina: float, max_stamina: float)
signal died

const TunablesScript := preload("res://scripts/systems/tunables.gd")

var tunables := TunablesScript.new()
var hp: int
var stamina: float
## DISPLAY-ONLY in Phase 2. SPEC Section 3 defines only the maximum FP;
## no FP-consuming actions or FP recovery model exist yet, so this stays static.
var fp: int
var is_dead: bool = false
var _stamina_recovery_delay_remaining: float = 0.0


func _ready() -> void:
	hp = tunables.player_max_hp
	stamina = tunables.player_max_stamina
	fp = tunables.player_max_fp


func take_damage(amount: int, _damage_type: DamageTypes.Type = DamageTypes.Type.PHYSICAL) -> void:
	if is_dead:
		return
	hp = maxi(hp - amount, 0)
	hp_changed.emit(hp, tunables.player_max_hp)
	if hp == 0:
		is_dead = true
		died.emit()


func take_poise_damage(_amount: float) -> void:
	# Player poise is not part of the Phase 2 contract. This receiver keeps the
	# shared HitResolver interface explicit until a later phase defines it.
	pass


func apply_knockback(impulse: Vector3) -> void:
	var body := get_parent() as CharacterBody3D
	if body != null:
		body.velocity += impulse


func spend_stamina(amount: float) -> bool:
	if amount < 0.0 or stamina < amount:
		return false
	stamina -= amount
	stamina_changed.emit(stamina, float(tunables.player_max_stamina))
	_stamina_recovery_delay_remaining = tunables.stamina_recovery_delay
	return true


func process_stamina_regen(delta: float, is_actively_costing: bool) -> void:
	if is_actively_costing or stamina >= tunables.player_max_stamina:
		return
	var regen_delta := delta
	if _stamina_recovery_delay_remaining > 0.0:
		var delay_step := minf(_stamina_recovery_delay_remaining, regen_delta)
		_stamina_recovery_delay_remaining -= delay_step
		regen_delta -= delay_step
	if regen_delta > 0.0:
		var previous_stamina := stamina
		stamina = minf(stamina + tunables.stamina_recovery_rate * regen_delta, tunables.player_max_stamina)
		if not is_equal_approx(stamina, previous_stamina):
			stamina_changed.emit(stamina, float(tunables.player_max_stamina))
