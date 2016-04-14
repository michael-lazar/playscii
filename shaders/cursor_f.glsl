precision mediump float;

uniform vec4 baseColor;
uniform float baseAlpha;

out vec4 outColor;

void main()
{
	outColor = baseColor;
	outColor.a *= baseAlpha;
}
