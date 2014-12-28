#version 130

uniform sampler2D texUnit;
uniform float scrollOffset;

in vec2 theCoords;

out vec4 outputColor;

void main()
{
	vec2 coords = theCoords;
    outputColor = texture(texUnit, coords);
}
