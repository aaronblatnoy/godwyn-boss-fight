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
# SPEC-derived normalized window: start_t = 0.2 / 0.65, end_t = 0.4 / 0.65.
# Frame->t is t = frame / assumed_clip_length_frames. The approximate frame labels
# imply 4 / start_t = 13 frames and 16 / end_t = 26 frames, so they cannot yet name
# one real clip length. Until Phase 9 imports it, derive t from the authoritative
# seconds window: roll_iframe_*_t = roll_iframe_*_seconds / roll_duration.
var roll_iframe_start_t: float:
	get:
		return roll_iframe_start_seconds / roll_duration
var roll_iframe_end_t: float:
	get:
		return roll_iframe_end_seconds / roll_duration

# --- ATTACKS ---
@export var light_attack_damage: int = 60 # SPEC.txt Section 3
@export var light_attack_active_start: float = 0.15 # SPEC.txt Section 3, seconds
@export var light_attack_active_end: float = 0.35 # SPEC.txt Section 3, seconds
@export var light_attack_recovery: float = 0.4 # SPEC.txt Section 3, seconds
@export var light_attack_hitstop: float = 0.06 # SPEC.txt Section 3; ref Section 8a value UNKNOWN
@export var light_attack_poise_damage: float = 15.0 # SPEC.txt Section 6, Godwyn poise per light
# PLAN CONTRACT / PLACEHOLDER, NO SPEC/REFERENCE SOURCE VALUE -- Phase 6 requires a 2-3 hit player chain; cap it at 3.
@export var light_attack_combo_max_hits: int = 3
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
@export var lockon_break_grace_seconds: float = 2.0 # ref Section 7 EXACT lockTgtKeepTime; continuous out-of-range grace prevents mobile-target lock flicker
@export var lockon_camera_lerp: float = 8.0 # SPEC.txt Section 3

# --- BOSS ---
@export var boss_max_hp: int = 3000 # SPEC.txt Section 6; ref has no Godwyn-specific HP
@export var boss_poise: int = 80 # SPEC.txt Section 6; ref has no conflicting exact Godwyn value
@export var boss_stagger_duration: float = 0.8 # SPEC.txt Section 6; ref says exact boss window UNKNOWN
@export var boss_poise_regen_delay: float = 6.0 # ref Section 3e APPROX community feel; SPEC requires regen but gives no value
@export var boss_poise_regen_rate: float = 13.0 # ref Section 3e APPROX community value; SPEC requires regen but gives no value
@export var boss_global_cooldown_min: float = 0.5 # SPEC.txt Section 6
@export var boss_global_cooldown_max: float = 1.4 # SPEC.txt Section 6

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

# --- ARENA ---
@export var arena_boundary_radius: float = 20.0 # SPEC.txt Section 5, Arena Playable radius: 20 meters / Boundary

# --- CAMERA ---
@export var camera_default_distance: float = 2.5 # SPEC.txt Section 4, meters behind player
@export var camera_default_height: float = 1.4 # SPEC.txt Section 4, meters above player
@export var camera_default_fov: float = 75.0 # SPEC.txt Section 4, degrees
@export var camera_pitch_clamp_min_degrees: float = -60.0 # SPEC.txt Section 4
@export var camera_pitch_clamp_max_degrees: float = 80.0 # SPEC.txt Section 4
@export var camera_lockon_fov: float = 72.0 # SPEC.txt Section 4, degrees
@export var camera_lockon_distance_min: float = 3.0 # SPEC.txt Section 4, meters
@export var camera_lockon_distance_max: float = 8.0 # SPEC.txt Section 4, meters
@export var camera_lockon_position_lerp: float = 6.0 # SPEC.txt Section 4 (distinct from the existing lockon_camera_lerp=8.0, which is the rotation lerp from SPEC Section 3)
# PLACEHOLDER -- SPEC.txt Sections 3/4 require boss upper-center framing but do not specify the exact target-focus weight; 0.68 biases the existing composition toward the boss. Replace when a real value lands, pending design review.
@export var camera_lockon_focus_target_weight: float = 0.68
# PLACEHOLDER -- SPEC.txt Sections 3/4 require the player lower-left but do not specify the exact screen-offset ratio; 0.12 supplies the existing lateral composition. Replace when a real value lands, pending design review.
@export var camera_lockon_player_screen_offset_ratio: float = 0.12
@export var camera_pullback_distance: float = 8.0 # SPEC.txt Section 4, Dynamic Pullback
@export var camera_pullback_in_time: float = 0.3 # SPEC.txt Section 4
@export var camera_pullback_return_time: float = 0.5 # SPEC.txt Section 4

