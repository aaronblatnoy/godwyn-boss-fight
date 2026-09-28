class_name HitResolver
extends Node


signal hit_landed(owner, victim, amount, poise)

var last_hitstop_duration: float = 0.0


func resolve(hitbox: Hitbox, hurtbox: Hurtbox) -> bool:
	if hitbox == null or hurtbox == null:
		return false
	if not hitbox.monitoring or not hurtbox.monitoring:
		return false
	if hitbox.owner_faction == hurtbox.faction:
		return false
	if hitbox.has_hit(hurtbox):
		return false
	if hurtbox.stats_target == null:
		push_error("HitResolver received a Hurtbox without a stats_target")
		return false

	hitbox.mark_hit(hurtbox)
	_apply_damage(hurtbox.stats_target, hitbox.damage, hitbox.damage_type)
	_apply_poise_damage(hurtbox.stats_target, hitbox.poise_damage)

	var knockback_direction := hitbox.global_position.direction_to(hurtbox.global_position)
	if knockback_direction.is_zero_approx():
		knockback_direction = Vector3.FORWARD
	_apply_knockback(hurtbox.stats_target, knockback_direction * hitbox.knockback)

	# The duration remains readable during the synchronous four-argument signal.
	last_hitstop_duration = hitbox.hitstop_duration
	var source: Node = hitbox.owner if hitbox.owner != null else hitbox
	hit_landed.emit(source, hurtbox.stats_target, hitbox.damage, hitbox.poise_damage)
	last_hitstop_duration = 0.0
	return true


func _apply_damage(target: Node, amount: int, type: DamageTypes.Type) -> void:
	if target.has_method("take_damage"):
		target.call("take_damage", amount, type)
	elif _has_property(target, &"hp"):
		target.set("hp", target.get("hp") - amount)
	else:
		push_error("HitResolver stats_target has no take_damage method or hp property")


func _apply_poise_damage(target: Node, amount: float) -> void:
	if target.has_method("take_poise_damage"):
		target.call("take_poise_damage", amount)
	elif _has_property(target, &"poise"):
		target.set("poise", target.get("poise") - amount)
	else:
		push_error("HitResolver stats_target has no take_poise_damage method or poise property")


func _apply_knockback(target: Node, impulse: Vector3) -> void:
	if target.has_method("apply_knockback"):
		target.call("apply_knockback", impulse)
	elif _has_property(target, &"velocity"):
		target.set("velocity", target.get("velocity") + impulse)
	elif _has_property(target, &"knockback_velocity"):
		target.set("knockback_velocity", target.get("knockback_velocity") + impulse)
	else:
		push_error("HitResolver stats_target has no knockback receiver")


func _has_property(object: Object, property_name: StringName) -> bool:
	for property: Dictionary in object.get_property_list():
		if property.name == property_name:
			return true
	return false
