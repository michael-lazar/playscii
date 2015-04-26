uniform mat4 projection;
uniform mat4 view;
uniform vec3 objectPosition;
uniform vec3 objectScale;
uniform vec2 quadSize;

in vec3 vertPosition;
in vec4 vertColor;

out vec4 theColor;

mat4 scale(float x, float y, float z)
{
    return mat4(
        vec4(x,   0.0, 0.0, 0.0),
        vec4(0.0, y,   0.0, 0.0),
        vec4(0.0, 0.0, z,   0.0),
        vec4(0.0, 0.0, 0.0, 1.0)
    );
}

void main()
{
	vec4 model = vec4(vertPosition * vec3(quadSize, 1), 1);
	// scale and transform model
	model *= scale(objectScale.x, objectScale.y, objectScale.z);
	model += vec4(objectPosition, 0);
	// apply camera
	gl_Position = projection * view * model;
	theColor = vertColor;
}
