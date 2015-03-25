#version 150

uniform sampler2D texture0;
uniform float alpha;

in vec2 theCoords;

out vec4 outColor;

void main()
{
	outColor = texture(texture0, theCoords);
	outColor.a *= alpha;
}
