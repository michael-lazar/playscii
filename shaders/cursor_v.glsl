uniform mat4 projection;
uniform mat4 view;
uniform vec3 objectPosition;
uniform vec3 objectScale;
uniform vec2 quadSize;
uniform vec2 vertTransform;
uniform vec2 vertOffset;

in vec3 vertPosition;

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
	float z = vertPosition.z;
	vec4 xform = vec4(vertTransform, 1, 1);
	vec4 offset = vec4(vertOffset, 0, 0);
	// apply scale to offsets rather than to model; more space between brackets
	offset *= scale(objectScale.x, objectScale.y, objectScale.z);
	// model = all 4 corners in the right place
	vec4 model = vec4(vertPosition, 1) * xform + offset;
	model += vec4(objectPosition, 0);
	// this stretches the cursor according to charset aspect, but fixes Y weirdness
	model *= vec4(quadSize, 1, 1);
	// apply camera
	gl_Position = projection * view * model;
}