# --- UI (SPEC Section 14) ---
@export var ui_player_left_margin: float = 40.0 # SPEC.txt Section 14, pixels
@export var ui_player_hp_bottom_offset: float = 80.0 # SPEC.txt Section 14, pixels
@export var ui_player_hp_size: Vector2 = Vector2(280.0, 14.0) # SPEC.txt Section 14, pixels
@export var ui_player_hp_color: Color = Color("c00000") # SPEC.txt Section 14
@export var ui_player_hp_border_color: Color = Color("000000") # SPEC.txt Section 14
@export var ui_player_hp_background_color: Color = Color("1a0000") # SPEC.txt Section 14
@export var ui_player_fp_gap: float = 8.0 # SPEC.txt Section 14, pixels below HP
@export var ui_player_fp_size: Vector2 = Vector2(200.0, 10.0) # SPEC.txt Section 14, pixels
@export var ui_player_fp_color: Color = Color("0050a0") # SPEC.txt Section 14
@export var ui_player_stamina_gap: float = 8.0 # SPEC.txt Section 14, pixels below FP
@export var ui_player_stamina_size: Vector2 = Vector2(240.0, 10.0) # SPEC.txt Section 14, pixels
@export var ui_player_stamina_color: Color = Color("7a9a20") # SPEC.txt Section 14
@export var ui_player_flask_gap: float = 12.0 # SPEC.txt Section 14, pixels below stamina
# PLACEHOLDER -- SPEC.txt Section 14 does not specify the empty-flask alpha; 0.35 visibly dims it while preserving the silhouette. Replace when real value lands.
@export var ui_player_flask_empty_alpha: float = 0.35
# PLACEHOLDER -- SPEC.txt Section 14 does not specify FP/stamina background colors; neutral black keeps the specified fills legible. Replace when real value lands.
@export var ui_player_secondary_bar_background_color: Color = Color("000000")
@export var ui_boss_bottom_offset: float = 40.0 # SPEC.txt Section 14, pixels
@export var ui_boss_hp_size: Vector2 = Vector2(600.0, 14.0) # SPEC.txt Section 14, pixels
@export var ui_boss_hp_color: Color = Color("c00000") # SPEC.txt Section 14
# PLACEHOLDER -- SPEC.txt Section 14 does not specify the boss-bar background color; reuse the specified player-HP background. Replace when real value lands.
@export var ui_boss_hp_background_color: Color = Color("1a0000")
@export var ui_boss_name_delay: float = 0.5 # SPEC.txt Section 14, seconds
@export var ui_boss_name_fade_duration: float = 0.6 # SPEC.txt Section 14, seconds
@export var ui_boss_name_line_1_size: int = 28 # SPEC.txt Section 14, points
@export var ui_boss_name_line_2_size: int = 16 # SPEC.txt Section 14, points
# PLACEHOLDER -- SPEC.txt Section 14 does not specify the exact "white with gold tint" hex; #FDEBC8 is the interpreted tint. Replace when real value lands.
@export var ui_boss_name_line_1_color: Color = Color("fdebc8")
# PLACEHOLDER -- SPEC.txt Section 14 does not specify numeric italic shear; 0.18 supplies the requested italic treatment. Replace when real value lands.
@export var ui_boss_name_line_2_italic_shear: float = 0.18
# PLACEHOLDER -- SPEC.txt Section 14 does not specify exact glyph spacing; 1 px supplies the requested slight letter spacing. Replace when real value lands.
@export var ui_boss_name_line_2_glyph_spacing: int = 1
# PLACEHOLDER -- SPEC.txt Section 14 does not specify the Dragon's Memory secondary-bar size; 400x8 keeps the stub subordinate to the boss bar. Replace when real value lands.
@export var ui_dragon_hp_size: Vector2 = Vector2(400.0, 8.0)
# PLACEHOLDER -- SPEC.txt Section 14 does not specify the Dragon's Memory secondary-bar offset; 122 px keeps the stub separate from the boss bar. Replace when real value lands.
@export var ui_dragon_hp_bottom_offset: float = 122.0
# PLACEHOLDER -- SPEC.txt Section 14 does not specify the Dragon's Memory secondary-bar color; #70B7A8 distinguishes the stub from boss HP. Replace when real value lands.
@export var ui_dragon_hp_color: Color = Color("70b7a8")
# PLACEHOLDER -- SPEC.txt Section 14 does not specify the Dragon's Memory secondary-bar background; #102624 supports the interpreted fill. Replace when real value lands.
@export var ui_dragon_hp_background_color: Color = Color("102624")
@export var ui_death_text_color: Color = Color("c8986e") # SPEC.txt Section 14
# PLACEHOLDER -- SPEC.txt Sections 3/14 do not specify the numeric "large" text size; 64 px provides the requested prominence. Replace when real value lands.
@export var ui_death_text_size: int = 64

