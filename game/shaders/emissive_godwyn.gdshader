shader_type spatial;
render_mode blend_add, unshaded, cull_disabled, depth_draw_never;

// SPEC.txt Phase 1 gold emission: color (1.0, 0.88, 0.45), strength 2.5.
uniform vec3 emission_color = vec3(1.0, 0.88, 0.45);
uniform float emission_strength = 2.5;
uniform float overlay_alpha = 0.06;

void fragment() {
	ALBEDO = emission_color;
	EMISSION = emission_color * emission_strength;
	ALPHA = overlay_alpha;
}
