shader_type canvas_item;

// Subtle drifting ground fog. Screen-space, low alpha; layered over the dark world
// to add depth and atmosphere (light scatters through it a little).

uniform float density : hint_range(0.0, 0.5) = 0.16;
uniform vec3 fog_col = vec3(0.05, 0.07, 0.10);

float hash(vec2 p) { return fract(sin(dot(p, vec2(41.3, 289.1))) * 43758.5453); }

float noise(vec2 p) {
	vec2 i = floor(p);
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = hash(i);
	float b = hash(i + vec2(1.0, 0.0));
	float c = hash(i + vec2(0.0, 1.0));
	float d = hash(i + vec2(1.0, 1.0));
	return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

void fragment() {
	vec2 uv = SCREEN_UV * vec2(4.0, 2.5);
	float n = noise(uv + vec2(TIME * 0.025, TIME * 0.015));
	n += 0.5 * noise(uv * 2.1 - vec2(TIME * 0.04, TIME * 0.01));
	n = clamp(n * 0.62, 0.0, 1.0);
	COLOR = vec4(fog_col, n * density);
}