# --- BOSS AI (Phase 5) ---
@export var boss_perception_close_range: float = 4.0 # SPEC.txt Section 6, "Close (< 4m)"
@export var boss_perception_mid_range: float = 10.0 # SPEC.txt Section 6, "Mid (4-10m)" upper bound
@export var boss_max_stillness_seconds: float = 1.5 # SPEC.txt Section 6, "never stays still for more than 1.5s except during THE PAUSE"
@export var boss_pause_duration_min: float = 3.0 # SPEC.txt Section 7, THE PAUSE: "Duration: 3.0-5.0s randomized"
@export var boss_pause_duration_max: float = 5.0 # SPEC.txt Section 7, THE PAUSE
@export var boss_pause_counter_delay: float = 0.12 # SPEC.txt Section 7, THE PAUSE: "He steps offline at 0.12s after input"
@export var boss_pause_cooldown: float = 15.0 # SPEC.txt Section 7, THE PAUSE: "The Pause cooldown: 15.0s"
# SPEC.txt Section 7, THE PAUSE: "Jump lunge weighted +30%"; interpreted as multiplicative (weight *= 1 + bonus) because SPEC gives no formula.
@export var boss_pause_wait_jump_lunge_bonus: float = 0.30
# PLACEHOLDER -- SPEC.txt Section 6 says only "closes distance gradually"; below player_walk_speed (3.5) to keep pursuit deliberate. Replace when real timing data lands.
@export var boss_pursuit_speed: float = 2.5
# PLACEHOLDER -- SPEC.txt Section 6 says only "circles the player slowly"; 3.0 keeps the orbital component faster than the gradual 2.5 m/s closing component. Replace when real timing data lands.
@export var boss_circle_speed: float = 3.0
# PLACEHOLDER -- SPEC.txt Section 7 says only "steps offline"; 1.5 meters makes the counter reposition measurable without leaving the 20m arena. Replace when real timing data lands.
@export var boss_pause_counter_step_distance: float = 1.5
@export var boss_memory_fragment_threshold_75: float = 0.75 # SPEC.txt lines 634-650, MEMORY FRAGMENT: 75% HP threshold
@export var boss_memory_fragment_threshold_50: float = 0.50 # SPEC.txt lines 634-650, MEMORY FRAGMENT: 50% HP threshold
@export var boss_memory_fragment_threshold_25: float = 0.25 # SPEC.txt lines 634-650, MEMORY FRAGMENT: 25% HP threshold
@export var boss_memory_fragment_duration: float = 10.0 # SPEC.txt lines 634-650, MEMORY FRAGMENT: 10.0s duration
@export var boss_memory_fragment_damage_multiplier: float = 1.25 # SPEC.txt lines 634-650, MEMORY FRAGMENT: all damage +25%
@export var boss_memory_fragment_move_speed_multiplier: float = 1.12 # SPEC.txt lines 634-650, MEMORY FRAGMENT: move speed +12%
@export var boss_memory_fragment_transition_time_multiplier: float = 0.85 # SPEC.txt lines 634-650, MEMORY FRAGMENT: transition time between cycles -15%
