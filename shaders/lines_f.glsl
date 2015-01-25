#version 130

uniform vec4 objectColor;

in vec4 theColor;

out vec4 outColor;

void main()
{
	outColor = theColor;
	outColor *= objectColor;
}
