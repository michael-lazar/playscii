#version 130

// plain vanilla (non CRT) screen shader

uniform sampler2D fbo_texture;
uniform float elapsed_time;
varying vec2 f_texcoord;

void main(void) {
	vec2 texcoord = f_texcoord;
	gl_FragColor = texture2D(fbo_texture, texcoord);
}
