#version 130

uniform mat4 projection;
uniform mat4 view;
uniform vec3 objectPosition;

attribute vec3 vertPosition;

void main()
{
	gl_Position = projection * view * (vec4(objectPosition, 0) + vec4(vertPosition, 1));
}
