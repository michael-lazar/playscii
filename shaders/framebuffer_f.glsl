// plain vanilla (non CRT) screen shader

precision mediump float;

uniform sampler2D fbo_texture;
uniform float elapsed_time;
in vec2 f_texcoord;
out vec4 f_outPixel;

void main(void) {
	vec2 texcoord = f_texcoord;
	f_outPixel = texture(fbo_texture, texcoord);
}
