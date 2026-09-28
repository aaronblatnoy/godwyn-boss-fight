class_name Tunables
extends Resource

# Phase 0 contains only values fixed by SPEC.txt or the authoritative reference.
#
# FROM elden-ring-combat-reference.md
# - Roll stamina: reference Section 1c says EXACT 12; this overrides SPEC's 15.
# - Roll i-frame boundaries: reference Section 1a says exact TAE indices are
#   UNKNOWN and its 433-467 ms duration is APPROX, so SPEC's exact 0.2-0.4 s
#   project window remains in force.
# - Stamina recovery: reference Section 2b gives only a disputed approximate
#   rate and a 0.5-1.0 s range, so SPEC's exact 25/s and 0.8 s remain in force.
# - R1/R2 stamina costs: reference Section 2c says weapon-dependent and gives no
#   directly conflicting constant, so SPEC's exact 12/22 values remain.
# - Lock-on: SPEC.txt Sections 3/4 define this project's 25 m acquisition and
#   35 m break distances. Reference Section 7's 2 s keep-alive is retained only
#   as supplementary context for a later phase; it does not override SPEC.

# --- PLAYER ---
@export var player_max_hp: int = 500 # SPEC.txt Section 3
@export var player_max_stamina: int = 100 # SPEC.txt Section 3
@export var player_max_fp: int = 80 # SPEC.txt Section 3
@export var player_walk_speed: float = 3.5 # SPEC.txt Section 3, meters/second
@export var player_sprint_speed: float = 6.5 # SPEC.txt Section 3, meters/second
@export var player_rotation_speed_degrees: float = 720.0 # SPEC.txt Section 3, degrees/second
@export var player_lockon_strafe_speed: float = 3.5 # SPEC.txt Section 3, meters/second
@export var player_mouse_sensitivity: float = 0.3 # SPEC.txt Section 3
@export var flask_count: int = 5 # SPEC.txt Section 3
@export var flask_heal: int = 180 # SPEC.txt Section 3; ref Section 4 has no matching upgrade tier
@export var flask_animation_duration: float = 0.6 # SPEC.txt Section 3; ref ~3 s is APPROX
@export var flask_roll_cancel_time: float = 0.3 # SPEC.txt Section 3
@export var death_delay: float = 0.8 # SPEC.txt Section 3
@export var death_screen_fade_duration: float = 0.5 # SPEC.txt Section 3
@export var death_text_fade_duration: float = 0.5 # SPEC.txt Section 3
@export var death_text_hold_duration: float = 2.5 # SPEC.txt Section 3

# --- STAMINA ---
@export var stamina_cost_light_attack: int = 12 # SPEC.txt Section 3; ref Section 2c has no global R1 constant
@export var stamina_cost_heavy_attack: int = 22 # SPEC.txt Section 3; ref Section 2c has no global R2 constant
@export var stamina_cost_roll: int = 12 # ref Section 1c EXACT; overrides SPEC.txt Section 3 value 15
@export var stamina_cost_sprint_per_second: float = 5.0 # SPEC.txt Section 3
@export var stamina_recovery_delay: float = 0.8 # SPEC.txt Section 3; ref Section 2b APPROX range includes it
@export var stamina_recovery_rate: float = 25.0 # SPEC.txt Section 3; ref Section 2b is disputed APPROX

# --- ROLL ---
@export var roll_distance: float = 3.5 # SPEC.txt Section 3, meters
@export var roll_duration: float = 0.65 # SPEC.txt Section 3, seconds
@export var roll_iframe_start_frame: int = 4 # SPEC.txt Section 3; ref exact TAE index UNKNOWN
@export var roll_iframe_end_frame: int = 16 # SPEC.txt Section 3; ref exact TAE index UNKNOWN
@export var roll_iframe_start_seconds: float = 0.2 # SPEC.txt Section 3, framerate-independent runtime contract
@export var roll_iframe_end_seconds: float = 0.4 # SPEC.txt Section 3, framerate-independent runtime contract

