#version 130

uniform mat4 projection;
uniform mat4 view;
//uniform mat4 rotation;
//uniform mat4 scale;

in vec3 vertPosition;
in vec2 texCoords;

out vec2 theCoords;

void main()
{
	gl_Position = projection * view * vec4(vertPosition, 1);
    theCoords = texCoords;
}
