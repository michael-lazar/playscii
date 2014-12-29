#version 130

uniform sampler2D texUnit;
uniform float scrollOffset;

in vec2 theCoords;
in vec4 theFGColor;
in vec4 theBGColor;

out vec4 outputColor;

void main()
{
	vec2 coords = theCoords;
    outputColor = texture(texUnit, coords);
	outputColor.rgb = theFGColor.rgb;
	if ( outputColor.a == 0.0 ) {
		outputColor = theBGColor;
	}
}
