shader_type canvas_item;

// Simulation-glitch post-process. The resting look is a SUBTLE cinematic grade
// (faint tint + gentle vignette + barely-there scanline). Chromatic aberration,
// datamosh bands and streaks only really show as `glitch` (0..1) spikes on events;
// main.gd drives `glitch` from the lucidity meter + brief event pulses.

uniform sampler2D screen_tex : hint_screen_texture, filter_linear;
uniform float glitch : hint_range(0.0, 1.0) = 0.05;

float rand(vec2 co) {
	return fract(sin(dot(co, vec2(12.9898, 78.233))) * 43758.5453);
}

void fragment() {
	vec2 uv = SCREEN_UV;

	// datamosh: only when glitch is genuinely high do a few bands jump
	float band = floor(uv.y * 48.0);
	float tt = floor(TIME * 14.0);
	float n = rand(vec2(band, tt));
	if (n > 1.0 - glitch * 0.45) {
		uv.x += (rand(vec2(band, tt + 3.7)) - 0.5) * glitch * 0.09;
	}

	// chromatic aberration — nearly none at rest, grows with glitch
	float ca = 0.0004 + glitch * 0.009;
	vec3 col;
	col.r = texture(screen_tex, uv + vec2(ca, 0.0)).r;
	col.g = texture(screen_tex, uv).g;
	col.b = texture(screen_tex, uv - vec2(ca, 0.0)).b;

	// gentle color grade: a hint of desaturation + cool tint + light contrast
	float luma = dot(col, vec3(0.299, 0.587, 0.114));
	col = mix(vec3(luma), col, 0.93);
	col *= vec3(0.96, 0.99, 1.03);
	col = (col - 0.5) * 1.03 + 0.5;

	// very subtle scanlines
	col *= 0.985 + 0.015 * sin(SCREEN_UV.y * 620.0);

	// soft vignette
	float vig = smoothstep(0.95, 0.4, length(SCREEN_UV - 0.5));
	col *= mix(0.92, 1.0, vig);

	// faint grain (mostly from glitch)
	col += (rand(SCREEN_UV * (TIME + 1.3)) - 0.5) * (0.005 + glitch * 0.07);

	// bright scan streaks only on strong glitch spikes
	float streak = step(1.0 - glitch * 0.35, rand(vec2(floor(uv.y * 130.0), tt)));
	col = mix(col, vec3(0.85, 0.95, 1.0), streak * glitch * 0.25);

	COLOR = vec4(col, 1.0);
}
