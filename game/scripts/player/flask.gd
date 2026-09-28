class_name Flask
extends Node


# Flask owns this signal because it is the charge authority. HUD code can bind
# directly to this node; PlayerStats remains focused on HP/stamina/FP mutations.
signal flask_changed(charges: int, max_charges: int)

const TUNABLES_SCRIPT := preload("res://scripts/systems/tunables.gd")

var tunables := TUNABLES_SCRIPT.new()
var charges: int = 0
var _is_drinking: bool = false


func _ready() -> void:
	charges = tunables.flask_count


func begin_drink() -> bool:
	if _is_drinking or charges <= 0:
		return false
	charges -= 1
	_is_drinking = true
	flask_changed.emit(charges, tunables.flask_count)
	return true


func complete_drink(stats: PlayerStats) -> void:
	if not _is_drinking:
		return
	# PLACEHOLDER -- SPEC gives no finer-grained heal-frame timing, so the heal
	# frame is the end of the configured 0.6-second drink until a clip is authored.
	_is_drinking = false
	stats.heal(tunables.flask_heal)


func cancel_drink() -> void:
	# The already-consumed charge is intentionally never refunded.
	_is_drinking = false


func refill() -> void:
	if charges == tunables.flask_count:
		return
	charges = tunables.flask_count
	flask_changed.emit(charges, tunables.flask_count)


func is_drinking() -> bool:
	return _is_drinking