# --- ATTACKS ---
@export var light_attack_damage: int = 60 # SPEC.txt Section 3
@export var light_attack_active_start: float = 0.15 # SPEC.txt Section 3, seconds
@export var light_attack_active_end: float = 0.35 # SPEC.txt Section 3, seconds
@export var light_attack_recovery: float = 0.4 # SPEC.txt Section 3, seconds
@export var light_attack_hitstop: float = 0.06 # SPEC.txt Section 3; ref Section 8a value UNKNOWN
@export var light_attack_poise_damage: float = 15.0 # SPEC.txt Section 6, Godwyn poise per light
@export var heavy_attack_damage: int = 110 # SPEC.txt Section 3
@export var heavy_attack_telegraph: float = 0.4 # SPEC.txt Section 3, seconds
@export var heavy_attack_active_start: float = 0.2 # SPEC.txt Section 3, seconds
@export var heavy_attack_active_end: float = 0.55 # SPEC.txt Section 3, seconds
@export var heavy_attack_recovery: float = 0.7 # SPEC.txt Section 3, seconds
@export var heavy_attack_hitstop: float = 0.1 # SPEC.txt Section 3; ref Section 8a value UNKNOWN
@export var heavy_attack_poise_damage_multiplier: float = 2.0 # SPEC.txt Section 3; 2 x light = 30, matching Section 6

# --- LOCK-ON ---
@export var lockon_max_range: float = 25.0 # SPEC.txt Section 3/4; lock-on range is a SPEC design decision, NOT in plan Assumption A6's reference-doc-override list
@export var lockon_break_range: float = 35.0 # SPEC.txt Section 3; lock-on range is a SPEC design decision, NOT in plan Assumption A6's reference-doc-override list
@export var lockon_break_grace_seconds: float = 2.0 # ref Section 7 EXACT; supplementary/deferred context, not wired in Phase 0
@export var lockon_camera_lerp: float = 8.0 # SPEC.txt Section 3

# --- BOSS ---
@export var boss_max_hp: int = 3000 # SPEC.txt Section 6; ref has no Godwyn-specific HP
@export var boss_poise: int = 80 # SPEC.txt Section 6; ref has no conflicting exact Godwyn value
@export var boss_stagger_duration: float = 0.8 # SPEC.txt Section 6; ref says exact boss window UNKNOWN

# --- LIGHTNING (Phase 1.5) ---
@export var lightning_unlock_hp_percent: float = 0.5 # SPEC.txt Section 7B
@export var lightning_threshold_tell_duration: float = 1.5 # SPEC.txt Section 7B, seconds
@export var lightning_pattern_marker_warning: float = 0.6 # SPEC.txt Section 7B, seconds
@export var lightning_pattern_strike_interval: float = 0.2 # SPEC.txt Section 7B, seconds
@export var lightning_targeted_strike_count_min: int = 3 # SPEC.txt Section 7B
@export var lightning_targeted_strike_count_max: int = 5 # SPEC.txt Section 7B
@export var lightning_targeted_strike_interval: float = 0.4 # SPEC.txt Section 7B, seconds
@export var lightning_mid_melee_warning: float = 0.25 # SPEC.txt Section 7B, seconds
@export var lightning_stationary_trigger_time: float = 0.5 # SPEC.txt Section 7B, seconds
@export var lightning_horizontal_sweep_tell: float = 0.5 # SPEC.txt Section 7B, seconds
@export var lightning_shrinking_circle_warning: float = 0.8 # SPEC.txt Section 7B, seconds
@export var lightning_shrinking_circle_hold: float = 2.0 # SPEC.txt Section 7B, seconds
@export var lightning_shrinking_circle_start_radius: float = 15.0 # SPEC.txt Section 7B, approximate (~) meters
@export var lightning_shrinking_circle_end_radius: float = 4.0 # SPEC.txt Section 7B, approximate (~) meters
@export var lightning_shrinking_circle_contraction_speed: float = 1.5 # SPEC.txt Section 7B, approximate (~) meters/second
@export var lightning_shrinking_circle_contraction_duration: float = 7.0 # SPEC.txt Section 7B, approximate (~) seconds
@export var lightning_dragons_charge_fire_line_width: float = 4.0 # SPEC.txt Section 7B, approximate (~) meters
@export var lightning_slam_aoe_radius: float = 8.0 # SPEC.txt Section 7B, meters
# NOT YET NUMERIC — SPEC describes strike AoE/damage qualitatively; defer to boss-phase AttackData resources.
# NOT YET NUMERIC — Dragon's Charge trigger timing/damage are qualitative; defer to boss-phase AttackData resources.

# --- COMBAT ---
@export var hitstop_time_scale: float = 0.05 # SPEC.txt Section 3
