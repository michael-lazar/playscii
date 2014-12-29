#version 130

uniform mat4 projection;
uniform mat4 view;
//uniform mat4 rotation;
//uniform mat4 scale;

in vec3 vertPosition;
in vec2 texCoords;
in vec4 fgColor;
in vec4 bgColor;

out vec2 theCoords;
out vec4 theFGColor;
out vec4 theBGColor;

void main()
{
	gl_Position = projection * view * vec4(vertPosition, 1);
    theCoords = texCoords;
	theFGColor = fgColor;
	theBGColor = bgColor;
}
