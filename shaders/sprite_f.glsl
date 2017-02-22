precision mediump float;

uniform sampler2D texture0;
uniform float alpha;
uniform vec2 texScale;

in vec2 theCoords;

out vec4 outColor;

void main()
{
	outColor = texture(texture0, theCoords.xy * texScale);
	outColor.a *= alpha;
}
