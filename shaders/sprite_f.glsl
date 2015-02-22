#version 130

uniform sampler2D texture0;
uniform float alpha;

in vec2 theCoords;

out vec4 outColor;

void main()
{
	outColor = texture2D(texture0, theCoords);
	outColor.a *= alpha;
}
